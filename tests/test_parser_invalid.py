from pathlib import Path

from sigmadsl.parser import parse_source


FIXTURES = Path("tests/fixtures/invalid")


def _codes(diags):
    return [d.code for d in diags]


def test_invalid_missing_in_context():
    path = FIXTURES / "missing_in_context.sr"
    _, diags = parse_source(path.read_text(encoding="utf-8"), file=path)
    assert "SD200" in _codes(diags)


def test_invalid_missing_colon_rule_header():
    path = FIXTURES / "missing_colon_rule.sr"
    _, diags = parse_source(path.read_text(encoding="utf-8"), file=path)
    assert "SD200" in _codes(diags)


def test_invalid_inconsistent_indentation():
    path = FIXTURES / "indentation_error.sr"
    _, diags = parse_source(path.read_text(encoding="utf-8"), file=path)
    assert "SD101" in _codes(diags)


def test_invalid_branch_missing_then_lines():
    path = FIXTURES / "missing_then_lines.sr"
    _, diags = parse_source(path.read_text(encoding="utf-8"), file=path)
    assert "SD201" in _codes(diags)


def test_invalid_forbidden_assignment_in_expr():
    path = FIXTURES / "forbidden_assignment.sr"
    _, diags = parse_source(path.read_text(encoding="utf-8"), file=path)
    assert "SD204" in _codes(diags)


def test_invalid_forbidden_loop_stmt():
    path = FIXTURES / "forbidden_loop_stmt.sr"
    _, diags = parse_source(path.read_text(encoding="utf-8"), file=path)
    assert "SD204" in _codes(diags)

