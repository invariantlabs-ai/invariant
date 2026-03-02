"""
Span's can be used to measure the duration of certain sub-tasks
during guardrail rule evaluation.
"""

import contextvars
import math
import time
from collections import defaultdict

CURRENT_SPAN = contextvars.ContextVar("CURRENT_SPAN", default=[])


class Span:
    """
    A class to represent a time span during execution (measures duration).
    """

    def __init__(self, name: str):
        self.name = name
        self.start = None
        self.children = []
        self.end = None

    def __enter__(self):
        current = CURRENT_SPAN.get()
        if len(current) > 0:
            current[-1].children.append(self)
        self.start = time.time()
        self.end = None

        CURRENT_SPAN.set(current + [self])

        return self

    def duration(self) -> float:
        """
        Return the duration of the span in seconds.
        """
        return (self.end or time.time()) - self.start

    def __exit__(self, exc_type, exc_value, traceback):
        self.end = time.time()
        current = CURRENT_SPAN.get()
        if len(current) > 0:
            assert current[-1] == self, "span end does not match span start"
            current.pop()
        else:
            CURRENT_SPAN.set([])

    def to_str(self, indent: int = 0) -> str:
        """
        Convert the span to a string representation.
        """
        result = (
            " " * indent
            + f"{self.name}: {((self.end or time.time()) - self.start) * 1000:.2f} ms\n"
        )
        for child in self.children:
            result += child.to_str(indent + 2)
        return result

    def timeline(self, scale=None, start=None) -> str:
        """Return a text-timeline max 80 chars wide (after 30-char label)."""
        # --- label (30 chars) -----------------------------------------------------
        label = (self.name[:27] + "...") if len(self.name) > 30 else self.name
        label += " " * (30 - len(label))

        # --- timing & scaling -----------------------------------------------------
        end_time = self.end or time.time()
        total_duration = end_time - self.start
        scale = 80 / total_duration if total_duration > 0 else 1.0

        offset_raw = 0 if start is None else (self.start - start) * scale
        start_pos = min(79, math.ceil(offset_raw))  # round ⬆
        end_pos = min(
            80, math.floor((end_time - (start or self.start)) * scale + offset_raw)
        )  # round ⬇
        if end_pos <= start_pos:
            end_pos = start_pos + 1

        # --- bar with duration in the middle --------------------------------------
        bar_len = end_pos - start_pos
        duration_ms = int((end_time - self.start) * 1000)
        num_str = f"{duration_ms} ms"
        bar = ["-"] * bar_len
        mid = max(0, (bar_len - len(num_str)) // 2)
        bar[mid : mid + len(num_str)] = list(num_str)

        line = label + " " * start_pos + "|" + "".join(bar) + "|"

        # --- children -------------------------------------------------------------
        lines = [line] + [child.timeline(scale=scale, start=self.start) for child in self.children]
        return "\n".join(lines)

    # -------- utility ------------------------------------------------------------
    def _merge(self, intervals):
        """Merge overlapping [start, end] intervals (assumes end > start)."""
        if not intervals:
            return []
        intervals.sort()  # by start
        s, e = intervals[0]
        merged = []
        for ns, ne in intervals[1:]:
            if ns <= e:  # overlap
                e = max(e, ne)
            else:  # disjoint → push, reset
                merged.append((s, e))
                s, e = ns, ne
        merged.append((s, e))
        return merged

    # -------- Span methods -------------------------------------------------------
    def collect(self):
        """Return *flat* list of all spans (self + descendants)."""
        spans = [self]
        for child in self.children:
            spans.extend(child.collect())
        return spans

    def span_percentage(self) -> str:
        """
        Text histogram of %-time per label.
        * same-label overlaps aren’t double-counted
        * sequential same-label spans are summed
        * line width: 30-char label + 1 + bar_width + 2 + “xxx.x%” = 80
        """
        root_start = self.start
        root_end = self.end or time.time()
        total_win = root_end - root_start or 1.0

        # aggregate intervals per label
        spans_by_label = defaultdict(list)
        for span in self.collect():
            spans_by_label[span.name].append((span.start, span.end or time.time()))

        # compute % per label
        pct = {}
        for label, ivals in spans_by_label.items():
            merged = self._merge(ivals)
            covered = sum(e - s for s, e in merged)
            pct[label] = 100 * covered / total_win

        return pct

    def render_span_percentage(self, bar_width=40) -> str:
        pct = self.span_percentage(bar_width=bar_width)
        # render
        lines = []
        for label, p in sorted(pct.items(), key=lambda x: -x[1]):  # largest first
            bar_len = int(bar_width * p / 100)
            bar = "#" * bar_len
            lbl = (label[:27] + "...") if len(label) > 30 else label
            lbl += " " * (30 - len(lbl))
            lines.append(f"{lbl}|{bar:<{bar_width}}| {p:5.1f}%")
        return "\n".join(lines)

    def header_span_percentage(self) -> str:
        pct = self.span_percentage()
        # create X-Invariant-Checking-Spans header
        header_values = []
        # just a: 32%, b: 12%, c: 8% → a: 32%, b: 12%, c: 8%
        for label, p in sorted(pct.items(), key=lambda x: -x[1]):
            header_values += [f"{label}: {p:.5f}%"]
        return ", ".join(header_values)
