# 복합 단위·근사 표현 수치 후보 v2

2026-10-21. 상태: 순수 계약·합성/오프라인 재구성 완료, 생성 SDK·실제 의미·앱 통합 미완료. [새 자료 점검](../research/role-guidance-acceptance.md)의 결정적 후보 누락을 먼저 보완한다. 역할/범위 의미 판단·AI 생성·앱 통합과 분리한다.

## Global Constraints

- 기존419개 실행/설정 파일·v1 후보/요청/지침/결과·fixture는 불변이다. 새 `numeric_candidates_v2.py`와 합성 테스트만 추가하며 v1 함수를 기본값에서 바꾸거나 전역 상수를 덮지 않는다. 앱/API/OpenAPI/DB/worker/UI·기본 모델·서버/main 변경과 실제 모델 호출0이다.
- 순수 함수 `build_numeric_candidates_v2`, `validate_numeric_candidates_v2`, `numeric_candidates_packet_v2` 및 별도 `NumericCandidateV2`/`NumericCandidateIndexV2`를 제공한다. profile은 `numeric-candidates-v2`, status는 unreviewed다. provenance·문장 분할/ID·수치 순서/ID·기존 ASCII/날짜/법령/범위 문법·20인용/256후보 한도는 기존 계약을 재사용한다. 명시 지원 문법 밖은 v1과 같은 보수적 후보로 남기며 의미를 추정하지 않는다.
- v2는 학교 단위 `개교`를 긴 단위로 인식하고 수량 뒤 `내외`를 별도 qualifier로 보존한다. 숫자와 사람 단위 사이 `여`(예: `47여명`, `47여 명`)를 근사 qualifier로 분리해 number=`47`, qualifier=`여`, unit=`명`의 정확 원문 span을 유지한다. `여`를 수치에 끼워 넣거나 unit에 섞지 않고 number lexical hint로 분류한다. 붙은 이름/식별자나 단위 뒤 이어진 다른 단어를 수량으로 단정하지 않는다. 새 단위/내외는 명시적 끝·공백/구두점·기존 조사 어미 등 경계에서만 확장한다. `여`는 이번에 사람 단위 앞만 지원하며 일반 한국어 형태소/모든 계수사 처리를 주장하지 않는다.
- 범위 양끝의 숫자·각자 원문에 있는 단위와 중간 `여`, 기존 접두/접미·새 `내외`를 보존한다. 누락 단위 전파·합산·정규화·상하한 계산은 없다. qualifier 최대4(접두1+양끝 중간2+접미1), atom 최대2다. 중간 qualifier는 해당 atom의 number 뒤/unit 앞에 있는 정확 `여`와 unit `명`에만 허용한다. 기존 qualifier의 범위 밖 위치와 겹침 금지·정렬·모든 자식 원문/인용 일치 검사를 유지한다. 원래 v1 validator를 느슨하게 만들지 않는다.
- 기존 lexical atom/span/문장 도구를 재사용하고 다른 중간 qualifier를 처리해야 하는 v2 scanner/모델만 분리한다. 변경된 grammar를 숨긴 기존 profile/기존 SDK 연결이나 monkey patch를 하지 않는다. source·packet 전체를 현재 source에서 재생성해 누락/추가/위변조·잘못된 실제 nested 타입/unchecked container/subclass·다른 버전을 거부하며 오류는 원문/내부 chain 없이 정리한다. key/env/client/I/O를 만들지 않는다.
- 테스트는 실제 연구 원문·UUID·긴 quote 대신 독립 합성 수치/문장을 사용한다. 이전 실제 증거는 수정하거나 새 성공으로 세지 않는다. controller는 원래 G/H 자료를 오프라인에서만 재구성해 새 후보/옛 후보를 별도로 비교한다. 이는 AI 의미 인수나 근사값을 정확값으로 바꿀 수 있다는 인증이 아니다.

## Task 1 — 순수 v2와 합성 검증

- [x] TDD RED→최소 구현→GREEN으로 새 모듈/테스트를 구현한다. 정확 Unicode/공백 offset·학교/사람/근사 표현·접두/범위/접미 조합·최대4qualifier·지원 경계/단어/식별자 음성 사례·구문 비지원의 보수적 보존·날짜/법령 우선·원래 v1 출력/패킷 불변·source/provenance drift·누락/추가/위조·nested 타입/컨테이너·버전 교차 거부·한도 독립 검사·무I/O를 검증한다. 기존 전체 grammar 복사나 테스트 수 늘리기보다 변경 경계에 집중한다.
- [x] 독립 태스크·최종 검토, 전체 테스트/린트/타입/빌드/계약·기존 코드/증거 보존, 원래 자료의 오프라인 후보 재구성을 확인한다. v2의 생성 SDK 연결·새 실제 의미 인수·앱 통합은 후속으로 둔다.

## 구현·검증 기록

실행 `9b409f08c9ab4f4155ccc939a4fc281874ca0155`에서 전체7,099개(Python6,279+JavaScript820)와 Ruff/format/mypy·ESLint/TypeScript/build/OpenAPI 검사를 통과했다. 기존419실행/설정 파일과 이전121증거를 보존했고 새 모듈/테스트만 추가했다. 태스크 검토에서 기간 근사 누락과 식별자 오인2건을 재현·수정하고 회귀 검사했다. 첫 QA는 경계 수정 전 중단했고 다음 QA는 새 테스트의 모듈 격리 문제로237실패했다. 두 기록을 보존하고 격리 수정 후 최종 전체 결과만 완료로 보고한다. 독립 태스크/최종 검토와 소유 QA/SDD 정리 영수증은 진행 기록을 따른다.

원래 G/H 자료를 별도 v2 index로 재구성해 알려진 학교·사람 단위/근사 표현 누락을 확인했다. 원래 v1 index 두 건은 byte-identical이며 과거 미호출·실패를 새 의미 성공으로 바꾸지 않는다. 실제 모델 호출0이고 숫자·단위·근사 표식 보존은 역할/범위·진실·중립·앱 품질 인증이 아니다. 지원 문법은 유한하며 모든 한국어 단위/근사 표현 처리를 주장하지 않는다.
