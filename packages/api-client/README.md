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
npm test -- packages/api-client/tests/evidence.test.ts apps/web/tests/evidence.test.tsx apps/web/tests/evidence-link.test.tsx
```

합성 `tests/fixtures/canvas-synthetic.json`을 테스트에만 사용합니다. 정상 Unicode 변형은 text hash를 재계산합니다. HTTP 실패, 잘못된 헤더와 JSON, 교차 workspace, 참조·페이지·표·인용 오류, 취소, 헤더 및 본문 timeout을 확인합니다. 전체 서버 및 실제 합성 PostgreSQL 결합 검증은 Controller가 별도로 수행합니다.

## 보호 세션·자료 목록·로그아웃

`getSession(options?)`와 `getEvidenceCatalog(workspaceId, options?)`는 생성된 `SessionInfo`·`EvidenceCatalog` 타입의 `{ data, requestId }`를 반환합니다. 세션은 `/api/v1/auth/session`, 목록은 `/api/v1/workspaces/{workspace_id}/evidence?limit=50`에 GET합니다. `logout(options?)`는 `/api/v1/auth/logout`에 POST하고 검증된 204에서 `{ requestId }`를 반환합니다. Origin은 브라우저가 설정합니다. 토큰·가짜 CSRF·사용자 identity를 JS에서 전송하지 않습니다.

세 경계는 relative URL·same-origin credentials·no-store, 기본 10초 헤더/본문 deadline, 외부 AbortSignal과 요청별 정리를 사용합니다. `AuthError`·`CatalogError`의 고정 kind는 `timeout`, `aborted`, `unauthorized`, `not-found`, `unavailable`, `malformed`, `network`입니다. HTTP 오류 본문이나 원시 예외를 노출하지 않고 유효한 UUID4 요청 ID만 보존합니다. 잘못된 ID나 양의 안전 정수가 아닌 timeout은 요청 전에 `malformed`로 거부합니다.

성공 GET은 JSON media type·no-store·요청 UUID와 표시 계약을 검증합니다. 세션은 schema 1·사용자/작업 공간 UUID4·viewer/editor/owner·최대 100개·고유한 UUID 오름차순 멤버십을 요구합니다. 목록은 같은 workspace·schema 1·최대 50개·고유 snapshot·문서 UUID4·NonBlank 공급처/출처·원문 종류·credential 없는 HTTP(S) URL·실제 UTC ISO 수집 시각·최대 160 Unicode code point excerpt·안전한 음이 아닌 정수 인용 수·strict bool을 요구합니다. 이 두 모델의 추가 필드도 거부합니다. 서버의 권한·자료 진위·권리·주장 지지 검증을 대체하지 않습니다.

`packages/api-client/tests/auth-catalog.test.ts`는 합성 응답으로 잘못된 계약·본문/헤더 timeout·취소·안전 오류를 검사합니다. 실제 공급자 로그인·DB 연결·운영 설정은 이 검사의 범위가 아닙니다.

## 보호 근거 문자 검색

`searchEvidence(workspaceId, { terms: ['등록금', '2026'], limit: 10 }, options?)`는 현재 세션의 작업 공간에 JSON POST를 보내 `{ data: EvidenceSearchResult, requestId }`를 반환합니다. 생성 타입 `EvidenceSearchQuery`, `EvidenceSearchResult`, `EvidenceSearchHit`와 요청용 `EvidenceSearchInput`을 공개합니다. 검색어는 URL이나 브라우저 저장소에 넣지 않습니다. 선택 필터 `provider`, `source_id`, `source_kind`, UTC `collected_from`/`collected_to`를 입력에 넣을 수 있습니다.

입력은 1~8개 단어, 각 1~64 Unicode code points, 공백 없는 양끝과 ASCII 기준 중복 금지, limit 1~20을 확인합니다. 응답은 필드·타입·개수·UUID4·수집 시각·위치 selector, 요청한 공간·검색어·필터·hit 일치와 coverage를 확인합니다. `SearchError.kind`는 `invalid-query`, `forbidden`, `unauthorized`, `not-found`, `unavailable`, `malformed`, `network`, `timeout`, `aborted`입니다. 기존 보호 요청의 same-origin cookie, no-store, 요청 ID, 헤더와 본문을 포함한 10초 기본 deadline 및 AbortSignal을 사용합니다. Origin 헤더는 브라우저가 설정합니다.

검색은 원문에 포함된 문자만 찾습니다. `coverage.missing_snapshots`가 양수이면 일부 자료가 미색인 상태이고 `truncated`는 후보 또는 결과 한도에 걸렸음을 뜻합니다. 빈 결과를 근거 없음으로 단정하거나 검색 위치를 저장된 인용·주장 지지 판정으로 취급하지 않습니다. 원문 위치를 열 때는 로드한 `EvidenceBundle`과 hit의 ID·selector를 다시 대조해야 합니다.

`resolveSearchSelection(routerState, bundle, workspaceId, snapshotId)`는 보호 GET에서 검증한 `EvidenceBundle`에 검색 hit가 가리키는 원문 위치가 정확히 존재하는지 확인합니다. workspace/snapshot/document/version/representation과 출처 메타데이터를 대조한 뒤 text/PDF의 quote·prefix·suffix·code point 범위와 실제 PDF 페이지, 표의 전체 cell text를 검사합니다. 유효하면 selector와 UTF-16 범위를 반환하고, 잘못되거나 오래된 상태에는 `null`을 반환합니다. router state는 저장된 인용을 만들지 않으며 직접 링크와 새로고침에는 전달되지 않습니다.
