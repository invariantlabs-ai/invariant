import os
import textwrap

import invariant.analyzer.language.ast as ast
from invariant.analyzer.language.linking import link
from invariant.analyzer.runtime.evaluation import (
    EvaluationContext,
    EvaluationResult,
    Interpreter,
    Unknown,
)
from invariant.analyzer.runtime.input import Input
from invariant.analyzer.stdlib.invariant.errors import ErrorInformation
from invariant.analyzer.stdlib.invariant.nodes import Event


class PolicyAction:
    def __call__(self, input_dict):
        raise NotImplementedError()


class RaiseAction(PolicyAction):
    def __init__(self, exception_or_constructor, globals):
        self.exception_or_constructor = exception_or_constructor
        self.globals = globals

    def can_eval(self, input_dict, evaluation_context):
        res = Interpreter.eval(
            self.exception_or_constructor,
            input_dict,
            self.globals,
            partial=True,
            evaluation_context=evaluation_context,
        )
        return res is not Unknown

    def __call__(self, model: EvaluationResult, evaluation_context=None):
        from invariant.analyzer.stdlib.invariant.errors import PolicyViolation

        if type(self.exception_or_constructor) is ast.StringLiteral:
            return PolicyViolation(self.exception_or_constructor.value, ranges=model.ranges)
        elif isinstance(self.exception_or_constructor, ast.Expression):
            exception = Interpreter.eval(
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

    def __init__(self, rule, models):
        self.rule = rule
        self.models: list[EvaluationResult] = models

    def applies(self):
        return len(self.models) > 0

    def execute(self, evaluation_context):
        errors = []
        for model in self.models:
            exc = self.rule.action(model, evaluation_context)
            if exc is not None:
                errors.append((model, exc))
        return errors


class Rule:
    def __init__(
        self,
        action: PolicyAction,
        condition: list[ast.Expression],
        globals: dict,
        repr: str = None,
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

    def action_can_eval(self, input_dict: dict, ctx: EvaluationContext):
        """Returns true iff self.action can be evaluated with the given input_dict and context (all relevant variables have already been assigned)."""
        return self.action.can_eval(input_dict, ctx)

    def apply(self, input_data: Input, evaluation_context=None) -> RuleApplication:
        models = [
            m
            for m in Interpreter.assignments(
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


class FunctionCache:
    def __init__(self):
        self.cache = {}

    def clear(self):
        self.cache = {}

    def arg_key(self, arg):
        # cache primitives by value
        if type(arg) is int or type(arg) is float or type(arg) is str:
            return arg
        # cache lists by id
        elif type(arg) is list:
            return tuple(self.arg_key(a) for a in arg)
        # cache dictionaries by id
        elif type(arg) is dict:
            return tuple((k, self.arg_key(v)) for k, v in sorted(arg.items(), key=lambda x: x[0]))
        # cache all other objects by id
        return id(arg)

    def call_key(self, function, args, kwargs):
        id_args = (self.arg_key(arg) for arg in args)
        id_kwargs = ((self.arg_key(k), self.arg_key(v)) for k, v in kwargs.items())
        return (id(function), *id_args, *id_kwargs)

    def contains(self, function, args, kwargs):
        return self.call_key(function, args, kwargs) in self.cache

    def call(self, function, args, **kwargs):
        # if function is not marked with @cache we just call it directly (see ./functions.py module)
        if not hasattr(function, "__invariant_cache__"):
            return function(*args, **kwargs)
        if not self.contains(function, args, kwargs):
            self.cache[self.call_key(function, args, kwargs)] = function(*args, **kwargs)
        return self.cache[self.call_key(function, args, kwargs)]


class InputEvaluationContext(EvaluationContext):
    def __init__(self, input, rule_set, policy_parameters):
        self.input = input
        self.rule_set = rule_set
        self.policy_parameters = policy_parameters

    def call_function(self, function, args, **kwargs):
        return self.rule_set.call_function(function, args, **kwargs)

    def has_flow(self, a, b):
        return self.input.has_flow(a, b)

    def get_policy_parameter(self, name):
        return self.policy_parameters.get(name)

    def has_policy_parameter(self, name):
        return name in self.policy_parameters

    def get_input(self) -> Input:
        return self.input


class RuleSet:
    rules: list[Rule]

    def __init__(self, rules, verbose=False, cached=True):
        self.rules = rules
        self.executed_rules = set()
        self.cached = cached
        self.function_cache = FunctionCache()
        self.verbose = verbose

    def call_function(self, function, args, **kwargs):
        return self.function_cache.call(function, args, **kwargs)

    def non_executed(self, rule, model):
        if not self.cached:
            return True
        return self.instance_key(rule, model) not in self.executed_rules

    def instance_key(self, rule, model):
        model_keys = []

        for k, v in model.variable_assignments.items():
            if type(v) is dict and "key" in v:
                model_keys.append((k.name, v["key"]))
            else:
                idx = (
                    v.metadata["trace_idx"]
                    if isinstance(v, Event) and "trace_idx" in v.metadata
                    else -1
                )
                model_keys.append((k.name, idx))
        return (id(rule), *(vkey for k, vkey in sorted(model_keys, key=lambda x: x[0])))

    def log_apply(self, rule, model):
        if not self.verbose:
            return

        print("Applying Rule")
        print("  Rule:", rule)
        # wrap and indent model
        model_str = textwrap.wrap(repr(model), width=120, subsequent_indent="         ")
        print("  Model:", "\n".join(model_str))

    def apply(self, input_data: Input, policy_parameters):
        exceptions = []

        self.input = input_data
        # make sure to clear the function cache if we are not caching
        if not self.cached:
            self.function_cache.clear()

        for rule in self.rules:
            evaluation_context = InputEvaluationContext(input_data, self, policy_parameters)

            result: RuleApplication = rule.apply(input_data, evaluation_context=evaluation_context)
            result.models = [m for m in result.models if self.non_executed(rule, m)]
            for model in result.models:
                if self.cached:
                    self.executed_rules.add(self.instance_key(rule, model))
                self.log_apply(rule, model)
            exceptions.extend(result.execute(evaluation_context))

        self.input = None
        return exceptions

    def __str__(self):
        return f"<RuleSet {len(self.rules)} rules>"

    def __repr__(self):
        return str(self)

    @classmethod
    def from_policy(cls, policy: ast.PolicyRoot, cached=False):
        rules = []
        global_scope = policy.scope
        global_variables = frozen_dict(link(global_scope))

        for element in policy.statements:
            if type(element) is ast.RaisePolicy:
                rules.append(Rule.from_raise_policy(element, global_variables))
            elif type(element) is ast.Import or type(element) is ast.Declaration:
                continue
            else:
                print("skipping element of type: ", type(element))

        return cls(rules, cached=cached)


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
