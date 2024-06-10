from invariant.stdlib.invariant.nodes import *
from invariant.stdlib.invariant.errors import *
from invariant.stdlib.invariant.message import *

def match(pattern: str, s: str) -> bool:
    import re
    return re.match(pattern, s) is not None