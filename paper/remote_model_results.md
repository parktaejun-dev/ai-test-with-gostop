# 원격 모델 비교 결과 | Remote Model Comparison Results

## 범위 | Scope

한국어:
이 문서는 고스톱 AI 평가 논문의 공개 결과 번들을 요약한다. 결과는 기술통계이며 보편적 모델 순위로 읽으면 안 된다.

핵심 insight는 다음과 같다.

> 고스톱 성능은 파라미터 규모만으로 설명되지 않는다. 모델 family, 정책 framing, serving 제약, 하방 위험 행동이 함께 작용한다.

English:
This note summarizes the public result bundles for the Go-Stop AI evaluation paper. The results are descriptive and should not be read as universal model rankings.

The central insight is:

> Go-Stop performance is not explained by parameter scale alone. Model family, policy framing, serving constraints, and tail-risk behavior interact.

## 왜 고스톱인가 | Why Go-Stop Is Used

한국어:
고스톱은 작은 확률적 의사결정 환경이다. 에이전트는 숨은 패, 불확실한 미래 드로우, 조합적 점수 규칙, 다중 에이전트 상호작용, 고/스톱 위험 결정 아래에서 행동해야 한다. 이 때문에 위험 민감적 순차 의사결정 평가에 적합하다.

목표 행동은 단순히 자주 이기는 것이 아니다. 강한 정책은 큰 하방 손실도 피해야 한다. 따라서 논문은 다음 지표를 함께 보고한다.

- `mean_profit`
- `cvar_5`
- `win_rate`
- `ruin_probability`
- sample count and support diagnostics

이 구조는 실시간 광고 입찰과 캠페인 예산 pacing처럼 불확실한 수익과 하방 위험 아래에서 지출, 대기, 입찰 조정을 반복 결정하는 산업적 의사결정에도 방법론적으로 연결된다.

English:
Go-Stop is a compact stochastic decision environment. Agents must act with hidden hands, uncertain future draws, combinatorial scoring rules, multi-agent interaction, and Go/Stop risk decisions. This makes it useful for evaluating risk-sensitive sequential decision making.

The target behavior is not only winning often. A strong policy should also avoid severe lower-tail losses. The paper therefore reports `mean_profit`, `cvar_5`, `win_rate`, `ruin_probability`, sample count, and support diagnostics. This framing has methodological relevance to industrial decision systems such as real-time bidding and campaign budget pacing.

## 주 패널 A: Qwen 파라미터 규모 | Main Panel A: Qwen Parameter-Scale Study

Artifact directory: `results/paper_qwen_4model_param_2h_2rep`

설정 / Configuration:
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

해석:
397B Qwen3.5 모델이 가장 높은 평균 수익과 가장 덜 나쁜 empirical CVaR을 보였다. 순위는 명목 파라미터 규모에 대해 단조적이지 않다. 다만 이 패널은 Qwen3.5와 Qwen Coder 변형을 함께 포함하므로 순수한 scale-effect 추정은 아니다.

Interpretation:
The 397B Qwen3.5 model produced the highest descriptive mean profit and least severe empirical CVaR. The ranking is not monotone in nominal parameter size. Because the panel mixes Qwen3.5 and Qwen Coder variants, this is not an isolated scale-effect estimate.

## 주 패널 B: NVIDIA 동일 규모 cross-family | Main Panel B: NVIDIA Same-Scale Cross-Family Study

Artifact directory: `results/paper_nvidia_120b_4model_family_1h_2rep_budget1`

설정 / Configuration:
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

해석:
Nemotron이 평균 수익과 empirical CVaR 기준으로 가장 높았다. 이는 제한된 하네스 안에서 family 차이가 관찰될 수 있음을 보여준다. 다만 one-hand horizon과 에이전트당 원격 호출 1회 제약이 있으므로 확증적 family-effect 추정은 아니다.

Interpretation:
Nemotron had the highest descriptive mean profit and least severe empirical CVaR. This is consistent with cross-family differences being visible under the harness, but it is not a confirmatory family-effect estimate because the run used a one-hand horizon and a one-call remote budget.

## 보조 패널 C: NVIDIA 소형 모델 | Supplementary Panel C: NVIDIA Small Models

Artifact directory: `results/tiny_nvidia_4model_1h_2rep_budget1_20260425_075542`

설정 / Configuration:
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

해석:
소형 모델 결과는 소형 모델이 일반적으로 충분하다는 증거가 아니다. 제한된 조건에서 한 소형 모델이 양의 평균 수익을 냈다는 feasibility 근거다.

Interpretation:
The small-model result does not prove that small models are generally sufficient. It shows that a small model can produce positive mean profit in this restricted setting.

## 보조 패널 D: Qwen 소형 모델 정책 스크린 | Supplementary Panel D: Qwen Small-Model Policy Screen

Artifact directories:
- `results/policy_screen_qwen_tiny_balanced_1h_1rep_20260425_102731`
- `results/policy_screen_qwen_tiny_analytic_1h_1rep_20260425_102731`
- `results/policy_screen_qwen_tiny_conservative_1h_1rep_20260425_102731`
- `results/policy_screen_qwen_tiny_aggressive_1h_1rep_20260425_102731`

각 model-policy cell은 24 표본이다. Each model-policy cell has 24 samples.

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

해석:
Qwen 소형 정책 스크린도 단조적이지 않다. 4B 모델이 정책 평균 기준으로 가장 높고, prompt framing에 따라 1위 모델이 바뀐다.

Interpretation:
The small Qwen policy screen is non-monotonic. The 4B model has the best policy-average mean profit, and the top model changes by prompt framing.

## 보조 패널 E: NVIDIA 정책 스크린 | Supplementary Panel E: NVIDIA Policy Screen

Artifact directories:
- `results/policy_screen_nvidia_balanced_1h_1rep_20260425_075542`
- `results/policy_screen_nvidia_analytic_1h_1rep_20260425_075542`
- `results/policy_screen_nvidia_conservative_1h_1rep_20260425_075542`
- `results/policy_screen_nvidia_aggressive_1h_1rep_20260425_075542`

각 model-policy cell은 24 표본이다. Each model-policy cell has 24 samples.

| Policy framing | Top model | Top mean profit | Top CVaR 5% |
|---|---|---:|---:|
| Balanced | `nvidia/nemotron-3-super-120b-a12b` | 645.17 | -2067.00 |
| Analytic | `nvidia/nemotron-3-super-120b-a12b` | 598.92 | -2067.00 |
| Conservative | `nvidia/nemotron-3-super-120b-a12b` | 416.67 | -1850.00 |
| Aggressive | `nvidia/nemotron-3-super-120b-a12b` | 598.83 | -3701.67 |

해석:
Nemotron은 네 정책 framing 모두에서 1위를 유지한다. 이는 prompt framing에 따라 1위가 바뀐 Qwen 소형 스크린과 대비된다.

Interpretation:
Nemotron remains the top model across all four policy framings. This contrasts with the Qwen small-model screen, where the leader changes by prompt framing.

## 연구문제 답변 | Research Questions Answered

한국어:
- RQ1: 고스톱은 숨은 정보, 확률적 전이, 고/스톱 위험, 다중 에이전트 상호작용을 결합하므로 위험 민감적 순차 의사결정 평가에 적합한 compact benchmark다.
- RQ2: Qwen 패널은 명목 파라미터 규모에 대해 단조적이지 않다.
- RQ3: NVIDIA 동일 규모 패널은 family별 기술통계 차이를 보이며, Nemotron이 평균 수익과 empirical CVaR에서 가장 높다.
- RQ4: 소형 모델과 정책 framing 스크린은 양의 소형 모델 성과와 모델별 prompt-policy 효과를 탐색적으로 보여준다.

English:
- RQ1: Go-Stop is a plausible compact benchmark for risk-sensitive sequential decision making because it combines hidden information, stochastic transitions, stop-or-continue risk, and multi-agent interaction.
- RQ2: The Qwen panel is not monotone in nominal parameter scale.
- RQ3: The NVIDIA same-scale panel shows visible cross-family differences, with Nemotron leading on mean profit and empirical CVaR.
- RQ4: Small-model and policy-framing screens show exploratory evidence of positive small-model performance and model-specific prompt-policy effects.

## 한계 | Limitations

한국어:
- 모델 패널은 사용 가능한 원격 API에서 구성한 convenience sample이다.
- Qwen 결과는 Coder와 Qwen3.5 변형을 함께 포함하므로 파라미터 규모와 모델 특화 목적이 부분적으로 얽혀 있다.
- NVIDIA 결과는 rate limit 때문에 `max_remote_calls_per_agent=1`을 사용했다.
- 세션 horizon은 짧다. Qwen 주 실험은 2 hands, NVIDIA 주 실험과 보조 실험은 1 hand다.
- 주 패널은 모델당 48 표본, 정책 스크린은 model-policy cell당 24 표본이다.
- CVaR은 기술통계이며 저장소의 안정적 CVaR 권장 기준인 모델당 100 세션보다 낮다.
- export table은 invalid-response, API-error, cache-hit, fallback-action rate를 별도 지표로 보고하지 않는다.

English:
- The model panels are convenience samples from available remote APIs.
- Qwen results mix Coder and Qwen3.5 variants, so parameter scale is partly confounded with model specialization.
- NVIDIA results used `max_remote_calls_per_agent=1` because of rate limits.
- Session horizons are short: 2 hands for Qwen main, 1 hand for NVIDIA main and supplementary screens.
- Main panels have 48 samples per model; policy screens have 24 samples per model-policy cell.
- CVaR is descriptive and below the repository's recommended 100 sessions per model for stable CVaR inference.
- The exported tables do not report invalid-response, API-error, cache-hit, or fallback-action rates.
