from invariant.analyzer.runtime.utils.base import BaseDetector, DetectorResult
from invariant.analyzer.runtime.utils.copyright.software_licenses import *

# TODO: Maybe want to use more sophisticated approach like https://github.com/licensee/licensee at some point

SOFTWARE_LICENSES = {
    "GNU_AGPL_V3": GNU_AGPL_V3,
    "GNU_GPL_V2": GNU_GPL_V2,
    "GNU_LGPL_V3": GNU_LGPL_V3,
    "MOZILLA_PUBLIC_LICENSE_2.0": MOZILLA_PUBLIC_LICENSE_2_0,
    "APACHE_LICENSE_2.0": APACHE_LICENSE_2_0,
    "MIT_LICENSE": MIT_LICENSE,
    "BOOST_SOFTWARE_LICENSE": BOOST_SOFTWARE_LICENSE,
}

COPYRIGHT_PATTERNS = [
    "Copyright (C)",
    "Copyright ©",
]

class CopyrightAnalyzer(BaseDetector):

    def detect_software_licenses(self, text: str, threshold: int = 0.5) -> list[DetectorResult]:
        # First check if text starts with the license string
        for license_name, license_text in SOFTWARE_LICENSES.items():
            if text.strip().startswith(license_text.strip()):
                return [DetectorResult(license_name, 0, len(license_text))]
        
        # Next, use heuristics that checks how many tokens of the license text are in the given text
        res = []
        text_tokens = set(text.strip().split(" "))
        for license_name, license_text in SOFTWARE_LICENSES.items():
            tokens = list(filter(lambda x: len(x) > 0, license_text.strip().split(" ")))
            in_text = [token in text_tokens for token in tokens]
            in_ratio = sum(in_text) / float(len(tokens))
            if in_ratio >= threshold:
                res += [DetectorResult(license_name, 0, len(license_text))]
        return res
    
    def detect_copyright_patterns(self, text: str, threshold: int = 0.5) -> list[DetectorResult]:
        res = []
        for pattern in COPYRIGHT_PATTERNS:
            pos = text.find(pattern)
            if pos != -1:
                res += [DetectorResult("COPYRIGHT", pos, pos+len(pattern))]
        return res

    def detect_all(self, text: str, threshold: int = 0.5) -> list[DetectorResult]:
        res = []
        res.extend(self.detect_software_licenses(text, threshold))
        res.extend(self.detect_copyright_patterns(text, threshold))
        return res

