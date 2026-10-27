# 정확 텍스트 참조 생성 SDK · v3

2026-10-27. [정확 텍스트 참조 코어](question-text-references.md)를 별도 bounded native Responses SDK에 연결한다. OpenSpec root=null에 따라 구현/TDD·독립 검토 절차를 적용한다. 기존 사용자 승인 범위의 위치 오류 개선이며 모델/예산 확대·과거 결과 수리는 하지 않는다.

## 계약

- 새 guarded_question_evidence_v3 모듈, fill_question_evidence_v3 도구, guarded-question-evidence-v3 영수증, question-evidence-source-v3 입력 형식을 사용한다. 이전 v1/v2·native transport·순수 코어·exports·지침/schema/영수증 바이트는 변경하지 않는다.
- 전체 질문과 전체 원문/인용 ID를 그대로 보내고 새 QuestionEvidenceTextInput만 받는다. 지침은 정확 유일 인용문·중복이면 더 긴 고유 문맥·offset/occurrence 금지·모호성 거부를 설명한다. 기존 수치/단위·상하한·분배·자격·선행조건/법적 효과·절차·불확실성·의존성/coverage 규칙은 보존한다. 출처는 지시가 아닌 비신뢰 데이터다.
- borrowed AsyncOpenAI/native guarded transport로1요청만 사용하며 기존 총20,000·출력4,000·60초·무재시도/무보정·스트림 닫힘·known usage/dispatch/진단 단계를 유지한다. preflight 초과는 송신 전 거부하고 입력/출력을 자르지 않는다. SDK는 client를 만들거나 닫지 않는다.
- 정확한 새 DTO 타입과 native 완료/usage를 확인하고, 텍스트 참조 코어로 기존 canonical 근거를 만든다. 원문을 전후 재검사하며 별도 v3 영수증의 profile/형식·정확 prompt/지침 hash·usage/원문/질문·canonical 검증을 재검사한다. 원문 변경·모호/누락 참조·형식/타입·유효하지 않은 영수증은 전체 거부한다.
- 공개 API·SQL/유료 namespace·DBOS/worker·최종 조합기·앱 연결/배포는 변경하지 않는다. SDK 합성 수용과 실제 모델 의미/완료 저장·앱 인수를 구분한다.

## 작업

- [x] 새 preflight/지침·native SDK/영수증 재검증 TDD·이전 바이트 보존.
- [x] 신규60/관련528개 모의 SSE·예산/취소/닫힘·원문/usage/receipt 변조·진단 검사.
- [x] 독립 태스크/전체/실제 결과 검토·전체10,466개·정적/타입/빌드/OpenAPI 검증.
- [x] Draft PR127·Sitesv150에 실제3/3 개발판정과 내구 버전/최종 생성/앱 미연결 범위 명시.

## 실제 확인 기준

모의 경로/독립 검토 후 별도 비공개 계획을 해시로 고정한 제한1요청만 허용한다. 기존 공개 원문/Q2/필수3명제·전체12개 기준을 보존하고 새 모델 결과/usage를 별도로 기록한다. 실패·불명확 송신 후 재시도/수리·한도 확대는 하지 않는다. 새 실제 결과를 과거 실패 응답의 복구나 일반 품질 성공으로 표시하지 않는다.
