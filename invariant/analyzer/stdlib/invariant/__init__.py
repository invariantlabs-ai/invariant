from invariant.analyzer.stdlib.invariant.nodes import *
from invariant.analyzer.stdlib.invariant.errors import *
from invariant.analyzer.stdlib.invariant.message import *
from invariant.analyzer.stdlib.invariant.quantifiers import *

def match(pattern: str, s: str) -> bool:
    import re
    return re.match(pattern, s) is not None