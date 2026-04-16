from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .diagnostics import Diagnostic
from .runner import decision_jsonl_lines, replay_from_log


@dataclass(frozen=True)
class DiffSummary:
    equal: bool
    count_a: int
    count_b: int
    signals_a: int
    annotations_a: int
    intents_a: int
    constraints_a: int
    signals_b: int
    annotations_b: int
    intents_b: int
    constraints_b: int
    first_divergence_index: int | None
    a_line: str | None
    b_line: str | None

    def to_text(self) -> str:
        lines: list[str] = []
        lines.append("Diff\n")
        lines.append(f"- equal: {'true' if self.equal else 'false'}\n")
        lines.append(
            f"- decisions_a: {self.count_a} (signal={self.signals_a}, annotation={self.annotations_a}, intent={self.intents_a}, constraint={self.constraints_a})\n"
        )
        lines.append(
            f"- decisions_b: {self.count_b} (signal={self.signals_b}, annotation={self.annotations_b}, intent={self.intents_b}, constraint={self.constraints_b})\n"
        )
        if self.first_divergence_index is None:
            lines.append("- first_divergence: <none>\n")
            return "".join(lines)

        lines.append(f"- first_divergence_index: {self.first_divergence_index}\n")
        lines.append("A\n")
        lines.append((self.a_line or "<missing>") + "\n")
        lines.append("B\n")
        lines.append((self.b_line or "<missing>") + "\n")
        return "".join(lines)


def diff_run_logs(log_a: Path, log_b: Path) -> tuple[DiffSummary | None, list[Diagnostic]]:
    res_a, diags_a = replay_from_log(log_path=log_a)
    if diags_a:
        return None, diags_a
    assert res_a is not None

    res_b, diags_b = replay_from_log(log_path=log_b)
    if diags_b:
        return None, diags_b
    assert res_b is not None

    lines_a = [l.rstrip("\n") for l in decision_jsonl_lines(res_a)]
    lines_b = [l.rstrip("\n") for l in decision_jsonl_lines(res_b)]

    equal = lines_a == lines_b
    i = _first_divergence(lines_a, lines_b)
    a_line = lines_a[i] if i is not None and i < len(lines_a) else None
    b_line = lines_b[i] if i is not None and i < len(lines_b) else None

    sa, aa, ia, ca = _counts(lines_a)
    sb, ab, ib, cb = _counts(lines_b)

    return (
        DiffSummary(
            equal=equal,
            count_a=len(lines_a),
            count_b=len(lines_b),
            signals_a=sa,
            annotations_a=aa,
            intents_a=ia,
            constraints_a=ca,
            signals_b=sb,
            annotations_b=ab,
            intents_b=ib,
            constraints_b=cb,
            first_divergence_index=i,
            a_line=a_line,
            b_line=b_line,
        ),
        [],
    )


def _first_divergence(a: list[str], b: list[str]) -> int | None:
    n = min(len(a), len(b))
    for i in range(n):
        if a[i] != b[i]:
            return i
    if len(a) != len(b):
        return n
    return None


def _counts(lines: list[str]) -> tuple[int, int, int, int]:
    signals = 0
    annotations = 0
    intents = 0
    constraints = 0
    for l in lines:
        try:
            d = json.loads(l)
        except Exception:
            # This should never happen for our runner output; treat as annotation for safety.
            annotations += 1
            continue
        kind = d.get("kind")
        if kind == "signal":
            signals += 1
        elif kind == "annotation":
            annotations += 1
        elif kind == "intent":
            intents += 1
        elif kind == "constraint":
            constraints += 1
        else:
            annotations += 1
    return signals, annotations, intents, constraints
