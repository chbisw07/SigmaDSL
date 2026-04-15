# Equity Minimal Rules (v0.1-B)

This folder is a starter **sample pack** for Sprint **v0.1-B** (“Ship samples + docs”).

All `.sr` files in this directory are expected to validate successfully with the current
Sprint **v0.1-A** parser (rule/when/elif/else/then, indentation-sensitive).

## Validate a single file

```bash
sigmadsl validate examples/equity_min_rules/basic_signal.sr
```

Expected output:

```text
OK
```

## Validate the whole sample pack

```bash
sigmadsl validate examples/equity_min_rules/
```

Expected output:

```text
OK
```

The reference output used by tests is in `expected/validate_ok.txt`.

## Samples

- `basic_signal.sr`: minimal rule, `when true`, single `then` verb call.
- `bar_threshold.sr`: dot-access + numeric comparison + logical `and`.
- `multi_then.sr`: multiple `then` lines within a branch.
- `elif_else.sr`: `when` + `elif` + `else` structure.
- `parentheses_expr.sr`: parentheses in conditions (shape-only parsing in v0.1).
- `percent_literal.sr`: percent literal token (`0.2%`) in a condition.
- `comments_and_blanks.sr`: comment lines and blank lines.
- `identifier_rule_name.sr`: rule name as an identifier (supported, though strings are preferred).
- `verb_args.sr`: multiple verb call arguments.
- `two_rules_one_file.sr`: multiple rules in a single file.

## Limitations (intentional, for later sprints)

- Expressions are parsed for **syntax shape** only in v0.1 (no typing/semantics).
- Verbs are parsed as calls; verb whitelisting and profile enforcement are later (v0.2+ / v1.0+).

