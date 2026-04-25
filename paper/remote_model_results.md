# Remote Model Comparison Results

## Scope

This note summarizes two remote-model experiments for the Go-Stop evaluation harness. The summaries below are descriptive and should not be read as universal model rankings.

1. Qwen parameter-scale comparison on Alibaba DashScope.
2. Rate-limited roughly same-size cross-family comparison on NVIDIA Build NIM.

Both experiments used all 24 seat permutations of a 4-model panel with 2 layout repetitions, giving 48 session samples per model and 192 session observations per experiment.

## Qwen Parameter-Scale Panel

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
The 397B Qwen3.5 model produced the highest descriptive mean profit and least severe empirical CVaR in this limited panel. The observed ranking is not monotone in nominal parameter size: the 480B Coder model ranked below the 397B and 122B models on mean profit and CVaR. Because the panel mixes Qwen3.5 and Qwen Coder variants, this is not an isolated scale-effect estimate.

## NVIDIA Constrained Same-Size Cross-Family Panel

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
Within the constrained NVIDIA panel, Nemotron had the highest descriptive mean profit and least severe empirical CVaR. This is consistent with cross-family differences being visible under the harness, but it is not a confirmatory family-effect estimate because the run used a one-hand horizon and a one-call remote budget.

## Limitations

- The model panels are convenience samples from available remote APIs.
- Qwen results mix Coder and Qwen3.5 variants, so parameter scale is partly confounded with model specialization.
- NVIDIA results used `max_remote_calls_per_agent=1` because of rate limits. The experiment measures constrained first-decision behavior more than full-game autonomous play.
- Session horizons are short: 2 hands for Qwen and 1 hand for NVIDIA.
- CVaR is based on 48 samples per model, with effective 5% tail mass 2.4 and support count 3.
- The exported tables do not report invalid-response, API-error, cache-hit, or fallback-action rates.
- Results support a paper section on feasibility, ranking under constrained evaluation, and limitations. They should not be framed as definitive general model rankings.
