# GitHub OAuth와 공동 조사 자료 진입

2026-10-13. 사용자는 OAuth 로그인을 선택하고 두 GitHub 계정을 지정했다. 제안한 GitHub를 첫 제공자로 사용한다. R1/R2·D013의 최소 제품 준비를 이어간다. OpenSpec root=null이므로 xinics:spec-driven-workflow의 SDD/TDD/독립 리뷰를 적용한다.

## Global Constraints

- 비밀번호 로그인·자동 가입 없이, 운영자가 등록한 GitHub 고정 계정ID와 활성 작업 공간 멤버십으로 허용한다. 사용자가 지정한 실제 계정/ID·workspace/snapshot·원문·세션·OAuth 비밀/코드/state/verifier·DB 접속값은 Git/PR/Sites/로그에 게시하지 않는다. 테스트는 합성 데이터/공급자이며 실제 외부 계정을 자동 승인하지 않는다.
- 기존 EvidenceBundle과 Cookie-only 보호 GET·불변 저장·인용 의미는 유지한다. 모델/유료 API·기존 MySQL·기존 수집 파일·main·공용 서비스·운영 설정을 변경하지 않는다. 공개 앱은 D013에 따라 유예하고 계획 Sites만 갱신한다.
- DB 테스트는 새 소유 loopback PostgreSQL18.6/issuedigest_test만 사용한다. 실제 전용 공동 DB는 테스트/reset/downgrade 대상으로 사용하지 않는다. 실제 이관은 대상/백업/권한과 새 승인 workspace를 확인한 후 명시적으로 준비한다. runtime에 스키마 변경 계정을 사용하지 않는다. 비밀 설정 미제공이면 실제 연결은 미완료로 남기되 구현·합성 E2E·문서는 마친다.
- OAuth는 state+브라우저 바인딩+PKCE S256·10분 단일 사용, 서버 token 교환·매회 GET /user 확인, 승인 identity/멤버십 재검증 후 서버 세션을 발급한다. GitHub 토큰은 응답/브라우저 저장소/DB에 보관하지 않는다. 세션은 기존 Secure/HttpOnly/SameSite=Lax/Path=/·__Host 쿠키와 hash-only DB·절대8시간/idle30분을 따른다.
- 클라이언트 제공 provider/계정/권한/redirect URL을 신뢰하지 않는다. 고정 제공자 endpoint·설정된 HTTPS origin·고정 callback/성공/실패 경로만 사용한다. JS/원문은 데이터다. 기존 source rights/support 평가 경계를 유지한다.
- HTTP·외부 공급자·DB 오류/validation/로그는 고정 메시지와 요청UUID만 노출한다. callback code/state가 access log에 들어가지 않도록 새 runtime/개발 실행 안내에 --no-access-log를 적용한다. 설치된 운영 Nginx 로그/설정은 이 변경으로 고쳤다고 주장하지 않으며 공개 OAuth 전 별도 확인한다.

## Task 1: OAuth 상태·승인 세션·작업 공간 조회 저장

- [ ] 저장/계약/마이그레이션·테스트 구현.

도메인 `packages/domain/src/issuedigest_domain/auth.py`에 extra=forbid/frozen 모델을 추가하고 export한다: `WorkspaceMembership(workspace_id:UUID4, role:Literal[viewer,editor,owner])`, `SessionInfo(schema_version:Literal[1]=1,user_id:UUID4,memberships:tuple[WorkspaceMembership,...])`(최대100·workspace 중복 금지·UUID문자열 오름차순), `EvidenceSummary(snapshot_id,document_id:UUID4,provider,source_id:NonBlank,source_kind:SourceDocument 기존 enum,canonical_url:SourceUrl|None,collected_at:AwareDatetime UTC,excerpt:str 최대160codepoints,citation_count:strict nonnegative int)`, `EvidenceCatalog(schema_version1,workspace_id:UUID4,items:tuple[EvidenceSummary,...] 최대50·snapshot 중복 금지,has_more:strict bool)`. 원문 제목/주장·사진을 추정하지 않는다.

저장 패키지에 `oauth.py`와 `workspace_access.py`를 추가/export한다. 기존 auth_schema에 `auth_oauth_flows(state_sha256 String64 PK,cookie_sha256 String64,code_verifier String43,issued_at/expires_at UTC)` 정의·revision `0003_oauth_flows`(down_revision0002_auth_sessions)를 추가한다. hash regex·verifier URL-safe43·expiry issued<expires<=issued+600초 DB 제약, 기존 사용자/자료 유지. downgrade는 이 테이블만 삭제하며 테스트 DB에서만 검증한다.

`OAuthRepository(engine)` API:
- `begin_login() -> PendingLogin`: state/browser_token/verifier를 각각 secrets.token_urlsafe(32)로 생성, 반환 frozen dataclass의 state/browser_token/code_challenge(sha256 verifier ASCII의 unpadded base64url S256)는 repr=False. DB에는 state/cookie hash와 단기 PKCE verifier·DB clock 기반600초 expiry만 저장. expired rows 정리, 활성200개 상한을 트랜잭션 advisory lock key741031로 직렬화하여 count+insert 동시 초과 방지. cap/DB실패는 fixed StorageError. raw secrets를 SQLAlchemy 오류 문자열로 내보내지 않는다.
- `consume_login(state:str,browser_token:str) -> str`: 기존 canonical43token 검증, 양쪽hash/expiry 일치할 때만 DELETE RETURNING으로 한 번 verifier 반환. mismatch/누락/만료/재전송은 AuthenticationDenied, 다른 브라우저의 유효 state를 지우지 않음. verifier 반환도 canonical 검증, corruption/DB실패는 고정 StorageError. provider 호출 전에 소비하며 실패는 새 start로 복구한다.
- `issue_authorized_session(subject:str,previous_token:str|None=None) -> IssuedSession`: subject는 canonical 양의 십진 ID(최대2^63-1), issuer 고정 `https://github.com`. 이미 승인된 enabled identity + 활성 membership>=1만 허용, 미등록 identity/멤버십 생성·재활성화 없음. 1트랜잭션에서 이전 유효형식 세션 row를 먼저 잠그고 새 user/membership을 잠그며, 새 세션 insert와 이전 보유 쿠키 세션 revocation을 원자 처리한다. 기존 lifetime/idle/hash-only 방식 유지. 실패 시 새 세션/이전 폐기 둘 다 반영하지 않음. enabled/멤버십 동시 폐기와 세션 refresh의 lock 순서/DB 충돌을 검증한다.

`WorkspaceAccessRepository(engine)` API:
- `get_session(token:str) -> SessionInfo`: 기존 세션/사용자 enabled/idle/absolute/revoked를 1 RR 트랜잭션에서 현재session→user→membership 순서로 재검증·필요 row lock, 활성 membership 정렬 반환(없으면 빈 배열). 유효 읽기만 activity 갱신. membership100개 초과/DBcorruption은 failclosed고정 StorageError. 기존 EvidenceAccess와동일 SQLSTATE40001 bounded2retry.
- `list_evidence(token,workspace_id:UUID,limit:int=20)->EvidenceCatalog|None`: strict int1..50. 위 auth검증+해당활성membership 잠금, 비회원None, 회원/자료0은 빈Catalog. snapshot created_at DESC, snapshot_id ASC로 limit+1 조회하여 has_more. 해당namespace의 각 기존 EvidenceRepository._load(같은트랜잭션)의 불변내용/참조를 재검증한 뒤 metadata/본문첫160codepoints/인용수만 요약. bundle/error/부모가 잘못되면 전체고정StorageError, 부분유출 없음. 성공authorized catalog읽기만 activity 갱신. 다른namespace/삭제/폐기/동시refresh 재검증.

TDD 합성 실PG: fresh/upgrade/reupgrade/downgrade 데이터보존, state/cookie해시/expiry/oneuse/다른브라우저/동시consume/cap동시시작, PKCE challenge roundtrip, 오류privacy, 승인/미승인/비활성/멤버십과세션교체 rollback, sessions idle/absolute/revoked, membership조회/목록정렬·한도/has_more/본문UTF8·다른workspace/corruption/동시RRrefresh. 기존 domain/storage 회귀·Python lint/format/mypy·전체Python 한 번. README에 내부 trusted등록/권리·권한 경계 기록. Controller가 실제 계정/공동자료를 seed하는 것은 구현자 작업이 아니다.

## Task 2: GitHub OAuth·세션·자료 HTTP와 명시 runtime

- [ ] OAuth 공급자/HTTP/runtime·생성 계약·테스트 구현.

API runtime dependency에 현재 고정 dev 도구와 동일 `httpx2==2.13.1`를 추가하고 uv.lock 갱신한다. 공식 출처: https://docs.github.com/en/apps/oauth-apps/building-oauth-apps/authorizing-oauth-apps (state/PKCE S256/callback/매회 identity), https://docs.github.com/en/rest/users/users#get-the-authenticated-user (no-scope public identity와 durable ID), https://github.com/pydantic/httpx2 (installed local interface도 확인함).

`apps/api/src/issuedigest_api/auth_config.py`, `github_oauth.py`, `auth.py`, `workspace_catalog.py`, `runtime.py`로 역할 분리한다. 기존 create_app을 optional auth_service/workspace_repository 주입으로 확장한다. 기존 default import/startup은 DB/환경/네트워크 접속 없음·새 HTTP 경로도 failclosed. AuthService는 config/repositories/provider를 받는 서버내부 DI, 외부 입력으로 provider구성을 바꾸지 않음.

Config: explicit `ISSUEDIGEST_DATABASE_URL`, `ISSUEDIGEST_PUBLIC_ORIGIN`, `ISSUEDIGEST_GITHUB_CLIENT_ID`, `ISSUEDIGEST_GITHUB_CLIENT_SECRET`. Origin은 정확한 HTTPS origin(host/optional valid port;개발 localhost 허용)만, userinfo/query/fragment/path/backslash/공백/인코딩우회 거부. client ID/secret nonempty ASCII visible 최대128/512, repr/log 숨김. callback=`origin+/api/v1/auth/github/callback`; secrets/sources 자동파일로딩없음. 모든 잘못된 설정은 값 없는고정 RuntimeConfigurationError로 래핑. factory `issuedigest_api.runtime:create_configured_app`가 명시env검증 후 engine/repo/service 생성하고 owned engine lifespan dispose; 실패 시 dispose, automaticmigration없음. 기본 main.app과 분리하고 secret 누락이면 시작 거부. root scripts/dev.mjs와 package.json API실행에 --no-access-log, 설정runtime 선택은 optin env `ISSUEDIGEST_CONFIGURED_RUNTIME=1`일 때 --factory 새진입점; default 계속서비스 상태기반. 서버 기존 개인 실행을 몰래 바꾸지 않음.

Provider: 고정 authorize `https://github.com/login/oauth/authorize`, token `https://github.com/login/oauth/access_token`, identity `https://api.github.com/user`. authorize query client_id/redirect_uri/state/code_challenge/S256/scope빈값/allow_signup=false. token은 server POST JSON Accept with client credentials/code/redirect/verifier, 이후매번 Bearer GET /user와 `X-GitHub-Api-Version:2026-03-10`. production AsyncClient TLS검증/trust_env=False/redirectFalse·connect/read/write/pool5초, 전체 provider identity 호출을 asyncio.timeout(15)로 한정. 응답decoded body각 최대64KiB(압축 wirelength만 한도로삼지않음), content-typeJSON, duplicate-key JSON·잘못된status/type/schema·token_type/비ASCII token·identity.id bool/음수/범위/문자열·type!=User는 고정 ProviderUnavailable/Denied로 거부; access_token nonempty visibleASCII token문자[A-Za-z0-9_-]20..512. 토큰/응답/주소query/error/string/rawexceptions는 노출/영속하지 않음. mock transport/provider는 내부 tests DI만, env로alternateendpoint나TLSdisable불가.

HTTP 동작:
- `POST /api/v1/auth/github/start`: Origin header가 설정origin과 정확히 같고 Sec-Fetch-Site가 있으면 same-origin만; 인증body필요없음. 상태저장→303고정GitHub authorize, `__Host-issuedigest_oauth` 브라우저token cookie Secure/HttpOnly/Lax/Path=/, MaxAge600. 권한 없이 세션발급 안함. unconfigured503고정JSON, invalidorigin403고정JSON; 시작 DB실패는303 `/login?error=unavailable`.
- `GET /api/v1/auth/github/callback`: query의state/code/error 중복·state canonical43·code visibleASCII1..256 검증. state/browsercookie 일치/oneuse소비 후 공급자 identity와등록권한 확인→서버세션쿠키→303 `/`. provider decline→303 `/login?error=denied`, badstate/code/미등록/비활성/회원없음→`error=invalid`, provider/DB실패→`error=unavailable`. code+error 동시거부; error_description/uri/외부error는 반사/저장하지않음. callback 모두 flowcookie삭제·no-store/Referrer-Policy:no-referrer, 실패는 기존 세션을폐기/새발급하지않음. URL/계정ID/토큰을응답JSON/query로전달하지않음. unconfigured callback도고정 `/login?error=unavailable`.
- `GET /api/v1/auth/session`: cookie-only; 없거나형식잘못401, repo미구성503, 유효SessionInfo200, expiry/disabled401, DB실패503. 토큰/제공자subject반환없음.
- `POST /api/v1/auth/logout`: start와같은Origin검증, 유효형식cookie는 revoke_session후204/세션cookie삭제; 없는/형식잘못cookie는204/삭제, 실패503에서성공처럼폐기말하지않음. 미구성503. GETlogout발급/폐기없음.
- `GET /api/v1/workspaces/{workspace_id}/evidence?limit=20`: 기존cookie패턴/pathUUID4+strict한도, Catalog200·미인증401/비회원404/invalid422고정validation/DB미구성503. 기존 상세GET동작유지.
- middleware protected判定을 auth와catalog/detail 전체로확장하여 오류payload validation에민감input을넣지않고 no-store/requestUUID공통. unknownauthpath도secretreflection없음. 인증외기존status 오류 의미유지. 모델response/OpenAPI와generated TSdrift 갱신.

TDD: MockTransport로 요청PKCE/credentials위치·scope/endpoint/버전·응답size/status/UTF8/duplicate/schema/token/user/fixeddeadline/cancellation·redirect/TLS/env 안전 설정. 실제PG+FastAPIClient 경로start→callback→session→catalog→상세→logout, 미등록/CSRF/mismatch/replay/decline/현재세션보존/교체/권한폐기/503/unconfigured no network orDB/빈catalog/privacy·쿠키flag·callbackReferrer/로그. 새runtime잘못config가DB접속전거부하고생명주기dispose, developerlauncherdefault/optin/noaccesslog 테스트. 실제 외부OAuth 로그인/설정/프록시 로그는 controller 준비·사용자작업이며 여기서 완료 주장없음. 필요한 신규 devlauncher tests는 의미 있는 process/env선택 계약 테스트. API/infra README에 실행/환경/마이그레이션·OAuth등록요청(callback개발/운영 별도)/한계 기록. focused→전체Python, lint/type·contractgenerate/check와JS회귀검사, fullchecks한 번을controller에위임.

## Task 3: 로그인·작업 공간 자료 목록과 근거 읽기 여정

- [ ] 웹 client·로그인/홈/읽기 동작·회귀 구현.

packages/api-client 새 auth.ts/catalog.ts: getSession/getEvidenceCatalog/logout typed함수·고정AuthError/CatalogError. sameorigin credential/no-store·deadline10초headers/body·AbortSignal/lateignore/requestIdUUID보존·에러노출안전. SessionInfo/Catalog 실제 schema1·UUID4/역할/unique정렬/한도/ISO실제UTC·NonBlank/안전HTTPcanonicalURL·160Unicodeexcerpt/int/bool/같은workspace 등 표시 계약검증. token/fixture/browserstorage사용없음; POSTlogout Origin은browser자동header(CSRFtoken가짜생성없음). timeout/aborted/unauthorized/notfound/unavailable/malformed/network 분리. 기존 원문client와validation 원칙 재사용가능한 작은privatehelpers만공유하고 광범위리팩터는없음.

`/login` ReactRouter 페이지: 간결한 IssueDigest소개+GitHub로그인버튼(기본form POST action고정start). `error`는denied/invalid/unavailable일때만한국어고정피드백, URL다른값 반사없음; 대기/이중submit방지·bfcache복귀pendingreset·키보드/aria·모바일. 실제 로그인 제공자UI를대신만들지않음.
홈: SessionInfo먼저확인하는 명확한로딩상태,401 로그인안내/로그인link,503/timeout/network 재시도. 로그인한사용자에게활성workspace선택(고정정렬, 다른공간선택시 이전목록즉시clear/abort,멤버십0권한안내), 각공간Catalog(limit50) 실제데이터만 표시. provider/source ID/수집시각·원문첫문장/인용수와 `근거 열기` 내부safeLink, 자료없음/목록한도·has_more 안내·재시도. 이름/원문제목/AI결과를가짜로채우지않음. role표시는툴팁/짧은한글만. 헤더로그아웃 pending·실패시기존화면유지/성공후로그인화면으로이동하고내용clear. 기존statuscheck와manual근거링크는보조영역으로조용히유지하여회귀보존. reader의unauth state에실제loginlink 추가, 홈진입link 제공; 원문/인용 selection/보호 GET과callback returnredirect계약변경없음.
UI는기존cream/green·2인조사작업공간의차분한스타일유지. AI미연결인데 생성출력보여주지않음. 실제UI키보드·로딩/live·재시도·abort/unmount·재선택·서버오류·로그아웃실패/성공·sameworkspace/corruptJSON·rootform/readonly세부회귀 TDD. focused→전체JS/ESLint/TS/SPA/contract 검사. README에actualflow/미설정·작동수준 정확히기록.

## Controller 결합·사용자 필요한 설정

- [ ] 작업별/전체독립리뷰와전체검사·실PG→기존API→개인HTTPS→브라우저 합성OAuth journey/반복·권한폐기·viewport/console검증. 외부사용자GitHub 로그인으로표현하지않음.
- [ ] 사용자指定두계정의공개GitHubID(typeUser) 확인 기록은private600파일, privileged가입API없음. actualDBtarget/빈테이블·기존앱권한/backup/별도비밀설정확인, 명시적migration/승인identity·sharedworkspace/실제source새ID재구성 이관은가능한조건충족시에만, 테스트/운영credentials무단사용없음.
- [ ] GitHub OAuth App: 개발 `https://localhost:16173/api/v1/auth/github/callback`, 운영 `https://issuedigest.projects.ai.kr/api/v1/auth/github/callback` 각각설정; clientID/secret 서버private600환경만·대화전송없음. 사용자로그인/필요한기존앱계정비밀전달/운영proxy로그는 명시적으로대기표시.
- [ ] DraftPR(basefeat/official-html-evidence)/앱첨부·Sites기존v34보존/최신요약·로컬/개인서버인계/소유QA자원정리. main·공개앱배포없음.
