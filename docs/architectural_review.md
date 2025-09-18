# Architectural Review – Terminal Dou Dizhu

**Date:** 2025-09-18

## Key Findings

- **High – Resume loses pass streak state**: `game.py` resets `passes_in_row` to 0 on each resume, while `core/replay.py` rebuilds no pass streak context. After a crash, a third consecutive pass fails to clear the trick, breaking turn order. Store the streak in ledger events (e.g., include counters in `PASS`/`ROUND_RESET`) or funnel all replay/live updates through a shared reducer that returns `passes_in_row` alongside other state.
- **High – Ruleset owns terminal I/O**: `StandardDouDizhuRules._bidding` mixes prompts with bidding logic, preventing reuse for bots, tests, or alternative front-ends. Extract a bidding/controller interface that the CLI implements and keep `RuleSet` deterministic.
- **High – Tight coupling across loop, rules, ledger**: `Game` and `StandardDouDizhuRules` both append directly to the ledger, so there is no single authority over event order or failure handling. A mid-append failure can corrupt the ledger unnoticed. Introduce an explicit event dispatcher so domain code emits intents and persistence is centralized.
- **Medium – Duplicated state-transition logic**: `_pick_from_hand` and `_simple_tips` in `game.py` implement removal/preview logic differently from `core/replay.py`. Any rule change must be replicated. Create a `GameState.apply(event)` reducer that both live play and recovery use.
- **Medium – Registry ownership limits rule variants**: `Game` owns `HandRegistry`, forcing variants to reach across layers for custom patterns. Let the ruleset provide/configure the registry to keep gameplay variants self-contained.
- **Medium – Player API ignores suit-level intent**: `Player.has_cards`/`take_cards` (rank-based matching) guess which suit to remove, which blocks multi-deck or deterministic AI uses. Expose suit-aware selectors or deterministic card ids so higher layers specify exact cards.

## Recommended Next Steps

1. Build a deterministic reducer that replays ledger events (including pass streak accounting) and have both CLI loop and recovery consume it.
2. Introduce controller abstractions around bidding/turn decisions; migrate terminal I/O into those controllers and keep `RuleSet` side-effect free.
3. Centralize event emission: let the loop construct domain events, feed them to the reducer, then flush to the ledger in one place with robust error handling.
