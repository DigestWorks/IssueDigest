# 서버 세션·작업 공간 권한·근거 조회 API

2026-10-12 한국 시간. R1의 첫 HTTP 자료 접근 경계를 구현한다. 기존 EvidenceRepository와 실제 PostgreSQL을 사용한다. A006의 로그인 공급자 선택은 유지하고, 공급자가 확인한 사용자를 서버 세션에 연결할 내부 인터페이스를 만든다. 로그인 화면·OIDC 검증·운영 연결 완료로 표시하지 않는다.

## Global Constraints

- 기준은 기존 R1/R2, D003/D004/D006/D007/D010/D011이다. Python/FastAPI·PostgreSQL·생성 OpenAPI/TypeScript를 사용하고 고정 외부 의존성 버전을 바꾸지 않는다. API의 storage workspace 의존성 연결과 uv.lock 재생성은 허용한다.
- 로그인 공급자·OIDC/JWT 검증·초대 UI·운영 DB·앱 로그인/자료 화면·AI·실행 저장/SSE·검색은 후속이다. 사용자 요청 헤더/쿼리/본문의 user_id·workspace_id·이메일을 인증 증거로 받지 않는다. 공개 세션 발급·사용자 등록·멤버십 변경·테스트 로그인 경로를 만들지 않는다.
- 실제 세션은 PostgreSQL에 저장한다. 토큰 원문·Cookie·DB URL/인증값·원문 내용은 저장 로그/오류/공개 문서에 넣지 않는다. 테스트는 전용 loopback issuedigest_test 합성 DB에만 마이그레이션/초기화한다. 공유 서버의 DB·계정·키·기존 운영 자료는 변경하지 않는다.
- 기본 ASGI 앱은 외부 연결 없이 import/기동한다. 명시적인 서버 구성으로 접근 저장소를 전달하기 전에는 보호 경로가 자료를 반환하지 않는다. app factory는 요청 파라미터에서 저장소/권한을 구성하지 않는다. 기존 상태/헬스 응답·request ID 의미와 기존 EvidenceBundle/CanvasBundle 계약·웹 UI는 보존한다.
- 자료 조회는 GET 한 경로만 추가한다. 반환은 검증된 기존 EvidenceBundle이며 임의 JSON 타입 단언·가상 자료·모델 재호출은 없다. 기존 도메인 component 이름 충돌 거부를 보존하고 OpenAPI의 실제 경로/쿠키 security/응답을 생성 TS로 연결한다. 생성 파일은 직접 수정하지 않는다.
- API 자료 응답/오류는 Cache-Control: no-store와 서버가 만든 X-Request-ID를 가진다. 로그인 미연결 상태를 운영 사용 가능으로 표현하지 않는다. 검증·PR·Sites·서버/현재 폴더 인계는 각각 증거를 기록한다. 이 계획의 ignored 리뷰 기록은 미병합 PR 검토가 끝날 때까지 보존한다.

## Task 1 · 세션 저장에서 보호 HTTP 조회까지

- [x] 아래 수용 조건 구현·검증. 독립 작업 리뷰 지적 보완·수정 범위 재검토 통과; 게시/인계는 진행 기록을 따른다.

1. `packages/storage`에 내부 인증 저장소와 auth_users/auth_workspace_memberships/auth_sessions 테이블 및 순차 Alembic migration을 추가한다. 사용자는 UUID4와 정확한 issuer/subject pair로 식별한다. 같은 pair를 다른 UUID로, 같은 UUID를 다른 pair로 바꾸면 충돌한다. 서로 다른 issuer의 같은 subject는 별개이며 이메일/공백 정규화로 합치지 않는다. 값은 nonempty·NUL 없음·길이 제한을 검증하고 그 원문을 보존한다. 사용자 enabled, membership active와 viewer/editor/owner 역할을 저장한다. 존재하지 않는 사용자 참조·미지원 역할·잘못된 UUID는 거부한다. 기존 근거 저장·기존 migration과 이미 저장한 스냅샷은 보존한다. 이 단계의 membership workspace UUID는 기존 근거의 namespace이며 workspace 생성/초대 관리 전체 기능이 아니다.
2. 공개하지 않은 내부 메서드로 검증된 외부 identity를 등록하고 회원 권한을 부여/회수하며 세션을 발급/폐기할 수 있다. 이 메서드 자체는 공급자 토큰 검증/초대 승인을 수행하지 않는다. caller가 신뢰되는 OIDC 연결기/관리자 경계여야 한다는 조건을 문서화한다. 비활성/없는 사용자에게 세션을 발급하지 않는다. 토큰은 secrets.token_urlsafe(32)의 256bit 임의 값이며 DB에는 SHA-256 해시만 저장한다. 원문은 발급 결과에서만 돌려주고 repr/log에 포함하지 않는다. 재발급은 다른 토큰을 만든다. 폐기는 idempotent하며 새 요청부터 효력이 있다.
3. 세션 절대 수명은 기본/최대 28,800초(8시간), 내부 발급 인자로 더 짧게 1~28,800 정수만 허용한다(bool 거부). 마지막 성공한 허용 조회 후 1,800초(30분) 이상 활동이 없으면 거부한다. 만료 시각/idle 경계와 같은 시각도 거부한다. 시각은 서버/DB의 timezone-aware UTC 기준이며 요청에서 받지 않는다. 성공한 권한 있는 조회만 마지막 활동을 갱신하며 절대 만료는 연장하지 않는다. 초기 등록·발급·갱신은 원자적이다. 사용자 비활성·세션 폐기·membership 회수를 다음 요청의 DB 조회에서 확인하며 권한을 메모리 캐시하지 않는다. 이미 시작한 응답을 소급 회수한다고 주장하지 않는다.
4. 내부 `load_evidence` 접근 경계에서 세션·사용자 활성·workspace membership을 확인한 뒤 같은 DB Connection/transaction으로 기존 근거 integrity 로더를 호출한다. 존재하지 않는 세션/만료/폐기/사용자 비활성은 인증 거부, 미가입 공간/다른 공간의 snapshot/없는 snapshot은 같은 자료 없음 응답이다. 권한 없는 호출은 근거 payload를 읽거나 반환하지 않는다. DB 장애/저장 훼손은 고정 오류로 숨기고 임의 다른 자료로 치환하지 않는다. 기존 EvidenceRepository.save/load API를 보존한다.
5. `create_app` 서버 factory와 `GET /api/v1/workspaces/{workspace_id}/evidence/{snapshot_id}`를 구현한다. UUID4 path를 사용하고 `__Host-issuedigest_session` Cookie만 인증 전달 채널로 받는다. 원문 토큰을 user header/Bearer/query/path로 받지 않는다. Cookie 없음/형식 오류는 401; 미구성 backend에 유효 형식 Cookie가 오면 503; 구성 후 unknown/expired/revoked/disabled 세션은 401; 미가입/다른 공간/없음은 동일한 404; DB 장애/훼손은 고정 503. 경로 형식 오류는 기존 FastAPI 422로 처리한다. 200은 기존 EvidenceBundle의 정확한 JSON이며 작업 공간·인용 순서·내용을 보존한다. 오류에 source/token/exception을 반영하지 않는다. 모든 이 경로의 상태에 no-store·request ID가 있고 401/404에도 근거 내용이 없다. 없음/형식 오류는 DB 연결 없이 거부한다.
6. 향후 로그인 callback이 사용할 `set_session_cookie`/`clear_session_cookie` 내부 helper를 구현한다. cookie 이름은 위와 같고 Secure·HttpOnly·SameSite=Lax·Path=/·Domain 없음이며 발급 만료를 넘는 지속시간을 설정하지 않는다. HTTP 개발용 불안전 cookie 옵션/클라이언트 저장소/자동 테스트 로그인은 추가하지 않는다. helper는 공개 발급 endpoint가 아니다. OpenAPI에서 apiKey/in:cookie/name을 표시하고 보호 경로만 해당 security requirement를 가진다. 실제 HTTP/export 동일·component ref 해석·기존 component 충돌 검사·생성 TS path compile 소비를 검증한다. 기존 두 경로는 익명 200으로 보존한다.
7. 역할별 파일로 storage schema/migration·identity/session/access·HTTP 경로/쿠키·app factory를 분리한다. 새 인증 공급자/암호/JWT 패키지·임의 의존성·앱 화면을 추가하지 않는다. API/storage README에 구성·내부 발급의 신뢰 전제·세션 수명·migration·불완전 로그인/운영 경계를 기록한다. 기존 tests의 두 경로 전용 기대값만 실제 추가 경로에 맞춰 의미 있게 변경하며 기존 정책·불변 모델 검증을 약하게 만들지 않는다.
8. TDD: 호출 가능한 최소 scaffold에 대한 실제 behavior assertion RED를 먼저 기록한다(import/수집 오류를 RED로 계산하지 않는다). 실제 PostgreSQL에서 identity 충돌/분리·hash-only 저장·토큰 비노출·수명/idle·활동 갱신·폐기/사용자 비활성·membership 회수·서로 다른 공간·동일 snapshot 두 회원 조회·invalid role/FK·migration 0001→head/다운그레이드의 근거 보존을 검증한다. 실제 DB + FastAPI TestClient에서 로그인/권한 matrix·동일 내용/인용 순서·no-store/request ID·오류 비노출을 확인한다. mock 성공만으로 인증/자료 접근을 검증하지 않는다. DB 미설정은 명시적 로컬 skip이고 CI는 기존 전용 PostgreSQL URL로 필수 실행한다. 새 fixture는 기존 테스트 utilities 또는 최소 공유 conftest로 통합해 서로 migration/reset을 깨뜨리지 않게 한다.

## 완료 증거

controller의 실제 PostgreSQL 포함 전체 npm run check, 독립 작업/전체 변경 리뷰 및 수정 범위 재검토, 실제 HTTP의 익명/권한/만료/다른 공간/성공 응답 확인. 합성 로그인은 내부 테스트 fixture 발급만 사용하며 제품 로그인 기능으로 배포하지 않는다. Draft PR·Sites 요약·현재 폴더/서버의 기본 fail-closed 앱 인계를 각각 기록한다.

## 구현 판단 기록

- 인증 공급자 선택과 분리한 실제 DB 세션·보호 조회부터 구현한다. 공급자 요구가 다르면 callback/세션 정책의 연결을 조정해야 한다.
- 세션은 절대8시간·idle30분을 초기 기본으로 한다. 더 긴 유지가 필요하면 로그인/재인증 정책과 cookie 수명을 함께 조정한다.
- 기존 근거에 새 auth FK를 소급 추가하지 않고 HTTP 접근에서 membership을 검사한다. workspace 관리 전체 기능은 후속으로 필요하다.
- 앱의 작업 공간 도구가 저장소를 인식하지 못해 기존 sibling worktree를 사용한다. 필요하면 앱의 작업 공간 연결을 정리해야 한다.
- 미병합 PR 리뷰 기록은 보존한다. 검토 후 로컬 scratch 정리가 필요하다.

## 공식 근거

- [OWASP Session Management](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html): 임의 세션 ID·서버 저장·idle/absolute 만료·폐기·cookie 보호. 위 시간은 프로젝트의 초기 정책이며 표준의 필수 고정값이라고 주장하지 않는다.
- [MDN Set-Cookie](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Set-Cookie): __Host-의 Secure·Path=/·Domain 없음 및 HttpOnly/SameSite.
- [FastAPI 추가 응답](https://fastapi.tiangolo.com/advanced/additional-responses/): 실제 응답과 OpenAPI의 일치. 수동 schema 복제가 아니라 기존 canonical model/ref를 사용한다.

## 구현·검증 결과

- 구현 `73f8684`, 동시 조회·오류 계약 보완 `ed44370`. issuer/subject는 각각 1~256 Unicode 문자이며 원문을 보존한다. 해시 세션, 신뢰된 내부 발급/권한 관리와 보호 조회를 구현했다.
- 같은 세션의 동시 조회에서 PostgreSQL 40001이 발생하면 전체 권한·무결성·활동 갱신 트랜잭션을 새로 시도한다. 총3회로 제한하며 소진·그 밖의 DB 오류는 고정503이다. 이미 읽은 자료/권한을 재사용하지 않는다. 실제 DB 겹침·재시도 도중 권한 회수·무결성 변경 및 한도 검증 통과.
- 401/404/422/503의 고정 JSON을 실제 FastAPI 응답 모델→OpenAPI→생성 TS에 연결했다. 422는 UUID4 오류 위치/종류만 남기고 입력/context는 반영하지 않는다. 기존 canonical EvidenceBundle/이름 충돌 검증은 보존했다.
- controller가 `ed44370`에서 실제 전용 PostgreSQL18.6을 포함한 전체 검사 exit0: Python778+JS134=912, skip0; lint/format·mypy·TS·SPA·계약 drift 통과. 독립 작업 리뷰의 두 지적을 수정하고 재검토 통과했다. 전체 변경 리뷰·PR·Sites·인계 상태는 진행 기록을 따른다.
- 실제 Uvicorn HTTP19회에서 두 회원의 정확한 동일 근거/인용 순서, 같은 세션 동시 조회200, 익명/형식 오류/폐기/비활성/절대·idle 만료401, 미가입/다른 공간/없는 자료404, 미구성 backend503을 확인했다. 보호 응답16회 모두 no-store/서버 UUID ID. HTTP OpenAPI와 export 동일. 내부 합성 DB/세션만 사용했고 확인용 서버 스레드를 종료했다.
- 실제 공급자 로그인·초대·앱 화면·운영 DB·기존 운영 자료·AI는 연결하지 않았다. 기본 앱은 외부 연결 없이 기동하고 보호 GET은 인증·구성이 없으면 자료를 반환하지 않는다.
