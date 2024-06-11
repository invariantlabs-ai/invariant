from invariant.runtime.utils.base import BaseDetector
from invariant.extras import presidio_extra

class PII_Analyzer(BaseDetector):
    
    def __init__(self):
        AnalyzerEngine = presidio_extra.package("presidio_analyzer").import_names('AnalyzerEngine')
        self.analyzer = AnalyzerEngine()

    def detect_all(self, text: str) -> list[str]:
        results = self.analyzer.analyze(text, language='en')
        res_matches = set()
        for res in results:
            res_matches.add(res.entity_type)
        return list(res_matches)