# 명시적 근거 필드 지침 · 실제 인수

2026-10-26 KST. [guarded-v2 계약](../changes/guarded-question-reference-rules.md)의 구현·코드 검토 후 같은 개발 자료로 최대1회 실제 인수를 진행한다. 이전 [guarded-v1 거부](guarded-question-acceptance.md)와 입력·필수 기준/루브릭·모델/상한은 유지하고 정확328byte field-rule 지침만 새 SDK에 추가한다. 기존 응답·원문·기준·사용량/소진 잠금은 변경하지 않는다.

## 응답 전 고정

원래 source/criteria/rubric 파일을 bytes 그대로 복사한다. 선택 질문Q2·필수P5/P9/P10, 전체12기준/다른9개 미평가는 유지한다. 모델 `gpt-6.1-sol`, reasoning low/service_tier default, 출력4,000/전체20,000·60초 operation/별도1초 cooperative close·무재시도/strict tool1개/no-store를 유지한다. 새 지침으로 정확한 기존 입력의 envelope는19,907이며 추가 지침 때문에 입력을 줄이거나 상한을 높이지 않는다.

실제 송신 전 현재 실행 파일·protocol·runner·정확 wire·원문/질문/기준·schema/지침·예산 hash를 새 namespace에 고정하고 소진 잠금을 먼저 기록한다. 실패·거부·타임아웃 후 재호출/수리·모델/자료/한도 교체는 없다. actual API 호출은 최대1회이며 합성 MockTransport의 횟수와 구분한다. old paid runner는 실행하지 않는다. 원문/응답/SSE는 읽은 부분만 private로 보존하고 키/헤더를 기록하지 않는다.

## 판정

HTTP/모델 terminal 완료·strict DTO·현재 원문/질문과 새 SDK 저장 영수증의 JSON 왕복·의미를 구분한다. JSON 왕복은 DB/앱 저장이 아니다. source_statement에 필요한 subject_refs/predicate_refs, quantity metric_refs/relative anchor가 비면 기존 source 검증기는 그대로 거부한다. uncertain으로 유효하게 제출해도 의미 완전성·사실 확인 성공으로 올리지 않는다. 원래 결과를 자동 다운그레이드하거나 보완하지 않는다.

원래 Q2필수3명제의 신청 개수/각각 상한(P5), 명시 법률상 기관/광역자치단체 신청 자격(P9), 공공기관의 상위기관 승인 선행조건(P10)을 명제별 좁은 필드와 직접 인용으로만 판단한다. explicit/equivalent/partial/not_represented/contradicted/undetermined를 유지하며 부분 보존은 완전 성공이 아니다. SDK 거부면3개도 미평가, 다른 질문9개는 미평가를 유지한다. 빈 부족 응답이나 단어/인용 위치 일치만 의미 성공으로 부르지 않는다. 이미 본 개발 자료·비맹검1회이며 실제 모델 개선율/holdout·사람/중립성/일반 품질을 인증하지 않는다.

최종 usage 미관측은0/무료가 아니며 관측 비용을 보존한다. HTTP 닫힘은 제공자 계산 취소/과금 절감 증거가 아니다. 앱/worker/main·DB/운영 데이터는 변경하지 않는다. 완료/구조/의미와 versioned worker의 합산 예산·권한·복구 인수는 별도다.

## 결과

구현·검증과 사전 고정 후 실제 결과를 추가한다. 현재 실제 호출 전이다.
