# Methods

## Evaluation target
- Evaluate fixed policies only.
- Learning, tuning, and log-based adaptation are disallowed.
- The main paper target is an LLM factorial study, not the heuristic sanity-check benchmark.

## Environment
- 4-player start
- 8 floor cards, 7 cards per player
- 3 active players after participation decisions
- 2 jokers included
- `ChooseMatch` branches explicitly when multiple same-month floor cards exist.
- Responsibility-style dokbak is triggered only when the next player directly captures the immediately preceding floor card to reach at least 3 points.
- Showdown evaluation is the difference between actual settlement and a no-showdown counterfactual at proposal time.
- Each player may propose showdown at most once per hand.

## Reproducibility
- Seed hierarchy:
  - `base_seed`
  - `lineup_seed`
  - `layout_seed`
  - `session_seed`
  - `hand_seed`
  - `decision_seed`
- The blocked factorial study uses the same reproducibility settings as the baseline calibration run:
  - base seeds `7,11,13,17,19`
  - repeated layouts
  - 300-hand horizon
  - initial bankroll `1000`
  - stake per point `1`

## Main paper design
- The main paper is a blocked factorial LLM study over a fixed `4-model x 4-strategy` panel.
- Factor A (`model`) is a frozen OpenRouter model panel pinned in repo-tracked config.
- Factor B (`strategy`) is a frozen English prompt strategy set:
  - `Balanced`
  - `Analytic`
  - `Conservative`
  - `Aggressive`
- The same four models are evaluated once per strategy.
- For each strategy:
  - enumerate all `24` seat-order permutations
  - repeat each layout across the multi-seed repeated-layout protocol
- The analysis unit is seat-level session profit.
- The nuisance block is `factorial_block_id = base_seed | layout | layout_repeat`.
- Each complete block contains `16` observations: `4` models × `4` strategies.

## Primary research questions
- `RQ1`: which factor explains more variance in mean session profit, model identity or prompt strategy?
- `RQ2`: are model and strategy effects robust on `CVaR_5` and ruin probability?
- `RQ3`: is there a non-trivial `model x strategy` interaction?

## Estimands
- `mean_profit`: session-ending bankroll minus initial bankroll.
- `cvar_5`: empirical expected shortfall over the bottom 5% of session profit.
- `ruin_probability`: share of seat-level sessions ending with bankroll `<= 0`.
- `profit_per_hand`, `win_rate`, `hands_survived`, `early_exit_rate`, and showdown metrics remain descriptive/supporting.

## Statistical protocol
- Primary analysis:
  - blocked factorial analysis on `mean_profit`
  - report `model`, `strategy`, and `model x strategy` terms
  - report partial eta-squared for each term
- Secondary robustness:
  - model-marginal and strategy-marginal `cvar_5`
  - model-marginal and strategy-marginal `ruin_probability`
  - uncertainty summarized with the existing block/bootstrap style over `factorial_block_id`
- The dominant main effect is defined operationally as the larger partial eta-squared between `model` and `strategy`.

## Prompt and model freezing
- Exact model IDs are pinned in repo-tracked config and recorded in manifests.
- Prompt strategies are stored as repo-tracked text files and hashed into manifests.
- If a pinned model is unavailable, the study must fail fast rather than silently substituting another model.

## Appendix calibration
- The four heuristic agents (`RandomAgent`, `RuleBasedAgent`, `GreedyProfitAgent`, `SurvivalAgent`) remain in the repository.
- Their baseline study is no longer the main paper result.
- It now serves as appendix calibration showing:
  - the environment is reproducible
  - the harness can detect policy differences
  - repeated layouts reveal identifiable layout effects
