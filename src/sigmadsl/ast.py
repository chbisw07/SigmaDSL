from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SourceSpan:
    line: int
    column: int


@dataclass(frozen=True)
class Expr:
    text: str
    node: "ExprNode | None"
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
    imports: tuple["ImportDecl", ...]
    rules: tuple[Rule, ...]
    path: Path | None = None


@dataclass(frozen=True)
class ImportDecl:
    """
    Deterministic module import declaration.

    v0.6-A: `import foo.bar` maps to `<pack_root>/foo/bar.sr`.
    """

    module: str
    span: SourceSpan
