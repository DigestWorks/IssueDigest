# 공통 Python 도메인·계약

Python 3.13.12·Pydantic 2.14.0의 `issuedigest-domain` 패키지입니다. 현재 `Liveness`, `ServiceStatus` 응답 모델만 정의하며 추가 필드와 잘못된 값은 거부합니다. 자료·인용·관계·실행·생성 화면 계약은 아직 확정하지 않았습니다.

앱은 이 패키지를 사용하지만 이 패키지는 앱 내부 구현에 의존하지 않습니다. FastAPI가 이 모델을 응답 계약과 OpenAPI의 원본으로 사용하며 웹은 HTTP 계약에서 생성한 타입으로 연결합니다.

저장소 루트에서 설치·검증합니다.

```sh
uv sync --locked --all-packages
uv run ruff check .
uv run mypy
uv run pytest
npm run contract:generate
npm run contract:check
```

`uv.lock`으로 의존성을 고정합니다. 모델 변경은 생성된 OpenAPI·TypeScript 타입과 API 테스트를 함께 검토합니다. 기준 DB·Neo4j·검색·실행기 모델이나 도구 호출은 아직 구현하지 않았습니다.
