# 이중언어 요약 | Bilingual Summary

## 한국어

### 초록

원고는 재현 가능한 4인 고스톱 하네스에서 고정 원격 LLM 정책을 평가한다. 고스톱은 숨은 정보, 불확실한 드로우, 조합적 점수 계산, 고/스톱 위험, 다중 에이전트 상호작용이 짧은 에피소드 안에 들어 있는 확률적 의사결정 환경으로 사용된다. 첫 번째 주 패널은 DashScope의 Qwen 계열 모델 4개를 30B, 122B, 397B, 480B 명목 총 파라미터 규모로 비교한다. 두 번째 주 패널은 NVIDIA Build의 Qwen, Mistral, Nemotron, Stockmark 모델 4개를 100B-122B 전후 규모에서 비교하되, 한 세션 한 손과 에이전트당 원격 호출 1회 제약을 둔다. 보조 실험은 NVIDIA 소형 모델과 네 가지 prompt-policy framing을 비교한다.

결과는 기술통계다. Qwen 패널은 명목 파라미터 규모에 대해 단조적이지 않았고, 제한된 NVIDIA 패널에서는 Nemotron이 mean profit과 empirical CVaR 기준으로 가장 높았으며, 정책 효과는 모델별로 다르게 나타났다.

### 광고 입찰과의 연결

광고 입찰은 고스톱과 같은 게임이 아니지만, 평가해야 하는 의사결정 구조가 닮아 있다. 광고 시스템은 제한된 예산 안에서 매 노출마다 입찰할지, 낮출지, 기다릴지를 결정한다. 전환 확률, 경쟁 입찰가, 빈도 피로, 잔여 예산, 캠페인 pacing은 모두 불확실하다. 따라서 평균 ROAS만 보지 않고 하방 위험, 예산 소진 위험, 드문 큰 손실을 함께 봐야 한다. 본 논문의 고스톱 평가는 광고 시스템을 직접 모사하지 않고, 순차 행동 선택과 위험 통제 평가 프레임으로 연결된다.

### 용어 정의

- Mean profit: 세션 종료 후 모델이 얻은 평균 수익이다.
- CVaR 5%: 가장 나쁜 하위 5% 결과의 평균 손실을 요약하는 하방 위험 지표다.
- Win rate: 세션에서 양의 수익을 낸 비율이다.
- Ruin probability: 자본이 소진되거나 사실상 파산 상태에 도달할 확률이다.
- Parameter scale: 모델의 명목 파라미터 규모다.
- Model family: Qwen, Mistral, Nemotron처럼 모델 계열 또는 개발 계통을 뜻한다.
- Policy framing: 모델에 제시하는 의사결정 지침의 성향이다.
- ROAS: 광고비 대비 매출이다.
- Budget pacing: 캠페인 예산을 기간 전체에 맞게 쓰도록 지출 속도를 조절하는 과정이다.

### 읽기 규칙

- RQ1: 고스톱을 위험 민감적 순차 의사결정 평가 환경으로 볼 수 있는가.
- RQ2: Qwen/DashScope 패널에서 관측 성능이 파라미터 규모에 대해 단조적인가.
- RQ3: 제한된 NVIDIA Build 패널에서 family별 기술통계 차이가 보이는가.
- RQ4: 소형 모델과 정책 framing 효과가 탐색적으로 관찰되는가.
- 본문 결과 번들:
  - `results/paper_qwen_4model_param_2h_2rep`
  - `results/paper_nvidia_120b_4model_family_1h_2rep_budget1`
- 보조 결과 번들:
  - `results/tiny_nvidia_4model_1h_2rep_budget1_20260425_075542`
  - `results/policy_screen_qwen_tiny_*_1h_1rep_20260425_102731`
  - `results/policy_screen_nvidia_*_1h_1rep_20260425_075542`
- 휴리스틱 baseline 산출물은 appendix calibration 전용이다.

### 산출물

- `paper/arxiv_main.tex`: 영어 학술 원고 소스.
- `paper/gostop_ai_evaluation_paper.pdf`: 한국어 섹션과 영어 섹션을 분리한 공개 PDF.
- `dashboard/paper.html`: 한국어 섹션과 영어 섹션을 분리한 웹 논문 페이지.
- `paper/remote_model_results.md`: 한국어 섹션과 영어 섹션을 분리한 결과 요약.
- `paper/ARTIFACTS.md`: 산출물 안내.

## English

### Abstract

The manuscript evaluates fixed remote LLM policies in a reproducible four-player Go-Stop harness. Go-Stop is used as a compact stochastic decision environment with hidden information, uncertain draws, combinatorial scoring, stop-or-continue risk, and multi-agent interaction. The first main panel compares four Qwen-labeled DashScope models at 30B, 122B, 397B, and 480B nominal total parameters. The second main panel compares four roughly 100B-122B NVIDIA Build models from Qwen, Mistral, Nemotron, and Stockmark under a one-call, one-hand constraint. Supplementary screens compare small NVIDIA models and four prompt-policy framings.

The results are descriptive: the Qwen panel is not monotone in nominal parameter scale, the constrained NVIDIA panel ranks Nemotron highest on mean profit and empirical CVaR, and policy effects are model-specific.

### Link to Advertising Bidding

Advertising bidding is not the same domain as Go-Stop, but the decision structure is similar enough to motivate the evaluation frame. An ad system repeatedly decides whether to bid, lower a bid, or wait under a finite budget. Conversion probability, competing bids, frequency fatigue, remaining budget, and campaign pacing are all uncertain. Mean ROAS alone can therefore be misleading; downside risk, budget burn risk, and rare severe losses also matter. The Go-Stop harness does not simulate advertising directly. It connects as a compact evaluation frame for sequential action selection and risk control.

### Glossary

- Mean profit: the average session-ending profit for a model.
- CVaR 5%: the average of the worst 5% outcomes.
- Win rate: the share of sessions with positive profit.
- Ruin probability: the probability that a player exhausts capital or reaches an effectively bankrupt state.
- Parameter scale: the nominal parameter size of a model.
- Model family: the model lineage or family, such as Qwen, Mistral, or Nemotron.
- Policy framing: the decision-making instruction style given to the model.
- ROAS: Return on Ad Spend.
- Budget pacing: controlling campaign spend rate across the intended time window.

### Reading Rule

- RQ1: Go-Stop as a compact risk-sensitive sequential decision environment.
- RQ2: observed monotonicity in the Qwen-labeled DashScope panel.
- RQ3: descriptive cross-family differences in the constrained NVIDIA Build panel.
- RQ4: exploratory small-model and policy-framing effects.
- Main result bundles:
  - `results/paper_qwen_4model_param_2h_2rep`
  - `results/paper_nvidia_120b_4model_family_1h_2rep_budget1`
- Supplementary result bundles:
  - `results/tiny_nvidia_4model_1h_2rep_budget1_20260425_075542`
  - `results/policy_screen_qwen_tiny_*_1h_1rep_20260425_102731`
  - `results/policy_screen_nvidia_*_1h_1rep_20260425_075542`
- Heuristic baseline artifacts are appendix calibration only.

### Artifacts

- `paper/arxiv_main.tex`: English academic manuscript source.
- `paper/gostop_ai_evaluation_paper.pdf`: public PDF with separated Korean and English sections.
- `dashboard/paper.html`: web paper page with separated Korean and English sections.
- `paper/remote_model_results.md`: result summary with separated Korean and English sections.
- `paper/ARTIFACTS.md`: artifact guide.
