from pathlib import Path

from sigmadsl.parser import parse_source


FIXTURES = Path("tests/fixtures/valid")


def test_valid_fixtures_parse_without_diagnostics():
    for path in sorted(FIXTURES.glob("*.sr")):
        text = path.read_text(encoding="utf-8")
        ast, diags = parse_source(text, file=path)
        assert diags == [], f"{path} unexpectedly produced diagnostics: {diags}"
        assert ast is not None
        assert len(ast.rules) >= 1

