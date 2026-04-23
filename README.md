# 4인 고스톱 AI 평가 하네스 v1.1

이 저장소는 고스톱 게임 서비스가 아니라, **고정 AI 정책의 장기 수익성과 리스크를 비교하는 평가 하네스**다.

## 포함 범위
- 4인 시작, 참여 결정 단계 후 3인 활성 본게임
- 죽기, 연사 금지, 광팔이
- 총통, 총통 숨기기, 흔들기, 중간 폭탄, 자폭
- 일반 나가리, 쇼당, 국진 이동
- 수익/리스크 중심 메트릭과 재현 가능한 시드 계층

## 빠른 실행
```bash
python3 main.py --output-dir results/paper_run
```

기본 자본은 플레이어당 `100,000원`, 기본 판돈은 `점당 100원`이다.
세션은 2명 오링될 때까지 진행한다.

생성 산출물:
- `report.json`
- `manifest.json`
- `agent_performance_table.csv`
- `cross_play_results.json`
- `session_logs.jsonl`

## 논문용 재현 절차
1. 동일 Python 버전에서 실행한다. 현재 확인 버전은 `Python 3.13.5`.
2. 동일 seed와 동일 결과 폴더를 사용한다.
3. `results/<run_name>/manifest.json`을 방법론 부록에 첨부한다.
4. 논문 표는 `agent_performance_table.csv`를 기준으로 작성한다.
5. 사건 분석은 `session_logs.jsonl`을 기준으로 수행한다.

## 핵심 지표
- `mean_profit`
- `cvar_5`
- `ruin_probability`
- `variance`
- `win_rate`
- `profit_per_hand`
- `hands_survived`
- `session_completed_rate`
- `early_exit_rate`
- `forced_gwang_sell_rate`
- `showdown_frequency`
- `showdown_ev_gain`
- `showdown_misplay_rate`

## 원격 모델 평가
`RemoteModelAgent`는 OpenAI Responses API를 직접 호출한다.

필수 환경 변수:
```bash
export OPENAI_API_KEY=...
```

선택 환경 변수:
```bash
export OPENAI_BASE_URL=https://api.openai.com/v1
```

원격 모델은 구조화 출력으로 `choice_index`만 반환해야 한다.

`OpenRouterModelAgent`는 OpenRouter `chat/completions`를 직접 호출한다.

필수 환경 변수:
```bash
export OPENROUTER_API_KEY=...
```

선택 환경 변수:
```bash
export OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
export OPENROUTER_HTTP_REFERER=https://godori.dahanda.dev
export OPENROUTER_APP_TITLE=godori-eval
export OPENROUTER_SELECTOR_URL=https://<your-server>/...
export OPENROUTER_SELECTOR_TOKEN=...
```

같은 family 내 파라미터 크기 가설 실험:
```bash
python3 scripts/run_openrouter_family_study.py \
  --family gemma \
  --base-seeds 7,11,13,17,19 \
  --output-dir results/openrouter_gemma_family_study
```

단일 seed 빠른 점검만 필요하면 `python3 -m experiments.openrouter_family_eval`을 쓰고, 전수 스윕은 위 스크립트를 쓴다.

OpenRouter 무료모델 선택을 서버에서 받으려면:
```bash
export OPENROUTER_SELECTOR_URL=https://<your-server>/...
export OPENROUTER_SELECTOR_TOKEN=...
```

서버에는 아래 JSON이 전송된다:
```json
{
  "family": "gemma",
  "free_only": true,
  "same_family_only": true,
  "count": 4,
  "strategy": "parameter_sweep"
}
```

응답은 문자열 배열 또는 `models`/`model_ids`/`items` 필드에 모델 ID 목록을 담으면 된다.

대시보드 데이터 번들 생성:
```bash
python3 scripts/build_dashboard_data.py \
  --results-root results
```

개별 run만 반영하려면:
```bash
python3 scripts/build_dashboard_data.py \
  --results-dir results/paper_run_v2 \
  --run-name paper_run_v2
```

대시보드 로컬 실행:
```bash
python3 -m http.server 8000
# http://127.0.0.1:8000/dashboard/
```

## 서버 배포 규칙

배포 절차는 `AGENTS.md`의 배포 규칙을 따른다.
## 주의
- baseline 4종은 sanity check용이다.
- 메인 비교 대상은 외부 고정 정책, 원격 모델, 재생 정책이다.
- 설명 로그는 저장만 하며 정책 개선에 사용하지 않는다.
