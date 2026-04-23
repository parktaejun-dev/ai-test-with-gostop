# References

## Go-Stop / Hwatu 구현 레퍼런스
- [reidlindsay/gostop](https://github.com/reidlindsay/gostop)
  - Python 기반 Go-Stop 구현. 규칙 엔진 구조와 테스트 분리 방식 참고용.
- [jihyun00/gostop](https://github.com/jihyun00/gostop)
  - C 기반 구현. `rule.c`, `rule.h`가 분리돼 있어 룰 함수 단위 비교에 적합.
- [kimsoomin7725/Hwatu-Gostop-Game](https://github.com/kimsoomin7725/Hwatu-Gostop-Game)
  - C# 기반 화투 게임 구현. 게임 루프와 상태 관리 분해 방식 참고용.
- [rei-developer/godori](https://github.com/rei-developer/godori)
  - Go 기반 Godori 엔진. 엔진/서비스 분리형 구조 참고용.

## 평가 하네스 / 게임 연구 인프라
- [OpenSpiel repository](https://github.com/google-deepmind/open_spiel)
  - 다양한 게임 환경과 알고리즘을 공통 API로 제공하는 대표적 평가 프레임워크.
- [OpenSpiel: A Framework for Reinforcement Learning in Games](https://arxiv.org/abs/1908.09453)
  - 게임 AI 평가 환경 설계, 재현성, 공통 인터페이스 정리에 직접 관련된다.

## 불완전 정보 / Cross-play / Zero-shot coordination
- [Evaluating and Modelling Hanabi-Playing Agents](https://arxiv.org/abs/1704.07069)
  - 숨은 정보 카드게임에서 에이전트 모델링과 파트너 적합성 문제를 다룬 초기 기준선.
- [Evaluating the Rainbow DQN Agent in Hanabi with Unseen Partners](https://arxiv.org/abs/2004.13291)
  - self-play 성능과 unseen-partner cross-play 성능이 다를 수 있다는 점을 보여준다.
- ["Other-Play" for Zero-Shot Coordination](https://arxiv.org/abs/2003.02979)
  - 새로운 상대와의 협업 평가를 self-play와 분리해야 한다는 관점에 직접 연결된다.
- [Any-Play: An Intrinsic Augmentation for Zero-Shot Coordination](https://arxiv.org/abs/2201.12436)
  - inter-algorithm cross-play를 명시적으로 평가 기준으로 잡는다.
- [Behavioral Differences is the Key of Ad-hoc Team Cooperation in Multiplayer Games Hanabi](https://arxiv.org/abs/2303.06775)
  - 정책 간 행동 차이가 cross-play 실패와 강하게 연결된다는 실험적 근거를 제공한다.
- [Towards Few-shot Coordination: Revisiting Ad-hoc Teamplay Challenge In the Game of Hanabi](https://arxiv.org/abs/2308.10284)
  - zero-shot 이후 few-shot 적응까지 포함한 협업 평가 확장 방향을 정리한다.

## 리스크 민감 평가
- [Risk-Sensitive Bayesian Games for Multi-Agent Reinforcement Learning under Policy Uncertainty](https://arxiv.org/abs/2203.10045)
  - 상대 정책 불확실성을 가진 다중 에이전트 환경에서 risk-sensitive 관점을 다룬다.
- [Near-Minimax-Optimal Risk-Sensitive Reinforcement Learning with CVaR](https://arxiv.org/abs/2302.03201)
  - CVaR를 명시적으로 최적화 대상으로 두는 이유를 뒷받침한다.

## 본 저장소에서의 활용
- Go-Stop 구현 레퍼런스는 카드/이벤트/정산 규칙 교차 확인용으로 사용한다.
- Hanabi / zero-shot coordination 문헌은 cross-play와 unseen-partner 평가 설계를 정당화하는 근거로 사용한다.
- risk-sensitive 문헌은 `cvar_5`, `ruin_probability`를 핵심 지표로 두는 방법론 근거로 사용한다.
