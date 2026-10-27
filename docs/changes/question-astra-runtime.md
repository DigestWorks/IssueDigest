# Astra의 내구 근거·최종 생성 지원

2026-10-27. [전체 인수 계획](question-native-final-acceptance.md)을 준비하며 기존 runner/저장/최종 SDK가 Sol만 허용한다는 것을 무송신2개 검사로 확인했다. standalone 성공을 전체 경로 성공으로 취급하지 않고, 명시적인 모델 계약 확장을 먼저 구현한다. 기본 Sol·현재 앱 설정은 그대로다.

## 모델 계약

기존 Sol은 근거v2/v3/v5·최종v1의 모델/예약·identity/hash/재생 계약을 유지한다. Astra는 근거v5에만 추가하며 v2/v3/v4와 임의 모델은 허용하지 않는다. 같은 최종 묶음의 근거 작업 모델은 모두 같아야 하고 최종 작업/영수증의 model과 일치해야 한다. Astra 최종 SDK는v5 근거만 받는다. 근거 영수증에 없는 model provenance를 추정하지 않으며 SQL 작업/원요청/journal에서 결합한다.

기존 최종 영수증의 명시 model 필드는 정확한 Sol/Astra Literal만 허용하도록 확장하고 실제 호출 모델을 기록한다. profile/tool/input_format·지침·canonical 입력·표시 schema는 유지한다. model을 제외한 Sol의 기존 최종 요청 bytes와 영수증은 그대로 수용한다. 저장 읽기는 receipt.model==job.model과 자식 모델 동등을 재검증한다. 원래 ID/hash에 이미 있는 model을 유지하고 재접수 중 모델 변경은 충돌 처리한다. 새로운 큐/자동 fallback/재시도는 만들지 않는다.

Astra는 분석/최종 각각 예약>=1달러를 DB/접수/읽기/실행에서 강제하고 기존 공유 월 예산/작업 상한을 유지한다. Sol의 기존 작은 예약을 올리거나 되돌려 쓰지 않는다. 같은 요청/부분 재개·권한/취소/원문·송신 의도/known usage 규칙을 보존한다.

## 저장

migration0015로 evidence_jobs 모델/profile CHECK를 Sol의 기존2/3/5 또는 Astra/v5로, briefing_jobs 모델/profile CHECK를 두 모델/최종v1로 확장한다. 두 테이블에 Astra 예약>=1 조건을 추가한다. 양 테이블 model/profile/reservation 열·정확한 제약/검증 상태를 모두 확인한 뒤 DDL을 시작하고 unknown/중복/NOT VALID/SQL 리터럴 변형을 거부한다.

역사 migration이 현재 Table metadata를 import하므로 metadata의 baseline CHECK는 바꾸지 않고 설명만 보완한다. 이전 migration은 변경하지 않는다. fresh base→head/0014→0015와 기존 Sol행 보존·재생을 확인한다. Astra 작업이 어느 쪽에든 남으면 downgrade를 거부하고 삭제하지 않는다. 없다면0014의 정확한 제약으로 되돌린다.

## 작업

- [x] T1: 저장 모델/모델-예약 정책·migration0015·이전/신규/거부/downgrade TDD.
- [x] T2: 최종SDK·dispatch/runner/worker·저장 읽기 모델 결합·Sol byte 회귀·native 합성 Astra ANSWER 저장/재열람/재접수0. 구현 완료, 독립 검토 대기.
- [x] 태스크별·전체 독립 검토와 전체10,936개/정적/타입/빌드/OpenAPI.
- [x] 전체 인수 도구98개·모의/독립 승인·새 실제 분석1/최종1→SQL 재열람·재접수0. [결과](../research/question-native-final-validation.md)에 한 사례의 의미 판정과 남은 앱 경계를 기록.

## 적용 경계

공개 API/화면·환경 기본 모델·현재 앱·공동DB/운영/main·Actions는 바꾸지 않는다. SDK/내구 모델 지원과 모델 채택은 별개다. 가격/실제 의미·SQL/앱 인수는 각각 검증하고 기존 실패/standalone 성공을 다른 실행으로 재라벨하지 않는다.
