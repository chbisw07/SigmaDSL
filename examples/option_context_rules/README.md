# Option context rules (v1.1-B)

This example pack demonstrates **runtime option context binding** for rules authored with `in option:`.

## Files

- `option_signals.sr` — rules that reference `option.iv` and `option.delta`
- `data/options_basic.csv` — atomic option snapshot series (single contract)
- `expected/run_option_signals.jsonl` — expected `sigmadsl run` output (JSONL)

## Commands

Validate:

```bash
sigmadsl validate examples/option_context_rules/option_signals.sr
```

Run (option snapshot CSV):

```bash
sigmadsl run \
  --context option \
  --input examples/option_context_rules/data/options_basic.csv \
  --rules examples/option_context_rules/option_signals.sr
```

Replay (optional run log):

```bash
sigmadsl run \
  --context option \
  --input examples/option_context_rules/data/options_basic.csv \
  --rules examples/option_context_rules/option_signals.sr \
  --log-out /tmp/opt_runlog.json

sigmadsl replay --log /tmp/opt_runlog.json
```

Explain (replace `D0001` with an id from the run output):

```bash
sigmadsl explain \
  --context option \
  --input examples/option_context_rules/data/options_basic.csv \
  --rules examples/option_context_rules/option_signals.sr \
  --decision-id D0001
```

