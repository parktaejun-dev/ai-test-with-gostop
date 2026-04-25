# Methods

## Evaluation target
- Evaluate fixed remote-model policies only.
- Learning, tuning, and log-based adaptation are disallowed.
- The current manuscript centers two remote-API panels:
  - Qwen-labeled parameter-scale panel on Alibaba DashScope.
  - Rate-limited roughly same-scale cross-family panel on NVIDIA Build NIM.

## Environment
- 4-player start.
- 8 floor cards, 7 cards per player.
- 3 active players after participation decisions.
- 2 jokers included.
- `ChooseMatch` branches explicitly when multiple same-month floor cards exist.
- Responsibility-style dokbak is triggered only when the next player directly captures the immediately preceding floor card to reach at least 3 points.
- Showdown evaluation is the difference between actual settlement and a no-showdown counterfactual at proposal time.
- Each player may propose showdown at most once per hand.

## Policy interface
- Remote models are called through OpenAI-compatible chat-completion APIs.
- The fixed prompt is:

```text
You are a fixed Go-Stop evaluation policy. Choose one legal action index only. Optimize long-run profit with risk control. Do not explain.
```

- The model must return JSON with one `choice_index`.
- Invalid, unparsable, out-of-range, over-budget, or post-`remote_eval_hands` decisions fall back to the first legal action.
- Repeated public states are cached by public-state hash.

## Panel A: Qwen parameter-scale panel
- Provider: Alibaba DashScope.
- Result directory: `results/paper_qwen_4model_param_2h_2rep`.
- Models:
  - `qwen3-coder-30b-a3b-instruct`
  - `qwen3.5-122b-a10b`
  - `qwen3.5-397b-a17b`
  - `qwen3-coder-480b-a35b-instruct`
- Nominal total parameters: 30B, 122B, 397B, 480B.
- Recorded active parameters: 3B, 10B, 17B, 35B.
- `session_hands=2`.
- `remote_eval_hands=2`.
- `layout_repetitions=2`.
- `base_seed=7`.
- `initial_bankroll=100000`.
- `stake_per_point=100`.
- Decoding: `temperature=0`, `max_tokens=64`, `enable_thinking=false`.
- The panel mixes Qwen3.5 and Qwen Coder variants, so it tests observed monotonicity in this callable Qwen-labeled panel rather than a pure scale effect.

## Panel B: NVIDIA constrained same-scale family panel
- Provider: NVIDIA Build NIM.
- Result directory: `results/paper_nvidia_120b_4model_family_1h_2rep_budget1`.
- Models:
  - `qwen/qwen3.5-122b-a10b`
  - `mistralai/mistral-small-4-119b-2603`
  - `nvidia/nemotron-3-super-120b-a12b`
  - `stockmark/stockmark-2-100b-instruct`
- Recorded nominal parameters: 122B, 119B, 120B, 100B.
- `session_hands=1`.
- `remote_eval_hands=1`.
- `max_remote_calls_per_agent=1`.
- `layout_repetitions=2`.
- `base_seed=7`.
- `initial_bankroll=100000`.
- `stake_per_point=100`.
- Decoding: `temperature=0`, `max_tokens=64`.
- This panel is a constrained first-decision proxy, not a full-horizon autonomous-play comparison.

## Design
- Each panel enumerates all `4! = 24` seat-order permutations.
- Each layout is repeated twice.
- Each panel has 48 session samples per model and 192 model-session observations.
- The analysis unit is seat-level terminal session profit.
- The pairing unit for diagnostics is `session_id`; layout effects are tracked through repeated layouts.

## Primary questions
- `RQ1`: In the Qwen-labeled DashScope panel, is observed Go-Stop performance monotone in nominal parameter scale?
- `RQ2`: In the rate-limited NVIDIA Build panel, are cross-family differences visible in descriptive profit and risk summaries?

## Metrics
- `mean_profit`: session-ending bankroll minus initial bankroll.
- `cvar_5`: empirical expected shortfall over the bottom 5% of session profit.
- `ruin_probability`: share of seat-level sessions ending with bankroll `<= 0`.
- `win_rate`, `profit_per_hand`, `hands_survived`, `session_completed_rate`, `early_exit_rate`, forced gwang-sell, and showdown metrics are descriptive/supporting metrics.

## Statistical interpretation
- Rankings in the manuscript are descriptive.
- CVaR uses only 48 session samples per model, so the effective 5% tail mass is 2.4 sessions and the support count is 3.
- The code marks `cvar_5_low_support=false` when support count is at least 3, but `analysis/statistics.py` separately treats CVaR inference below 100 sessions per model as unstable.
- Pairwise mean-profit and CVaR diagnostics are available in each `report.json`, but the manuscript does not claim universal model rankings or isolated causal effects.

## Reproducibility commands
Qwen panel:

```bash
python3 scripts/run_dashscope_qwen_parameter_sweep.py \
  --session-hands 2 \
  --layout-repetitions 2 \
  --remote-eval-hands 2 \
  --decoding max_tokens=64 \
  --decoding temperature=0 \
  --decoding enable_thinking=false \
  --output-dir results/paper_qwen_4model_param_2h_2rep
```

NVIDIA panel:

```bash
python3 scripts/run_nvidia_same_size_family_eval.py \
  --session-hands 1 \
  --layout-repetitions 2 \
  --remote-eval-hands 1 \
  --max-remote-calls-per-agent 1 \
  --decoding max_tokens=64 \
  --decoding temperature=0 \
  --output-dir results/paper_nvidia_120b_4model_family_1h_2rep_budget1
```

## Appendix calibration
- The four heuristic agents (`RandomAgent`, `RuleBasedAgent`, `GreedyProfitAgent`, `SurvivalAgent`) remain in the repository as calibration artifacts.
- They are not the main result for the current manuscript.
