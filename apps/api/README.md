# API 앱

Python 3.13.12·FastAPI 0.143.0 API입니다. 기본 `issuedigest_api.main:app`은 환경·DB·네트워크에 연결하지 않습니다. Google OAuth와 보호 자료 조회는 서버에서 명시적으로 구성한 runtime에서 제공합니다. 실제 Google 앱 등록·비밀 설정·계정 승인과 운영 접속 확인은 별도 준비입니다.

저장소 루트에서 uv 0.11.4로 실행합니다.

```sh
uv sync --locked --all-packages
npm run dev:api
# 기본 앱의 직접 실행
uv run --package issuedigest-api uvicorn issuedigest_api.main:app --no-access-log --reload --host 127.0.0.1 --port 8000
```

## 명시 구성 runtime

비밀값은 저장소 밖의 서버 환경에 제공하며 파일·Google 기본 자격 증명을 자동 탐색하지 않습니다. 다음 네 환경 변수가 모두 필요합니다.

| 환경 변수 | 의미 |
| --- | --- |
| `ISSUEDIGEST_DATABASE_URL` | 명시적인 `postgresql+psycopg` 앱 권한 연결 |
| `ISSUEDIGEST_PUBLIC_ORIGIN` | 정확한 HTTPS origin, 경로·후행 `/` 없음; HTTPS localhost 허용 |
| `ISSUEDIGEST_GOOGLE_CLIENT_ID` | 등록한 Google 웹 앱 client ID |
| `ISSUEDIGEST_GOOGLE_CLIENT_SECRET` | 해당 앱의 서버 전용 secret |

```sh
# 위 환경 변수를 안전하게 주입한 후에만 실행
ISSUEDIGEST_CONFIGURED_RUNTIME=1 npm run dev:api
# 또는 직접 실행
uv run --package issuedigest-api uvicorn issuedigest_api.runtime:create_configured_app --factory --no-access-log --host 127.0.0.1 --port 8000
```

`npm run dev`에도 같은 opt-in이 적용됩니다. opt-in이 없으면 기본 상태 앱을 계속 실행합니다. reload를 포함한 자식 프로세스는 함께 종료합니다. 구성 오류는 DB 접속 전에 검증하고 값 없는 고정 오류로 시작을 거부합니다. runtime은 자신이 만든 engine을 실패·종료 시 dispose하며 스키마를 자동 생성하거나 마이그레이션하지 않습니다. storage README의 명시 마이그레이션을 먼저 수행하고 runtime에는 스키마 변경 계정을 사용하지 않습니다.

Google Console에 개발·운영 웹 앱의 승인 origin과 callback을 각각 등록해야 합니다. callback은 정확히 `ISSUEDIGEST_PUBLIC_ORIGIN` + `/api/v1/auth/google/callback`입니다. HTTPS와 같은 origin에서 웹과 API에 접근하도록 준비하며 localhost HTTP에는 보안 cookie를 완화하지 않습니다. 등록한 이메일 초대는 개인 DB의 trusted operator 경계에서만 생성합니다. 공개 가입·비밀번호 로그인·멤버십 변경 API는 없습니다.

## HTTP 계약

| 요청 | 성공 |
| --- | --- |
| `GET /health/live` | `Liveness` 200 |
| `GET /api/v1/status` | `ServiceStatus` 200 |
| `POST /api/v1/auth/google/start` | 고정 Google authorize 주소로 303; 600초 flow cookie |
| `GET /api/v1/auth/google/callback` | 검증·권한 확인 후 `/`로 303; 실패는 고정 `/login?error=denied\|invalid\|unavailable` |
| `GET /api/v1/auth/session` | `SessionInfo` 200; provider subject·email·token 없음 |
| `POST /api/v1/auth/logout` | 세션 폐기 후 204·cookie 삭제 |
| `GET /api/v1/workspaces/{workspace_id}/evidence?limit=20` | `EvidenceCatalog` 200; 정수 1~50, 비회원 404 |
| `GET /api/v1/workspaces/{workspace_id}/evidence/{snapshot_id}` | 기존 불변 `EvidenceBundle` 200 |
| `POST /api/v1/workspaces/{workspace_id}/evidence/search` | 현재 멤버십의 문자 일치 `EvidenceSearchResult` 200 |

검색 요청은 세션 쿠키와 설정된 공개 origin의 `Origin` 헤더를 사용합니다. `Sec-Fetch-Site`가 있으면 `same-origin`이어야 합니다. JSON 본문 예시는 `{"terms":["등록금","2026"],"limit":10}`이며 모든 단어가 원문 검색 단위에 문자 그대로 포함되어야 합니다. `provider`, `source_id`, `source_kind`, UTC `collected_from`/`collected_to` 필터도 지원합니다. URL query string은 허용하지 않으며 UTF-8 JSON 본문은 최대 16,384바이트입니다. 잘못된 JSON·중복 키·필드·한도·미디어 형식은 내용이 고정된 422, Origin 거부는 403입니다.

검색은 현재 세션과 작업 공간 멤버십을 저장소에서 매번 확인합니다. 비회원은 404, 만료·폐기된 세션은 401, 서비스/저장 오류는 503입니다. 결과의 `coverage.missing_snapshots`는 아직 검색 투영이 없는 자료 수이며, `truncated`와 `scanned_candidates`는 후보·결과 한도 해석에 사용합니다. 빈 결과나 미색인은 근거 부재 판정이 아닙니다. API 요청은 투영 재구축, 원문 수집, AI 호출을 수행하지 않습니다. 원문 위치와 quote는 문자 검색 결과이며 주장 지지 판정은 `not_evaluated`입니다.

start/logout은 설정 origin과 정확히 일치하는 Origin 헤더가 필요하며 Sec-Fetch-Site가 있으면 `same-origin`만 허용합니다. callback은 브라우저에 묶인 state를 한 번 소비한 뒤 PKCE·nonce·서명·issuer·audience·시간을 검증합니다. Google issuer는 고정 canonical HTTPS로 저장합니다. 첫 바인딩은 운영자의 명시 초대와 Gmail 또는 검증된 Google Workspace 이메일에 한정합니다. 이후 등록된 issuer/sub와 활성 멤버십으로 허용하고 이메일 변경으로 권한을 바꾸지 않습니다. 실패한 callback은 기존 세션을 유지하며 모든 callback 응답은 flow cookie 삭제와 `Referrer-Policy: no-referrer`를 적용합니다.

인증은 `__Host-issuedigest_session` cookie 하나만 받습니다. 세션과 flow cookie는 Secure·HttpOnly·SameSite=Lax·Path=/·Domain 없음입니다. 세션은 hash만 저장하고 절대 최대 8시간·idle 30분을 적용합니다. Google ID/access/refresh token은 DB·브라우저 저장소에 저장하지 않습니다. 요청 이메일·subject·권한·외부 redirect를 신뢰하지 않습니다. 유효 cookie 없이 401, 미구성/DB 장애는 고정 503, 잘못된 UUID4/limit은 입력 값을 포함하지 않는 422입니다. 보호 응답은 `Cache-Control: no-store`와 새 UUID4 `X-Request-ID`를 포함합니다. 인증 경로의 자동 slash redirect는 callback query가 반사되지 않도록 고정 404로 처리합니다.

Google HTTP는 고정 endpoint, TLS 검증, 환경 proxy 무시, redirect 금지와 각 동작 5초/전체 교환 15초 제한을 사용합니다. decoded 응답 64KiB와 ID token 16KiB를 제한하고 strict JSON/중복 key/JWT 형식을 확인합니다. 고정 인증서를 비동기로 받은 뒤 inline transport로 google-auth SDK에 전달하여 추가 네트워크 호출을 허용하지 않습니다. scope는 `openid email`이며 메일·Drive·profile·avatar·유료 API를 요청하지 않습니다. 의존성은 [httpx2 2.13.1](https://pypi.org/project/httpx2/2.13.1/), [google-auth 2.62.0](https://pypi.org/project/google-auth/2.62.0/), [cryptography 50.0.2](https://pypi.org/project/cryptography/50.0.2/)로 고정합니다.

상태 응답은 프로세스가 응답한다는 뜻이며 DB·Google·작업 엔진 준비 완료를 뜻하지 않습니다. 개발 실행과 안내는 `--no-access-log`를 사용합니다. Vite의 `/api` proxy 실패 로그도 URL·callback query·error stack/object 대신 고정 메시지만 남기며 다른 빌드·경고·health 진단은 유지합니다. 지원하는 `npm run dev`/`dev:api`/`dev:web`와 웹 workspace의 `npm run dev`는 query를 직접 기록하는 `vite:proxy`·`vite:time` DEBUG namespace만 자식 환경에서 제외하며 다른 namespace는 보존합니다. 임의의 직접 Vite 실행이나 운영자의 별도 설정은 이 실행 경로의 보장 밖입니다. 기존 운영 프록시/Nginx 로그 설정은 변경하지 않았으며 공개 OAuth 전에 callback query·cookie가 기록되지 않는지 별도 확인해야 합니다.

## 검증과 계약

```sh
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run pytest
npm run contract:generate
npm run contract:check
```

FastAPI·실제 소유 loopback PostgreSQL 테스트 DB·합성 RSA 서명·MockTransport로 start→callback→session→catalog→근거→logout을 확인합니다. 실제 외부 Google 로그인이나 사용자 계정의 준비 완료를 뜻하지 않습니다. 테스트 DB 연결과 보호 장치는 storage README를 따릅니다. OpenAPI/TS는 실제 domain 모델로 생성하며 기존 Evidence/Canvas/Research/Execution 계약과 인용 의미를 유지합니다. `/docs`와 `/openapi.json`의 운영 공개 정책은 별도 배포 단계에서 정합니다.

서버 코드의 `create_app(access_repository=None, *, auth_service=None, workspace_repository=None)`은 내부 DI만 받습니다. AuthService가 검증된 identity를 초대 저장소에 전달하고 승인된 세션을 발급합니다. default import/startup에는 외부 접속이 없습니다.

## 첫 실제 조사 API

명시적 `create_configured_app()`만 PostgreSQL 연구 저장소를 연결합니다. `ISSUEDIGEST_RESEARCH_ENABLED=1`을 설정해야 새 질문 POST가 예약되며, 기본값은 비활성입니다. 이 값은 모델 키·작업자가 준비된 뒤에만 켭니다. 비활성일 때 자료 목록과 저장된 조사 GET은 열리고 새 질문은 고정된 `503 Research model unavailable`을 반환합니다. API 프로세스는 모델을 호출하거나 마이그레이션하지 않습니다.

보호 경로는 `/api/v1/workspaces/{workspace_id}/research/sources`, `/research` GET·POST, `/research/{run_id}` GET, `/research/{run_id}/cancel` POST입니다. 세션 쿠키와 현재 membership을 다시 확인합니다. owner/editor만 생성·취소할 수 있습니다. POST는 same-origin, `application/json`, 최대 16 KiB, 중복 키 금지를 적용합니다. 취소 본문은 `{}`입니다. 모델 입력·결과는 URL/로그에 남기지 않으며 모든 조사 응답은 `no-store`입니다. 현재 API의 고정 오류는 401 인증, 403 출처·역할, 404 비회원·다른 공간, 409 멱등성·동시 실행, 422 입력, 429 월 예산, 503 저장소·모델 준비를 구분합니다.
