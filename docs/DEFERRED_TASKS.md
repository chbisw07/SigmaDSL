Yes. Across SigmaDSL, Codex has **intentionally deferred** these items. They are not failures; they were kept out to protect deterministic foundations.

## Deferred items and when to implement

| Deferred item                                                      | Why deferred                                                             | Suggested phase                                 |
| ------------------------------------------------------------------ | ------------------------------------------------------------------------ | ----------------------------------------------- |
| Broker execution / live order placement                            | DSL must stay broker-agnostic; execution belongs to adapters/STPRO       | After v2.0-D, in STPRO integration phase        |
| Broker routing / OMS lifecycle                                     | Requires broker-specific state, order ids, modify/cancel, reconciliation | STPRO adapter layer, not core DSL               |
| Broker symbol mapping                                              | Depends on Zerodha/Angel/Fyers symbol formats                            | STPRO integration                               |
| Product mapping: MIS/CNC/NRML/options product types                | Broker-specific, not DSL-level                                           | STPRO execution adapter                         |
| Real live runtime / async event engine                             | Would introduce nondeterminism too early                                 | Later v3.x or STPRO runtime                     |
| Plan execution                                                     | Plan IR is intentionally non-executable                                  | Adapter phase after Plan IR contracts stabilize |
| Portfolio optimization                                             | Needs holdings, capital, margin, exposure state                          | Later risk/planning phase                       |
| Advanced risk engine                                               | Current risk is fail-closed and deterministic, but simple                | v2.1+                                           |
| Stateful risk models                                               | Requires account/position history and broker truth                       | STPRO + risk adapter phase                      |
| Multi-leg option strategy construction                             | Needs chain, selection, intent/plan semantics to mature first            | v2.1/v2.2                                       |
| Iron condor/spread/straddle planning                               | Strategy-level planning not yet built                                    | v2.1+                                           |
| Option chain advanced analytics: max pain, GEX, probability models | Metrics need strong semantics and goldens                                | v1.3 or v2.1                                    |
| Strike/tenor skew surface                                          | More complex than current simple `iv_skew`                               | v1.3+                                           |
| Per-contract iteration/aggregation DSL                             | Could complicate language semantics                                      | v1.3/v2.1                                       |
| Dynamic per-bar option reselection                                 | Current selection is once-per-run deterministic                          | v1.3 if needed                                  |
| Full `in chain:` strategy generation                               | Chain context exists, but not strategy builder                           | v2.1+                                           |
| Imports/package registry / publish-install workflow                | Local packaging exists; registry is distribution problem                 | Later ecosystem phase                           |
| Remote package dependencies                                        | Needs trust/security/versioning                                          | Later ecosystem phase                           |
| Signing/trust chain for packs                                      | Not needed for local deterministic use                                   | Later distribution phase                        |
| Website / learning portal                                          | Book/docs first, website later                                           | After v2.0 foundation stabilizes                |
| UI/frontend                                                        | DSL is CLI/library first                                                 | Later, possibly STPRO or docs site              |
| AI-assisted rule authoring                                         | Needs stable language and examples first                                 | Later assistant/tooling phase                   |
| In-language profile declarations                                   | Profiles are CLI-selected for now                                        | Later language ergonomics phase                 |
| Expanded indicator catalog                                         | EMA/RSI/ATR/VWAP first; avoid indicator sprawl                           | v1.3 or cookbook-driven phase                   |
| Backtesting PnL / brokerage / slippage                             | DSL currently emits decisions/plans, not trade simulation                | Separate backtest engine / SigmaLab integration |
| Margin calculation                                                 | Broker/exchange-specific and changes frequently                          | STPRO/broker adapter phase                      |

## Recommended roadmap from here

Finish **v2.0-D** first. That gives you parity proof and adapter contracts.

Then I’d sequence the deferred work like this:

```text
v2.0-D  Parity harness + adapter contracts
v2.1-A  Adapter contract validation + plan consumer mock
v2.1-B  Plan-level risk constraints v2
v2.1-C  Multi-leg Plan IR foundation
v2.2-A  Option strategy planning: spreads/straddles/condors
v2.3+   STPRO integration adapter
Later   Broker execution, UI, AI authoring, website
```

Most important rule: **broker execution should not enter SigmaDSL core**. SigmaDSL should produce trusted decisions/plans; STPRO/adapters should execute and reconcile.

If you want next, I can help you:

👉 design STPRO ↔ DSL integration architecture (this is the real payoff)

