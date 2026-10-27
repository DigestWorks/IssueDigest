# 명시된 근거 범위의 정확 텍스트 참조

2026-10-27. [직전 실제 거부](../research/question-compact-json-validation.md)에서 짧은 수치 표현은 전체 원문 두 곳, 해당 supporting 근거 안에서는 한 곳이었다. 원문 전체의 위치를 유일하게 요구하던 기존 계약을 유지하고 별도 순수 변환기에 명시된 범위의 유일성을 정의한다. OpenSpec root=null이므로 구현/TDD·독립 검토를 적용한다.

## 범위 결정

새 모듈 question_scoped_text_references의 build_question_scoped_text_evidence만 추가한다. 기존 QuestionEvidenceTextInput DTO/schema를 그대로 사용해 같은 canonical QuestionEvidencePropositions v1을 만든다. provider/생성 영수증/내구 실행/저장/API/UI/서버를 연결하거나 기존 converter의 의미를 바꾸지 않는다. 새 생성 버전은 후속이다.

1. 각 proposition의 supporting_refs는 해당 citation 전체에서 정확히 한 번 등장해야 한다. 빈 문구·없는 citation/텍스트·중첩 출현을 포함한 중복은 거부한다. 별도 추론 문장 분할이나 지원 문구 확장을 하지 않는다.
2. subject/predicate/facet refs와 그 모든 nested value refs는 같은 proposition의 이미 확정된 supporting_refs 안에서만 찾는다. citation이 같고 하나의 지원 범위 안에 완전히 들어가는 exact match만 후보로 센다. 겹친 지원 범위가 같은 위치를 여러 번 포함하면 같은 (citation,start,end) 위치 한 개로 센다. 서로 다른 두 위치면 거부한다. 인접 지원 범위를 이어 붙이거나, 다른 proposition/citation에서 문맥을 빌리거나, 전역 유일성으로 fallback하지 않는다.
3. 검색은 겹치는 출현도 센다. 정규화·근사·첫/마지막/가까운 위치 선택·공백 변경·산술·누락 채우기를 하지 않는다. 한 ref라도0개 또는2개 이상이면 전체를 거부한다. 지원/참조 입력 자체를 dedupe하거나 바꾸지 않는다.
4. 모든 위치를 결정한 뒤 기존 canonical builder/validator에 그대로 위임한다. nested value가 facet.refs에 정확히 포함되어야 하는 규칙, proposition support 포함, duplicate refs/ID, bounds/distribution targets·의존 관계/coverage·불확실성 규칙을 유지한다. 지원 범위 안에서 찾았다는 이유로 facet.refs를 자동 추가하지 않는다.
5. 기존 actual-type/DTO·source/question/전후 source hash·mutant 방어를 유지하고 입력을 바꾸지 않는다. 반환은 unreviewed 구조 일치일 뿐 의미·진실·권한·원래 모델 실행 승인/성공이 아니다.

## 작업

- [x] T1: 새 순수 converter·성공/모호성/범위·Unicode/겹침·모든 facet/값·기존 검증 위임의 RED→GREEN.
- [x] 태스크별 및 별도 전체 독립 검토·전체10,662개 검사/정적/타입/빌드/OpenAPI.
- [x] 변경 없는 이전 실제 인자의 비공개 오프라인 진단. 기존 거부/프로필·usage 보존, 변환 결과를 이전 영수증 수리나 새 실제 성공으로 쓰지 않음. 추가 제약 오류가 있으면 그대로 기록.
- [x] 결과/Draft PR130/Sitesv153 갱신. 외부 모델 호출0·개발 서비스/공동DB/main/운영 변경0.

## 수용 경계

전역 중복이 지원 범위에서는 유일한 합성 입력은 정확 canonical 위치와 일치해야 한다. 지원 안의 중복, 모호한 지원 자체, 같은 문구를 포함한 서로 다른 지원 두 개, 지원 밖/다른 citation·원문 변경은 거부한다. 겹친 지원이 같은 위치만 감싸는 경우는 성공하되 refs duplicate·서로 다른 반복 위치는 계속 거부한다. 기존 globally unique 입력과 전체 facet 결과는 이전과 동일해야 한다. 원래 실제 응답이 새 규칙으로도 다른 canonical 제약을 어기면 실패를 유지한다.
