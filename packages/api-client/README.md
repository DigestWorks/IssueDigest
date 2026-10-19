# 웹 API 클라이언트·생성 타입

npm workspace의 비공개 TypeScript 소스 패키지입니다. 웹이 `@issuedigest/api-client`를 가져와 같은 출처의 상태 확인, 보호 세션·자료 목록·근거 GET과 로그아웃 POST를 호출합니다. 별도 게시·번들·서버 앱은 없습니다.

Python 도메인 모델과 FastAPI OpenAPI가 계약의 원본입니다. `openapi.json`과 `src/schema.d.ts`는 생성 산출물이며 버전 관리합니다. `getStatus`는 생성 타입을 사용하고 응답을 런타임에도 검사합니다. 생성 스키마의 리터럴이나 필수 필드가 바뀌면 클라이언트의 타입 검사도 재검토를 요구합니다.

저장소 루트에서 실행합니다.

```sh
npm ci
npm run setup
npm run contract:generate
npm run contract:check
npm run typecheck
npm test
```

`getStatus()`는 `{ data, requestId }`를 반환합니다. `ConnectionError.kind`는 `http`, `invalid-response`, `network`, `timeout`을 구분합니다. 정상 응답의 세 필드·리터럴·추가 필드·서버 UUID를 검증하고 잘못된 JSON·HTTP 오류를 성공으로 취급하지 않습니다. 확인 가능한 서버 요청 ID는 오류에도 보존합니다.

기본 제한 시간은 5초이며 `getStatus({ timeoutMs })`로 변경할 수 있습니다. 제한 시간은 응답 본문 읽기까지 포함하고 느린 요청을 중단합니다. 자동 재시도·캐시·인증·공급자 호출은 없습니다. 재시도는 화면에서 사용자가 요청합니다.

`contract:check`는 임시 폴더에서 OpenAPI와 타입을 재생성하고 커밋 대상 파일과 바이트 비교합니다. 파일을 바꾸거나 Git 상태에 의존하지 않고 차이가 있으면 실패합니다. TypeScript 5.9.3은 현재 `openapi-typescript`의 `^5.x` 지원 범위를 만족하도록 고정합니다. 생성 파일을 직접 수정하지 않습니다.

첫 원문·인용 계약의 생성 타입도 공개합니다: `SourceDocument`, `DocumentVersion`, `ParsedRepresentation`, `PageSpan`, `ParsedTable`, `TableCell`, `Citation`, `TextQuoteSelector`, `PdfQuoteSelector`, `NormalizedBox`, `TableCellSelector`, `EvidenceBundle`, `CitationAnchorValidation`. 수기 TypeScript 계약을 별도로 복제하지 않습니다. 이 첫 계약의 모델은 실제 앱의 OpenAPI components에 등록되었습니다. 현재 보호 근거 GET과 읽기 화면은 아래 절에서 설명합니다. 자료 수집이나 쓰기 동작을 추가하지 않습니다.

`getCitationUtf16Range(text, selector)`는 Python `model_dump`가 기본값까지 포함한 생성 text/pdf 전송 타입을 받아 `{ start, end }`의 JS UTF-16 인덱스를 반환합니다. 먼저 code point 범위와 quote·prefix/suffix의 정확한 일치를 확인하고 잘못된 입력을 throw합니다. 한글·BMP 밖 이모지·결합 문자·공백·NFC/NFD를 그대로 보존하며 grapheme cluster로 분할하지 않습니다. 생성 타입의 text/pdf kind를 요구하며 table selector는 입력이 아닙니다. PDF 페이지/좌표·버전 연결은 서버의 표현/번들 검증 범위이며 이 함수는 제공된 텍스트의 인용 범위만 확인합니다. Python과 TS 테스트는 `tests/fixtures/citation-unicode.json` 합성 자료와 같은 offsets를 공유합니다.

정확한 anchor가 일치해도 `support_status="not_evaluated"`이며 주장 지지·원문 보관·접근 권한·파싱 성공을 보장하지 않습니다. 출처 날짜 정밀도·재수집 관측·비교 fingerprint·실제 parser와 저장·실행 이벤트 저장·SSE·화면 렌더러·사용량 집계는 후속 작업입니다.


두 번째 부분 계약의 생성 타입도 공개합니다: `SourceIdentity`, `Entity`, `Claim`, `DerivationRecord`, `IdentityReview`, `SupportReview`, `EntityReference`, `ClaimReference`, `DocumentReference`, `RelationReference`, `Relation`, `DateInterval`, `Dimension`, `ComparisonContext`, `Observation`, `ComparisonReason`, `ComparisonAssessment`, `ResearchBundle`. 공개 aliases는 실제 OpenAPI에서 생성한 `components` 타입을 가리킵니다. compile 소비자는 수치를 number로 바꾸거나 document를 검토 target으로 쓰거나 미등록 인과 predicate·합산 승인을 넣으면 실패합니다. TypeScript 타입은 Python의 날짜 정밀도·UUID4·참조 연결·수치 문법·판정 일관성 검증을 실행하지 않습니다.

이 추가는 TypeScript 런타임 기능이나 제품 HTTP 경로를 만들지 않습니다. 비교 계산은 Python의 `assess_comparison`이 수행하며 수치 자체를 비교·합산하지 않습니다. `same_context`는 알려진 조건의 일치만 뜻하고 합산/분포는 `not_evaluated`입니다. 인용 존재·입력된 사람 검토는 주장 내용의 진실이나 인증된 검토 행위를 보장하지 않습니다.


세 번째 부분 계약은 `ExecutionVersions`, `RunInput`, `RunSubmission`, `Run`, `SubmissionAssessment`, `RunEvent`, `RunHistory`, `RunSnapshot`, `ReplayBatch`, `CallAttempt`, `CanvasDraft`, `CanvasRevision`, `CanvasBundle`, `PricingSnapshot`, `BudgetWindow`, `UsageReservation`, `UsageEntry`, `UsageBook`, `BudgetAssessment`, `RunExecutionBundle`과 종류별 모듈/액션 aliases를 공개합니다. `CanvasModule`, `CanvasAction`, `RunEventPayload`, `MoneyMicrowon`도 실제 생성 component의 필드에서 유도합니다. 내부 payload 클래스를 모두 공개할 필요는 없으며 수기 schema를 복제하지 않습니다.

`tests/execution-types.ts` compile 소비자는 금액 문자열, 완성된 module.ready, bar 차트와 제안 액션을 사용하고 숫자 금액·임의 HTML·pie·도구 실행·원시 예외를 거부합니다. TypeScript는 UUID4·참조 연결·JS 안전 정수 범위·money 문법·상태 전이·예산식을 런타임에 검증하지 않습니다. Python의 입력 검증이 원본입니다. 이 추가는 새로운 TS 런타임·렌더러·제품 HTTP/SSE 경로를 만들지 않습니다.


## 보호 근거 GET

`getEvidence(workspaceId, snapshotId, options?)`는 기존 `GET /api/v1/workspaces/{workspace_id}/evidence/{snapshot_id}`를 호출하고 `{ data: EvidenceBundle, requestId: string }`을 반환합니다. 요청은 relative URL, `credentials: same-origin`, `cache: no-store`를 사용합니다. 원문이나 토큰을 저장소, query, 로그에 기록하지 않습니다.

두 경로 ID는 fetch 전에 UUID4로 검사합니다. `options.timeoutMs`는 기본 10,000ms이며 양의 finite integer만 받습니다. 유효하지 않은 ID나 timeout은 `invalid-link` 오류로 거부하며 fetch하지 않습니다. deadline은 헤더와 JSON body를 모두 포함합니다. `options.signal`은 이미 취소된 경우와 진행 중 취소에 반응합니다. 각 요청은 timer와 abort listener를 정리합니다.

`EvidenceError.kind`는 `invalid-link`, `authentication`, `not-found`, `unavailable`, `invalid-response`, `network`, `timeout`, `aborted`입니다. 401, 404, 503을 구분하고 다른 HTTP 실패도 `unavailable`로 분류합니다. 메시지는 고정된 오류 종류만 포함합니다. 오류 본문, 서버 detail, 원시 예외는 반환하지 않습니다. 오류의 `requestId`는 UUID4 서버 헤더가 확인된 경우에만 전달합니다.

200 응답은 JSON media type, 유효한 `X-Request-ID`, `Cache-Control: no-store`와 다음 표시 경계를 통과해야 합니다.

- schema version 1과 document, version, representation, citations envelope.
- 요청 workspace, document→version→representation chain과 각 citation의 version 및 representation 참조.
- 필요한 source 문자열과 종류, credential 없는 HTTP(S) 원문 링크, 시간대가 있는 유효한 수집 시각. 필수 UUID, parser 문자열, SHA256 형식도 확인합니다.
- text 타입과 code point 범위 안의 순서 있는 비어 있지 않은 PageSpan. 실제 페이지 번호는 양의 정수이며 중복이 없습니다. 페이지 번호의 크기로 저장 순서를 변경하지 않습니다.
- 고유 citation ID, 고유 table ID, 표 안의 고유 cell ID와 cell text 타입.
- text와 PDF selector의 정확한 quote, prefix, suffix와 Unicode 범위. PDF는 실제 페이지 경계와 정상화된 region 범위를 확인합니다.
- table_cell selector는 등록된 표와 셀을 참조하며 quote가 전체 cell text와 정확히 일치해야 합니다. 공백과 빈 셀 내용을 변형하지 않습니다.

이 검증은 JSON을 타입 cast만으로 성공 처리하지 않으며 화면이 사용하는 메타데이터를 모두 확인합니다. 서버의 전체 Pydantic 스키마를 재구현하지 않습니다. 사용하지 않는 선택적 table 연구 메타데이터, 추가 필드, 원문 해시의 실제 재계산은 이 경계의 검증 대상이 아닙니다. 인증, 멤버십, 저장된 원문의 진위와 무결성, 의미적 주장 지지는 서버와 별도 검토의 책임입니다. 공개 배포는 별도입니다.

집중 검사는 저장소 루트에서 실행합니다.

```sh
npm test -- packages/api-client/tests/evidence.test.ts apps/web/tests/evidence.test.tsx
```

합성 `tests/fixtures/canvas-synthetic.json`을 테스트에만 사용합니다. 정상 Unicode 변형은 text hash를 재계산합니다. HTTP 실패, 잘못된 헤더와 JSON, 교차 workspace, 참조·페이지·표·인용 오류, 취소, 헤더 및 본문 timeout을 확인합니다. 전체 서버 및 실제 합성 PostgreSQL 결합 검증은 Controller가 별도로 수행합니다.

## 보호 세션·로그아웃

`getSession(options?)`는 `/api/v1/auth/session`에서 생성된 `SessionInfo` 타입의 `{ data, requestId }`를 반환합니다. `logout(options?)`는 `/api/v1/auth/logout`에 POST하고 검증된204에서 `{ requestId }`를 반환합니다. Origin은 브라우저가 설정하며 JS는 토큰·가짜 CSRF·사용자 신원을 전송하지 않습니다.

두 경계는 같은 출처 쿠키·no-store·기본10초 헤더/본문 deadline·AbortSignal과 요청별 정리를 사용합니다. `AuthError`는 고정 kind로 HTTP 오류 본문/원시 예외를 숨기고 유효한 UUID4 요청 ID만 보존합니다. 세션은 schema1·사용자/작업 공간 UUID4·viewer/editor/owner·최대100개·고유 UUID 오름차순 멤버십과 정확 필드를 검증합니다. `tests/auth.test.ts`는 계약·권한 오류·본문/헤더 timeout·취소/늦은 응답·안전한 로그아웃을 검사합니다. 실제 공급자 로그인·DB/운영 검증을 대신하지 않습니다.

미사용 수동 자료 목록 클라이언트/타입과 전용 테스트는 제거했습니다. 서버의 독립 보호 자료 목록과 원문/검색 API를 삭제하거나 공개하지 않습니다.

## 보호 근거 문자 검색

`searchEvidence(workspaceId, { terms: ['등록금', '2026'], limit: 10 }, options?)`는 현재 세션의 작업 공간에 JSON POST를 보내 `{ data: EvidenceSearchResult, requestId }`를 반환합니다. 생성 타입 `EvidenceSearchQuery`, `EvidenceSearchResult`, `EvidenceSearchHit`와 요청용 `EvidenceSearchInput`을 공개합니다. 검색어는 URL이나 브라우저 저장소에 넣지 않습니다. 선택 필터 `provider`, `source_id`, `source_kind`, UTC `collected_from`/`collected_to`를 입력에 넣을 수 있습니다.

입력은 1~8개 단어, 각 1~64 Unicode code points, 공백 없는 양끝과 ASCII 기준 중복 금지, limit 1~20을 확인합니다. 응답은 필드·타입·개수·UUID4·수집 시각·위치 selector, 요청한 공간·검색어·필터·hit 일치와 coverage를 확인합니다. `SearchError.kind`는 `invalid-query`, `forbidden`, `unauthorized`, `not-found`, `unavailable`, `malformed`, `network`, `timeout`, `aborted`입니다. 기존 보호 요청의 same-origin cookie, no-store, 요청 ID, 헤더와 본문을 포함한 10초 기본 deadline 및 AbortSignal을 사용합니다. Origin 헤더는 브라우저가 설정합니다.

검색은 원문에 포함된 문자만 찾습니다. `coverage.missing_snapshots`가 양수이면 일부 자료가 미색인 상태이고 `truncated`는 후보 또는 결과 한도에 걸렸음을 뜻합니다. 빈 결과를 근거 없음으로 단정하거나 검색 위치를 저장된 인용·주장 지지 판정으로 취급하지 않습니다. 원문 위치를 열 때는 로드한 `EvidenceBundle`과 hit의 ID·selector를 다시 대조해야 합니다.

`resolveSearchSelection(routerState, bundle, workspaceId, snapshotId)`는 보호 GET에서 검증한 `EvidenceBundle`에 검색 hit가 가리키는 원문 위치가 정확히 존재하는지 확인합니다. workspace/snapshot/document/version/representation과 출처 메타데이터를 대조한 뒤 text/PDF의 quote·prefix·suffix·code point 범위와 실제 PDF 페이지, 표의 전체 cell text를 검사합니다. 유효하면 selector와 UTF-16 범위를 반환하고, 잘못되거나 오래된 상태에는 `null`을 반환합니다. router state는 저장된 인용을 만들지 않습니다. state가 없는 직접 URL은 선택 없이 읽고, 기존 history 항목을 새로고침해 state가 유지되면 보호 GET 후 canonical 검증을 다시 수행합니다.

## 조사 클라이언트

`listResearchRuns`, `getResearchRun`, `submitResearch`, `cancelResearchRun`은 OpenAPI 생성 타입과 응답 검증을 사용합니다. 모든 요청은 같은 출처 쿠키·`no-store`·서버 request ID를 확인하고 원시 HTML/JS를 실행하지 않습니다. `ResearchRun.result.canvas`는 기존 `CanvasView`에 전달하고 `source_titles`는 document ID를 실제 제목으로 바꿀 때 사용합니다. `ResearchError.kind`는 `conflict`(409), `budget`(429), `unavailable`(503)을 포함합니다. 사용자 재시도 때 같은 `request_id`를 재사용하면 재과금 없이 같은 run을 얻습니다. GET/새로고침은 모델 호출을 시작하지 않습니다.


`submitResearch(workspaceId, {request_id, question, parent_run_id?}, options?)`는 질문과 선택적인 완료 부모 실행만 허용합니다. snapshot_ids/임의 필드·빈 질문·잘못된ID는 전송 전에 거부합니다. `ResearchRun.snapshot_ids`는 서버가 찾은0~5개 근거의 기록입니다. queued/무근거실패의 빈 근거와 완료 결과의1개 이상 근거를 구분하며 잘못된 상태/이벤트/결과는 거부합니다. 저장된 research-v1/v2와 private research-v3/v4/v5의 정확 인용/Canvas를 검증해 읽습니다. v3는 고정 automated reviewer metadata·1개/claim·정확 인용 순서·300자 설명·허용 scope/assessment와 UTC 시각을6자리 소수초까지 대조합니다. 혼합/누락/중복·다른 대상/인용·잘못된 시각은 거부합니다. 과거 결과에 분류를 추정하지 않습니다. 전용 research source catalog 클라이언트/타입/endpoint는 없습니다.


## 익명 공개 브리핑 GET

`listPublicBriefings(options?)`, `getPublicBriefing(slug, version?, options?)`과 생성 계약의 PublicBriefingSummary/Detail/List·PublicSourceAttribution·PublicBriefingErrorResponse 타입을 제공합니다. slug와 안전한 양의 정수 버전은 fetch 전 검사합니다. GET은 same-origin/no-store이며 JSON·요청 ID/no-store 헤더·정확 필드/형식·최대20목록·5자료/12claims/4모듈·고유 ID/참조·공개 provenance·공식 policyNewsView URL·출처 title/date/hash 대응·정확 인용을 검증합니다. 보호 연구의 bounded Canvas/evidence 검증은 공유하되 공개는v1/v2·빈 support_reviews만 허용합니다. v3의 review 배열을 제거해도 공개 응답으로 허용하지 않습니다.

기본10초 deadline은 헤더/본문에 적용하며 외부 abort·timeout·network·404·503·malformed를 구분합니다. 원시 오류 본문을 표시하지 않고 자동 재시도/쓰기/모델/세션 요청을 하지 않습니다. 서버가 공개 UUID namespace와 전체 canonical payload digest를 검증합니다. 브라우저는 hash 형식과 같은 고정 버전의 불변 hash를 비교하며 Python canonical 숫자 직렬화를 별도로 재구현하지 않습니다. 클라이언트 암호학적 증명·자동 사실/권리 판정을 주장하지 않습니다. 서버가 검토한 공개 source만 원문 창에 전달합니다.

private v4도 기존 세 분류/300자 설명/동일 인용 순서/UTC 마이크로초 검증과 UI를 사용한다. reviewer_id issuedigest-research-v4와 method_version research-v4가 같은 버전의 모든 claim에 정확히 일치해야 하며 v3/v4/v5 혼합·누락·다른 인용/시각은 거부한다. 공개는 계속 v1/v2/빈 reviews만 허용하고 v3/v4/v5는 review를 제거해도 거부한다. generic Claim/default·OpenAPI·과거 canonical JSON/hash는 변경하지 않는다.


새 private v5의 고정 reviewer_id는 `issuedigest-research-v5`, method_version은 `research-v5`다. 같은 엄격 분류·UTC 마이크로초·인용 순서·claim당1개 규칙을 적용한다. v3/v4/v5를 서로 섞지 않고 public v1/v2/빈 reviews 경계를 유지한다. 과거 결과를 새 분류로 다시 쓰지 않는다.


private research-v6도 고정 issuedigest-research-v6/research-v6와 claim당 정확1개 평가·동일 인용 순서·UTC 마이크로초를 검증한다. 첫 모듈은 summary이고 첫 claim의 평가는 supported여야 하며 나머지는 comparison/timeline 상세와 마지막 evidence다. v6 provider에는 category/source_subject 필드가 없고 긍정 해석은 서버가 고정한 `제공 자료에 따르면, ` 주체로 attributed 변환된다. canonical 결과는 기존 documented 분류와 정확한 custom subject 검증을 계속 허용한다. 과거 v1~v5 결과·공개 v1/v2/빈 reviews 경계와 OpenAPI는 유지한다. Python 실제 v6 builder의 합성 fixture를 웹과 함께 소비하며 혼합/누락/위조/stripped-public를 거부한다.

v6 claim text와 모델 module title은 Python과 같은 Unicode code-point 기준500/100자 한도를 검사한다. canonical 귀속 주체는 최대80자, 본문은 최대400자로 검사하며 custom subject는 모든 선택 원문 인용에 있어야 한다. 고정 `제공 자료` 주체는 이 부분 문자열 검사의 예외다. 생성 astral fixture는 고정 `제공 자료` 주체와 400-code-point astral 본문을 사용하고, 80-code-point custom subject는 별도 canonical 호환성 검사다. 다른 private 버전의 기존 raw-client 길이 검사와 비답변의 공통 경계는 유지한다.


v6 본문과 canonical 귀속 주체의 nonblank 검사는 Python Unicode whitespace와 ECMAScript WhiteSpace/LineTerminator 합집합으로 통일한다. NEL(U+0085)·BOM(U+FEFF) 단독/혼합 공백만 있으면 거부한다. 공유 명시 predicate는 검사만 하며 유효한 원문과 앞뒤 공백은 변경하지 않는다. 과거 공통 필드·비답변 경계는 유지한다.


private research-v7는 정확 issuedigest-research-v7/research-v7만 추가한다. v6의 첫 supported summary·comparison/timeline 상세·정확 귀속 주체/인용/날짜·Unicode code-point/nonblank 검사를 그대로 적용한다. API/OpenAPI shape·과거 raw-client 동작·공개v1/v2·빈 reviews 계약을 보존하며 stripped-public v7도 거부한다. 실제 Python v7 builder 생성 fixture가 전체 client와 동일 UI의 열린 첫 요약·접힌 상세·정확 원문/비답변 경로를 통과한다. 이는 사실 검증 인증이나 실제 모델 의미 품질 평가가 아니다.


private research-v8도 정확 `issuedigest-research-v8`/`research-v8`만 허용한다. v6/v7의 첫 supported summary·귀속 접두어·Unicode·인용별 정확 날짜·동일 평가 인용 순서·UTC와 혼합/누락/위조 거부를 그대로 적용한다. 실제 Python builder의 날짜0 comparison/정확 날짜 timeline/astral/비답변 fixture를 full client가 소비한다. intact/stripped privatev8은 public에서 거부하며 OpenAPI와 공개 계약을 넓히지 않는다.
