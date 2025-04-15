from invariant.analyzer.runtime.input import Input


class Quantifier:
    """
    A quantifier is a way to quantify sub-expressions in the Invariant language over the entire input object.

    Generally, it allows users to define custom trace-level evaluation modes that can be used to check e.g. whether a given
    expression holds for e.g. all elements in a trace, or at least for one element in a trace.

    See invariant/stdlib/invariant/quantifiers.py for different quantifier implementations.
    """

    def eval(self, input_data: Input, body, globals: dict, evaluation_context: "EvaluationContext"):
        raise NotImplementedError
