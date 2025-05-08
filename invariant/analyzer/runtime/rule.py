import os
import textwrap
from typing import Optional, Callable, TypeVar, ParamSpec, Awaitable

import invariant.analyzer.language.ast as ast
from invariant.analyzer.language.linking import link
from invariant.analyzer.runtime.evaluation import (
    EvaluationContext,
    EvaluationResult,
    Interpreter,
    Unknown,
)
from invariant.analyzer.runtime.function_cache import FunctionCache
from invariant.analyzer.runtime.input import Input
from invariant.analyzer.runtime.symbol_table import SymbolTable
from invariant.analyzer.stdlib.invariant.errors import ErrorInformation

P = ParamSpec("P")
R = TypeVar("R")

class PolicyAction:
    def __call__(self, input_dict):
        raise NotImplementedError()

    async def can_eval(self, input_dict, evaluation_context):
        raise NotImplementedError()


class RaiseAction(PolicyAction):
    def __init__(self, exception_or_constructor, globals):
        self.exception_or_constructor = exception_or_constructor
        self.globals = globals

    async def can_eval(self, input_dict, evaluation_context):
        res = await Interpreter.eval(
            self.exception_or_constructor,
            input_dict,
            self.globals,
            partial=True,
            evaluation_context=evaluation_context,
        )
        return res is not Unknown

    async def __call__(self, model: EvaluationResult, evaluation_context=None):
        from invariant.analyzer.stdlib.invariant.errors import PolicyViolation

        if type(self.exception_or_constructor) is ast.StringLiteral:
            return PolicyViolation(self.exception_or_constructor.value, ranges=model.ranges)
        elif isinstance(self.exception_or_constructor, ast.Expression):
            exception = await Interpreter.eval(
                self.exception_or_constructor,
                model.variable_assignments,
                self.globals,
                partial=False,
                evaluation_context=evaluation_context,
            )

            if isinstance(exception, ErrorInformation):
                exception.ranges = model.ranges
            elif not isinstance(exception, BaseException):
                exception = PolicyViolation(str(exception), ranges=model.ranges)

            return exception
        else:
            print("raising", self.exception_or_constructor, "not implemented")
            return None


class RuleApplication:
    """
    Represents the output of applying a rule to a set of input data.
    """

    rule: "Rule"
    models: list[EvaluationResult]

    def __init__(self, rule, models):
        self.rule = rule
        self.models: list[EvaluationResult] = models

    def applies(self):
        return len(self.models) > 0

    async def execute(self, evaluation_context, rule_idx: int):
        errors = []
        for model in self.models:
            exc = await self.rule.action(model, evaluation_context)
            # if the action does not return something, we assume it is a success
            if exc is not None:
                # augment error information with unique identifier of the underlying variable assignment (model)
                if isinstance(exc, ErrorInformation):
                    exc.key = str((rule_idx, model.result_key()))
                # append the error to the list of errors
                errors.append((model, exc))

        return errors


class Rule:
    def __init__(
        self,
        action: PolicyAction,
        condition: list[ast.Expression],
        globals: dict,
        repr: str | None = None,
    ):
        self.action = action
        self.condition = condition
        self.globals = globals
        self.repr = repr
        # enables logging of all evaluated models and partial models
        self.verbose = os.environ.get("INVARIANT_VERBOSE", False)

    def __repr__(self):
        return self.repr or f"Rule({self.action}, {self.condition}, {self.input_variables})"

    def __str__(self):
        return repr(self)

    async def action_can_eval(self, input_dict: dict, ctx: EvaluationContext):
        """Returns true iff self.action can be evaluated with the given input_dict and context (all relevant variables have already been assigned)."""
        return await self.action.can_eval(input_dict, ctx)

    async def apply(self, input_data: Input, evaluation_context=None) -> RuleApplication:
        models = [
            m
            async for m in Interpreter.assignments(
                self.condition,
                input_data,
                globals=self.globals,
                verbose=self.verbose,
                extra_check=self.action_can_eval,
                evaluation_context=evaluation_context,
            )
            if m.result is True
        ]

        # locate ranges in input
        for m in models:
            m.ranges = input_data.locate(m.ranges)

        return RuleApplication(self, models)

    @classmethod
    def from_raise_policy(cls, policy: ast.RaisePolicy, globals):
        # return Rule object
        return cls(
            RaiseAction(policy.exception_or_constructor, globals),
            policy.body,
            globals,
            "<Rule raise '" + policy.location.code.get_line(policy.location) + "'>",
        )


class InputEvaluationContext(EvaluationContext):
    def __init__(
        self, input: Input, rule_set: "RuleSet", policy_parameters, symbol_table: Optional[SymbolTable]
    ):
        super().__init__(symbol_table=symbol_table)
        self.input = input
        self.rule_set = rule_set
        self.policy_parameters = policy_parameters

    async def acall_function(self, func: Callable[P, Awaitable[R]] | Callable[P, R], *args: P.args, **kwargs: P.kwargs) -> R:
        return await self.rule_set.acall_function(func, *args, **kwargs)

    def has_flow(self, a, b):
        return self.input.has_flow(a, b)

    def is_parent(self, a, b):
        return self.input.is_parent(a, b)

    def get_policy_parameter(self, name):
        return self.policy_parameters.get(name)

    def has_policy_parameter(self, name):
        return name in self.policy_parameters

    def get_input(self) -> Input:
        return self.input


class RuleSet:
    rules: list[Rule]
    symbol_table: SymbolTable

    def __init__(
        self, rules, symbol_table: SymbolTable, verbose=False, cached=True, function_cache=None
    ):
        self.rules = rules
        self.cached = cached
        self.function_cache = function_cache or FunctionCache()
        self.verbose = verbose
        self.symbol_table = symbol_table or SymbolTable()

    def instance(self, cache: Optional[FunctionCache] = None):
        """
        Returns a new RuleSet instance that is a copy of the current one, but with a new function cache.

        This is useful for creating a new instance of the RuleSet with a different base cache to read and write to.
        """
        return RuleSet(
            self.rules,
            symbol_table=self.symbol_table,
            verbose=self.verbose,
            cached=True,
            function_cache=cache or self.function_cache,
        )

    # on deallocation, clear function cache explicitly
    def __del__(self):
        self.function_cache.clear()

    async def acall_function(self, func: Callable[P, Awaitable[R]] | Callable[P, R], *args: P.args, **kwargs: P.kwargs) -> R:
        return await self.function_cache.acall(func, *args, **kwargs)

    def log_apply(self, rule, model):
        if not self.verbose:
            return

        print("Applying Rule")
        print("  Rule:", rule)
        # wrap and indent model
        model_str = textwrap.wrap(repr(model), width=120, subsequent_indent="         ")
        print("  Model:", "\n".join(model_str))

    async def apply(self, input_data: Input, policy_parameters):
        exceptions = []

        self.input = input_data
        # make sure to clear the function cache if we are not caching
        if not self.cached:
            self.function_cache.clear()

        for rule_idx, rule in enumerate(self.rules):
            evaluation_context = InputEvaluationContext(
                input_data, self, policy_parameters, symbol_table=self.symbol_table
            )

            r = rule.apply(input_data, evaluation_context=evaluation_context)

            result: RuleApplication = await r
            result.models = [m for m in result.models]
            for model in result.models:
                self.log_apply(rule, model)

            error: list[ErrorInformation] = await result.execute(evaluation_context, rule_idx)
            exceptions.extend(error)

        self.input = None
        return exceptions

    def __str__(self):
        return f"<RuleSet {len(self.rules)} rules>"

    def __repr__(self):
        return str(self)

    @classmethod
    def from_policy(
        cls, policy: ast.PolicyRoot, cached=False, symbol_table: Optional[SymbolTable] = None
    ):
        # make sure we have a symbol table (used to resolve function calls and imports)
        symbol_table = symbol_table or SymbolTable()

        rules = []
        global_scope = policy.scope
        global_variables = frozen_dict(link(global_scope, symbol_table=symbol_table))

        for element in policy.statements:
            if type(element) is ast.RaisePolicy:
                rules.append(Rule.from_raise_policy(element, global_variables))
            elif type(element) is ast.Import or type(element) is ast.Declaration:
                continue
            else:
                print("skipping element of type: ", type(element))

        return cls(rules, symbol_table=symbol_table, cached=cached)


class frozen_dict:
    def __init__(self, base_dict):
        self.base_dict = base_dict

    def __iter__(self):
        return iter(self.base_dict)

    def __len__(self):
        return len(self.base_dict)

    def keys(self):
        return self.base_dict.keys()

    def values(self):
        return self.base_dict.values()

    def items(self):
        return self.base_dict.items()

    def __getitem__(self, key):
        return self.base_dict[key]

    def __setitem__(self, key, value):
        assert False, "cannot modify frozen dictionary"

    def __repr__(self):
        return "frozen " + repr(self.base_dict)

    def __str__(self):
        return "frozen " + str(self.base_dict)
