# 웹 API 클라이언트·생성 타입

npm workspace의 비공개 TypeScript 소스 패키지입니다. 웹이 `@issuedigest/api-client`를 가져와 같은 출처의 `GET /api/v1/status`를 호출합니다. 별도 게시·번들·서버 앱은 없습니다.

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
