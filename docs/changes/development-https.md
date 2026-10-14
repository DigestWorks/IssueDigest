# 고정 HTTPS 개발 접속 준비

2026-10-14 한국 시간. 원격 localhost 미리보기의 인증서/포트 문제를 피하고 사용자 실제 Google 로그인→자료 목록→원문·인용을 확인할 개발 경로를 준비한다. 기존 제품 코드/API·스키마/의존성을 바꾸지 않는 운영 준비이며 공개 제품/main 배포는 유예한다(D013).

## 경로·범위

- 준비 주소는 `https://dev.issuedigest.projects.ai.kr`. 현재 DNS/TLS/공개 프록시는 미설치다. 관리자와 주소/인증서가 달라지면 실제 origin/callback을 함께 맞춘다. localhost 미리보기를 사용자 확인 주소로 다시 제공하지 않는다.
- 공개 Nginx TLS → 서버 내부 `127.0.0.1:18173`의 개인 정적 웹/프록시 → 기존 `127.0.0.1:18090`의 개인 FastAPI runtime → 기존 앱 권한 DB. 웹은 고정 Node/lockfile의 React Router SPA 빌드이며 Vite 개발 서버/HMR을 외부에 노출하지 않는다.
- 개인 웹 자산과 개인 Nginx prefix/config/PID·실행만 만든다. 기존 Nginx 설치 바이너리를 개인 계정으로 실행하고 루프백에만 바인딩한다. 시스템 Nginx/인증서·운영 서비스/main·공용 checkout·기존 DB/회원/자료·권한은 변경하지 않는다.
- 개인 API의 공개 origin을 준비 주소에 맞추되 기존 앱 역할/Google client를 사용한다. Google Console에 해당 callback이 추가돼야 실제 제공자 인증이 성공한다. Google client 파일에 남은 과거 redirect 목록은 Console의 현재 허용 목록 검증이 아니다.
- 실제 세션/identity/token을 제조하지 않는다. Origin 거부·보호401·start/취소flow·등록 자료 유지만 내부에서 검증한다. 실제 외부 DNS/TLS/로그인 성공을 미리 완료로 기록하지 않는다.
- 개인 API/웹은 tmux 개발 세션이다. 재부팅 자동 시작·운영 서비스/비용/정기 백업 완료가 아니다. 운영 전환과 달리 소유 개발 프로세스만 제어한다. 실패하면 개인 웹만 정지하고 기존 개인 API를 알려진 이전 설정으로 복귀시킨다.

## 관리자와 사용자 작업

개발자가 직접 하지 못하는 범위는 DNS·공개 인증서·시스템 Nginx다. 기존 권한 제한을 유지하고 관리자에게 외부 HTTPS 경로 설치만 요청한다. 서버 자체의 추가 유료 자원·DB 계정/권한·sudo 확대는 필요하지 않다. 구체적인 프록시와 적용/검증 순서는 [개발 HTTPS 인수인계](../../infra/development-https.md)를 따른다.

사용자는 기존 Google OAuth 웹 클라이언트의 승인된 리디렉션 URI에 `https://dev.issuedigest.projects.ai.kr/api/v1/auth/google/callback`을 추가한다. 기존 localhost URI는 제거할 필요 없다. 키·secret 재발급/공유는 요청하지 않는다. 외부 HTTPS가 실제로 연결된 뒤 Google 로그인과 자료 열람을 사용자 브라우저에서 확인한다.

Sites는 상태 요약을 계속 갱신하지만 사용자가 이미 열어 둔 탭을 다시 열거나 이동하지 않는다.

## 실행·검증

- [x] 개인 서버의 고정 빌드·별도 자산 보관, 개인 정적 Nginx의 설정 검사·loopback 웹/SPA/보호 API 응답 확인.
- [x] 기존 앱 계정/Google client·새 공개 origin과 start/cancel/Origin 거부·자료/초대·세션0 확인.
- [x] 관리자 적용 파일/요청 메시지·공식 문서/독립 검토·Draft PR/Sites 기록과 개발 인계.
- [x] 사용자 Google Console callback 추가 완료 전달. 실제 제공자 반환 검증은 외부 HTTPS 후 확인.
- [ ] 관리자 DNS/TLS/공개 프록시 연결.
- [ ] 외부 인증서·동일 origin 라우팅·미승인 거부와 실제 사용자 Google 로그인/원문·인용3개 확인.

## 실제 내부 준비 결과

제품 코드 변경 없이 서버의 Node24.21.0/기존 lockfile로 정적 빌드12파일·source map0을 만들고 소유 별도 경로에 보관했다. 원본 source commit은95b7bff다. 기존 개인 Nginx 바이너리의 지원하지 않는 `-e` 옵션으로 첫 설정 검사가 중단됐고, 실행 전 설치 버전에 맞는 `-p/-c` 명령으로 검사·기동했다. 기본 시스템 error log 경로 접근 경고는 개인 계정 startup의 초기 경고이며 개인 config의 실제 로그 경로/접근 권한을 사용한다. 시스템 로그 권한을 바꾸지 않았다. 개인 tmux `https-web`은 loopback18173, 기존 개인 API는18090이다.

실제 내부 검사: `/`·`/login`·빌드 asset200, 없는asset·dotfile404, health200·인증 전session401, 과거localhost Origin403·준비주소 start303, 정확 callback/PKCE/nonce·Secure/HttpOnly/Lax cookie·브라우저에 연결된 취소 callback303 확인. 취소 검사에서 Cookie를 HTTP 내부 upstream에 명시 전달했으며 이는 외부 TLS가 종료된 프록시 전달을 검증한 것이다. HTTP 브라우저의 Secure cookie 제한을 완화하거나 공개 TLS 검증을 대신한 것이 아니다. 확인 후 자료1건/인용3개/초대1건·미바인딩 초대 유지, 실제 auth user/session/member/flow0·앱 DDL 부재다.

관리자 설치안을 계정 개인600 파일에 준비했다. 실제 DNS/TLS/공개 프록시·Google Console의 새 callback 허용·사용자 로그인은 미완료다. 예시 TLS 설정의 인증서 경로는 발급/검사 전이며 내부 설정 검사와 다르다. 앱/자료/의미 검색·AI/워커의 제품 완료를 주장하지 않는다.

사용자가 새 Google callback 추가 완료를 전달했다. Console 설정을 독립 조회하거나 실제 Google 반환을 확인한 것은 아니며, 외부 HTTPS 적용 후 제공자 흐름에서 검증한다. 웹 asset 검사 도구가 처음에는 script src를 기대했지만 빌드는 inline import를 사용했다. asset URL을 실제 빌드 형식에서 찾아 재검사했고 모든 내부 검사가 통과했다. 제품 코드는 수정하지 않았다.
