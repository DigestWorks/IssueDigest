# 개발 HTTPS 연결 인수인계

2026-10-15 한국 시간. 개발 주소는 `https://dev.issuedigest.projects.ai.kr`이며 DNS/TLS/공개 연결을 직접 확인했다. 실제 사용자 Google 로그인·자료 열람은 별도 확인한다. [작업·검증 경계](../docs/changes/development-https.md)를 따른다. 기존 `issuedigest.projects.ai.kr`·운영 서비스·main 자동 배포는 유지한다.

## 2026-10-15 18:46 KST · 자료 중심 UI·법안 기본 정보

[작업 명세](../docs/changes/workspace-clarity-legacy.md)의 source0116885·정적14파일/source map0을 개인 runtime에 반영했다. API/개인 Nginx만 재시작/reload하고 시스템·운영·main을 유지했다. 외부 CA/hostname·index 빌드 일치·home/login/asset/health/status200·미인증session/search401/no-store다.

공동 개발DB에 기본 정보8건을 추가해 총자료9/인용19·모두 색인, 반복 신규0·기존 인증/자료 보존·schema0004/DDL 부재를 확인했다. 전후 서버 외부 백업·별도 loopback 앱 복원/새8 bundle 대조, 합성 계정 보호 목록/GET/검색·권한 폐기를 확인했다. 실제 사용자 세션을 생성/대신 사용하지 않았다. 사용자의 자료/검색 확인과 정기 수집/AI·운영 배포는 별도다.

## 2026-10-15 18:04 KST · 검색 앱 갱신

[검색 인터페이스](../docs/changes/evidence-search-interface.md) source `fd26683`의 고정 Node/lockfile 빌드14파일·source map0을 개인 자산 경로에 보관했다. 개인 API 재시작과 개인 정적 Nginx root/reload만 수행했다. 외부 TLS/시스템 서비스·main/공용 checkout·DB schema/권한은 유지했다.

CA/hostname 검증을 유지한 실제 개발 HTTPS에서 index가 해당 빌드와 일치하고 home/login/asset/health200·미인증session/search401/no-store다. DB read-only 확인에서 기존 승인 자료1건/인용3개·초대 바인딩·schema0004·DDL 없는 앱 역할을 확인했다. 실제 사용자 세션을 제조/대신 사용하지 않았고 사용자 본인의 검색·원문 열람은 별도 확인한다. 원문·PDF·셀·오류·로그아웃 여정의 브라우저 검증은 별도 소유 합성 DB/HTTP 환경에서 수행했다.

개인 runtime 집계는 계정 전용 `~/.local/state/issuedigest/evidence-search-interface-20261015/`에 보관한다. 이전 초기 준비 source와 현재 앱 갱신 source를 구분한다. 재부팅 자동 실행·운영 배포·인증서 갱신 실행의 완료를 의미하지 않는다.

## 2026-10-15 17:04 KST · 외부 연결 완료

- 권한 DNS ns1~ns4.hosting.co.kr와 Google/Cloudflare 모두 같은 개발 서버의 A 레코드를 반환한다. 앞선 ns3만 응답하던 불일치는 이번 재검사에서 해소됐다.
- 일반 개발 URL과 서버 직접 SNI 연결 모두 CA/hostname 인증서 검증 통과. `/login`·빌드 JS·`/health/live`200, 미인증 `/api/v1/auth/session`401이다.
- 설치된 개발 virtual host의 IPv4/IPv6 443·인증서·18173 프록시·access_log off와 error_log 폐기 설정을 읽기 확인했다. 관리자가 외부 설정을 적용했으며 개발자는 시스템 설정을 수정하지 않았다. 자동 갱신의 실제 실행/재부팅 복구는 이번 검사가 아니다.
- HTTPS의 잘못된 Origin403·정상 로그인 시작303·정확 Google callback/PKCE·Secure/HttpOnly/Lax cookie·브라우저에 연결된 취소303을 확인했다. Google 제공자에는 로그인 요청을 보내지 않고 취소 flow만 정상 소모했다. 사용자 계정·세션을 임의로 생성하지 않았다.
- 이제 사용자에게 [개발 로그인](https://dev.issuedigest.projects.ai.kr/login)을 안내할 수 있다. 후속 읽기 전용 DB 확인에서 실제 identity·membership·세션 기록·초대 subject 바인딩 존재를 확인했다. 사용자 화면의 승인 자료/인용 열람·로그아웃은 아직 확인 대기다. 아래 초기 실패 기록은 당시 상태로 보존하며 추가 DNS/TLS 요청은 해소됐다.

## 2026-10-15 · 초기 외부 연결 점검 (이후 해소)

- 개발 virtual host의 HTTP80 → 내부18173 프록시는 설치됐다. DNS를 우회해 실제 서버에 Host를 유지한 읽기 검사에서 `/login`200·`/health/live`200·미인증session401을 확인했다. 이것은 HTTP upstream 확인이며 일반 도메인 접속/HTTPS 성공이 아니다.
- 현재 개발 주소의 DNS는 OS/Google Public DNS/Cloudflare 및 권한 DNS `ns1.hosting.co.kr`, `ns2.hosting.co.kr`에서 NXDOMAIN이다. 권한 응답에도 A 레코드가 없어 로컬 캐시 전파 대기로만 간주하지 않는다. 실제 활성 `projects.ai.kr` 존에서 이름 `dev.issuedigest`의 서버 연결 레코드를 확인해야 한다. 서버 IP는 공개 문서에서 제외한다.
- 개발 virtual host는80만 listen하며 TLS 설정이 없다. 서버 IP에 SNI를 유지한 인증서 검증은 hostname mismatch(code62)로 실패했다. 인증서 검증을 끄거나 HTTP에서 Google 로그인을 진행하지 않았다.
- 설치된 개발 virtual host에는 요청/오류 로그 차단이 없고 전역 access/error 로그를 상속한다. Google callback을 실행하기 전에 개발 host의 OAuth code/state·cookie가 로그에 남지 않도록 기존 설치안의 로그 정책을 반영해야 한다. 로그 파일 내용이나 비밀값은 읽지 않았다.
- 시스템 Nginx/인증서/DNS/앱·DB/권한을 변경하지 않고 읽기 조사만 수행했다. 아래 설치안과 사용자 callback 추가 완료 기록은 유지한다. 실제 Google 제공자 로그인/자료 열람·인증서 갱신 검증은 미완료다.

당시 전달 문장 (현재 추가 요청 불필요):

> 서버의 HTTP 프록시는 확인했습니다. 다만 `dev.issuedigest.projects.ai.kr`이 권한 DNS(ns1/ns2.hosting.co.kr)에서도 NXDOMAIN입니다. 활성 projects.ai.kr 존에 `dev.issuedigest`를 기존 IssueDigest와 같은 서버로 연결하는 레코드가 반영됐는지 확인 부탁드립니다. 이후 개발 주소용 TLS/443 연결과 callback 요청/오류 로그 차단도 적용해 주세요. 현재는 HTTP80 프록시만 있고 개발 주소의 HTTPS 인증서 검증은 hostname mismatch로 실패합니다. 기존 HTTP/ACME 준비는 유지해 주시면 됩니다.

## 개발자가 준비하는 부분

React Router 정적 빌드를 개인 자산 경로에 보관하고, 별도 개인 Nginx에서 `127.0.0.1:18173`으로 제공한다. `/login` 등 SPA 경로와 `/assets`를 구분하고 `/api/`·`/health/live`는 개인 API `127.0.0.1:18090`으로 전달한다. Vite/HMR을 외부에 노출하지 않으며 시스템 Nginx가 개인 홈 디렉터리를 읽을 권한도 필요 없다. 외부 Nginx는 이 내부 upstream 하나만 연결한다.

개인 tmux의 `https-web`·`api` 창이 담당한다. 웹 설정/정지 PID와 Google loader는 계정 개인 `~/.local/state/issuedigest/development-https-20261014/`에 있으며 비밀/접속값은 공개 저장소에 옮기지 않는다. 재부팅 자동 실행 서비스는 이번 준비에 포함하지 않는다. 개발 API의 `ISSUEDIGEST_PUBLIC_ORIGIN`은 준비 주소와 같고 기존 DDL 없는 앱 역할/Google 클라이언트를 사용한다. 초대된 계정만 실제 자료를 읽는다.

## 관리자에게 전달할 메시지

> 민재님, localhost 미리보기에서는 인증서/포트 문제로 실제 Google 로그인 확인이 안 돼 고정 HTTPS 개발 주소를 준비했습니다.
>
> 1. `dev.issuedigest.projects.ai.kr`을 현재 IssueDigest 개발 서버로 DNS 연결해 주세요.
> 2. 이 주소에 신뢰 가능한 TLS 인증서와 갱신을 설정하고, Nginx에서 전체 경로를 `http://127.0.0.1:18173`으로 프록시해 주세요. 개발 웹이 `/api/`·`/health/live`를 내부 API18090으로 전달합니다.
> 3. 원래 Host와 Origin·Cookie·쿼리·Set-Cookie를 유지하고 HTTPS임을 전달해 주세요. OAuth code/state/cookie가 access/error 로그에 남지 않도록 이 개발 virtual host의 요청 로그는 비활성화해 주세요. 단순 access_log off만으로 error 로그의 query가 사라지는 것은 아닙니다.
>
> 프록시 설치안은 이 문서와 개발 계정 `~/.local/state/issuedigest/development-https-20261014/administrator-site.conf`에 준비합니다. 기존 서비스 주소·운영 서비스·main 자동 배포와 DB 권한은 변경할 필요 없습니다. sudo 권한 확대나 새 서버/DB는 요청하지 않습니다. 적용 후 주소와 HTTPS/갱신 설정 완료 여부를 알려주시면 실제 외부 응답과 Google 로그인은 제가 이어서 확인하겠습니다.

주소를 바꿔야 하는 사정이 있으면 먼저 최종 주소를 알려준다. 개발자는 API origin·Google callback을 함께 변경한다. 내부18173/18090은 인터넷에 직접 개방하지 않는다.

## Nginx 설치안

다음은 기존 HTTP 컨텍스트의 별도 virtual host 설치안이다. 먼저 DNS와 인증서를 준비하고 인증서 경로를 실제 발급 경로와 맞춘다. 기존 virtual host/default_server를 삭제하거나 덮어쓰지 않는다. HTTP ACME 검증/갱신 경로는 서버의 기존 인증서 관리 방식에 맞춰 추가한다.

```nginx
server {
    listen 80;
    server_name dev.issuedigest.projects.ai.kr;
    access_log off;
    error_log /dev/null emerg;
    return 308 https://dev.issuedigest.projects.ai.kr$request_uri;
}

server {
    listen 443 ssl;
    server_name dev.issuedigest.projects.ai.kr;
    ssl_certificate /etc/letsencrypt/live/dev.issuedigest.projects.ai.kr/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/dev.issuedigest.projects.ai.kr/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    access_log off;
    error_log /dev/null emerg;
    client_max_body_size 1m;

    location / {
        proxy_pass http://127.0.0.1:18173;
        proxy_http_version 1.1;
        proxy_set_header Connection "";
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Proto https;
        proxy_set_header X-Forwarded-For $remote_addr;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_connect_timeout 5s;
        proxy_read_timeout 30s;
        proxy_redirect off;
    }
}
```

Cookie/Origin·Set-Cookie를 재작성하거나 URI prefix를 추가/제거하지 않는다. Basic 인증을 추가하면 OAuth callback에 미치는 영향을 별도 확인한다. 앱 자료 권한은 Google 명시 초대로 제한한다.

운영 관측/로그 설계는 별도 작업이다. 이번 개발 접속에서는 callback 비밀값을 로그에 쓰지 않는다. 관리자는 인증서 준비·설정 추가 후 `nginx -t` 통과를 확인하고 reload한다. 인증서 발급 전 경로로는 TLS 설정 검사가 실패하므로 내부 loopback 설정 검증을 외부 TLS 설정 검증 완료로 취급하지 않는다.

## 사용자 Google 설정과 완료 확인

사용자가 기존 Google OAuth 웹 클라이언트에 아래 승인된 리디렉션 URI 추가 완료를 전달했다. 실제 제공자 반환은 외부 HTTPS 연결 후 검증한다.

```text
https://dev.issuedigest.projects.ai.kr/api/v1/auth/google/callback
```

기존 localhost URI 삭제·secret 재발급은 필요 없다. 웹 인증 코드 흐름의 시작은 서버 form POST이므로 브라우저 JavaScript SDK의 추가 origin 설정을 요구하지 않는다. Audience/Testing 테스트 사용자에는 승인된 Google 계정이 필요하며 아직 실제 제공자 화면에서 확인하지 않았다. 값·secret을 대화/PR/Sites로 보내지 않는다.

관리자 적용 후 개발자가 TLS 검증을 유지한 `/login`·정적 asset·`/health/live`·인증 전session401·잘못된Origin403·정확 callback/보안cookie를 확인한다. 그 뒤 사용자 Google 로그인→승인 공간 자료 목록→원문·인용3개, 미초대/만료/로그아웃을 확인한다. 이전 내부 테스트와 실제 사용자의 완료는 구분한다.

근거: [Nginx 실행·개인 prefix/정적·프록시](https://nginx.org/en/docs/beginners_guide.html), [proxy_pass와 헤더](https://nginx.org/en/docs/http/ngx_http_proxy_module.html), [Google 웹 서버 OAuth·등록 redirect URI](https://developers.google.com/identity/protocols/oauth2/web-server).

## 2026-10-15 · 실제 조사 흐름 반영

개발 주소의 제품 source는 `d6e2df1`이다. 개인 API·정적15파일·DBOS worker를 연결했고 기존 시스템 프록시/TLS·main/운영 배포는 변경하지 않았다. 외부 index/asset7개 일치·login/health200·보호session/research401/no-store·Origin403을 확인했다. 서버에서 실제 모델 요약1건을 호출해 구조/인용 검증까지 확인했으며 실제 사용자 세션을 대신 사용하지 않았다. 자료11건·인용32개·검색20단위, 앱 역할 DDL 제한 유지. 상세 실행/비용/한계는 [조사 개발 인수인계](research-development.md), 전후 백업·별도 소유 DB 복원은 [진행 기록](../docs/planning/progress.md)을 따른다.
