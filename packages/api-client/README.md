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

첫 원문·인용 계약의 생성 타입도 공개합니다: `SourceDocument`, `DocumentVersion`, `ParsedRepresentation`, `PageSpan`, `ParsedTable`, `TableCell`, `Citation`, `TextQuoteSelector`, `PdfQuoteSelector`, `NormalizedBox`, `TableCellSelector`, `EvidenceBundle`, `CitationAnchorValidation`. 수기 TypeScript 계약을 별도로 복제하지 않습니다. 이 모델은 실제 앱의 OpenAPI components에 등록되며 HTTP paths는 기존 두 경로 그대로입니다. 자료 수집·저장·인용 조회 API나 제품 화면은 아직 없습니다.

`getCitationUtf16Range(text, selector)`는 Python `model_dump`가 기본값까지 포함한 생성 text/pdf 전송 타입을 받아 `{ start, end }`의 JS UTF-16 인덱스를 반환합니다. 먼저 code point 범위와 quote·prefix/suffix의 정확한 일치를 확인하고 잘못된 입력을 throw합니다. 한글·BMP 밖 이모지·결합 문자·공백·NFC/NFD를 그대로 보존하며 grapheme cluster로 분할하지 않습니다. 생성 타입의 text/pdf kind를 요구하며 table selector는 입력이 아닙니다. PDF 페이지/좌표·버전 연결은 서버의 표현/번들 검증 범위이며 이 함수는 제공된 텍스트의 인용 범위만 확인합니다. Python과 TS 테스트는 `tests/fixtures/citation-unicode.json` 합성 자료와 같은 offsets를 공유합니다.

정확한 anchor가 일치해도 `support_status="not_evaluated"`이며 주장 지지·원문 보관·접근 권한·파싱 성공을 보장하지 않습니다. 출처 날짜 정밀도·재수집 관측·비교 fingerprint·실제 parser와 저장·관계·실행·화면·사용량 계약은 후속 작업입니다.
