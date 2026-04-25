# Remote Model Comparison Results

## Scope

This note summarizes the public result bundles for the Go-Stop AI evaluation paper.
The results are descriptive and should not be read as universal model rankings.

The central insight is:

> Go-Stop performance is not explained by parameter scale alone. Model family, policy framing, serving constraints, and tail-risk behavior interact.

## Why Go-Stop Is Used

Go-Stop is a compact stochastic decision environment. Agents must act with hidden hands, uncertain future draws, combinatorial scoring rules, multi-agent interaction, and Go/Stop risk decisions. This makes it useful for evaluating risk-sensitive sequential decision making.

The target behavior is not only winning often. A strong policy should also avoid severe lower-tail losses. The paper therefore reports:

- `mean_profit`
- `cvar_5`
- `win_rate`
- `ruin_probability`
- sample count and support diagnostics

This framing has methodological relevance to industrial decision systems such as real-time bidding and campaign budget pacing, where agents repeatedly decide whether to spend, wait, or adjust bids under uncertain returns and downside risk.

## Main Panel A: Qwen Parameter-Scale Study

Artifact directory: `results/paper_qwen_4model_param_2h_2rep`

Configuration:
- Provider: Alibaba DashScope
- Models: `qwen3-coder-30b-a3b-instruct`, `qwen3.5-122b-a10b`, `qwen3.5-397b-a17b`, `qwen3-coder-480b-a35b-instruct`
- Session hands: 2
- Layout repetitions: 2
- Remote eval hands: 2
- Samples per model: 48
- CVaR low support: false for all models by the implementation threshold
- CVaR effective 5% tail mass: 2.4 sessions per model

| Model | Mean profit | Win rate | CVaR 5% | Sample count |
|---|---:|---:|---:|---:|
| `qwen3.5-397b-a17b` | 996.25 | 0.3021 | -1850.08 | 48 |
| `qwen3.5-122b-a10b` | -51.75 | 0.3542 | -4145.33 | 48 |
| `qwen3-coder-480b-a35b-instruct` | -198.92 | 0.2396 | -5084.75 | 48 |
| `qwen3-coder-30b-a3b-instruct` | -745.58 | 0.1042 | -5269.25 | 48 |

Interpretation:
The 397B Qwen3.5 model produced the highest descriptive mean profit and least severe empirical CVaR. The ranking is not monotone in nominal parameter size. Because the panel mixes Qwen3.5 and Qwen Coder variants, this is not an isolated scale-effect estimate.

## Main Panel B: NVIDIA Same-Scale Cross-Family Study

Artifact directory: `results/paper_nvidia_120b_4model_family_1h_2rep_budget1`

Configuration:
- Provider: NVIDIA Build NIM
- Models: `qwen/qwen3.5-122b-a10b`, `mistralai/mistral-small-4-119b-2603`, `nvidia/nemotron-3-super-120b-a12b`, `stockmark/stockmark-2-100b-instruct`
- Target scale: roughly 100B-122B parameters
- Session hands: 1
- Layout repetitions: 2
- Remote eval hands: 1
- Max remote calls per agent per session: 1
- Samples per model: 48
- CVaR low support: false for all models by the implementation threshold
- CVaR effective 5% tail mass: 2.4 sessions per model

| Model | Mean profit | Win rate | CVaR 5% | Sample count |
|---|---:|---:|---:|---:|
| `nvidia/nemotron-3-super-120b-a12b` | 500.65 | 0.2708 | -1384.17 | 48 |
| `mistralai/mistral-small-4-119b-2603` | -73.19 | 0.2917 | -4150.00 | 48 |
| `qwen/qwen3.5-122b-a10b` | -172.85 | 0.1875 | -3350.42 | 48 |
| `stockmark/stockmark-2-100b-instruct` | -254.60 | 0.2500 | -4267.08 | 48 |

Interpretation:
Nemotron had the highest descriptive mean profit and least severe empirical CVaR. This is consistent with cross-family differences being visible under the harness, but it is not a confirmatory family-effect estimate because the run used a one-hand horizon and a one-call remote budget.

## Supplementary Panel C: NVIDIA Small Models

Artifact directory: `results/tiny_nvidia_4model_1h_2rep_budget1_20260425_075542`

Configuration:
- Provider: NVIDIA Build NIM
- Session hands: 1
- Layout repetitions: 2
- Remote eval hands: 1
- Max remote calls per agent per session: 1
- Samples per model: 48

| Model | Mean profit | Win rate | CVaR 5% | Sample count |
|---|---:|---:|---:|---:|
| `ibm/granite-3.0-3b-a800m-instruct` | 381.25 | 0.3125 | -1966.67 | 48 |
| `meta/llama-3.2-1b-instruct` | -20.83 | 0.2708 | -2083.33 | 48 |
| `google/gemma-2-2b-it` | -68.75 | 0.2500 | -3833.33 | 48 |
| `microsoft/phi-4-mini-instruct` | -291.67 | 0.1667 | -3916.67 | 48 |

Interpretation:
The small-model result does not prove that small models are generally sufficient. It does show that a small model can produce positive mean profit in this restricted setting.

## Supplementary Panel D: Qwen Small-Model Policy Screen

Artifact directories:
- `results/policy_screen_qwen_tiny_balanced_1h_1rep_20260425_102731`
- `results/policy_screen_qwen_tiny_analytic_1h_1rep_20260425_102731`
- `results/policy_screen_qwen_tiny_conservative_1h_1rep_20260425_102731`
- `results/policy_screen_qwen_tiny_aggressive_1h_1rep_20260425_102731`

Each model-policy cell has 24 samples.

| Policy framing | Top model | Top mean profit | Top CVaR 5% |
|---|---|---:|---:|
| Balanced | `qwen3-4b` | 224.88 | -1166.67 |
| Analytic | `qwen3-4b` | 412.33 | -2566.83 |
| Conservative | `qwen3-8b` | 238.08 | -1301.67 |
| Aggressive | `qwen3-14b` | 254.08 | -1284.33 |

Average mean profit across the four policy framings:

| Model | Average mean profit |
|---|---:|
| `qwen3-4b` | 65.47 |
| `qwen3-14b` | 11.22 |
| `qwen3-1.7b` | -14.82 |
| `qwen3-8b` | -61.86 |

Interpretation:
The small Qwen policy screen is non-monotonic. The 4B model has the best policy-average mean profit, and the top model changes by prompt framing.

## Supplementary Panel E: NVIDIA Policy Screen

Artifact directories:
- `results/policy_screen_nvidia_balanced_1h_1rep_20260425_075542`
- `results/policy_screen_nvidia_analytic_1h_1rep_20260425_075542`
- `results/policy_screen_nvidia_conservative_1h_1rep_20260425_075542`
- `results/policy_screen_nvidia_aggressive_1h_1rep_20260425_075542`

Each model-policy cell has 24 samples.

| Policy framing | Top model | Top mean profit | Top CVaR 5% |
|---|---|---:|---:|
| Balanced | `nvidia/nemotron-3-super-120b-a12b` | 645.17 | -2067.00 |
| Analytic | `nvidia/nemotron-3-super-120b-a12b` | 598.92 | -2067.00 |
| Conservative | `nvidia/nemotron-3-super-120b-a12b` | 416.67 | -1850.00 |
| Aggressive | `nvidia/nemotron-3-super-120b-a12b` | 598.83 | -3701.67 |

Interpretation:
Nemotron remains the top model across all four policy framings. This contrasts with the Qwen small-model screen, where the leader changes by prompt framing.

## Research Questions Answered

- RQ1: Go-Stop is a plausible compact benchmark for risk-sensitive sequential decision making because it combines hidden information, stochastic transitions, stop-or-continue risk, and multi-agent interaction.
- RQ2: The Qwen panel is not monotone in nominal parameter scale.
- RQ3: The NVIDIA same-scale panel shows visible cross-family differences, with Nemotron leading on mean profit and empirical CVaR.
- RQ4: Small-model and policy-framing screens show exploratory evidence of positive small-model performance and model-specific prompt-policy effects.

## Limitations

- The model panels are convenience samples from available remote APIs.
- Qwen results mix Coder and Qwen3.5 variants, so parameter scale is partly confounded with model specialization.
- NVIDIA results used `max_remote_calls_per_agent=1` because of rate limits.
- Session horizons are short: 2 hands for Qwen main, 1 hand for NVIDIA main and supplementary screens.
- Main panels have 48 samples per model; policy screens have 24 samples per model-policy cell.
- CVaR is descriptive and below the repository's recommended 100 sessions per model for stable CVaR inference.
- The exported tables do not report invalid-response, API-error, cache-hit, or fallback-action rates.
- Results support a paper section on feasibility, ranking under constrained evaluation, and model-policy interaction. They should not be framed as definitive general model rankings.
