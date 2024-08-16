import json
import re
from datasets import load_dataset
from invariant.policy import Policy
from invariant.traces import *

ds = load_dataset("THUDM/AgentInstruct")

class ID_Manager:

    def __init__(self):
        self.curr_id = 0
    
    def next(self):
        self.curr_id += 1
        return str(self.curr_id)
    
    def last(self):
        return str(self.curr_id)
    
def parse_trace(msgs: list[dict]):
    id = ID_Manager()
    events = []
    for event_idx, msg in enumerate(msgs):
        role, content = msg["from"], msg["value"]
        if role == "gpt":
            if "Act:" in content:
                func = re.search(r'Act: (.+)($|\n)', content).group(1)
                if func.startswith("bash"):
                    bash_cmd = re.search(r'```bash\n(.+)\n```', content, re.DOTALL).group(1)
                    events.append(tool_call(id.next(), "bash", {"cmd": bash_cmd}))
                elif func.startswith("answer"):
                    ans = re.search(r'answer\((.+)\)', func).group(1)
                    events.append(tool_call(id.next(), "answer", {"answer": ans}))
                elif func.startswith("finish"):
                    events.append(tool_call(id.next(), "finish", {}))
                else:
                    raise ValueError("")
            elif "Action:" in content:
                func = re.search(r'Action:\n*(.+)($|\n)', content).group(1).strip()
                if func.startswith("Operation"):
                    sql_cmd = re.search(r'```sql\n(.+)\n```', content, re.DOTALL).group(1)
                    events.append(tool_call(id.next(), "Operation", {"sql_cmd": sql_cmd}))
                elif func.startswith("Answer"):
                    ans = re.search(r'Final Answer: (.+)', content).group(1)
                    events.append(tool_call(id.next(), "Final Answer", {"answer": ans}))
                else:
                    match = re.search(r'([a-zA-Z_]+)\((.+)\)', func)
                    if match is None:
                        match = re.search(r'([a-zA-Z_]+)\[(.+)\]', func)
                    if match is None:
                        match = re.search(r'([a-zA-Z_]+)()', func)
                    func_name = match.group(1)
                    func_args = match.group(2).split(", ")
                    func_args = {f"arg_{i}": arg for i, arg in enumerate(func_args)}
                    events.append(tool_call(id.next(), func_name, func_args))
            elif "ACTION:" in content:
                func = re.search(r'ACTION: ([A-Za-z]+)', content)
                if func is None:
                    func_name = "finish"
                    func_args = [re.search(r'ACTION: (.+)', content).group(1)]
                else:
                    func_name = func.group(1)
                    func_args = re.search(r'ACTION: (.+)', content).group(1)
                func_args = {f"arg_{i}": arg for i, arg in enumerate(func_args)}
                events.append(tool_call(id.next(), func_name, func_args))
            elif "Final Answer:" in content:
                match = re.search(r'Final Answer: (.+)', content)
                func_name = "Final Answer"
                ans = match.group(1)
                events.append(tool_call(id.next(), func_name, {"answer": ans}))
            else:
                events.append(assistant(content))
        else:
            if event_idx == 0:
                events.append(user(content))
            else:
                events.append(tool(id.last(), content))
    return events


policy = Policy.from_string("""
raise "error" if:
    (out: ToolCall) -> (out2: ToolCall)
    out is tool:create_note
    out2 is tool:send_sms
""")

subsets = ["os", "db", "alfworld", "webshop", "kg"]

traces = {}
for sub in subsets:
    traces[sub] = []
    for msgs in ds[sub]:
        trace = parse_trace(msgs["conversations"])
        traces[sub].append(trace)
        res = policy.analyze(trace)

for sub in subsets:
    metadata = {"metadata": {"description": f"Traces collected from AgentInstruct subset: {sub}"}}
    for trace in traces[sub]:
        for i in range(len(trace)):
            if "function" in trace[i]:
                trace[i] = {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [trace[i]],
                }
    with open(f"agent-datasets/agent_instruct_{sub}.json", "w") as fou:
        for trace in traces[sub]:
            print(json.dumps(trace), file=fou)




