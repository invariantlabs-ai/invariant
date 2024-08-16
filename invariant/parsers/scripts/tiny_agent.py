import json
from invariant.traces import *

with open("../agent_datasets/TinyAgent-dataset/training_data.json", "r") as fin:
    data = json.load(fin)

class ID_Manager:

    def __init__(self):
        self.curr_id = 0
    
    def next(self) -> str:
        self.curr_id += 1
        return str(self.curr_id)
    
    def last(self) -> str:
        return str(self.curr_id)

id = ID_Manager()

traces = []
for key in data:
    key = list(data.keys())[0]
    input = data[key]["input"]
    output = data[key]["output"]

    plan, join = output[0], output[1]

    trace = []
    trace.append(user(input))
    for idx, event in enumerate(plan["parsed_output"]):
        args = {f"arg_{i}": arg for i, arg in enumerate(event["tool_args"])}
        trace.append(tool_call(id.next(), event["tool_name"], args))
        trace.append(tool(id.last(), f"{idx}"))
    traces.append(trace)

from invariant.policy import Policy

policy = Policy.from_string("""
raise "error" if:
    (out: ToolCall) -> (out2: ToolCall)
    out is tool:create_note
    out2 is tool:send_sms
""")

for trace in traces:
    res = policy.analyze(trace)

metadata = {"metadata": {"description": "Traces collected from TinyAgent dataset"}}
for trace in traces:
    for i in range(len(trace)):
        if "function" in trace[i]:
            trace[i] = {
                "role": "assistant",
                "content": "",
                "tool_calls": [trace[i]],
            }
with open(f"agent-datasets/tiny_agent.json", "w") as fou:
    for trace in traces:
        print(json.dumps(trace), file=fou)
