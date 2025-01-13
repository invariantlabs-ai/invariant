from dataclasses import dataclass  # noqa: I001
import json
import re
import contextvars
from itertools import product
from typing import Generator

from invariant.analyzer.language.ast import *
from invariant.analyzer.runtime.patterns import SemanticPatternMatcher
from invariant.analyzer.runtime.input import Input, Selectable, Range
from invariant.analyzer.language.scope import InputData
from invariant.analyzer.runtime.evaluation_context import EvaluationContext, PolicyParameters


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


INTERPRETER_STACK = contextvars.ContextVar("interpreter_stack", default=[])


class Interpreter(RaisingTransformation):
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
    def current():
        stack = INTERPRETER_STACK.get()
        if len(stack) == 0:
            raise ValueError(
                "Cannot access Interpreter.current() outside of an interpretation context (call stack below Interpreter.eval)."
            )
        return stack[-1]

    @staticmethod
    def eval(
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
                results = interpreter.visit_ShortCircuitedConjunction(expr)
            else:
                # otherwise evaluate all expressions
                results = [interpreter.visit(e) for e in expr]

            # evaluate all component expressions
            result = Interpreter.eval_all(results)

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
    def eval_all(list_of_results):
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
    def assignments(
        expr_or_list,
        input_data: Input,
        globals: dict,
        verbose=False,
        extra_check: callable = None,
        evaluation_context: EvaluationContext | None = None,
    ) -> Generator[EvaluationResult, None, None]:
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
        candidates = [{}]

        while len(candidates) > 0:
            # for each variable, select a domain
            candidate_domains = candidates.pop()
            # for each domain, compute set of possible values
            candidate = {
                variable: select(domain, input_data)
                for variable, domain in candidate_domains.items()
            }
            # iterate over all cross products of all known variable domains
            for input_dict in dict_product(candidate):
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

                result, new_variable_domains, ranges = Interpreter.eval(
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
                    for k, v in input_dict.items():
                        ranges.append(Range.from_object(v))
                    yield model
                    continue
                # if we find a complete model, we can stop
                elif result is True and (
                    extra_check is None or extra_check(input_dict, evaluation_context)
                ):
                    model = EvaluationResult(result, input_dict, input_data, ranges)
                    # add all objects form input_dict as object ranges
                    for k, v in input_dict.items():
                        ranges.append(Range.from_object(v))
                    yield model
                    continue
                elif len(new_variable_domains) > 0:
                    # if more derived variable domains are found, we explore them
                    updated_domains = {**subdomains, **new_variable_domains}
                    candidates.append(updated_domains)

                    if verbose:
                        termcolor.cprint("discovered new variable domains", "green")
                        for k, v in updated_domains.items():
                            termcolor.cprint("  -" + str(k) + " in " + str(v), color="green")
                        print()

    def __init__(self, variable_store, globals, evaluation_context=None, partial=True):
        super().__init__(reraise=True)

        self.variable_store = variable_store
        self.globals = globals
        self.evaluation_context = evaluation_context or EvaluationContext()
        self.partial = partial

        self.ranges = []

        # variable ranges describe the domain of all encountered
        # free variables. A domain of 'None' means the variable
        # quantifies over the global input domain (cf. Input objects).
        self.variable_domains = {}

    def __enter__(self):
        INTERPRETER_STACK.get().append(self)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        INTERPRETER_STACK.get().pop()

    def visit_ShortCircuitedConjunction(self, exprs: list):
        results = []
        for e in exprs:
            result = self.visit(e)
            if result is False:
                return results + [False]
            results.append(result)
        return results

    def visit_PolicyRoot(self, node: PolicyRoot):
        raise NotImplementedError("Policies cannot be evaluated directly.")

    def visit_FunctionDefinition(self, node: FunctionDefinition):
        raise NotImplementedError("Function definitions cannot be evaluated directly.")

    def visit_Declaration(self, node: Declaration):
        if node.is_constant:
            return Interpreter.eval(node.value[0], {}, self.globals, self.evaluation_context)
        return node

    def visit_RaisePolicy(self, node: RaisePolicy):
        raise NotImplementedError("RaisePolicy nodes cannot be evaluated directly.")

    def visit_Quantifier(self, node: Quantifier):
        """
        Quantifiers are evaluated by their implemented quantifier functions.

        For this, they are provided with the body expression and the surrounding evaluation state (variable store, globals, input data).

        The actual quantifier semantics are implemented in the respective quantifier classes (stdlib).
        """
        quantifier = self.visit(node.quantifier_call)
        if type(quantifier) is type:
            quantifier = quantifier()

        captured_variables = CapturedVariableCollector().collect(node.body)
        free_captured_variables = [
            v for v in captured_variables if v not in self.variable_store and v not in self.globals
        ]
        if len(free_captured_variables) > 0:
            return Unknown

        return quantifier.eval(
            input_data=self.evaluation_context.get_input(),
            body=node.body,
            globals={**self.globals, **self.variable_store},
            evaluation_context=self.evaluation_context,
        )

    def visit_BinaryExpr(self, node: BinaryExpr):
        op = node.op

        # special case: variabel binding
        if op == ":=":
            self.variable_store[node.left.id] = self.visit(node.right)
            return NOP
        # special case: (var: type) in <set>
        elif op == "in" and type(node.left) is TypedIdentifier:
            # collect mappings for the quantified variable
            rvalue = self.visit(node.right)
            if rvalue is not Unknown:
                assert type(node.left.id) is VariableDeclaration, (
                    "Expected VariableDeclaration, got {}".format(node.left.id)
                )
                self.register_variable_domain(
                    node.left.id, VariableDomain(node.left.type_ref, rvalue)
                )
            # in boolean semantics, this just evaluates to True
            return True
        # special case: arrow operator
        elif op == "->":
            if not (isinstance(node.left, Identifier) and isinstance(node.right, Identifier)):
                raise ValueError(
                    "The '->' operator can only be used with Identifier or TypedIdentifier."
                )

            # # collect free variable, if not already specified
            if type(node.left) is TypedIdentifier:
                assert node.left.id is not None, "Encountered TypedIdentifier without id {}".format(
                    node.left
                )
                self.register_variable_domain(
                    node.left.id, VariableDomain(node.left.type_ref, None)
                )
            if type(node.right) is TypedIdentifier:
                assert node.right.id is not None, (
                    "Encountered TypedIdentifier without id {}".format(node.right)
                )
                self.register_variable_domain(
                    node.right.id, VariableDomain(node.right.type_ref, None)
                )

            lvalue = self.visit_Identifier(node.left)
            rvalue = self.visit_Identifier(node.right)

            if lvalue is Unknown or rvalue is Unknown:
                return Unknown
            return self.evaluation_context.has_flow(lvalue, rvalue)
        # standard binary expressions
        else:
            lvalue = self.visit(node.left)
            rvalue = self.visit(node.right)

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
                return self.visit_Is(node, lvalue, rvalue)
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

    def visit_Is(self, node: BinaryExpr, left, right):
        if (
            type(node.right) is UnaryExpr
            and node.right.op == "not"
            and type(node.right.expr) is NoneLiteral
        ):
            return left is not None

        if type(right) is SemanticPattern or type(right) is ToolReference:
            matcher = SemanticPatternMatcher.from_semantic_pattern(right)
            return matcher.match(left)
        else:
            return left is right

    def visit_UnaryExpr(self, node: UnaryExpr):
        # not, -, +
        op = node.op
        opvalue = self.visit(node.expr)

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

    def visit_MemberAccess(self, node: MemberAccess):
        obj = self.visit(node.expr)
        # member access on unknown values is unknown
        if obj is Unknown:
            return Unknown

        if type(obj) is PolicyParameters:
            if not obj.has_policy_parameter(node.member):
                raise KeyError(
                    f"Missing policy parameter '{node.member}' (policy relies on `input.{node.member}`), which is required for evaluation of a rule."
                )
            return obj.get(node.member)

        if hasattr(obj, node.member):
            return getattr(obj, node.member)

        try:
            if type(obj) is str:
                obj = json.loads(obj)
            return obj[node.member]
        except Exception:
            raise KeyError(f"Object {obj} has no key {node.member}")

    def visit_KeyAccess(self, node: KeyAccess):
        obj = self.visit(node.expr)
        key = self.visit(node.key)

        # if either the object or the key is unknown, the result is unknown
        if obj is Unknown or key is Unknown:
            return Unknown
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
                except (json.JSONDecodeError, KeyError):
                    raise KeyError(f"Object {obj} has no key {key}")
            raise KeyError(f"Object {obj} has no key {key}")

    def visit_FunctionCall(self, node: FunctionCall):
        function = self.visit(node.name)
        args = [self.visit(arg) for arg in node.args]

        # only call functions, once all parameters are known
        if function is Unknown or any(arg is Unknown for arg in args):
            return Unknown
        kwargs = {entry.key: self.visit(entry.value) for entry in node.kwargs}

        if isinstance(function, Declaration):
            return self.visit_PredicateCall(function, args, **kwargs)
        else:
            return self.evaluation_context.call_function(function, args, **kwargs)

    def visit_PredicateCall(self, node: Declaration, args, **kwargs):
        assert not node.is_constant, "Predicate call should not be constant."
        assert isinstance(node.name, FunctionSignature), (
            "predicate declaration did not have a function signature as name."
        )
        signature: FunctionSignature = node.name

        parameters = {}
        for p in signature.params:
            parameters[p.name.id] = args.pop(0)
        parameters.update(kwargs)
        return all(
            Interpreter.eval(condition, parameters, self.globals, self.evaluation_context)
            for condition in node.value
        )

    def visit_FunctionSignature(self, node: FunctionSignature):
        raise NotImplementedError("Function signatures cannot be evaluated directly.")

    def visit_ParameterDeclaration(self, node: ParameterDeclaration):
        raise NotImplementedError("Parameter declarations cannot be evaluated directly.")

    def visit_StringLiteral(self, node: StringLiteral):
        return node.value

    def visit_Expression(self, node: Expression):
        raise NotImplementedError("Expressions cannot be evaluated directly.")

    def visit_NumberLiteral(self, node: NumberLiteral):
        return node.value

    def visit_Identifier(self, node: Identifier):
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
            result = Interpreter.eval(result, {}, self.globals, self.evaluation_context)

        # when `input` is resolved to the built-in `InputData` symbol, use
        # `PolicyParameters` to resolve policy parameters (e.g. values passed
        # to the analyze(...) function)
        if result is InputData:
            return PolicyParameters(self.evaluation_context)

        return result

    def visit_TypedIdentifier(self, node: TypedIdentifier):
        # # collect free variable, if not already specified
        self.register_variable_domain(node.id, VariableDomain(node.type_ref, None))
        # typed identifiers always evaluate to True
        return True

    def register_variable_domain(self, decl: VariableDeclaration, domain):
        assert type(decl) is VariableDeclaration, (
            "Can only register new variable domains for some VariableDeclaration, not for {}".format(
                decl
            )
        )
        if decl not in self.variable_store and decl not in self.globals:
            self.variable_domains[decl] = domain

    def visit_ToolReference(self, node: ToolReference):
        return node

    def visit_SemanticPattern(self, node: SemanticPattern):
        return node

    def visit_Import(self, node: Import):
        return NOP

    def visit_ImportSpecifier(self, node: ImportSpecifier):
        return NOP

    def visit_NoneLiteral(self, node: NoneLiteral):
        return None

    def visit_BooleanLiteral(self, node: BooleanLiteral):
        return node.value

    def visit_ObjectLiteral(self, node: ObjectLiteral):
        return {self.visit(entry.key): self.visit(entry.value) for entry in node.entries}

    def visit_ArrayLiteral(self, node: ArrayLiteral):
        return [self.visit(entry) for entry in node.elements]
