# Risk rules examples (v1.0-B)

This folder contains small, runnable examples showing **risk constraints v1**:

- risk rules run as a separate deterministic phase
- risk constraints can block prior decisions (fail-closed)
- blocked decisions are represented in the stable decision schema via `enforcement`

## Scenario A: Block signals when close <= 100

```bash
sigmadsl run \\
  --profile signal \\
  --input examples/risk_rules/data/bars_basic.csv \\
  --rules examples/risk_rules/packs/signal_always \\
  --risk-rules examples/risk_rules/packs/risk_block_close
```

Compare to:

```bash
diff -u examples/risk_rules/expected/run_signal_blocked.jsonl <(sigmadsl run --profile signal --input examples/risk_rules/data/bars_basic.csv --rules examples/risk_rules/packs/signal_always --risk-rules examples/risk_rules/packs/risk_block_close)
```

## Scenario B: Cap intent quantity at 50

```bash
sigmadsl run \\
  --profile intent \\
  --input examples/risk_rules/data/bars_basic.csv \\
  --rules examples/risk_rules/packs/intent_declare \\
  --risk-rules examples/risk_rules/packs/risk_cap_position
```

