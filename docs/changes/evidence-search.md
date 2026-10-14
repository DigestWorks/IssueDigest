# 저장 근거의 PostgreSQL 문자 검색 기반

2026-10-14. R2/R3·D011/D015의 첫 검색 경로다. 같은 PostgreSQL을 개발/운영에서 사용한다. 공동 앱 DB 설정/백업 확인은 대기이며 전용 검증 DB에서만 실행한다. OpenSpec root=null이므로 이 명세와 Superpowers 구현 단계를 사용한다.

## 범위·수용 조건

저장된 불변 EvidenceBundle에서 한국어 검색어·명칭·식별자를 문자 그대로 찾고, 원문 버전과 정확한 텍스트/페이지/셀 위치를 반환한다. 의미 검색·형태소 분석·질문 답변·근거의 주장 지지는 이 변경의 결과가 아니다. HTTP·화면·DBOS/outbox 소비·벡터 임베딩은 후속이다.

- typed SDK의 검색 입력은 literal terms 1~8개, 각 1~64 Unicode code points, 비공백·중복 없는 문자열, 결과 한도1~20이다. 앞뒤 공백을 명시적으로 거부한다. 같은 검색 단위 안에 모든 term이 포함되는 AND 검색이며 ASCII A~Z만 소문자로 비교한다. Unicode 정규화/한국어 어간 추정/와일드카드 해석을 하지 않는다. 선택 필터는 정확 provider/source_id/source_kind, UTC-aware collected_from/to(수집 시각, 시작 포함/끝 제외)이고 시간 순서를 검사한다.
- 도메인 모델은 frozen/extra=forbid/엄격 한도이며 construct/copy로 우회한 SDK 입력도 다시 검증한다. 검색 결과는 workspace/snapshot/document/version/representation 및 source metadata(provider/source_id는 canonical NonBlank 문자열 전체를 보존하며 query 필터 한도로 자르지 않음)·selector·matched terms·anchor_status=matched·support_status=not_evaluated를 갖는다. 새로운 Citation UUID를 만들어 등록된 인용처럼 보이지 않는다. 기존 Citation 검증에서 selector 검증을 재사용 가능하게 분리해 기존 동작을 보존한다.
- profile literal-ngrams-v1: 본문512자, 중첩63자; PDF는 기존 PageSpan 안에서만 분할한다. application/pdf의 비어 있지 않은 본문에 PageSpan이 없으면 고정 입력 오류로 거부하며, 빈 PDF 본문의 온전한 셀은 페이지를 주장하지 않고 투영할 수 있다. 정확 application/pdf만 PDF 분할 조건이며, 일반 본문은 PageSpan metadata가 있어도 전체 본문과 span 사이 텍스트를 TextQuoteSelector로 분할한다. PDF는 PdfQuoteSelector(실제 page, regions는 추정하지 않음), 2,048자 이하 비어 있지 않은 표 셀은 온전한 TableCellSelector다. 큰/빈 셀의 제외 건수를 별도로 기록하며 본문에 있는 내용은 본문 단위로 찾을 수 있다. 각 selector를 원 표현과 대조한다. 텍스트1,000,000자/표1,000개/셀20,000개/검색 단위6,000개/단위 텍스트 총2,000,000자 한도를 직렬화/전체 투영 생성 전에 검사하고 고정 오류로 거부한다.
- 결정적 단위 순서/selector/text/checksum과 ASCII 비교용 문자1·2·3-gram 집합을 만든다. PostgreSQL native ARRAY + GIN @> 연산으로 후보를 제한하고 실제 문자 포함 여부를 재검사한다. 검색용 변환으로 원문 offset을 바꾸지 않는다. 새 extension/service/dependency를 설치하지 않는다. [GIN 배열 연산](https://www.postgresql.org/docs/18/indexes-types.html), [배열 포함 연산](https://www.postgresql.org/docs/18/functions-array.html)을 따른다.
- storage의 명시 rebuild_projection(workspace_id,snapshot_id)는 canonical EvidenceRepository load를 재사용하고 하나의 DB transaction에서 projection manifest/units를 교체한다. 없는 자료는 None, 동일 내용은 unchanged, 변경/실패는 원 근거·인용·outbox·이전 투영을 보존한다. 동일 snapshot 병렬 rebuild는 직렬화하고 반복 결과가 같다. source snapshots와는 별도의 재생성 가능한 projection이다. 새 Alembic migration0004의 FK/한도/check/index 및 upgrade/downgrade를 검증한다. import/startup/save에 숨은 migration/rebuild/network 호출을 추가하지 않는다.
- WorkspaceAccessRepository.search_evidence(session_token,workspace_id,query)는 기존 _transaction/_authorize/_refresh와 현재 membership 잠금을 재사용한다. 만료/폐기/disabled는 AuthenticationDenied, 다른 공간/비회원은 None, 권한 있는 검색만 last_activity를 갱신한다. REPEATABLE READ/40001 재시도 경계를 보존한다. workspace 필터는 SQL 후보·coverage·canonical reload 모두에 적용한다. 보호 SDK의 성공 결과는 typed model이다.
- 후보는 최대200개(+1로 잘림 확인), 정렬은 수집 시각 desc·snapshot ID·unit ordinal의 결정적 순서다. 필터는 원 문서/버전에서 얻으며 published_at이나 정책 시행 시각으로 부르지 않는다. 같은 snapshot 후보가 연속하는 SQL 순서에 따라 현재 snapshot의 전체 canonical bundle/projection만 유지하고 다음 snapshot 전에 이전 전체 상태를 해제하되 이미 반환할 hit selector는 보존한다. 모든 조사 후보를 canonical bundle과 selector/text/checksum/source identity/profile로 검증하고 불일치는 고정 StorageCorruption/StorageError로 실패한다. 후보 ngram은 검색어 순서·반복을 보장하지 않으므로 정확 재검사를 반드시 한다. 결과는 필터 범위 total/indexed/missing snapshot 수·skipped cell 수, scanned candidate 수·truncated를 제공한다. 한도/미투영 자료가 있는 빈 결과를 전체 자료에 답이 없다는 판단으로 쓰지 않는다. 일치가 0이어도 투영 상태를 알 수 있다. 관련성 점수/Recall/semantic confidence를 조작하지 않는다.
- 공개 tests는 합성 데이터만. 실제 원문·인용·hash/UUID·승인 계정/접속 설정은 private700/600 산출물로 보관한다. 전용 loopback 소유 DB에서만 migration/쓰기·합성 세션을 검증한다. 공동 DB/승인 등록 계획/사용자 초대·공유 checkout·운영 서비스/main·공개 앱은 변경하지 않는다.

## Global Constraints

기존 domain/storage/auth 계약을 재사용한다. worker 앱 내부를 패키지에서 가져오지 않는다. 새 외부 종속성·공급자 호출·pgvector/Neo4j/DBOS runtime은 추가하지 않는다. 실제 공동 DB 적용·OAuth·검색 평가20문항 통과·AI 답변·제품 완성을 주장하지 않는다. 외부 CI/draft PR·Sites 요약과 개인 개발 코드 인계는 기존 승인 범위이며 main 병합/앱 공개는 D013에 따라 유예한다.

## 구현 태스크

### Task 1: 문자 검색 계약·투영·보호 조회 SDK

- [x] 합성 TDD: 한국어/ASCII/emoji/combining char/SQL metacharacter·한도·PDF 경계/셀 전체 인용·construct 우회·후보 오탐/잘림·필터/coverage·없는 투영·변조/오류·다른 공간/세션 폐기·반복/rollback/병렬·마이그레이션 roundtrip. 실제 assertion RED 후 구현한다.
- [x] packages/domain의 search 모델/결정적 단위·selector 검증, packages/storage의 별도 projection schema/migration0004·명시 rebuild·현재 권한 보호 search SDK를 구현한다. 기존 save/load/auth의 동작·생성 웹/API 계약을 유지한다.
- [x] 관련 README에 실제 SDK 사용법·필터/잘림/미투영/문자검색 한계·명시 migration/rebuild·후속 API/UI/pgvector를 기록한다. targeted 테스트·format/lint/mypy/self-review·commit과 작업 보고를 남긴다. controller는 독립 리뷰를 수행한다.

## Controller 검증·기록

- [x] 실제 private HWPX3개를 새 전용 DB에서 투영하고 정확 term/본문·셀 위치/필터/권한/반복을 검증한다. 작은 실자료 위치 검증은 평가20문항/전체 검색 품질과 구분한다.
- [ ] 전체 검사·독립 전체 리뷰·문서/개인정보 검증·Draft PR/앱 첨부·Sites 이전 기록 보존·개발 인계. 실제 공동 DB 설정/백업 입력 대기를 별도로 기록한다.

## 검증 기록

최종 코드f5e3314에서 controller 전체 Python1,787+JS322=2,109개·정적/타입/SPA/OpenAPI 검사 통과, skip/warning0. 작업 리뷰의 전체 투영 보관·canonical metadata 한도·비PDF PageSpan 분기 세 항목을 한 번의 수정 범위에서 assertion RED8개 후 보완했다. 기능84개·영향 도메인/저장968개 통과, 수정 범위 재검토에서 세 항목 해결·새 지적0으로 승인받았다. 독립 전체 변경 리뷰는 진행 중이다. 실제 HWPX3개·문자 검색9건/전체 셀6건을 제한된 전용 앱 역할로 재검증, 원문/버전/selector 모두 일치·주장 지지 미평가·반복 unchanged3·미색인/필터/다른 공간/세션 폐기 검증. 공동 DB 적용/실제20문항 점수/의미 검색·HTTP/UI·대규모 성능은 후속이다.
