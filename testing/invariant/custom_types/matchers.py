"""Defines the expect functions."""

from enum import StrEnum
from typing import Any

from invariant.scorers.llm.classifier import Classifier
from invariant.scorers.strings import embedding_similarity, levenshtein


class Matcher:
    """Base class for all matchers."""

    def matches(self, actual_value: Any) -> bool:
        """This is the method that subclasses should implement."""
        raise NotImplementedError("Subclasses should implement this method.")


class LambdaMatcher(Matcher):
    """Matcher for checking if a lambda function returns True."""

    def __init__(self, lambda_function):
        self.lambda_function = lambda_function

    def matches(self, actual_value: Any) -> bool:
        """Check if the lambda function returns True for actual_value."""
        return self.lambda_function(actual_value)

    def __str__(self):
        return f"LambdaMatcher({self.lambda_function})"

    def __repr__(self):
        return str(self)


class HasSubstring(Matcher):
    """Matcher for checking if a string contains a substring."""

    def __init__(self, substring: str):
        self.substring = substring

    def matches(self, actual_value: Any) -> bool:
        if not isinstance(actual_value, str):
            raise TypeError("HasSubstring matcher only works with strings.")
        return self.substring in actual_value

    def __str__(self):
        return f"HasSubstring({self.substring})"

    def __repr__(self):
        return str(self)


class IsSimilar(Matcher):
    """A Matcher for checking if a string is similar to an expected string by checking if the similary score reaches a given threshold."""

    LEVENSHTEIN = "levenshtein"
    EMBEDDING = "embedding"

    metric_to_scorer_mapping = {
        LEVENSHTEIN: levenshtein,
        EMBEDDING: embedding_similarity,
    }

    def __init__(
        self,
        expected_value: str,
        threshold: float,
        actual_metric: str = LEVENSHTEIN,
    ):
        self.expected_value = expected_value
        self.threshold = threshold
        self.actual_metric = actual_metric

    def matches(self, actual_value: str):
        if not isinstance(actual_value, str):
            raise TypeError("CompareSimilarity matcher only works with strings")
        if self.actual_metric not in self.metric_to_scorer_mapping:
            raise ValueError(f"Unsupported metric {self.actual_metric}")

        similar_score = self.metric_to_scorer_mapping[self.actual_metric](
            actual_value, self.expected_value
        )
        return similar_score >= self.threshold


class IsFactuallyEqual(Matcher):
    """Matcher for checking if the output is close to expected using llm"""

    class Agreement(StrEnum):
        SUPER_STRICT_AGGREMENT = "super strict aggrement"
        STRICT_AGGREMENT = "strict aggrement"
        FUZZY_AGGREMENT = "fuzzy aggrement"

    levels_to_score_mapping = {
        Agreement.FUZZY_AGGREMENT: 1,
        Agreement.STRICT_AGGREMENT: 2,
        Agreement.SUPER_STRICT_AGGREMENT: 3,
    }

    def __init__(
        self,
        expected_value: str,
        question: str,
        level: Agreement = Agreement.STRICT_AGGREMENT,
    ):
        assert (
            level in self.levels_to_score_mapping.keys()
        ), f"Invalid scoring level {level}. Must be one of {self.levels_to_score_mapping.keys()}"

        self.expected_value = expected_value
        self.question = question
        self.level = level

    def matches(
        self,
        actual_value: Any,
        model: str = "gpt-4o",
        client: str = "OpenAI",
    ) -> bool:
        if not isinstance(actual_value, str):
            raise TypeError("is factually equivalent matcher only works with strings")
        prompt = """You are comparing a submitted answer to an expert answer on a given question.
                    Compare the factual content of the submitted answer with the expert answer. Ignore any differences in style, grammar, or punctuation.
                    The submitted answer may either be a subset or superset of the expert answer, or it may conflict with it. Determine which case applies. Answer the question by selecting one of the following options:
                    (0) There is a disagreement between the submitted answer and the expert answer.
                    (1) The submitted answer is a subset of the expert answer and is fully consistent with it.
                    (2) The submitted answer is a superset of the expert answer and is fully consistent with it.
                    (3) The answers differ, but these differences don't matter from the perspective of factuality.
                    (4) The submitted answer contains all the same details as the expert answer.
                 """
        text = f"""Here is the data:
                    [Question]: {self.question},
                    [Expert]: {self.expected_value},
                    [Submission]: {actual_value},
                """
        llm_clf = Classifier(
            model=model,
            prompt=prompt,
            options=["0", "1", "2", "3", "4"],
            client=client,
        )
        res_score = llm_clf.classify(text=text)
        print(f"result: {res_score}")

        try:
            res_score_number = int(res_score)
        except ValueError:
            raise ValueError(f"llm returned invalid result {res_score}")

        return res_score_number >= self.levels_to_score_mapping[self.level]


class ContainsImage(Matcher):
    """
    Matcher for checking if string is an image or dict contains image.

    Checks if the string starts with "local_base64_img: " or "local_img_link: ".
    Checks if dict has a content field, and if that content field starts with "local_base64_img: " or "local_img_link: ".
    """

    def matches(self, actual_value: str | dict) -> bool:
        """
        Args:
            actual_value: str | dict - The value to check if it is an image.

        Returns:
            bool: True if the value is an image, False otherwise.
        """
        if not isinstance(actual_value, dict) and not isinstance(actual_value, str):
            raise TypeError(
                "ContainsImage matcher only works with dictionaries and strings."
            )
        if isinstance(actual_value, dict):
            if "content" not in actual_value:
                return False
            actual_value = actual_value["content"]
        return actual_value.startswith("local_base64_img: ") or actual_value.startswith(
            "local_img_link: "
        )
