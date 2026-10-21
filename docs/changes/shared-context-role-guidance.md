# 측정 대상·계층적 범위 지침

2026-10-21. 상태: 구현 예정. [동일 계약 비교](../research/shared-context-model-comparison.md)에서 남은 대상/상위 지역 누락을 별도 지침 경로로 보완한다. 의미 성공·앱 적용을 미리 주장하지 않는다.

## Global Constraints

- 기존 417개 실행/설정 파일, v1 요청·지침·결과·fixture는 변경하지 않는다. 새 모듈/합성 테스트만 추가하고 기존 strict dynamic tool schema와 builder/runtime을 재사용한다. 공개/API/DB/worker/UI·제품 기본 모델과 앱/서버 배포 변경0이다.
- 별도 profile `role-guided-shared-context-v1`, identity `issuedigest_role_guided_shared_context_v1`, tool `fill_role_guided_shared_context_v1`로 원래 prompt의 profile과 tool 이름만 바꾸고 명시 지침을 덧붙인다. 원래 자료/후보/필드/한도는 유지한다. caller-owned Model·단일 요청·retry0·repair0·no-store·30초·20,000/출력2,500을 유지한다. 실제 유료 호출0이다.
- 지침: 측정 변수는 수치가 세는 대상/현상을 담는다. 행위/상태 술어만으로 세는 대상을 대체하지 않는다. 지역·집단·기관 범위는 별도 scope에 담고 명시적으로 적용되는 상위/하위 범위 모두 유지한다. context_text의 넓은 문맥은 선택한 역할의 누락을 보충하지 않는다. 기관명을 위치로 추정하거나 명시적 적용 근거 없이 인접 문장에서 범위를 전파하지 않는다. scope 최대4 초과를 숨기기 위해 임의 삭제/합치기하지 않는다. 모호한 역할을 발명하지 않는다. 실제 source가 아닌 합성 예시만 테스트한다.
- 새 결과는 unreviewed·현재 source 전체 재구성·현재 dynamic schema/슬롯/상태 근거·strict nested 타입 검사와 정확 prompt/instructions 해시·bounded usage를 유지한다. v1 결과·해시와 새 결과를 상호 승인하지 않는다. 오류는 비밀/원문/chain 없이 알려진 usage를 보존한다.
- envelope는 새 실제 지침·새 prompt·raw/normalized tool schema 중 큰 값+기존 framing+출력 예약으로 송신 전에 검사한다. 초과면 요청0이고 축약/증액/대체하지 않는다. 합성/모의 검사와 실제 의미 품질은 구분한다.

## Task 1 — 지침 경로와 검증

- [ ] 새 `role_guided_shared_context.py`와 `test_role_guided_shared_context.py`를 TDD로 구현한다. 기존 파일은 불변이다. 기존 runtime/frame builder를 공유하고 복잡한 전체 validator를 복제하지 않는 작은 adapter를 사용한다. 실제 dynamic strict schema·본문/지침/identity·단일 요청/수리0·현재 source/receipt/profile·위변조/unchecked nested/subclass 거부·한도/사용량/클라이언트 수명·preflight와 v1 body 불변을 검증한다. 역할/상위·하위 범위는 독립 합성 출력의 전체 재구성으로 검증하되 mock을 모델의 의미 판단 증거로 사용하지 않는다.
- [ ] 독립 태스크·전체 검토와 전체 QA를 실행하고 기존 코드/증거 보존을 확인한다. 후속 실제 의미 인수/충분한 출력 용량·앱 통합은 미완료로 남긴다.
