from invariant.analyzer.extras import presidio_extra
from invariant.analyzer.runtime.utils.base import BaseDetector


class PII_Analyzer(BaseDetector):
    def __init__(self, threshold=0.5):
        AnalyzerEngine = presidio_extra.package("presidio_analyzer").import_names("AnalyzerEngine")
        self.analyzer = AnalyzerEngine()
        self.threshold = threshold

    def detect_all(self, text: str, entities: list[str] | None = None):
        results = self.analyzer.analyze(text, language="en", entities=entities)
        res_matches = set()
        for res in results:
            if res.score > self.threshold:
                res_matches.add(res)
        return list(res_matches)

    async def adetect(self, text: str, entities: list[str] | None = None):
        return self.detect_all(text, entities)
