import re
from re import Pattern
from pydantic.dataclasses import dataclass
from invariant.analyzer.runtime.utils.base import BaseDetector, DetectorResult

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

@dataclass
class SecretPattern:
    secret_name: str
    patterns: list[Pattern]


class SecretsAnalyzer(BaseDetector):
    """
    Analyzer for detecting secrets in generated text.
    """
    def __init__(self):
        super().__init__()
        self.secrets = self.get_recognizers()

    def get_recognizers(self) -> list[Pattern]:
        secrets = []
        for secret_name, regex_pattern in SECRETS_PATTERNS.items():
            secrets.append(SecretPattern(secret_name, regex_pattern))
        return secrets
    
    def detect_all(self, text: str) -> list[DetectorResult]:
        res = []
        for secret in self.secrets:
            for pattern in secret.patterns:
                for match in pattern.finditer(text):
                    res.append(DetectorResult(secret.secret_name, match.start(), match.end()))
        return res
