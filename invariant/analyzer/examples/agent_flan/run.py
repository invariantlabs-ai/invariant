"""
Demonstrates how to analyze a the Agent-FLAN dataset using the Invariant
Agent Analyer to detect security vulnerabilities in the execution of bash commands.
"""

import json
import re

# Data taken from https://huggingface.co/datasets/internlm/Agent-FLAN/tree/main/data

input_file = "data/data_agent_instruct_react.jsonl"
# input_file = "data/data_agent_instruct_tflan.jsonl"

# input_file = "data/toolbench_tflan_cot_30p.jsonl"
# input_file = "data/data_toolbench_negative.jsonl"
# input_file = "data/toolbench_instruct_j1s1_3k.jsonl"

with open(input_file, "r") as fin:
    input_data = [json.loads(line) for line in fin]

print(len(input_data))


def has_bash(conv):
    return any(
        [msg["role"] == "assistant" and "```bash" in msg["content"] for msg in conv["conversation"]]
    )


for conv_idx, conv in enumerate(input_data):
    if not has_bash(conv):
        continue

    tool_called, tool_call_id = False, 0
    ipl_messages = []

    for msg in conv["conversation"]:
        if msg["role"] == "system":
            ipl_messages.append({"role": "system", "content": msg["content"]})
        elif msg["role"] == "user":
            if tool_called:
                tool_call_id += 1
                ipl_messages.append(
                    {"role": "tool", "tool_call_id": str(tool_call_id), "content": msg["content"]}
                )
            else:
                ipl_messages.append({"role": "user", "content": msg["content"]})
        elif msg["role"] == "assistant":
            tool_called = False
            if "Act: answer" in msg["content"] or "Act: finish" in msg["content"]:
                pass
            else:
                tool_called = True
                match = re.search(r"```bash\n(.+?)\n```", msg["content"], re.DOTALL)
                bash_cmd = match.group(1) if match else None
                # print("-> ", bash_cmd)
                ipl_messages += [
                    {
                        "id": str(tool_call_id),
                        "type": "function",
                        "function": {"name": "bash", "arguments": {"cmd": bash_cmd}},
                    }
                ]
        else:
            assert False

    from invariant.analyzer import Policy

    policy = Policy.from_string(
        r"""
    raise "find not allowed" if:
        (call: ToolCall)
        call.function.name == "bash"
        "exec" in call.function.arguments.cmd
    """
    )
    analysis_result = policy.analyze(ipl_messages)

    print("trace: \n")
    bash_script = ""
    for msg in ipl_messages:
        if "type" in msg:
            import shlex

            # print(msg)
            bash_script += msg["function"]["arguments"]["cmd"] + "\n"
            tokens = shlex.split(msg["function"]["arguments"]["cmd"])

            all_cmds = []
            # split by pipe |
            while "|" in tokens:
                idx = tokens.index("|")
                all_cmds.append(tokens[:idx])
                tokens = tokens[idx + 1 :]
            all_cmds.append(tokens)
            # print(all_cmds)

    with open(f"bash/script_{conv_idx}.sh", "w") as fout:
        fout.write(bash_script)
    print(bash_script)
    print("errors: ", analysis_result.errors)
