"""
1. Download trajectories from here: https://drive.google.com/drive/folders/141YuDFtt502NhufbVL4YH463TZ4VFb2v
2. Run: rye run python step_webarena.py --print-full --trace-dir 2405_all_tasks_step_webarena_bugfix
3. The file 'step_webarena.json' will be created with the traces
"""
import argparse
import copy
import json
import os
import re
from pydantic.dataclasses import dataclass
from typing import Optional
from presidio_analyzer import AnalyzerEngine
from invariant.examples.web.parsing_utils import create_id_based_action
from invariant.examples.web.web_rules import *
from invariant.traces import *
from invariant.runtime.input import Input
#from langsmith import traceable

@dataclass
class Trace:
    input: list
    reward: int
    objective: str

    def print(self, max_len=1000, ignore_el=None, lite=False):
        print("======================")
        print("obj: ", self.objective)
        for a in self.input:
            if lite and "role" in a and a["role"] != "user":
                continue
            if ignore_el is not None:
                if "type" in a and "tool_call" in ignore_el:
                    continue
                if a["role"] in ignore_el:
                    continue
            if "type" in a:
                print_obj = copy.deepcopy(a["function"])
            else:
                print_obj = copy.deepcopy(a)
            for k, v in print_obj.items():
                if type(v) is str and len(v) > max_len:
                    print_obj[k] = v[:max_len] + "..."

            if "type" in a:
                print("call: ", end="")
            else:
                print("msg: ", end="")
            print(print_obj)
                
        print("REWARD: ", self.reward)
        print("======================")

    
# @traceable(
#     project_name="webarena",
#     run_type="llm",
#     metadata={"ls_provider": "my_provider", "ls_model_name": "my_model", "env": "default_env"}
# )
# def step_webarena_agent(inv_trace: list):
#     return inv_trace

def get_env(data):
    if type(data) is not dict:
        return None

    if ":7780" in data['trajectory'][0]['url']:
        return "shopping_admin"
    elif ":3000" in data['trajectory'][0]['url']:
        return "map"
    elif "webarena-env-shopping" in data['trajectory'][0]['url']:
        return "shopping"
    elif "webarena-env-reddit" in data['trajectory'][0]['url']:
        return "reddit"
    elif "webarena-env-github" in data['trajectory'][0]['url']:
        return "github"
    elif "webarena-env-cms" in data['trajectory'][0]['url']:
        return "shopping_admin"
    elif ":8023" in data['trajectory'][0]['url']:
        return "gitlab"
    elif ":9999" in data['trajectory'][0]['url']:
        return "forum"
    assert False, f"unknown url: {data['trajectory'][0]['url']}"

def load_data(trace_dir, idx):
    trace_file = os.path.join(trace_dir, f"{idx}.json")
    if not os.path.exists(trace_file):
        return None, 0
    with open(trace_file) as f:
        data = json.load(f)
    return data


def read_trace(data):
    objective = data['trajectory'][0]['objective']
    # url = data['trajectory'][0]['url']
    # trace = Trace(actions=[], reward=0, objective=objective)

    input = [user(objective)]

    for d in data['trajectory']:
        observation = d['observation']
        objective = d['objective']

        input.append({"role": "tool", "content": observation})

        action = d['action']
        action_idx = re.search(r'(\[\d+\])', action)

        if action_idx is not None:
            lines = filter(lambda line: action_idx[0] in line, observation.splitlines())
            lines = list(map(lambda line: line.strip(), lines))
            if len(lines) == 1:
                extra_arg = lines[0][lines[0].find("]")+2:]
        else:
            extra_arg = ""

        input += [{"role": "assistant", "content": d["reason"]}]
        try:
            call = create_id_based_action(action, extra_arg=extra_arg)
            input += [call]
        except Exception as e:
            call = None
            # print("exc: ", e)

        if call is None:
            continue

    reward = d.get('reward', 0.0)
    return Trace(input, reward, objective)

class Stat:
    
    def __init__(self):
        self.tot_inst = {}
        self.tot_reward = {}
        self.tot_flagged = {}

    def flag(self, env):
        if env not in self.tot_flagged:
            self.tot_flagged[env] = 0
        self.tot_flagged[env] += 1

    def add_inst(self, env, reward):
        if env not in self.tot_inst:
            self.tot_inst[env] = 0
            self.tot_reward[env] = 0
        self.tot_inst[env] += 1
        self.tot_reward[env] += reward
        
def diff_observations(obs1, obs2, ignore_map=None, split_chr="\n", max_len=1000):
    obs1 = obs1.split(split_chr)
    obs2 = obs2.split(split_chr)

    for old_val, new_val in ignore_map:
        obs1 = [re.sub(old_val, new_val, x.strip()) for x in obs1]
        obs2 = [re.sub(old_val, new_val, x.strip()) for x in obs2]
    
    diff_chunks = []
    for chunk in obs1:
        if chunk not in obs2:
            diff_chunks += [chunk]

    diff = "\n".join(diff_chunks)
    if len(diff) > max_len:
        diff = f"<DIFF LONGER THAN {max_len}>"
    return diff

    # obs1 = re.sub(r'\[\d+\]', '[]', obs1).split("\n")
    # obs1 = [x.strip() for x in obs1]
    # diff_lines = []
    # for x in obs2.split("\n"):
    #     parsed_x = re.sub(r'\[\d+\]', '[]', x).strip()
    #     if parsed_x not in obs1:
    #         diff_lines += [x.strip()]
    # if len(diff_lines) > 5:
    #     return ["<DIFF MORE THAN 5 LINES]"]
    # return diff_lines

def filter_hallucinated_pii(trace: Trace) -> bool:
    """Filter trace based on whether it contains hallucinated PII."""
    excluded_words = ['goto']
    analyzer = AnalyzerEngine()
    entities = ['EMAIL_ADDRESS', 'PERSON', 'PHONE_NUMBER', 'CREDIT_CARD']
    for i, a in enumerate(trace.actions):
        found_entities = analyzer.analyze(text=a.action, language='en', entities=entities, score_threshold=0.7)
        for ent in found_entities:
            ent_text = a.action[ent.start:ent.end]
            found = ent_text.lower() in trace.objective.lower()
            for j in range(i+1):
                if ent_text.lower() in trace.actions[j].observation.lower():
                    found = True
            if not found and not ent_text in excluded_words:
                print("Possible hallucination, not found: ", ent_text, ent)
                return True
    return False

def filter_repetition(trace: Trace, rep_k: int) -> bool:
    """Filter trace based on whether some action repeats k times or more"""
    cnt += {}
    for a in trace.actions:
        parsed_action = re.sub(r'\[\d+\]', '[]', a.action).strip()
        if parsed_action not in cnt:
            cnt[parsed_action] = 0
        cnt[parsed_action] += 1
        if cnt[parsed_action] >= rep_k:
            return True
    return False

def filter_has_action(trace: Trace, action: str, has_action: bool) -> bool:
    """Filter trace based on whether given action is present or not"""
    action_in_trace = any([action in a.action for a in trace.actions])
    return action_in_trace == has_action

def filter_short_trace(trace: Trace, n: int) -> bool:
    """Filter traces that have length shorter or equal than n"""
    return len(trace.actions) <= n

def filter_different_actions(trace: Trace, n: int) -> bool:
    """Filter traces that have less than n different actions"""
    actions = set()
    for a in trace.actions:
        parsed_action = re.sub(r'\[\d+\]', '[]', a.action).strip()
        actions.add(parsed_action)
    return len(actions) <= n

def filter_query_has(trace: Trace, substr: str) -> bool:
    """Filter traces that contain given substring."""
    return substr.lower() in trace.objective.lower()

parser = argparse.ArgumentParser()
parser.add_argument("--idx", type=str, default=None)
parser.add_argument("--env", type=str, default=None)
parser.add_argument("--print-lite", action='store_true', default=False)
parser.add_argument("--print-full", action='store_true', default=False)
parser.add_argument("--print-stats", action='store_true', default=False)
parser.add_argument("--query-has", type=str, default=None)
parser.add_argument("--tot-flags", type=int, default=0)
parser.add_argument("--trace-dir", type=str, default=None)
args = parser.parse_args()

stat = Stat()

if args.idx is not None:
    if ":" in args.idx:
        args.idx = args.idx.split(":")
        from_idx, to_idx = int(args.idx[0]), int(args.idx[1])
    else:
        from_idx, to_idx = int(args.idx), int(args.idx)+1
else:
    from_idx, to_idx = 0, 811

#rule = RepetitionFilterRule(10, ["element_id"])
#rule = DifferentActionsRule(2)
#rule = Hallucinated_PII_Rule(["goto"])

rules = [
    #Hallucinated_PII_Rule(["goto"]),
    ContainsSubstring("best-selling product", types=["message"]),
    #RepetitionFilterRule(3, ["element_id"]),
]

if args.query_has is not None:
    rules += [ContainsSubstring(args.query_has, types=["message"])]

out_traces = []

for idx in range(from_idx, to_idx):
    data = load_data(args.trace_dir, idx)
    env = get_env(data)
    if env is None:
        continue
    if args.env is not None and env != args.env:
        continue

    trace = read_trace(data)
    out_traces += [trace.input]

    # if args.query_has is not None:
    #     if args.query_has.lower() not in trace.objective.lower():
    #         continue

    flags = []
    for rule in rules:
        if rule.filter(trace.input):
            flags += [f"Flagged by rule: {type(rule)}"]

    # if args.query_has is not None and filter_query_has(trace, args.query_has):
    #     flagged = True

    # if filter_hallucinated_pii(trace):
    #     flagged = True

    # if filter_repetition(trace, 5):
    #     flagged = True

    # if filter_short_trace(trace, 3):
    #     flagged = True

    # if filter_different_actions(trace, 1):
    #     flagged = True

    # if filter_has_action(trace, "click", False):
    #     flagged = True

    # if filter_has_action(trace, "combobox", True):
    #     flagged = True
    
    # if True:
    #     flagged = True

    #print(idx, trace.objective, trace.reward, env)
    if len(flags) >= args.tot_flags and (args.print_lite or args.print_full):
        print("Flags: ", flags)
        print("Index: ", idx)
        if args.print_lite:
            trace.print(lite=True, max_len=90)
        if args.print_full:
            trace.print(max_len=90)

        prev_obs = None
        for idx, el in enumerate(trace.input):
            if "type" in el:
                print("call: ", el["function"])

            if "role" in el and el["role"] == "tool":
                obs = el["content"]
                if prev_obs is not None:
                    print("out_diff: ", diff_observations(prev_obs, obs, ignore_map=[(r'\[\d+\]', '[]')]))
                prev_obs = obs

        # if args.print_full:
        #     trace.print()
        
        # stat.flag(env)
        # print("file: ", idx)

        # import difflib
        # differ = difflib.Differ()
        # prev_obs = None
        # for i, el in enumerate(trace.input):
        #     if i > 0:
        #         print("diff: ", diff_observations(
        #             differ, trace.actions[i-1].observation, act.observation))

    stat.add_inst(env, trace.reward)

if args.print_stats:
    for env in stat.tot_inst:
        print(f"env: {env}, reward: {stat.tot_reward[env]}, inst: {stat.tot_inst[env]}, avg_reward: {stat.tot_reward[env]/stat.tot_inst[env]:.2f}")
    print("==============")
    for env in stat.tot_flagged:
        print(f"env: {env}, flagged: {stat.tot_flagged[env]}")


with open("webarena_step.json", "w") as f:
    metadata = {"metadata": {"description": "Traces collected from WebArena Step agent"}}
    print(json.dumps(metadata), file=f)
    for trace in out_traces:
        for i in range(len(trace)):
            if "function" in trace[i]:
                trace[i] = {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [trace[i]],
                }
        print(json.dumps(trace), file=f)
