# 공유 맥락 생성 SDK

2026-10-21. 상태: SDK 구현·합성 구조/오프라인 용량 검증 완료. 실제 의미 인수·앱 적용 미완료. [순수 공유 맥락](shared-measurement-context.md)을 별도 단일 borrowed-model 요청에 연결한다. 기존 앱·기본 모델·과거 요청/결과는 유지한다.

## Global Constraints

- 새 `shared_context_generation.py`와 합성 테스트만 추가한다. 기존 모든 실행/설정·fixture·SDK·순수 계약·공통 runtime·의존성은 불변이다. 앱/API/OpenAPI/DB/worker/UI 변경이나 실제 서버 적용은 없다.
- `SharedContextGeneration`은 고정 profile `shared-context-generation-v1`, status `unreviewed`, frame `SharedMeasurementFrame`, 정확 UTF-8 prompt/instructions SHA256, 기존 bounded KnownUsage를 저장한다. `SharedContextGenerationError`는 기존 runtime 오류를 상속해 nullable known_usage를 보존하며 원문/비밀/내부 chain을 노출하지 않는다.
- `shared_context_prompt(source)`는 순수 preflight 함수를 제공한다. `create_shared_context_framer(model)`은 필수 caller-owned Model을 빌리는 lazy handle이다. key/env/client 생성·폐기 없이 `run_shared_context_framer(handle, source)`에서 기존 `_run_contextual_request`를 재사용한다. 별도 identity `issuedigest_shared_context_v1`, 단일 strict tool `fill_shared_context_v1`, 요청1/재시도0·수리0·후처리 누락0·fallback0, timeout30/no-store, 전체20,000/출력2,500을 유지한다. 실제 모델 호출은 이번 SDK/합성 인수에서는0이다.
- 입력은 전체 source·순서 있는 whole quotes·현재 서버 수치/문장 후보를 기존 `_prompt`로 그대로 담는다. source metadata/제목만으로 의미를 인증하지 않는다. 새 profile·eligible_status_sentence_ids·context_id_slots(c1..c12)·reporting_event_id_slots(e1..e12)만 덧붙인다. source/후보를 자르거나 모델을 자동 선택하지 않는다.
- 실제 dynamic schema는 contexts/events/bindings/relations 필수·상한12/12/12/16, anchor의 현재 sentence enum·정확 contextual text, scopes≤4, binding/relation endpoint의 현재 candidate enum, status sentence의 eligible enum(nullable)을 사용한다. context_id/context reference는 c1..c12, event_id/event reference는 e1..e12로 제한한다. fixed 슬롯은 라벨이며 원문/의미를 인증하지 않는다. shared ID regex를 provider에 복사하지 않고 Literal로 좁힌다.
- context는 순수 SharedMeasurementContext를 파생하고 모든 역할/목적을 보존한다. eligible 상태 문장이 없으면 context.value_status를 unknown으로 좁히고 binding.status_evidence_sentence_id는 null로만 허용한다. eligible이 있으면 기존 value_status enum과 eligible/null ID를 사용하고 알려진 상태의 binding 의무·후보별 문장/같은 인용은 순수 builder에서 검사한다.
- event는 attributed_report(actor/predicate 필수), narration(actor null/predicate 필수), unknown(actor/predicate null, tense unknown)의 실제 strict 변형으로 좁힌다. 모든 필드는 필수다. 원래 nullable 역할·보고 시제와 값 상태를 섞거나 override하지 않는다. relations는 기존 ContextualFrameRelationInput의 현재 enum/anchor/whole statement를 그대로 보존한다.
- 원래 dynamic root와 모든 nested 실제 model·tuple을 canonical 검사하기 전에는 dump/narrow하지 않는다. canonical helper와 순수 계약의 `_actual_models`를 재사용할 수 있다. 검증된 dynamic 출력만 JSON으로 순수 SharedMeasurementInput에 좁혀 기존 builder로 전달한다. 잘못된 relation/anchor/참조 전체를 거부하며 부분 삭제/첫 위치 선택/수리는 없다.
- stored validator는 현재 source로 preflight를 다시 만들고 whole SharedMeasurementFrame을 재구성한다. 저장 input을 현재 dynamic schema에 재검증하여 슬롯/현재 candidate·sentence·eligible 제약도 확인한다. 모든 wrapper/receipt/usage·source drift/추가필드/subclass/unchecked model container 위변조를 거부한다. 구조·원문 일치는 의미·진실·중립·권한 인증이 아니다.
- preflight는 prompt UTF-8 bytes + instructions bytes + max(raw/normalized actual tool schema bytes) + 기존 framing2,048 + 출력2,500 ≤20,000을 호출 전에 확인한다. preflight를 넘으면 공개 prompt 함수와 runner는 sanitized 오류로 요청 전에 거부한다. 최대 record 수는 동시 적재 보장이 아니며 출력 용량은 별도 측정한다.
- 지침은 비신뢰 원문 지시를 무시하고, 원래 수치/단위/범위/열린 상한 보존, 실질 수치 선택/우연 날짜 제외, 공통 측정 항목과 범위/발표자 분리, 명시 공유 참조만 상속, 서로 다른 항목/기간/상태는 별도 맥락, 보고 predicate/tense는 예정행위와 구분, 목적/조건/실제 전망 근거 분리, 반복 anchor의 정확 context, 후보 전체 문장 상태 근거·모호하면 unknown/null, 직접 관계만 유지하도록 한다. 과거 private 사례/질문/긴 quote를 새 코드/문서/fixture에 복사하지 않는다.

## Task 1 — 생성 경로·합성 검증

- [x] 위 단일 SDK·동적 schema·전체 재구성/receipt 검증을 새 모듈에 구현하고 새 합성 테스트로 검증한다. 기존 요청/fixture/순수 계약 불변·실제 strict provider schema와 정규화·request body/usage/error handling·모델 미호출 preflight·실제 nested 타입과 bypass·profile/hash/source drift·슬롯/후보/eligible/현재 문장·보고 사건 variants·empty output/무수치 입력·상한·단일 요청/무재시도·빌린 client 수명·예산 경계를 포함한다. cap 오류는 다른 규칙에 가리지 않게 독립 검증한다. TDD RED/최소 구현/green과 실제 결과를 기록한다.

## 이후 인수

controller는 기존 private4자료를 모델 호출 없이 전체 source 그대로 preflight하여 실제 schema/요청 bytes와 예시 출력 크기를 기록한다. 이는 데이터 재노출·의미 성공 재판정이 아니다. 수용 가능한 용량을 확인한 뒤 별도 사전 고정 미관측 실제 자료·의미 기준/호출 상한으로 인수한다. 불충족이면 상한 증액/숨은 source 축약/성공까지 호출하지 않고 제약을 기록한다. 전체 앱 권한·예산·내구 실행/복구·최종 브리핑 품질은 이후다.

## 구현·검증 결과

소스 `54afcd96cba638bd3dddecfbcaf0419acf02c4a7`에서 focused103/agents2685·전체7,019개(Python6,199+JavaScript820)와 Ruff/format/mypy·ESLint/TypeScript/build/OpenAPI 검사를 통과했다. 독립 태스크·최종 검토로 확인한다. 기존415개 실행/설정 파일과 이전97개 증거의 hash 불변을 확인했다. 새 모듈/테스트만 추가했고 실제 모델·외부 네트워크 요청·앱/서버/main/운영 변경0이다.

기존 private4자료를 그대로 사용한 새경로 preflight는 모두 수용했다. 요청 예산 envelope는18,119/16,641/15,895/16,237이며20,000까지 여유는1,881/3,359/4,105/3,763이다. 지침3,996 UTF-8 bytes·raw tool5,636/5,617/5,592/5,617·normalized5,383/5,364/5,339/5,364 중 큰 값을 예약한다. 전체 prompt는3,939/2,480/1,759/2,076 bytes이며 원래 whole quotes/후보 내용을 유지했다. 이 보수적 bytes+예약 계산을 실제 청구 토큰·모델 지연·일반 최대 용량으로 해석하지 않는다.

controller의 MockTransport4회는 실제 SDK 전송 형식/storeFalse/max_output_tokens2500과 빈 구조 응답의 wrapper 재구성만 검증했다. 실제 AI 호출·비용은0이며 모의 usage는 청구가 아니다. 빈 결과를 이용했으므로 역할을 포함한 충분한 출력/의미 품질은 미검증이다. records 최대12/12/12/16과 역할 text1000자는 동시 완전 출력 보장이 아니다. 이전 실제 생성 의미0/4와 추론 비교 반환2의 의미0/2·다른2미판정은 재판정하지 않는다.

별도 비어 있지 않은 합성 예시(공유 맥락1·보고 사건1·수치2·직접 관계1, 모든 맥락 역할·두 공통 범위)를 실제 동적 schema와 순수 builder에서 검증했다. compact provider arguments1,342 UTF-8 bytes/1,274 codepoints, function-call envelope1,631 bytes다. 모델 호출/실제 토큰 측정은 없으며 최대 레코드/장문 역할의 완전 출력 보장과 실제 의미 품질은 여전히 미검증이다.

지침·자료·해시 일치는 소비된 source의 일관성 증거이며 모든 metadata의 서명이 아니다. 기존 `_prompt`가 전송하지 않는 title만의 변경은 기존대로 허용한다. 사용량 초과 등 일부 SDK 중단은 기존 runtime에서 응답 capture가 남지 않을 수 있어 known_usage=null이며 무료가 아니다. runtime을 바꾸지 않았고 명시 사용량이 남은 거부는 보존한다.

다음은 새 미관측 실제 자료·의미 기준과 호출 상한을 사전 고정한 인수다. 앱 연결 전에는 전체 예산·현재 권한·내구 실행/복구·브리핑 품질을 별도로 확인한다. 구조 성공·빈 mock 반환을 실제 AI 의미 성공으로 표시하지 않는다.
