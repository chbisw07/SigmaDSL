from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SourceSpan:
    line: int
    column: int


@dataclass(frozen=True)
class Expr:
    """
    Sprint 0.1-A: expressions are parsed only to a shallow token list / text.

    Later sprints can replace this with a real expression AST without changing
    the surrounding rule/branch structure.
    """

    text: str
    span: SourceSpan


@dataclass(frozen=True)
class VerbArg:
    name: str
    value: Expr


@dataclass(frozen=True)
class VerbCall:
    name: str
    args: tuple[VerbArg, ...]
    span: SourceSpan


@dataclass(frozen=True)
class ThenLine:
    call: VerbCall
    span: SourceSpan


@dataclass(frozen=True)
class Branch:
    kind: str  # 'when' | 'elif' | 'else'
    condition: Expr | None  # else has no condition
    actions: tuple[ThenLine, ...]
    span: SourceSpan


@dataclass(frozen=True)
class Rule:
    name: str
    context: str
    branches: tuple[Branch, ...]
    span: SourceSpan


@dataclass(frozen=True)
class SourceFile:
    rules: tuple[Rule, ...]
    path: Path | None = None

