# AGENTS 규칙

## 서버 배포 규칙
- 배포는 공개 문서(`README.md`)에 구체적인 대상 서버, IP, 키 경로를 기록하지 않는다.
- 배포는 `./scripts/deploy_server.sh` 한 가지만 사용한다.
- `GOSTOP_DEPLOY_HOST`는 환경변수로 반드시 전달한다.
  - 형식: `user@host`
- `GOSTOP_DEPLOY_KEY`는 필요 시 환경변수로 전달한다.
- `GOSTOP_DEPLOY_DIR`는 필요 시 환경변수로 덮어쓴다.
  - 기본값은 `/home/ubuntu/projects/gostop_ai_evaluation`
- `GOSTOP_RUN_TESTS=1` 시 배포 후 테스트를 실행한다.
- 배포 예시:
  ```bash
  export GOSTOP_DEPLOY_HOST="user@host"
  export GOSTOP_DEPLOY_DIR="/home/ubuntu/projects/gostop_ai_evaluation"
  export GOSTOP_DEPLOY_KEY="/absolute/path/to/key"
  export GOSTOP_RUN_TESTS=1
  ./scripts/deploy_server.sh
  ```
