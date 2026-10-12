# API 앱

Python 3.13.12·FastAPI 0.143.0의 HTTP 진입점입니다. 응답 모델은 `issuedigest-domain`에서 가져옵니다. PostgreSQL 세션과 멤버십으로 보호하는 근거 조회를 제공합니다. 로그인 공급자·OIDC/JWT 검증·초대·앱 로그인 화면은 아직 연결하지 않았습니다. 기본 앱은 외부 연결 없이 시작하며 자료 접근은 차단합니다.

모든 명령은 저장소 루트에서 실행합니다. uv 0.11.4가 필요합니다.

```sh
uv sync --locked --all-packages
npm run dev:api
# npm 없이 API 직접 실행
uv run --package issuedigest-api uvicorn issuedigest_api.main:app --reload --host 127.0.0.1 --port 8000
```

## 현재 HTTP 계약

| 요청 | 200 JSON |
| --- | --- |
| `GET /health/live` | `{ "status": "ok" }` |
| `GET /api/v1/status` | `{ "service": "issuedigest-api", "api_version": "v1", "status": "ok" }` |
| `GET /api/v1/workspaces/{workspace_id}/evidence/{snapshot_id}` | 기존 검증된 `EvidenceBundle` JSON (세션·멤버십 필요) |

상태는 API 프로세스가 응답한다는 의미이며 DB·워커·작업 엔진 준비 완료를 뜻하지 않습니다. 모든 응답에는 서버가 새로 생성한 UUID v4 `X-Request-ID`가 있습니다. 클라이언트가 제공한 값은 채택하지 않습니다. HTTP 오류와 예기치 않은 서버 오류에도 같은 규칙을 적용하며 서버 예외 상세는 응답에 노출하지 않습니다.

로컬 API 문서는 `/docs`, 원본 OpenAPI는 `/openapi.json`입니다. 계약 변경 시 루트의 `npm run contract:generate`로 버전 관리 파일을 다시 생성합니다. 운영 인증·문서 공개 정책은 실제 배포 기능에서 정합니다.

## 검증

```sh
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run pytest
npm run contract:check
```

테스트는 실제 FastAPI 앱을 사용해 응답·서버 UUID·404·500·OpenAPI 모델을 검증합니다. 현재 Starlette의 TestClient가 지원하는 `httpx2`를 개발 의존성으로 사용합니다. 실행 API는 외부 서비스나 유료 호출을 필요로 하지 않습니다. 키·비밀 설정·공급자 자격 증명은 추후 서버에서만 처리합니다.


원문·인용과 개체·주장·관계·관측·비교 조건의 도메인 전송 모델을 OpenAPI components로 등록합니다. `ResearchBundle`, `ComparisonAssessment`와 의존 모델을 기존 models_json_schema 호출에 함께 등록하며 이름 충돌을 거부합니다. 실제 `/openapi.json`과 export 결과가 일치하고 태그 union 참조가 해석됩니다. 기존 익명 상태 경로 두 개와 보호 근거 GET 한 개만 제공합니다. 연구 자료 생성·공개 저장·공개 세션 발급 경로는 아직 없습니다.


## 서버 구성과 보호 조회

`create_app(access_repository: EvidenceAccessRepository | None = None)`은 서버 코드에서만
저장소를 받습니다. 요청 헤더·쿼리·본문의 사용자/공간 ID나 이메일로 권한을 구성하지 않습니다.
기본 `issuedigest_api.main:app`은 연결을 열지 않으며 유효한 세션 형식의 요청도 503입니다.
로그인 미연결 상태이므로 운영 로그인 기능이 완료된 것으로 사용하면 안 됩니다.

```python
from issuedigest_api.main import create_app
from issuedigest_storage import EvidenceAccessRepository, create_storage_engine

# server_database_url은 서버의 비밀 설정에서 읽습니다. 출력하거나 버전 관리하지 않습니다.
# 기존 환경의 마이그레이션은 명시적으로 별도 적용합니다.
engine = create_storage_engine(server_database_url)
app = create_app(EvidenceAccessRepository(engine))
# engine 수명 및 종료 시 dispose는 이 서버 구성 코드가 관리합니다.
```

경로 ID는 UUID4입니다. 인증 전달 채널은 `__Host-issuedigest_session` Cookie 하나이며
Bearer·사용자 헤더·쿼리·경로 토큰을 인증 증거로 사용하지 않습니다. Cookie 없음/형식 오류는
DB 연결 없이 401, 미구성 backend는 503, 모르는/만료/폐기/비활성 세션은 401입니다.
미가입 공간·다른 공간의 스냅샷·없는 스냅샷은 같은 404를 반환합니다. DB 장애/자료 훼손은
고정 503이며 원문·토큰·예외 상세를 반환하지 않습니다. UUID 경로 오류는 422이며 입력 원문과
예외 context는 반영하지 않습니다. 보호 조회의 모든 응답에 `Cache-Control: no-store`와
서버 UUID `X-Request-ID`를 설정합니다. 성공 JSON은 기존 workspace·내용·인용 순서를 보존합니다.

OpenAPI는 cookie apiKey security를 이 보호 경로에만 선언하고 기존 canonical
`EvidenceBundle` component를 참조합니다. HTTP 출력도 동일 모델로 검증합니다.
component 이름 충돌 거부와 기존 Evidence/Canvas 계약은 유지합니다. 생성 OpenAPI/TS는
`npm run contract:generate`로 생성하며 실제 HTTP/export 일치와 TS 경로 소비를 검사합니다.

## 향후 로그인 callback의 내부 경계

저장소의 `IdentityRepository`/`SessionRepository`는 이미 검증된 외부 identity와 이미 승인된
멤버십을 다루는 신뢰된 공급자 연결기/관리자 코드 전용입니다. 이 메서드는 OIDC 토큰 검증이나
초대 승인을 수행하지 않습니다. 공개 발급·등록·멤버십 수정·개발 로그인 경로는 없습니다.
세션 절대 수명은 기본/최대 28,800초이며 내부 발급에서 정수 1~28,800초로 줄일 수 있습니다.
마지막 성공한 허용 조회 후 1,800초 이상 idle이면 거부하며 절대 만료를 연장하지 않습니다.

`issuedigest_api.cookies.set_session_cookie(response: Response, issued: IssuedSession)`과
`clear_session_cookie(response: Response)`는 향후 callback을 위한 내부 helper입니다.
Secure·HttpOnly·SameSite=Lax·Path=/·Domain 없음이며 cookie 수명은 발급 만료를 넘지 않습니다.
HTTPS를 전제로 하며 HTTP 개발용 불안전 옵션이나 클라이언트 토큰 저장소는 없습니다.
테스트만 내부 fixture로 합성 세션을 발급합니다. 실제 PostgreSQL 통합 검증은 storage README의
전용 loopback 합성 DB 설정을 사용하며 CI에서는 이 검증이 필수입니다.
