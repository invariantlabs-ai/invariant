import os
import requests
from invariant.runtime.utils.base import BaseDetector
from invariant.extras import presidio_extra

PRESIDIO_URL = os.environ.get("PRESIDIO_URL", None)

AnalyzerEngine = presidio_extra.package("presidio_analyzer").import_names('AnalyzerEngine')
RecognizerResult = presidio_extra.package("presidio_analyzer").import_names('RecognizerResult')

class PII_Analyzer(BaseDetector):

    def __init__(self, threshold=0.5):
        self.analyzer = AnalyzerEngine() if PRESIDIO_URL is None else None
        self.threshold = threshold

    def analyze(self, text: str, **kwargs) -> list[RecognizerResult]:
        results = None
        if PRESIDIO_URL:
            response = requests.post(f"{PRESIDIO_URL}/analyze", json={"text": text, **kwargs})
            results = [RecognizerResult.from_json(r) for r in response.json()]
        else:
            results = self.analyzer.analyze(text, **kwargs)
        return results

    def detect_all(self, text: str, entities: list[str] | None = None):
        results = self.analyze(text, language='en', entities=entities)
        res_matches = set()
        for res in results:
            if res.score > self.threshold:
                res_matches.add(res)
        return list(res_matches)