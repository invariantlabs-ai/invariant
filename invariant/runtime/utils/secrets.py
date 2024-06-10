import re
from invariant.runtime.utils.base import BaseDetector, DetectorResult
from presidio_analyzer import Pattern, PatternRecognizer

# Patterns from https://github.com/Yelp/detect-secrets/tree/master/detect_secrets/plugins
# TODO: For now, we run everything with re.IGNORECASE, ignoring the flags below
SECRETS_PATTERNS = {
    "GITHUB_TOKEN": [
        re.compile(r'(ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9_]{36}'),
    ],
    "AWS_ACCESS_KEY": [
        re.compile(r'(?:A3T[A-Z0-9]|ABIA|ACCA|AKIA|ASIA)[0-9A-Z]{16}'),
        re.compile(r'aws.{{0,20}}?{secret_keyword}.{{0,20}}?[\'\"]([0-9a-zA-Z/+]{{40}})[\'\"]'.format(
            secret_keyword=r'(?:key|pwd|pw|password|pass|token)',
        ), flags=re.IGNORECASE),
    ],
    "AZURE_STORAGE_KEY": [
        re.compile(r'AccountKey=[a-zA-Z0-9+\/=]{88}'),
    ],
    "SLACK_TOKEN": [
        re.compile(r'xox(?:a|b|p|o|s|r)-(?:\d+-)+[a-z0-9]+', flags=re.IGNORECASE),
        re.compile(r'https://hooks\.slack\.com/services/T[a-zA-Z0-9_]+/B[a-zA-Z0-9_]+/[a-zA-Z0-9_]+', flags=re.IGNORECASE | re.VERBOSE),
    ],
}


class SecretsAnalyzer(BaseDetector):
    """
    Analyzer for detecting secrets in generated text.
    """
    def __init__(self):
        super().__init__()

    def get_recognizers(self) -> list[PatternRecognizer]:
        self.secret_recognizers = []
        for secret, regex_pattern in SECRETS_PATTERNS.items():
            patterns = [
                Pattern(name=f"{secret}_{i}", regex=pat.pattern, score=0.5)
                for i, pat in enumerate(regex_pattern)
            ]
            self.secret_recognizers.append(PatternRecognizer(secret, patterns=patterns, global_regex_flags=re.IGNORECASE))
        return self.secret_recognizers
    
    def detect_all(self, text: str) -> list[DetectorResult]:
        recognizers = self.get_recognizers()
        pres_results = []
        for recognizer in recognizers:
            pres_results.extend(recognizer.analyze(text, entities=recognizer.supported_entities))
        res = [DetectorResult(pr.entity_type, pr.start, pr.end) for pr in pres_results]
        return res
