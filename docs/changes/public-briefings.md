# 비회원 브리핑 읽기와 명시 게시

2026-10-16. D016~D019·R1/R2/R4와 제품 인터뷰의 비회원 읽기 → AI 질문부터 로그인 여정을 연결한다. 이전 질문 전용 작업은 완료됐으며 임시 자료 도구를 추가하지 않는다. OpenSpec root=null이므로 명세 기반 SDD/TDD·독립 검토를 적용한다.

## Global Constraints

- 현재 비공개 근거·질문·실행·멤버십/세션을 공개로 전환하지 않는다. 공개 게시물은 운영자가 전체 공개 내용·근거의 이용 범위를 검토한 불변 복사본이다. 비공개 run/question/actor/session/request/provisioning 정보를 가져오는 자동 게시나 브라우저 쓰기 API를 만들지 않는다. 사용자 초대·가입·모델/예약 정책을 바꾸지 않는다.
- 최초 지원 출처는 공공누리1유형 텍스트 재게시를 개별 확인한 한국정책브리핑 공식 policyNewsView 문서다. HTTPS www.korea.kr/news/policyNewsView.do?newsId=<ASCII numeric>만 허용하고 다른 query·자격정보·fragment·호스트를 거부한다. 같은 정부 사이트의 모든 내용에 이용권을 추정하지 않는다. 각 원문의 정확한 텍스트 SHA·공식 URL·발행일·출처/저작자·KOGL1 조건 확인 시각·검토자와 사진/이미지 제외 확인이 게시 계획에 있어야 한다. 모델 생성물/변환 문구와 원문을 구분하고 인용 일치를 사실 판정으로 표시하지 않는다.
- 입력은 명시 PublicBriefingPlan이다: slug(ASCII 소문자/숫자/단일 hyphen,3~80자), public_id(UUID4), version(양의 안전 정수), title(1~150), description(1~350), as_of(UTC), CanvasBundle와 각 evidence.document_id에 정확히 대응하는 출처 검토(title/publisher/published_on/checked_at/reviewer/license=kogl-type-1/attribution/정확 representation.text_sha256/사진·외부 저작물 제외 확인). 공개용 title/description은 private question에서 자동 추출하지 않는다. 자료/텍스트/claims/modules는 기존 연구-v1/v2 bounded Canvas와 같은 한도(5자료·12claims·요약/비교/타임라인/근거·최대4모듈·정확 인용·open_evidence 액션)로 검증한다. 기존 공개 계약의 field/type/UUID/날짜/수치 검증을 재사용한다.
- 공개 DTO는 슬러그·공개 ID/버전·표제·설명·as_of·발행시각·내용 hash·공개 Canvas·출처표시만 포함한다. 내부 workspace/run/document/version/representation/raw/citation/claim/draft/module/revision ID는 공개 namespace의 별도 UUID4로 매핑하고 titles/action/reference도 일관되게 매핑해 원래 ID를 내보내지 않는다. 공개 workspace/run ID도 공개 namespace용이며 실제 접근 맥락이 아니다. source_id는 공개 문서 ID로 대체하고 parser 메타데이터를 공개 복사본으로 명확히 구분한다. 원문의 text/pages/tables/selector/인용과 수집시각은 변경하지 않는다. 내부 reviewer·검토 계획·원래 Canvas ID/질문/토큰/예산은 응답에 포함하지 않는다. 자유 텍스트의 공개 적합성은 전체 hash에 대한 명시 내용 검토로 확인하며 자동 PII 제거/사실 검증을 주장하지 않는다.
- 발행은 CLI/신뢰 서버 저장 API만 사용한다. 검증된 전체 계획(model_dump(mode=json), 기본값 명시·UTC 정규화)의 canonical JSON SHA256를 별도 --reviewed-sha256 값으로 확인하며 값이 다르면 쓰지 않는다. 같은 slug/version/plan의 반복은 동일한 공개 데이터/시각/hash를 반환한다. 다른 내용의 덮어쓰기·버전 건너뛰기·동시 발행 경쟁·철회 후 같은 버전 재활성화는 거부한다. 새 버전은 이전 행/인용을 변경하지 않는다. 최신은 max version이며 최신 철회 뒤 옛 버전을 자동 최신으로 되살리지 않는다.
- PostgreSQL0007_public_briefings의 독립 테이블에 공개 payload/hash·비공개 plan hash/검토 기록·발행/철회 시각을 저장한다. 기존 자료/실행/세션 행과 schema0006 정책을 변경하지 않는다. 앱 import/startup은 DB연결·migration·자동 발행을 하지 않는다. CLI는 기존 private-file/URL/로그 실패 처리 원칙을 재사용하고 계획 본문/키/개인정보를 오류에 노출하지 않는다. 새 DDL은 명시 소유자 migration, 앱 역할에는 최소 DML만 부여한다.
- 익명 GET /api/v1/briefings(최신 공개20개 이하), /api/v1/briefings/{slug}, /api/v1/briefings/{slug}/versions/{version}를 제공한다. 응답 no-store·X-Request-ID·검증된 JSON. 미설정503, 없음/철회404, 잘못된 입력422는 입력/계획/비공개 값 없이 반환한다. 읽기·원문 열기·재열람은 모델/DBOS/세션/예산을 호출·생성하지 않는다. 공개 GET은 private repo를 조회하지 않는다. private endpoint는 계속401/403으로 보호한다.
- 웹은 질문 입력 아래 실제 게시된 브리핑만 단정한 목록으로 보여 준다. 허위 인기/최신/추천·가상 게시물·준비 중 체크포인트를 만들지 않는다. 목록이 없으면 영역을 생략하고 진짜 요청 실패는 조용한 재시도 가능한 상태로 구분한다. /briefings/:slug와 /briefings/:slug/versions/:version을 비회원 읽기 경로로 연결하고 제목·기준시각·출처 표시·기존 CanvasView의 30초 요약/접기와 정확 인용 drawer를 제공한다. 개별 버전 링크는 해당 시점 결과를 보존하고 더 새 버전이 있을 때만 최신판 링크를 표시한다.
- 공개 인용을 누를 때 같은 공개 버전 GET으로 현재 게시 상태와 불변 hash를 재검증한 뒤 승인된 공개 원문만 연다. 철회404는 브리핑/열린 원문을 지우고 읽을 수 없음을 안내한다. 이전 slug/버전의 늦은 응답·닫힌 drawer가 새 화면을 되살리지 않는다. 일시 네트워크 오류/503은 철회로 단정하지 않는다. 페이지 재진입/브라우저 focus/visible 복귀에서도 현재 게시 상태를 재확인하며 철회 전 브라우저가 이미 받은 데이터를 원격 삭제할 수 있다고 주장하지 않는다.
- 공개 읽기에서 후속 질문은 공개 표제/이용자가 직접 쓴 질문만 일반 홈 질문 입력으로 전달한다. public/private run ID를 parent로 전달하거나 공개 원문을 private 권한 우회로 이용하지 않는다. guest draft→로그인→명시 생성과 헤더 아이콘·다크모드·키보드/초점·44px·모바일을 유지한다. 읽기 위해 로그인하라는 문구는 삽입하지 않는다.
- 기존 문서의 완료 작업을 현재 미완료로 중복 두지 않는다. 공개 게시 원본은 명시 권리/내용 검토한1건부터 시작하며 다른 검증 자료/옛 저장 실행은 공개하지 않는다. 제한된 첫 게시를 전체 B2C 품질·정기 수집/외부 탐색·최신 이슈·알림/추천/공유 완료로 표시하지 않는다. main/운영 병합은 유예하고 개인 개발 도메인 적용만 한다. 키·실제 계정·개별 private UUID/원문은 공개 Git/PR/Sites에 넣지 않는다.

## Task 1: 명시 게시·철회 저장과 공개 읽기 API

- [x] 도메인 게시 계획/공개 요약·상세·출처 계약과 순수 검증/공개 ID 변환을 구현한다. 불변 근거·현재 bounded Canvas·정확 인용을 재사용하고 public payload에 original IDs/운영 검토자/민감 필드를 싣지 않는다. Python 저장/API가 같은 한도를 검증하고 TS가 사용할 명확한 public shape를 제공한다.
- [x] migration0007_public_briefings와 독립 저장소를 구현한다. slug 단위 실제 PostgreSQL transaction/lock·순차 version/CAS·idempotency·payload hash/행 참조 재검증·철회를 처리하고 private 데이터/현재 세션을 바꾸지 않는다. 최신 철회 뒤 과거 버전의 자동 부활을 막는다. 과거 특정 버전은 자기 철회 전까지 불변으로 읽는다.
- [x] 게시 CLI의 offline validate(정확 계획 hash)/check/apply/withdraw 경로를 구현하고 실제 URL/비밀 파일·logging·에러를 안전하게 처리한다. 전체 검토 hash 명시 없이는 발행하지 않는다. 권리/시간/누락·다른 본문 hash/잘못된 출처·추가 근거·섞인 버전·위조 공개 입력을 거부한다. 브라우저 발행/자동 게시를 만들지 않는다.
- [x] create_app의 선택적인 public repository와 익명 공개 GET3개를 연결한다. 잘못된 입력의 echo가 없는422·없음/철회404·미설정503·no-store·X-Request-ID와 기존 보호401·모델0/세션0/기존 저장 무변경을 검증한다. DB/서버 실행 진입은 명시 주입만 허용한다. 생성 OpenAPI와 schema.d.ts를 갱신한다. 수동 TS transport/web는 Task2가 맡는다.
- [x] TDD와 실제 전용 PostgreSQL: plan/권리/hash/정확 인용/namespace격리·공개 조회private0·새버전/옛버전·같은/다른 동시 발행·철회 경쟁/재활성 거부·corrupt payload와latest운영무결성·anonymous GET/금지쓰기·보호API401·출력에private ID0. 기존 의미 있는 보안·DBOS·세션 회귀를 유지한다. 공용 실제 DB는 테스트 fixture로 사용하지 않는다. 변경 관련 Python lint/types/tests·contract 생성 후 커밋/보고한다. 실제 서버·게시 데이터·Sites는 수정하지 않는다.

## Task 2: 공개 브리핑의 발견·읽기·인용과 질문 연결

- [ ] strict public TS transport/validation/type export를 구현한다. 기존 Canvas/evidence 안전 검증을 재사용/공유하되 private research의 검증을 약화하지 않는다. 같은 slug/version/public IDs/출처/본문/인용/hash와bounded shape를 검증하며 malformed/시간초과/abort/no-store를 구분한다. generated 파일은 Task1 산출물을 소비한다.
- [ ] 홈 질문 아래 실제 게시 목록과 공개 브리핑 라우트를 연결한다. 질문 입력은 기본 진입점이며 empty는 생략·실패는 재시도 가능하다. public route는 세션 조회 완료에 종속하지 않는다. 기존 CanvasView·원문 읽기 UI를 재사용하고 source attribution/license/as_of·개별 버전/최신판 링크를 정확히 보여 준다. 새 임시 진단/ID/관리 메뉴·과장된 인기/최신/가짜 데이터/카드 대시보드는 만들지 않는다. 절제된 편집형 세로 읽기·현행 브랜드/테마·390/1440·44px/키보드·접기/원문 초점 복원을 유지한다.
- [ ] citation click/다시 진입/focus/visibility에서 같은 공개 버전의 현재 상태를 재조회한다.404는 화면/원문 정리, 일시 오류는 복구 가능, 늦은 구 버전 응답/닫기 경쟁은 무시한다. 페이지 비동기 요청을 취소하고 stale content를 새 slug로 보여주지 않는다.
- [ ] 공개 브리핑에서 질문 입력을 일반 홈 draft로 연결한다. guest는 로그인에서 질문 복원 후 직접 실행하며 member는 질문을 편집한 뒤 명시 제출한다. private/public parent run을 섞지 않는다. 공개 읽기·새로고침·원문은 유료 요청을 만들지 않는다. 기존 Google login/세션/초안/기록/권한/생성/취소를 보존한다.
- [ ] meaningful TDD: public guest list→read→exact citation→back/focus·stable v1/new v2·404withdrawal cleanup·malformed/crossref·networkretry·route races·question draft/login/noautoPOST·private401. 이전 검사 광범위 삭제 없이 관련 검사를 보강하고 UI cosmetic absence만 새 테스트로 만들지 않는다. JS lint/types/tests/build/contract 후 커밋/보고한다.
- [ ] README/AGENTS·R1/R2/R4·D020·계획/작업/진행·개발 실행 문서를 현재 공개/비공개 계약으로 정리한다. 질문 전용 작업은 완료로 이동하고 기록은 보존한다. 외부 수집/전체 상품 품질/개인화는 후속이며 public source조건과 운영 게시 유예를 명시한다. 실제 데이터 등록·dev rollout·Sites는 controller가 검증 뒤 수행한다.

## 최종 검증과 개발 반영

컨트롤러가 실제 PG 전체 검사와 독립 API/브라우저·390/1440/다크모드·public0모델/세션·private권한 경계를 검증하고 전체 변경을 백지 컨텍스트로 검토한다. 기존 공공누리1유형 공식 자료의 전체 공개 계획/표시/인용/근거 부족 표현을 검토해1건만 개인 개발 public table에 명시 게시한다. 실제 비공개 질문/기록을 발행하지 않는다. 기존 실제 앱 자료/인증/실행을 보존하는 사전 백업·명시 migration/최소 권한·반복검증과 별도 전용 DB 복원을 확인하고 웹/API를 같은 개발 도메인에 반영한다. 새 유료 모델 호출은 불필요하면 하지 않는다. 이전 실행 worker는 바꾸지 않는 한 강제 재시작하지 않는다. PR·문서·Sites를 갱신하되 main/운영은 병합하지 않고 사용자의 탭은 열지 않는다.
