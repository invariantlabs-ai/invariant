import asyncio
import contextvars
import json
import re
import sys
from dataclasses import dataclass  # noqa: I001
from itertools import product
from typing import AsyncGenerator, Awaitable, Callable, ParamSpec, TypeVar

import termcolor

P = ParamSpec("P")
R = TypeVar("R")
from invariant.analyzer.language.ast import (
    ArrayLiteral,
    BinaryExpr,
    BooleanLiteral,
    CapturedVariableCollector,
    Declaration,
    Expression,
    FunctionCall,
    FunctionDefinition,
    FunctionSignature,
    Identifier,
    Import,
    ImportSpecifier,
    KeyAccess,
    ListComprehension,
    MemberAccess,
    Node,
    NoneLiteral,
    NumberLiteral,
    ObjectLiteral,
    ParameterDeclaration,
    PolicyError,
    PolicyRoot,
    Quantifier,
    RaisePolicy,
    RaisingAsyncTransformation,
    SemanticPattern,
    StringLiteral,
    TernaryOp,
    ToolReference,
    TypedIdentifier,
    UnaryExpr,
    VariableDeclaration,
)
from invariant.analyzer.language.scope import InputData, VariableDeclaration
from invariant.analyzer.runtime.evaluation_context import EvaluationContext, PolicyParameters
from invariant.analyzer.runtime.functions import CachedFunctionWrapper
from invariant.analyzer.runtime.input import Input, Range, Selectable
from invariant.analyzer.runtime.interface.primitives import DictValue, StringValue
from invariant.analyzer.runtime.nodes import Event
from invariant.analyzer.runtime.patterns import SemanticPatternMatcher
from invariant.analyzer.runtime.runtime_errors import MissingPolicyParameter
from invariant.analyzer.runtime.utils.invariant_attributes import (
    invariant_attr,
    is_safe_invariant_value,
)


class symbol:
    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return self.name

    def __str__(self):
        return self.name


# symbol to represent nop statements
NOP = symbol("<nop>")
# symbol to represent unknown values (e.g. if based on an unknown variable)
Unknown = symbol("<unknown>")


@dataclass
class VariableDomain:
    """
    The domain of a free or derived variable in the body of an IPL rule.

    Variable domains are sometimes only known after evaluation of the rule body.
    """

    type_ref: str
    values: list | None


def select(domain: VariableDomain, input_data: Input):
    """
    Returns all possible candidate values for a given variable domain.

    If the domain is open, i.e. ranges over the entire input data, all
    elements of the specified variable type are returned.
    """
    if domain.values is None:
        return input_data.select(domain.type_ref)
    else:
        return Selectable(domain.values).select(domain.type_ref)


def dict_product(dict_of_candidates):
    """Given a dictionary of variable names to lists of possible values,
    return a generator of all possible combination dictionaries."""
    keys = list(dict_of_candidates.keys())
    candidates = list(dict_of_candidates[key] for key in keys)
    for candidate in product(*candidates):
        yield {keys[i]: candidate[i] for i in range(len(keys))}


@dataclass
class EvaluationResult:
    """
    Represents a valid assignment of variables based on some input value
    such that a rule body evaluates to True.
    """

    result: bool
    variable_assignments: dict
    input_value: any
    ranges: list

    def result_key(self):
        """
        Returns a key for this result, given a rule index.

        This key can be used to recognize this rule match across different calls
        to the interpreter (e.g. to filter error duplicates in incremental analysis).

        The key is based on the variable assignments of the rule body, and is
        stable across runs of the interpreter.
        """
        model_keys = []

        for k, v in self.variable_assignments.items():
            if type(v) is dict and "key" in v:
                model_keys.append((k.name, v["key"]))
            else:
                idx = (
                    v.metadata["trace_idx"]
                    if isinstance(v, Event) and "trace_idx" in v.metadata
                    else -1
                )
                model_keys.append((k.name, idx))

        return tuple(vkey for k, vkey in sorted(model_keys, key=lambda x: x[0]))


INTERPRETER_STACK = contextvars.ContextVar("interpreter_stack", default=[])


class Interpreter(RaisingAsyncTransformation):
    """
    The Interpreter class is used to evaluate expressions based on
    a given variable store and global variables. It is used to evaluate
    the conditions of a policy rule, as well as the actions of a policy
    rule.

    Largely relies on Python's built-in evaluation mechanisms, but also
    provides some custom evaluation logic for special cases (e.g. flow
    semantics, containment checks, custom set operations).
    """

    @staticmethod
    def current() -> "Interpreter":
        stack = INTERPRETER_STACK.get()
        if len(stack) == 0:
            raise ValueError(
                "Cannot access Interpreter.current() outside of an interpretation context (call stack below Interpreter.eval)."
            )
        return stack[-1]

    @staticmethod
    async def eval(
        expr_or_list,
        variable_store,
        globals,
        evaluation_context=None,
        return_variable_domains=False,
        partial=True,
        assume_bool=False,
        return_ranges=False,
    ):
        """Evaluates the given expression(s).

        Args:
            expr_or_list: list of or single expression to evaluate.
            variable_store: The variable store to use for evaluation (dict).
            globals: The global variables to use for evaluation (dict).
            evaluation_context: The EvaluationContext to use for evaluation.
            return_variable_domains: If True, also returns any new variable domains derived during evaluation.
            partial: If True, returns Unknown if any part of the expression is unknown. If False, raises an exception when
                     an unknown variable is encountered.
            assume_bool: Specifies whether it is safe to assume the the list of expressions is a boolean expression. If True,
                         the evaluation will be short-circuited in order of the provided expressions.

        Returns:
            The result of the evaluation. If multiple expressions are given, a list of results is returned. For
            boolean evaluation, always evaluates all(expr_or_list) and returns True, False or Unknown.
        """
        with Interpreter(
            variable_store, globals, evaluation_context, partial=partial
        ) as interpreter:
            # make sure 'expr' is a list
            is_list_expr = isinstance(expr_or_list, list)
            if not is_list_expr:
                expr = [expr_or_list]
            else:
                expr = expr_or_list

            if assume_bool:
                # use short-circuit evaluation for boolean conjunctions
                # note: this is not just an optimization, but also prevents type errors, if only
                # a later condition fails (e.g. `type(a) is int and a + b > 2`), where checking the
                # second condition fail with a type error if `a` is not an integer.
                results = await interpreter.visit_ShortCircuitedConjunction(expr)
            else:
                # otherwise evaluate all expressions
                results = [await interpreter.visit(e) for e in expr]

            # evaluate all component expressions
            result = await Interpreter.eval_all(results)

            # for non-list expressions with list results, select the first result
            if type(result) is list:
                result = result[0] if not is_list_expr else result

            # construct return object
            return_obj = (result,)

            # if requested, also return new mappings
            if return_variable_domains:
                return_obj = (result, interpreter.variable_domains)

            # if requested, also return ranges
            if return_ranges:
                return_obj = return_obj + (interpreter.ranges,)

            if len(return_obj) == 1:
                return return_obj[0]
            else:
                return return_obj

    @staticmethod
    async def eval_all(list_of_results):
        """
        Like all(...) over a list of evaluation results, but also accounts for Unknown and NOP values.

        Args:
            list_of_results: The list of results to evaluate (as returned by .visit_* methods).
        """
        # remove nops
        results = [r for r in list_of_results if r is not NOP]
        # check if all results are boolean
        is_bool_result = all(type(r) is bool or r is Unknown for r in results)

        # simply return non-boolean results
        if not is_bool_result:
            return results
        else:
            # special handling for true|false|unknown value evaluation
            any_unknown_part = any(r is Unknown for r in results)
            any_false_part = any(r is False for r in results)

            if any_false_part:
                # definitive false
                result = False
            elif any_unknown_part:
                # unknown
                result = Unknown
            else:
                # definitive true
                result = True

            return result

    @staticmethod
    async def assignments(
        expr_or_list,
        input_data: Input,
        globals: dict,
        verbose=False,
        extra_check: callable = None,
        evaluation_context: EvaluationContext | None = None,
    ) -> AsyncGenerator[EvaluationResult, None]:
        """
        Iterator function over all possible variable assignments that either definitively satisfy or violate the given expression.

        The returned generator yields EvaluationResult objects, which contain the boolean evaluation result as 'result'.

        To obtain only models (assignments that satisfy the expression), use `[m for m in Interpreter.assignments(...) if m.result is True]`.

        Args:
            expr_or_list: The expression or list of expressions to evaluate.
            input_data: The input data to use for evaluation.
            globals: The global variables available during evaluation.
            verbose: If True, prints additional information about the evaluation process.

            extra_check: An optional function that is called for each candidate assignment. If the function returns False,
                         the model is further expanded (more mappings are determined) until a subsequent extra_check(...)
                         call returns True.

                         This is relevant when a partial assignment can already be determined to evaluate to True (based on logical
                         implications), but the client requires further variables to be picked to make the model complete.

            evaluation_context: The evaluation context to use for evaluation.
        """
        tasks = []
        results = asyncio.Queue()

        async def process(candidate_domains: dict):
            # for each domain, compute set of possible values
            candidate = {
                variable: select(domain, input_data)
                for variable, domain in candidate_domains.items()
            }

            # iterate over all cross products of all known variable domains
            async def process_input(input_dict):
                subdomains = {
                    k: VariableDomain(d.type_ref, values=[input_dict[k]])
                    for k, d in candidate_domains.items()
                }

                if verbose:
                    termcolor.cprint("=== Considering Model ===", "blue")
                    for k, v in input_dict.items():
                        print(
                            "  -",
                            k,
                            ":=",
                            id(v),
                            str(v)[:120] + ("" if len(str(v)) < 120 else "..."),
                        )
                    if len(input_dict) == 0:
                        print("  - <empty>")
                    print()

                # track number of rule body evaluations
                evaluation_context.evaluation_counter += 1

                result, new_variable_domains, ranges = await Interpreter.eval(
                    expr_or_list,
                    input_dict,
                    globals,
                    evaluation_context=evaluation_context,
                    return_variable_domains=True,
                    assume_bool=True,
                    return_ranges=True,
                )

                if verbose:
                    print("\n    result:", termcolor.colored(result, "green" if result else "red"))
                    print()

                if result is False:
                    model = EvaluationResult(result, input_dict, input_data, ranges)
                    # add all objects form input_dict as object ranges
                    for _, v in input_dict.items():
                        ranges.append(Range.from_object(v))
                    results.put_nowait(model)
                # if we find a complete model, we can stop
                elif result is True and (
                    extra_check is None or await extra_check(input_dict, evaluation_context)
                ):
                    model = EvaluationResult(result, input_dict, input_data, ranges)
                    # add all objects form input_dict as object ranges
                    for _, v in input_dict.items():
                        ranges.append(Range.from_object(v))
                    results.put_nowait(model)
                elif len(new_variable_domains) > 0:
                    # if more derived variable domains are found, we explore them
                    updated_domains = {**subdomains, **new_variable_domains}
                    tasks.append(asyncio.create_task(process(updated_domains)))

                    if verbose:
                        termcolor.cprint("discovered new variable domains", "green")
                        for k, v in updated_domains.items():
                            termcolor.cprint("  -" + str(k) + " in " + str(v), color="green")
                        print()

            # iterate over all cross products of all known variable domains
            for input_dict in dict_product(candidate):
                tasks.append(asyncio.create_task(process_input(input_dict)))

        # start with the input data as candidate
        initial = asyncio.create_task(process({}))
        tasks.append(initial)

        while len(tasks) > 0 or results.qsize() > 0:
            # check and re-raise for any exceptions
            for t in tasks:
                if t.done() and t.exception():
                    raise t.exception()

            # only keep tasks that are not done yet
            tasks = [t for t in tasks if not t.done()]
            # yield any new results
            if results.qsize() == 0:
                # if no tasks remain, we can stop
                if len(tasks) == 0:
                    break
                # wait for at least one more task to finish
                await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
            else:
                yield await results.get()
                results.task_done()

    def __init__(self, variable_store, globals, evaluation_context=None, partial=True):
        super().__init__(reraise=True)

        self.variable_store = variable_store
        self.globals = globals
        self.evaluation_context = evaluation_context or EvaluationContext()
        self.partial = partial

        self.ranges = []

        self.output_stream = sys.stdout

        # variable ranges describe the domain of all encountered
        # free variables. A domain of 'None' means the variable
        # quantifies over the global input domain (cf. Input objects).
        self.variable_domains = {}

        # parent interpreter
        self.parent = None

    def __enter__(self):
        if len(INTERPRETER_STACK.get()) > 0:
            self.parent = INTERPRETER_STACK.get()[-1]
        INTERPRETER_STACK.get().append(self)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        INTERPRETER_STACK.get().pop()

    async def evaluate_arrow_operator(self, node: BinaryExpr, operator: str):
        """
        Evaluates the arrow operator (-> or ~>) on two identifiers.

        Returns a tuple of the left and right values.
        """
        if not (isinstance(node.left, Identifier) and isinstance(node.right, Identifier)):
            raise ValueError(
                f"The '{operator}' operator can only be used with Identifier or TypedIdentifier."
            )

        # collect free variable, if not already specified
        if type(node.left) is TypedIdentifier:
            assert node.left.id is not None, "Encountered TypedIdentifier without id {}".format(
                node.left
            )
            self.register_variable_domain(node.left.id, VariableDomain(node.left.type_ref, None))
        if type(node.right) is TypedIdentifier:
            assert node.right.id is not None, "Encountered TypedIdentifier without id {}".format(
                node.right
            )
            self.register_variable_domain(node.right.id, VariableDomain(node.right.type_ref, None))

        lvalue = await self.visit_Identifier(node.left)
        rvalue = await self.visit_Identifier(node.right)

        return lvalue, rvalue

    async def visit_ShortCircuitedConjunction(self, exprs: list):
        results = []

        for e in exprs:
            result = await self.visit(e)
            if result is False:
                return results + [False]
            results.append(result)

        # # gather all sub results, and as soon as one is False, return False

        # TODO: this cannot be done yet, since sometimes the order of execution matters (with assignments and existential quantifiers over collections)
        # To enable this, we first need to build a dependency graph, and then only schedule tasks for nodes on the same level, so that evaluation/variable dependencies are not violated.

        # tasks = [asyncio.create_task(self.visit(e)) for e in exprs]
        # while len(tasks) > 0:
        #     done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        #     for t in done:
        #         tasks.remove(t)
        #         result = t.result()
        #         if result is False:
        #             return results + [False]
        #         results.append(result)

        return results

    async def visit_PolicyRoot(self, node: PolicyRoot):
        raise NotImplementedError("Policies cannot be evaluated directly.")

    async def visit_FunctionDefinition(self, node: FunctionDefinition):
        raise NotImplementedError("Function definitions cannot be evaluated directly.")

    async def visit_Declaration(self, node: Declaration):
        if node.is_constant:
            return await Interpreter.eval(node.value[0], {}, self.globals, self.evaluation_context)
        return node

    async def visit_RaisePolicy(self, node: RaisePolicy):
        raise NotImplementedError("RaisePolicy nodes cannot be evaluated directly.")

    async def visit_Quantifier(self, node: Quantifier):
        """
        Quantifiers are evaluated by their implemented quantifier functions.

        For this, they are provided with the body expression and the surrounding evaluation state (variable store, globals, input data).

        The actual quantifier semantics are implemented in the respective quantifier classes (stdlib).
        """
        quantifier = await self.visit(node.quantifier_call)
        if type(quantifier) is type:
            quantifier = quantifier()

        captured_variables = CapturedVariableCollector().collect(node.body)
        free_captured_variables = [
            v for v in captured_variables if v not in self.variable_store and v not in self.globals
        ]
        if len(free_captured_variables) > 0:
            return Unknown

        return await quantifier.eval(
            input_data=self.evaluation_context.get_input(),
            body=node.body,
            globals={**self.globals, **self.variable_store},
            evaluation_context=self.evaluation_context,
        )

    async def visit_BinaryExpr(self, node: BinaryExpr):
        op = node.op

        # special case: variabel binding
        if op == ":=":
            self.variable_store[node.left.id] = await self.visit(node.right)
            return NOP
        # special case: (var: type) in <set>
        elif op == "in" and type(node.left) is TypedIdentifier:
            # collect mappings for the quantified variable
            rvalue = await self.visit(node.right)
            if rvalue is not Unknown:
                assert (
                    type(node.left.id) is VariableDeclaration
                ), "Expected VariableDeclaration, got {}".format(node.left.id)
                self.register_variable_domain(
                    node.left.id, VariableDomain(node.left.type_ref, rvalue)
                )
            # in boolean semantics, this just evaluates to True
            return True
        # special case: arrow operator
        elif op == "->":
            lvalue, rvalue = await self.evaluate_arrow_operator(node, op)

            if lvalue is Unknown or rvalue is Unknown:
                return Unknown
            return self.evaluation_context.has_flow(lvalue, rvalue)
        elif op == "~>":
            lvalue, rvalue = await self.evaluate_arrow_operator(node, op)

            if lvalue is Unknown or rvalue is Unknown:
                return Unknown
            return self.evaluation_context.is_parent(lvalue, rvalue)

        # standard binary expressions
        else:
            lvalue = await self.visit(node.left)
            rvalue = await self.visit(node.right)

            if op == "and":
                # if any value of a conjunction is False, the whole conjunction is False
                # even if other parts are unknown
                if lvalue is False or rvalue is False:
                    # definitive false
                    return False
                # otherwise, if something is unknown, the whole conjunction is unknown
                if lvalue is Unknown or rvalue is Unknown:
                    # unknown
                    return Unknown

                return lvalue and rvalue
            elif op == "or":
                # if any value of a disjunction is True, the whole disjunction is True
                # even if other parts are unknown
                if lvalue is True or rvalue is True:
                    # definitive true
                    return True
                # otherwise, if something is unknown, the whole disjunction is unknown
                if lvalue is Unknown or rvalue is Unknown:
                    # unknown
                    return Unknown

                return lvalue or rvalue

            # expressions based on unknown values are unknown
            if lvalue is Unknown or rvalue is Unknown:
                return Unknown

            if op == "contains_only":
                return all(el in lvalue for el in rvalue)
            elif op == "+":
                return lvalue + rvalue
            elif op == "-":
                return lvalue - rvalue
            elif op == "*":
                return lvalue * rvalue
            elif op == "/":
                return lvalue / rvalue
            elif op == "%":
                return lvalue % rvalue
            elif op == "**":
                return lvalue**rvalue
            elif op == "==":
                return lvalue == rvalue
            elif op == "!=":
                return lvalue != rvalue
            elif op == ">":
                return lvalue > rvalue
            elif op == "<":
                return lvalue < rvalue
            elif op == ">=":
                return lvalue >= rvalue
            elif op == "<=":
                return lvalue <= rvalue
            elif op == "is":
                return await self.visit_Is(node, lvalue, rvalue)
            elif op == "in":
                # note: special case for (var: type) in <set> handled above

                # note: different from Python, we define '<value> in None' as 'False'
                if rvalue is None:
                    return False

                if isinstance(lvalue, list):
                    return [x in rvalue for x in lvalue]

                if type(rvalue) is str and type(lvalue) is str:
                    # find all ranges where left matches right
                    for m in re.finditer(lvalue, rvalue):
                        self.mark(rvalue, m.start(), m.end())
                    return lvalue in rvalue

                return lvalue in rvalue
            else:
                raise NotImplementedError(f"Unknown binary operator: {op}")

    def mark(self, obj: object, start: int | None = None, end: int | None = None):
        """
        Marks a relevant range or subobject in the input object as relevant
        for the currently evaluated expression (e.g. a string match or
        an entire object like a specific tool call).

        Args:
            obj: The object that the range refers to.
            start: The start index of the range (pass 'None' if you want to indicate an object-level range, i.e. an entire object in the input is considered relevant for the currently evaluated expression).
            end: The end index of the range (pass 'None' if you want to indicate an object-level range, i.e. an entire object in the input is considered relevant for the currently evaluated expression).
        """
        self.ranges.append(Range.from_object(obj, start, end))

        # also mark in parent
        if self.parent is not None:
            self.parent.mark(obj, start, end)

    async def visit_Is(self, node: BinaryExpr, left, right):
        if (
            type(node.right) is UnaryExpr
            and node.right.op == "not"
            and type(node.right.expr) is NoneLiteral
        ):
            return left is not None

        if type(right) is SemanticPattern or type(right) is ToolReference:
            matcher = SemanticPatternMatcher.from_semantic_pattern(right)
            return await matcher.match(left)
        else:
            return left is right

    async def visit_UnaryExpr(self, node: UnaryExpr):
        # not, -, +
        op = node.op
        opvalue = await self.visit(node.expr)

        # unknown -> unknown
        if opvalue is Unknown:
            return Unknown

        if op == "not":
            return not opvalue
        elif op == "-":
            return -opvalue
        elif op == "+":
            return +opvalue
        else:
            raise NotImplementedError(f"Unknown unary operator: {op}")

    async def visit_MemberAccess(self, node: MemberAccess):
        obj = await self.visit(node.expr)
        # member access on unknown values is unknown
        if obj is Unknown:
            return Unknown

        if type(obj) is PolicyParameters:
            if not obj.has_policy_parameter(node.member):
                raise MissingPolicyParameter(
                    f"'{node.member}' (policy relies on `input.{node.member}`), which is required for evaluation of a rule."
                )
            return obj.get(node.member)

        # check for special cases
        if type(obj) is str:
            try:
                # case 1: member access on stringified JSON objects
                obj = json.loads(obj)
                return obj[node.member]
            except json.JSONDecodeError:
                # case 2: member access on str instance (e.g. .split, .strip, etc.)
                return invariant_attr(StringValue(obj), node.member)
        # standard dict case
        elif type(obj) is dict:
            # case 3: member access on dictionaries (first resolved against dict keys, then against available dict methods)
            if node.member in obj.keys():
                return obj.get(node.member)
            else:
                # try to access the member as a method of the dict (e.g. .keys(), .values(), etc.)
                dict_value = DictValue(obj)
                try:
                    return invariant_attr(dict_value, node.member)
                except KeyError as e:
                    raise AttributeError(
                        f"object {obj} of type {type(obj)} does not support member access {node.member}"
                    ) from e
        # case 4: access via safe invariant object interface
        elif is_safe_invariant_value(obj):
            return invariant_attr(obj, node.member)
        elif self.evaluation_context.symbol_table.allows_module_interfacing():
            return getattr(obj, node.member)

        # case 4: member access on unsupported types
        raise TypeError(
            f"object {obj} of type {type(obj)} does not support member access (e.g. {node.member})"
        )

    async def visit_KeyAccess(self, node: KeyAccess):
        obj = await self.visit(node.expr)
        key = await self.visit(node.key)

        # if either the object or the key is unknown, the result is unknown
        if obj is Unknown or key is Unknown:
            return Unknown

        # check for index access
        if type(key) is int and hasattr(obj, "__getitem__"):
            # check for __getitem__ access on strings
            return obj.__getitem__(key)

        if not hasattr(obj, "keys"):
            raise TypeError(f"Object {obj} has no keys (type: {type(obj)})")

        if key not in obj.keys():
            raise KeyError(f"Object {obj} has no key {key} (type: {type(obj)})")

        try:
            return obj[key]
        except TypeError as e:
            # HACK: this handles cases where a subobject may still be represented
            # as a JSON string, which is not yet parsed. Ideally, this case should
            # already be handled before invoking the analyzer. In OpenAI message logs,
            # however, we may encounter this case in practice.
            if "string indices must be integers" in str(e):
                try:
                    obj = json.loads(obj)
                    return obj[key]
                except (json.JSONDecodeError, KeyError) as e:
                    raise KeyError(f"Object {obj} has no key {key}") from e
            raise KeyError(f"Object {obj} has no key {key}") from e

    def _is_unknown(self, value):
        if value is Unknown:
            return True
        elif isinstance(value, list):
            return any(self._is_unknown(item) for item in value)
        else:
            return False

    async def visit_FunctionCall(self, node: FunctionCall):
        function = await self.visit(node.name)
        args = await asyncio.gather(*[self.visit(arg) for arg in node.args])
        kwarg_items = await asyncio.gather(
            *[
                asyncio.gather(self.visit(entry.key), self.visit(entry.value))
                for entry in node.kwargs
            ]
        )
        kwargs = {k: v for k, v in kwarg_items}

        # only call functions, once all parameters are known
        if (
            function is Unknown
            or any(self._is_unknown(arg) for arg in args)
            or any(self._is_unknown(v) for v in kwargs.values())
        ):
            return Unknown

        if isinstance(function, Declaration):
            return await self.visit_PredicateCall(function, args, **kwargs)
        else:
            return await self.acall_function(function, *args, **kwargs)

    async def visit_TernaryOp(self, node: TernaryOp):
        condition = await self.visit(node.condition)

        # If condition is unknown, the result is unknown
        if condition is Unknown:
            return Unknown

        # Evaluate only the branch that will be executed
        if condition:
            return await self.visit(node.then_expr)
        else:
            return await self.visit(node.else_expr)

    async def visit_PredicateCall(self, node: Declaration, args, **kwargs):
        assert not node.is_constant, "Predicate call should not be constant."
        assert isinstance(
            node.name, FunctionSignature
        ), "predicate declaration did not have a function signature as name."
        signature: FunctionSignature = node.name

        parameters = {}
        for p in signature.params:
            parameters[p.name.id] = args.pop(0)
        parameters.update(kwargs)

        async for result in Interpreter.assignments(
            # recursively evaluate the predicate body
            node.value,
            self.evaluation_context.get_input(),
            # re-use globals, and assign parameter bindings
            {**self.globals, **parameters},
            # same evaluation context
            evaluation_context=self.evaluation_context,
        ):
            # if the predicate is satisfied, we can stop
            if result.result is True:
                return result.result

        return False

    async def visit_FunctionSignature(self, node: FunctionSignature):
        raise NotImplementedError("Function signatures cannot be evaluated directly.")

    async def visit_ParameterDeclaration(self, node: ParameterDeclaration):
        raise NotImplementedError("Parameter declarations cannot be evaluated directly.")

    async def visit_StringLiteral(self, node: StringLiteral):
        return node.value

    async def visit_Expression(self, node: Expression):
        raise NotImplementedError("Expressions cannot be evaluated directly.")

    async def visit_NumberLiteral(self, node: NumberLiteral):
        return node.value

    async def visit_Identifier(self, node: Identifier):
        if node.id is None:
            raise PolicyError("'{}' (id: {}) must have an id".format(node, id(node)))

        if node.id in self.variable_store:
            result = self.variable_store[node.id]
        elif node.id in self.globals:
            result = self.globals[node.id]
        else:
            if not self.partial:
                raise ValueError(
                    f"Failed to resolve variable {node.name}, no binding found for {node.id}"
                )
            # if a variable is unknown, we return the Unknown object
            return Unknown

        if isinstance(result, Node):
            result = await Interpreter.eval(result, {}, self.globals, self.evaluation_context)

        # when `input` is resolved to the built-in `InputData` symbol, use
        # `PolicyParameters` to resolve policy parameters (e.g. values passed
        # to the analyze(...) function)
        if result is InputData:
            return PolicyParameters(self.evaluation_context)

        return result

    async def visit_TypedIdentifier(self, node: TypedIdentifier):
        # # collect free variable, if not already specified
        self.register_variable_domain(node.id, VariableDomain(node.type_ref, None))
        # typed identifiers always evaluate to True
        return True

    def register_variable_domain(self, decl: VariableDeclaration, domain):
        assert (
            type(decl) is VariableDeclaration
        ), "Can only register new variable domains for some VariableDeclaration, not for {}".format(
            decl
        )
        if decl not in self.variable_store and decl not in self.globals:
            self.variable_domains[decl] = domain

    async def visit_ToolReference(self, node: ToolReference):
        return node

    async def visit_SemanticPattern(self, node: SemanticPattern):
        return node

    async def visit_Import(self, node: Import):
        return NOP

    async def visit_ImportSpecifier(self, node: ImportSpecifier):
        return NOP

    async def visit_NoneLiteral(self, node: NoneLiteral):
        return None

    async def visit_BooleanLiteral(self, node: BooleanLiteral):
        return node.value

    async def visit_ObjectLiteral(self, node: ObjectLiteral):
        return {
            await self.visit(entry.key): await self.visit(entry.value) for entry in node.entries
        }

    async def visit_ArrayLiteral(self, node: ArrayLiteral):
        return [await self.visit(entry) for entry in node.elements]

    async def visit_ListComprehension(self, node: ListComprehension):
        iterable = await self.visit(node.iterable)

        if iterable is None:
            return []

        if iterable is Unknown:
            return Unknown

        var_name = node.var_name.id if hasattr(node.var_name, "id") else node.var_name
        results = []
        original_vars = self.variable_store.copy()
        for item in iterable:
            self.variable_store[var_name] = item

            if node.condition:
                condition_result = await self.visit(node.condition)
                if condition_result is Unknown:
                    results.append(Unknown)
                    continue
                elif condition_result is not True:
                    continue

            result = await self.visit(node.expr)
            results.append(result)

        # Restore original variable store
        self.variable_store = original_vars
        return results

    async def acall_function(
        self,
        function: Callable[P, Awaitable[R]] | Callable[P, R] | CachedFunctionWrapper,
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> R:
        ctx: EvaluationContext = self.evaluation_context
        # if function is a cached function wrapper, unwrap it (at this point we
        # are already caching it)
        func = function.func if isinstance(function, CachedFunctionWrapper) else function
        linked_function = ctx.link(func, None)
        # also unwrap linked function, if a cached function wrapper
        linked_function = (
            linked_function.func
            if isinstance(linked_function, CachedFunctionWrapper)
            else linked_function
        )
        return await ctx.acall_function(linked_function, *args, **kwargs)
