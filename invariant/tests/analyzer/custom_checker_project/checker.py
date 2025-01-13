from invariant.analyzer.stdlib.invariant.nodes import Message

def contains_hello(msg: Message) -> bool:
    return "hello" in msg.content