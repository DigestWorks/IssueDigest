# 수치 후보 v2의 공유 맥락 생성 연결

2026-10-21. 상태: 별도 SDK·합성/오프라인 검증 완료. 기존 후보 v2를 별도 생성 경로와 저장 결과 재구성에 연결한다. 실제 의미 인수·앱 반영은 별도다.

## Global Constraints

- 기존421개 실행/설정 파일·모든 이전 요청/지침/결과·fixture는 불변이다. 새 `shared_measurement_context_v2.py`, `shared_context_generation_v2.py`와 각각의 합성 테스트만 추가한다. API/OpenAPI/DB/worker/UI·기본 모델·서버/main 변경과 실제 모델 호출은0이다. 기존121개 실제 증거를 보존하며 소진된 유료 runner를 재실행하지 않는다.
- 순수 `SharedMeasurementFrameV2`는 profile `shared-measurement-context-v2`, status unreviewed, 원래 `SharedMeasurementInput`, 완전한 `NumericCandidateIndexV2`, 수치별 resolved 역할/최대4범위/별도 목적과 직접 관계를 저장한다. 중첩 v1 수치 index로 환원하거나 절단된 수량을 새 결과에 섞지 않는다. 입력의 공통 맥락/보고 사건/명시 binding 계약은 유지한다. 새 빌더/검증기는 `build_shared_measurement_frame_v2`, `validate_shared_measurement_frame_v2`다.
- 동일한 context/event ID의 중복·미참조/누락, 수치 중복 binding, 다른 인용 역할/목적/범위, 중복 위치 범위, 합계4초과 범위, 수치 자신의 문장이 아닌 상태 근거를 거부한다. known status는 전체 수치 문장, known reporting tense는 명시 predicate가 필요하다. 대상/발표자·시제/값 상태·목적/조건/전망 근거·비교 기준을 분리한다. 정확 문맥 anchor의 반복/Unicode/공백과 전체 관계 statement·cue·두 수치/대상·직접 관계·중복쌍/순환 검사를 보존한다. 구조 검사는 의미/진실/중립/권한/완전성 인증이 아니다.
- v2 index를 먼저 source에서 재구성한다. 기존의 문장 ID·정확 anchor·관계·동적 schema 함수를 읽기 전용 재사용할 수 있다. 이 함수들은 공통 structural 필드만 읽으므로, 타입 경계에 한정한 명시 `cast`는 허용하되 index 변환/직렬화 세탁/monkey patch/전역 교체는 금지한다. 관계 검사는 v2의 전체 표현(단위·근사 포함)을 사용하고 문맥 전체의 statement 포함 검사 후 짧은 anchor를 저장한다. 공통 함수의 v1 후보 재생성에 의존하지 않는다.
- 생성 profile은 `shared-context-generation-v2`, provider identity `issuedigest_shared_context_v2`, strict tool `fill_shared_context_v2`다. 후보 v2의 전체 원문·문장·수치 표현/atom별단위/qualifier를 prompt에 보존한다. 동적 후보/문장/상태/맥락12·사건12 slot 제한, 역할 지침과 bounded borrowed-model runtime을 재사용한다. prompt/instructions 정확 SHA256, 전체 v2 frame, 알려진 usage를 별도 result에 저장한다. 공개 함수는 `shared_context_prompt_v2`, `create_shared_context_framer_v2`, `run_shared_context_framer_v2`, `validate_shared_context_generation_v2`다.
- 원문·지침·raw/normalized schema 최대 byte·framing2048·출력2500의 합이20000을 넘으면 송신 전 거부한다. 전체20000/출력2500, timeout30초/no-store, 요청1회, retry/repair/fallback0, caller 소유 필수 Model과 client lifecycle을 유지한다. key/env/client/I/O 생성은 하지 않는다. 실패 시 실제 알려진 usage만 보존하고 무료로 단정하지 않는다. source/동적 실제 nested 타입·tuple/canonical guard를 직렬화 전에 검사하며 저장 결과의 전체 재구성·현행 schema와 모든 receipt를 재검증한다. v1/v2 교차·위조/누락/추가·source drift는 정리된 오류로 전체 거부한다.
- 실제 연구 자료/UUID/긴 인용은 테스트나 문서에 넣지 않는다. 독립 합성 자료·FunctionModel/mock HTTP만 사용한다. 신규 테스트의 module import/reload 격리는 기존 v2 테스트 방식을 따라 전체 순서에서도 class identity를 보존한다. controller는 기존 G/H의 오프라인 prompt 용량·후보 보존만 확인하며 실제 의미 성공으로 세지 않는다.

## Task 1 — v2 순수 프레임·bounded SDK

- [x] TDD RED→최소 구현→GREEN으로 두 모듈과 테스트를 추가한다. 비어 있지 않은 공유 맥락·학교/사람/내외·range·문맥/범위/사건·관계 원문 보존 및 v2 전체 재구성을 확인한다. 입력/결과의 nested unchecked 타입·컨테이너·버전/receipt·source drift, 무후보/용량 초과 송신0·runtime1회/usage/거부·기존 v1 request/output 불변과 no-I/O를 검증한다. 기능 경계에 집중하며 단순 테스트 수 확장은 피한다.
- [x] 독립 태스크/최종 검토, controller의 전체QA·기존421파일/121증거 불변·원래 G/H 오프라인 prompt 검증, 소유 자원 정리를 완료한다. 문서/PR/Sites에서 구현·실제 의미·앱 적용을 구분한다.

## 구현·검증 기록

실행 `8cf2e4b1e9da4c2b4c4804dcb767535804aa5bb3`에서 전체7,206개(Python6,386+JavaScript820)와 Ruff/format/mypy·ESLint/TypeScript/build/OpenAPI 검사를 통과했다. 기존421개 실행/설정 파일과 이전121개 실제 증거는 불변이며 새 모듈2개/테스트2개만 추가했다. 독립 태스크·최종 검토와 소유 자원 정리는 진행 기록을 따른다.

기존 G/H의 원문 전체를 새 요청으로 재구성해 후보 표현·atom별 단위·근사 표현과 요청 한도를 확인했다. 이는 실제 모델 의미 성공/출력 충분성 검증이 아니며 이전 실패를 수정하지 않는다. 실제 모델 호출·앱/서버/main 변경0이다. 새 경로의 미관측 의미 인수와 수치별 범위 누락·전체 앱 통합은 남아 있다.

검증 중 새 테스트의 모듈/패키지 참조 격리 문제를 수정하고 순서 회귀1,189개를 통과했다. 독립 태스크 검토에서 중복 fixture를 공통 import로 정리했으며 최종 검토는 C0/I0/M0이다. 이전 중단·실패 기록을 보존하고 최종 전체QA만 완료로 센다. 소유 QA컨테이너2개/SDD를 정리했으며 앱은 변경하지 않았다.
