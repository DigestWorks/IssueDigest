# 웹 앱

React Router Framework mode·React·TypeScript의 한국어 조사 작업 공간입니다. 현재는 빈 자료 상태와 실제 API 연결 확인만 제공합니다. 조사·저장·AI 실행과 가상 자료는 없습니다.

## 루트에서 실행

Node 24.21.0·npm 11.19.0을 선택합니다. 모든 명령은 저장소 루트에서 실행합니다.

```sh
npm ci
npm run setup
npm run dev
```

`npm run dev` 통합 실행기는 Linux에서 지원·검증했습니다. Windows에서는 `npm run dev:api`와 `npm run dev:web`을 별도 터미널에서 실행하고 각각 직접 종료합니다.

웹은 `http://127.0.0.1:5173`입니다. 웹만 실행하려면 `npm run dev:web`을 사용하고, 다른 터미널에서 `npm run dev:api`로 API를 실행합니다. 확인 요청을 접수하면 확인 중 상태와 중복 클릭 방지를 표시하고 검증된 성공·실패·재시도를 안내합니다. 시간 초과는 기본 5초이며 응답 본문 읽기도 포함합니다.

웹은 같은 출처의 `/api/v1/status`를 `@issuedigest/api-client`로 호출합니다. 인증·도메인·공급자·도구 호출은 API의 책임이며 앱 내부 코드를 직접 가져오지 않습니다.

## 개발 프록시

Vite 서버가 `/api`·`/health`를 `http://127.0.0.1:8000`으로 전달합니다. 다른 API 포트가 필요하면 아래처럼 실행합니다.

```sh
uv run --package issuedigest-api uvicorn issuedigest_api.main:app --reload --host 127.0.0.1 --port 8001
# 다른 터미널, 저장소 루트
API_PROXY_TARGET=http://127.0.0.1:8001 npm run dev:web
```

`API_PROXY_TARGET`은 개발 서버에서만 읽으며 브라우저 번들에 넣지 않습니다. `VITE_*`에 비밀값이나 공급자 키를 넣지 않습니다. 기본 웹 포트는 중복 사용 시 자동 변경하지 않고 실패합니다.

## 검증과 생산 빌드

```sh
npm run lint
npm run typecheck
npm test
npm run build
npm run contract:check
```

`ssr: false`인 Framework SPA 구조입니다. 루트는 빌드 때 미리 렌더링되므로 브라우저 전용 API를 초기 렌더에 사용하지 않습니다. 기본 서버 진입점의 빌드 의존성인 `@react-router/node`·`isbot`도 고정합니다. 별도 웹 서버 앱이나 배포 패키지는 추가하지 않습니다.

운영에 제공할 파일은 `apps/web/build/client`입니다. 정적 호스트·리버스 프록시에서 `/api/*`, `/health/*`를 API로 먼저 연결하고 나머지 앱 경로는 `index.html`로 연결합니다. 개발 프록시는 운영 구성에 포함되지 않습니다. 운영 배포는 아직 하지 않았습니다.

UI 테스트는 실제 화면과 공통 클라이언트를 사용하며 HTTP 경계만 대체해 확인 중·성공·실패·재시도·잘못된 계약을 확인합니다. 데스크톱·모바일·실제 API 중단 스모크 증거는 [진행 기록](../../docs/planning/progress.md)에 별도로 남깁니다. [공식 SPA 안내](https://reactrouter.com/how-to/spa)를 사용했습니다.
