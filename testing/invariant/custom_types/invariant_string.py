"""Describes an invariant string in a test."""

from __future__ import annotations

import json
import re
from operator import ge, gt, le, lt, ne
from typing import Any, Literal, Union

from _pytest.python_api import ApproxBase

from invariant.custom_types.invariant_bool import InvariantBool
from invariant.custom_types.invariant_number import InvariantNumber
from invariant.custom_types.invariant_value import InvariantValue
from invariant.scorers.code import execute, is_valid_json, is_valid_python
from invariant.scorers.llm.classifier import Classifier
from invariant.scorers.llm.detector import Detector
from invariant.scorers.moderation import ModerationAnalyzer
from invariant.scorers.strings import embedding_similarity, levenshtein


class InvariantString(InvariantValue):
    """Describes an invariant string in a test."""

    def __init__(self, value: str, addresses: list[str] = None):
        if not isinstance(value, str):
            raise TypeError(f"value must be a str, got {type(value)}")
        if addresses is None:
            addresses = []
        if isinstance(addresses, str):
            addresses = [addresses]
        super().__init__(value, addresses)

    def _compare(self, other: Union[str, "InvariantString"], operator) -> InvariantBool:
        """Helper function to compare with another string."""
        if isinstance(other, InvariantString):
            other = other.value
        cmp_result = operator(self.value, other)
        return InvariantBool(cmp_result, self.addresses)

    def __eq__(self, other: Union[str, "InvariantString"]) -> InvariantBool:
        """Check if the string is equal to the given string."""
        if isinstance(other, InvariantString):
            other = other.value
        if isinstance(other, ApproxBase):
            return self.value == other
        return InvariantBool(self.value == other, self.addresses)

    def __ne__(self, other: Union[str, "InvariantString"]) -> InvariantBool:
        """Check if the string is not equal to the given string."""
        return self._compare(other, ne)

    def __gt__(self, other: Union[str, "InvariantString"]) -> InvariantBool:
        """Check if the string is greater than the given string."""
        return self._compare(other, gt)

    def __lt__(self, other: Union[str, "InvariantString"]) -> InvariantBool:
        """Check if the string is less than the given string."""
        return self._compare(other, lt)

    def __ge__(self, other: Union[str, "InvariantString"]) -> InvariantBool:
        """Check if the string is greater than or equal to the given string."""
        return self._compare(other, ge)

    def __le__(self, other: Union[str, "InvariantString"]) -> InvariantBool:
        """Check if the string is less than or equal to the given string."""
        return self._compare(other, le)

    def __add__(self, other: Union[str, "InvariantString"]) -> "InvariantString":
        """Concatenate the string with another string."""
        if isinstance(other, InvariantString):
            return InvariantString(self.value + other.value, self.addresses + other.addresses)
        return InvariantString(self.value + other, self.addresses)

    def __radd__(self, other: str) -> "InvariantString":
        """Concatenate another string with this string (reverse operation)."""
        return InvariantString(other + self.value, self.addresses)

    def __str__(self) -> str:
        return f"InvariantString(value={self.value}, addresses={self.addresses})"

    def __repr__(self) -> str:
        return str(self)

    def __len__(self):
        raise NotImplementedError(
            "InvariantString does not support len(). Please use functionals.len() instead."
        )

    def __getitem__(self, key: Any, default: Any = None) -> "InvariantString":
        """Get a substring using integer, slice or string."""
        if isinstance(key, int):
            range = f"{key}-{key+1}"
            return InvariantString(self.value[key], self._concat_addresses([range]))
        elif isinstance(key, str):
            valid_json = self.is_valid_code("json")
            if not valid_json:
                return default
            json_dict = json.loads(self.value)
            # TODO: We can find more precise address here
            return InvariantString(json_dict[key], self.addresses)
        elif isinstance(key, slice):
            start = key.start if key.start is not None else 0
            stop = key.stop if key.stop is not None else len(self.value)
            range = f"{start}-{stop}"
            return InvariantString(self.value[key], self._concat_addresses([range]))
        raise TypeError("InvariantString indices must be integer, slices or strings")

    def count(self, pattern: str) -> InvariantNumber:
        """Counts the number of occurences of the given regex pattern."""
        new_addresses = []
        for match in re.finditer(pattern, self.value, re.DOTALL):
            start, end = match.span()
            new_addresses.append(f"{start}-{end}")
        return InvariantNumber(
            len(new_addresses),
            (self.addresses if len(new_addresses) == 0 else self._concat_addresses(new_addresses)),
        )

    def len(self):
        """Return the length of the string."""
        return InvariantNumber(len(self.value), self.addresses)

    def __getattr__(self, attr):
        """Delegate attribute access to the underlying string.

        Args:
            attr (str): The attribute being accessed.

        Returns:
            Any: Uses InvariantValue.of to return the result.
                 If the result is a string, then an InvariantString is returned with that
                 the result string as the value. If the result is a number, then an InvariantNumber.
        """
        if hasattr(self.value, attr):
            method = getattr(self.value, attr)

            # If the method is callable, wrap it to return an InvariantValue where appropriate
            if callable(method):

                def wrapper(*args, **kwargs):
                    result = method(*args, **kwargs)
                    return InvariantValue.of(result, self.addresses)

                return wrapper
            return method
        raise AttributeError(f"'InvariantString' object has no attribute '{attr}'")

    def _concat_addresses(self, other_addresses: list[str] | None, separator: str = ":") -> list[str]:
        """Concatenate the addresses of two invariant values."""
        if other_addresses is None:
            return self.addresses
        addresses = []
        for old_address in self.addresses:
            # Check if old_address ends with :start-end pattern
            match = re.match(r"^(.*):(\d+)-(\d+)$", old_address)
            assert match is not None
            prefix, start, _ = (
                match.groups()[0],
                int(match.groups()[1]),
                int(match.groups()[2]),
            )
            for new_address in other_addresses:
                new_match = re.match(r"^(\d+)-(\d+)$", new_address)
                assert new_match is not None
                new_start, new_end = (
                    start + int(new_match.groups()[0]),
                    start + int(new_match.groups()[1]),
                )
                addresses.append(prefix + separator + f"{new_start}-{new_end}")
        return addresses

    def moderation(self) -> InvariantBool:
        """Check if the value is moderated."""
        analyzer = ModerationAnalyzer()
        res = analyzer.detect_all(self.value)
        new_addresses = [str(range) for _, range in res]
        return InvariantBool(len(res) > 0, self._concat_addresses(new_addresses))

    def contains(
        self,
        *patterns: Union[str, InvariantString],
        criterion: Literal["all", "any"] = "all",
        flags=re.IGNORECASE,
    ) -> InvariantBool:
        """Check if the value contains all of the given patterns.

        Args:
            *patterns: Variable number of patterns to check for. Each pattern can be a string
                      or InvariantString.
            criterion: The criterion to use for the contains check - can be "all" or "any".
            flags: The flags to use for the regex search. To pass in multiple flags, use the bitwise OR operator (|). By default, this is re.IGNORECASE.

        Returns:
            InvariantBool: True if all patterns are found, False otherwise. The addresses will
                          contain the locations of all pattern matches if found.
        """
        if criterion not in ["all", "any"]:
            raise ValueError("Criterion must be either 'all' or 'any'")
        new_addresses = []
        for pattern in patterns:
            if isinstance(pattern, InvariantString):
                pattern = pattern.value

            pattern_matches = []
            for match in re.finditer(pattern, self.value, flags=flags):
                start, end = match.span()
                pattern_matches.append(f"{start}-{end}")

            if criterion == "all" and not pattern_matches:
                return InvariantBool(False, self.addresses)
            if criterion == "any" and pattern_matches:
                return InvariantBool(True, self._concat_addresses(pattern_matches))
            new_addresses.extend(pattern_matches)

        return InvariantBool(criterion == "all", self._concat_addresses(new_addresses))

    def contains_all(self, *patterns: Union[str, InvariantString]) -> InvariantBool:
        """Check if the value contains all of the given patterns."""
        return self.contains(*patterns, criterion="all")

    def contains_any(self, *patterns: Union[str, InvariantString]) -> InvariantBool:
        """Check if the value contains any of the given patterns."""
        return self.contains(*patterns, criterion="any")

    def __contains__(self, pattern: str | InvariantString) -> InvariantBool:
        """Check if the value contains the given pattern."""
        return self.contains(pattern)

    def match(self, pattern: str, group_id: int | str = 0) -> InvariantString:
        """Match the value against the given regex pattern and return the matched group."""
        match = re.search(pattern, self.value)
        if match is None:
            return None
        start, end = match.span(group_id)
        return InvariantString(match.group(group_id), self._concat_addresses([f"{start}-{end}"]))

    def match_all(self, pattern: str, group_id: int | str = 0):
        """Match the value against the given regex pattern and return all matches."""
        for match in re.finditer(pattern, self.value):
            start, end = match.span(group_id)
            yield InvariantString(match.group(group_id), self._concat_addresses([f"{start}-{end}"]))

    def is_similar(self, other: str, threshold: float = 0.5) -> InvariantBool:
        """Check if the value is similar to the given string using cosine similarity."""
        if not isinstance(other, str):
            raise ValueError("is_similar() is only supported for string values")
        cmp_result = embedding_similarity(self.value, other) >= threshold
        return InvariantBool(cmp_result, self.addresses)

    def levenshtein(self, other: str) -> InvariantNumber:
        """Check if the value is similar to the given string using the Levenshtein distance."""
        if not isinstance(other, str):
            raise ValueError("levenshtein() is only supported for string values")
        cmp_result = levenshtein(self.value, other)
        return InvariantNumber(cmp_result, self.addresses)

    def is_valid_code(self, lang: str) -> InvariantBool:
        """Check if the value is valid code in the given language."""
        if lang == "python":
            res, new_addresses = is_valid_python(self.value)
            return InvariantBool(res, self._concat_addresses(new_addresses))
        if lang == "json":
            res, new_addresses = is_valid_json(self.value)
            return InvariantBool(res, self._concat_addresses(new_addresses))
        raise ValueError(f"Unsupported language: {lang}")

    def llm(
        self,
        prompt: str,
        options: list[str],
        model: str = "gpt-4o",
        use_cached_result: bool = True,
        client: str = "OpenAI",
    ) -> InvariantString:
        """Check if the value is similar to the given string using an LLM.

        Args:
            prompt (str): The prompt to use for the LLM.
            options (list[str]): The options to use for the LLM.
            model (str): The model to use for the LLM.
            use_cached_result (bool): Whether to use a cached result if available.
            client (invariant.scorers.llm.clients.client.SupportedClients): The
            client to use for the LLM.
        """
        llm_clf = Classifier(model=model, prompt=prompt, options=options, client=client)
        res = llm_clf.classify(self.value, use_cached_result)
        return InvariantString(res, self.addresses)

    def extract(
        self,
        predicate: str,
        model: str = "gpt-4o",
        use_cached_result: bool = True,
        client: str = "OpenAI",
    ) -> list[InvariantString]:
        """Extract values from the underlying string using an LLM.

        Args:
            predicate (str): The predicate to use for extraction. This is a rule
            that the LLM uses to extract values. For example with a predicate
            "cities in Switzerland", the LLM would extract all cities in
            Switzerland from the text.
            model (str): The model to use for extraction.
            use_cached_result (bool): Whether to use a cached result if available.
            client (invariant.scorers.llm.clients.client.SupportedClients): The
            client to use for the LLM.
        """
        llm_detector = Detector(model=model, predicate_rule=predicate, client=client)
        detections = llm_detector.detect(self.value, use_cached_result)
        ret = []
        for substr, r in detections:
            ret.append(InvariantString(substr, self._concat_addresses([str(r)])))
        return ret

    def execute_contains(
        self, pattern: str, suffix_code: str = "", detect_packages: bool = False
    ) -> InvariantString:
        """Execute the value as Python code and return the standard output as InvariantString.

        Args:
            pattern (str): The pattern to check for in the output.
            suffix_code (str): The Python code to append to the value before execution.
            detect_packages (bool): Whether to detect the dependencies of the code.
        """
        res = execute(self.value + "\n" + suffix_code, detect_packages)
        has_pattern = re.search(pattern, res) is not None
        return InvariantBool(has_pattern, self.addresses)
