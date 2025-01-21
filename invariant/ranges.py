from invariant.analyzer import Policy
from invariant.analyzer.traces import *  # for message trace helpers

policy = Policy.from_string(
    """
# make sure the agent never leaks the user's email via search_web
raise PolicyViolation("User's email address was leaked", call=call) if:
    (call: ToolCall)
    call is tool:search_web({
        q: <EMAIL_ADDRESS>
    })

# web results should not contain 'France'
raise PolicyViolation("A web result contains 'France'", call=result) if:
    (result: ToolOutput)
    result is tool:search_web
    "France" in result.content
"""
)

# given some message trace (user(...), etc. helpers let you create them quickly)
messages = [
    system("You are a helpful assistant. Your user is signed in as bob@mail.com"),
    user("Please do some research on Paris."),
    assistant(None, tool_call("1", "search_web", {"q": "bob@mail.com want's to know about Paris"})),
    tool("1", "Paris is the capital of France."),
]

error = policy.analyze(messages).errors[1]
# PolicyViolation(A web result contains 'France', call=...)
error.ranges
# [
#   Range(object_id='4323252960', start=None, end=None, json_path='3'),
#   Range(object_id='4299976464', start=24, end=30, json_path='3.content:24-30')
# ]
# -> the error is caused by 3rd message (tool call), and the relevant range is in the content at offset 24-30
