# 중단 가능한 질문별 근거 생성 · 실제 모델 인수

2026-10-25. 기반 PR107/d48fc75. [새 SDK](../changes/guarded-question-evidence.md)의 실제 전송·완료/거부·관측 비용·질문별 의미를 확인한다. 문서·제한 연구로 spec-driven-workflow 문서 예외를 적용한다. 기존474개 non-Markdown 파일과 이전 SDK/실험의 원문·기준·응답·비용·소진 잠금을 보존한다. 실행 코드 불변이므로 기존 전체9,468QA를 구조 증거로 재사용하며 앱/worker/main 활성화·서버/DB 변경은 없다.

## 응답 전에 고정하는 조건

이전 [v2 실제 미완료](question-evidence-generation-v2-acceptance.md)와 같은 전체 개발 원문·정확한 Q2·전체12명제 기준·필수P5/P9/P10·원래 판정 루브릭을 bytes 그대로 복사한다. 새 경로는 `run_guarded_question_evidence`이며 모델 `gpt-6.1-sol`, reasoning low, service_tier default, strict tool1개, 전체20,000/출력4,000, 단일 요청/재시도0이다. 기존 정확한 v2 지침을 유지하고 compact 진단 suffix는 붙이지 않는다. 모델·원문·질문·한도를 교체하거나 결과를 수리하지 않는다.

원문/기준/실제 SDK MockTransport body·SDK 입력/출력 profile·지침·현재 코드·프로토콜·runner를 송신 전에 hash 고정한다. 새 namespace의 소진 잠금을 먼저 만들고 실제 요청은 최대1회다. 실패·네트워크 오류·공백 감지·미완료 후 재시도하지 않는다. 기존 runner나 소진 namespace는 실행/변경하지 않는다.

실제 HTTP/SSE bytes는 읽은 부분만 비공개로 기록한다. 로깅은 원문/헤더/키를 stdout이나 공개 저장소에 노출하지 않으며, 스트림을 미리 버퍼링하거나 끝까지 drain하지 않는다. transport60초/별도1초 cooperative close·argument80,000UTF-8bytes·10,000event 한도를 그대로 따른다. HTTP 닫힘은 제공자 계산 중단/최종 과금 절감의 증거가 아니다. 최종 usage 미수신은 무료0이 아닌 미관측이다.

## 판정 단위와 완료 기준

HTTP 응답·terminal 수신·native strict 수용·현재 Source/정확 질문의 새 저장 영수증 왕복·의미를 별도로 기록한다. SDK 거부/부분 JSON은 수리하거나 의미 성공으로 전환하지 않는다. 저장 왕복은 JSON 파일→새 validator 재구성까지이며 DB 영속화나 앱 실행을 뜻하지 않는다. 빈 insufficient 결과도 의미 성공이 아니다.

- P5: 신청 주체가 대규모·중규모 각각 최대1곳을 신청한다는 수치·상한·분배 대상·신청 상태를 보존한다. 선정 계획 개수와 섞지 않는다.
- P9: 광역자치단체와 명시 법률상 공공기관의 신청 자격 주체·범위를 보존한다.
- P10: 공공기관·상위기관 승인·신청 전 선행 조건을 같은 명제/직접 참조로 연결한다.

선택 명제의 좁은 의미 필드와 직접 참조만 판정하며 전체 원문/무관한 출력에 단어가 있다는 것으로 성공 처리하지 않는다. explicit/equivalent/partial/not_represented/contradicted/undetermined를 유지하고 partial을 완전 보존으로 세지 않는다. 완료/strict 실패면 필수3개도 미평가다. 다른 질문9개는 이번 질문의 미평가로 두고 전체12기준을 유지한다. 이 개발 자료·기준을 이미 본 비맹검 관측이며 독립 리뷰도 사람/holdout·진실·중립성·일반 품질 인증을 대신하지 않는다.

## 관측·후속

실제 호출 전이다. 결과를 아래에 추가하고 실패를 포함한 원래 기록을 보존한다. 현재 제한 연구가 실제 모델 완료/의미를 충족해야 versioned worker·합산 예산/권한/내구 복구 연결을 검토한다. 이번에 앱의 기본 경로를 바꾸지 않는다.
