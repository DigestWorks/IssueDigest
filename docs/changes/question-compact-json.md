# 완결된 compact JSON 생성 후보

2026-10-27. [직전 내구 실행 인수](../research/question-text-runtime-validation.md)는 동일 요청 body의 성공/공백 정체 실패를 관측했다. 문자열 밖 공백256 한도에서 차단됐고 완료/usage는 미관측이다. 현재 원인은 단정하지 않는다. OpenSpec root=null이므로 구현/TDD·독립 검토를 적용한다.

## 선택과 한계

공식 [Structured Outputs의 JSON mode 설명](https://developers.openai.com/api/docs/guides/structured-outputs#json-mode)은 JSON 생성 지침 부재 시 공백 반복 가능성을 설명한다. 기존은 strict tool이므로 이 일반 경고가 이번 실패의 원인이라는 증거는 아니다. strict schema/transport는 이미 사용 중이다. 우선 한 변수에 가까운 작은 후보로 JSON 인자를 명시하고 문자열 밖 formatting 공백을 쓰지 않도록 지시한다. 인용문 내부 공백·원문·질문·schema·의미 규칙은 유지한다.

기존 v3 지침/영수증/실패를 바꾸지 않고 별도 guarded-question-evidence-v4 / question-evidence-source-v4 / fill_question_evidence_v4 SDK만 추가한다. 지침에서 기존 한 문장의 출력 지시만 대체한다: "Return one fill_question_evidence_v4 call with complete JSON arguments; no formatting whitespace outside strings, prose or other tools." 다른 의미/불확실성 규칙은 그대로다. 단순 문구 변경이 안정성을 보장하지 않으며 새 계약도 실제 결과에 따라 보류할 수 있다.

## 보존 경계

기존 v1/v2/v3·정확 유일 매칭 코어·transport·원래 실행/저장·서버·앱은 변경하지 않는다. 기존 요청/실패/사용량을 재호출하거나 수리하지 않는다. 고정 모델·native stream·strict schema·1요청/무재시도·20,000/출력4,000/60초와 공백256 차단을 유지한다. 모호한 참조는 여전히 전체 거부한다. 키/개인 원문/사전 질문은 저장소와 공개 Sites에 올리지 않는다.

## 작업

- [x] T1: 별도 v4 SDK/영수증·단일 지침 변경·v3 body 보존·native 모의/TDD.
- [x] 독립 태스크 및 전체 검토·전체10,585개 검사/정적/타입/빌드/API 계약.
- [x] 동일 고정 원문/질문/사전 기준·새 후보1회 실제 검증과 별도 결과 검토. 모델 완료/DTO 통과했지만 반복 수치 참조로 전체 거부. 새 호출 전 preflight/freeze/모의/검토를 통과했고 재시도0.
- [x] 결과/Draft PR129/Sitesv152 갱신. SDK가 통과하더라도 내구 버전·저장/최종·앱 연결은 후속이며 자동 전환하지 않는다.
