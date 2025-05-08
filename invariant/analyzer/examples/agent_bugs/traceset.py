import json
import os
import textwrap

import termcolor

try:
    from tqdm.notebook import tqdm
except:
    from tqdm import tqdm


def clip_string(string, replacement="…", width=10):
    if width > 0 and len(string) > width:
        string = string[: width - len(replacement)] + replacement
    return string


def format_message(idx, message, arg_value_width=0, **kwargs):
    all_colors = list(sorted(set(termcolor.COLORS.keys()) - set(["white", "black"])))

    def _format_content(content, max_content_lines=100, string_width=30, **kwargs):
        lines = content.split("\n")
        if max_content_lines > 1 and len(lines) > max_content_lines:
            lines = lines[:max_content_lines]
            lines.append("...")
            out = "\n".join(lines)
        elif max_content_lines == 1:
            out = clip_string(lines[0], width=string_width) + ("⏎" if len(lines) > 1 else "")
        else:
            out = content
        return out

    def _color_fn(fn):
        idx = sum(ord(c) for c in fn) % len(all_colors)
        return termcolor.colored(fn, all_colors[idx])

    role = message["role"]  # [:1].upper()

    out = f"[{idx}, {role}] "
    if "tool_calls" in message and len(message["tool_calls"]) > 0:
        assert len(message["tool_calls"]) == 1
        fn = message["tool_calls"][0]["function"]["name"]
        arg = message["tool_calls"][0]["function"]["arguments"]
        if "invariant_highlight" in message["tool_calls"][0]:
            style = lambda x: termcolor.colored(x, attrs=["underline"])
        else:
            style = lambda x: x
        arg = ",".join(
            [f"{k.strip()}:{clip_string(v.strip(), width=arg_value_width)}" for k, v in arg.items()]
        )
        out += f"{style(_color_fn(fn))}({arg})"
    out = termcolor.colored(out, attrs=["bold"])
    out += _format_content(message["content"].strip(), **kwargs)
    return out


def format_trace(trace, join_sequence="\n\n", **kwargs):
    out = []
    for i, message in enumerate(trace):
        out.append(format_message(i, trace[i], **kwargs))
    return join_sequence.join(out)


class TraceHandel:
    def __init__(self, trace):
        self.trace = trace

    def __getitem__(self, i):
        return self.trace[i]

    def __iter__(self):
        return self.trace.__iter__()

    def __str__(self):
        return format_trace(self.trace)

    def __repr__(self):
        return self.trace.__repr__()

    def __len__(self):
        return len(self.trace)

    def _ipython_display_(self):
        print(format_trace(self.trace, skip_sequence="︙"))


class TraceSet:
    def __init__(self, traces=None):
        self.traces = [] if traces is None else traces

        self.stored_file = None

    def save(self, filename):
        with open(filename, "w") as f:
            self.stored_file = filename
            for t in self.traces:
                f.write(json.dumps(t) + "\n")

    @classmethod
    def from_file(cls, filename):
        traces = []
        with open(filename, "r") as f:
            for line in f:
                traces.append(json.loads(line))
        return cls(traces)

    def analyze(self, policy):
        """Analyze the trace set with a given policy"""
        results = []
        for trace in self.traces:
            results += [policy.analyze(trace)]
        return results

    def filter(
        self,
        invariant_condition: str,
        max_items: int | None = None,
        python: str | None = None,
        prefix: str | None = None,
    ) -> "TraceSet":
        max_items = self.get_max_items(max_items)

        invariant_condition = invariant_condition.strip()
        if invariant_condition == "":
            return self
        policy = self.prepare_policy(invariant_condition, prefix)

        if python is not None:
            with open("temp.py", "w") as f:
                f.write(python)

        results = []
        # filter traces by policy
        for trace in tqdm(self.traces[:max_items]):
            result = policy.analyze(trace)
            if len(result.errors) > 0:
                results.append(trace)

        if os.path.exists("temp.py"):
            os.remove("temp.py")

        return TraceSet(results)

    def get_max_items(self, max_items):
        try:
            max_items = int(max_items)
        except:
            max_items = len(self.traces)

        if max_items == -1:
            max_items = len(self.traces)

        max_items = max(min(len(self.traces), max_items), 0)

        return max_items

    def prepare_policy(self, invariant_condition: str, prefix: str | None = None):
        from invariant.analyzer import Policy

        # construct makeshift policy
        policy_str = f"""raise "found result" if:
{textwrap.indent(invariant_condition, "  ")}
        """
        policy_str = textwrap.dedent(policy_str)
        if prefix is not None:
            policy_str = f"{prefix}\n{policy_str}"
        policy = Policy.from_string(policy_str)

        return policy

    def __repr__(self):
        return f"<{type(self).__name__} with {len(self.traces)} traces>"

    def __len__(self):
        return len(self.traces)

    def __getitem__(self, idx):
        return TraceHandel(self.traces[idx])

    def __iter__(self):
        return iter(TraceHandel(trace) for trace in self.traces)

    def pretty(self, max_lines=30, **kwargs):
        appendix = ""
        if max_lines > 1 and len(self.traces) > max_lines:
            traces = self.traces[:max_lines]
            appendix = f"\n...and {len(self.traces) - max_lines} more"
        else:
            traces = self.traces
        traces = [
            format_trace(t, join_sequence=" -> ", max_content_lines=1, arg_value_width=5, **kwargs)
            for t in traces
        ]
        traces = [
            termcolor.colored(f"Trace {i}: ", attrs=["bold"]) + trace
            for i, trace in enumerate(traces)
        ]

        return f"TraceSet with {len(self.traces)} traces:\n" + "\n\n".join(traces) + appendix

    def _ipython_display_(self):
        print(self.pretty())


class OpenDevinLoader(TraceSet):
    @staticmethod
    def parse_trace(trajectory):
        import re

        from invariant.analyzer.traces import assistant, tool, tool_call, user

        regex = {
            "bash": r"<execute_bash>(.*?)</execute_bash>",
            "ipython": r"<execute_ipython>(.*?)</execute_ipython>",
            "browse": r"<execute_browse>(.*?)</execute_browse>",
        }

        trace = []
        last_call_idx = None
        for idx, msg in enumerate(trajectory):
            if msg["role"] == "assistant":
                function_name, arg = None, None
                for lang in ["bash", "ipython", "browse"]:
                    match = re.search(regex[lang], msg["content"], re.DOTALL)
                    if match is not None:
                        function_name = lang
                        arg = match.group(1)
                        thought = msg["content"][: match.start()]
                if function_name is None:
                    trace.append(assistant(msg["content"]))
                else:
                    last_call_idx = str(idx)
                    call = tool_call(last_call_idx, function_name, {"arg": arg})
                    trace.append(assistant(thought, call))
            else:
                if msg["content"].startswith("OBSERVATION:\n\n"):
                    trace.append(tool(last_call_idx, msg["content"][len("OBSERVATION:\n\n") :]))
                else:
                    trace.append(user(msg["content"]))
        return trace

    @classmethod
    def from_repository(cls, repository, project):
        from datasets import load_dataset

        conversations = load_dataset(repository)[project]["conversations"]
        traces = []
        for conv in conversations:
            trace = cls.parse_trace(conv)
            traces.append(trace)
        return cls(traces)


class SWEAgentTraceSet(TraceSet):
    @staticmethod
    def parse_trace(trajectory):
        from invariant.analyzer.traces import assistant, tool, tool_call

        inv_traj = []
        for idx, el in enumerate(trajectory):
            action = el["action"]
            action_name = action[: action.find(" ")]
            action_params = action[action.find(" ") + 1 :]

            if action_name == "edit":
                code = action[action.find("\n") : action.rfind("end_of_edit")]
                loc = action_params[: action_params.find("\n")]
                tc = tool_call(str(idx), "edit", {"code": code, "loc": loc})
            else:
                tc = tool_call(str(idx), action_name, {"arg": action_params})
            inv_traj.append(assistant("", tc))

            observation = el["observation"]
            inv_traj.append(tool(str(idx), observation))
        return inv_traj

    @classmethod
    def from_path(cls, path):
        traces = []
        files = os.listdir(path)
        for tracefile in files:
            with open(os.path.join(path, tracefile), "r") as f:
                input_data = json.loads(f.read())
                trajectory = input_data["trajectory"]
            trace = cls.parse_trace(trajectory)
            traces.append(trace)
        return cls(traces)
