import json
from pathlib import Path

from sigmadsl.evaluator import compile_source_file, evaluate_underlying
from sigmadsl.linting import lint_text
from sigmadsl.parser import parse_source
from sigmadsl.runtime_models import Bar, UnderlyingEvent, dec
from sigmadsl.typechecker import typecheck_source_file


def _load_events(path: Path) -> list[UnderlyingEvent]:
    rows = json.loads(path.read_text(encoding="utf-8"))
    events: list[UnderlyingEvent] = []
    for i, r in enumerate(rows):
        bar = Bar.from_dict(r)
        symbol = str(r.get("symbol", "TEST"))
        uret = r.get("underlying_return_5m")
        events.append(
            UnderlyingEvent(
                symbol=symbol,
                index=i,
                bar=bar,
                underlying_return_5m=dec(uret) if uret is not None else None,
            )
        )
    return events


def _compile_rules(path: Path):
    text = path.read_text(encoding="utf-8")
    sf, parse_diags = parse_source(text, file=path)
    assert sf is not None
    assert parse_diags == []
    assert typecheck_source_file(sf) == []
    assert lint_text(text, file=path) == []
    return compile_source_file(sf)


def _writeable_json(obj: object) -> str:
    return json.dumps(obj, sort_keys=True, indent=2) + "\n"


def test_evaluator_trace_golden_basic():
    rules = _compile_rules(Path("tests/fixtures/eval/rules_basic.sr"))
    events = _load_events(Path("tests/fixtures/eval/bars_basic.json"))
    result = evaluate_underlying(rules, events)
    golden = Path("tests/golden/eval_basic.json").read_text(encoding="utf-8")
    assert _writeable_json(result.to_dict()) == golden


def test_evaluator_trace_golden_percent_literal():
    rules = _compile_rules(Path("tests/fixtures/eval/rules_percent.sr"))
    events = _load_events(Path("tests/fixtures/eval/bars_percent.json"))
    result = evaluate_underlying(rules, events)
    golden = Path("tests/golden/eval_percent.json").read_text(encoding="utf-8")
    assert _writeable_json(result.to_dict()) == golden


def test_evaluator_is_deterministic_over_repeated_runs():
    rules = _compile_rules(Path("tests/fixtures/eval/rules_basic.sr"))
    events = _load_events(Path("tests/fixtures/eval/bars_basic.json"))
    r1 = evaluate_underlying(rules, events).to_dict()
    r2 = evaluate_underlying(rules, events).to_dict()
    assert r1 == r2


def test_rule_ordering_is_deterministic_across_files():
    # file path order is used as a deterministic cross-file tie-breaker until imports exist.
    text_a = 'rule "A" in underlying:\n    when true:\n        then annotate(note="a")\n'
    text_b = 'rule "B" in underlying:\n    when true:\n        then annotate(note="b")\n'

    sf_a, diags_a = parse_source(text_a, file=Path("a.sr"))
    sf_b, diags_b = parse_source(text_b, file=Path("b.sr"))
    assert sf_a is not None and diags_a == []
    assert sf_b is not None and diags_b == []

    rules = compile_source_file(sf_b) + compile_source_file(sf_a)
    events = [
        UnderlyingEvent(
            symbol="X",
            index=0,
            bar=Bar.from_dict({"timestamp": "t0", "open": "1", "high": "1", "low": "1", "close": "1", "volume": "0"}),
        )
    ]

    res = evaluate_underlying(rules, events).to_dict()
    notes = [d.get("note") for d in res["decisions"]]
    assert notes == ["a", "b"]


def test_series_functions_accept_dotted_series_name():
    text = (
        'rule "Series" in underlying:\n'
        "    when bar.close == highest(bar.close, 2):\n"
        '        then annotate(note="ok")\n'
    )
    sf, diags = parse_source(text, file=Path("series.sr"))
    assert sf is not None and diags == []
    rules = compile_source_file(sf)
    events = _load_events(Path("tests/fixtures/eval/bars_basic.json"))
    res = evaluate_underlying(rules, events).to_dict()
    assert [d.get("note") for d in res["decisions"]] == ["ok", "ok", "ok"]
