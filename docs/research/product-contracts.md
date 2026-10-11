# 제품 계약 조사

2026-10-11 · 조사 완료, 설계 제안. API·DB 스키마나 제품 기능을 구현·확정한 문서가 아니다. 범위는 원문·인용·관계, 실행·이벤트, 생성 화면·사용량 계약이다. 엔진의 실제 성능·운영비 비교는 후속 실험이다.

## 조사 결과

원문 → 정확한 인용 → 주장·관계 → 질문별 화면을 하나의 추적 가능한 경로로 연결해야 한다. 기존 법안 식별·처리 이력·여론조사 조건 파싱은 재사용 후보다. 기존 피드의 노출 조건, 요약 중심 검색, 로컬 실행 로그와 와이어프레임의 가상 출처 ID를 그대로 제품 계약으로 삼기는 어렵다.

다음 구현은 DB·AI 공급자와 독립적인 Python 계약·검증 규칙부터 시작하는 편이 좋다. 저장·권한·실행 복구 구현은 DB·실행기·인증 결정 뒤 진행한다. 기존 서버 정보 없이 계약을 준비할 수 있지만 실제 원문 검증과 엔진 평가에는 자료와 실행 환경이 필요하다.

| 영역 | 제안 | 막으려는 문제 |
| --- | --- | --- |
| 원문 | 문서 식별·원문 버전·파싱 결과를 분리 | 다시 파싱했을 때 과거 인용 위치가 바뀜 |
| 인용·관계 | 정확한 위치와 출처, 구조 검증과 의미 검토를 분리 | 출처 링크는 맞지만 주장을 뒷받침하지 않음 |
| 실행 | 저장된 순번 이벤트·제출 중복 방지·불명확한 호출 상태 | 새로고침·재시도로 유료 호출이나 결과가 중복됨 |
| 생성 화면 | 허용 모듈·근거 참조·불변 결과 버전 | 생성 전 가상 결과 노출, 실패 시 정상 결과 유실 |
| 사용량 | 비용 예약·실제 정산·미확정 비용 구분 | 동시 요청이 같은 예산을 중복 사용 |

## 확인한 코드와 한계

원격 main의 SHA를 GitHub API로 대조했다. LawDigest와 별도 파이프라인의 아래 기준은 조사 시점 원격 main과 일치한다. IssueDigest main은 아직 `ba47f3a`이며 실행 기반은 PR #2의 `4e63421`이다. 운영 서버·DB·실제 보유량·현재 수집 성공은 확인하지 않았다. 기존 테스트는 읽었으며 운영 DB나 공급자에 연결해 실행하지 않았다.

| 대상·고정 기준 | 코드에서 확인 | 재사용과 변경 |
| --- | --- | --- |
| [법안 조회·정규화](https://github.com/DigestWorks/LawDigest/blob/9e969d33cf8c184f78181a15cd9687f78155f461/services/data/src/lawdigest_data/bills/DataFetcher.py#L447), [회귀 테스트](https://github.com/DigestWorks/LawDigest/blob/9e969d33cf8c184f78181a15cd9687f78155f461/services/data/tests/test_open_assembly_bill_fetcher.py#L90) | BILL_ID/BILL_NO, 법안·PDF URL, 처리 상태, 선택 응답 누락 유지, bill_id 중복 제거 | 원천 식별·결측 규칙 유지. 법안이라는 개체와 상세 HTML/PDF라는 문서는 각각 식별 |
| [발의자 결측 테스트](https://github.com/DigestWorks/LawDigest/blob/9e969d33cf8c184f78181a15cd9687f78155f461/services/data/tests/test_data_processor.py#L32) | 공동 발의자 조회가 비면 해당 법안을 제외하는 기존 동작 | 조사 자료까지 폐기할지 재검토. 원문은 유지하고 관계 미확인 상태를 표시하는 안 제안 |
| [여론조사 모델](https://github.com/DigestWorks/LawDigest/blob/9e969d33cf8c184f78181a15cd9687f78155f461/services/data/src/lawdigest_data/polls/models.py), [파서 검증](https://github.com/DigestWorks/LawDigest/blob/9e969d33cf8c184f78181a15cd9687f78155f461/services/data/tests/polls/test_parser_validation_unit.py#L36) | 문항·모집단·방법·표본·가중치·기간·오차·PDF 참조. 일부 결측과 비율 합계 80%도 허용하는 테스트 | 조건 추출은 보존. 파싱 통과를 완전한 분포·서로 비교 가능한 조사라는 판정으로 사용하지 않음 |
| [파이프라인 실행 기록](https://github.com/DigestWorks/LawDigest/blob/9e969d33cf8c184f78181a15cd9687f78155f461/services/data/src/lawdigest_data/runtime/pipeline.py#L68) | UUID 실행 ID, JSONL 시작/단계/종료, 로컬 artifact·오류 기록 | 단계별 관측 원칙 유지. 제품용 저장 이벤트·재접속 순번·권한·복구 계약 필요 |
| [AI 근거 패킷](https://github.com/DigestWorks/LawDigest/blob/9e969d33cf8c184f78181a15cd9687f78155f461/services/ai/src/lawdigest_ai/processor/agentic_bill_report.py#L670), [본문 검증](https://github.com/DigestWorks/LawDigest/blob/9e969d33cf8c184f78181a15cd9687f78155f461/services/ai/src/lawdigest_ai/processor/agentic_bill_report.py#L1737) | 사전 조회한 근거·조회 오류와 결과 형식/내부 표현 검증 | 근거 제한·조회 오류 구분 유지. 검토한 본문 검증 함수의 형식 확인만으로 문장별 근거 일치를 보장할 수 없음 |
| [검색 문서](https://github.com/DigestWorks/LawDigest/blob/9e969d33cf8c184f78181a15cd9687f78155f461/services/data/src/lawdigest_data/bills/search_document.py) | 법안명·AI 제목·AI 요약·원천 요약을 결합 | 원문·생성 설명·개체 식별 필드를 분리하고 검색 적중이 정확한 인용으로 돌아가도록 변경 |
| 별도 파이프라인 `693f4ba3a97e718b9cf7c08036bf676002d70708` | DataFetcher·DataProcessor·DatabaseManager·WorkFlowManager가 존재 | 통합 저장소와 중복 후보. 존재만으로 현재 운영 실행 경로나 더 우수한 버전이라고 판정하지 않음 |
| 비공개 와이어프레임 `a847474bfc5759f56f9db48a9f5efa0de3b4a827` | 제한된 모듈·참조/비교 차원/날짜/관계 검증, Decisions→조회→Responses 흐름 | 참고 구조만 사용. 가상 출처 ID·모델 고정·메모리 맥락·접속 코드·자체 범용 스키마 검증기는 이식하지 않음. 비공개 코드는 공개 저장소에 복사하지 않음 |

## 1. 원문·파싱·인용

### 식별과 버전 제안

| 객체 | 필요한 내용 | 경계 |
| --- | --- | --- |
| SourceDocument | 내부 ID, 공급처·자료 종류·원천 ID, 원문 URL | 동일성은 공급처/종류/원천 ID로 판정. URL만으로 전체 자료를 합치지 않음 |
| FetchObservation | 조회 시각·응답 결과·원문 객체 참조·원문 바이트 해시 | 같은 내용을 다시 수집한 사실과 콘텐츠 변경을 구분 |
| DocumentVersion | 문서 ID·버전 ID·비교용 콘텐츠 해시·원문 참조·게시/발생 시각 | 한 번 저장한 내용을 덮어쓰지 않음. 비교용 정규화 규칙도 버전 관리 |
| ParsedRepresentation | 원문 버전 ID·파서/설정 버전·정규화 텍스트/표 참조·텍스트 해시·결측 | 파서 변경만으로 원문이 수정됐다고 표시하지 않음 |
| Chunk | 파싱 결과 ID·텍스트 범위·분할기 버전 | 검색 단위. 인용의 영구 식별자를 chunk 번호에만 의존시키지 않음 |
| Citation | 원문/파싱 버전 ID·인용문·위치 선택자·검증 결과 | 당시 사용한 버전과 위치로 돌아감. 최신 문서로 조용히 치환하지 않음 |

동일 문서·동일 비교 해시는 콘텐츠 버전을 중복 생성하지 않는다. 재조회 관측은 남긴다. HTML 시각·광고 등 제외 규칙과 API JSON 정규화는 공급처별로 명시해야 하며, 임의로 제외해 실제 변경을 숨기지 않는다. 동일 원문이 과거 버전으로 되돌아온 경우도 새 관측으로 기록한다.

수집 시각은 시간대가 있는 UTC instant, 원천의 날짜/기간은 알려진 정밀도와 시간대를 보존한다. 연도·월·일만 있는 값을 임의의 시각으로 늘리거나 모르는 값을 0으로 채우지 않는다. 발효 시점과 게시·수집 시점을 구분한다. 이용 범위와 삭제·정정·제한 상태는 별도 정책 기록으로 관리하고 열람 시 현재 권한을 확인한다.

### 인용 위치 제안

W3C의 텍스트 인용 선택자와 위치 선택자는 인용문·앞뒤 문맥, 시작/끝 위치를 정의한다. 이를 참고해 자체 계약을 만들되 전체 JSON-LD/RDF 도입을 뜻하지 않는다. [W3C Web Annotation](https://www.w3.org/TR/annotation-model/#selectors)

- 텍스트: 정규화 텍스트의 Unicode code point 기준 `[start, end)`와 exact/prefix/suffix. Python과 JavaScript UTF-16 인덱스 차이를 변환·테스트한다. 정규화 규칙은 파싱 버전에 고정한다.
- PDF: 파일 페이지 번호는 1부터, 인쇄된 페이지 표시는 별도. 회전·crop box를 반영한 페이지 좌상단 기준 0~1 좌표와 여러 사각형을 허용한다. OCR·레이아웃 파서가 실제로 제공한 위치만 사용한다. 좌표가 없으면 위치 정밀도 부족을 표시한다.
- 표/API: 원문 버전·표/레코드/셀 ID, 문항·단위·기간·모집단·방법·표본·가중치 조건과 원문 위치를 연결한다. 다른 조건의 값을 합산할 수 있는지는 별도 비교 규칙으로 판단한다.
- `구조 유효`, `원문 위치 일치`, `주장 지지 여부`를 분리한다. 인용문이 존재해도 인과관계나 수치 해석을 지지한다는 뜻은 아니다. 의미 검토는 방법·버전·결과와 사람 검토 여부를 기록한다.
- 과거 인용 참조는 남기되, 현재 보관·열람 정책이 원문 공개를 금지하면 원문/인용문 제공을 제한하고 이유를 표시한다. 해시나 과거 권한 기록만으로 현재 접근을 허용하지 않는다.

## 2. 개체·주장·관계

| 객체 | 제안 필드·규칙 |
| --- | --- |
| Entity | 종류·이름·원천 식별자·별칭·유효 기간·동일성 검토 상태. 이름만으로 동명이인을 합치지 않음 |
| Claim | 누가 주장했는지, 내용, 사건/유효 시점, `source_assertion`/`observation`/`inference`, citation 참조, 검토 기록 |
| Relation | 주체/대상 참조, 제한된 관계 종류·방향, 유효 기간, citation 참조, 온톨로지 버전·검토 상태 |
| Observation | 수치 원문/정규화 값·단위·차원·기간·조건·citation. 값의 결측 사유를 보존 |

최초 관계 어휘는 발의·심사·대안 법안·지지/반박·자료에서 언급됨 같은 검증 가능한 범위부터 제안한다. 같은 문서에 등장함, 시간 선후, 청원 동의 수를 인과관계·전체 여론으로 바꾸지 않는다. 관계 종류와 각 양 끝의 허용 개체 종류는 온톨로지 버전별로 제한한다. 원문은 누군가의 주장 자체를 뒷받침할 수 있지만 주장 내용의 진실까지 보장하지 않는다.

Neo4j에는 기준 데이터의 개체/관계/근거 ID와 투영 버전을 전달한다. 원문 수정·관계 정정·삭제는 기준 데이터 변경과 outbox로 전파하며, 같은 사건 재처리가 중복 연결을 만들지 않아야 한다. 기준 저장소·검색·Neo4j의 쓰기를 하나의 분산 트랜잭션이라고 가정하지 않는다. 생성·변환·사용 주체를 추적하는 구분은 [W3C PROV](https://www.w3.org/TR/prov-overview/)를 참고한 설계 제안이다.

## 3. 실행·이벤트·재접속

Run은 질문·작업 공간·요청자·선택한 자료 버전·부모 화면 버전·제출 키·입력 해시·모델/프롬프트/도구/계약/실행기 버전·추적 ID를 고정한다. HTTP `request_id`, 장기 실행 `run_id`, 관측 `trace_id`, 공급자 요청 ID는 구분한다. Step/Attempt에는 재시도 횟수·입출력 참조·외부 요청 식별자·실패 종류를 남긴다.

상태 후보: `queued → running → succeeded | failed | cancelled`, 그리고 취소 접수 `cancel_requested`, 외부 호출 결과를 확인해야 하는 `awaiting_reconciliation`. 자료 부족·질문 확인은 정상 결과의 종류로 표현하고 실행기 오류와 구분한다. 최종 상태는 저장 트랜잭션에서 경쟁을 해결하며 늦게 도착한 결과가 취소된 화면을 덮어쓰지 않는다. 취소 후 추가 유료 단계를 시작하지 않는다.

### 전송 제안

질문 제출 POST → run 접수와 첫 저장 이벤트 → 세션으로 인증한 GET SSE 구독. 취소는 별도 POST다. SSE의 id와 Last-Event-ID는 재연결 커서로 활용할 수 있다. 서버 측 저장·권한·재생은 별도 구현해야 한다. [WHATWG SSE](https://html.spec.whatwg.org/multipage/server-sent-events.html#the-last-event-id-header)

| Event 봉투 | 규칙 제안 |
| --- | --- |
| schema_version, run_id, seq, type, occurred_at, payload | 타입별 payload를 제한. seq는 run 내 단조 증가, 저장의 고유 키는 `(run_id, seq)` |
| run.accepted / stage.changed | 접수·검색·도구·검증·화면 구성의 실제 상태. 근거 없는 진행률이나 내부 추론문을 전송하지 않음 |
| module.ready | 검증을 통과한 전체 모듈과 해당 draft/revision ID. 미완성 JSON 조각을 제품 UI로 실행하지 않음 |
| run.succeeded / run.failed / run.cancelled / run.awaiting_reconciliation | 결과 참조 또는 공개 오류 코드·재시도 가능 범위. 원시 예외·키·공급자 응답 전체를 공개하지 않음 |

서버는 이벤트를 저장한 뒤 전송한다. 재접속은 저장 이벤트를 커서 이후부터 읽고 실시간 전달과 연결할 때 생기는 누락·중복을 처리한다. 클라이언트는 중복 seq를 무시하고 누락을 재조회한다. 새로고침은 기존 run을 구독하며 질문을 재제출하지 않는다. 오래된 커서는 현재 스냅샷·새 커서로 복구하고 복구 불가를 명시한다. heartbeat는 연결 유지용이며 작업 진척 이벤트가 아니다.

### 중복·불명확한 유료 호출

같은 작업 공간·사용자·제출 키와 같은 입력 해시는 같은 run을 반환한다. 같은 키에 다른 입력은 충돌로 처리한다. worker 복구는 별도 실행 lease/세대와 엔진의 보장을 사용한다. 공개 RunEvent와 실행기 내부 history는 목적이 달라 직접 같은 테이블/형식으로 취급하지 않는다.

[DBOS의 step](https://docs.dbos.dev/explanations/concurrent-executions)은 at-least-once 실행일 수 있고, [Temporal Activity](https://docs.temporal.io/activity-definition#idempotency)도 재시도될 수 있다. 외부 유료 요청이 성공했지만 로컬 저장 전 중단하면 두 엔진 모두 공급자 측 중복 과금 방지를 자동 보장한다고 해석할 수 없다.

따라서 호출 attempt·요청 식별자·사용량을 저장하고, 제공자가 지원하는 중복 키·상태 조회를 확인해야 한다. 성공 여부를 모르는 경우 자동 재발송하지 않고 보류/조회/명시적 새 실행으로 처리한다. 결과 조회나 취소 지원 여부는 도구별 capability로 관리한다.

## 4. Generative UI와 AI 책임

화면은 같은 근거를 쓰더라도 질문에 따라 모듈의 종류·순서·비교 차원·강조·배치를 생성한다. 지원 범위 후보는 근거 카드·비교표·타임라인·관계도·수치 차트다. 질문 전에 이를 가상 결과로 채우지 않는다. 모듈별 색·여백·반응형·접근성은 앱 디자인 시스템이 담당한다.

### AI와 서버의 경계 제안

| 역할 | 담당 | 제한 |
| --- | --- | --- |
| 접근·비용·자료 범위 | 서버 규칙 | 모델 판단으로 권한·한도를 늘릴 수 없음 |
| 의도·탐색 방향·화면 계열 선택 | Decisions | 제한된 선택지와 `other`/확인 필요. 확률 임계값은 실제 평가셋으로 결정 |
| 근거 검색·관계/외부 조회 | 등록 도구 | 허용 범위 안에서 실행하고 실제 조회 결과 ID를 반환 |
| 설명·비교 차원·화면 초안 | Responses Structured Outputs | 제공한 근거 참조·허용 명세를 사용하고 서버 검증을 거침 |
| 원문 위치·관계·수치·UI 명세 검증 | 서버 검증과 의미 검토 | 모양이 맞는 JSON과 사실이 맞는 결과를 구분 |
| 필터·정렬·근거 펼침·저장 결과 재열람 | 웹/서버 조회 | 추가 AI 호출 없음. 새 해석·새 자료 요청은 새 run |

공식 문서상 [Decisions](https://developers.openai.com/api/docs/guides/decisions)는 public beta이며 현재 `gpt-6-luna`를 사용하고 predicate/choice/score를 제공한다. 구조화된 설명 생성과 도구 호출은 별도 용도다. 여기서는 문서와 기존 요청 코드만 확인했으며 새 프로젝트 키로 호출·접근 권한·한국어 품질·지연·비용을 실측하지 않았다. 기존 코드의 고정 모델명을 새로운 모델 선정 결정으로 가져오지 않는다.

첫 방향 판단은 질문·선택 범위를 사용한다. 실제 답변 가능 여부는 검색한 근거·결측·시점과 검증 뒤 판단한다. 질문만 보고 높은 confidence가 나왔다고 근거가 충분하다고 결론내리지 않는다. 서로 의존하는 판단은 한 번의 독립 질문 묶음으로 처리하지 않는다.

### 화면·명세 제안

- 모델의 `CanvasDraft`와 서버가 저장·배포하는 `CanvasRevision`을 구분한다. 서버가 권한·버전·참조·시간·검증 상태를 부여하며 모델이 이를 생성하지 않는다.
- 모듈에는 안정 ID·kind·제목·형식별 props와 근거 참조를 둔다. 사실 문장·비교 셀·시간 사건·관계 edge는 citation/claim 참조를 갖는다. 제목·요약에도 새 사실을 무근거로 추가하지 않는다.
- 차트 값은 검증된 Observation에서 가져오고 단위·기간·조건을 유지한다. 서로 비교할 수 없는 조사와 불완전 비율을 하나의 완전한 분포처럼 그리지 않는다. 모델이 임의 수치를 만드는 경로를 두지 않는다.
- 허용 액션은 근거 열기·자료 선택·로컬 필터/정렬·새 질문처럼 명시한다. 모델이 임의 URL·스크립트·CSS·도구 이름을 추가하지 않는다. 저장·취소 등 쓰기 액션은 사용자 동작과 서버 권한을 확인한다.
- CanvasRevision은 부모 revision·입력 자료 버전·모듈·검증 기록을 보존한다. 후속 변경은 기준 revision과 충돌 검사를 거쳐 새 revision이 된다. 실패/취소된 draft는 마지막 정상 결과를 대체하지 않는다.
- 자료 부족·질문 확인·공급자 거부·미완성 출력은 정상 화면과 구분한다. 검증 실패의 자동 수정 횟수도 도구/토큰 예산에 포함해 제한한다.

[Pydantic discriminated union](https://pydantic.dev/docs/validation/latest/concepts/unions/#discriminated-unions)을 domain 모델의 kind별 분기에 활용하는 안이다. 웹 타입은 기존 OpenAPI 생성 경로를 유지한다. 도메인/전송 모델의 JSON Schema와 모델 공급자용 스키마를 동일 파일로 무조건 전달하지 않는다.

[OpenAI Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs)는 JSON Schema의 제한된 범위를 사용하며 object root, required 필드, additionalProperties 규칙이 있다. 공급자용 스키마 변환 계층에서 지원 범위로 표현하고, 반환값은 원본 Pydantic 모델과 참조 검증을 다시 통과시킨다. 거부·미완성 응답은 따로 처리한다. 실제 사용 모델의 제약도 구현 시 확인한다.

## 5. 사용량과 예산

UsageReservation은 run·예약 최대 비용·예산 기간·가격/환율 스냅샷을, UsageLedger는 attempt별 모델/도구·입출력 토큰·실제 또는 추정 비용·공급자 사용량 참조·정산 상태를 기록하는 안이다. 정밀 소수/최소 단위 정수로 계산하고 API에는 정밀도를 잃지 않는 문자열을 사용한다.

예약은 동시 요청에도 한 번만 남은 예산을 차감하도록 DB 트랜잭션으로 처리한다. 취소가 환불이라는 가정을 하지 않는다. 이미 청구된 재시도는 각각 정산하고, 결과를 모르는 유료 호출의 예약분을 즉시 돌려주지 않는다. 불명확한 비용은 조회/정산 정책으로 관리하고 상한 계산에서 보수적으로 반영한다.

월 10만 원은 AI만의 한도가 아니다. 서버·DB·원문 저장·외부 백업·세금/환율 여유와 다른 곳에서 같은 키를 사용하는 비용까지 따로 집계해야 한다. 실제 단가·고정비·환율 정책은 이번 조사에서 확정하지 않았다.

## 6. 기술 선택에 영향을 주는 조사 결과

| 미결정 항목 | 이번에 확인한 연결·주의점 | 다음 판단에 필요한 증거 |
| --- | --- | --- |
| PostgreSQL / MySQL | 둘 중 선택 전 원문 버전·unique key·outbox·동시 비용 예약·revision 충돌을 계약에 표현 가능 | 같은 자료로 트랜잭션·이관 부담·검색/실행기 결합·자원·운영비 확인. 이번 문서로 DB를 확정하지 않음 |
| pgvector 조합 / OpenSearch Nori | 검색 결과가 문서 ID를 넘어 정확한 원문 버전·구간으로 돌아와야 함 | 동일한 한국어 질문·기대 인용으로 검색률·필터·지연·메모리 실측. 아직 성능 우열을 판정하지 않음 |
| PydanticAI + DBOS / Temporal | 외부 호출 attempt와 공개 이벤트 저장은 엔진과 별도 계약. 실행기 교체를 약속하는 추상화가 아니라 후보 평가의 공통 입력 | 아래 복구/스트리밍 실험과 배포 버전 변경·월 비용 비교 후 생산 엔진 선정 |
| 자체 제한 모듈 렌더러 / json-render | [json-render](https://json-render.dev/docs)는 catalog·허용 액션·registry 기반 JSON UI를 제공. Python 계약→catalog/spec 연결과 근거/권한 검증은 우리 책임 | 같은 검증된 화면으로 React Router 통합·접근성·부분 갱신·보존 명세 호환성을 비교. 의존성은 아직 추가하지 않음 |

특히 최신 [PydanticAI DBOS 통합](https://pydantic.dev/docs/ai/capabilities/durable_execution/dbos/#streaming)은 workflow 내부의 일반 streaming API에서 모델 이벤트를 버퍼링한다. live 전달에는 durability event handler 등 별도 경로와 멱등 처리가 필요하다. `DBOSDurability`만 붙이고 workflow 밖에서 실행하면 내구성이 생기지 않는다. 따라서 “PydanticAI를 붙이면 실시간 생성·재접속·복구가 모두 해결된다”는 전제를 두지 않는다.

## 다음 구현 범위와 검증

첫 계약 구현 후보는 `packages/domain`의 원문/파싱/인용/개체·관계 모델, Run/Event, CanvasDraft/Revision, Usage 모델과 검증 규칙이다. ID·시각·enum·금액·schema_version의 공통 규칙을 먼저 확정하고 Python 모델 → OpenAPI → TypeScript 타입 생성 경로를 확장한다. 정적 계약만으로 실제 권한·저장·예약·복구가 구현됐다고 표시하지 않는다. 다음은 검증 계획이며 아직 테스트를 작성·실행하지 않았다.

| 검증 묶음 | 최소 시나리오 |
| --- | --- |
| 원문·인용 | 같은 내용 재수집/원문 변경/파서만 변경, 한글·이모지 offset, PDF 회전/페이지/범위, 다른 버전·없는 표 셀 참조, 정확한 인용이지만 지지하지 않는 주장 |
| 관계·조건 | 동명이인, 동시 등장→인과 오연결, 근거 없는 edge, 다른 문항/표본/기간 합산, 결측 수치를 0이나 완전 분포로 처리 |
| 실행·재접속 | 중복 제출/다른 payload 충돌, 이벤트 저장 전 전송 거부, 중복·누락 seq, 새로고침 재구독, 취소/완료 경쟁, 결과 불명확 유료 호출 보류 |
| 화면·공급자 | 모르는 kind/action, 비교 차원 불일치, 다른 공간 근거 참조, 차트값·단위 변조, draft 실패 시 정상 결과 보존, 거부/미완성 응답과 schema 변환 왕복 |
| 비용·권한·저장 | 동시 예약 한도, 재시도 실제 비용, 취소 후 미확정 예약, 다른 공간 접근·회원 제거, revision 충돌. DB·인증·실행기 선정 뒤 통합 검증 |

실행기 실험은 두 후보에 동일한 흐름을 적용한다: 근거 조회 → 유료 호출 attempt 기록 → 공급자 결과 → 검증 모듈 저장 → 완료. 결과 수신 직후 저장 전 중단, 저장 뒤 SSE 전송 전 중단, 이벤트 전달 중 재접속, 취소, 새 worker 버전 배포를 주입한다. 공개 이벤트 누락/중복, 외부 호출 횟수·비용, 복구 시간, 첫 검증 모듈 지연·메모리·운영 구성을 기록한다. 공급자 시뮬레이터는 장애 검증 도구로만 사용하고 제품 자료·AI 결과로 표시하지 않는다.

지금 사용자에게 서버·키 추가 작업은 필요하지 않다. 실제 자료 평가 전에 첫 이슈·대표 질문 3~5개와 허용 원문을 함께 선정하고, 이후 기존 서버의 읽기 스냅샷·수집 현황을 확인한다. 성능·정확도·월 비용은 그 자료로 측정하기 전까지 미검증이다.

관련 원본: [요구사항·설계](../planning/requirements-design.md), [결정 기록](../planning/decisions.md), [작업 목록](../planning/tasks.md), [진행 기록](../planning/progress.md).
