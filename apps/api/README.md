# API 앱

Python 3.13.12·FastAPI 0.143.0의 HTTP 진입점입니다. 응답 모델은 `issuedigest-domain`에서 가져옵니다. DB·검색·실행기·공급자·인증을 아직 연결하지 않았습니다.

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


원문·인용과 개체·주장·관계·관측·비교 조건의 도메인 전송 모델을 OpenAPI components로 등록합니다. `ResearchBundle`, `ComparisonAssessment`와 의존 모델을 기존 models_json_schema 호출에 함께 등록하며 이름 충돌을 거부합니다. 실제 `/openapi.json`과 export 결과가 일치하고 태그 union 참조가 해석됩니다. HTTP 경로는 위 두 개 그대로이며 연구 자료 생성/조회·저장·인증 API는 아직 없습니다.
