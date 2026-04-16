from __future__ import annotations

from pathlib import Path

from . import ast
from .builtins import verb_signatures
from .decision_profiles import DecisionProfile, allowed_verbs as allowed_verbs_for_profile
from .diagnostics import Diagnostic, Severity, diag


def check_profile_compliance(
    sf: ast.SourceFile,
    *,
    profile: DecisionProfile,
    file: Path | None = None,
) -> list[Diagnostic]:
    """
    v1.0-A: enforce profile-specific verb allowlists.

    The profile selection is currently provided by the caller (CLI / runner) rather than being
    declared in-language.
    """

    allowed = allowed_verbs_for_profile(profile)
    known_verbs = set(verb_signatures().keys())
    diags: list[Diagnostic] = []

    for rule in sf.rules:
        for branch in rule.branches:
            for then_line in branch.actions:
                name = then_line.call.name
                if name not in known_verbs:
                    # Unknown verbs are handled by type checking; avoid duplicate diagnostics.
                    continue
                if name in allowed:
                    continue
                diags.append(
                    diag(
                        code="SD410",
                        severity=Severity.error,
                        message=f"Profile violation: verb {name!r} is not allowed for profile {profile.value!r}",
                        file=file,
                        line=then_line.call.span.line,
                        column=then_line.call.span.column,
                    )
                )

    return sorted(diags)
