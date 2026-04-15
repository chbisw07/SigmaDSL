from pathlib import Path

from sigmadsl.parser import parse_source
from sigmadsl.typechecker import typecheck_source_file


VALID_DIR = Path("tests/fixtures/typecheck/valid")
INVALID_DIR = Path("tests/fixtures/typecheck/invalid")


def test_typecheck_valid_fixtures_have_no_diagnostics():
    for path in sorted(VALID_DIR.glob("*.sr")):
        sf, parse_diags = parse_source(path.read_text(encoding="utf-8"), file=path)
        assert parse_diags == [], f"{path} parse diagnostics: {parse_diags}"
        diags = typecheck_source_file(sf)
        assert diags == [], f"{path} type diagnostics: {diags}"


def test_typecheck_invalid_fixtures_produce_expected_codes():
    cases = {
        "non_bool_condition.sr": {"SD300"},
        "bad_comparison_types.sr": {"SD300"},
        "bad_boolean_operand.sr": {"SD300"},
        "bad_verb_arg_type.sr": {"SD313"},
        "missing_required_verb_arg.sr": {"SD311"},
        "unknown_verb.sr": {"SD310"},
        "unknown_identifier.sr": {"SD301"},
    }

    for filename, expected_codes in cases.items():
        path = INVALID_DIR / filename
        sf, parse_diags = parse_source(path.read_text(encoding="utf-8"), file=path)
        assert parse_diags == [], f"{path} parse diagnostics: {parse_diags}"
        diags = typecheck_source_file(sf)
        codes = {d.code for d in diags}
        assert expected_codes.issubset(codes), f"{path} expected {expected_codes} in {codes}"

