# Sigma Rule DSL — Specification Snapshot (`dsl_v1.1.md`)

Document ID: `dsl_v1.1`  
Status: Implemented snapshot (v1.0 stable equity product + v1.1-A/B option contract context)  
Last updated: 2026-04-24  
Related source documents (mandatory):
- `docs/dsl.md` — thesis backbone + architecture boundaries (source of truth)
- `docs/dsl_proj_plan.md` — versioned roadmap + productization sequencing (source of truth)

---

## Snapshot note (v1.1)

This document is a **full copy-forward** of `docs/dsl_v1.0.md` with **only the referenced v1.1 chapters updated**
to reflect implemented v1.1-A/B option contract context foundations (contract ids + atomic snapshots + runnable `in option:` rules).

Updated sections in this snapshot:
- Chapter 3.1 (options domain boundary clarified for v1.1-A)
- Chapter 12.2.2 (option context field types and runner semantics concretized for v1.1-A/B)

All other sections are inherited unchanged from the base spec.

## 0. Document Status and Governance

### 0.1 Purpose
This document defines the **current intended specification** for **Sigma Rule DSL** before implementation begins. It is meant to be:
- an architecture reference,
- a language and semantics reference,
- a developer reference for initial implementation,
- a stakeholder-facing reference for scope and constraints,
- the baseline for future versioned spec snapshots.

### 0.2 How this document evolves (versioned documentation governance model)
Sigma Rule DSL will be implemented iteratively (sprint-based) per `docs/dsl_proj_plan.md`. The specification evolves the same way:
- `DSL_v0.md` is the **initial complete spec** before development begins.
- After each sprint, this spec is **incrementally updated** to reflect:
  - implementation learnings,
  - semantic clarifications,
  - resolved TBD items,
  - refined constraints,
  - new examples and diagnostics behavior.
- Each major delivered product increment gets a **snapshot version**:
  - `DSL_v0.md` → `DSL_v0.1.md` → `DSL_v0.2.md` → `DSL_v0.3.md` → …
- The document is **not rewritten from scratch** each time. Changes are appended/edited in place with:
  - clear section status markers (LOCKED / CURRENTLY DECIDED / PROVISIONAL / TBD / DEFERRED),
  - changelog entries (future addition; TBD),
  - continuity and traceability preserved.

### 0.3 Locked vs provisional content rule
To keep implementation safe and predictable:
- **LOCKED** sections are treated as non-negotiable constraints for the current DSL generation.
- **CURRENTLY DECIDED** sections are safe to implement now but may evolve with later versions.
- **PROVISIONAL** sections can be implemented behind flags, with tests capturing observed behavior.
- **TBD** sections must not be “filled in” by implementation guesses; they require explicit design resolution.
- **DEFERRED** sections are intentionally postponed to later versions; do not build them early.

---

## 0.4 Status Marker Definitions (required)

Each important section uses a status block:

**Status: LOCKED**  
Rationale: Intentionally fixed for the DSL’s identity and safety.  
Implications: Must be enforced by validators; changes require explicit, high-cost decision.

**Status: CURRENTLY DECIDED**  
Rationale: Clear enough to implement now; expected to remain stable, but can evolve.  
Implications: Implement with tests and diagnostics; allow future tightening/refinement.

**Status: PROVISIONAL**  
Rationale: Direction is known, but details will likely change during implementation.  
Implications: Implement minimally, prefer configuration/feature flags, and document edges.

**Status: TBD**  
Rationale: Not sufficiently resolved; multiple viable options exist.  
Implications: Add placeholders and constraints; collect examples and open questions.

**Status: DEFERRED**  
Rationale: Intentionally postponed to later product versions.  
Implications: Do not implement now; document as future work and ensure current design doesn’t block it.

---

## 0.5 Current Known Decisions (required)

**Status: LOCKED**  
Rationale: These are the identity constraints from `docs/dsl.md`.  
Implications: Enforced by grammar + type checking + validators + runtime semantics.

1) **Python-shaped DSL, not Python** (Ch 10–11).  
2) **Deterministic execution**: same inputs + same versions → same outputs (Ch 6).  
3) **Rule-based and declarative**: rules produce decisions, not programs (Ch 10, Ch 13).  
4) **No loops / no unrestricted functions / no arbitrary assignments** (Ch 2.6, Ch 10–14).  
5) **Actions are verbs**; effects are planned, not executed (Ch 15, Ch 13.5).  
6) **Separation is mandatory**: signal generation vs strategy intent vs execution planning vs risk enforcement (Ch 4, Ch 17–18).  
7) **No direct broker execution in DSL** (Ch 2.6.3).  
8) **Context-aware rules**: underlying, option, chain contexts (Ch 14.2, Ch 8).  
9) **Strong typing and validation** are required (Ch 12).  
10) **Explainability + traceability + replayability** are first-class (Ch 4.6, Ch 6.5, Ch 21.6).

---

## 0.6 Current Open Questions (required)

**Status: TBD**  
Rationale: These require explicit design resolution; do not guess in implementation.  
Implications: Track in issues; resolve in early sprints (v0.1–v0.4) where possible.

Language surface and semantics:
- Exact DSL file extension and packaging conventions (`.sr` vs `.sigma` vs `.dsl`) and module layout.
- Exact syntax for rule headers, metadata, and tags (string vs identifier; quoting rules).
- Missing-data semantics: do we use 2-valued logic only, or a 3-valued `unknown` (Ch 13.3.2)?
- Numeric type and rounding policy: `decimal` scale, price rounding ticks, and deterministic rounding rules.
- Conflict resolution policy details: rule ordering, tie-breakers, and action merge semantics (Ch 13.6, Ch 15.4).

Domain + data:
- Canonical schema for option greeks/IV inputs (computed vs vendor vs hybrid) and validation rules.
- Exact representation of “chain snapshot atomicity” (Ch 8.2) across data feeds and replays.
- Corporate action adjustment policy (Ch 7.5.2) in early versions (v0.4+).

Planning + risk:
- Minimal set of “intent verbs” needed before v2.0, and the first plan IR schema boundaries (Ch 17).
- Risk policy primitives: what is the v1.0 “risk constraints v1” minimum set (Ch 18)?

Tooling:
- Stable decision output schema versioning strategy (Ch 25.2; referenced by roadmap v1.0).
- Golden test strategy for timezones/timestamps (Ch 7.4) across environments.

---

## 0.7 Deferred Topics (required)

**Status: DEFERRED**  
Rationale: Explicitly postponed per `docs/dsl_proj_plan.md` sequencing.  
Implications: Avoid building these early; ensure the core doesn’t preclude them.

- Rich IDE/editor features (language server, code navigation) (Ch 21.5).
- Visualization dashboards and operator UIs (Ch 22).
- Full governance workflows (approvals, promotion, rollback) beyond packaging basics (Ch 9.6, Ch 23.4).
- AI-assisted workflows beyond “suggest → validate → simulate → approve” scaffolding (Ch 20).
- Advanced performance engineering and load testing suite (Ch 26).
- Live integration “at scale” operational hardening (Ch 24) beyond basics needed for deterministic replay.

---

## 0.8 Version Evolution Policy (required)

**Status: CURRENTLY DECIDED**  
Rationale: Needed for predictable development and stakeholder alignment.  
Implications: Changes to language surface must be tracked and versioned.

### 0.8.1 Version naming
- `DSL_v0.md` is the pre-development baseline.
- `DSL_v0.1.md` corresponds roughly to v0.1 product scope (authoring bootstrap).
- `DSL_v0.2.md` corresponds to typed authoring (v0.2).
- `DSL_v0.3.md` corresponds to deterministic evaluation core (v0.3).
- `DSL_v0.4.md` corresponds to MVP replayable equity runner (v0.4).

### 0.8.2 What triggers a spec version bump
- Any change to grammar, types, deterministic semantics, decision schema, or verb signatures.
- Any new reserved keyword or forbidden construct enforcement.
- Any change that affects deterministic outputs (including rounding policies and indicator definitions).

### 0.8.3 How TBD shrinks over time
- Each sprint should close at least a few TBDs, converting them to PROVISIONAL or CURRENTLY DECIDED.
- A section can only become LOCKED after it has:
  - shipped in a released version,
  - a golden test suite covering it,
  - and evidence it supports determinism/replay.

---

## 0.9 Scope Classification (in / anticipated / deferred / out-of-scope)

**Status: CURRENTLY DECIDED**  
Rationale: Required to keep `DSL_v0.md` grounded while still “complete”.  
Implications: Use this to decide what to implement now vs later.

### A) In current DSL scope (v0.x core)
- Rule authoring: rule blocks, contexts, conditions, `then` verb blocks.
- Compile-time validation: syntax + type checking + forbidden constructs.
- Deterministic evaluation for `underlying` context (equities) with trace.
- Deterministic logging + replay + diff (MVP by v0.4).
- Minimal data ingestion for deterministic fixtures/CSV (CLI-level).

### B) Anticipated but not fully specified yet
- Exact decision output schema versioning strategy (v1.0 hardens this).
- Exact missing-data/unknown logic policy (must be resolved early).
- Exact numeric rounding rules (must be resolved before indicator-heavy usage).
- Full module/import syntax and pack manifest schema (v0.6).

### C) Intentionally deferred (later product versions)
- Options contract context (`option`) (v1.1).
- Option chain context (`chain`) + derived metrics (v1.2).
- Intent verbs + execution planning IR (v2.0).
- Rich IDE features and visualization UX (post v1.0+).

### D) Explicitly outside DSL scope
- Direct broker execution from DSL.
- Arbitrary Python execution, arbitrary imports, arbitrary user functions.
- Running untrusted code or permitting side effects during rule evaluation.

---

# Chapter 1 — Introduction (from `docs/dsl.md`)

## 1.1 Problem statement: deterministic rule systems for Indian markets

**Status: CURRENTLY DECIDED**  
Rationale: Core motivation and framing are clear and stable.  
Implications: Drives all major architectural constraints.

Indian equities and derivatives trading systems often fail due to:
- ad-hoc logic embedded in application code,
- weak validation and unclear semantics,
- inability to reproduce decisions (“why did this trade happen?”),
- coupling of signal logic with execution and risk in non-auditable ways.

Sigma Rule DSL addresses this by providing:
- a deterministic, declarative rule language,
- strong validation and typing,
- separation of signal/intent/plan/risk,
- explainability traces and replay logs.

## 1.2 Why a DSL (and why not Python)

**Status: LOCKED**  
Rationale: This is the identity of the project.  
Implications: Must be enforced by the parser and validators.

Python is familiar but unsafe for deterministic trading decision systems because it enables:
- arbitrary side effects, imports, networking, time access,
- uncontrolled loops/recursion,
- mutable state and non-replayable behavior.

Sigma Rule DSL is “Python-shaped” for readability but prohibits Python’s generality.

## 1.3 Key goals and non-goals (summary)

**Status: CURRENTLY DECIDED**  
Rationale: Aligned with `docs/dsl.md` + `docs/dsl_proj_plan.md`.  
Implications: Drives milestone acceptance criteria.

Goals:
- deterministic rule compilation and evaluation,
- explainable outputs with traces and reason codes,
- reusable rule packs,
- domain-aware contexts (underlying, option, chain),
- separation of signal/intent/plan/risk.

Non-goals (high-level; expanded later):
- direct broker execution in the DSL,
- general programming features (loops, arbitrary functions, assignments),
- UI-first product.

---

# Chapter 2 — Product Requirements (PRD alignment)

## 2.1 Product shape (as delivered incrementally)

**Status: CURRENTLY DECIDED**  
Rationale: Directly derived from `docs/dsl_proj_plan.md`.  
Implications: Each version must deliver user-visible CLI capabilities.

The product is a **CLI-first** language toolchain + runtime:
- `validate`, `lint`, `run`, `explain`, `replay`, `diff`, `pack`, `report`, `plan` (as delivered per roadmap).

Roadmap anchoring (from `docs/dsl_proj_plan.md`):
- v0.1–v0.2: authoring + validation
- v0.3–v0.4: deterministic evaluation + trace + replay (MVP at v0.4)
- v0.5: indicators
- v0.6: library packaging/imports
- v1.x: options and chain contexts
- v2.0: intent→plan→risk platform readiness

## 2.2 Guardrails (restated as enforceable requirements)

**Status: LOCKED**  
Rationale: Required by `docs/dsl.md` Ch 2.6 and used throughout architecture.  
Implications: Must be validated at compile time.

- No loops.
- No arbitrary assignments.
- No user-defined functions.
- No direct broker execution from DSL.
- Only allowed built-ins (verbs, indicators, predicates) are permitted.

---

# Chapter 3 — Trading Domain Primer (India-focused)

## 3.1 Domain support boundary for early versions

**Status: PROVISIONAL**  
Rationale: The domain is broad; early versions only need slices.  
Implications: Implement minimal domain entities needed for v0.3–v0.4; extend later.

### v0.1–v0.4 (equity-first)
- Equity instruments (symbol, exchange, segment).
- OHLCV bar series and simple session metadata.
- Basic market calendar assumptions (timezone handling must be explicit; see Ch 7.4).

### v1.1+ (options)
- Option contract identifiers: underlying, expiry, strike, call/put, lot size.
- v1.1-A concretizes a **canonical contract id** for deterministic fixtures and run logs.
- Option snapshot inputs: bid/ask/last, OI, volume, and optional greeks inputs (atomic per-contract snapshots in v1.1-A).

### v1.2+ (chain)
- Chain snapshots with atomicity/staleness policies and derived metrics.

---

# Chapter 4 — System Conceptual Model

## 4.1 Separation of concerns (mandatory)

**Status: LOCKED**  
Rationale: Central architectural discipline from `docs/dsl.md` Ch 4.  
Implications: Language profiles and runtime phases must reflect this separation.

Sigma Rule DSL is explicitly separated into four conceptual layers:
1) **Signal generation**: classification of market conditions into signals/labels.
2) **Strategy intent**: expression of desired position/strategy intent (still not orders).
3) **Execution planning**: translation of intent into broker-agnostic plan outputs.
4) **Risk enforcement**: constraints that gate or adjust outputs (fail-closed).

The DSL must never collapse these into a single “do_trade()” concept.

## 4.2 Deterministic event-driven model

**Status: CURRENTLY DECIDED**  
Rationale: Required for replay and explainability (Ch 6, Ch 13).  
Implications: Runtime API must be event-driven, with stable ordering.

Rules are evaluated in response to events (examples):
- bar close event (equities),
- option snapshot event,
- chain snapshot event,
- session boundary events (open/close),
- (future) order/position update events (outside DSL execution; used for intent/risk context).

Determinism requires a stable definition of:
- what constitutes an event,
- evaluation phase ordering,
- tie-breakers when multiple rules match.

## 4.3 Explainability model

**Status: CURRENTLY DECIDED**  
Rationale: This is a core differentiator and correctness requirement.  
Implications: Every decision output must carry a trace.

Every evaluation produces:
- structured decision outputs (signals/intents/constraints),
- a trace that includes:
  - rule evaluation ordering,
  - predicate outcomes,
  - reasons for match/non-match,
  - actions emitted (verbs invoked),
  - any risk blocks and reason codes.

---

# Chapter 5 — Architecture Overview

## 5.1 Component boundary (DSL vs adapters)

**Status: LOCKED**  
Rationale: “No direct broker execution in DSL” is non-negotiable (Ch 2.6.3).  
Implications: Execution connectors are outside; DSL outputs plans only.

Sigma Rule DSL includes:
- compiler pipeline (lex/parse/type/validate),
- deterministic evaluation runtime,
- trace/replay/diff tooling,
- pack/import tooling.

Out of scope (but referenced via contracts):
- broker adapters,
- market data ingestion systems (beyond reading deterministic fixtures/CSV in early versions).

---

# Chapter 6 — Determinism, Replay, and Correctness

## 6.1 Determinism definition

**Status: LOCKED**  
Rationale: Primary constraint that shapes all other choices.  
Implications: Any non-deterministic behavior is a bug.

Determinism means:
- Given the same:
  - rule pack content (including dependencies),
  - compiler/runtime versions,
  - configuration (timezone policy, rounding policy, indicator versions),
  - input event stream,
- the system produces the same:
  - decisions (signals/intents/plans/constraints),
  - traces,
  - logs,
  - reports.

## 6.2 Sources of non-determinism and required mitigations

**Status: CURRENTLY DECIDED**  
Rationale: Required to avoid “heisenbugs” and to pass replay tests.  
Implications: These items become test gates.

Mitigate:
- wall-clock time: DSL must not access system time; use event timestamps only.
- randomness: DSL must not access RNG.
- floating point drift: prefer deterministic numeric types and fixed rounding policy (TBD: exact policy).
- concurrency: runtime must define deterministic ordering; any parallelism must be semantically transparent.
- external variability: log and replay all inputs; don’t call external services during evaluation.

## 6.3 Replay and diff requirements

**Status: CURRENTLY DECIDED (v0.4-A implementation)**  
Rationale: Replayability is a product requirement by v0.4; the runner needs a concrete, testable log schema.  
Implications: Changes to log schema are versioned; replay must fail-closed on unsupported schema versions.

### 6.3.1 v1.0-B run log schema (profile + decision schema + risk sources)

In v1.0-B, the runner produces a **single JSON run log** with:

- `schema`: `sigmadsl.runlog`
- `schema_version`: `1.0-b`

The log is designed to be **self-contained** for replay:

- embedded rule file texts + sha256
- embedded normalized input events
- provenance metadata for the original CSV (path/hash/columns/row_count)

Minimum contents (v1.0-A):

- engine identifier:
  - `engine_version`
- rules snapshot:
  - `rules.files[] = { path, sha256, text }`
- input snapshot:
  - `input.csv = { path, sha256, columns, row_count }` (provenance only)
  - `input.events[]` (canonical event list used by evaluation)
- profile + decision schema metadata (v1.0-A):
  - `profile` (e.g., `signal`)
  - `decision_schema = { schema, schema_version }`
- risk sources (v1.0-B, optional):
  - `risk.rules.files[] = { path, sha256, text }` (embedded snapshots for replay)
- indicator pins (v0.5-A+):
  - `indicators.registry_version` (engine-side registry identifier)
  - `indicators.pinned[]` (all pinned indicator versions shipped by the engine)
  - `indicators.referenced[]` (which indicator versions were referenced by the executed rules)

Notes:
- replay does not rely on the current filesystem state of original rule/CSV files.
- v0.5-A adds indicator version pinning to support replay-safe feature computation.
- Backward compatibility:
  - v1.0-B loaders should continue accepting:
    - `schema_version: 0.4-a` logs (which omit `indicators` and profile metadata)
    - `schema_version: 0.5-a` logs (which omit profile + decision schema metadata)
    - `schema_version: 1.0-a` logs (which omit the optional `risk` section)

### 6.3.2 v0.4-B diff contract (decisions)

**Status: CURRENTLY DECIDED (v0.4-B implementation)**  
Rationale: Determinism debugging needs a stable, testable comparison tool.  
Implications: Equality definition and divergence reporting are part of the CLI contract.

`sigmadsl diff <run_a.json> <run_b.json>` compares two run logs by:

1) replaying each log deterministically, and
2) comparing the resulting **decision JSONL lines** exactly (byte-for-byte per line, in order).

Equality:
- runs are equal iff the ordered decision JSONL streams are identical.

First divergence:
- the first index where decision lines differ, or
- the first index where one stream ends (length mismatch).

---

# Chapter 7 — Data Model and Market Data Interfaces

## 7.1 Canonical entities (v0 baseline)

**Status: PROVISIONAL**  
Rationale: The entity list is clear (Ch 7), but schema details evolve with implementation.  
Implications: Implement minimal fields required by v0.3–v0.4.

Baseline entities:
- `Instrument` (symbol, exchange, segment)
- `Bar` (timestamp, open, high, low, close, volume)
- `Quote` (bid/ask/last) (optional early)
- `Decision` (signal/intent/constraint + trace)
- `Trace` (rule evaluations + reasons)

## 7.2 Time and timezone policy

**Status: CURRENTLY DECIDED (v0.4 implementation)**  
Rationale: v0.4 needs deterministic behavior across OS/timezone settings; a minimal policy is required now.  
Implications: Timestamp parsing/normalization can be added later, but must be versioned and golden-tested.

v0.4 policy:
- the runner treats `timestamp` as an **opaque string identity**
- timestamps are preserved exactly in:
  - decision outputs,
  - traces,
  - run logs,
  - replay outputs
- the runtime does not parse timestamps or normalize timezones in v0.4
- outputs must be invariant to the process/system timezone (`TZ`) (covered by tests)

Notes / deferred:
- A canonical timezone/normalization policy (IST vs UTC) is still required before indicator-heavy versions.
- When timestamp parsing is introduced, it must be logged/pinned and replayed deterministically.

## 7.3 Data quality and “known/unknown” semantics

**Status: TBD**  
Rationale: Closely tied to 2-valued vs 3-valued logic decision.  
Implications: Needs resolution early because it affects rule semantics.

Constraints already known:
- Missing/stale inputs must not silently produce trades; default behavior should be safe (fail-closed).

---

# Chapter 8 — Option Chain Modeling and Analytics Layer

## 8.1 Chain snapshots and atomicity

**Status: PROVISIONAL**  
Rationale: Clear intent in thesis (Ch 8.2), but concrete feed behaviors vary.  
Implications: Define a minimal chain snapshot contract before implementing v1.2.

Chain snapshot requirements:
- A chain snapshot is a point-in-time set of option rows for a given underlying + expiry set.
- The DSL must treat a chain snapshot as an **atomic input** with:
  - `as_of` timestamp,
  - completeness/quality metadata,
  - staleness indicators.

## 8.2 Derived chain metrics

**Status: DEFERRED**  
Rationale: Delivered in v1.2 per roadmap; do not overspec now.  
Implications: Document intent and constraints; finalize in `DSL_v1.2.md`.

Constraints:
- All derived metrics must be deterministic with fixed rounding.
- Aggregations must define windows and selection clearly (Ch 14.4, Ch 16.4).

---

# Chapter 9 — Strategy Lifecycle and State Machine

## 9.1 Lifecycle governance

**Status: DEFERRED**  
Rationale: Roadmap focuses first on author/run/replay; lifecycle governance comes later.  
Implications: Keep output schemas and logs compatible with future lifecycle features.

---

# Chapter 10 — Sigma Rule DSL: Language Overview

## 10.1 Language intent

**Status: LOCKED**  
Rationale: Foundational identity and constraints.  
Implications: Enforced in grammar and validators.

Sigma Rule DSL is:
- declarative and rule-oriented,
- deterministic and replayable,
- context-aware for underlying/option/chain,
- strongly typed and validated,
- based on action verbs that produce **decisions**, not broker actions.

Sigma Rule DSL is not:
- a general-purpose language,
- a Python subset you can “escape” to,
- a direct trading execution script.

## 10.2 Language profiles (signal / intent / plan / risk)

**Status: CURRENTLY DECIDED (v1.0-A implementation)**  
Rationale: v1.0 requires explicit separation boundaries and stable output contracts.  
Implications: Profile-specific verb allowlists are enforced during validation/linting and must be deterministic.

Profiles:
- `signal`: allowed to emit classifications/signals.
- `intent`: allowed to emit intent outputs (declare/cancel) (outputs only in v1.0-A).
- `plan`: allowed to emit broker-agnostic plans (DEFERRED; not implemented in v1.0-A).
- `risk`: allowed to emit constraints/blocks (outputs only in v1.0-A; enforcement is later).

Profile selection (v1.0-A):
- there is not yet an in-language `profile` header
- the runner/validators select a profile via CLI `--profile {signal|intent|risk}`
- default is `signal` for backward compatibility

Allowed verbs (v1.0-A, enforced by profile):
- `signal`: `emit_signal`, `annotate`
- `intent`: `declare_intent`, `cancel_intent`, `annotate`
- `risk`: `constrain_max_position`, `block`, `annotate`

---

# Chapter 11 — Lexical Structure and Syntax (Python-shaped)

## 11.1 Python-shaped blocks and indentation

**Status: CURRENTLY DECIDED**  
Rationale: Readability requirement; early parsing needs this definition.  
Implications: Lexer must be indentation-aware and deterministic.

- Indentation defines blocks (like Python).
- A file is composed of declarations (imports, rule definitions, pack metadata) (exact top-level structure is PROVISIONAL).
- Comments are supported (line comments `# ...` at minimum).

## 11.1.1 File structure (v0 target)

**Status: PROVISIONAL**  
Rationale: Needed for v0.1 parsing, but exact packaging/imports evolve by v0.6.  
Implications: Start with a minimal, stable top-level and expand carefully.

In v0.x, a DSL source file is intended to contain:
- optional file-level metadata header (DEFERRED unless needed),
- zero or more imports (DEFERRED to v0.6; may be stubbed earlier),
- one or more `rule` blocks.

## 11.1.2 Grammar sketch (v0.x; non-normative but implementation-guiding)

**Status: PROVISIONAL**  
Rationale: Provides enough shape for compiler work while allowing early iteration.  
Implications: Lock down during v0.1–v0.2 with fixtures and goldens.

The following is an intentionally small grammar sketch:

```ebnf
file         := (rule_block | blank | comment)* ;

rule_block   := "rule" rule_name "in" context ":" NEWLINE INDENT rule_body DEDENT ;
rule_name    := STRING | IDENT ;         # prefer STRING for human names
context      := IDENT ;                  # expected: underlying | option | chain

rule_body    := branch+ ;
branch       := when_branch | else_branch ;

when_branch  := "when" expr ":" NEWLINE INDENT then_line+ DEDENT
               ( "elif" expr ":" NEWLINE INDENT then_line+ DEDENT )*
               ( else_branch )? ;

else_branch  := "else" ":" NEWLINE INDENT then_line+ DEDENT ;

then_line    := "then" verb_call NEWLINE ;
verb_call    := IDENT "(" (arg ("," arg)*)? ")" ;
arg          := IDENT "=" expr ;
expr         := ... (see expression grammar) ;
```

Notes:
- The `then` keyword is repeated for each action line to keep parsing unambiguous.
- Multi-action branches are supported via multiple `then` lines.
- “Bare” action statements without `then` are not planned (keeps rule bodies declarative).

## 11.2 Reserved keywords and tokens

**Status: PROVISIONAL**  
Rationale: Keyword set depends on final grammar; avoid churn by keeping minimal early set.  
Implications: v0.1 should lock a minimal keyword set.

Anticipated keywords (subset; subject to change):
- `rule`, `in`, `when`, `then`, `elif`, `else`
- `and`, `or`, `not`
- context names: `underlying`, `option`, `chain` (may be identifiers rather than keywords)

## 11.2.1 Identifiers and namespaces

**Status: CURRENTLY DECIDED**  
Rationale: Needed for stable authoring and diagnostics.  
Implications: Enforce predictable rules; disallow “clever” Python tricks.

- Identifiers are ASCII letters/digits/underscore; must not start with a digit.
- Case sensitivity: **case-sensitive** (PROVISIONAL; likely to remain).
- Namespaces are dot-access only for **context objects** and **structured values** (e.g., `bar.close`, `option.expiry`).
- Dynamic attribute access is forbidden.

## 11.2.2 Literals

**Status: PROVISIONAL**  
Rationale: Literal surface affects parsing and typing; keep it small early.  
Implications: v0.1 should implement a minimal literal set; expand later.

Planned literals:
- Booleans: `true`, `false`
- Integers: `123`
- Decimals: `123.45` (TBD: decimal type representation)
- Strings: `"..."` (double-quoted; escapes TBD)
- Percent literal: `0.2%` (TBD; may be replaced with `percent(0.2)` to avoid parsing ambiguity)

## 11.3 Imports and modules

**Status: CURRENTLY DECIDED (v0.6-A implementation)**  
Rationale: v0.6 introduces reusable rule libraries; imports must be deterministic and safe.  
Implications: Import semantics are part of the compiler/runner contract and must be testable with fixtures.

### 11.3.1 Import syntax (v0.6-A)

Imports are **top-level declarations** only:

```sr
import lib.util

rule "..." in underlying:
    when true:
        then annotate(note="ok")
```

Rules:
- supported form: `import <dotted.module.path>`
- no aliasing (`as`), no selective imports, no star imports
- imports are not allowed inside `rule` blocks

### 11.3.2 Pack root and module name mapping

The compiler/runner chooses a **pack root** deterministically from the CLI input:

- if the user provides a **file** path, the pack root is the file’s parent directory
- if the user provides a **directory** path, the pack root is that directory

Module names map deterministically from filesystem paths under the pack root:

- `<root>/foo/bar.sr` → module name `foo.bar`
- `<root>/foo/__init__.sr` → module name `foo`
- `<root>/__init__.sr` → module name `__root__` (entry-only; not intended as an import target)

Import resolution:

- `import foo.bar` resolves to `<root>/foo/bar.sr`
- resolution is deterministic; no globbing or dynamic paths exist in v0.6-A

### 11.3.3 Dependency validation

Constraints (enforced in v0.6-A):
- missing import targets are compile-time errors
- ambiguous module mappings are compile-time errors
- cycles are compile-time errors (direct or indirect)

The CLI surfaces these errors via deterministic diagnostics codes:
- missing import target: `SD601`
- duplicate/ambiguous module mapping: `SD602`
- import cycle: `SD603`

## 11.4 Expression grammar (conditions)

**Status: PROVISIONAL**  
Rationale: Needed for v0.1–v0.3; exact operator set can be minimal initially.  
Implications: Keep operator precedence explicit and stable.

### 11.4.1 Operators (intended)
- Boolean: `and`, `or`, `not`
- Comparisons: `==`, `!=`, `<`, `<=`, `>`, `>=`
- Arithmetic (restricted; type-checked): `+`, `-`, `*`, `/`

### 11.4.2 Precedence (intended)
Highest → lowest:
1) Parentheses `( ... )`
2) Unary `not`, unary `-`
3) `*`, `/`
4) `+`, `-`
5) Comparisons
6) `and`
7) `or`

### 11.4.3 Function-style calls inside expressions

**Status: CURRENTLY DECIDED**  
Rationale: DSL needs indicators/predicates, but must remain whitelisted.  
Implications: Parser may allow call syntax, but validator must restrict targets.

- Expression calls are allowed only for whitelisted **pure deterministic** functions (e.g., indicators such as `ema(close, 50)`).
- User-defined functions are forbidden.
- Calls must be side-effect free and must not access external systems.

---

# Chapter 12 — Static Type System and Validation

## 12.1 Type system goals

**Status: LOCKED**  
Rationale: Strong typing is required by thesis constraints.  
Implications: Types must gate actions and prevent ambiguous computations.

Goals:
- prevent nonsensical comparisons (price vs percent),
- enforce correct units and rounding policies,
- prevent passing wrong argument types to verbs and indicators,
- enable safe evolution of rule packs with diagnostics.

## 12.2 Baseline types (v0 scope)

**Status: CURRENTLY DECIDED**  
Rationale: Needed for v0.2 typed authoring roadmap.  
Implications: Implement these types early.

Primitive-like:
- `Bool`
- `Int`
- `Decimal` (TBD exact representation)
- `String`
- `Timestamp`
- `Duration`

Domain types (initial set):
- `Price`
- `Quantity`
- `Percent`
- `Money`
- `Symbol`
- `Exchange`
- `Segment`

## 12.2.1 Type rules (selected, v0.x)

**Status: PROVISIONAL**  
Rationale: Needed to implement v0.2 type checking; exact coercion rules must be conservative.  
Implications: Prefer “no implicit coercions” to preserve determinism.

Principles:
- **No implicit unit coercions** (e.g., `Price` is not `Decimal`).
- Comparisons require compatible types (`Price` vs `Price`, not `Price` vs `Percent`).
- Boolean operators require `Bool`.

Selected operator typing (initial intent):
- `Price + Price -> Price`
- `Price - Price -> Price`
- `Price * Decimal -> Price`
- `Price / Decimal -> Price`
- `Price / Price -> Decimal` (dimensionless ratio; may be useful; PROVISIONAL)
- `Percent * Price -> Price` (TBD; could be allowed later; keep conservative in v0.2)
- `Decimal * Decimal -> Decimal`, etc.

Percent literal handling:
- If `%` literal exists, `0.2%` types as `Percent` with value `0.002` (PROVISIONAL).

## 12.2.2 Context object field types (minimum)

**Status: PROVISIONAL**  
Rationale: Required for implementation and examples; exact schema evolves with domain model.  
Implications: Lock a minimal field set for v0.3.

Intended `underlying` context fields:
- `bar.open/high/low/close: Price`
- `bar.volume: Quantity` (or `Int`; TBD)
- `bar.time: Timestamp`
- `session.is_regular: Bool` (or similar)
- `data.is_fresh: Bool` (data quality predicate)

Intended `option` context fields (v1.1+; implemented as typed schema in v1.1-A and runnable in v1.1-B):
- `option.contract_id: String` (canonical broker-agnostic id)
- `option.strike: Price`
- `option.expiry: Date` (strict ISO date `YYYY-MM-DD` for contract expiry)
- `option.type: String` (canonical right values: `CALL`/`PUT`)
- `option.lot: Quantity` (lot size)
- quote fields (optional): `option.bid/ask/last/close: Price`
- IV/greeks (optional):
  - `option.iv: Percent` (ratio, e.g. `0.25` == 25%)
  - `option.delta/gamma/theta/vega: Decimal`

Runner note (v1.1-B, implemented):
- `sigmadsl run --context option --input options.csv --rules rules.sr`
- if multiple `contract_id` values exist in the input, the runner requires an explicit `--contract-id` (fail closed)
- snapshot usability is enforced conservatively (see `docs/options_contract_context.md`)

Canonical option contract identifier (v1.1-A, implemented):

```
OPT:<VENUE>:<UNDERLYING>:<EXPIRY>:<STRIKE>:<RIGHT>:<LOT>
```

Example:

```
OPT:NSE:TCS:2026-01-29:100:CALL:150
```

Validation rules (v1.1-A):
- expiry is strict `YYYY-MM-DD` (no guessing)
- strike is a decimal with at most 2 fractional digits
- right is `CALL` or `PUT` (parser may normalize `CE/PE` into `CALL/PUT`)
- lot is an integer > 0

See `docs/options_contract_context.md` for the implemented model and guard philosophy.

Intended `chain` context fields (v1.2+; DEFERRED):
- `chain.as_of: Timestamp`
- `chain.is_fresh: Bool`
- derived metrics like `chain.pcr_oi: Decimal` (DEFERRED)

## 12.7 Compile-time validation pipeline (what “validate” means)

**Status: CURRENTLY DECIDED**  
Rationale: The product depends on reliable validation in v0.1–v0.2.  
Implications: Compiler must produce deterministic results for each stage.

Validation stages (conceptual):
1) Lex/parse → AST
2) AST structural validation (rule blocks, branches, `then` lines)
3) Forbidden construct validation (assignments/loops/functions/imports)
4) Type checking
5) Profile compliance checks (signal/intent/plan/risk; scaffolding early)
6) (Later) dependency/import resolution and pack compatibility checks

## 12.3 Rounding and precision policy

**Status: TBD**  
Rationale: Affects determinism and indicator results.  
Implications: Must be resolved before v0.5 indicators are trusted.

Constraints:
- No floating-point nondeterminism in outputs.
- Rounding must be explicit and consistent across OS/CPU.

---

# Chapter 13 — Semantics: Deterministic Rule Evaluation

## 13.1 Execution context and phases

**Status: CURRENTLY DECIDED**  
Rationale: Required for a deterministic evaluator (v0.3–v0.4).  
Implications: Runtime must expose a stable phase model.

Conceptual phases (high-level):
1) Input event ingestion (bar/snapshot).
2) Context binding (underlying / option / chain).
3) Rule evaluation (predicates).
4) Action emission (verbs) → decision outputs.
5) Risk enforcement phase (for risk profile; earlier versions may stub).
6) Logging/tracing.

## 13.1.1 Deterministic evaluation algorithm (v0.3-A)

**Status: CURRENTLY DECIDED (v0.3-A implementation)**  
Rationale: v0.3 is the first runnable evaluator slice; ordering must be explicit and golden-tested.  
Implications: Any change to ordering or trace shape is a versioned behavior change.

Given an event series `E[0..N-1]` and a compiled rule set `P`:

1) Bind context objects from each `E[i]` (v0.3-A: `underlying` bar-only context; see 14.4.1).
2) Establish a deterministic rule evaluation order:
   - primary: file path (lexicographic) as a cross-file tie-breaker until imports exist,
   - secondary: source order within file,
   - tertiary: rule name (lexicographic).
3) For each event `E[i]` in order:
   - For each rule `R` in order:
     - Evaluate branch predicates in source order: `when`, then each `elif`, then optional `else`.
     - The first matching branch (predicate `true`) selects its `then` actions.
     - If no branch matches and no `else`, the rule emits no actions.
     - Each `then` verb call emits a structured decision or annotation (v0.3-A supports a minimal verb set).
4) Emit:
   - `decisions` (ordered by event → rule → action) and
   - `trace` capturing the evaluation in the same deterministic order.

## 13.4 Trace and reason codes (v0.3-A)

**Status: CURRENTLY DECIDED**  
Rationale: Explainability is first-class and must exist by v0.3–v0.4.  
Implications: Trace schema must be stable enough for golden tests.

Each evaluation produces a trace containing at minimum:

- engine version pin (runtime identifier),
- per-event evaluation records (ordered by event index), including:
  - event identity (`symbol`, `index`, `timestamp`),
  - per-rule evaluation records (ordered by deterministic rule order):
    - rule name + context,
    - branch predicate outcomes (`true`/`false`; `unknown` remains TBD),
    - selected branch (`when`/`elif`/`else`/none),
    - verbs invoked with arguments (after type checking),
    - emitted decision IDs (if any).

Reason codes:
- Every emitted decision should include a short machine-friendly `reason` string.
- Reason codes must be stable for tests and dashboards.

## 13.5 Side effects and idempotency

**Status: CURRENTLY DECIDED**  
Rationale: Effects must remain within “planned outputs”, never external actions.  
Implications: Runtime must be pure relative to external systems.

- Verb invocation is the only “effect”, and it only produces structured outputs.
- Evaluation must not perform IO, network calls, or non-deterministic operations.
- Re-evaluating the same event in replay must yield identical decisions and traces.

## 13.2 Condition semantics and unknowns

**Status: TBD**  
Rationale: `docs/dsl.md` explicitly calls out a possible three-valued logic.  
Implications: Must be decided early; affects “fail closed” behavior.

Constraints already known:
- Missing/unknown data should not accidentally trigger trades.

Candidate policies (to resolve):
- 2-valued logic with “missing data causes condition = false unless guarded”.
- 3-valued logic (`true/false/unknown`) where `unknown` propagates and must be handled explicitly.

## 13.3 Conflict resolution and priority

**Status: PROVISIONAL**  
Rationale: Must be deterministic; exact strategy can evolve.  
Implications: Implement v0.3 with a simple, stable tie-breaker; lock later.

Minimum deterministic requirements:
- Rule evaluation order is deterministic (e.g., source order).
- If multiple rules emit decisions of the same kind, merges must be deterministic and explainable.

---

# Chapter 14 — DSL Constructs: Rules, Contexts, and Guards

## 14.1 Rule definition (conceptual)

**Status: CURRENTLY DECIDED**  
Rationale: Needed to author and validate rules early.  
Implications: v0.1 parser must support rule blocks.

Each rule has:
- name (stable identifier / string),
- optional description/tags (PROVISIONAL),
- a context binding: `underlying`, `option`, or `chain`,
- one or more condition branches,
- a `then` block of action verbs.

## 14.2 Context binding

**Status: CURRENTLY DECIDED**  
Rationale: Context separation is central to the architecture (Ch 4.4, Ch 14.2).  
Implications: Evaluator must bind context deterministically.

Contexts:
- `underlying`: equity/index instrument context.
- `option`: option contract context (v1.1+).
- `chain`: option chain snapshot context (v1.2+).

## 14.3 Guards and preconditions

**Status: PROVISIONAL**  
Rationale: Guards are necessary, but the exact predicate catalog evolves.  
Implications: Provide a minimal, deterministic guard set early.

Examples of guard categories:
- session guards: market open/close windows,
- liquidity guards (later),
- data quality guards: “inputs present and not stale”.

## 14.4 Context object model (read-only)

**Status: CURRENTLY DECIDED**  
Rationale: Required to prevent “hidden state” and enforce no assignments.  
Implications: Evaluator exposes only read-only structured objects.

Rules do not create variables. They read from **context objects** provided by the runtime.

### 14.4.1 `underlying` context (v0.3+)

**Status: CURRENTLY DECIDED (v0.3-A implementation)**  
Rationale: A runnable evaluator requires a concrete v1 underlying context surface.  
Implications: Treat these field names as part of the v0.3 boundary; additions are allowed, renames are breaking.

v0.3-A provides a minimal read-only field environment (both dotted and plain “series” aliases):

- `bar.open`, `bar.high`, `bar.low`, `bar.close`: Price
- `bar.volume`: Quantity
- `bar.time`: Timestamp (v0.3-A treats this as an opaque string identity)
- `session.is_regular`: Bool
- `data.is_fresh`: Bool
- `underlying.return_5m`: Percent (PROVISIONAL; used in examples/fixtures)

Series aliases (for lookback helpers like `highest(close, 20)`):

- `open`, `high`, `low`, `close`: Price
- `volume`: Quantity

Note: structured objects like `instrument` (symbol/exchange/segment) remain planned; v0.3-A evaluation traces still carry `symbol`
as the event identity.

### 14.4.2 `option` context (v1.1+)

**Status: DEFERRED**  
Rationale: Options contract context is delivered in v1.1.  
Implications: Keep `underlying` semantics stable; add `option` later.

Intended objects:
- `option` (option contract identifiers + snapshot fields)
- `underlying` (link to underlying instrument context)
- `data`, `session`

### 14.4.3 `chain` context (v1.2+)

**Status: DEFERRED**  
Rationale: Chain context is delivered in v1.2.  
Implications: Chain snapshot semantics must be atomic and deterministic.

Intended objects:
- `chain` (snapshot + derived metrics; derived metrics deferred)
- `underlying`, `data`, `session`

## 14.5 Deterministic lookbacks and historical access

**Status: PROVISIONAL**  
Rationale: Needed for indicators and “prior high” style rules; must remain deterministic.  
Implications: Any historical access must be explicitly windowed and aligned.

Constraints:
- Rules may reference historical values only through whitelisted deterministic functions:
  - e.g., `highest(close, 20)`, `ema(close, 50)` (v0.5+ for indicators),
  - not via loops or ad-hoc indexing.
- Window alignment policy (bar-close vs intrabar) must be defined and logged.

## 14.6 Rule metadata (tags, priority, compatibility)

**Status: PROVISIONAL**  
Rationale: Useful for libraries and governance, but not required for v0.1 MVP parsing.  
Implications: Introduce incrementally with stable schema.

Planned metadata fields (non-exhaustive):
- `tags`: list of strings (e.g., `["equity", "screener"]`)
- `priority`: integer (used in deterministic tie-breakers; carefully)
- `since`: compatibility marker for minimum engine version

## 14.7 Built-in predicates and functions (initial catalog shape)

**Status: PROVISIONAL**  
Rationale: Necessary to write runnable examples; the exact catalog evolves with versions.  
Implications: Start with a small whitelisted set; extend only with tests and docs.

### 14.7.1 Built-in predicates (v0.3–v0.4)
- `data.is_fresh: Bool` — true when required inputs are present and within staleness thresholds (TBD thresholds).
- `session.is_regular: Bool` — true during regular trading session (TBD exact India-market calendar behavior).

### 14.7.2 Built-in historical functions (v0.3–v0.4 minimal, v0.5+ expanded)
- `highest(series, length) -> Price|Decimal` (type depends on series)
- `lowest(series, length) -> Price|Decimal`

Indicator functions (v0.5+; DEFERRED for v0.x MVP):
- `ema(series, length) -> Price|Decimal`
- `rsi(series, length) -> Decimal`
- `atr(length) -> Price`

Constraints:
- All functions must be deterministic, side-effect free, and version-pinned (Ch 16.1.1).
- No user-defined functions.

---

# Chapter 15 — Actions as Verbs: Effect Model

## 15.1 Action philosophy: plan, don’t execute

**Status: LOCKED**  
Rationale: Non-negotiable boundary (Ch 13.5, Ch 2.6.3).  
Implications: Verbs produce decisions/intent/plans, not broker execution.

Verbs are the **only** allowed “effectful” constructs in the DSL. They:
- emit decisions (signals/intents/constraints/plans),
- are typed and validated,
- are logged in traces,
- are deterministic and idempotent by design (details PROVISIONAL).

## 15.2 Verb categories (initial catalog shape)

**Status: PROVISIONAL**  
Rationale: Verb catalog grows with versions; signatures evolve with implementation.  
Implications: Implement minimal verbs in v0.3–v0.4; expand later.

Planned categories (from `docs/dsl.md` Ch 15.2):
- **Intent verbs:** declare/adjust/cancel intent (v2.0 focus; scaffolding in v1.0).
- **Risk verbs:** cap exposure, block trades, reduce size (v1.0+).
- **Execution planning verbs:** place plan, route, slice (v2.0).
- **Position management verbs:** `move_stop`, `start_trailing_stop` (v2.0; requires position state).

Minimal early verbs (v0.3–v0.4):
- `emit_signal(...)` (PROVISIONAL naming; emits a `SignalDecision` object).
- `annotate(...)` (adds trace annotations without changing decisions).

## 15.3 Verb invocation syntax (statement-level)

**Status: CURRENTLY DECIDED**  
Rationale: Keeps effect syntax explicit and reviewable.  
Implications: Parser should treat verb calls as a distinct statement category.

Verb calls appear only in `then` lines:
```sr
then emit_signal(kind="BUY", reason="breakout")
then annotate(note="skipped_due_to_data")
```

Constraints:
- Verbs are only allowed in `then` blocks.
- Each verb has a fixed, typed signature.
- Unknown verbs are compile-time errors.

## 15.4 Decision output types (conceptual)

**Status: CURRENTLY DECIDED (v1.0-A implementation)**  
Rationale: v1.0 requires a stable, downstream-consumable decision contract.  
Implications: Output fields are versioned; changes require goldens + backward-compat checks.

Core conceptual decision categories:
- `SignalDecision`: classification outputs (labels, strengths, reasons).
- `IntentDecision`: strategy intent outputs (declare/cancel) (outputs only in v1.0-A; planning is later).
- `RiskConstraintDecision`: constraints/blocks with reason codes (outputs only in v1.0-A; enforcement is later).
- `PlanDecision`: broker-agnostic plan outputs (DEFERRED until v2.0).

Minimum fields every decision should carry:
- `schema`, `schema_version` (decision schema identifiers)
- `id` (deterministic id; v0.x uses sequential IDs per run: `D0001`, `D0002`, …)
- `kind` (decision kind)
- `profile` (signal/intent/risk)
- `verb` (the verb that produced the decision)
- event linkage: `symbol`, `event_index`, `timestamp`
- `trace_ref` (stable linkage into trace data)

### 15.4.1 v1.0-A runner output (`decisions.jsonl`)

**Status: CURRENTLY DECIDED (v1.0-A implementation)**  
Rationale: v1.0 establishes a stable decision contract across `run`/`replay`/`diff`.  
Implications: Decision output schema is versioned and protected by goldens.

`sigmadsl run` emits decisions as JSON lines (one decision per line) in deterministic order.

Current v1.0-B decision JSON fields (minimum set):

- `schema`: `sigmadsl.decision`
- `schema_version`: `1.0-b`
- `id`
- `kind`: `signal` | `annotation` | `intent` | `constraint`
- `profile`: `signal` | `intent` | `risk`
- `verb`
- `rule_name`, `context`
- `symbol`, `event_index`, `timestamp` (timestamp treated as an opaque identity)
- `trace_ref = { event_index, rule_name, action_index }`
- `enforcement = { status, blocked_by }`
- `event_index` (0..N-1 within the evaluated series)

Verb-specific fields:

- for `emit_signal` decisions:
  - `signal_kind` (string)
  - `reason` (string or null)
  - `strength` (decimal string or null)
- for `annotate` decisions:
  - `note` (string)

Notes:
- Trace is produced internally in v0.3 but is not emitted as a separate persisted log yet (replay logging is v0.4).
- Multi-symbol series evaluation and decision ID stability across merges are deferred.

## 15.5 Idempotency and merging rules (effect semantics)

**Status: PROVISIONAL**  
Rationale: Essential for deterministic outcomes; exact merge semantics need real examples.  
Implications: Define simple rules early; tighten with use cases.

Intended behavior:
- Within a single event evaluation, identical verb calls may either:
  - be emitted as duplicates (discouraged), or
  - be deduplicated deterministically (preferred).

Open questions:
- How to define “identical” (same verb + same args + same context)?
- Whether deduplication is part of the language semantics or a downstream consumer concern.

## 15.6 Extending the verb catalog

**Status: CURRENTLY DECIDED**  
Rationale: Extensibility is necessary but must remain safe.  
Implications: Add verbs only through engine releases, not user code.

Rules:
- Users cannot define verbs.
- New verbs are introduced only via engine versions with:
  - schema/version updates,
  - documentation,
  - tests and golden traces.

---

# Chapter 16 — Indicator and Feature Framework (Deterministic)

## 16.1 Indicator availability sequencing

**Status: CURRENTLY DECIDED**  
Rationale: Roadmap pins indicators to v0.5 (not earlier).  
Implications: Keep early versions minimal; don’t overbuild.

- v0.1–v0.4: keep features minimal (basic bar fields and simple comparisons).
- v0.5: add deterministic indicator registry (EMA/RSI/ATR/VWAP) with pinned versions and golden numeric tests.
- v1.x+: add options features and chain aggregations.

## 16.1.1 Indicator registry principles

**Status: CURRENTLY DECIDED**  
Rationale: Required to prevent “indicator drift” across time and machines.  
Implications: Indicator implementations must be versioned and referenced explicitly.

Principles:
- Indicators are **pure functions** of the input series and configuration.
- Indicator computations must be deterministic with explicit rounding.
- Each indicator has a version identifier used in logs/replay.
- The engine should record which indicator versions were used in a run.

## 16.1.2 Initial built-in indicator set (v0.5)

**Status: CURRENTLY DECIDED (v0.5-A implementation)**  
Rationale: v0.5-A ships a small indicator set; semantics must be pinned and covered by goldens.  
Implications: Any semantic change requires a version bump (e.g., `ema@2`) and updated goldens.

Indicators are called as **pure expression functions** and are **version-pinned** by the engine.
The engine records indicator pins in the run log (Ch 6.3.1) using `name@version` keys.

Implemented built-ins (v0.5-A):
- `ema(series, length) -> Price`
  - exponential moving average with `k = 2 / (length + 1)`
  - aligned to bar-close; uses the history up to and including the current bar
  - warmup: allowed (computes on partial history)
- `rsi(series, length) -> Percent` (ratio in `[0, 1]`)
  - computed from consecutive differences over the last `(length-1)` diffs (partial if fewer)
  - special cases:
    - avg_gain == 0 and avg_loss == 0 => 0.5
    - avg_loss == 0 => 1.0
    - avg_gain == 0 => 0.0
- `atr(length) -> Price`
  - uses `high/low/close` from the bar stream (no explicit series args in v0.5-A)
  - true range (TR) per bar:
    - `max(high-low, abs(high-prev_close), abs(low-prev_close))`
  - ATR is the simple moving average of TR over the last `length` bars (partial if fewer)
- `vwap() -> Price` and `vwap(length) -> Price`
  - uses `close` as the price and `volume` for weights
  - `vwap()` uses all bars up to the current bar; `vwap(length)` uses the last `length` bars (partial if fewer)
  - if `sum(volume) == 0` over the window, VWAP returns the last close (conservative)

## 16.2 Deterministic windows

**Status: CURRENTLY DECIDED (v0.5-A implementation)**  
Rationale: Indicators require explicit alignment and warmup behavior for determinism and replay.  
Implications: These rules are part of the v0.5 contract and are protected by numeric goldens.

v0.5-A window policy:
- **Alignment**: bar-close aligned; windows include the current bar.
- **Warmup / insufficient history**: allowed; indicators compute over available history in a deterministic way.
- **Missing/invalid inputs**:
  - in v0.5-A, the runner input model requires OHLCV fields; missing required columns is a validation error.
  - indicator-specific edge cases are defined per indicator (e.g., `vwap` when sum(volume)==0).
- **Rounding policy**:
  - indicator outputs are quantized to **8 decimal places**, rounding **half up**.
  - this rounding policy is pinned and must not depend on platform defaults.
- **Caching**:
  - per-run in-memory caching is permitted as an optimization
  - cache keys must include the pinned indicator id (`name@version`), parameters, and event index
  - caching must not change semantics (a cache miss vs hit must produce identical results)

## 16.3 Options and chain features (later)

**Status: DEFERRED**  
Rationale: Delivered in v1.1+ and v1.2+.  
Implications: Do not design-lock without real chain fixtures.

Planned later features:
- option-level features: IV rank/percentile, greeks-based features (Ch 16.3)
- chain-level aggregations and cross-strike features (Ch 16.4)

---

# Chapter 17 — Execution Planning Layer (Broker-agnostic)

## 17.1 Planning separation

**Status: LOCKED**  
Rationale: Separation is mandatory; broker execution is out of scope.  
Implications: DSL outputs plan IR; adapters execute outside.

## 17.2 Planning semantics (high-level)

**Status: DEFERRED**  
Rationale: Delivered in v2.0; overspec now is risky.  
Implications: Define the plan IR after intent verbs are stable.

Constraints already known:
- plans must be deterministic and traceable,
- plans are broker-agnostic abstractions (entry/exit/size primitives),
- no network/broker calls from DSL runtime.

---

# Chapter 18 — Risk Management and Enforcement

## 18.1 Risk philosophy: fail closed

**Status: LOCKED**  
Rationale: Explicit in thesis (Ch 18.1) and required for safety.  
Implications: Missing data or uncertain situations should block, not allow.

Risk rules:
- operate as a separate phase from signal/intent generation,
- can block or constrain decisions/plans,
- must emit reason codes and traces.

## 18.2 Minimal risk scope (v1.0)

**Status: CURRENTLY DECIDED (v1.0-B implementation)**  
Rationale: v1.0 requires a minimal, deterministic, fail-closed risk gate for equity outputs.  
Implications: Risk runs as a separate phase and must be replayable.

Implemented constraints (Sprint v1.0-B scope):
- risk is evaluated as a separate phase after primary decision generation.
- risk rules emit constraint decisions:
  - `block(reason=...)`: blocks all primary decisions at the same event index.
  - `constrain_max_position(quantity=..., ...)`: blocks `declare_intent(...)` when `quantity` exceeds the max.
- blocked decisions are represented via `enforcement={status, blocked_by}`.
- unsupported/unknown constraint kinds are treated as block-all (fail-closed).

Current applicability boundary:
- event-local only (constraints apply to decisions at the same event index).
- no portfolio-wide stateful enforcement yet (deferred).

---

# Chapter 19 — Backtesting, Simulation, and Live Parity

## 19.1 Parity principle

**Status: CURRENTLY DECIDED**  
Rationale: Core to determinism and trust (Ch 19).  
Implications: Backtest and replay should share the same evaluator.

Parity means:
- the same rule pack evaluated by the same engine should behave identically across:
  - “historical run” mode,
  - “replay” mode,
  - (later) simulated-live modes,
except for explicitly modeled differences (fees/slippage models), which must be deterministic and logged.

## 19.2 Fill and slippage models

**Status: DEFERRED**  
Rationale: DSL core must exist before modeling execution effects.  
Implications: Keep early versions focused on decisions + traces.

---

# Chapter 20 — AI Integration Layer (Deterministic + Guarded)

## 20.1 Allowed AI roles

**Status: DEFERRED**  
Rationale: AI must not compromise determinism; roadmap introduces later.  
Implications: If built, AI only suggests changes; it never executes trades.

Guardrails (already known):
- “suggest → validate → simulate → approve” workflow only.
- all AI outputs must pass the same compiler/validator gates as human-authored rules.

---

# Chapter 21 — Developer Tooling: Compiler, Linter, CLI

## 21.1 CLI-first toolchain

**Status: CURRENTLY DECIDED**  
Rationale: Roadmap is CLI-first; editor work is deferred.  
Implications: CLI behavior must be stable and testable with goldens.

Planned commands (shipped incrementally; see `docs/dsl_proj_plan.md`):
- `validate` (v0.1)
- `lint` (v0.2)
- `run` + `explain` (v0.3)
- `replay` + `diff` (v0.4)
- `pack` (v0.6)
- `report` (v1.0)
- `plan` (v2.0)

v0.4-A introduces the replay surface (and v0.5/v1.0 update the run log schema):

- `run --log-out runlog.json` writes a self-contained run log (schema `sigmadsl.runlog` `1.0-b`)
- `replay --log runlog.json` re-evaluates from embedded snapshots and re-emits decision output deterministically

v0.4-B concretizes the debugging surface:

- `explain --decision-id D0003 ...` prints a stable “why it fired” summary + the emitting trace record
- `explain --rule "..." --event-index N ...` prints a stable “why it did not fire” view using the per-rule trace at that event
- `diff run_a.json run_b.json` compares two run logs deterministically (decision counts + first divergence)

v0.5-B adds lightweight pack introspection:

- `profile path/to/rules/` prints a stable summary of:
  - which indicators are referenced (pinned versions),
  - which functions are called,
v1.0-B adds risk gating as a separate phase:

- `run --risk-rules path/to/risk_pack` applies deterministic constraints to prior decisions
- risk sources are embedded in the run log for replay
  - which verbs are used.

v0.6-A adds deterministic imports and module layout:

- top-level `import ...` declarations are supported (Ch 11.3)
- `validate`, `lint`, `run`, and `profile` resolve the deterministic import closure from the entry path
- missing modules, ambiguous modules, and cycles are rejected at compile time

v0.6-B adds local packaging:

- `pack path --out pack.zip --name NAME --version X.Y.Z` creates a deterministic bundle
- `validate --pack pack.zip` verifies manifest + hashes + embedded source validity

v1.0-C adds reporting:

- `report --input decisions.jsonl` aggregates outcomes per rule / symbol / day from a decision JSONL stream
  - report consumes the stable decision schema (`sigmadsl.decision` `1.0-b`) emitted by `run` / `replay`
  - output is deterministic and golden-testable

## 21.2 Diagnostics requirements

**Status: CURRENTLY DECIDED**  
Rationale: Deterministic diagnostics are required for reproducibility.  
Implications: Diagnostics output must be stable and golden-tested.

Diagnostics must include:
- file path, line, column
- error code
- short message
- (optional) hint / fix suggestion

---

# Chapter 22 — Visualization, UX, Operator Interfaces

**Status: DEFERRED**  
Rationale: Not required for MVP; depends on stable decision schema.  
Implications: Keep outputs machine-readable for later UI integration.

---

# Chapter 23 — Rule Library Model, Reuse, and Governance

## 23.1 Library model intent

**Status: CURRENTLY DECIDED**  
Rationale: Reuse is core to product value and roadmap (v0.6).  
Implications: Design packaging so rule packs are portable and versioned.

Rule packs should support:
- copy/modify/reuse,
- deterministic imports,
- semantic versioning and compatibility metadata,
- hashing for provenance.

Details (pack manifest fields, compatibility checks): PROVISIONAL until v0.6.

## 23.2 Library layout and imports (v0.6-A)

**Status: CURRENTLY DECIDED (v0.6-A implementation)**  
Rationale: A library model is required before packaging can be made reliable.  
Implications: Layout rules must be simple and deterministic; validation must fail closed.

v0.6-A establishes:
- a deterministic module naming scheme from filesystem layout (Ch 11.3.2)
- deterministic `import ...` resolution (Ch 11.3.1)
- dependency graph validation with cycle detection

Notes:
- v0.6-A does **not** ship pack manifests or bundling; it only provides the deterministic library/module substrate.
- v0.6-B will add pack metadata (name/version/compatibility/hashes) and a bundle artifact (`sigmadsl pack`).

## 23.3 Local pack artifact (v0.6-B)

**Status: CURRENTLY DECIDED (v0.6-B implementation)**  
Rationale: A local bundle format is required before any governance/publishing can be meaningful.  
Implications: Pack contents and manifest must be deterministic; integrity must be verifiable.

v0.6-B introduces a deterministic local pack artifact:

- container: zip file (stored; stable ordering)
- contents:
  - `manifest.json`
  - `rules/...` (bundled `.sr` sources for the import closure)

Manifest requirements (v0.6-B):
- schema identifiers:
  - `schema = "sigmadsl.pack"`
  - `schema_version = "0.6-b"`
- metadata:
  - `name`, `version`
  - `compat.dsl_spec` (e.g., `dsl_v0.6`)
- closure contents:
  - `modules[]` mapping `{name, path}`
  - `files[]` list `{path, sha256, bytes_len}` for integrity verification

Validation requirements:
- `sigmadsl validate --pack <file>` must:
  - validate manifest schema/version
  - verify file presence and sha256 hashes
  - validate embedded sources (parse/type + import graph)
  - fail closed on corruption/tampering

Note:
- guardrail/profile checks remain in `sigmadsl lint` (no `lint --pack` in v0.6-B)

---

# Chapter 24 — Security, Reliability, Operations

**Status: DEFERRED**  
Rationale: Runtime is offline/CLI-first initially; production ops comes later.  
Implications: Still enforce “no external calls during evaluation”.

Minimum security requirement (LOCKED):
- The DSL runtime must not allow arbitrary IO/network calls from rule evaluation.

---

# Chapter 25 — Reference Implementations and Contracts

## 25.1 Contracts over integrations

**Status: CURRENTLY DECIDED**  
Rationale: Keeps DSL independent and integrable.  
Implications: Define schemas and adapter contracts without building full integrations.

Planned contracts:
- market data adapter contract (input events schema),
- plan adapter contract (output plan schema),
- risk engine contract (phase separation and inputs/outputs).

Schemas: PROVISIONAL; must stabilize by v1.0+.

---

# Chapter 26 — Performance Engineering

**Status: DEFERRED**  
Rationale: Correctness and determinism first (Ch 6); performance tuning later (Ch 26).  
Implications: Avoid premature optimization.

---

# Chapter 27 — Worked Examples (required)

> Note: Example syntax is **Python-shaped** and respects **no loops / no arbitrary assignments / verbs-only actions**.  
> Where syntax is not yet locked, examples are marked PROVISIONAL.

## 27.1 DSL Writing Style Guide (required)

**Status: CURRENTLY DECIDED**  
Rationale: Ensures rule packs remain readable and reviewable.  
Implications: Linter should enforce parts of this over time.

Guidelines:
- Rule names: stable, descriptive, prefixed by domain (e.g., `EQ:` / `OPT:` / `CHAIN:`).
- Keep conditions readable; prefer guard predicates over deep boolean nesting.
- One conceptual intent per rule (avoid mega-rules).
- Use explicit `reason` fields on verbs to improve explainability.
- Prefer deterministic thresholds and named constants (TBD: constant mechanism) over magic numbers.

Good (readable, guarded):
```sr
rule "EQ: Breakout Above Prior High" in underlying:
    when session.is_regular and data.is_fresh and bar.close > prior_high(20):
        then emit_signal(kind="BUY", reason="breakout_20d_high")
```

Bad (opaque, unguarded):
```sr
rule "r1" in underlying:
    when bar.close > 123.45 and rsi(14) < 40 and (a and b and c and d and e):
        then emit_signal(kind="BUY")
```

## 27.2 Forbidden Constructs (required)

**Status: LOCKED**  
Rationale: Prevents turning DSL into Python and preserves determinism.  
Implications: Must be rejected at compile time (v0.2).

Forbidden:
- Variable assignment and mutation (`x = ...`, `x += ...`, etc.).
- Loops (`for`, `while`) and recursion.
- User-defined functions (`def ...`) and lambdas.
- Imports of arbitrary libraries or filesystem/network access.
- Access to wall clock time (`now()`) and randomness (`random()`).
- Reflection/metaprogramming (dynamic attribute access, eval/exec-like behavior).
- Unbounded collections and arbitrary map/reduce patterns (TBD: what limited collections are allowed).

Allowed (strictly whitelisted):
- Built-in deterministic predicates, indicators, and verbs.
- Literal constants (numbers/strings/booleans).
- Structured access to context objects (bar fields, option fields, chain rows).

## 27.3 Worked Example — Equity signal rule (v0.3+)

**Status: PROVISIONAL**  
Rationale: Semantics are clear; exact syntax will be locked during v0.1–v0.3.  
Implications: Use as target for early compiler + evaluator tests.

```sr
rule "EQ: Close Above 20-Bar High" in underlying:
    when session.is_regular and data.is_fresh and bar.close > highest(close, 20):
        then emit_signal(kind="BULLISH", strength=0.7, reason="close_above_20bar_high")
    else:
        then annotate(note="no_signal")
```

Expected behavior:
- Produces a deterministic `SignalDecision` for each bar-close event where the predicate is true.
- Trace includes predicate outcomes and the emitted signal.

## 27.4 Worked Example — Equity screening rule (batch run; v0.4 MVP)

**Status: CURRENTLY DECIDED**  
Rationale: MVP requires “equity rule runner + trace + replay” (v0.4).  
Implications: `run` and `replay` must support this workflow.

```sr
rule "EQ: Screener — Trend + Low Volatility" in underlying:
    when data.is_fresh and bar.close > ema(close, 50) and atr(14) < 0.02 * bar.close:
        then emit_signal(kind="SCREEN_PASS", reason="trend_low_vol")
    else:
        then emit_signal(kind="SCREEN_FAIL", reason="missing_conditions")
```

Expected product behavior:
- User runs: `sigmarule run --rules screener_pack/ --input bars.csv`
- Output: JSON lines with `SCREEN_PASS`/`SCREEN_FAIL` per symbol per event, with trace.
- Replay reproduces identical outputs (v0.4).

## 27.5 Worked Example — Option contract rule (v1.1+)

**Status: DEFERRED**  
Rationale: Options contract context delivered in v1.1 per roadmap.  
Implications: Keep as future target; do not implement in v0.x.

```sr
rule "OPT: Select ATM Call, Weekly Expiry" in option:
    when option.is_weekly and option.is_atm and data.is_fresh:
        then emit_signal(kind="OPT_CANDIDATE", reason="weekly_atm_call")
```

## 27.6 Worked Example — Option premium behavior rule (v1.1+)

**Status: DEFERRED**  
Rationale: Depends on options snapshots and IV/greeks inputs.  
Implications: Keep semantics minimal until data model is stable.

```sr
rule "OPT: Rising IV With Stable Underlying" in option:
    when data.is_fresh and abs(underlying.return_5m) < 0.2% and option.iv_change_5m > 1.0%:
        then emit_signal(kind="IV_EXPANSION", reason="iv_up_underlying_flat")
```

## 27.7 Worked Example — Option chain-based classification rule (v1.2+)

**Status: DEFERRED**  
Rationale: Chain context delivered in v1.2 per roadmap.  
Implications: Must wait for chain snapshot atomicity and derived metrics definitions.

```sr
rule "CHAIN: Put-Call OI Imbalance" in chain:
    when chain.is_fresh and chain.pcr_oi > 1.3 and chain.oi_change_puts > chain.oi_change_calls:
        then emit_signal(kind="BEARISH_SENTIMENT", reason="pcr_oi_high_put_oi_rising")
```

## 27.8 Worked Example — Management rule using action verbs (v2.0+)

**Status: DEFERRED**  
Rationale: Management verbs require position/intent state and plan separation (v2.0).  
Implications: Must not be attempted before intent→plan is stable.

```sr
rule "MGMT: Start Trailing Stop After 1R" in underlying:
    when position.is_open and position.unrealized_r_multiple >= 1.0:
        then start_trailing_stop(distance=1.0 * atr(14), reason="lock_in_after_1R")
```

## 27.9 Worked Example — Intentionally invalid rule (and why)

**Status: LOCKED**  
Rationale: Demonstrates forbidden constructs clearly.  
Implications: v0.2 must reject this with deterministic diagnostics.

```sr
rule "INVALID: Assignment And Loop" in underlying:
    when true:
        then
            x = bar.close            # forbidden: assignment
            for i in range(10):      # forbidden: loop
                emit_signal(kind="BUY")
```

Expected diagnostics (shape; exact codes TBD):
- error: assignments are not allowed in Sigma Rule DSL
- error: loops are not allowed in Sigma Rule DSL

---

# Chapter 28 — Limitations, Tradeoffs, Future Work

## 28.1 Tradeoffs vs general-purpose languages

**Status: CURRENTLY DECIDED**  
Rationale: Required to maintain scope and safety.  
Implications: Stakeholders must accept reduced expressiveness for determinism.

Sigma Rule DSL intentionally sacrifices:
- arbitrary computation,
- custom functions,
- loops and complex state,
in exchange for:
- deterministic behavior,
- strong validation,
- explainable outputs and replay.

---

# Chapter 29 — What this document does NOT guarantee yet (required)

**Status: TBD**  
Rationale: Honesty about uncertainty prevents accidental lock-in.  
Implications: These areas must be resolved through early implementation and explicit design choices.

This spec does **not** yet guarantee:
- final concrete grammar (exact keywords, exact rule header syntax, exact metadata syntax),
- final numeric type/rounding policy and tick-size handling,
- final missing-data semantics (`unknown` policy),
- complete verb catalog and final verb signatures,
- final decision output schema and versioning strategy,
- final option/chain schemas and derived metric definitions,
- final planning IR schema (v2.0) and its adapter contracts,
- final risk policy primitives (v1.0 minimum set),
- any UI/visualization features (explicitly deferred),
- production-grade operational posture (monitoring/runbooks) (deferred).

---

## Appendix A — Alignment to the product roadmap (`docs/dsl_proj_plan.md`)

**Status: CURRENTLY DECIDED**  
Rationale: Prevents overspec and keeps effort aligned with deliverable versions.  
Implications: Implementation should use this mapping to prioritize.

- v0.1: Ch 11 + Ch 21 (`validate`) + minimal examples
- v0.2: Ch 12 + forbidden constructs + `lint`
- v0.3: Ch 13–14 + trace model + `run` + basic `explain`
- v0.4: Ch 6.5 + replay/diff + MVP equity screener workflows
- v0.5: Ch 16 indicators + golden numeric tests
- v0.6: Ch 23 packaging/imports
- v1.0: profiles + risk basics + reporting
- v1.1: option context
- v1.2: chain context
- v2.0: intent→plan→risk integration and parity harness
