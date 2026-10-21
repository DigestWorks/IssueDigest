# 측정 대상·계층적 범위 지침

2026-10-21. 상태: SDK·합성 검증 완료, 실제 의미 인수·앱 적용 미완료. [동일 계약 비교](../research/shared-context-model-comparison.md)에서 남은 대상/상위 지역 누락을 별도 지침 경로로 보완한다. 의미 성공·앱 적용을 미리 주장하지 않는다.

## Global Constraints

- 기존 417개 실행/설정 파일, v1 요청·지침·결과·fixture는 변경하지 않는다. 새 모듈/합성 테스트만 추가하고 기존 strict dynamic tool schema와 builder/runtime을 재사용한다. 공개/API/DB/worker/UI·제품 기본 모델과 앱/서버 배포 변경0이다.
- 별도 profile `role-guided-shared-context-v1`, identity `issuedigest_role_guided_shared_context_v1`, tool `fill_role_guided_shared_context_v1`로 원래 prompt의 profile과 tool 이름만 바꾸고 명시 지침을 덧붙인다. 원래 자료/후보/필드/한도는 유지한다. caller-owned Model·단일 요청·retry0·repair0·no-store·30초·20,000/출력2,500을 유지한다. 실제 유료 호출0이다.
- 지침: 측정 변수는 수치가 세는 대상/현상을 담는다. 행위/상태 술어만으로 세는 대상을 대체하지 않는다. 지역·집단·기관 범위는 별도 scope에 담고 명시적으로 적용되는 상위/하위 범위 모두 유지한다. context_text의 넓은 문맥은 선택한 역할의 누락을 보충하지 않는다. 기관명을 위치로 추정하거나 명시적 적용 근거 없이 인접 문장에서 범위를 전파하지 않는다. scope 최대4 초과를 숨기기 위해 임의 삭제/합치기하지 않는다. 모호한 역할을 발명하지 않는다. 실제 source가 아닌 합성 예시만 테스트한다.
- 새 결과는 unreviewed·현재 source 전체 재구성·현재 dynamic schema/슬롯/상태 근거·strict nested 타입 검사와 정확 prompt/instructions 해시·bounded usage를 유지한다. v1 결과·해시와 새 결과를 상호 승인하지 않는다. 오류는 비밀/원문/chain 없이 알려진 usage를 보존한다.
- envelope는 새 실제 지침·새 prompt·raw/normalized tool schema 중 큰 값+기존 framing+출력 예약으로 송신 전에 검사한다. 초과면 요청0이고 축약/증액/대체하지 않는다. 합성/모의 검사와 실제 의미 품질은 구분한다.

## Task 1 — 지침 경로와 검증

- [x] 새 `role_guided_shared_context.py`와 `test_role_guided_shared_context.py`를 TDD로 구현한다. 기존 파일은 불변이다. 기존 runtime/frame builder를 공유하고 복잡한 전체 validator를 복제하지 않는 작은 adapter를 사용한다. 실제 dynamic strict schema·본문/지침/identity·단일 요청/수리0·현재 source/receipt/profile·위변조/unchecked nested/subclass 거부·한도/사용량/클라이언트 수명·preflight와 v1 body 불변을 검증한다. 역할/상위·하위 범위는 독립 합성 출력의 전체 재구성으로 검증하되 mock을 모델의 의미 판단 증거로 사용하지 않는다.
- [x] 독립 태스크·전체 검토와 전체 QA를 실행하고 기존 코드/증거 보존을 확인한다. 후속 실제 의미 인수/충분한 출력 용량·앱 통합은 미완료로 남긴다.

## 검증 기록

실행 `f8a235763b0b2442f47f8b329c681d4cb396ffaa`에서 전체7,049개(Python6,229+JavaScript820)와 정적 검사·빌드·OpenAPI 검사를 통과했다. 기존417실행/설정 파일과 이전 실제 증거98개를 보존했다. 실제 모델 호출·앱/서버/main 변경0이다. 합성 출력 재구성/지침 전송은 모델이 실제 자료의 의미를 개선했다는 증거가 아니며 미관측 자료·충분한 출력 인수는 후속이다.

기존4자료의 원문 전체를 유지한 새 지침 preflight는 모두 수용했다. envelope는18,865/17,387/17,799/17,697이며20,000 한도를 유지했다. 실제 SDK 형식의 빈 모의 응답4회로 요청·wrapper만 확인했고 실제 모델 호출은0이다. 최대 record/장문 역할의 충분한 출력이나 의미 개선은 확인하지 않았다.

설치된 SDK는 사용량 초과를 public 응답 capture 이전에 거부할 수 있다. 이 경우 known_usage=null이며 무료라는 뜻이 아니다. 원래 runtime을 보존하고 알려진 사용량이 남는 오류와 구분한다.

## 후속 실제 인수

[새 자료 점검](../research/role-guidance-acceptance.md)에서 사전 후보 누락 차단1·실제1회 반환/의미0/1을 확인했다. 이 구현 당시의 실제0회와 구분하며 지침이 의미 문제를 해결했다고 주장하지 않는다. 앱 적용은 계속 보류하고 후보 단위·근사 표현과 수치별 범위 누락을 후속으로 둔다.
