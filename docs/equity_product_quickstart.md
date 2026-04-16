# SigmaDSL Equity Product Quickstart (v1.0)

This quickstart shows the **current stable equity CLI workflow** end-to-end:

- deterministic validation and linting
- deterministic `run` decision outputs (JSONL)
- `explain` (“why did / didn’t it fire?”)
- replay logs + deterministic replay
- deterministic diff
- **reports** (Sprint v1.0-C)
- optional **risk gating** (Sprint v1.0-B)

All examples use files already in this repo.

## Install (dev)

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e ".[dev]"
```

## 1) Validate + lint a rules file

```bash
sigmadsl validate tests/fixtures/eval/rules_basic.sr
sigmadsl lint tests/fixtures/eval/rules_basic.sr
```

Expected output:

```text
OK
```

## 2) Run on a bars CSV (deterministic decisions)

```bash
sigmadsl run --input tests/fixtures/run/bars_basic.csv --rules tests/fixtures/eval/rules_basic.sr > decisions.jsonl
```

`decisions.jsonl` is the stable decision stream (one JSON object per line).

## 3) Explain “why did it fire?”

Pick a decision id from `decisions.jsonl`, then:

```bash
sigmadsl explain --decision-id D0003 --input tests/fixtures/run/bars_basic.csv --rules tests/fixtures/eval/rules_basic.sr
```

## 4) Explain “why didn’t it fire?”

```bash
sigmadsl explain --rule "EQ: Breakout" --event-index 0 --input tests/fixtures/run/bars_basic.csv --rules tests/fixtures/eval/rules_basic.sr
```

## 5) Replay (log + replay)

```bash
sigmadsl run --input tests/fixtures/run/bars_basic.csv --rules tests/fixtures/eval/rules_basic.sr --log-out runlog.json
sigmadsl replay --log runlog.json > replay.jsonl
diff -u decisions.jsonl replay.jsonl
```

## 6) Diff (two logs)

```bash
sigmadsl diff run_a.json run_b.json
```

See `docs/debugging_determinism.md` for the replay+diff workflow.

## 7) Report (rule / symbol / day aggregates)

```bash
sigmadsl report --input decisions.jsonl
```

## 8) Optional: risk gating (fail-closed)

Runnable examples live under `examples/risk_rules/`.

Block signals when `close <= 100`:

```bash
sigmadsl run --profile signal --input examples/risk_rules/data/bars_basic.csv --rules examples/risk_rules/packs/signal_always --risk-rules examples/risk_rules/packs/risk_block_close > out.jsonl
sigmadsl report --input out.jsonl
```

See `docs/risk_constraints.md` for the current enforcement semantics.

