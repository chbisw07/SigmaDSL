# Option contract selection helpers (v1.1-C)

This example pack demonstrates **deterministic contract selection** over explicit option snapshot inputs:

- ATM selection
- OTM selection
- delta-based selection (when delta is present)

Scope:
- selection happens once per run (single contract stream is chosen deterministically)
- no option chain context (`in chain:`) and no chain analytics
- no fuzzy/broker symbol matching (canonical `OPT:...` ids only)

## Files

- `option_selected_echo.sr` — emits a signal with `reason=option.contract_id` to make the selected contract visible
- `data/options_bundle.csv` — multi-contract option snapshot bundle
- `expected/` — expected JSONL outputs for each selection mode

## Commands

Validate:

```bash
sigmadsl validate examples/options_contract_rules/option_selected_echo.sr
```

ATM (CALL):

```bash
sigmadsl run \
  --context option \
  --select atm \
  --right CALL \
  --input examples/options_contract_rules/data/options_bundle.csv \
  --rules examples/options_contract_rules/option_selected_echo.sr
```

Nearest OTM (CALL):

```bash
sigmadsl run \
  --context option \
  --select otm \
  --right CALL \
  --input examples/options_contract_rules/data/options_bundle.csv \
  --rules examples/options_contract_rules/option_selected_echo.sr
```

Delta selection (CALL, target 0.68):

```bash
sigmadsl run \
  --context option \
  --select delta \
  --right CALL \
  --target-delta 0.68 \
  --input examples/options_contract_rules/data/options_bundle.csv \
  --rules examples/options_contract_rules/option_selected_echo.sr
```

