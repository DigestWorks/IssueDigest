# 실제 Google 로그인 개발 연결

2026-10-14 한국 시간. 기존 Google OAuth/자료 열람 명세와 공동 DB 적용 이후의 실제 연결 작업이다. 기존 제품 코드·API/스키마·의존성 변경은 없고 승인된 개발 runtime과 사용자 첫 로그인 확인을 수행한다.

## 범위·조건

- 실제 공동 DB의 head0004·승인 자료1건/인용3개/초대1건과 기존 DDL 없는 앱 계정을 사용한다. 개발자의 스키마 계정·합성 identity/세션/멤버십은 runtime에 주입하지 않는다.
- 서버 개인 worktree/개인 tmux API만 구성 runtime으로 바꾼다. 앱 URL은 등록된 `https://localhost:16173`, callback은 `/api/v1/auth/google/callback`이다. Google client JSON은 기존 승인된 파일만 사용하고 계정 개인700/600 경로에 보관한다. 접속값·토큰/원문·Google ID/계정/개별 식별자는 공개 문서/로그에서 제외한다.
- 공개 앱/main·공용 checkout·운영 서비스·프록시·시스템 인증서 신뢰 설정·권한은 변경하지 않는다. localhost HTTPS는 개발용 자체 서명 인증서와 개인 SSH 터널을 사용한다. 서버는 loopback만 수신한다. 브라우저 신뢰 예외와 HTTP 자동 검사의 명시 CA 검증을 구분한다.
- 변경 전 정확한 tmux pane/포트·미설정 API·소유 checkout을 확인한다. 설정 누락/다른 소유 프로세스·포트 충돌은 중단한다. 실패 시 해당 개인 API만 기존 상태 실행으로 복귀한다. DB migration/reset/추가 invite/세션 생성은 하지 않는다.
- 인증 전 웹/상태 API·session401·자료 조회401·잘못된 Origin 거부를 검사한다. 정상 start는 실제 DB의 일회 flow와 Secure/HttpOnly/Lax cookie·고정 Google 주소/등록 callback·openid email/PKCE/nonce를 확인하되 인증 code/token을 제조하지 않는다. 생성한 검증 flow는 같은 브라우저 cookie/state의 명시 취소 callback으로 소비한다.
- 사용자 브라우저에서 실제 Google 로그인을 수행한 뒤 session·승인 공간 자료 목록·원문/인용3개 열람을 확인한다. 그 전에는 실제 로그인/열람 완료로 표시하지 않는다. 두 번째 Google 계정과 공개 배포·AI/의미 검색은 후속이다.

## 실행·검증

- [x] 기존 앱 역할/Google 파일·callback·서버 개인 API/포트 확인 및 비밀 주입·configured runtime 시작.
- [x] 개인 SSH 터널/HTTPS·미인증 보호·CSRF·실제 start/cancel flow와 사용자/세션0 보존 확인.
- [ ] 인증 전 브라우저 화면·Google 로그인 사용자 진입 준비/열기. 실제 로그인 완료는 별도 결과로 기록.
- [x] docs/검토·Draft PR·Sites와 개인 개발 인계. 로그인/열람 사용자 확인은 미완료로 유지.
- [ ] 사용자 실제 로그인→같은 공간 자료 목록→원문·인용 확인.

## 실제 연결 결과와 사용자 접속 제한

기존 앱 역할·head0004·승인 자료1건·실제 사용자/세션/회원/flow0을 확인했다. Google 설정은 개인600 파일로 서버 개인 계정에 전달하고, 개인 tmux API만 구성 runtime으로 바꿨다. 웹·공용 checkout·운영 서비스·main은 변경하지 않았다. 이전 API의 정상 종료 직후 pane가 사라지는 시차 때문에 controller guard가 중단됐고, 실제 포트 해제/남은 web pane를 다시 확인한 뒤 새 개인 API window에서 시작했다. private 진단 기록을 보존한다.

HTTPS HTTP 검사에서는 개발 인증서를 명시 CA로 검증했다. 로그인/health200·session401·잘못된Origin403, 실제 Google start303·정확 callback/openid email/PKCE/nonce·Secure/HttpOnly/Lax cookie, 브라우저에 묶인 취소 callback303과 flow 소비를 확인했다. 확인 후 승인 자료1/인용3/초대1은 유지되고 실제 auth user/session/member/flow0이다. Google code/token/identity를 제조하거나 실제 로그인 성공을 가장하지 않았다.

인증 전 Chromium 화면은 자체 서명 인증서 예외를 적용한 QA이다. 이는 사용자 앱 내 브라우저의 인증서 신뢰 검증이 아니다. 사용자 화면에서는 `ERR_CERT_AUTHORITY_INVALID`가 발생하고 미리보기 주소의 포트도16173에서 다른 포트로 바뀌었다. 이 주소를 그대로 Google OAuth에 사용할 수 없으며 실제 로그인 검증은 접속 방식 결정 전까지 대기다. API/개발 HTTPS가 응답하는 것과 사용자의 실제 접속 가능성을 분리한다.

사용자에게 원격 localhost를 접속 주소로 제공한 것은 잘못된 안내였다. 사용자 PC의 SSH/인증서 설정을 요구하는 방향을 중단하고 고정 HTTPS 개발 주소에서 확인하도록 경로를 준비한다. 별도 개발 주소/프록시·인증서·OAuth callback 등록이 필요하다. 공개 앱 배포 유예(D013)는 유지한다. 기존 서비스의 Nginx 설정은 읽기 가능하지만 개발 계정이 수정할 수 없음을 직접 확인했고 변경하지 않았다. 개발 주소 설치는 관리자 협력이 필요한 후속 작업이며 현재 접속 가능한 것으로 표시하지 않는다. 현재 연결을 실제 로그인/자료 열람 완료로 표시하지 않는다.

인증 전 로그인 화면을1366×900/390×844에서 확인했다. 로그인 페이지 콘솔 오류/경고0, 미인증 홈은 로그인 안내와 예상 session401을 보였다. 브라우저 인증서 예외 QA이며 실제 Google 제공자 로그인/사용자 접속 성공 증거가 아니다.
