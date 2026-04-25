# 원격 모델 비교 결과 | Remote Model Comparison Results

## 한국어

### 범위

이 문서는 고스톱 AI 평가 논문의 공개 결과 번들을 요약한다. 결과는 기술통계이며 보편적 모델 순위로 읽으면 안 된다.

핵심 insight는 다음과 같다.

> 고스톱 성능은 파라미터 규모만으로 설명되지 않는다. 모델 family, 정책 framing, serving 제약, 하방 위험 행동이 함께 작용한다.

### 왜 고스톱인가

고스톱은 작은 확률적 의사결정 환경이다. 에이전트는 숨은 패, 불확실한 미래 드로우, 조합적 점수 규칙, 다중 에이전트 상호작용, 고/스톱 위험 결정 아래에서 행동해야 한다. 이 때문에 위험 민감적 순차 의사결정 평가에 적합하다.

목표 행동은 단순히 자주 이기는 것이 아니다. 강한 정책은 큰 하방 손실도 피해야 한다. 따라서 논문은 `mean_profit`, `cvar_5`, `win_rate`, `ruin_probability`, 표본 수, support diagnostics를 함께 보고한다.

### 산업적 연결: 광고 입찰

광고 입찰은 고스톱과 같은 게임이 아니지만, 평가해야 하는 의사결정 구조가 닮아 있다. 광고 시스템은 제한된 예산 안에서 매 노출마다 입찰할지, 낮출지, 기다릴지를 결정한다. 전환 확률, 경쟁 입찰가, 빈도 피로, 잔여 예산, 캠페인 pacing은 모두 불확실하다.

평균 ROAS만 보면 위험하다. 어떤 정책은 평균 성과가 좋아 보여도 특정 구간에서 예산을 너무 빨리 태우거나, 낮은 품질 inventory에 과도하게 노출되거나, 드문 큰 손실을 만들 수 있다. 본 논문의 고스톱 평가는 광고 시스템을 직접 모사하지 않고, 순차 행동 선택, 불확실성, 예산/위험 trade-off, 하방 위험 관리가 함께 나타나는 정책 평가 프레임으로 연결된다.

### 용어 정의

- Mean profit: 세션 종료 후 모델이 얻은 평균 수익이다.
- CVaR 5%: 가장 나쁜 하위 5% 결과의 평균 손실을 요약하는 하방 위험 지표다. 이 논문에서는 표본 수가 작으므로 기술통계로 사용한다.
- Win rate: 세션에서 양의 수익을 낸 비율이다.
- Ruin probability: 자본이 소진되거나 사실상 파산 상태에 도달할 확률이다.
- Parameter scale: 모델의 명목 파라미터 규모다. MoE 모델에서는 전체 파라미터와 active parameter가 다를 수 있다.
- Model family: Qwen, Mistral, Nemotron처럼 모델 계열 또는 개발 계통을 뜻한다.
- Policy framing: 같은 게임 상태에서 모델에 제시하는 의사결정 지침의 성향이다.
- `max_remote_calls_per_agent`: 한 세션에서 에이전트가 원격 모델 API를 호출할 수 있는 최대 횟수다.
- ROAS: 광고비 대비 매출이다.
- Budget pacing: 캠페인 예산을 기간 전체에 맞게 쓰도록 지출 속도를 조절하는 과정이다.

### 주 패널 A: Qwen 파라미터 규모

Artifact directory: `results/paper_qwen_4model_param_2h_2rep`

설정:
- Provider: Alibaba DashScope
- Models: `qwen3-coder-30b-a3b-instruct`, `qwen3.5-122b-a10b`, `qwen3.5-397b-a17b`, `qwen3-coder-480b-a35b-instruct`
- Session hands: 2
- Layout repetitions: 2
- Remote eval hands: 2
- Samples per model: 48
- CVaR effective 5% tail mass: 2.4 sessions per model

| Model | Mean profit | Win rate | CVaR 5% | Sample count |
|---|---:|---:|---:|---:|
| `qwen3.5-397b-a17b` | 996.25 | 0.3021 | -1850.08 | 48 |
| `qwen3.5-122b-a10b` | -51.75 | 0.3542 | -4145.33 | 48 |
| `qwen3-coder-480b-a35b-instruct` | -198.92 | 0.2396 | -5084.75 | 48 |
| `qwen3-coder-30b-a3b-instruct` | -745.58 | 0.1042 | -5269.25 | 48 |

해석: 397B Qwen3.5 모델이 가장 높은 평균 수익과 가장 덜 나쁜 empirical CVaR을 보였다. 순위는 명목 파라미터 규모에 대해 단조적이지 않다.

### 주 패널 B: NVIDIA 동일 규모 cross-family

Artifact directory: `results/paper_nvidia_120b_4model_family_1h_2rep_budget1`

설정:
- Provider: NVIDIA Build NIM
- Models: `qwen/qwen3.5-122b-a10b`, `mistralai/mistral-small-4-119b-2603`, `nvidia/nemotron-3-super-120b-a12b`, `stockmark/stockmark-2-100b-instruct`
- Target scale: roughly 100B-122B parameters
- Session hands: 1
- Layout repetitions: 2
- Remote eval hands: 1
- Max remote calls per agent per session: 1
- Samples per model: 48

| Model | Mean profit | Win rate | CVaR 5% | Sample count |
|---|---:|---:|---:|---:|
| `nvidia/nemotron-3-super-120b-a12b` | 500.65 | 0.2708 | -1384.17 | 48 |
| `mistralai/mistral-small-4-119b-2603` | -73.19 | 0.2917 | -4150.00 | 48 |
| `qwen/qwen3.5-122b-a10b` | -172.85 | 0.1875 | -3350.42 | 48 |
| `stockmark/stockmark-2-100b-instruct` | -254.60 | 0.2500 | -4267.08 | 48 |

해석: Nemotron이 평균 수익과 empirical CVaR 기준으로 가장 높았다. one-hand horizon과 에이전트당 원격 호출 1회 제약이 있으므로 확증적 family-effect 추정은 아니다.

### 보조 패널 C: NVIDIA 소형 모델

Artifact directory: `results/tiny_nvidia_4model_1h_2rep_budget1_20260425_075542`

| Model | Mean profit | Win rate | CVaR 5% | Sample count |
|---|---:|---:|---:|---:|
| `ibm/granite-3.0-3b-a800m-instruct` | 381.25 | 0.3125 | -1966.67 | 48 |
| `meta/llama-3.2-1b-instruct` | -20.83 | 0.2708 | -2083.33 | 48 |
| `google/gemma-2-2b-it` | -68.75 | 0.2500 | -3833.33 | 48 |
| `microsoft/phi-4-mini-instruct` | -291.67 | 0.1667 | -3916.67 | 48 |

해석: 소형 모델 결과는 소형 모델이 일반적으로 충분하다는 증거가 아니다. 제한된 조건에서 한 소형 모델이 양의 평균 수익을 냈다는 feasibility 근거다.

### 보조 패널 D/E: 정책 스크린

각 model-policy cell은 24 표본이다.

| Policy framing | Qwen top model | Top mean profit | Top CVaR 5% |
|---|---|---:|---:|
| Balanced | `qwen3-4b` | 224.88 | -1166.67 |
| Analytic | `qwen3-4b` | 412.33 | -2566.83 |
| Conservative | `qwen3-8b` | 238.08 | -1301.67 |
| Aggressive | `qwen3-14b` | 254.08 | -1284.33 |

| Policy framing | NVIDIA top model | Top mean profit | Top CVaR 5% |
|---|---|---:|---:|
| Balanced | `nvidia/nemotron-3-super-120b-a12b` | 645.17 | -2067.00 |
| Analytic | `nvidia/nemotron-3-super-120b-a12b` | 598.92 | -2067.00 |
| Conservative | `nvidia/nemotron-3-super-120b-a12b` | 416.67 | -1850.00 |
| Aggressive | `nvidia/nemotron-3-super-120b-a12b` | 598.83 | -3701.67 |

### 연구문제 답변

- RQ1: 고스톱은 숨은 정보, 확률적 전이, 고/스톱 위험, 다중 에이전트 상호작용을 결합하므로 위험 민감적 순차 의사결정 평가에 적합한 compact benchmark다.
- RQ2: Qwen 패널은 명목 파라미터 규모에 대해 단조적이지 않다.
- RQ3: NVIDIA 동일 규모 패널은 family별 기술통계 차이를 보이며, Nemotron이 평균 수익과 empirical CVaR에서 가장 높다.
- RQ4: 소형 모델과 정책 framing 스크린은 양의 소형 모델 성과와 모델별 prompt-policy 효과를 탐색적으로 보여준다.

## English

### Scope

This note summarizes the public result bundles for the Go-Stop AI evaluation paper. The results are descriptive and should not be read as universal model rankings.

The central insight is:

> Go-Stop performance is not explained by parameter scale alone. Model family, policy framing, serving constraints, and tail-risk behavior interact.

### Why Go-Stop Is Used

Go-Stop is a compact stochastic decision environment. Agents must act with hidden hands, uncertain future draws, combinatorial scoring rules, multi-agent interaction, and Go/Stop risk decisions. This makes it useful for evaluating risk-sensitive sequential decision making.

The target behavior is not only winning often. A strong policy should also avoid severe lower-tail losses. The paper reports `mean_profit`, `cvar_5`, `win_rate`, `ruin_probability`, sample count, and support diagnostics together.

### Industrial Link: Advertising Bidding

Advertising bidding is not the same domain as Go-Stop, but the decision structure is similar enough to motivate the evaluation frame. An ad system repeatedly decides whether to bid, lower a bid, or wait under a finite budget. Conversion probability, competing bids, frequency fatigue, remaining budget, and campaign pacing are all uncertain.

Mean ROAS alone can be misleading. A policy may show attractive average performance while spending too fast in specific segments, over-exposing low-quality inventory, or creating rare but severe losses. The Go-Stop harness does not simulate advertising directly; it connects as a policy-evaluation frame for sequential action selection, uncertainty, budget-risk trade-offs, and lower-tail risk control.

### Glossary

- Mean profit: the average session-ending profit for a model.
- CVaR 5%: the average of the worst 5% outcomes. In this paper it is descriptive because sample counts are small.
- Win rate: the share of sessions with positive profit.
- Ruin probability: the probability that a player exhausts capital or reaches an effectively bankrupt state.
- Parameter scale: the nominal parameter size of a model. For MoE models, total parameters and active parameters can differ.
- Model family: the model lineage or family, such as Qwen, Mistral, or Nemotron.
- Policy framing: the decision-making instruction style given to the model.
- `max_remote_calls_per_agent`: the maximum number of remote model API calls an agent can make in one session.
- ROAS: Return on Ad Spend.
- Budget pacing: controlling campaign spend rate across the intended time window.

### Main Panel A: Qwen Parameter-Scale Study

Artifact directory: `results/paper_qwen_4model_param_2h_2rep`

Configuration:
- Provider: Alibaba DashScope
- Models: `qwen3-coder-30b-a3b-instruct`, `qwen3.5-122b-a10b`, `qwen3.5-397b-a17b`, `qwen3-coder-480b-a35b-instruct`
- Session hands: 2
- Layout repetitions: 2
- Remote eval hands: 2
- Samples per model: 48
- CVaR effective 5% tail mass: 2.4 sessions per model

| Model | Mean profit | Win rate | CVaR 5% | Sample count |
|---|---:|---:|---:|---:|
| `qwen3.5-397b-a17b` | 996.25 | 0.3021 | -1850.08 | 48 |
| `qwen3.5-122b-a10b` | -51.75 | 0.3542 | -4145.33 | 48 |
| `qwen3-coder-480b-a35b-instruct` | -198.92 | 0.2396 | -5084.75 | 48 |
| `qwen3-coder-30b-a3b-instruct` | -745.58 | 0.1042 | -5269.25 | 48 |

Interpretation: The 397B Qwen3.5 model produced the highest descriptive mean profit and least severe empirical CVaR. The ranking is not monotone in nominal parameter size.

### Main Panel B: NVIDIA Same-Scale Cross-Family Study

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

| Model | Mean profit | Win rate | CVaR 5% | Sample count |
|---|---:|---:|---:|---:|
| `nvidia/nemotron-3-super-120b-a12b` | 500.65 | 0.2708 | -1384.17 | 48 |
| `mistralai/mistral-small-4-119b-2603` | -73.19 | 0.2917 | -4150.00 | 48 |
| `qwen/qwen3.5-122b-a10b` | -172.85 | 0.1875 | -3350.42 | 48 |
| `stockmark/stockmark-2-100b-instruct` | -254.60 | 0.2500 | -4267.08 | 48 |

Interpretation: Nemotron had the highest descriptive mean profit and least severe empirical CVaR. This is not a confirmatory family-effect estimate because the run used a one-hand horizon and a one-call remote budget.

### Supplementary Panel C: NVIDIA Small Models

Artifact directory: `results/tiny_nvidia_4model_1h_2rep_budget1_20260425_075542`

| Model | Mean profit | Win rate | CVaR 5% | Sample count |
|---|---:|---:|---:|---:|
| `ibm/granite-3.0-3b-a800m-instruct` | 381.25 | 0.3125 | -1966.67 | 48 |
| `meta/llama-3.2-1b-instruct` | -20.83 | 0.2708 | -2083.33 | 48 |
| `google/gemma-2-2b-it` | -68.75 | 0.2500 | -3833.33 | 48 |
| `microsoft/phi-4-mini-instruct` | -291.67 | 0.1667 | -3916.67 | 48 |

Interpretation: The small-model result does not prove that small models are generally sufficient. It shows that a small model can produce positive mean profit in this restricted setting.

### Supplementary Panels D/E: Policy Screens

Each model-policy cell has 24 samples.

| Policy framing | Qwen top model | Top mean profit | Top CVaR 5% |
|---|---|---:|---:|
| Balanced | `qwen3-4b` | 224.88 | -1166.67 |
| Analytic | `qwen3-4b` | 412.33 | -2566.83 |
| Conservative | `qwen3-8b` | 238.08 | -1301.67 |
| Aggressive | `qwen3-14b` | 254.08 | -1284.33 |

| Policy framing | NVIDIA top model | Top mean profit | Top CVaR 5% |
|---|---|---:|---:|
| Balanced | `nvidia/nemotron-3-super-120b-a12b` | 645.17 | -2067.00 |
| Analytic | `nvidia/nemotron-3-super-120b-a12b` | 598.92 | -2067.00 |
| Conservative | `nvidia/nemotron-3-super-120b-a12b` | 416.67 | -1850.00 |
| Aggressive | `nvidia/nemotron-3-super-120b-a12b` | 598.83 | -3701.67 |

### Research Questions Answered

- RQ1: Go-Stop is a plausible compact benchmark for risk-sensitive sequential decision making because it combines hidden information, stochastic transitions, stop-or-continue risk, and multi-agent interaction.
- RQ2: The Qwen panel is not monotone in nominal parameter scale.
- RQ3: The NVIDIA same-scale panel shows visible cross-family differences, with Nemotron leading on mean profit and empirical CVaR.
- RQ4: Small-model and policy-framing screens show exploratory evidence of positive small-model performance and model-specific prompt-policy effects.
