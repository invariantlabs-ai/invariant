from invariant.runtime.utils.base import BaseDetector

class PII_Analyzer(BaseDetector):
    
    def __init__(self):
        from presidio_analyzer import AnalyzerEngine
        self.analyzer = AnalyzerEngine()

    def detect_all(self, text: str) -> list[str]:
        results = self.analyzer.analyze(text, language='en')
        res_matches = set()
        for res in results:
            res_matches.add(res.entity_type)
        return list(res_matches)