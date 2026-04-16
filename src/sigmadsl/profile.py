from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from . import ast
from .diagnostics import Diagnostic, Severity, diag
from .expr import Call, ExprNode, dotted_name
from .indicators import INDICATOR_REGISTRY_VERSION, pinned_indicator_keys, referenced_indicator_keys
from .linting import lint_text
from .modules import load_modules_for_path, resolve_import_closure
from .parser import parse_source
from .typechecker import typecheck_source_file


@dataclass(frozen=True)
class ProfileSummary:
    files: tuple[str, ...]
    rule_count: int
    contexts: tuple[str, ...]
    verbs: tuple[str, ...]
    functions: tuple[str, ...]
    indicators: dict

    def to_dict(self) -> dict:
        return {
            "files": list(self.files),
            "rule_count": self.rule_count,
            "contexts": list(self.contexts),
            "verbs": list(self.verbs),
            "functions": list(self.functions),
            "indicators": self.indicators,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, indent=2) + "\n"


def profile_paths(path: Path) -> tuple[ProfileSummary | None, list[Diagnostic]]:
    modules, index_diags, root = load_modules_for_path(path)
    if index_diags:
        return None, sorted(index_diags)

    entry_paths = [path] if path.is_file() else [m.path for m in modules]
    closure, import_diags = resolve_import_closure(root=root, modules=modules, entry_paths=entry_paths)
    if import_diags:
        return None, sorted(import_diags)

    rule_count = 0
    contexts: set[str] = set()
    verbs: set[str] = set()
    functions: set[str] = set()
    indicator_keys: set[str] = set()

    all_diags: list[Diagnostic] = []

    for m in closure:
        all_diags.extend(m.parse_diags)
        if m.source_file is None or m.parse_diags:
            continue

        all_diags.extend(typecheck_source_file(m.source_file))
        all_diags.extend(lint_text(m.text, file=m.path))

        if [d for d in all_diags if d.location.file == m.path]:
            continue

        rule_count += len(m.source_file.rules)
        contexts.update(r.context for r in m.source_file.rules)
        verbs.update(_verbs_used(m.source_file))
        functions.update(_functions_used(m.source_file))
        indicator_keys.update(referenced_indicator_keys(m.source_file))

    if all_diags:
        return None, sorted(all_diags)

    return (
        ProfileSummary(
            files=tuple(str(m.path) for m in closure),
            rule_count=rule_count,
            contexts=tuple(sorted(contexts)),
            verbs=tuple(sorted(verbs)),
            functions=tuple(sorted(functions)),
            indicators={
                "registry_version": INDICATOR_REGISTRY_VERSION,
                "pinned": list(pinned_indicator_keys()),
                "referenced": sorted(indicator_keys),
            },
        ),
        [],
    )


def _verbs_used(sf: ast.SourceFile) -> set[str]:
    out: set[str] = set()
    for rule in sf.rules:
        for branch in rule.branches:
            for then_line in branch.actions:
                out.add(then_line.call.name)
    return out


def _functions_used(sf: ast.SourceFile) -> set[str]:
    out: set[str] = set()

    def walk(node: ExprNode | None):
        if node is None:
            return
        if isinstance(node, Call):
            fn = dotted_name(node.func)
            if fn is not None:
                out.add(fn)
            for a in node.args:
                walk(a)
            for _, v in node.kwargs:
                walk(v)
            return
        for child in getattr(node, "__dict__", {}).values():
            if isinstance(child, ExprNode):
                walk(child)
            elif isinstance(child, tuple):
                for item in child:
                    if isinstance(item, ExprNode):
                        walk(item)
                    elif isinstance(item, tuple) and len(item) == 2 and isinstance(item[1], ExprNode):
                        walk(item[1])

    for rule in sf.rules:
        for branch in rule.branches:
            if branch.condition is not None:
                walk(branch.condition.node)
            for then_line in branch.actions:
                for arg in then_line.call.args:
                    walk(arg.value.node)

    return out
