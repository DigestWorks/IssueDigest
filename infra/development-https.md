# 개발 HTTPS 연결 인수인계

2026-10-14 한국 시간. 준비 주소는 `https://dev.issuedigest.projects.ai.kr`이며 DNS/TLS/공개 연결은 아직 완료하지 않았다. [작업·검증 경계](../docs/changes/development-https.md)를 따른다. 기존 `issuedigest.projects.ai.kr`·운영 서비스·main 자동 배포는 유지한다.

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
