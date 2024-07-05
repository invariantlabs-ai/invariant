from invariant.language.ast import *
from invariant.runtime.patterns import SemanticPatternMatcher
from invariant.language.scope import InputData
from dataclasses import dataclass
import json
import re
import contextvars

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

class EvaluationContext:
    """
    An evaluation context enables a caller to handle the
    evaluation of external functions explicitly (e.g. for caching)
    and provide their own flow semantics (e.g. lookup in a graph).
    """
    def call_function(self, function, args, **kwargs):
        return function(*args, **kwargs)
    
    def has_flow(self, left, right):
        return False
    
    def get_policy_parameter(self, name):
        return None

    def has_policy_parameter(self, name):
        return False
    
class PolicyParameters:
    """
    Returned when accessing `input` in the IPL, which provides access
    to policy parameters passed to the `.analyze(..., **kwargs)` function.
    """
    def __init__(self, context):
        self.context: EvaluationContext = context

    def get(self, key):
        return self.context.get_policy_parameter(key)
    
    def has_policy_parameter(self, key):
        return self.context.has_policy_parameter(key)

@dataclass
class VariableDomain:
    """
    The domain of a free or derived variable in the body
    of an IPL rule.
    """
    type_ref: str
    values: list

@dataclass
class Range:
    """
    Represents a range in the input object that is relevant for 
    the currently evaluated expression.

    A range can be an entire object (start and end are None) or a
    substring (start and end are integers, and object_id refers to
    the object that the range is part of).
    """
    object_id: str
    start: int|None
    end: int|None

    @classmethod
    def from_object(cls, obj, start=None, end=None):
        if type(obj) is dict and "__origin__" in obj:
            obj = obj["__origin__"]
        return cls(str(id(obj)), start, end)
    
    def match(self, obj):
        return str(id(obj)) == self.object_id

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
            raise ValueError("Cannot access Interpreter.current() outside of an interpretation context (call stack below Interpreter.eval).")
        return stack[-1]

    @staticmethod
    def eval(expr_or_list, variable_store, globals, evaluation_context=None, return_variable_domains=False, partial=True, assume_bool=False, return_ranges=False):
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
        with Interpreter(variable_store, globals, evaluation_context, partial=partial) as interpreter:    
            # make sure 'expr' is a list
            is_list_expr = isinstance(expr_or_list, list)
            if not is_list_expr: expr = [expr_or_list]
            else: expr = expr_or_list
            
            if assume_bool:
                # use short-circuit evaluation for boolean conjunctions
                # note: this is not just an optimization, but also prevents type errors, if only
                # a later condition fails (e.g. `type(a) is int and a + b > 2`), where checking the 
                # second condition fail with a type error if `a` is not an integer.
                results = interpreter.visit_ShortCircuitedConjunction(expr)
            else:
                # otherwise evaluate all expressions
                results = [interpreter.visit(e) for e in expr]
            # remove nops
            results = [r for r in results if r is not NOP]
            
            is_bool_result = all(type(r) is bool or r is Unknown for r in results)

            # simply return non-boolean results
            if not is_bool_result:
                result = results[0] if not is_list_expr else results
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
                assert type(node.left.id) is VariableDeclaration, "Expected VariableDeclaration, got {}".format(node.left.id)
                self.register_variable_domain(node.left.id, VariableDomain(node.left.type_ref, rvalue))
            # in boolean semantics, this just evaluates to True
            return True
        # special case: arrow operator
        elif op == "->":
            if not (isinstance(node.left, Identifier) and isinstance(node.right, Identifier)):
                raise ValueError("The '->' operator can only be used with Identifier or TypedIdentifier.")
            
            # # collect free variable, if not already specified
            if type(node.left) is TypedIdentifier:
                assert node.left.id is not None, "Encountered TypedIdentifier without id {}".format(node.left)
                self.register_variable_domain(node.left.id, VariableDomain(node.left.type_ref, None))
            if type(node.right) is TypedIdentifier:
                assert node.right.id is not None, "Encountered TypedIdentifier without id {}".format(node.right)
                self.register_variable_domain(node.right.id, VariableDomain(node.right.type_ref, None))

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
                return lvalue ** rvalue
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

    def mark(self, obj: object, start: int|None = None, end: int|None = None):
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
        if type(node.right) is UnaryExpr and node.right.op == "not" and type(node.right.expr) is NoneLiteral:
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
        if opvalue is Unknown: return Unknown

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
        if obj is Unknown: return Unknown

        if type(obj) is PolicyParameters:
            if not obj.has_policy_parameter(node.member):
                raise KeyError(f"Missing policy parameter '{node.member}' (policy relies on `input.{node.member}`), which is required for evaluation of a rule.")
            return obj.get(node.member)

        if hasattr(obj, node.member):
            return getattr(obj, node.member)
        elif type(obj) is dict:
            try:
                return obj[node.member]
            except KeyError:
                raise KeyError(f"Could not find key '{node.member}' in {obj}")
        else:
            raise KeyError(f"Cound not find member '{node.member}' in {obj}")

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
        assert isinstance(node.name, FunctionSignature), "predicate declaration did not have a function signature as name."
        signature: FunctionSignature = node.name

        parameters = {}
        for p in signature.params:
            parameters[p.name.id] = args.pop(0)
        parameters.update(kwargs)
        return all(Interpreter.eval(condition, parameters, self.globals, self.evaluation_context) for condition in node.value)

    def visit_FunctionSignature(self, node: FunctionSignature):
        raise NotImplementedError("Function signatures cannot be evaluated directly.")

    def visit_ParameterDeclaration(self, node: ParameterDeclaration):
        raise NotImplementedError(
            "Parameter declarations cannot be evaluated directly."
        )

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
                raise ValueError(f"Failed to resolve variable {node.name}, no binding found for {node.id}")
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
        assert type(decl) is VariableDeclaration, "Can only register new variable domains for some VariableDeclaration, not for {}".format(decl)
        if not decl in self.variable_store and not decl in self.globals:
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