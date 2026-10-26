# 명시적 근거 필드 지침 · 실제 인수

2026-10-26 KST. [guarded-v2 계약](../changes/guarded-question-reference-rules.md)의 구현·코드 검토 후 같은 개발 자료로 최대1회 실제 인수를 진행한다. 이전 [guarded-v1 거부](guarded-question-acceptance.md)와 입력·필수 기준/루브릭·모델/상한은 유지하고 정확328byte field-rule 지침만 새 SDK에 추가한다. 기존 응답·원문·기준·사용량/소진 잠금은 변경하지 않는다.

## 응답 전 고정

원래 source/criteria/rubric 파일을 bytes 그대로 복사한다. 선택 질문Q2·필수P5/P9/P10, 전체12기준/다른9개 미평가는 유지한다. 모델 `gpt-6.1-sol`, reasoning low/service_tier default, 출력4,000/전체20,000·60초 operation/별도1초 cooperative close·무재시도/strict tool1개/no-store를 유지한다. envelope는 기존 보수적 UTF-8/schema·출력 상한 비교 값으로 실제 provider 토큰 usage와 다르다. 새 지침으로 정확한 기존 입력의 envelope는19,907이며 추가 지침 때문에 입력을 줄이거나 상한을 높이지 않는다.

실제 송신 전 현재 실행 파일·protocol·runner·정확 wire·원문/질문/기준·schema/지침·예산 hash를 새 namespace에 고정하고 소진 잠금을 먼저 기록한다. 실패·거부·타임아웃 후 재호출/수리·모델/자료/한도 교체는 없다. actual API 호출은 최대1회이며 합성 MockTransport의 횟수와 구분한다. old paid runner는 실행하지 않는다. 원문/응답/SSE는 읽은 부분만 private로 보존하고 키/헤더를 기록하지 않는다.

## 판정

HTTP/모델 terminal 완료·strict DTO·현재 원문/질문과 새 SDK 저장 영수증의 JSON 왕복·의미를 구분한다. JSON 왕복은 DB/앱 저장이 아니다. source_statement에 필요한 subject_refs/predicate_refs, quantity metric_refs/relative anchor가 비면 기존 source 검증기는 그대로 거부한다. uncertain으로 유효하게 제출해도 의미 완전성·사실 확인 성공으로 올리지 않는다. 원래 결과를 자동 다운그레이드하거나 보완하지 않는다.

원래 Q2필수3명제의 신청 개수/각각 상한(P5), 명시 법률상 기관/광역자치단체 신청 자격(P9), 공공기관의 상위기관 승인 선행조건(P10)을 명제별 좁은 필드와 직접 인용으로만 판단한다. explicit/equivalent/partial/not_represented/contradicted/undetermined를 유지하며 부분 보존은 완전 성공이 아니다. SDK 거부면3개도 미평가, 다른 질문9개는 미평가를 유지한다. 빈 부족 응답이나 단어/인용 위치 일치만 의미 성공으로 부르지 않는다. 이미 본 개발 자료·비맹검1회이며 실제 모델 개선율/holdout·사람/중립성/일반 품질을 인증하지 않는다.

최종 usage 미관측은0/무료가 아니며 관측 비용을 보존한다. HTTP 닫힘은 제공자 계산 취소/과금 절감 증거가 아니다. 앱/worker/main·DB/운영 데이터는 변경하지 않는다. 완료/구조/의미와 versioned worker의 합산 예산·권한·복구 인수는 별도다.

## 결과

실제 요청1회/HTTP200·response.completed·30.925초, 새 `guarded-question-evidence-v2` SDK가 명제3개를 수용했다. 현재 원문/정확 질문의 결과를 JSON 파일에 저장한 뒤 새 validator로 재구성해 같은 영수증을 확인했다. DB/앱 저장이나 일반 의미 성공을 뜻하지 않는다. 재호출·수리·자동 필드/상태 보완·모델/자료/한도 변경0이다.

최종 관측 usage는 입력2,444/출력2,781/합계5,225·요청1이다. 추론1,476은 출력에 포함되며 추가 가산하지 않는다. raw cached read0/cache write2,308을 보존했고 최종 청구 금액·캐시 TTL/비용 절감은 미확인이다. 읽은 SSE413,639bytes/HTTP1,670chunks를 보존했으며 local body 닫힘·반환 시 borrowed client 유지도 확인했다. HTTP chunk/event/token 수를 혼용하지 않는다.

원래 인자3,668UTF-8bytes는 native JSON duplicate-key/nonfinite·strict DTO/canonical·현재 원문 계약 검사를 통과했다. 인용 참조20회는 모두 exact이며 반복을 포함한 occurrence 수다. 이것을 독립 인용20개나 의미 보존20/20으로 해석하지 않는다. 이전 raw 응답을 보정한 결과가 아니며 신규 요청의 원래 출력을 그대로 검사했다. 단일 개발 관측이므로 규칙 준수 개선율/재현율·기존 요청과 인과 효과를 확정하지 않는다.

독립 AI 개발 검토의 첫 판정을 원래 주석과 별도로 보존했고, 조율자가 아래 근거를 사전 기준과 대조해 같은 판정에 동의했다. SDK 수용만을 근거로 삼지 않았다.

| 필수 명제 | 개발 판정 | 좁은 필드·관계의 근거 |
| --- | --- | --- |
| P5 | explicit | 신청 주체/행위와 수량·상한·분배 관계가 각 범주별 독립 신청 상한을 보존한다. 범주를 함께 묶은 참조 span도 별도 신청 의미를 유지한다. |
| P9 | explicit | 자격 facet이 두 신청 주체 종류와 명시 법률상 한정을 보존한다. |
| P10 | explicit | 주체/행위와 선행조건 facet이 상위기관 승인을 신청 전 조건으로 보존한다. |

선택3개는 explicit3개이며 다른 질문9개는 미평가·전체12기준을 유지한다. 출처 정보의 좁은 의미 보존에 대한 비맹검 AI 개발 판정이고 사람 정답/holdout/일반 정확도·진실·중립성 인증이 아니다. 결과 status는 계속 unreviewed다. 같은3명제에 대한 동의를 독립 표본6개나 전체12개 성공으로 세지 않는다.

## 증거 검토

독립 검토 C0/I0/M0. 단일 소진 요청·사전 고정12파일/정확 body와328byte 차이·현재476실행 파일/이전474실행·51/36과거 증거 보존·raw 인자와 새 저장 결과 동일성·현재 원문/JSON 재검증을 확인했다. 자동 보정·추가 제공자 호출0이다. 실제 제공자 측 request audit·청구서·앱 저장/worker 복구 인수는 별도다. 새전체9,515개(Python8,695+JS820)·정적 검사/빌드/OpenAPI·실패/skip/warning0를 통과했다. PR/Sites 결과는 최종 인계에 기록한다.

최종 인계: [Draft PR109](https://github.com/DigestWorks/IssueDigest/pull/109)·Sitesv131 public/native succeeded, 이전v130/변경7문서 정확 사본(70325c2)을 보존했다. Site source `ae602f7f73f4314d026e28e9c70e1b649f882686`, saved `appgprj_6ac612dd42708191a7a0c8377be64d48~appgver_fef73bb1d6748191b31a9c00d425ad76`, deployment `appgdep_6adeb6fd9a408191933065b216cac3fc`다. HTML116/로컬대상3,335/공개텍스트350·비공개60+12항목 제외를 확인했고 사용자 탭 이동/새브라우저QA0이다. 자체QA1/전용volume1을 정리했으며 실제 요청은 이번 최초1회뿐이다. 이후 인계는 저장소 원본을 따르고 main/앱/worker 활성화는 없다.
