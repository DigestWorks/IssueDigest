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

실제1회 호출 결과를 아래에 보존한다. 실패를 성공으로 보정하지 않는다. 현재 제한 연구가 실제 모델 완료/의미를 충족해야 versioned worker·합산 예산/권한/내구 복구 연결을 검토한다. 이번에 앱의 기본 경로를 바꾸지 않는다.

## 실제 관측

실제 HTTP 요청1회/응답200, `response.completed`와 최종 usage를31.842초에 수신했다. SDK는 reason `output`으로 거부했고 새 저장 영수증은 만들지 않았다. 재시도·수리·모델/자료/한도 교체0이다. 읽은 SSE375,290bytes/1,311개 HTTP chunk를 비공개 보존했고 HTTP body 닫힘·반환 시 borrowed client 유지도 확인했다. HTTP chunk는 SSE event 개수나 토큰 수와 다르다.

최종 알려진 사용량은 입력2,387/출력2,569/합계4,956·요청1이다. 추론1,406은 출력에 포함되며 추가 가산하지 않는다. raw cached read0/cache write2,251도 보존했다. 이번에는 최종 사용량을 관측했지만 실제 청구 금액/캐시 TTL·제공자 계산 취소나 비용 절감은 입증하지 않았다.

## 읽기 전용 원인 진단

원래 args3,337UTF-8bytes는 완전한 JSON·strict DTO·canonical 타입 검사를 통과했고, 원문 hash도 같았다. 새SDK의 실패는 그 다음 source contract 검사였다. 명제3개 중 앞2개는 `source_statement`를 제출했지만 첫 명제의 subject_refs/predicate_refs, 두 번째의 predicate_refs를 비웠다. 기존 계약은 이 경우 `uncertain`을 요구하므로 첫 오류 `Missing evidence requires explicit uncertainty`로 거부한다. 자료에 주체/서술어가 없다는 판정이 아니라 모델이 해당 필드를 채우지 않았다는 관측이다.

인용 참조17회(고유 참조 tuple11개)는 모두 원문과 정확히 일치했다. 반복 등장한 참조를 포함한 occurrence 수이며 독립 참조17개나 의미 성공률17/17을 뜻하지 않는다. exact span·JSON 형식 통과는 주체/관계·자격/선행조건의 완전한 의미 보존을 인증하지 않는다. 원래 응답에 불확실 상태를 덧붙이거나 빠진 참조를 채워 넣지 않았다.

SDK 거부이므로 Q2필수P5/P9/P10은 모두 미평가다. 부분 구조를 읽은 진단을 의미 성공/실패 점수로 바꾸지 않으며 다른 질문9명제·전체12분모를 유지한다. 이번1회에서는 공백 정체로 중단되지 않았지만 재현율·정체 해결·이전 요청과 인과 비교는 주장하지 않는다.

## 다음 구현 범위

정확한 주체·서술어 참조와 uncertainty의 관계를 새 출력 지침/계약에서 보완하고 합성 경계·실제 의미를 다시 인수한다. 현재 원문 검증기를 완화하거나 누락 필드를 자동으로 채우지 않는다. 실제 완료/구조 수용을 얻기 전 versioned worker·합산 예산/권한/복구·앱 적용은 보류한다. 기존9,468QA는 코드 불변의 구조 증거이며 이번 실제 의미 인수 통과로 표시하지 않는다.

## 검토·보존

독립 증거 검토 C0/I0/M0로 사전 고정11파일·현재474실행/이전SDK36/과거실제58·진단66 증거와 정확 송신 body·응답 완료/최종usage·SDK 거부를 확인했다. 원래 인자의 native duplicate-key/nonfinite guard도 별도로 통과해 source contract 거부 원인과 구분했다. 수신 SSE1,156events와 HTTP1,311chunks를 구분했다. 실제 제공자 측 요청 audit/최종 청구서·의미·앱 인수는 미확인이다. PR107 CI도 통과했으나 이번 문서·제한 연구의 실제 의미 통과로 세지 않는다. 문서 링크·개인정보 검사·게시 기록은 최종 인계를 따른다.
