# Bilingual Summary | 이중언어 요약

This paper package now centers a blocked factorial LLM study rather than a heuristic-only benchmark note.

이 논문 패키지는 이제 휴리스틱 4종 벤치마크가 아니라, `모델 정체성 vs 프롬프트 전략`을 비교하는 blocked factorial LLM study를 중심에 둔다.

## Abstract | 초록

English:
The repository now frames four-player Go-Stop evaluation as a blocked factorial LLM study. The main question is whether model identity or prompt strategy explains more variance in long-run Go-Stop performance. The fixed study design uses a pinned four-model OpenRouter panel and four canonical English prompt strategies (`Balanced`, `Analytic`, `Conservative`, `Aggressive`). The primary analysis reports partial eta-squared on mean session profit, while `CVaR_5` and ruin probability remain secondary robustness metrics. The previously checked-in four-heuristic study is retained as appendix calibration rather than the main result.

Korean:
이 저장소는 이제 4인 고스톱 평가를 blocked factorial LLM study로 정식화한다. 핵심 질문은 장기 성과의 분산을 더 크게 설명하는 요인이 `모델 자체`인지 `전략 프롬프트`인지다. 메인 설계는 고정된 OpenRouter 4개 모델 패널과 네 가지 영문 전략 프롬프트(`Balanced`, `Analytic`, `Conservative`, `Aggressive`)를 사용한다. 1차 분석은 mean session profit에 대한 partial eta-squared 비교이고, `CVaR_5`와 ruin probability는 2차 robustness 지표로 둔다. 기존 4개 휴리스틱 연구는 이제 메인 결과가 아니라 appendix calibration으로 남는다.

## Main Reading Rule | 메인 읽기 규칙

English:
- Main paper question: `model vs strategy`
- Main result bundle: output of `scripts/run_openrouter_factorial_study.py`
- Main figures: interaction, effect-size comparison, secondary risk summary
- Heuristic baseline bundle: appendix-only calibration

Korean:
- 본문 질문: `모델 vs 전략`
- 본문 결과 번들: `scripts/run_openrouter_factorial_study.py` 산출물
- 본문 그림: interaction plot, effect-size 비교, secondary risk summary
- 휴리스틱 baseline 번들: appendix calibration 전용

## Artifact Reminder | 아티팩트 안내

English:
- `paper/arxiv_main.tex`: manuscript source
- `paper/ARTIFACTS.md`: figure/table provenance
- `paper/artifacts/`: baseline appendix calibration bundle currently checked in
- future factorial bundles: generated under `results/openrouter_factorial_study*`

Korean:
- `paper/arxiv_main.tex`: 본문 소스
- `paper/ARTIFACTS.md`: 그림/표 provenance
- `paper/artifacts/`: 현재 체크인된 appendix calibration 번들
- 향후 factorial 번들: `results/openrouter_factorial_study*` 아래 생성
