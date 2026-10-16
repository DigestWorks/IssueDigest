# 진행 기록


## 현재 작업 · 질문 전용 브리핑 · 2026-10-16

- 작업/요구사항: [D019](decisions.md)·[승인 작업 명세](../changes/question-driven-briefing.md). feat/question-driven-briefing, Task2 기준cdbcf93. 사용자는 질문만 입력하고 결과의 정확 인용에서 원문을 연다. 수동 자료 선택·추천·카탈로그·레거시 자료 관리/검색 화면·범위 선택기·준비 중 안내·자동 중복 원문 블록을 제거했다. 첫 승인 멤버십을 내부 요청 맥락으로 사용하며 기존 세션·현재 권한·정확 인용/검색 계약을 유지한다.
- 구현: 질문/부모/요청ID의 엄격한 전송 검증, queued/무근거실패의 빈 근거와 완료 결과의1개 이상 근거·최대5개 provenance, v1/v2 저장 Canvas를 읽는다. 질문·로그인 복원·중복 제출/동일ID 재확인·실제 단계/취소·후속 질문·기록 GET 재열람을 유지했다. 현재401/403/404에서 Canvas·자료 제목·원문 창·질문 초안을 함께 정리하며 이전 맥락의 늦은 오류와 일시503/네트워크 실패를 구분한다.
- 검증: Node24.21.0에서 전체 JS442개/24파일·린트·타입·SPA빌드·계약 검사 통과. transport RED5→GREEN30, 현재 권한의 stale Canvas/초안 RED3→GREEN8, 권한 재조회/직접 reader 초안 RED4→GREEN9를 확인했다. 이후 자동 원문 블록 삭제에 맞춰 실제 인용 경로의 의미를 유지하도록 기존 검사를 조정했다. 정확 원문/quote/모달 닫기·초점/지연조회·권한·후속·저장 경로와 서버 검색/reader 계약 검사는 보존했다. 낮은 영향 삭제에 absence/cosmetic 테스트를 새로 추가하지 않았다.
- 미검증/남은 입력: 컨트롤러의 최종 독립 리뷰·실제 합성 PostgreSQL/HTTP 및 모바일/PC QA·개인 개발 적용·제한된 실제 모델 검증은 이 Task2 구현 기록에서 완료로 주장하지 않는다. 이전 활성run/workflow가 없는지 확인한 뒤 v2 웹/API/워커를 함께 적용해야 하며 진행 중 작업을 임의 폐기하지 않는다.
- 경계/다음 행동: 현재 저장 색인의 제한된 문자 검색이며 웹 전체/의미 검색·최신 외부 수집·공개 브리핑/개인 소유·추천/알림/공유는 후속이다. 현재 공유 검증 이력을 개인 보관함으로 표시하지 않는다. 실제 자료/계정/키·서버·외부 서비스·운영main 변경은 Task2에서 수행하지 않았다. 컨트롤러가 최종 검증/적용을 이어간다.
- Sites 반영 상태: 대기. 과거 요약/검증 이력을 보존하며 이번 구현자가 Sites를 수정하지 않았다.

## 현재 작업 · B2C 화면·활성 계획·로그인 유지 · 2026-10-16

- 요청과 수용 기준: [D018](decisions.md)·[작업 명세](../changes/b2c-cleanup-persistent-login.md). 질문 중심 B2C 브리핑을 기준으로 기본 자료 메뉴·공동 작업/역할 배지·법안 전용 요약 행동과 옛 활성 계획을 정리했다. 근거 검색·선택·원문/정확 인용·생성·재열람은 유지하며 공유 검증 이력을 개인 보관함으로 표시하지 않는다.
- 구현: 서버 세션 최대14일·미사용7일과 새0006 마이그레이션9ad2cca/d6d05f3, 헤더 아이콘·화면·활성 문서 재편befb97f. 기존 세션 만료일을 연장하지 않으며 보안 쿠키·해시 저장·현재 권한·교체/로그아웃 폐기를 유지한다.
- 검증: 컨트롤러 실제 전용 PostgreSQL2090개·JS493개, Python/JS 린트·타입·빌드·계약 통과. 작업별 독립 검토 통과.390/1440 합성 브라우저에서 아이콘/계정·테마 보존·질문→로그인 초안·자료→원문/인용·브리핑 기록을 확인했고390완료 브리핑/후속질문의 밝은·어두운 화면을 확인했다. 이 검증에서 실제 계정 세션이나 유료 모델 호출을 대신 만들지 않았다.
- 운영 준비: 승인된 두 번째 개발 초대를 비공개 등록·반복 검증했다. 관리자 권한 확대·공개 가입은 없다. 변경 대상 인증 행·세션 제약과 기존 데이터 건수의 비공개 백업/기준을 준비했다. 전체 DB dump가 아닌 이번 인증 변경의 표적 백업이며 공용 DB 테스트 초기화는 하지 않았다.
- 적용: 전체 변경 독립 검토 승인 후 개인 개발 소스f545e752f4dab69842c39b0e405b0e70416c6ab6·0006 세션 제약·API/워커 재시작을 확인했다. 기존 세션 만료일과 자료/신원 건수 보존, 정책1209600/604800초, 정적17파일/이전41자산 보존, 외부 HTTPS/화면·API200/비회원401/no-store/현재6해시 일치를 확인했다. 실제 배포된390/1440 화면·계정 메뉴·질문→로그인도 확인했다. [해당 소스 CI](https://github.com/DigestWorks/IssueDigest/actions/runs/38859480281)는 성공했다.
- 복구 기록: 개인 배포 도구가 PostgreSQL의336시간 표기와 tmux HOME 이스케이프를 잘못 해석해 확인/재시작이 중단됐다. 간격을 초 단위로 검증하고 원래 개인 실행 설정으로 API/워커를 복구했다. 이후 외부 응답·프로세스 생존·새 파일을 다시 확인했다. 제품 코드·운영/main·기존 데이터 변경은 없었다.
- 인계: 동료 실제 Google 첫 로그인은 당사자가 확인한다. 기존8시간 로그인 쿠키는 만료일을 보존했으므로 재로그인 후14일/7일 정책을 적용받는다. 공개 게시·개인 소유/추천·알림과 기존 권한 상실 시 표시 상태 전체 정리는 출시 전 후속이다. Sites v54 요약 게시를 마쳤으며 main/운영 게시는 유예한다.

- Sites: [v54 제품·개발 계획](https://lawdigest-rebuild-plan.ijaesinii.chatgpt.site/) public/native succeeded. source `1d4774572728aa7c4a179cad02c8d70ffa6d8080`, saved `appgprj_6ac612dd42708191a7a0c8377be64d48~appgver_4c615e2913a08191b6ae5a2ad1e4d859`, deployment `appgdep_6ad1c1e5e00c8191b7d783ffef439b13`. 문서 사본5dd8a9a·이전v53 보관·HTML39/내부 링크·자산·앵커1040개/공개 텍스트102파일의 비밀값 제외를 확인했다. 옛 보관 페이지6개의 잘못된 data URI favicon 경로만 보정하고 기록 본문은 유지했다. 사용자의 브라우저 탭을 열거나 이동하지 않았다.


## 현재 작업 · 개발 보조 도구 제거 · 2026-10-16

- 사용자 피드백에 따라 홈 하단의 연결 확인·수동 근거 URL 입력을 제거한다. 실제 자료 목록/검색/브리핑의 근거 열기와 보호 라우트는 유지한다. [범위](../changes/home-tools-removal.md).
- 기준f275e03·기존 Draft PR32 후속. 구현3b8be31로 전용 상태/핸들러/스타일/구식 테스트17건을 정리했다. JS493·린트/타입/빌드/계약 및 작업 검토를 통과했고390/1440 합성 브라우저에서 도구 부재와 실제 자료→원문/정확 인용을 확인했다. 전체 독립 검토를 통과했고 개인 개발 웹81a1c64 반영·외부 HTTPS/정적6해시·배포된390/1440 화면을 확인했다. 새 소스는 기존 Draft PR32에 갱신했고 main/운영은 유예한다. 서버 API·DB·main/운영은 변경하지 않는다.
- Sites 요약은 다음 기록 정리 시 반영 대기다. 이번 작은 화면 정리는 저장소 기록을 원본으로 한다.


## 현재 작업 · 로고·다크모드·로그인 진입 · 2026-10-16

- 요청: 생성 로고, 명시적 테마 전환, 우측 계정 메뉴와 행동 시 로그인. [수용 기준](../changes/brand-theme-entry.md)에 기록했다. 기존 비공개 자료와 자동 유료 실행 경계는 유지한다.
- 기준: feat/briefing-experience의7188d7f에서 별도 feature branch. 기존 격리 worktree를 재사용하며 main/운영 배포를 변경하지 않는다. JS478개 기준 검사를 통과했다.
- 상태: 생성 PNG·명시 테마·계정 메뉴·행동 시 로그인 구현(2c56571). 웹510검사/린트/타입/빌드·계약 검사를 통과했다.320/390/1440 독립 합성 브라우저에서 비회원 초안/진입·테마·저장 브리핑/비교·원문·로그인 페이지 로그아웃을 확인했다. 작업/전체 검토와 계정·로그아웃·401/403 진입 보완 재검토를 통과했다. [Draft PR32](https://github.com/DigestWorks/IssueDigest/pull/32)와 개인 개발 웹ace770f 반영을 마쳤다. HTTPS/정적6해시+로고·보호401/no-store를 확인했다. 외부 독립 브라우저에서도 생성 로고·테마 보존·계정 메뉴·질문→로그인 초안을 확인했다. 제품/검증 기준ace770f의 [CI 전체2557검사](https://github.com/DigestWorks/IssueDigest/actions/runs/38855551075)도 통과했다. Sites v53 요약 게시를 마쳤다. 실제 계정 로그인·모델·DB 쓰기를 대신 실행하지 않았다.
- Sites: [v53 로고·테마·로그인 진입](https://lawdigest-rebuild-plan.ijaesinii.chatgpt.site/#brand-theme-entry) native succeeded/public. source8c5b91b1f74dc4156137d8f5bbbf0e9704ddaf39, saved `appgprj_6ac612dd42708191a7a0c8377be64d48~appgver_6ebfea1363fc8191822d4b450655ff7d`, deployment `appgdep_6ad1b5b83d888191b6337efc7ada671b`. 문서 사본e065769·v52 보존·HTML38/링크1031/공개 텍스트99파일 비밀값 제외 통과. 사용자의 탭은 열거나 이동하지 않았다.
- 인계: 실제 개발 정적 웹은ace770f(제품 코드2c56571). 이후 커밋은 검증/게시 기록이다. 자체 합성 QA 서버·브라우저는 정리하며 feature branch와 Draft PR32는 보존한다. 공개 브리핑/개인화 등 후속 범위는 기존 작업 목록을 따른다.


2026-10-16. 최신 상태는 아래 현재 작업을 따르며 과거 검증 기록을 보존한다. 상태는 문서·코드·검증·운영 증거를 구분한다. 웹·API·상태 계약·개발 자동 검증 기반, 첫 원문·파싱·인용 및 두 번째 개체·주장·관계·비교 조건, 세 번째 실행·화면·사용량 부분 계약을 구현했다. 실제 HTTP·브라우저 스모크 검증을 통과했으며 전체 P1과 제품 기능은 미완료다.

| 단계 | 현재 상태 | 완료 증거·다음 조건 |
| --- | --- | --- |
| P0 계획·기록 | 작성·게시 완료 · 검토 중 | 저장소 조사·사용자 응답·요구사항·설계·작업 목록 작성 |
| P1 기반 | 웹·API 개발 기반 구현 · 전체 미완료 | npm/uv 워크스페이스·상태 계약·자동 검증 통과. 실제 HTTP·브라우저 스모크 통과. 원문·인용·개체·주장·관계·실행·화면·사용량 부분 계약 구현. PostgreSQL 근거 스냅샷 저장·초기 outbox 추가. DB 세션·회원 권한·보호 근거 조회 구현. Google 로그인·명시 초대·자료 목록 구현·합성 검증. 공동 DB 초기 적용 완료. 실제 로그인·나머지 API·이벤트·워커·검색은 미완료 |
| P2 실제 근거 | 첫 이슈 공식 HTML1건 검증 · 등록 도구 준비 | 정부 본문35문단/3,231자·인용3개와 전용 검증 DB 저장 재조회. 기존PDF6개/35문항/87위치는 별도 검사. 첫 코퍼스/평가20문항·표/수치/주장 지지·공동 DB 승인1건 적용 완료, 나머지 자료 이관은 후속 |
| P3 검색·관계 | 문자 검색 SDK 구현·검증 · 전체 미완료 | 불변 근거의 본문/페이지/셀 검색·현재 권한·명시 색인 재생성 검증. 보호 API/화면은 아래 작업에서 연결. pgvector·재순위화·실제 질문 평가/Neo4j는 후속 |
| P4 에이전트·UI | 수동 조사·실제 모델 연결 · 품질 평가 후속 | 자료 선택·PydanticAI/DBOS·생성 모듈·정확 인용·후속 질문·저장/취소 구현. 합성 결합·실제 모델3건·개발 HTTPS 반영 확인. 전체 질문 품질·모듈 스트리밍·관계도/이미지·전체 제품은 후속 |
| P5 공유·이미지 | 미착수 | 저장/권한 경로와 이미지 공급자 필요 |
| P6 운영 검증 | DNS·HTTPS·자동 배포 준비 · 앱 공개 유예 | 서버·전용 DB/pgvector·자료 접근 확인. 최소 제품·비용·권한·운영 연결·별도 복원 검증 후 첫 게시 판단 |
| 이전 와이어프레임 | 코드 보존 · 배포 종료 | Vercel 배포 14개 삭제, Git 자동 배포 연결 해제 |

## 2026-10-13 · 공개 배포 인수인계

- 동료 보고: 공용 checkout·릴리스 개발 그룹 쓰기, main 자동 검사/배포·제한된 배포 SSH, 별도 운영 API 서비스 준비. 개발 브랜치·기존 DB·자료는 변경하지 않음.
- 직접 확인: DNS 정상, 서버와 외부에서 인증서 검증을 유지한 HTTPS `/` HTTP503. 외부 `/health/live`·`/api/v1/status` HTTP502, 운영 API inactive·현재 릴리스 없음. TLS 대기라는 전달 문서보다 HTTPS 연결이 진행됐지만 앱은 아직 게시되지 않았다.
- 최신 main `6d0884e`의 workflow·배포 스크립트·서비스·웹 설정을 읽었다. 개발 코드와의 읽기 전용 병합 미리보기에서 충돌 표시 없음. 통합 커밋·통합 후 검사·main 병합·첫 배포·복구는 아직 수행하지 않았다. 앱 화면은 빈 자료/연결 확인이며 실제 자료·AI·로그인·운영 DB는 후속이다.
- 상세: [공개 앱 배포 상태](../../infra/public-deployment.md). 이 변경은 문서만이며 운영 설정·공용 checkout·자료 변경 없음. 문서3개/상대 링크6개·공개 접속정보 제외·git diff --check 통과. 코드 전체 테스트는 반복하지 않았다.
- Sites: [v32 배포 상태](https://lawdigest-rebuild-plan.ijaesinii.chatgpt.site/#deployment) 공개 게시 native succeeded·URL 확인. source `d71b41cae7e4282453df8d9a910e9b9ddb7f2dc5`, saved version `appgprj_6ac612dd42708191a7a0c8377be64d48~appgver_4b8329f3a14c8191b1b3a35220d84593`, deployment `appgdep_6acde040f0c08191b1b854866d9d7b38`. 사본 기준579e023·이전v31 보존, HTML17개/로컬 링크·anchor248개/manifest/공개 접속정보 제외 통과. 보존본의 상대 링크를 기존 형식에 맞춰 수정 후 재검사했다. 문서 변경의 브라우저 화면 검사는 수행하지 않았다. 서버 개인 worktree도 문서만 fast-forward하며 운영 앱을 게시하지 않는다.

## 현재 작업 · B2C 브리핑 경험 첫 연결 · 2026-10-16

- 기준: [승인 인터뷰](../research/product-experience-interview.md)와 [첫 실제 연결 명세](../changes/briefing-experience.md). feat/briefing-experience, base feat/assembly-source-connector/e8c7b0a. B2C가 목표이며 두 사람은 초기 검증 참여자다(D016). 기존 linked worktree를 재사용한다.
- 구현: 질문 우선 홈·초대 로그인 초안·편집 후 명시 실행, 직접 선택/제한적인 연결 자료 후보, 현재 선택 원문의 정확 인용 선열람, 검증된 실제 AI 모듈의 브리핑·모바일 주장별 비교, 본문을 떠나지 않는 정확 원문 창을 연결했다. 기본 Canvas 계약·기존 저장/후속/멱등성/취소/예산은 유지한다. 공개 최근 이슈나 가짜 AI 결과를 채우지 않는다.
- 구분: 생성 중 먼저 보이는 것은 원문 인용이다. AI 부분 답변·전체 검색 이력·확인된 사실이 아니다. 현재 AI 주장 basis는 해석 그대로 표시하며 UI가 사실·찬반 분류를 만들지 않는다. 저장한 조사는 공동 조사 기록이지 개인 비공개 북마크가 아니다.
- 검증: Task1/2 작업 독립 검토와 보완 재검토 승인. Python2047/skip0·Ruff189·mypy83, 최종 웹478/25파일·lint/type/build/contract 통과. Python은 이번 UI 변경이 없어 같은 작업의 검사를 반복하지 않았다. 전체 검토의 초안 재등장·늦은 원문 응답2건과 저장 개별 조회 피드백을 RED8→GREEN8로 보완하고 scoped 재검토 C0/I0/M0을 확인했다. 합성 HTTP+소유 PG/FunctionModel 브라우저에서 질문 복원/조사0, 무관 질문 실행0, 원문→완료 모달 유지·정확 mark/Escape/초점 복귀, 320/390/1440 비교 가로넘침0, 실패/취소 원문 유지, viewer 생성 비활성, 저장 재열람 추가모델0을 확인했다. 실패→새 조사 즉시 입력 보존·지연된 목록404 뒤 원문/모달 삭제도 새 빌드 브라우저로 재확인했다. 최종 새 브라우저에서 guest reset→B→A/POST0, 늦은 A 조회→B 유지/닫힘 유지, 저장 GET의 loading→503→동일 GET 재시도2회도 확인했다. 권한404/일시503 주입과 원문 응답 지연 외에는 실제 합성 API/DB다. 실제 OAuth 제공자 로그인·실제 모델 추론 품질 검증이 아니다.
- 판단: HTTP403을 기존 클라이언트 권한 오류로 구분하고 현재 보호 리소스404도 원문을 닫는 조건으로 다룬다. 기존 backend가 회원권 상실에404를 쓰기 때문이다. 기존 원문 화면의403 안내가 로그인/권한 안내로 바뀌고, 실제 자료 누락/일시404라도 닫힌 원문은 성공한 재조회가 필요하다. HTTP/스키마·DB·워커 계약은 바꾸지 않는다.
- 개발 적용: [개발 앱](https://dev.issuedigest.projects.ai.kr/)의 정적 웹 source35a530a 반영, 파일16개/이전 asset9개 유지·개인 Nginx reload. 외부 TLS·홈/login/health/status200·session/research401/no-store, 현재 asset7개의 로컬 빌드 일치와 기존 asset7개의 같은 바이트를 확인했다. 기존 API/worker·TLS/시스템 프록시·자료·비밀 설정 유지, DB쓰기/migration·실제 사용자 세션 대행·유료 모델 검증·main/운영 게시0. [Draft PR31](https://github.com/DigestWorks/IssueDigest/pull/31), base feat/assembly-source-connector. Sites v52 public/native succeeded, 이전v51 보존. source56d070e744fd470eb5a509b141d9dbdb0c2051fb, saved appgprj_6ac612dd42708191a7a0c8377be64d48~appgver_08fcb4f6351881918e5f38180f209918, deployment appgdep_6ad1a3ddff84819188daf00100cc762c. 사본기준83e81f0, HTML37/로컬링크·anchor984/공개텍스트97의 실제 비밀값 제외 검사 통과. 사용자 브라우저 탭을 열지 않았다.
- 후속: 공개 게시·공유 불변 브리핑, 개인 관심 이슈/변경·알림, 실제 주목도·개인화, 검증된 AI 모듈의 점진 전달. 공개 이슈 범위·외부 탐색 범위·초기 AI 이용 정책은 답변 대기다. 현재 자료12건을 공개 브리핑12개나 최근 인기 이슈로 표시하지 않는다. 권한 상실 시 현재 원문 미리보기/창은 지우지만 이미 표시한 Canvas/자료 제목 전체 정리는 공개 출시 전 후속으로 남긴다.

## 이전 작업 · 수집 연결·제품 경험 인터뷰 · 2026-10-16

- 범위: [첫 국회 원문 연결기](../changes/assembly-source-connector.md), [제품 경험 인터뷰](../research/product-experience-interview.md). feat/assembly-source-connector, base feat/research-journey/2439385. 기존 linked worktree를 유지하며 새 branch에서 진행한다.
- 읽기 조사: 기존 MySQL Bill41,004·제안일2020-06-01~2026-07-10 확인, SELECT만 수행했다. 행수/상한은 현재 수집 실행의 정상·최신성을 보장하지 않는다. 기존 Airflow는 검토 코드의 폐기 경로이며 실제 활성 실행기는 추가 확인 대상이다.
- 구현: 공개 국회 상세 GET/읽기 POST의 고정2요청·TLS/크기/형식/비밀로그 제한·정확 요약 추출과 private capture→기존 승인 등록 계획의 offline 연결을 구현했다. 실제 공식 원문487자를 수집하고 정확 인용1개를 준비했다. 원문과 관계없는 footer 구조 문제·숨김/native context 반영 문제를 RED회귀→보완·독립 검토로 해결했다. 재수집의 문서 변경 판정·정기 수집·전체 처리 이력/변경 감지/알림은 이번 완료가 아니다.
- 실제 연결: 기존 앱 역할로 제안 내용1건/인용1개를 추가해 총자료12·인용33·검색21단위/outbox12. 기존11건의 hash·계정/초대/권한·세션 보존, 반복 신규0. schema/DDL·legacy쓰기·실제사용자 세션 대행·모델호출0. 기존 개인 API/웹/조사worker는 재시작하지 않았다. 신규 수집기가 상주/예약 실행되는 상태는 아니다.
- 검증: controller 별도 소유 PG18.6 전체 Python2047개/skip0, JS408개·Ruff188파일/mypy83·TypeScript/빌드/계약 통과. 독립 작업/보완/전체/최종 보완 재검토 C/I/M0. 실제GET/POST2회·265262바이트capture, 본문487자·canonical 인용·같은artifact반복추가0 확인. 앞선GET 호환 실패와 controller의 잘못된 로컬base경로 참조는 적용 전에 교정했으며 실제DB 부분쓰기0이었다.
- 백업: 적용 전후 서버 외부 full/app archive 보존. 적용 후 앱 archive를 별도 소유 PG18.6에 복원해 자료12/인용33/검색21·기존11hash와 실제auth행 보존·기존/신규 canonical bundle·합성 신원 보호catalog12/다른공간/미인증/viewer생성거부를 확인했다. 이후 자체컨테이너/익명볼륨을 제거했다. 원래사용자의 세션은 대신 사용하지 않았다. 외부TLS·동일기존웹빌드/asset7개·login/health200·보호401/Origin403도 확인했다. 프런트 코드는 그대로이며 새로운관심이슈/생성UI를 배포한것이아니다. 실제 DB 테스트/초기화/복원·운영 원본/MySQL·공용 checkout·main은 변경하지 않는다.
- 인터뷰: 질문 우선+최근 이슈 탐색, 사실/주장/미확인 요약, 여론조사/언론/온라인 반응 구분, 근거 부족을 솔직히 인정하는 AI 어조를 사용자 답변으로 기록했다. 30초 요약·결과 중심 동적 화면·관심 이슈 저장/변화→후속 탐색→공유·휴대폰 중심·최신 전체 요약의 변경 표시·새 사실/공식 결정/정정 우선까지 답변을 받았다. 여러 매체의 새 보도 기반 최근 이슈·중요 변화 발생 시 알림 선호, ChatGPT의 위젯/에이전트 경험과 Linear/Toss/Apple 수준의 정돈·마감 선호도 기록했다. AI가 자료 탐색→비교/시각화까지 자율 진행하는 선호도 확인했다. 우선 모듈·구체적인 불만은 추가 질문 중이다. 제안과 확정 답변을 구분하며 새 UI는 아직 구현하지 않는다.
- 인계: [Draft PR #30](https://github.com/DigestWorks/IssueDigest/pull/30), 기준제품 코드912854f·문서a413b46의 [CI 성공](https://github.com/DigestWorks/IssueDigest/actions/runs/38838392607). 서버 개인 checkout도a413b46으로 동기화하고 수집/준비 entrypoint2개를 설치했다. 앱/워커 재시작·정기 수집 시작·main/운영 게시 없음.
- Sites: [v50 제품 경험 인터뷰·첫 연결기](https://lawdigest-rebuild-plan.ijaesinii.chatgpt.site/#product-experience) public/native succeeded. source `ee61a05a320aa203cc5578bc2e347d2a576f881f`, saved `appgprj_6ac612dd42708191a7a0c8377be64d48~appgver_77be20c2049c8191b3ebebecde763ae2`, deployment `appgdep_6ad186d11a0c819195a52504ced7d6c2`. 이전v49 보존·사본기준a413b46·HTML35/로컬 링크anchor892/공개 텍스트94개와 실제 비밀값/계정/원문 제외 검사 통과. source동기화의 일시DNS실패는 복구 확인 후 같은소스/프로젝트로 재개했다. 브라우저 탭을 열지 않았다.
- 정리: 자체 PG 검사/복원 컨테이너·익명볼륨을 제거하고 private capture·job·계획·전후dump·리뷰를 보존했다. SDD 스크래치만 비공개 보관 후 정리하며 PR 작업용 linked worktree는 유지한다. 인터뷰는 계속 진행 중이고 신규UI 배포로 표시하지 않는다.

## 이전 작업 · 첫 조사 흐름 · 2026-10-15

- 범위: [명세](../changes/research-journey.md), [실행·비용·검증 경계](../../infra/research-development.md), feat/research-journey, base feat/workspace-clarity-legacy/5fd3824. 사용자 승인 범위는 자료 선택→질문→생성 결과→정확 원문→자동 저장·재열람이다. main/운영 게시 유예(D013)를 유지한다.
- 화면: **이슈 조사 / 자료 / 저장한 조사**. 실제 자료 제목·의안번호·제안일로 고르고 법안 핵심 정리·질문을 시작한다. 접수/검색/분석/인용 연결 확인과 취소·실패·연결 대기·한도를 구분한다. 질문 전에는 AI 결과를 표시하지 않는다. 생성된 해석·검증된 인용 위치·원문을 구분하고 후속 질문·같은 결과 재열람을 연결했다.
- 실행: PydanticAI2.56.0/DBOS3.2.0, gpt-5.4-mini Responses/store=False, PG migration0005. 명시 DBOS 초기화·앱 DDL 제한·내구 checkpoint·현재 권한·idempotency·월 글로벌 USD10/최대40건 보수적 예약. 새로고침/완료 GET은 모델 호출0, 응답 유실 구간의 정확히 한 번 과금은 보장하지 않는다.
- 자료 연결: [기존 법안 내용·이력 대조](../research/bill-history-reuse.md). 최근 기본 정보8건의 수집 이력0건을 확인했다. 별도21대 법안2건의 원본 제안 내용400/422자와7개 과거 날짜/단계 문구를 국회 원문과 대조하고 정확 인용13개를 준비했다. 과거 자료/최신 상태/전문을 구분하며 기존9건의 불변 hash·계정·초대·권한을 보존한다. 개발 DB에2건/인용13개를 추가해 총11건/인용32개/검색20단위를 연결했다. 반복 적용 신규0, 기존9건과 계정·권한·세션 보존을 확인했다.
- 검증: controller 전체 Python1,888+JS408=2,296개, skip/warning0·Ruff178/mypy77·TypeScript/빌드/계약 통과. 작업별 독립 검토/보완 재검토 C/I/M0. 합성 신원·실제 자료 복원본·실제 HTTP/PG/DBOS·합성 FunctionModel 브라우저에서 요약/비교/타임라인·진행 상태·정확 원문 선택·후속 질문·저장 재열람·새로고침 POST0·취소·실패·390px 가로 넘침0/pageerror0 확인. 타임라인 JSONB 날짜 재열람과 요청 중 선택/취소/Back/Forward 상태를 회귀 검증으로 보완했다. 전체 독립 검토·보완 재검토·실제 결과 표시/접근성 검토 C/I/M0. 실제 결과 1365/390px·원문 재진입·추가 POST0/pageerror0 확인.
- 실제 AI: 승인 키를 저장소 밖600권한으로 준비했다. 별도 소유 DB·실제 자료·합성 신원의 HTTP/PG/DBOS 흐름에서 gpt-5.4-mini 고정 질문3건의 요약·비교·타임라인과 정확 원문·저장/재열람을 확인했다. 선택1/2/2자료의 주장3/2/7개가 모두 선택 자료를 인용하고7개 과거 날짜가 원문 인용과 일치했다. 첫 제공자 응답의 보조 메시지 중복으로 실패한1건은 보존하고 반환 투영·선택/관련 자료 구분·알려진 사용량 보존을 보완했다. 실제 응답4회 합계 입력8499/출력1572토큰이며 청구액을 조회한 결과는 아니다. 실제 사용자 세션을 임의 발급/재사용하지 않았다.
- 품질 한계: 이3건은 실행/저장/정확 위치/모듈 차이를 확인한 표본이다. 타임라인 질문의 전체4항목 요청을 법안별4/3개로 표시한 사례가 있어 길이·개수 지시 준수 평가는 후속이다. 인용 일치는 주장 지지/법적 효력 검증이 아니며, 전체20문항·두 사용자의 상품적 품질/운영비 평가는 미완료다.
- 개발 반영: [개발 앱](https://dev.issuedigest.projects.ai.kr/) 제품 source `d6e2df1`·정적15파일/source map0, 개인 API/DBOS worker·앱 역할 DDL 제한·migration0005 연결. TLS 검증을 유지한 index/asset7개 빌드 일치·login/health200·미인증session/research401/no-store·잘못된Origin403 확인. 서버에서도 별도 고정 질문1회를 검증해 입력1064/출력267토큰·요약/근거 모듈을 확인했다(실제 사용자 세션/DB 쓰기0).
- 백업/복구: 적용 직전과 적용 후 서버 외부 full/app archive 보존. 별도 소유 PG18.6에 적용 후 app archive 복원, 자료11/인용32/검색20·DBOS schema·새 canonical bundle2·기존 계정/세션 건수 보존, 합성 신원으로 보호 catalog11·비회원/다른 공간/viewer생성 거부 확인. 실제 DB를 초기화/복원하지 않았다. 전체 역할·확장·운영 복구 검증은 별도다.
- 인계: [Draft PR #29](https://github.com/DigestWorks/IssueDigest/pull/29), [제품 코드 CI 성공](https://github.com/DigestWorks/IssueDigest/actions/runs/38732066902). [Sites v49](https://lawdigest-rebuild-plan.ijaesinii.chatgpt.site/#research-journey) 공개 게시 native succeeded. source `eee84956564eb2d29c6d18ddf15db61ffd52bb58`, saved version `appgprj_6ac612dd42708191a7a0c8377be64d48~appgver_0057c22d36cc81919ff55d2c65963dcf`, deployment `appgdep_6ad0c52ac25c8191b400fea83ef699d5`. 이전v48 보존·사본 기준65a4e9c·HTML34/로컬 링크·anchor847·공개 텍스트90개 비밀값/계정/원문 제외 확인. 기존 브라우저 탭은 열지 않았다. 운영 원본/MySQL·공용 checkout·시스템 서비스·main은 변경하지 않는다. 비밀값·실제 계정·개별ID·원문은 비공개 검증 위치에만 둔다.

- 정리: 자체 합성 브라우저·API·worker 종료, 이미지/전체ID/작업label/loopback 포트 대조 후 자체 QA·복원 컨테이너/익명 볼륨 제거. 실제 모델 결과·검증·전후 dump·리뷰 기록은 비공개에 보존한다. 서버 개인 개발 앱/worker는 유지하며 문서 인계 커밋은 제품 코드를 변경하지 않는다.

## 이전 작업 · 자료 중심 UI·기존 법안 연결 · 2026-10-15

- 범위: [작업 명세](../changes/workspace-clarity-legacy.md), R2/R3/D011/D015 유지. feat/workspace-clarity-legacy, base feat/evidence-search-ui/b94c7fb. 격리 worktree·OpenSpec root=null·작업별 구현/독립 리뷰를 적용한다.
- UI: 검색→자료→원문/인용이 중심인 작은 작업 공간으로 정리한다. ID/정밀 시각·개발 진단은 보조 상세로 옮기고 기본 자료 유형/날짜/읽기를 우선한다. 실제 AI 답변·생성 UI 미연결 상태를 명시한다.
- 자료: 기존 MySQL Bill을 SELECT만 하여 고등교육·등록금 관련8건을 선별했다. 제안일2026-03-30~2026-06-22, 원문 링크8건에서 HTTP200·국회 host·법안명/원천ID 대응 확인. 기본 메타데이터만 추가하며 전문/AI 요약/현재 처리 상태를 새로 검증했다고 표시하지 않는다. 원문/개인 ID/계정은 비공개에 보관한다.
- 재검사: 기존 parsed JSON840/PDF774, 연결 후보225·격리384·미지원231·PDF 헤더 없음23으로 확인했다. 이 집계는 원문·인용·이용 조건 검증이 아니므로 PDF 본문 등록은 보류한다.
- 검증: 전체 Python1,853+JS365=2,218개·skip/warning0·Ruff162/mypy69/TS/빌드/계약·독립 작업/전체 검토 C/I/M0. 합성 실제 HTTP/PG 브라우저에서 검색→위치→PDF/표/인용·새로고침·390px·로딩/재시도/빈 결과·로그아웃401, pageerror0(의도한503 console1) 확인.
- 실제 추가: 기본 정보8건/인용16개를 기존 앱 역할/초대로 개발DB에 추가. 총자료9/인용19/outbox9, 자료9건 전체 색인·총16단위. 반복 신규0, 기존 공식 자료·계정/초대/권한·세션 보존. schema/권한/legacy 쓰기/AI 호출 변경 없음.
- 백업/조회: 전후 서버 외부 full/app 백업·소유 loopback DB 앱 복원/새8 bundle 대조. 복원본의 별도 합성 계정으로 보호 목록9·GET8·검색8 및 다른 공간/권한·세션 폐기 거부. 실제 사용자 세션을 생성/대신 사용하지 않았다.
- 개발 앱: 2026-10-15 18:46 KST source0116885·정적14파일/source map0 반영. 외부 TLS·index 빌드 일치·home/login/asset/health/status200·미인증session/search401/no-store. 사용자 본인의 자료/검색 확인은 남아 있다. main/운영 배포 유예·시스템/공용 checkout 유지.
- 인계: [Draft PR #28](https://github.com/DigestWorks/IssueDigest/pull/28) 게시·앱 첨부. 공개 [Sites v48](https://lawdigest-rebuild-plan.ijaesinii.chatgpt.site/#workspace-clarity) native succeeded·source34492f9, 이전v47 보존·사본 기준c446d0d·HTML33/로컬 링크803/공개 텍스트86개 실제 비밀값/UUID/개별hash/원문 제외 확인. 브라우저 탭은 열지 않았다. 새 키/관리자 권한 요청은 없다.
- 정리: 브라우저/합성 API 종료·소유/이미지/label/loopback 포트 대조 후 전용 QA 컨테이너와 익명 볼륨/복원 자료를 제거했다. 실제/합성 검증 증거·private 계획·전후 dump는 개인 위치에 보존한다. 개발 문서·PR·Sites를 갱신하며 마지막 저장소 인계 commit은 코드/자료/운영 설정을 바꾸지 않는다.

## 이전 작업 · 보호 근거 검색 API·화면 · 2026-10-15

- 작업/담당: [검색 인터페이스](../changes/evidence-search-interface.md), R2/R3·D011/D015. controller/구현자·feat/evidence-search-ui, base docs/development-https-audit/edfa66f. 격리 worktree·OpenSpec root=null, 기존 SDK를 소비한다.
- 현재: 보호 JSON POST·typed client·작업 공간 검색 화면·검증된 원문 위치 reader 연결을 구현했다. Task1 검토에서 JSON 날짜/마이크로초/출력 메타데이터 한도와 async DB 호출을 보완했고 재검토를 통과했다. Task2 검토 승인 후 새로고침 문서/coverage 표시를 정리했다. 전체 변경 독립 리뷰 Critical/Important0, Minor1 문구 보완 후 재검토 승인. [Draft PR #27](https://github.com/DigestWorks/IssueDigest/pull/27) 게시·앱 첨부, 개발 앱 갱신·Sites v47 게시·개발 인계 완료다. 의미 검색·AI 생성·스키마 변경은 이번 범위가 아니다.
- 개발 접속: 2026-10-15 17:04 KST에 권한DNS4곳/Google/Cloudflare 일치·실제 HTTPS 인증서 검증 정상. login/asset/health200·미인증session401·Origin403·Google start/브라우저 결합 취소303·callback/PKCE/보안cookie·외부 로그 차단을 확인했다. 앞선 DNS 불일치/TLS 대기는 해소됐다. [상세](../../infra/development-https.md).
- 실제 로그인: 이번 읽기 전용 DB 확인에서 실제 identity·작업 공간 membership·세션 기록·초대 subject 바인딩의 존재를 확인했다(개별 값은 비공개). 실제 Google 로그인 후 저장 상태가 생성됐으며, 사용자 화면의 원문/인용 열람·오류 상태/로그아웃 완료는 아직 확인하지 않았다. main/운영 배포 유예는 유지한다.
- 검증: controller 전체 Python1,808개·Ruff format159/mypy68, JS363개·lint/TypeScript/SPA/OpenAPI 통과(2,171개, skip/warning0). 마지막 표시 정리 후 관련64개·검색9개와 정적/빌드 재검사 통과. 별도 소유 PostgreSQL과 실제 HTTP API의 합성 브라우저 여정으로 text/emoji/결합문자·PDF 실제 페이지·전체 표 셀·기존 인용·새로고침 재검증·loading·503 후 재시도/빈 결과·390px 가로 넘침 없음·로그아웃401 확인. pageerror0, 의도적으로 주입한503 네트워크 console 오류1개는 실패 UI 검증이다. 실제 제공자 호출/공동 DB 합성 쓰기 없이 수행했다. Sites v47 게시 완료이며 기존 탭을 열지 않았다.
- 개발 앱: 2026-10-15 18:04 KST, 제품 source fd26683·서버 고정 도구/lockfile 빌드14파일/source map0. 개인 API 재시작·개인 정적 Nginx root 갱신/reload 후 실제 HTTPS index가 해당 빌드와 byte hash 일치, home/login/asset/health200·미인증 session/search401/no-store 확인. 기존 schema0004·승인 자료1건/인용3개·초대 바인딩·DDL 없는 앱 권한 유지. 시스템 Nginx·DB schema/승인 자료·main/운영은 변경하지 않았다. 실제 사용자 검색/원문 열람 품질은 개발 앱에서 확인한다.
- CI: [fd26683 전체 검사 성공](https://github.com/DigestWorks/IssueDigest/actions/runs/38710036436). 이후 문서/게시 metadata는 제품 코드와 구분한다.
- Sites: [v47 근거 검색·개발 접속](https://lawdigest-rebuild-plan.ijaesinii.chatgpt.site/#evidence-search) native succeeded/public. source `08a39ab63573112d0c62fe7e86406b8c449ac667`, saved `appgprj_6ac612dd42708191a7a0c8377be64d48~appgver_cc4108a53ab0819180dea991bf1803d0`, deployment `appgdep_6ad0981ad0748191b2a67f3a4a2badcc`. 사본 기준cff9eee·v46 보존·HTML32/로컬 링크·anchor760·공개 텍스트84파일 실제 비밀값/계정/개별ID 제외 통과. 문서 요약의 새 Site 브라우저 검사는 수행하지 않았고 기존 탭을 열거나 이동하지 않았다. 제품 브라우저 검증은 위 별도 기록을 따른다.

## 이전 작업 · 개발 HTTPS 외부 연결 점검 · 2026-10-15

- 작업/담당: [개발 HTTPS 인수인계](../../infra/development-https.md)의 관리자 적용 후 실제 외부 확인. controller·docs/development-https-audit, baseops/development-https/a54e98c. 제품 코드 변경 없음.
- 확인: 관리자 HTTP80 virtual host→내부18173 설치. 정확 Host·DNS 우회 읽기 검사에서 login/health200·미인증session401. 실제 서버 내부 웹/API는 응답한다.
- 미완료: 개발 주소는 OS/Google/Cloudflare와 권한DNS2곳(ns1/ns2.hosting.co.kr)에서 NXDOMAIN. 서버 직접 연결/SNI·정상 인증서 검증은 hostname mismatch62, 개발 host에443/TLS 미설정. 전역 access/error 로그를 상속하며 개발 host의 OAuth 로그 차단 미반영이다.
- 다음: 활성 projects.ai.kr DNS 존에서 dev.issuedigest 레코드 확인·개발 TLS/443·callback 로그 정책 반영을 동료에게 추가 전달. 사용자 Google callback 추가 완료 기록은 유지한다. 해당 조건을 만족한 뒤 실제 HTTPS/Google 로그인·자료 열람을 검증한다.
- 범위: 읽기 조사만 수행. 인증서 검증 우회/HTTP Google 로그인·OAuth start/callback·서버/앱/DB/권한/main 변경 없음. 새 사용자 입력은 DNS/TLS 적용 결과이며 비밀값을 요청하지 않는다. 문서 상대 링크25개·실제 비밀값/계정/개별ID 제외·diff 검사를 통과했다. [Draft PR #26](https://github.com/DigestWorks/IssueDigest/pull/26) baseops/development-https·앱 첨부. 제품 코드 변경 없어 전체 테스트를 반복하지 않았다.
- Sites: [v46 개발 HTTPS 점검](https://lawdigest-rebuild-plan.ijaesinii.chatgpt.site/#development-https) native succeeded/public. source `be426d9bc8644aa6d498161273b0a5d4378752fb`, saved `appgprj_6ac612dd42708191a7a0c8377be64d48~appgver_f6d298c1216481919bf24117705d9f70`, deployment `appgdep_6ad06f3bdf34819197e4b6dc0d9dea74`. 사본 기준87123d0·v45 보존, HTML31/로컬 링크anchor718/manifest·Site공개69파일 비밀값 제외 통과. 첫 source helper 열기는 Git 호스트 DNS 오류로 중단됐고 호스트 재조회 후 같은 Site/credential로 정상 재개했다. 문서 요약의 새 브라우저 검사는 수행하지 않았고 사용자 요청대로 Site를 다시 열지 않았다.
- 인계: 서버/앱을 변경하지 않으며 현재 읽기 점검 문서 branch의 사용자 폴더·서버 개인 worktree 동기화는 마무리 중이다.

## 이전 작업 · 고정 HTTPS 개발 접속 준비

- 작업: [고정 HTTPS 개발 준비](../changes/development-https.md), [관리자 적용/요청](../../infra/development-https.md). controller·ops/development-https·baseops/google-login-runtime/95b7bff. 제품 코드·API/DB 스키마·의존성 변경 없음. Sites는 갱신하되 사용자가 이미 열어 둔 탭을 다시 열거나 이동하지 않는다.
- 준비: dev.issuedigest.projects.ai.kr의 별도 개발 origin. 개인 정적 빌드12파일/source map0·개인 Nginx loopback18173→기존 개인 API18090, Vite/HMR 외부 노출 없음. 개인 API의 origin과 기존 Google client/app 역할을 연결했다. 설치 Nginx의 미지원 CLI 옵션은 설정 검사에서 발견해 호환 명령으로 검사·기동했고, 시스템 로그/권한 변경 없이 개인 prefix를 사용한다.
- 검증: 내부 SPA/login/assets200·없는asset/dotfile404·health200·미인증session401·과거Origin403·새originstart/취소callback303와 callback/PKCE/nonce/보안cookie. 검사 후 승인자료1/인용3/초대1·실제auth user/session/member/flow0·앱DDL 없음. 내부 HTTP Cookie 전달은 TLS 종료 뒤 proxy 동작 검사이며 공개 TLS·사용자 브라우저 로그인 증거가 아니다.
- 대기: 개발 주소 DNS/TLS/공개 Nginx는 아직 없거나 미검증이다. 사용자는 Google callback 추가 완료를 전달했고 실제 제공자 반환은 외부 HTTPS 후 검증한다. 시스템 Nginx는 읽기만 가능하고 sudo 권한 목록 조회도 허용되지 않아 직접 설치하지 않았다. 관리자에게 기존 서버의 개발 virtual host 연결만 요청한다. 새 자원·DB/권한·sudo 확대·main 병합/운영 앱 배포는 요청하지 않는다.
- 사용자 입력: 기존 Google OAuth 웹 client에 `https://dev.issuedigest.projects.ai.kr/api/v1/auth/google/callback` 추가 완료 전달. 실제 외부 HTTPS 후 사용자 Google 로그인/자료 목록/원문·인용3개 확인. 비밀값 재발급/대화 공유 없음.
- 다음: 관리자와 사용자 설정 반영을 받은 뒤 인증서 검증을 유지한 외부 접속과 실제 사용자 여정 확인. 독립 운영/문서 검토C/I/M0·상대 링크87개·공개303파일 실제 비밀값/계정/개별ID 제외·diff 검사를 통과했다. [Draft PR #25](https://github.com/DigestWorks/IssueDigest/pull/25) baseops/google-login-runtime·앱 첨부. 제품 코드는 바꾸지 않아 전체 테스트를 수동 반복하지 않았고 서버 정적 빌드와 실제 내부 응답/flow를 새로 검증했다.
- Sites: [v45 개발 HTTPS](https://lawdigest-rebuild-plan.ijaesinii.chatgpt.site/#development-https) native succeeded/public. source `662b8ca6cc3768fa8ad0742fdf9c86e5de26b923`, saved `appgprj_6ac612dd42708191a7a0c8377be64d48~appgver_03393bc90128819198b961784da0bf53`, deployment `appgdep_6acf4d9a63dc81918ed642d29174165a`. 사본 기준5d61671·v44 보존·HTML30/로컬 링크anchor677/manifest 통과. 요약 변경의 브라우저 검사는 수행하지 않았다. 사용자 요청대로 Sites를 다시 열거나 탭을 이동하지 않았다.
- 개발 인계: 개인 nginx/API·자산/비밀 loader를 후속 HTTPS 연결용으로 유지한다. 공용 자원·운영 서비스·실제 Google사용자/세션을 변경하지 않았다. 사용자 폴더/서버 개인 worktree를 ops/development-https/origin 추적으로 연결하고 같은348841f·깨끗한 Git 상태를 확인했다. [기록 기준5d61671 CI 성공](https://github.com/DigestWorks/IssueDigest/actions/runs/38543640234)을 확인했으며 이후 게시/인계 문서 커밋과 구분한다.

## 이전 작업 · 실제 Google 로그인 개발 연결

- 작업: [개발 runtime 연결](../changes/google-login-runtime.md), R1/D015. controller·ops/google-login-runtime, baseops/database-bootstrap/44f7562. 제품 코드/API·스키마·의존성 변경 없음.
- 결과: 서버 개인 API에 기존 DDL 없는 앱 DB 계정과 승인 Google 설정을 주입했다. head0004·공식 자료1건/인용3개/초대1건 유지. 개인 SSH/HTTPS로 로그인/health200·미인증session401·잘못된Origin403·실제start/취소callback303·PKCE/nonce/cookie/flow 소비를 확인했다. 실제 사용자/세션/회원0이다.
- 사용자 확인: 자체 서명 인증서 예외를 둔 인증 전 브라우저 QA와 달리 사용자 앱 내 미리보기는 ERR_CERT_AUTHORITY_INVALID로 차단되고 포트도 변경됐다. 실제 Google 로그인·자료 목록/인용 열람은 대기다. 원격localhost 안내를 정정하고 사용자 SSH/인증서 설정 요구를 중단했다. 고정HTTPS 개발주소가 필요하며 설치된 Nginx 설정은 읽기만 가능하고 수정 권한은 없다. runtime 응답을 사용자 접속 완료로 간주하지 않는다.
- 다음: 고정HTTPS 개발주소·프록시/인증서·등록 callback을 준비한 뒤 사용자 첫 Google 로그인→자료 목록→원문/인용을 확인한다. 현재 공개 앱·운영 서비스·main은 변경하지 않는다. Google Audience/test-user 오류는 실제 제공자 화면을 확인한 뒤 필요한 항목만 안내한다.
- 검토·기록: 독립 운영/문서 검토C/I/M0·상대 링크48개·공개 파일299개의 실제 비밀값/계정/개별ID 제외·diff 검사 통과. [Draft PR #24](https://github.com/DigestWorks/IssueDigest/pull/24) baseops/database-bootstrap·앱 첨부. 제품 코드 변경 없어 전체 테스트를 수동 반복하지 않았다.
- Sites: [v44 실제 로그인 연결](https://lawdigest-rebuild-plan.ijaesinii.chatgpt.site/#google-login-runtime) native succeeded/public. source `b9a63e8ff849c25b2297cef13bbc0a9e4f4feba7`, saved `appgprj_6ac612dd42708191a7a0c8377be64d48~appgver_8c1bab7b07a88191a2a622c79e9a4532`, deployment `appgdep_6acf45cac25c8191abb1ccb00524adb4`. 사본 기준2b73886·v43 보존·HTML29/로컬 링크anchor637/manifest·Site공개65파일 실제 private 값 제외 확인. 계획 문서 요약의 새 브라우저 화면 검사는 수행하지 않았다.
- 정리: 실패한 localhost preview의 소유 controller를 확인하고 종료해 SSH/HTTPS 자식 프로세스·QA브라우저를 정리했다. 서버 개인 configured API와 private 설정은 후속 개발용으로 유지한다. 공개 앱 배포나 사용자 접속 완료가 아니다. 사용자 폴더/서버 개인 worktree를 ops/google-login-runtime/origin 추적으로 연결하고 같은219e2ed·깨끗한 Git 상태를 확인했다. [기록 기준2b73886 CI 성공](https://github.com/DigestWorks/IssueDigest/actions/runs/38539567880)과 이후 게시/인계 문서 커밋을 구분한다.

## 이전 작업 · 공동 개발 DB 초기 적용

- 작업: [공동 DB 적용 기록](../changes/shared-database-bootstrap.md). 기존 명시 migration/승인 등록 도구를 실제 전용 DB에서 실행했다. 담당 controller, `ops/database-bootstrap`·base feat/evidence-search/d700182. 제품 코드 변경 없음.
- 결과: PG18.6/vector0.8.7 유지, revision0004·public15테이블. 기존 개발/앱 역할 분리·필요 DML/앱 DDL 부재를 실제 검증했고 권한/계정/설정 변경 없음. 승인 공식 자료1건/인용3개/초대1건/outbox1건·검색8단위, 등록/투영 반복에서 중복0·unchanged. 실제 사용자/세션/회원/로그인 flow0이며 승인 초대는 미바인딩 상태다.
- 복구: 전/후 full+app archive를 서버 밖 개인 경로에 보존하고 앱 범위를 별도 소유 PG18.6에 복원했다. canonical 전체·승인 초대·outbox·검색 투영 대조 통과. vector 바이너리/역할·전체 서버 복구/정기 백업 완료는 아니다. 원문 bytes/승인 입력은 별도 개인 경로에 유지한다.
- 검증: 서버 실제 CLI offline/check/apply/repeat·권한/기존 vector·앱 범위 복원 성공. 초기 스키마 소유 역할 guard와 복원 후 초대 검증 도구의 가정을 수정한 과정은 상세 기록/private 로그에 보존했다. 제품 코드 기존 전체2,109개/CI d700182 성공을 재사용하며 문서만 변경해 전체 테스트를 반복하지 않는다.
- 남은 입력: 현재 새 관리자 요청 없음. 첫 실제 Google 브라우저 로그인은 사용자 확인, 두 번째 Google 이메일은 추가 초대 시 필요. 정기 백업/전체 복구·분담 비용은 사용자 작업 저장·첫 공개 전 별도 확인.
- 다음: 앱 runtime을 기존 앱 역할/Google 설정으로 연결하고 사용자 실제 로그인→자료 목록→원문·인용 열람을 확인한다. 보호 검색 API/UI·의미 검색/AI·worker는 후속이다. D013 공개 앱 배포 유예를 유지한다.
- 검토·게시: 독립 결과/문서 검토 C0/I0/M1 후 과거 요청 상태의 시점을 정정하고 재검토 잔여C/I/M0. [Draft PR #23](https://github.com/DigestWorks/IssueDigest/pull/23) basefeat/evidence-search·앱 첨부. 문서 상대 링크82개·diff·공개 파일298개의 비밀값/계정/개별ID/hash 제외 확인. 소유 QA 컨테이너/익명 볼륨 제거·임시 passfile 부재 확인, 개인 백업/계획·리뷰는 보존.
- Sites: [v43 공동 DB](https://lawdigest-rebuild-plan.ijaesinii.chatgpt.site/#shared-database) native succeeded/public. source `ecfb668fa776a0b287c72086afc2ef83c23b4b21`, saved `appgprj_6ac612dd42708191a7a0c8377be64d48~appgver_23855b8565a8819184f39a313ac8a38d`, deployment `appgdep_6acf3ac604b88191a1da91d77e585213`. 사본 기준9905a7d·v42 보존, HTML28개/로컬 링크·anchor598개/manifest 통과. 문서 요약만 변경했으며 새 브라우저 화면 검사는 수행하지 않았다.
- 개발 인계: 사용자 폴더·서버 개인 worktree를 ops/database-bootstrap/origin 추적으로 연결하고 같은 a4313b9·깨끗한 Git 상태를 확인했다. 제품 코드/의존성 변경 없음. 실제 앱 runtime·Google 로그인은 다음 작업. [초기 적용 기록9905a7d CI 성공](https://github.com/DigestWorks/IssueDigest/actions/runs/38534024267)을 확인했으며 이후 게시/인계 문서 커밋과 구분한다.

## 이전 작업 · PostgreSQL 문자 검색 기반

- 작업: [저장 근거 검색 명세](../changes/evidence-search.md), R2/R3·D011/D015. 원문 버전과 정확한 본문 구간/페이지/셀 위치를 반환하는 첫 검색 SDK.
- 담당/브랜치: controller·implementer, `feat/evidence-search`; HWPX 수집 PR #21 위의 격리 worktree. [Draft PR #22](https://github.com/DigestWorks/IssueDigest/pull/22) 게시·앱 첨부. Sites·개발 인계는 후속 기록한다.
- 상태: domain 문자 검색/위치 단위, PostgreSQL ARRAY/GIN 후보·명시 투영 재생성, 현재 세션/회원 보호 SDK 구현. 작업 리뷰의 메모리 보관·긴 출처 식별자·일반 문서 페이지 정보 세 항목을 f5e3314에서 assertion RED8개 후 보완했다. 수정 범위 재검토에서 세 항목 해결·새 지적0으로 승인받았다. 독립 전체 변경 리뷰도 Critical/Important/Minor0으로 승인받았다.
- 검증: 최종 코드f5e3314의 controller 전체 Python1,787+JS322=2,109개, Ruffformat152/mypy67/ESLint/TS/SPA/OpenAPI 통과, skip/warning0. 실제 HWPX3개·문자 검색9건/전체 셀6건을 별도 DDL 금지·원문 UPDATE 없는 앱 역할로 다시 대조, 반환 위치 matched/not_evaluated·반복3회 unchanged·필터/권한/세션 폐기·미색인1건 표시·SQL @>/GIN 확인. 작은 실자료 위치 검사이며20문항 평가·대규모 성능/메모리 실측이 아니다.
- 범위: 같은 검색 단위에서 literal terms AND·ASCII 대소문자 비교, 출처/수집 시각 필터. 원문은 변경하지 않으며 이전 전체 투영을 후보별로 쌓아두지 않는다. 일반 문서는 전체 본문 TextQuoteSelector, PDF는 실제 PageSpan·셀은 전체 셀. 본문 있는 application/pdf에 페이지 정보가 없으면 재파싱 전 색인하지 않는다. 큰/빈 셀·후보/결과 한도·미투영 자료가 완전성을 제한한다.
- 후속: 보호 검색 API·화면, pgvector 의미 검색·재순위화·관계 검색·검색/AI20문항 평가·DBOS/outbox 소비. 인계 중 새 앱 설정 파일을 확인했고 소유자/비공개 권한·실제 대상 DB·DDL 없는 앱 역할·PostgreSQL18.6/pgvector0.8.7를 읽기 전용으로 검증했다. 기본 PostgreSQL URI를 메모리에서 psycopg 형식으로 바꿔 연결했으며 설정 파일을 수정하지 않았다. 실제 DB에는 기존 앱/검색 스키마가 아직 없고 초기 마이그레이션·백업/복구 조건 확인·자료 등록은 후속이다. 실제 승인 계획/초대·공동 DB·Google 로그인·공유 checkout·운영 서비스·main·공개 앱은 변경하지 않았다.
- CI: [0fa92fa 검사 성공](https://github.com/DigestWorks/IssueDigest/actions/runs/38524891935). 제품 코드f5e3314 이후는 문서 변경이며 실제 전체 검사와 별도로 구분한다.
- Sites: [v41 근거 검색](https://lawdigest-rebuild-plan.ijaesinii.chatgpt.site/#evidence-search) 공개 게시 native succeeded, v40 보존. source `ea23ba32934dbea7cd8c1b1d656ded35a765fdad`, saved `appgprj_6ac612dd42708191a7a0c8377be64d48~appgver_a7cde360ec2481918849e55e66667d45`, deployment `appgdep_6acf290e1be88191b143cdb50b03b006`. 사본 기준f89b1bc·HTML26/로컬 링크·anchor523/manifest·공개 파일289개의 실제 비밀값/계정/인용/내부 ID 제외 검사 통과. SDK와 앱/의미 검색/평가 미완료를 구분했다. 문서 요약 변경의 새 브라우저 화면 검사는 수행하지 않았으며 브라우저 열기 요청은 queued였다.
- 추가 게시: 인계 중 새로 확인한 앱 DB 읽기 접속/DDL 없는 역할·앱 테이블 미적용 상태를 v42에 반영했다. source `a1406c41238de6d9a58c701542b715d712edf16b`, saved `appgprj_6ac612dd42708191a7a0c8377be64d48~appgver_87a9b38c6ae08191b81d7979e44a641e`, deployment `appgdep_6acf2c2221f4819198af9813ada04620` native succeeded/public. 사본 기준842af02·v41 보존·HTML27/로컬 링크·anchor560/공개 파일290개·비밀값 제외 검사 통과. 이후 상태는 저장소 원본을 따른다.
- 정리·인계: 소유 검증 컨테이너의 전체 ID·이미지·label·실제 loopback binding 대조 후 해당 컨테이너/익명 볼륨만 제거했다. 미병합 검토 worktree/RED·GREEN·리뷰/개인 근거는 보존한다. 현재 폴더와 서버 개인 worktree를 feat/evidence-search·origin 추적으로 연결하고 locked 설치/SDK 무DB import를 확인했다. ARM 검색 도메인34개·mypy67개 통과. 웹/API 코드 화면은 바꾸지 않았으며 공동 DB/로그인/서비스/main·공개 앱은 미연결이다.

## 이전 작업 · HWPX 수집 작업·등록 계획 연결

- 작업: [수집 작업 명세](../changes/hwpx-import.md), R2/R3·D011/D015. 파일 snapshot을 기존 파서/정확 인용 계약으로 준비하고 승인된 등록 계획에 추가한다.
- 담당/브랜치: controller·implementer, `feat/hwpx-import`; HWPX 파서 PR #20 위의 격리 worktree.
- 상태: worker 패키지의 준비 함수·명시 명령 구현·검증 완료. 실제 첨부3개/정확 인용9개를 준비해 기존 합성 자료1개/초대2개를 보존하는 계획을 만들고 전용 검증 DB의 기존 CLI 검사/등록/반복/재조회까지 확인했다. 작업 리뷰의 JSON 직렬화 전 한도1건을9511d78/7090d72에서 입력·파생 결과의 구조/바이트 예비 검사로 보완하고 재검토에서 해결·새 지적0을 확인했다. 최종 코드7090d72 전체 Python1,703+JS322=2,025개·format145/mypy63/TS/빌드/계약 통과, skip/warning0. 정상 자료의 출력 byte 동일·기존 CLI 등록/반복/재조회도 다시 확인했다. 독립 전체 변경 리뷰 Critical/Important/Minor0으로 승인. [Draft PR #21](https://github.com/DigestWorks/IssueDigest/pull/21) 게시·앱 첨부. Sites v40 공개 게시·개발 인계 완료. 기본 실행은 비공개 artifact 준비이며 DB 적용은 기존 등록 도구의 명시 실행으로 분리한다. SDK/CLI 준비를 DBOS 런타임·주기 수집 완료로 표시하지 않는다.
- Sites: [v40 HWPX 수집 작업](https://lawdigest-rebuild-plan.ijaesinii.chatgpt.site/#hwpx-import) 공개 게시 native succeeded, v39 보존. source `b15a694fd3279270721e5cbe799d352d48ead68a`, saved `appgprj_6ac612dd42708191a7a0c8377be64d48~appgver_5a7dc517fc0c819180c94b1c5a7bd612`, deployment `appgdep_6acf1692cc6881919e854f432bff5f61`. 사본 기준d5581e6·HTML25개/로컬 링크·anchor487개/manifest·실제 비밀값/계정/인용/해시/UUID 제외59파일 통과. 새 브라우저 화면 검사는 수행하지 않았고 열기 요청은 queued였다.
- 인계: 사용자 폴더와 서버 개인 worktree를 `feat/hwpx-import`/origin 추적으로 연결했다. c6806b2에서 같은 코드·깨끗한 Git 상태·locked worker 설치·실제 준비 명령 --help 실행을 확인했다. 공개/공용 checkout·앱 runtime·DB는 변경하지 않았다.
- CI: [구현/검토38b920e 검사 성공](https://github.com/DigestWorks/IssueDigest/actions/runs/38517871947), [PR 링크 포함d5581e6 검사 성공](https://github.com/DigestWorks/IssueDigest/actions/runs/38517965438). 이후 게시/인계 문서만 바뀐 커밋의 exact-head 결과와 구분한다.
- 정리: 전체 ID·이미지·loopback 포트·소유 label을 대조해 검증용 DB 컨테이너/익명 볼륨을 제거했다. 개인 검증 입력/원문/산출물은700/600, 미병합 검토 증거는 보존한다.
- 실제 연결: 서버 앱 접속 설정은 이번 읽기 확인에서도 부재. 동료에게 이미 전달한 설정/백업 요청은 유지하며 새 확인 질문은 하지 않는다. 공동 DB·실제 초대·Google 로그인·공개 앱은 변경 전이다.

## 이전 작업 · HWPX 본문·표·인용

- 작업: [HWPX 명세](../changes/hwpx-evidence.md), R2/R3. 첫 이슈의 핵심 첨부를 기존 근거 계약으로 연결한다.
- 담당/브랜치: controller·implementer, `feat/hwpx-evidence`; 첫 자료 풀 PR #19 위의 격리 worktree. 본문 구역 순서·표/셀 주소·병합·단위 문구를 보존하며 의미를 추정하지 않는다.
- 상태: 로컬 bytes·기대 해시 기반 HWPX 파서와 기존 계약 어댑터 구현. 본문 구역/표·셀 주소·병합·중첩·단위 문구를 보존한다. 구역과 머리말을 혼동한 실제 파일 경계는 합성 회귀 사례로 보완했다. 독립 작업/전체 변경 리뷰 승인. ZIP64 지원 범위 문구1건을9a3ce66에서 보완하고 재검토에서 해결·새 지적0으로 승인받았다. [Draft PR #20](https://github.com/DigestWorks/IssueDigest/pull/20) 게시·앱 첨부. Sites v39 공개 게시·개발 인계 완료.
- 검증: 코드169d109에서 전체 Python1,615+JS322=1,937개·Ruff/format137/mypy57/TS/SPA/계약 통과, skip/warning0. 실제 첨부3개·표34개·셀278개의 XML 구조/범위와 인용281개를 대조했고 전용 검증 DB 저장/재실행/동일 조회·다른 공간 격리 확인. 문서 예제의 포맷 오류는169d109에서 수정한 뒤 전체 검사했다.
- 한계: CLI/worker·공동 DB·로그인/화면 연결은 후속. 단위/기간은 셀 문구로 보존하며 추정 메타데이터는 넣지 않는다. Q05/Q06의 의미/단위/합산 판정과 검색/AI 평가 실행·적격30~50개 코퍼스는 미완료다.
- Sites: [v39 HWPX 자료 읽기](https://lawdigest-rebuild-plan.ijaesinii.chatgpt.site/#hwpx-evidence) 공개 게시 native succeeded, v38 보존. source `32a30aeb758b03131a68f90772a99d954543c35e`, saved `appgprj_6ac612dd42708191a7a0c8377be64d48~appgver_a17d6662b7388191b2fbe90456e8a19a`, deployment `appgdep_6acf05011cf081918879fb001244e527`. 사본 기준7724f02·HTML24개/로컬 링크·anchor453개/manifest·실제 비밀값/계정/인용/해시/UUID 제외57파일 통과. 새 브라우저 화면 검사는 수행하지 않았고 열기 요청은 queued였다.
- 인계: 사용자 폴더와 서버 개인 worktree를 `feat/hwpx-evidence`/origin 추적으로 연결하고 cd45e04 코드·locked 의존성·HWPX 모듈 로딩·깨끗한 Git 상태를 확인했다. 공개/공용 checkout·앱 runtime·DB는 변경하지 않았다.
- CI: [구현·검토 b4aba72 검사 성공](https://github.com/DigestWorks/IssueDigest/actions/runs/38511445562), [PR 링크 포함7724f02 검사 성공](https://github.com/DigestWorks/IssueDigest/actions/runs/38511501704). 이후 게시/인계 문서만 바뀐 커밋의 exact-head 결과와 구분한다.
- 운영 경계: 소유 컨테이너의 전체 ID·이미지·loopback 포트를 대조해 검증용 DB/익명 볼륨을 정리했다. 기존 자료/공동 DB·실제 로그인·AI·main·공개 앱은 변경하지 않는다.

## 이전 작업 · 첫 이슈 자료 풀·평가 질문

- 작업/범위: [자료 풀 기록](../research/first-issue-corpus.md)·[출처45개](../research/first-issue-sources.tsv)·[질문20개](../../tests/evaluation/first-issue.md), R2/R3/R4. 기존 지방국립대 등록금 지원 이슈를 유지하고 정부안·기존 제도·관점/확정 근거 부재를 구분한다.
- 담당/브랜치: controller, `docs/first-issue-corpus`; 선행 등록 도구 위의 격리 worktree. 문서/조사 작업이며 제품 코드·스키마·API·의존성·공동 DB·운영은 변경하지 않는다. [Draft PR #19](https://github.com/DigestWorks/IssueDigest/pull/19) 게시·앱 첨부. Sites v38 공개 게시 완료.
- 결과: 공식 후보45개, HTTPS 응답 스냅샷38개 개인 보관. 라이선스 표시/100자 이상 텍스트13개 중 재게시1·다른 부처 대조자료1을 제외한 관련11개와 참고 법령 조문3개로 초기 연구 풀14개를 구성했다. 핵심4·배경10, 기존 앱 파서 지원3개. 첨부 안내38자2개와 접근/로봇 규칙 확인 대기7개를 실제 사용 가능한 자료로 세지 않는다. 현재 풀은 정부 자료 중심이며 반대 성명/회의록/확정 자료가 없다.
- 평가: 답변형15·자료 부족4·합성 지시 공격1, 총20개 질문/필수 근거/기대 화면/판정 기준 정의. 텍스트 위치·앞뒤 문맥 후보26개가 기존 Citation 계약에 일치했다. 지지 판정은 not_evaluated, 실행0·점수 없음. Q05의 목록 구조·Q06의 수치 표는 별도 검증이 필요하다.
- 검증: 출처45행·응답38개 해시·연구 풀14개/앱 파서3개·문항20개·인용 계약26개·문서 상대 링크78개·개인 권한700/600·공개 파일8개의 실제 비밀값/계정/인용 제외·git diff --check 통과. 제품 코드 변경이 없어 기존 c12e18e의1,919개 CI를 기준으로 삼고 전체 검사를 수동 반복하지 않았다. 검색/AI 평가 실행은0이며 문서 검증과 구분한다.
- 다음: 핵심 HWPX 본문·표/단위/출처를 생산용 파서에 연결하고, 직접 성명·국회/정확 통계와 재사용 조건을 추가 확인한다. 검토된 실제 코퍼스30~50건과20문항의 검색/AI 실행·품질 점수는 미완료다. 앱 접속 설정/백업·실제 등록/Google 로그인 대기와 독립적으로 진행했다.
- Sites: [v38 첫 이슈·평가](https://lawdigest-rebuild-plan.ijaesinii.chatgpt.site/#first-issue-evaluation) 공개 게시 native succeeded, v37 보존. source `0842dbe5b3ec55f4790008134c901f1d013133d6`, saved `appgprj_6ac612dd42708191a7a0c8377be64d48~appgver_17ef7d53d0008191bf13503a89181555`, deployment `appgdep_6acefdd94e388191988ffbecd4a9a103`. 사본 기준c62b3af·HTML23개/로컬 링크·anchor420개/manifest·공개 파일55개의 실제 비밀값/계정/인용 제외 통과. 새 브라우저 화면 검사는 수행하지 않았다. 원문·전체 인용·개별 해시/UUID·실제 계정·접속정보는 공개 기록에 포함하지 않는다.

## 이전 작업 · 공동 공간의 자료·접근 허용 등록

- 작업/범위: [등록 도구 명세](../changes/workspace-bootstrap.md), R1/R2·D015. 검증한 근거와 승인 계정의 초대를 함께 등록하고, 실패 시 전체 취소·재실행 시 중복 방지를 제공하는 운영자 CLI. 로그인·권한·근거 계약은 유지한다.
- 담당/브랜치: controller·implementer, `feat/workspace-bootstrap`; 선행 Google OAuth 위의 격리 worktree. 최종 검증·독립 리뷰 완료, [Draft PR #18](https://github.com/DigestWorks/IssueDigest/pull/18) 게시·앱 첨부. main 미병합, Sites·개발 인계 완료.
- 현재 상태: 자료/초대 Connection helper와 비공개 입력 검증·대상 읽기 검사·명시 등록 CLI를 구현했다. 같은 트랜잭션의 전체 취소·중복 방지·기존 초대 상태 보존을 검증했다. helper·CLI 작업 검토와 수정 재검토, 전체 변경 검토·최종 문서 보완 재검토를 모두 승인받았다. CLI 리뷰의 연결 정리 로그/성공 오판·무호출 테스트 지적2개와 최종 초대 행 잠금 UPDATE 권한 안내를 보완했다. 열린 지적은 없다. 새 HTTP 등록 API·자동 가입·자동 마이그레이션은 추가하지 않는다.
- 검증: 최종 코드22ede20에서 전체 Python1,597+JS322=1,919개·Ruff/format/mypy56/TS/SPA/계약 통과, skip/warning 없음. 별도 합성 CLI의 검증/읽기/최초 등록/반복→실제 서명 검증 SDK의 고정 MockTransport→두 계정 동일 자료 목록/원문/인용·다른 공간/미초대 차단·로그아웃 결합 검사1개 통과. 이 검사는 실제 Google 네트워크 로그인·브라우저 검사와 다르다. 초기 QA는 미정규화 fixture를 기대값으로 써 실패했고, 기존 EvidenceBundle의 정규화 결과와 비교하도록 QA만 수정해 통과했다.
- 실제 준비: 캐시의 공식 원문을 기록된 해시·이용 조건·본문·인용3개와 재대조했다. 새 공유 공간의 예약 ID와 승인 계정1개/자료1건의 개인 등록 계획을600으로 보관했다. 새 도구 기본 모드에서 개인 계획의 오프라인 검증도 통과했다. 원문 재수집·실제 DB 등록·계정 바인딩·실제 로그인 완료는 아니다.
- 서버 확인: 일시적인 SSH/GitHub 연결 실패 후 재접속했다. 전용 PostgreSQL18.6/vector0.8.7·앱 근거/인증 테이블0개, 기존 앱 접속 설정 파일 부재를 읽기 확인했다. 공동 DB·서비스·권한은 변경하지 않았다. 사용자는 기존 앱 접속 설정 위치/전달과 백업 시각·복구 방법을 동료에게 요청하겠다고 답했다. 실제 준비 완료로 간주하지 않는다.
- 다음 조건: 도구 검증은 완료했다. 실제 앱 계정/대상/필요 권한·백업 조건이 확인되면 명시 스키마 준비·등록과 사용자 실제 로그인으로 이어간다. 두 번째 계정은 미정이며 개발자 DDL 계정을 앱 runtime에 쓰지 않는다. 공개 앱·main 병합은 D013에 따라 유예한다.
- CI: [ac68478 검사 성공](https://github.com/DigestWorks/IssueDigest/actions/runs/38502605190), 구현 코드22ede20·독립 리뷰 및 보완 문서 포함. 이후 게시/인계 기록만 변경한 커밋의 결과와 구분한다.
- 인계: 현재 폴더를 `feat/workspace-bootstrap`으로 연결하고 locked 의존성/개인 입력의 기본 오프라인 검사1초대/1자료를 확인했다. 서버 개인 worktree도 해당 브랜치 origin 추적·코드를 fast-forward, 프로젝트 전용 환경을 선택한 ARM operator 모듈 로딩·mypy56 통과. 기본 미설정 앱을 유지하며 실제 DB/OAuth runtime에 연결하지 않았다. 테스트 DB의 전체 ID·실제 loopback 할당·이미지를 대조해 소유 컨테이너/익명 볼륨을 제거했다. 미병합 검토 worktree·RED/GREEN/리뷰/결합 증거는 보존한다.
- Sites: [v37 등록 준비](https://lawdigest-rebuild-plan.ijaesinii.chatgpt.site/#workspace-bootstrap) 공개 게시 native succeeded, v36 보존. source `32bbde3e40d69685888f21bd35fcf0e65d4a1527`, saved `appgprj_6ac612dd42708191a7a0c8377be64d48~appgver_bd0ac4636b648191a14d906b0fd946fa`, deployment `appgdep_6aceecf9c850819194c66e02f31cd646`. 사본 기준ac68478·HTML22/로컬 링크·anchor388/manifest·실제 비밀값/계정/인용/내부 ID 제외 검사 통과. 문서 갱신의 브라우저 화면 검사는 수행하지 않았고 브라우저 열기 요청은 queued였다. 현재 원본의 이후 게시/인계 기록과 사본 기준을 구분한다.

## 이전 작업 · Google 로그인·공동 조사 자료 진입

- 작업: [Google OAuth·공동 조사 자료 진입](../changes/google-oauth-workspace.md), R1/R2·D015. 명시 초대·Google 고정 identity·서버 세션·현재 권한과 공동 자료 목록을 연결했다.
- 담당/브랜치: controller·implementer, `feat/google-oauth-workspace` · [Draft PR #17](https://github.com/DigestWorks/IssueDigest/pull/17), 선행 공식 HTML #16 위의 격리 worktree. 최종 CI·게시·개발 인계를 아래 결과로 기록한다.
- 상태: 저장·공급자/HTTP/runtime·웹 세 작업의 독립 검토와 전체 변경 리뷰 승인. 주소의 비표준 표기로 정상 로그인이 차단되는 문제를 startup 거부로 보완했다. 전체 리뷰의 정렬/한도 테스트·OpenAPI 경계값 세 보완을 한 번의 수정 범위로 반영하고 scoped 재검토에서 모두 해결·새 지적 없음으로 승인받았다.
- 검증: 코어 코드 `e61d531`에서 controller 전체 Python1,491+JS320=1,811개·정적/빌드/계약 통과, skip/warning 없음. 인계 중 발견한 개발 포트 전달 오류를 `29a152d`에서 TDD·독립 리뷰로 수정했다. controller 웹322개·lint/타입/SPA/계약과 최종 코드 CI 전체 Python1,491+JS322=1,813개가 통과했다. 별도 실제 PostgreSQL·DDL 금지 앱 역할·개인 HTTPS·브라우저에서 합성 서명/두 계정의 로그인→자료 목록→원문/인용→로그아웃, 미초대 차단·실패 로그인 시 기존 세션 유지 확인. 데스크톱1366/모바일390에서 가로 넘침 없음·page error0. 브라우저의 이동 중/bfcache 보류 실험은 완료하지 못했으며 해당 동작은 컴포넌트 테스트 범위로 남긴다. 실제 외부 Google 로그인으로 표현하지 않는다.
- 남은 입력: Google 클라이언트 JSON 필수 항목·개발 callback 일치/개인 보관600 확인. 실제 Google 로그인·테스트 사용자 등록 여부·기존 앱 전용 DB 계정의 비밀 설정/필요 테이블 권한·두 번째 Google 계정은 미확인. 앱 접속 설정은 최신 개인 서버 조회에서도 없거나 읽을 수 없다. 승인 계정은 저장소 밖 미등록 기록만 있으며 공동 DB를 변경하지 않았다.
- 다음: 기존 앱 계정의 비밀 설정을 받아 역할/대상·백업 조건을 확인한 뒤 새 공유 공간·명시 초대·검증한 공식 원문을 이관한다. 실제 Google 로그인은 사용자가 확인한다. 스키마 변경용 계정을 앱 실행에 사용하지 않는다.
- 인계: 사용자 폴더를 `feat/google-oauth-workspace`로 연결하고 고정 의존성을 설치했다. 격리 검토 폴더는 해당 코드의 detached 상태로 보존한다. 개인 서버 worktree도 같은 코드·upstream으로 연결했다. ARM Google/설정/runtime103개 통과·공동 DB 미사용에 따른 조건부 PostgreSQL1개 skip, launcher13개·mypy54/웹 타입/SPA/계약 확인. 지정 개인 웹/API의 헬스·상태·로그인 화면200 및 API 계약 일치를 확인했다. 기본 미설정 runtime을 유지하며 실제 OAuth/공동 DB를 연결했다고 표시하지 않는다. 소유 합성 DB/볼륨·브라우저·QA API/웹은 정리했다.
- CI: [최종 코드29a152d · 검사 성공](https://github.com/DigestWorks/IssueDigest/actions/runs/38402405745). 작업/전체/수정 및 실행 포트 보완 리뷰 모두 승인. 후속 문서 커밋의 exact-head 결과는 PR에서 확인한다.
- Sites: v35 공개 게시 성공·v34 보존, source `3648837847e5c1b3d87dfa9294c27d0e00435153`, saved `appgprj_6ac612dd42708191a7a0c8377be64d48~appgver_2d7136cfed788191b8db582803e0b301`, deployment `appgdep_6ace29a304e481919c5beaa7ac6cd541`. 서버 포트 보완·최종 인계/1,813개 CI 결과를 [v36](https://lawdigest-rebuild-plan.ijaesinii.chatgpt.site/#google-oauth)에 게시했다. source `bffe1117e1759197d42f80d327f38c505b55205a`, saved `appgprj_6ac612dd42708191a7a0c8377be64d48~appgver_40148f188db08191a3d05c5dd9f8f75f`, deployment `appgdep_6ace2f6a61a08191a457f2c32f876211` native succeeded/public. v35도 보존했으며 사본 기준2911619·HTML21/로컬링크·anchor358/manifest/공개 비밀값 제외 검사를 통과했다. 계획 문서의 새 브라우저 화면 검사는 수행하지 않았다. 현재 원본의 이후 게시 기록과 사본 기준을 구분한다. 공개 앱·main 병합은 D013에 따라 유예한다.

## 이전 작업 · 공식 정책 HTML 원문 준비

- 작업: [공식 정책 HTML 원문·인용 준비](../changes/official-html-evidence.md), R2/P2. 첫 이슈 정부 자료의 본문·발행일·출처표시 조건을 실제 원문과 대조한다.
- 담당/브랜치: controller·implementer, `feat/official-html-evidence` · [Draft PR #16](https://github.com/DigestWorks/IssueDigest/pull/16); 선행 근거 읽기 #15 위, main 미병합.
- 상태: HTML 제한 추출·메타데이터/이용 조건·기존 표현/인용 어댑터 구현b3febab, 독립 리뷰 P1 caller-ID 오류 노출을 assertion RED11개 후 fixed AuditError로 보완47394b2, scoped 재검토 해결·새 지적0. 실제 정부 원문35문단/3,231자·정확 인용3개·저장 재조회 검증. 서버 개인 공간에도 원문/메타데이터/검증 산출물5개600·디렉터리700/내용 동일로 보존했다. 검증용 workspace/snapshot은 실사용 승인 계정/공간이 아니다. 전체 원문·인용·hash/ID는 공개 기록에 복제하지 않는다.
- 검증: focused150개·controller 최종 전체 Python1,277+JS233=1,510개 및 정적/빌드/계약 검사 통과. 초기 assertion RED122개와 보완 RED 보존. 실제 정부 원문과 독립 브라우저 DOM 본문 동일·외부 요청43건 차단, 전용 검증 DB 최초 저장/같은 재전송 미생성/동일 재조회·두 fixture 사용자 보호 GET200/no-store·비로그인401/다른 공간404. 최종 코드47394b2에서 전체 검사·실제 원문 재추출/메타데이터/인용/저장 재열람 확인. 독립 전체 변경 리뷰52e0377 승인·Critical/Important/Minor0.
- 범위: 원문 사진/이미지·캡션·메뉴/AI요약 제외, 이용/파서/정규화 기록. 공동 작업용 DB 적재·실제 로그인·AI·공개 앱은 후속이다. 기존/운영 DB나 공용 서비스를 변경하지 않는다.
- 다음: Draft PR·Sites·개발 인계 결합을 마친 뒤 실제 작업 공간/로그인·선별 원문 수집·AI 결과 연결로 진행한다. 실제 앱 공개·main 병합은 D013에 따라 유예한다.
- Sites: v34 공개 게시 완료·v33 보존. 첫 공식 원문/정확 인용·개인 검증 DB/합성 사용자/실제 공동 DB 후속을 구분했다. HTML19개/로컬 링크·anchor301개·manifest/접속정보 제외·공백 검사 통과. 문서 요약 변경의 브라우저 레이아웃 검사는 반복하지 않았다.
- 게시 증거: source `50aa3605f82c40334cf082d00641c8e666f1b322`, saved version `appgprj_6ac612dd42708191a7a0c8377be64d48~appgver_c9da071b39148191b71a6216026e47c0`, deployment `appgdep_6acdfcf7f80c8191a272031d0c74b8a4` native succeeded·URL 확인, 기존 공개 설정 유지. 사본 기준d7f9766. [CI #38377896184](https://github.com/DigestWorks/IssueDigest/actions/runs/38377896184) exact d7f9766 성공. PR #16 앱 첨부 완료.
- 개발 인계: 현재 폴더와 서버 개인 worktree d7f9766·깨끗함 확인, 서버 origin/feat/official-html-evidence 추적·locked 설치/ARM HTML150개/mypy45개 통과. 원문/산출물5개600 서버 개인 보존·내용 일치 확인. 마지막 게시 기록 커밋도 개인 worktree에 fast-forward한다. 공유 저장소/운영 DB/서비스 변경·main 병합·앱 배포 없음.
- 정리: 소유한 전용 검증 DB 컨테이너만 전체 ID 대조 후 제거했다. 개인 원문/메타데이터/검증 bundle은 보존하며 실제 서비스 DB 저장 상태로 표현하지 않는다. 자체 오프라인 브라우저 세션은 닫았다. 미병합 검토 worktree/RED·GREEN·리뷰/검증 로그는 보존한다.

## 이전 작업 · 저장 근거 읽기 화면

- 작업/관련 단계: [보호 근거 읽기 화면](../changes/evidence-reader.md), R1/R2/R4의 웹/API 소비 부분. 사용자 D013에 따라 공개 앱 배포 유예.
- 담당/브랜치: controller·implementer, `feat/evidence-reader` · [Draft PR #15](https://github.com/DigestWorks/IssueDigest/pull/15), 선행 #14 위·미병합. 별도 격리 worktree이며 main·공용 배포 checkout은 유지한다.
- 상태: 구현eec0136·리뷰 보완7c13ae8. 같은 출처 보호 GET 소비·display validation·취소/전체 deadline·안전한 오류, 링크 진입·원문/페이지/표/정확 인용 위치 화면 구현. 독립 작업 리뷰의 P2 두 건(페이지 없는 표의 원문 복귀·긴 원문 강조 위치 이동)을 assertion RED3개 후 수정하고 scoped 재리뷰에서 모두 해결·새 지적 없음. 독립 전체 변경 리뷰 승인·Critical/Important/Minor0. 리뷰는 실제 로그인·전체 schema/semantic·운영 감사·실제 이슈 코퍼스/AI/정책 결론·PDF 이미지/전표 재구성·규모/전체 접근성 매트릭스·게시/인계를 완료했다고 판단하지 않았다. 기존 명세·후속 요구사항의 범위와 일치하며 새로운 예외/지적은 없다.
- 검증: 초기 client 실제 namespace assertion RED54개·UI 실제 렌더/폼 RED30개·호환성/키보드/표 선택 RED 보존, 최종 focused103개. controller 최종 전용 loopback 합성 PostgreSQL18.6 포함 전체 Python1,127+JS233=1,360개, skip0·lint/format/mypy/TS/SPA/contract 검사 통과. runtime/서버 계약·generated 타입·의존성/lockfile·운영 DB 변경 없음.
- 실제 브라우저: 합성 PostgreSQL→기존 FastAPI 보호 GET→개인 HTTPS Vite→브라우저. JSON200/no-store, Home 링크 진입·두 fixture 사용자 동일 bundle·비로그인/다른 공간 차단·PDF/text 강조·키보드 표 선택·선택 시 추가 GET 없음, 1366/390·가로 넘침 없음·화면 직접 확인. 긴 합성 원문450문단 뒤쪽 text/PDF 인용은 두 크기에서 최초/반복 선택 후 실제 mark가 viewport 안에 보임. pages=[]·table-only에서도 원문 복귀 확인. JavaScript page 예외0·예상401/404 resource 메시지 외 console 오류0.
- 기록: 원래 assertion RED·QA 실패 로그를 보존했다. 최초 브라우저 journey는 실제 문구와 다른 retry locator를 기다려 실패했으며 DOM 확인 후 QA locator만 수정해 통과했다. 긴 원문 첫 시도는 브라우저 세션이 없어 실행되지 않았고 재개 후 검증했다. 이를 생산 코드 RED라고 주장하지 않는다. fixture/세션·QA 포트/키·이미지는 ignored 개인 영역만 사용하며 공개 앱에 추가하지 않았다.
- 첫 이슈: 사용자 위임에 따라 최근 시사를 검색해 [지방국립대 등록금 지원](../research/first-issue.md)의 대상·재원·형평성을 선정(D014). 대표 질문5개와 원문/보도5개 시작 목록. 실제 코퍼스/평가셋·기사 이용·정부안/확정·인과 검토는 후속이며 이번 합성 UI QA를 이 이슈 자료의 평가로 간주하지 않는다.
- 범위: 같은 출처 보호 GET 소비, 안전한 자료 링크 진입, 원문/페이지/인용 위치와 접근/로딩/오류 상태. 실제 로그인 발급·자료 이관·운영 DB·AI 생성은 후속. 자료/토큰을 브라우저 저장소나 공개 기록에 남기지 않는다.
- 다음 행동: 선정 이슈의 공식 원문·이용/버전·근거 대응 확보와 실제 자료 등록·로그인/AI 연결을 단계적으로 진행한다. 이 읽기 부분은 구현/리뷰/검사/PR/Sites/개발 인계를 마쳤고 전체 최소 제품·운영 준비는 후속이다. 실제 앱 배포·main 병합 없음.
- Sites: v33 공개 게시 완료. 배포 유예·첫 이슈 선정·읽기 구현과 기존 v32 보존을 반영했다. 문서 요약의 브라우저 화면 검사는 반복하지 않았다.
- 게시 증거: Sites source `daf4768e150388d4e7ec031108c8eeae8204826c`, saved version `appgprj_6ac612dd42708191a7a0c8377be64d48~appgver_e00da3bb61a88191a01a7659e314ab45`, deployment `appgdep_6acdefc525a88191aee950652bf0a308` native succeeded·URL 확인, 공개 설정 유지. 사본 기준cc97c87·HTML18개/로컬 링크·anchor274개/manifest/공개 접속정보 제외·문서7개/상대 링크58개 통과. [cc97c87 CI](https://github.com/DigestWorks/IssueDigest/actions/runs/38370950027) 성공. PR #15 앱 첨부 완료.
- 개발 인계: 현재 폴더 `feat/evidence-reader`·서버 개인 worktree의 같은 origin 추적·cc97c87/깨끗함 확인. ARM 타입/웹233개 통과, 개발 웹과 자료 route200·상태JSON200·비로그인 보호GET401 확인. 이번 마지막 문서 기록도 fast-forward하고 동일 HEAD·깨끗함을 확인한다. 리뷰 worktree는 detached로 검증 증거를 보존한다. 운영 서비스·DB·공용 checkout·배포 설정은 유지한다.

## 이전 작업 · PDF 인용 후보

- 작업: [PDF 인용 후보·문맥 선택](../changes/pdf-quote-candidates.md), R2/P2의 다음 부분 구현. 반복 문항의 정확 위치 후보와 페이지/인접 문맥 조건의 유일 선택을 구현한다.
- 담당/브랜치/PR: controller/implementer · `feat/pdf-quote-candidates` · [Draft PR #14](https://github.com/DigestWorks/IssueDigest/pull/14) · 선행 #13 위·미병합.
- 상태: 구현·독립 작업 리뷰·controller 전체 검사·실제 후보 대조 완료, 독립 전체 변경 리뷰 승인·Draft PR #14 게시/앱 첨부·Sites v31 공개 게시 완료. 표/응답 수치·원문 진위·올바른 근거 위치의 의미 판단·제품 화면/운영 DB 연결은 별도다.
- 검증: 같은 비무작위6개에서35문항/87정확 위치,35문항 모두 여러 페이지·4문항은 같은 페이지에서도 반복한다. 각 문항에 유일한 페이지/80자 문맥 매치가 있지만 적합한 조사/표의 위치라는 판단은 하지 않았다. 신규106개·전체Python1,127+JS134=1,261개 및 타입/빌드/계약 검사 통과. 새API의 실제87후보/페이지+문맥round-trip을 검증했다. 제품자동선택/올바른조사·표판정은 하지 않았다.
- 관리자 요청: 실제 전달은 pgvector만, 완료. 별도 DB 로그인 계정 존재 확인. 다른 미전달 제안은 현재 개발의 선행 조건이 아니며 [필요 시점](../../infra/administrator-request.md)에 확인한다. 추가 권한/키/외부 요청 없이 진행한다.
- 다음: 전체 변경 리뷰·PR·Sites·인계를 마무리하고 자료/근거의 실제 조회·선택 흐름에 연결한다. 첫 제품 이슈·자료 이용 조건·표/수치 검증은 별도다. 실제 원문/문맥은 공개하지 않는다.
- Sites: v31 공개 게시 완료, v30을 보존했다. 후보/명시 선택의 위치 검증과 조사/표 의미·제품 화면 연결 후속을 구분했다.

## 2026-10-13 · PDF 인용 후보·문맥 선택

- 구현: af1bd39·작업 체크리스트/명세 cc38d23. 별도 quotes 모듈의 불변 검색 한도/결과·정확 후보 목록·페이지/인접 문맥 resolver를 추가했다. 기존 추출/locator/CLI·도메인/API·생성 타입·의존성은 유지했다. 후보에는 caller 문서/표현 ID·텍스트 해시와 정확한 페이지/문자 위치가 연결된다.
- 동작: 겹치는 매치·페이지 경계·문맥의 페이지 침범도 유일성 판정에서 누락하지 않는다. 기본 text1,000,000자·raw occurrence10,000개·반환 후보100개·앞뒤80자 preview이며 반환 후보 제한 뒤에도 전체 건수를 세고 has_more를 표시한다. 실패/잘린 목록으로 유일성을 추정하거나 첫 위치를 자동 선택하지 않는다. 명시 페이지 요청은 그 PageSpan 길이에 text 한도를 적용한다.
- 검증: 합성 assertion RED43개/교정된 resolver RED55개 후 신규106개 GREEN, ingestion349개. worker/controller 각각 최종 코드에서 전용 합성 PostgreSQL18.6 포함 전체 Python1,127+JS134=1,261개, skip0·린트/format·mypy·TS·SPA·OpenAPI drift exit0. README 예제도 합성 유효 모델/선택 조건과 실제 인용 검증으로 실행했다. 독립 작업/전체 변경 리뷰 승인·Critical/Important/Minor 지적0. 기존 명세의 유효 모델 입력·미평가 의미/권한·운영 제외와 전사 로그 한계를 유지하며 PR/Sites/인계는 controller가 별도 확인한다.
- 기존 회귀: 원본 보존 테스트가 전체 stat의 atime(읽기 접근 시각)까지 비교하여 초 경계에서 실패했다. 읽기 후에도 bytes·dev/ino/mode/size/mtime_ns/ctime_ns를 비교하도록 이 assertion만 정정했다. PDF 생산 코드는 변경하지 않았다. 원래 전체 실패 로그는 덮어써졌고 관측 실패의 명시적 전사 발췌만 남아 있음을 보고서에 기록했다. 해당 테스트·ingestion·전체 gate는 정정 후 통과했다.
- 실제 대조: 같은 비무작위 소표본6개/35문항, 추출은 PDF당 wall15초로 제한했다. 새API가 정확 위치87개를 반환했고87개 모두 기존 validate_citation의 anchor matched/support not_evaluated를 통과했다. 기본 문항만 요청하면35개 모두 quote_ambiguous, 후보의 페이지로만 제한하면75회 matched/12회 ambiguous였다. 후보별 명시 페이지+앞뒤 원문 문맥으로87회 모두 동일 위치 round-trip 통과, 각35문항에 하나 이상의 유효 round-trip이 있었다. 반환 후보1개로 제한한35회도 총수/has_more를 유지했다.
- 해석 경계: 모든 후보를 QA 조건으로 대조했으며 적합한 조사/표 위치를 고르거나 제품에서 자동 선택하지 않았다. 테스트용 caller UUID는 저장된 문서 버전이 아니다. 위치 일치·선택 가능성과 원문 진위·조사/표 대응·응답 수치·주장 지지를 구분한다. 전체225개 품질로 일반화하지 않는다.
- 보호: 실제 문항/문맥·텍스트·경로·해시·UUID는 개인 환경 밖으로 내보내지 않고 집계만 기록했다. operating DB·원문·공유 서비스·DNS·모델 호출/새 의존성 변경 없음. 추가 관리자 요청 없음. 테스트 migration은 명시적인 전용 로컬 합성DB에만 실행했다.
- 게시: [Draft PR #14](https://github.com/DigestWorks/IssueDigest/pull/14) 생성·앱 첨부 완료, 선행 #13 위·미병합. [46a9d20 CI](https://github.com/DigestWorks/IssueDigest/actions/runs/38342927912) 성공. Sites v31 게시와 현재 폴더/서버 사용자 전용 worktree의 867f2df 인계를 확인했다. 실제 제품 화면/운영 DB 배포는 수행하지 않았다.
- Sites: [v31 공개 게시](https://lawdigest-rebuild-plan.ijaesinii.chatgpt.site/#quote-candidates) native succeeded·URL 확인, 공개 설정 유지. source `b9828cc9e0143db890d9fcb742a2876859904a52`, saved version `appgprj_6ac612dd42708191a7a0c8377be64d48~appgver_f818301f172c819194d781e919ca2920`, deployment `appgdep_6acda94ad80c8191a864aebadc8d8efd`. 사본 기준867f2df·이전v30 보존·HTML16개/로컬 링크·anchor224개/manifest/공개 접속정보 제외·문서6개/상대 링크64개·git diff --check 통과. 실제 원문/문항/문맥·개별ID/해시는 미게시. 문서 변경의 브라우저 화면 검사는 수행하지 않았고 사이트 탭 열기는 queued 접수다.
- 인계: 현재 폴더 feat/pdf-quote-candidates·서버 사용자 worktree 같은 origin 브랜치 추적. 867f2df에서 locked 설치·실제 finder/resolver import·Git 깨끗함을 확인했다. 게시 기록까지 포함하는 마지막 문서 커밋도 fast-forward하고 최종 응답 전에 같은 HEAD/깨끗함을 확인한다. 앱 프로세스 재시작·운영 데이터/공유 서비스 변경 없음. 미병합 리뷰/RED·GREEN 증거는 격리 폴더에 보존한다.


## 2026-10-13 · pgvector 완료·관리자 요청 정정

- 사용자 정정: 실제 전달 요청은 pgvector만이다. 이전에 세 항목 전체를 전달/답변 대기로 기록한 것은 잘못된 추정이었다. 앱 계정/백업·운영/도메인은 미전달 제안으로 정정하고 구현 차단 항목에서 제외한다.
- 동료 보고: PostgreSQL18.6 유지·pgvector0.8.7 설치/활성화, 개발자/앱 계정 연산·HNSW 검색 검증, 재생성 유지용 Dockerfile/Compose/초기화 SQL·이미지 빌드·DB 백업 반영·재시작 없음.
- 직접 확인: 기존 DB helper의 읽기 전용 transaction에서 server18.6/vector0.8.7/public·L2/코사인 연산 정상, 별도 프로젝트 로그인 계정1개(non-superuser/non-owner/CONNECT), public 앱 테이블0개. 비밀값·계정명은 미출력. 앱 계정 실제 로그인/상속/테이블 권한·HNSW/재생성·백업 복원은 직접 검증하지 않았다.
- 필요한 시점: 앱 계정은 신규 생성 대신 기존 계정을 앱 연결 때 확인한다. 정기 백업/서버 밖 사본·복원은 보존할 사용자 작업 저장 전에 준비하되 기존 구성 우선이다. 서버 부하는 개발자가 실측, 새 자원은 부족할 때만 요청한다. IssueDigest 실제 부담 비용은 운영 전, DNS/프록시는 두 사용자 앱 제공 시점에 확인한다. 지금 새 서버·유료 저장소·관리자 권한 요청은 없다.
- 근거·상세: [관리자 요청 상태](../../infra/administrator-request.md). 이번 변경은 문서/읽기 전용 확인이며 운영 DB·앱 코드·권한·백업·DNS·공유 서비스 변경이나 외부 메시지 발송 없음. 검색 기능·한국어 품질·운영 준비 완료로 표시하지 않는다.
- 게시: 기존 [Draft PR #13](https://github.com/DigestWorks/IssueDigest/pull/13)의 문서와 설명을 갱신했다. [Sites v30](https://lawdigest-rebuild-plan.ijaesinii.chatgpt.site/) native succeeded·공개 설정 유지. source `f6edd927796a800929162402c0000d2314213bdb`, saved version `appgprj_6ac612dd42708191a7a0c8377be64d48~appgver_ca6cf7d80f3c8191a36c6419298b8066`, deployment `appgdep_6acd9e30126c8191bacaae370b582ea6`. 사본 기준212bf18·이전v29 보존. 문서5개/상대 링크20개·HTML15개/로컬 링크·anchor202개·수치/공개 접속정보 제외·git diff --check 통과. 문서만 변경하여 코드 전체 테스트·브라우저 화면 검사는 반복하지 않았다. 마지막 게시 기록도 서버 사용자 전용 worktree로 fast-forward하고 깨끗함을 확인한다.

## 2026-10-13 · PDF 페이지 텍스트·정확 인용 준비

- 구현: `c778b80`, 문서 예제 형식 보완 `fce7a41`. pypdf6.20.1 고정, 원본 해시 확인 후 익명 복사본만 제한된 Linux 자식 프로세스에서 파싱한다. 페이지 텍스트·빈 페이지·code-point 구간을 기존 ParsedRepresentation/PdfQuoteSelector 계약에 연결했다. DB/API·생성 타입 변경 없음.
- 인용: 한 페이지 안의 정확하고 유일한 문자열만 선택한다. 반복·겹침·페이지 경계·파싱/한도 실패를 고정 오류로 거부한다. validate_citation의 anchor matched와 support not_evaluated를 구분한다. 표 구조·좌표·OCR·출처 진위·조사 대응·수치/주장 지지를 추정하지 않는다.
- 검증: 합성 assertion RED/GREEN과 ingestion243개(신규133개)를 구현했다. controller 첫 전체 검사는 늦게 편집된 README 코드 예제의 형식 오류로 중단됐다. 예제만 보완한 최종 코드에서 전용 합성 PostgreSQL18.6 포함 전체 Python1,021+JS134=1,155개, skip0·린트/format·mypy·TS·SPA·OpenAPI drift exit0. 독립 작업/전체 변경 리뷰는 승인·Critical/Important/Minor 지적0. 범위 밖인 원문/수치/표/OCR·전수 품질·첫 이슈/이용 권리·OS sandbox를 완료로 표시하지 않는다. PR/Sites/인계는 controller가 별도 검증한다.
- 실제 대조: 2026-10-13 UTC, 서버의 기존 후보225개를 parsed 상대 경로 순으로 정렬하고 서로 다른 PDF 해시의 첫6개를 선택했다. 추출 성공 여부/크기에 따른 재선택 없는 비무작위 소표본이며 전체225개 품질로 일반화하지 않는다. PDF당 wall15초로 제한, 6개 모두 성공·92페이지·빈 페이지0·텍스트94,535 code points. 개인 환경에서 기존 question_text35개를 정확 대조했고 전부 quote_ambiguous였다. 자동 확정 인용0개이며 실패를 성공으로 바꾸거나 fuzzy/공백 정규화를 사용하지 않았다.
- 별도 위치 확인: 추출한 각 PDF의 첫 비어 있지 않은 페이지에서 최대80 code points를 명시 페이지로 선택한 probe6개는 기존 인용 검증 matched/support not_evaluated를 통과했다. 임시 호출자 UUID만 사용했고 실제 저장된 문서 버전이나 기존35문항의 인용으로 표시하지 않는다.
- 출력: 실제 installed inspect-pdf도 집계만 반환했고 opt-in 추출 텍스트/메타데이터는 원문·Git 밖 개인 폴더의 새600 파일에 저장했다. 원문·질문·해시·경로·URL·UUID를 공개 기록/Sites에 넣지 않는다. 기존 원문·운영 DB·공유 서비스·DNS 변경이나 모델 호출 없음. 원격 직접 shell CLI 도움말은 venv PATH 미설정으로 exit127이었고 uv run으로 설치된 명령을 실행해 정상 확인했다.
- 남은 품질: 질문이 반복되는 문서에는 명시적 문항·페이지·표 대응이 필요하다. 원문 진위/조사 대응과 표·응답 수치 검증, 첫 제품 이슈·이용 조건·실제 평가셋은 후속이다. pypdf 업그레이드 시 암호화 사전 거부 hook과 회귀 테스트를 다시 확인해야 하며 resource 한도는 OS sandbox를 대체하지 않는다.
- 게시: [Draft PR #13](https://github.com/DigestWorks/IssueDigest/pull/13) 생성·앱 첨부 완료, 선행 #12 위·미병합. [def67c8의 CI](https://github.com/DigestWorks/IssueDigest/actions/runs/38338133072) 성공. Sites v29 게시와 현재 폴더/서버 사용자 전용 worktree의 f0c34d6 인계를 확인했다. 실제 제품 앱/운영 DB 배포는 수행하지 않았다.
- Sites: [v29 공개 게시](https://lawdigest-rebuild-plan.ijaesinii.chatgpt.site/#pdf-evidence) 성공. source `a84ffcec8ae42a2a76edb32fe8db368062f65d77`, saved version `appgprj_6ac612dd42708191a7a0c8377be64d48~appgver_578bd5a013808191b6383ac332013977`, deployment `appgdep_6acd9b12fe548191a4702a9a4e818322` native succeeded·URL 확인. 사본 기준f0c34d6·v28 보존·HTML14개/로컬 링크·anchor181개/manifest/공개 접속정보 제외 통과. 문서6개 상대 링크61개 검사 통과. 원문/개인 추출 상세는 미게시, 문서 변경의 브라우저 화면 검사는 수행하지 않았다. 사이트 탭 열기는 queued 접수다.
- 인계: 현재 폴더는 feat/pdf-text-evidence, 서버 사용자 전용 worktree는 같은 origin 브랜치를 추적하며 f0c34d6에서 Git 깨끗함·locked 설치·installed inspect-pdf 도움말을 확인했다. 게시 기록을 포함하는 마지막 문서 커밋도 fast-forward하고 최종 응답 전에 같은 HEAD·깨끗함을 확인한다. API/웹 프로세스를 재시작하거나 운영 DB·공유 서비스를 변경하지 않았다. 미병합 리뷰/RED·GREEN 증거는 격리 폴더에 보존한다.


## 2026-10-13 · 관리자 요청·읽기 전용 연결기 준비

- 사용자 요청에 따라 관리자가 해야 할 설치/계정/접근 작업만 전달 문서로 좁혔다. 개발자는 자료 연결기·검증과 후속 백업 자동화/배포 설정을 맡는다. 외부 저장소·DNS 공급자·청구 비용은 확인 전이다.
- 현재 계정의 비대화식 sudo/Docker 관리·DB superuser/CREATEROLE/CREATEDB 권한이 없고, DB 소유자이며 vector 패키지가 없음을 다시 확인했다. pg_dump/pg_restore 사용 가능, 서버 웹 포트는 기존 서비스가 사용 중이다. 접속 세부정보는 공개 기록에 넣지 않는다.
- 연결기는 parsed/pdf 파일만 명시 경로에서 읽는다. basename 대응은 후보로만 표시하고 누락·다중 후보·헤더 없는 PDF를 격리한다. 개별/전체 읽기 한도·symlink/경로 검증·집계와 개인 상세 결과를 분리한다. 첫 제품 이슈·기존 계약을 변경하지 않는다.
- 작업 절차: spec-driven-workflow 적용. OpenSpec root null로 해당 단계는 생략, 계획/요구사항을 변경 문서에 작성하고 SDD/TDD·독립 리뷰·실제 PG 포함 전체 검증으로 진행한다. native worktree 도구가 바깥 폴더를 Git 저장소로 인식하지 못해 기존 sibling 격리 방식으로 준비했다. 다른 작업의 리뷰 폴더·기록은 보존한다.
- baseline: locked Python3.13.12/uv0.11.4·SHA 확인한 Node24.21.0/npm11.19.0·전용 합성 PostgreSQL18.6, 전체 Python778+JS134=912·린트/타입/SPA/계약 drift 통과. 기본 시스템 도구 차이로 첫 npm 설치가 거절돼 고정 도구를 선택했다. 엔진 제약/lockfile 우회는 하지 않았다.
- 구현: `02d6cc5` 표준 라이브러리 전용 ingestion 패키지. 명시 경로·descriptor 기반 symlink/특수 파일 거부, JSON metadata·basename 다중 후보·PDF 헤더/해시·변경/크기/총 읽기 한도, 집계 전용 stdout·600 exclusive 개인 manifest. 원문/인용 증명·DB 이관을 만들지 않는다.
- 검증: 실제 assertion RED/GREEN 기록과 신규101개·전체Python879+JS134=1,013개, lint/format·mypy·TS·SPA·계약 drift를 controller가 최종 구현에서 exit0 확인했다. 새 외부 의존성·기존 생성 계약 변경 없음. 독립 작업 리뷰에서 명세/품질 모두 승인, 지적0. 전체 변경 리뷰의 비차단 URL 제어문자 처리 지적1개를 `1a6f71d`에서 Unicode Cc 거부·실제 assertion RED3/GREEN110개로 보완했다. 한 번의 수정 범위 재검토에서 해결·새 문제 없음 확인. 최종 controller 전체Python888+JS134=1,022개와 모든 검증 exit0, skip0. PR #12 생성·앱 첨부 완료, Sites는 대기 중이다.


- 실제 검사: 서버 사용자 전용 worktree `02d6cc5`에서 locked 설치 후 2026-10-13 10:37 한국 시간에 완료. 읽은 JSON840개 중 candidate225·quarantined384·unsupported231. 격리 사유: 등록번호 형식8·유효 출처 URL 없음315·다중 PDF 후보49·PDF 누락12. parsed 비JSON1개는 읽지 않았다.
- PDF:774개를 스트리밍 검사, 헤더 없는23개·정상 PDF의 동일 해시 그룹90개·유효 등록번호 중복 그룹226개. 전체 읽기942,478,095 bytes. 중복 그룹은 문서/조사 건수와 같지 않으며 자동 병합하지 않았다. 헤더/해시/basename 대응은 원문 동일성·인용 정확성의 증명이 아니다.
- 보완 영향 확인: 개인 manifest의 유효 metadata에 제어문자를 포함한 출처 URL이0개임을 집계로 확인했다. 이전 실제 검사 건수는 `02d6cc5` 관측 결과이며 전체943MB 재검사를 반복하지 않았다.
- 개인 상세 결과:840개 JSON의 manifest를 원문 경로와 Git 밖 개인 디렉터리의 새600 파일로 저장했다. 공개 stdout은 집계만, 원문·경로·등록번호·URL·해시는 기록하지 않았다. 소스 파일·운영 DB·공유 서비스·DNS 변경 없음. 전체 수집 상태/일관된 스냅샷을 보장하지 않는다.


- 게시: [Draft PR #12](https://github.com/DigestWorks/IssueDigest/pull/12) 생성·앱 첨부 완료, 선행 PR #11 위이며 미병합. [baf4b18의 CI](https://github.com/DigestWorks/IssueDigest/actions/runs/38333517845) 성공. 실제 제품 앱/운영 DB 배포는 수행하지 않았다.
- Sites: [v28 공개 게시](https://lawdigest-rebuild-plan.ijaesinii.chatgpt.site/) 성공. source `d1e95100359480f2e80d35d68bfd2ce8b824a859`, saved version `appgprj_6ac612dd42708191a7a0c8377be64d48~appgver_2792cfe7828c81918724c8ad7bc24447`, deployment `appgdep_6acd8d1834288191b467053c8bbcaf21` native succeeded·URL 확인. 사본 기준baf4b18·기존v27 보존·HTML13개/로컬 링크·anchor161개/manifest/공개 접속정보 제외 통과. 문서 변경의 브라우저 화면 검사는 수행하지 않았다. 앱 사이트 탭 열기는 queued 접수였다.
- 인계: 마지막 게시 기록까지 현재 폴더/서버 사용자 전용 worktree를 fast-forward하고 locked 새 ingestion 설치·Git 깨끗함·설치된 CLI를 확인한다. 최종 응답은 이 확인 결과를 기준으로 한다. 기존 웹/API·공유 서비스·운영 DB·수집 원문은 변경하지 않는다. 미병합 작업의 검증/리뷰 증거는 격리 폴더에 보존한다.

## 2026-10-12 · 전용 DB·기존 수집 자산 조사

- 관리자 안내를 실제 서버 조회로 확인했다. PostgreSQL18.6 전용 DB 접속·CREATE 권한·빈 public, vector가 설치/설치 가능 목록에 없음을 확인했다. 개인 설정 값은 출력·커밋하지 않았다. 기본 API는 계속 DB 미연결로 자료를 거부한다.
- 기존 MySQL SELECT 전용 helper로 허용 28테이블을 순차 COUNT했다. 법안41,004·여론조사305·후보25,235, 기간·AI 산출물·원문 URL/파일 참조와 누락을 기록했다. 전체 DB의 고정 시점 스냅샷은 아니다.
- 파일/상태/코드는 읽기 조사만 했다. 여론조사 PDF774개 중23개에 헤더 없음, 파싱 자료의 basename 누락/충돌을 확인했다. 폴더의 PDF 수를 검증된 고유 원문 수로 기록하지 않는다. 종료 이벤트·READY·수정 시각을 현재 수집 성공으로 간주하지 않는다.
- D012: 사용자 확정 서비스 도메인 issuedigest.projects.ai.kr. 조사 컴퓨터의 DNS 조회는 이름 해석 실패. DNS/TLS/프록시/콜백·공개 앱 배포는 수행하지 않았다. 계획 Sites 주소를 변경하지 않는다.
- 검증/공개: 문서 링크·기준 숫자·접속 세부정보 제외를 검사한다. 앱 코드·DB/수집 서비스·운영 데이터 변경 없음. 문서-only이므로 spec-driven 전체 구현 절차와 코드 테스트를 반복하지 않는다.
- 게시: [Draft PR #11](https://github.com/DigestWorks/IssueDigest/pull/11) 생성. 앱 첨부를 요청했으나 응답은 미확인이다. 변경 문서9개 상대 링크54개·공개 접속정보 제외·주요 집계값·git diff --check 통과. [사본 기준333f63e CI](https://github.com/DigestWorks/IssueDigest/actions/runs/38227033348) 성공. 기존 PR #10과 그 검토·테스트 증거를 보존한다.
- Sites: [v27 공개 게시](https://lawdigest-rebuild-plan.ijaesinii.chatgpt.site/) 성공. source `60fa91853bcb28c46ea36174de70774ccb3bb2a4`, saved version `appgprj_6ac612dd42708191a7a0c8377be64d48~appgver_5fcc117ac53881919ff4ca475789c41c`, deployment `appgdep_6acca1f9b3ac819199c9f83621765992` native succeeded·URL 확인. 사본 기준 `333f63e`; 이전 v26 보존. HTML12개·로컬 링크/anchor142개·manifest·공개 접속정보 제외 통과. 정적 문서 내용만 바꿨고 이번 변경의 브라우저 화면 검사는 수행하지 않았다.
- 인계: 현재 폴더와 서버 사용자 전용 worktree를 게시 기록91a41d8까지 동기화하고 깨끗한 상태를 확인했다. 기존 코드와 동일하므로 앱 프로세스·의존성·서비스 변경 없음. 이 인계 기록을 포함한 마지막 문서 커밋도 fast-forward하며 결과는 최종 응답 기준 확인한다. 사이트 탭 열기를 요청했으나 앱 응답은 미확인이다. 마지막 문서 커밋의 CI 결과는 PR에서 확인한다.

## 2026-10-12 · 서버 세션·회원 권한·첫 근거 조회 API

- 구현 `73f8684`, 보완 `ed44370`: 실제 PostgreSQL identity/membership/hash-only session 저장과 한 cookie-only 보호 GET. 신뢰된 내부 등록/발급·폐기/회원 권한 관리, secure cookie helper, 외부 연결 없는 기본 app factory를 구현했다. 절대8시간·idle30분은 초기 정책이며 공급자 검증/로그인·초대 승인 기능이 아니다.
- 데이터 경계: 같은 DB transaction에서 세션·활성 사용자·회원 권한을 먼저 확인하고 기존 근거 무결성 로더를 사용한다. 토큰 원문은 DB에 저장하지 않는다. 권한 없는 요청에 자료 내용을 반환하지 않고 모든 보호 응답에 no-store/새 request ID를 넣는다. 401/404/422/503 JSON과 기존200을 canonical OpenAPI/생성 TS로 연결한다.
- 검증: controller가 `ed44370`에서 실제 전용 PostgreSQL18.6 포함 전체 npm run check exit0 확인. Python778·JS134=912개, skip0; lint/format·mypy·TS·SPA·drift 통과. 기존 migration0001↔0002의 근거 보존·해시 저장·활동/만료·폐기·권한 회수·workspace 격리·동시 조회 검증. 초기 callable RED와 동시 요청/오류 모델 보완의 실제 assertion RED/GREEN 증거 보존.
- HTTP: 실제 확인용 Uvicorn 서버에서19회 요청. 두 회원의 동일 근거/인용 순서·같은 세션 동시200, 익명/형식 오류/Bearer/폐기/비활성/절대·idle 만료401, 미가입/다른 공간/없는 자료404, 미구성503. 보호 응답16회 모두 no-store/고유 서버 UUID, 실제 OpenAPI/export 동일. 내부 합성 세션만 쓰고 서버 스레드 종료.
- 리뷰: 독립 작업 리뷰에서 동시 같은 세션의 RR serialization503 및 오류 JSON 생성 계약 누락을 지적했다. 전체 transaction 40001 재시도(총3회)와 정상 오류 모델/생성 TS로 수정해 독립 수정 범위 재검토 통과. 재시도마다 권한/무결성을 새로 확인하며 소진/다른 DB 장애는 고정503이다. ignored 보고서의 denied-retry 테스트 설명 과장을 실제 테스트 내용으로 정정했다. 전체 변경 `04e2efa..193eed8` 독립 리뷰도 지적0으로 통과했다.
- 게시: [Draft PR #10](https://github.com/DigestWorks/IssueDigest/pull/10) 생성·앱 첨부 완료. [검토 기준193eed8의 CI](https://github.com/DigestWorks/IssueDigest/actions/runs/38223884082) 성공.
- 서버: 사용자 전용 ARM64 worktree를 `193eed8`로 fast-forward, locked 설치·웹134개/lint/TS/SPA/drift 통과. 원격 Python 전체나 운영 DB 검사를 수행한 것으로 표시하지 않는다. 기존 reload 부모가 새 storage 패키지 경로를 반영하지 못해 사용자 전용 API 창만 다시 시작했고, 직접/API 프록시10회에서 OpenAPI/export 동일·200상태·401/503 fail-closed/no-store/request ID 확인. 첫 인계는 로컬 로그 폴더가 없어 중단됐고 폴더 준비 후 재검증했다. 공유 서비스/관리자 설정 변경 없음.
- 현재 폴더: `feat/session-evidence-api`에 연결하고 locked npm/uv 설치, 기본 앱 import/OpenAPI/export 일치 확인. 기존 SSH 개발 연결을 통해 직접/API 프록시10회200/401/503·no-store/서버 UUID와 웹200 재확인. 서버와 현재 폴더의 마지막 문서 커밋도 동기화한다.
- Sites: v26 공개 배포 성공(`appgdep_6acc9c45c0d481918af07dd7ce9cc7c7`), saved version `appgprj_6ac612dd42708191a7a0c8377be64d48~appgver_ee3f5e57031c8191a67ea492b977c08f`, source `104c525440823de2757ea26edf39d0a453d46839`. 사본 기준 `80b56e0`; 그 이후 게시/인계 상태는 저장소 원본을 따른다. 이전v25 보존, HTML11개의 로컬 링크/anchor124개·manifest·공개 개인정보 제외 검사 통과. native succeeded URL 확인·사이트 탭 열기 요청 접수. 렌더러/제품 웹 UI를 변경하지 않았다.
- 운영: 실제 로그인·공급자 검증·초대·제품 화면·운영 DB·원문 bytes·AI·SSE·전체P1은 미완료. 공유 DB·운영 자료·서버관리자 설정을 바꾸지 않았다. 공개 요약·현재 폴더 연결을 완료했다. 최종 문서 커밋의 서버 동기화와 CI는 마지막 인계 확인에서 검증한다. 미병합 리뷰 증거는 격리 폴더에 보존한다.

## 2026-10-12 · 검증된 생성 화면 React 렌더러

- 구현 `a0f52b7` + 스타일 격리 보완 `068cb1f`: `@issuedigest/ui`의 CanvasView가 기존 생성 공개 타입/CanvasBundle을 소비한다. 근거·요약·주장 비교·날짜 구간·실제 방향 관계·정확 소수 수치 bar/표를 명세 순서·span으로 표시한다. 선택 근거·workspace·typed 참조·비교 조건·액션을 준비한 후 표시하며 깨진 화면은 부분 내용 없이 거부한다.
- 경계: null 빈 상태·근거 부족·추가 질문을 구분한다. 근거 열기·문서 선택·후속 질문·정렬은 등록 값의 콜백만 전달한다. 실제 API/AI·원문/액션 실행·로그인·SSE·취소·화면 저장·운영 DB는 미연결이다. 선택하지 않은 관계 endpoint는 표시하지 않는다. 문서 제목은 기존 계약에 없어 실제 source_id를 사용한다.
- 검증: controller가 `068cb1f`에서 전용 로컬 PostgreSQL18.6을 포함한 전체 `npm run check` exit0 확인. Python712개(저장39개 포함, skip 없음)·JS134개(UI74개), lint/format·타입·SPA 빌드·계약 drift 통과. 공유 합성 JSON을 기존 Python 계약과 생성 타입을 사용하는 React 테스트가 소비한다. 초기 실제 assertion RED63개, 스타일 containment RED3개 후 GREEN 증거 보존.
- 브라우저: 합성 자료의 내부 QA 화면에서1366/390 가로 넘침 없음·여섯 모듈·명세 구성 변화·빈/자료 부족·Enter 및 실제 Tab+Space의 정확 인용 ID·바깥/안쪽 스타일 격리·콘솔 오류/경고0 확인. 합성 결과를 제품 앱에 연결하거나 AI 생성 결과로 표시하지 않았다. 내부 QA 서버·브라우저와 전용 테스트 DB는 검사 후 종료했다.
- 리뷰: 독립 작업 리뷰의 CSS 범위 지적을 수정하고 재검토 통과. 전체 변경 리뷰의 fixture 주석·검증 기준 SHA 지적을 `cdaaec8`에서 정정하고 한 번의 수정 범위 재검토로 종료했다. 잔여 지적 없음. ignored 리뷰/검증 기록은 미병합 PR 검토가 끝날 때까지 격리 폴더에 보존한다.
- 게시: [Draft PR #9](https://github.com/DigestWorks/IssueDigest/pull/9) 생성·앱 첨부 완료. `83b7b7e`의 [GitHub CI](https://github.com/DigestWorks/IssueDigest/actions/runs/38218480943) 성공. 최종 게시 메타데이터는 문서만 변경한다.
- 서버/폴더: ARM64의 사용자 전용 worktree `cdaaec8`에서 locked 설치·웹 lint/타입·JS134·SPA·계약 drift 통과. 원격 Python/운영 DB 검사를 실행한 것으로 표시하지 않는다. 기존 tmux 웹/API 유지, 직접/프록시 및 로컬 연결 HTTP200·요청 ID 확인. 현재 사용자 폴더를 `feat/canvas-renderer`에 연결하고 locked 설치·UI export/CSS 경로를 확인했다. 마지막 문서 커밋도 개발 서버에 동기화한다.
- Sites: v25 공개 배포 성공(`appgdep_6acc8dfe53d08191a7267f919c17ff40`), 이전v24 보존. 사이트 source `078f41465efdbf919a737d2a8e69e2bd1dde2a27`, 저장소 문서 사본 기준 `83b7b7e`. 이후 게시 기록은 저장소 원본을 확인한다. 공개 요약의 로컬 링크·상태·건수·접속 세부정보 제외 검사 통과, 사이트 탭 열기 요청 접수.

## 2026-10-12 · 엔진 확정·첫 PostgreSQL 저장

- D011: 사용자 선택 PostgreSQL·pgvector·PydanticAI/DBOS 확정. A001~A003 추천/대안은 당시 비교 이력으로 대체 관계를 보존했다. [공식 근거·호환 범위·검증 기준](../research/engine-selection.md)에 선택과 실측을 구분했다.
- 구현: typed storage uv 패키지, SQLAlchemy2.1.4/Alembic1.20.0/psycopg3.3.6 고정. 문서·버전·표현·인용의 전역 불변 ID·공간/부모 FK, 스냅샷 인용 순서·내용 해시·동일 ID 재전송, 원자적 초기 outbox와 최초 마이그레이션.
- 실제 DB 검증: 새 전용 로컬 PostgreSQL18.6 합성 DB에서 저장39개, 전체Python711+JS60·lint/타입/SPA/계약 drift 통과. controller가 최종 `aaf810a`에서 동일 전체 명령을 직접 실행하고 exit0 확인. DB 미설정은 수동 로컬 통합 검사 skip이며 CI는 명시적 전용 서비스/URL·미설정 실패로 필수 실행한다.
- 리뷰: 독립 작업 리뷰의 AUTOCOMMIT 원자성·commit 응답 불확실 안내 수정, 전체 리뷰의 PDF signed-zero JSONB 정규화 수정. 각각 실제 DB RED/GREEN 및 범위 재검토 통과. 최종 잔여 지적 없음. 유실 commit 응답을 실제 장애로 주입하는 검증은 수행하지 않았으며 같은 ID 재확인 정책을 문서화했다.
- 운영 경계: PostgreSQL 연결 준비 항목 작성. 개발 서버 DB 설치·공유 서비스/기존 운영 데이터 변경·공급자 유료 호출 없음. 파일 원문 참조는 실제 파일 보존·해시 대조 완료가 아니다. workspace 필터는 로그인/멤버십 검증이 아니다. 검색·복구·월10만 원 실측과 전체P1은 미완료.
- 게시/인계: [Draft PR #8](https://github.com/DigestWorks/IssueDigest/pull/8)을 PR #7 브랜치 위에 게시·앱 첨부했다. `def2244`의 [GitHub CI](https://github.com/DigestWorks/IssueDigest/actions/runs/38195790846) 통과. 개발 서버의 개인 worktree를 같은 기준으로 동기화하고 ARM64 의존성·전체 검사 Python711+JS60·lint/타입/SPA/drift 통과. 서버에는 DB를 설치하지 않았으며 SSH 임시 역방향 연결로 로컬 전용 PostgreSQL18.6을 사용했다. 검증 후 임시 연결 종료, 기존 웹/API 직접·프록시 HTTP200·요청 ID 재확인. Sites v24 공개 배포 성공(`appgdep_6acc46d38e988191b16c6446fa9e5b26`), 이전v23 보존. 사이트 문서 사본은 `4b68ec7` 기준이며 이후 게시 기록은 저장소 원본을 확인한다. 사용자 폴더도 `feat/postgres-storage`로 연결하고 locked 설치·storage import를 확인했다. 리뷰 증거는 기존 격리 폴더에 보존한다.

## 2026-10-12 · 개발 서버 환경·실행 검증

- 담당/브랜치: controller · `docs/development-server-access`; 서버 `codex/jaesin-development`, 검증 기준 `806e22e`. 사용자 승인 범위에서 도구·worktree·의존성·웹/API를 준비했다. 제품 코드·공개 계약·고정 버전·lockfile 변경 없음.
- 사용자 전용 Node24.21.0/npm11.19.0/uv0.11.4/Python3.13.12 설치 및 PATH 선택 파일 구성. 공유 시스템 도구·기존 사용자 uv 보존. npm/uv lockfile 설치 성공, ARM64 전체 검사 Python672+JS60·lint·타입·SPA 빌드·계약 drift 통과.
- 서버 main은 깨끗한 초기 커밋으로 보존하고 중첩 worktree는 로컬 exclude로 제외했다. 지정 웹15173/API18090은 loopback에만 바인딩. SSH 터널 직접/프록시 HTTP200·JSON·UUID v4·실제 OpenAPI 일치 확인. 브라우저 실제 연결 성공·1366/390 가로 넘침 없음·콘솔 오류/경고0. tmux 종료 후 두 포트 해제·재시작 성공, 앱과 터널 실행 상태 유지.
- 저장소가 PUBLIC임을 GitHub에서 확인해 이전 비공개 표기를 정정했다. 공개 최신 문서에서 접속 주소·계정·키 경로를 제거하고 저장소 밖 개인 설정에 보관한다. 이전 커밋/PR에 접속 메타데이터는 남으며 키 본문·인증값은 커밋하지 않았다. 저장소 가시성·Git 이력은 변경하지 않았다.
- 미검증: 운영 배치·DB/수집/AI·앱 인증, 실제 데이터·서버 전용 자원·월 비용·서버 개인 push 권한. 관리자 설치·공유 서비스·운영 데이터 변경 없음. 개발 실행을 전체 P1이나 운영 배포 완료로 표시하지 않는다.
- 다음: 서버 자원·비용·기존 데이터 확인 및 DB·검색·실행기·배치·인증 판단. 새 유료 자원/API 키 설정은 아직 필요 없다. 기존 Draft PR #7을 현재 범위로 갱신·앱 첨부 완료, 기록 커밋 `e3c3f12`의 [GitHub CI](https://github.com/DigestWorks/IssueDigest/actions/runs/38192821177) 성공. Sites v23 배포 성공(`appgdep_6acc3b1ac77881918bd90ba41f0b47bf`), 이전 v22 보존. 공개 요약의 상태·로컬 링크·접속 메타데이터 제외 검사 통과. 사이트 사본은 `e3c3f12` 기준으로 이후 게시 메타데이터는 저장소 원본을 확인한다.

## 2026-10-12 · 개발 서버 접속·준비 상태 확인

- 담당/브랜치: controller · `docs/development-server-access`. 서버 안내와 SSH 읽기 확인을 [서버 확인 기록](https://github.com/DigestWorks/IssueDigest/blob/docs/development-server-access/infra/development-server.md)에 정리했다. 코드·공개 계약·의존성 변경 없음.
- 사용자 요청으로 키를 저장소 밖 SSH 전용 경로로 옮기고 권한 600을 적용했다. 키 내용·인증값은 기록/커밋하지 않았다. SSH 접속과 안내 파일·기초 자원·도구·Git 상태·포트 확인 완료.
- ARM64·4 CPU, 메모리 약 23.4GiB(가용 12.9GiB), 디스크 여유 약 39GiB. 순간 관측값이며 전용 할당·월 비용을 뜻하지 않는다. 개발 포트 15173/18090은 listener 없음, Docker 소켓 관리 권한 없음.
- 도구 버전이 고정 기준과 다르며 uv는 사용자 경로에 설치되어 있으나 비대화 SSH PATH에는 없다. 시스템 설치·환경 수정·Git fetch/checkout·의존성 설치·앱 기동·DB·운영 서비스 변경은 수행하지 않았다.
- 서버 main은 초기 README와 .gitignore만 있는 깨끗한 상태. GitHub 읽기에서 최신 `feat/execution-contracts` 확인; PR #1~#6 미병합으로 main에는 실행 코드가 아직 없다. GitHub push 권한은 미검증.
- 다음: 사용자 전용 도구·최신 코드 worktree·lockfile 설치와 원격 검증. 관리자 협의는 자원 배정·공존 서비스·비용·DB/백업 배치안을 구체화한 뒤 진행. 기존 수집 서버와의 관계·실제 데이터 현황은 미확인.
- 검증: 변경 문서의 상대 링크·고정 버전·지정 포트 명령안과 저장소 스크립트 일치, diff 공백·키 본문 제외 검사 통과. 문서 변경이므로 앱 테스트를 재실행하지 않았다. 원격 앱 실행 명령과 터널은 아직 명령안. [Draft PR #7](https://github.com/DigestWorks/IssueDigest/pull/7) 게시, 기록 커밋 `01cc3d3`의 [GitHub CI](https://github.com/DigestWorks/IssueDigest/actions/runs/38191551337) 통과. Sites v22 공개 요약 배포 성공(`appgdep_6acc367937b081919b14cc437c830f22`), 이전 v21 보존. 공개 요약에 SSH 주소·계정·키 경로는 포함하지 않는다. PR #7 앱 첨부 완료, 사이트 탭 열기 요청도 접수됨. 직접 URL로도 인계한다.

## 2026-10-12 · 실행 계약 검토·인계

- 구현 `b408ad6` + 배열 최소 개수 보완 `e2255d7`. 실제 API 스키마의 14개 필드 RED 후 보완 GREEN, Python/JSON의 개수·중복 검증 보존. 작업 리뷰·수정 범위 재검토·전체 변경 리뷰 통과, 최종 신규 지적 없음. controller의 reviewed-head 전체 검사 672 Python + 60 JS 및 lint/타입/빌드/drift 성공. 의존성·HTTP 경로·기존 도메인 정책·웹 UI 변경 없음.
- [Draft PR #6](https://github.com/DigestWorks/IssueDigest/pull/6)을 선행 PR #5 위에 게시했다. GitHub CI·Sites·사용자 폴더 연결은 이 기록 이후 완료 상태를 갱신한다. 자동 PR 첨부 요청은 응답하지 않아 직접 URL로 공유한다. 미병합 PR의 ignored SDD 검토/실행 증거는 이 작업의 격리 폴더에 보존한다.

## 2026-10-11 · 실행·이벤트·화면·사용량 부분 계약

- 역할별 `contract_values.py`, `canvas_modules.py`, `execution.py`, `canvas.py`, `usage.py`, `execution_bundle.py`에 순수 모델/함수를 구현했다. 새 계약의 strict 버전/정수/문자열·UTC 시각·tuple/frozen·추가 필드 거부를 적용하고 기존 원문/연구 정책·두 HTTP 경로·웹 UI를 보존한다.
- 입력 자료 순서와 원문 질문·실행 버전을 SHA-256에 고정하고 실제 입력 동등성으로 제출 reuse/conflict를 판정한다. 연속 seq 이력을 fold하여 취소/미확인/완료 경합·늦은 모듈을 거부하고 실패/취소의 base 화면과 비용 확인을 보존한다.
- Canvas는 허용 모듈/액션·선택 원문/인용 합집합·주장/관계/관측 존재·차트의 알려진 같은 조건·부모/expected ID를 검사한다. CallAttempt는 상태별 시각/결과와 prefix별 유료 적격성을 기록한다. 이 함수들은 실행·권한·서버 저장 인증이 아니다.
- Usage는 서울 완전한 달·월 전체 운영비 10만 원·다른 비용·정밀 정수 금액·unknown hold·각 retry 합계·실제 초과비용과 정산을 검사한다. 전체 bundle은 모듈 발표/성공 revision·attempt/reconciliation·가격/예약/entry를 연결한다. 제공된 다른 run의 정상 historical revision도 검사하며 최소 ancestor 목록을 선택하지 않는다.
- 검증: 순수 알고리즘 일곱 개 각각 callable scaffold에 대한 실제 assertion RED를 확인하고 focused GREEN과 실제 schema 등록/기존 component 동일·collision/입력 불변·생성 TS compile 소비자를 확인했다. 상세 명령/출력·self-review는 ignored `.superpowers/sdd/execution-contracts/task-1-report.md`와 evidence에 보존한다. 초기 `npm run check` 1회 통과: Python 656개·JS 60개, Ruff/format/mypy·ESLint·양쪽 TS 타입·SPA 생산 빌드·생성 계약 drift 통과. 유료 적격 cursor는 실제 dispatch 직전 권한 재확인·물리적 취소 경합 보장의 증거가 아니며 worker/DB 처리는 후속이다.
- 리뷰 보완 1차: 실제 OpenAPI의 ID 배열에 문자열 `minLength`가 생성되는 P2를 확인했다. 공통 tuple 길이 제약을 AfterValidator보다 먼저 적용하여 `minItems`를 생성하고 runtime cardinality/uniqueness를 보존했다. 실제 앱의 14개 배열 assertion RED 후 focused 286개·전체 `npm run check` 1회(Python 672개·JS 60개, lint/타입/SPA 빌드/계약 drift) 통과. OpenAPI/TS를 재생성했으며 TS 결과는 동일하다. 수정 부분 독립 재리뷰 대기다.
- 인계 대기: 독립 작업·전체 변경 리뷰, Draft PR, Sites v20 이후 공개 요약, 사용자 폴더 연결은 controller가 담당한다. 결합 완료 checkbox를 닫지 않았다. 신규 의존성·외부/유료 호출·비공개/운영 자료·실행기·저장소·SSE/제품 API·UI/AI 구현은 없다.

## 2026-10-11 · 개체·주장·관계·비교 조건 계약

- 동일 이름의 독립 개체와 미해결/미검토를 보존하고 외부 identity 3항 키 충돌을 거부한다. 근거 있는 원문 주장/관측/추론 입력과 inference에만 필요한 가공 기록을 구분한다. 검토는 UTC 시각·방법/버전·인용과 귀속/내용/관계 범위를 기록하며 실제 인증 행위·주장 진실을 보장하지 않는다.
- `issuedigest-relations-v1`의 6종 방향/양 끝 종류와 제공 객체 존재를 검사한다. 근거 없는/미등록 인과/자기 관계·다른 공간·없는 endpoint를 거부한다. mentions는 source 문서 버전의 인용만 허용한다. 자동 역관계·그래프 투영은 없다.
- 정확한 Python date/JSON YYYY-MM-DD 기간·strict 양의 표본 크기·최대128자 정밀 ASCII 소수 문자열과 원문/결측을 보존한다. 비교는 모든 조건과 value 결측을 순서대로 보고하고 different를 missing보다 우선한다. 같은 조건의 다른 값·순서만 다른 차원은 same_context이며 합산/분포는 not_evaluated다. 결과 ID·사유·status 모순도 거부한다.
- ResearchBundle의 전체 공간·문서/버전 일치·고유 인용/표현/검토 ID·typed 참조·검토 citation subset을 검증한다. 같은 문서/버전의 다른 파싱 표현은 허용한다. 검증 대상은 제공된 묶음이며 저장소 전체 unique enforcement는 아니다.
- 실제 OpenAPI components를 단일 등록 경로로 확장하고 생성 TS와 공개 aliases/compile 소비자를 갱신했다. 기존 HTTP 두 경로·상태/원문/인용·웹 UI를 보존했다. 종속성·외부/유료 호출·비공개/운영 자료 사용 없음.
- 초기 구현 검증: focused 새 계약+API 228개 통과, Ruff/mypy·공개 생성 타입 소비자 통과. 전체 `npm run check` 1회 통과: Python 380개·JS 60개, Ruff/format/mypy·ESLint·양쪽 타입 검사·SPA 생산 빌드·생성 계약 drift 검사 통과. RED/GREEN·수정 파일·self-review는 로컬 SDD `research-contracts/task-1-report.md`에 보존한다.
- 인계: 독립 작업 리뷰 통과. 전체 변경 리뷰의 P2 지적(같은 항목의 결측/다름 ID 겹침과 필수 항목의 결측 사유)을 `e902cb4`에서 보완했다. JSON 회귀 RED 8개 실패·정상 5개 통과 후 GREEN 107개, 수정 부분 재리뷰 지적 없음. 컨트롤러 최종 전체 검사도 393 Python + 60 JS 통과. 초기 비교 알고리즘만의 독립 RED 증거 범위는 제한적이며 이를 뒤늦게 충족했다고 주장하지 않는다. 현재 동작 테스트·코드 리뷰로 구현을 검증했다. 사용자 폴더 연결·실제 API 계약 및 웹 기동 확인 완료. Sites v20 공개 게시와 사용자 폴더 연결까지 확인하여 C1~C4 결합 완료를 체크했다. 나머지 P1·출처 시간 정밀도·재수집·내용 비교 fingerprint·Run/Event/Canvas/Usage·실제 자료/추출/저장/권한·AI·Neo4j는 미완료.

- 게시: [Draft PR #5](https://github.com/DigestWorks/IssueDigest/pull/5), base `feat/source-evidence-contracts`, 구현 `d82a8f1` + 보완 `e902cb4`. 보완 커밋의 [GitHub CI #38144301870](https://github.com/DigestWorks/IssueDigest/actions/runs/38144301870) 성공. Sites v20 공개 게시 성공. 사본 기준 `06dda30` 이후 상태는 저장소 원본에서 확인한다. 앱의 자동 PR 첨부·사이트 열기 요청이 응답하지 않아 직접 URL로 공유한다.

## 2026-10-11 · 첫 원문·파싱·인용 계약

- 원문 문서/버전과 파싱 표현을 분리하고 모든 내부/원문 객체 ID를 UUID4, 해시는 소문자 SHA-256, 수집 시각은 시간대 필수·UTC 직렬화로 검증한다. 원문 bytes를 받지 않으므로 raw hash는 형식만 검사한다.
- 중첩 frozen 모델·tuple, JSON 왕복·extra 거부, strict 오프셋/페이지/표본/유한 PDF 좌표를 구현했다. 원문/표현/인용 ID 연결, 페이지 범위·표/셀·인용 중복과 정확한 quote/context를 검증한다. 파서 버전별 표현·인용의 공존은 계약 테스트이며 DB 중복 제거 증거가 아니다.
- 빈 표·빈 셀·좌표 없는 PDF를 유지하고 통계 조건은 null을 채우거나 합산하지 않는다. `validate_citation` 결과는 anchor `matched`와 support `not_evaluated`를 구분한다. Python 검증 생략 construction/copy는 입력 경로로 사용하지 않도록 패키지 README에 기록했다.
- FastAPI OpenAPI components에 모델을 등록하고 기존 두 HTTP paths와 상태·요청 ID를 유지했다. 충돌 시 오류를 내며 `/openapi.json`과 export 스크립트가 같다. OpenAPI/TS 타입을 생성하고 웹 클라이언트에서 공개한다.
- `getCitationUtf16Range`는 Python code point→JS UTF-16 범위를 변환하며 quote/context 오류를 거부한다. 공통 합성 UTF-8 fixture로 한글·BMP 밖 이모지·결합 문자·NFC/NFD·선행/후행 공백을 검사한다. grapheme 분할·PDF 렌더링은 범위 밖이다.
- 검증: focused Python domain 140개, API 포함 150개 및 TS 인용 변환 40개 통과. 전체 `npm run check` 1회 통과: Python 150개·TS 60개, Ruff/mypy/ESLint·양쪽 타입·생산 SPA 빌드·생성 계약 drift 검사 통과. RED/GREEN 상세는 로컬 SDD `task-1-report.md`에 보존한다. 새 종속성·외부 호출·운영/비공개 자료 사용 없음.
- 후속: 출처 연/월/일 시간 정밀도·재수집 관측·내용 비교 fingerprint·실제 parser/원문 저장, 주장/관계·비교 조건, Run/Event/Canvas/Usage·저장·권한 검증. 전체 P1과 제품 기능은 미완료.
- 검토: `9271a0a`에서 독립 작업 명세/품질 리뷰와 전체 변경 리뷰 모두 지적 없음. 컨트롤러 전체 검사도 통과. 사용자 폴더 `/data/lawdigest/IssueDigest`에 브랜치를 연결하고 잠긴 설치·전체 검사 150 Python + 60 JS를 다시 통과했다. 별도 작업 공간의 검증 기록은 PR 병합 전까지 보존한다.
- 게시: [Draft PR #4](https://github.com/DigestWorks/IssueDigest/pull/4) 생성, 선행 PR #3 위에 쌓았으며 미병합. 구현 커밋 `9271a0a`의 [GitHub CI](https://github.com/DigestWorks/IssueDigest/actions/runs/38137640138) 성공. Sites v19 공개 배포 성공. 스냅샷 기준은 `63f88fe`이며 최신 상태는 이 저장소다. 앱의 브라우저 열기·PR 첨부 요청이 응답하지 않아 직접 URL로 공유한다.

## 2026-10-11 · 제품 계약 조사

- 기존 LawDigest·별도 파이프라인 원격 main SHA를 GitHub API로 확인했고 기존 조사 기준과 일치했다. IssueDigest 실행 기반은 `4e63421`, main은 PR 미병합 상태다.
- 원문 버전과 파싱 결과 분리, 정확한 인용 위치, 구조/원문 위치/주장 지지 검증 분리, 조건 있는 수치·관계, 저장 순번 이벤트, 불명확 유료 호출, 검증된 모듈과 불변 화면 버전·예약/정산의 설계 제안을 기록했다.
- 기존 발의자 결측에 따른 자료 제외·여론조사 불완전 분포 허용·요약 중심 검색·로컬 JSONL 기록의 재사용 경계를 정리했다. 기존 운영 데이터/공급자 호출·테스트 실행은 하지 않았다.
- Decisions public beta와 역할을 공식 문서로 확인했다. PydanticAI DBOS의 일반 모델 스트리밍 버퍼링과 live handler/중복 처리 경계를 확인해 실행기 비교 실험에 반영했다. 새 프로젝트 키·모델 품질·지연·비용은 미검증이다.
- 조사 완료는 계약 모델/API·저장·권한·AI/화면 구현 완료가 아니다. PostgreSQL·검색·DBOS/Temporal·json-render를 채택하지 않았다.
- 검증: 상대 문서 링크·고정 코드 근거·문서 상태 구분·변경 공백 확인. 런타임 코드를 바꾸지 않았으므로 로컬 전체 테스트를 반복하지 않는다.
- 사용자 입력: 지금 서버·키 추가 작업 불필요. 실제 평가 자료 단계 전에 첫 이슈·질문·원문 범위를 함께 선정한다.
- 게시: [Draft PR #3](https://github.com/DigestWorks/IssueDigest/pull/3) 작성·연결. base는 개발 기반 PR #2의 브랜치이며 병합하지 않았다. 문서 커밋 `8988f33`의 [GitHub CI](https://github.com/DigestWorks/IssueDigest/actions/runs/38134714271) 성공. Sites v18 공개 배포 성공, 네 영역으로 요약하고 설계 제안/제품 미구현 상태를 표시했다. 공개 사본 기준은 `8988f33`이며 최신 상태는 저장소 원본이다.

## 2026-10-11 · 웹·API 개발 실행 기반

- 작업: [Task 1](../changes/development-foundation.md). 기준 커밋 `862b2d94c20902ad3f64c5534956100bd5d8830b`, 브랜치 `feat/development-foundation`. P1 중 독립된 실행·계약·검증 기반만 구현했다.
- Node 24.21.0·npm 11.19.0·Python 3.13.12·uv 0.11.4를 사용했다. npm workspaces(웹·API 클라이언트)와 uv workspace(API·Python 도메인), 정확한 직접 의존성·잠금 파일, 루트 설치·개발·검증 명령을 구성했다.
- API의 `/health/live`, `/api/v1/status`는 지정한 JSON과 서버 UUID `X-Request-ID`를 반환한다. 오류에도 요청 ID를 부여한다. 상태는 API 프로세스의 응답 여부이며 DB·워커 준비 완료가 아니다.
- Python 모델/FastAPI OpenAPI에서 OpenAPI·TypeScript 타입을 생성·버전 관리한다. 재생성 비교와 런타임 응답 검증을 포함했다. 웹은 Framework SPA, 같은 출처 개발 프록시, 한국어 빈 자료 상태와 실제 연결 확인만 제공한다.
- TDD: API 7개 실패 후 7개 통과. 클라이언트·화면 20개 실패 후 20개 통과. 잘못된 응답·HTTP/네트워크 실패·본문까지 포함한 시간 초과·화면 확인 중·실패·재시도를 검증했다.
- 자동 검증: `npm run check` 통과. Python Ruff·mypy·pytest, TypeScript ESLint·타입·Vitest, 생산 SPA 빌드와 계약 변경 검사. 같은 절차의 [GitHub Actions 실행 #38133178226](https://github.com/DigestWorks/IssueDigest/actions/runs/38133178226)이 기반 코드 커밋 `d132583`에서 성공했다. 원격에서도 테스트 27개·lint·타입·생산 빌드·계약 검사를 통과했다.
- 실제 스모크: 컨트롤러 확인 완료. API 직접 연결과 웹 프록시의 두 엔드포인트에 정확한 JSON/UUID v4, 404에 UUID v4, 웹 HTTP 200을 확인했다. 데스크톱 1366×900·모바일 390×844에서 가로 넘침 없이 hydration을 확인했다. 실제 응답 지연 때 접수 안내·확인 중 비활성 버튼, API 중단 때 실패·재시도, 복구 후 재시도 성공을 확인했다. `npm run dev`로 두 서버 기동, Ctrl+C 후 두 포트 해제도 확인했다. favicon 404는 로컬 SVG로 수정했고 새 브라우저 콘솔 오류·경고는 각 0건이다. 생산 빌드의 `build/client`도 QA용 정적 미리보기에서 hydration·실제 동일 출처 상태 요청·콘솔 오류 없음으로 확인했다. 이는 빌드 검증이며 운영 배포는 아니다. 브라우저 산출물은 로컬 `output/issuedigest-foundation`에만 보관하고 커밋하지 않는다.
- 범위 밖: 기준 DB·검색·실행기·인증 결정, 워커·자료 수집·AI·권한·저장·운영 배포. 기존 P1 미완료 항목과 계획 Draft PR #1의 검토 이력을 유지한다.
- 검토 후속: 명세·코드 품질 검토와 전체 변경 리뷰를 통과했다. 본문 수신 시간 초과 때 이미 받은 서버 요청 ID를 보존하도록 `bae8e89`에서 수정했다. 기존 회귀 테스트에 ID 검증을 추가하여 1개 실패·19개 통과의 RED 후 전체 27개 테스트·검사를 통과했으며, 수정 범위 재검토에서 지적 해결과 새 문제 없음이 확인됐다. 통합 개발 실행기의 프로세스 종료 지원·검증 범위를 Linux로 문서화하고 Windows는 두 앱의 별도 터미널 실행·종료를 안내했다. 앱 코드는 변경하지 않았다.
- 다음 행동: [PR #2](https://github.com/DigestWorks/IssueDigest/pull/2) 검토와 자료·인용·실행 계약 정의. 운영 서버 설치·유료 외부 호출은 수행하지 않는다.
- Sites: v17 공개 게시 성공. 웹·API 개발 기반 완료와 전체 P1·제품 기능 미완료를 구분했다. 공개 문서 사본은 `dbbce9a` 시점이며 최신 원본은 저장소 문서다.

## 2026-10-11 · 모노레포 구현 준비

- 로컬 경로: `/data/lawdigest/IssueDigest`. 기존 클론을 원격 저장소와 같은 이름으로 변경하고 커밋 이력을 보존했다.
- `origin`: `https://github.com/DigestWorks/IssueDigest.git` · fetch/push 연결 확인.
- 브랜치: `docs/issuedigest-implementation-plan`. 기존 Draft PR #1에서 계획과 준비 내용을 함께 검토한다.
- 웹·API·워커·도메인·연결기·에이전트·UI·운영·평가 폴더와 책임 README를 추가했다. 의존성·실행 코드·배포 구성은 아직 없다.
- `AGENTS.md`와 문서 안내에 읽는 순서·결정·작업·검증·인계 방법을 정했다. Linear는 사용하지 않는다.
- 검증: 로컬 문서 링크·디렉터리 경로, Git 연결, 변경 공백, 비밀 설정·생성 파일 제외 규칙 확인. 실행 가능한 앱이 없어 런타임 테스트는 수행하지 않았다.
- 다음 행동: 공유 계약·언어별 개발 설정부터 구성하고 실제 실행·타입·테스트 결과를 기록한다.
- Sites: 이번 준비 내용의 요약 반영 대기. 결정·진행의 최신 원본은 이 저장소다.

## 2026-10-11 · 계획·배포 정리

- 조직·서비스·새 저장소 지정 반영: DigestWorks / IssueDigest.
- 첫 사용자: 우리 둘의 조사·근거 비교. 월 운영비 상한: 10만 원.
- 기존 백엔드·AI 파이프라인 서버 존재 확인. 상세 정보는 사용자 요청에 따라 추후 반영.
- 구현 계획·요구사항·결정·작업·와이어프레임 기록 작성.
- 와이어프레임 Vercel 프로젝트의 `paused=true`, 배포 삭제·자동 Git 연결 해제 검증. 실행 코드·개인 저장소는 유지.
- 계획 초안 PR과 IssueDigest 계획 사이트를 게시했다. Sites v15 배포 성공을 확인했다.

## 게시·검토

- 계획 PR: [#1 · 구현 계획과 결정·진행 기록](https://github.com/DigestWorks/IssueDigest/pull/1) · Draft, 병합 전.
- Sites: [IssueDigest 구현 계획](https://lawdigest-rebuild-plan.ijaesinii.chatgpt.site/). 초기 계약 단계에서 v20 공개 게시에 성공했다. 이후 게시 버전은 각 날짜의 기록과 현재 작업을 따른다. 원문·파싱·인용과 개체·주장·관계·비교 계약·검증·PR 요약을 반영했다. 계획·개발 기반 상태와 저장소 문서·PR 검토 경로를 반영했다.
- 구현 시작: 로컬 폴더·협업 문서와 웹·API·상태 계약·개발 검증 기반 완료. 실제 스모크 결과·코드 검토는 개발 기반 작업에 기록한다. PR #1~#5는 Draft이며 병합하지 않았다.

## 서버 정보를 기다리지 않고 진행 가능한 항목

- 기준 데이터·인용·실행 이벤트·화면 명세 계약 검토.
- 기존 수집/가공 규칙과 회귀 테스트의 재사용 범위 평가.
- 첫 이슈·대표 질문·원문 조건 선정과 실제 평가셋 준비.
- 검색·작업 복구·권한·비용의 결정 실험 설계.

유료 외부 호출이나 운영 서버 설치를 시작한 것으로 표시하지 않는다.

## 게시 검증 증거

- Sites v20 source: `d5ee646d64f65fa2dbc262d08a478dbc788e155a`, saved version `appgprj_6ac612dd42708191a7a0c8377be64d48~appgver_c69a26fc4d788191a2c2b21dc7ceafc9`, deployment `appgdep_6acb93b276408191ba940bc1a5681c61`, 상태 `succeeded` (2026-10-11 22:48:50 한국 시간). 기존 공개 설정 유지. 1366×900·390×844에서 가로 넘침 없음, 제품 계약 4행·최종 테스트 수·PR #5·이전 v19 보존 링크 정상, 현재/보존 문서 로컬 파일 링크·anchor 정상, 콘솔 오류/경고 0건. 사본 기준 `06dda300bb5171e5f41cf94e24338aa26f682d61`; 최신 기록은 저장소 원본이다.
- 최종 실행 코드 `e902cb4`: 구현자·컨트롤러 전체 검사 각각 통과(393 Python + 60 JS), 독립 작업·전체 변경·지적 보완 후 수정 부분 리뷰 통과. [코드 CI #38144301870](https://github.com/DigestWorks/IssueDigest/actions/runs/38144301870) 성공. 이후 변경은 문서·게시 기록만이다.
- 사용자 폴더 `/data/lawdigest/IssueDigest`의 `feat/research-contracts`: 실제 API `/openapi.json`과 생성 계약이 동일하고 ResearchBundle/ComparisonAssessment 등 새 모델과 기존 두 HTTP 경로만 존재, 웹 HTTP 200 확인. 개발 서버 5173/8000은 로컬 확인용이며 운영 배포가 아니다. 별도 작업 공간의 리뷰/RED·GREEN 기록은 PR 병합 전까지 보존한다.

- Sites v19 source: `36ece7df45854a5db46d1c9690641a3d5bfd09d9`, deployment `appgdep_6acb7b68bcb08191a9b187bc7327f92e`, 상태 `succeeded` (2026-10-11 12:05 UTC). 기존 공개 설정 유지. 로컬 1366×900·390×844에서 새 계약 요약·내부 anchor와 보존 파일 링크 정상, 가로 넘침 없음, 콘솔 오류/경고 0건. v18 이전 조사안을 별도 보존했다. 저장소 원본/공개 사본 기준을 구분했다.
- 원격 검증: 구현 `9271a0a` CI #38137640138, 검토/PR 문서 `63f88fe` CI #38137818441 성공. 제품 구현 코드는 독립 작업/전체 리뷰 이후 변경하지 않았다.
- 사용자 폴더의 실제 API `/openapi.json`에서 EvidenceBundle과 기존 상태 경로만 확인, 웹 HTTP200 확인. 개발 서버는 로컬 5173/8000에서 기동 중이며 운영 배포가 아니다.

- Sites v18 source: `02565938f167a9a6c0c5203b5bfdf6569640e8f6`, deployment `appgdep_6acb6fc608108191b1f9a302100aed7b`, 상태 `succeeded`. 기존 공개 설정 유지. 1366×900·390×844에서 가로 넘침 없음, 새 요약 4행·전체 내부 링크 정상, 콘솔 오류/경고 0건 확인.

- Sites v17 source: `721cf362a2d61a7aa2a7bb6013e18a04857ff700`, deployment `appgdep_6acb6a2969d08191b6f8999e42beb5a4`, 상태 `succeeded` (2026-10-11 10:51 UTC). 기존 공개 설정을 유지했다. 1366×900·390×844에서 가로 넘침 없음·내부 링크 정상·콘솔 오류/경고 0건을 확인했다. 아래 v15 증거는 이전 게시 기록이다.

- Sites v15 source: `a96fae750ac020212d239e3d69344718cd6c3f02`, deployment `appgdep_6acb5724c784819184713ada7b2a8a8a`, 상태 `succeeded`.
- Vercel: 배포 목록 0개, `paused=true`, Git 연결 없음. 대표 주소와 두 과거 배포 주소는 HTTP 404 `DEPLOYMENT_NOT_FOUND`.
- 화면: 1366×1000·390×844에서 문서 가로 넘침 없음, 내부 메뉴 이동 확인, 콘솔 오류 0건. 문서 링크·보존 원문·계획 사본 일치 확인.


## 2026-10-12 · 사용자 폴더 연결·게시 준비

- 사용자 폴더 `/data/lawdigest/IssueDigest`의 깨끗한 상태를 확인하고 `feat/execution-contracts`를 연결했다. 격리 구현 폴더는 같은 커밋에 detached로 보존했다. 기존에 이 작업이 실행한 API 프로세스만 중지하고 새 브랜치의 통합 개발 실행을 기동했다. 실제 `/openapi.json` HTTP 200과 생성 JSON의 정확한 일치, RunHistory/RunExecutionBundle/CanvasBundle/UsageBook/BudgetAssessment 및 차트 minItems2·기존 HTTP 두 경로를 확인했다. 웹 HTTP 200. 새로운 제품 화면/AI 실행 검증은 아니다.
- 검토된 구현 `e2255d7`의 [GitHub CI #38150424568](https://github.com/DigestWorks/IssueDigest/actions/runs/38150424568) 성공. Docs-only 인계 커밋 뒤의 최종 HEAD CI는 마지막에 다시 확인한다. Sites의 이전 v20 기록을 보존하고 새 공개 요약·docs 사본 게시를 준비 중이다. 결합 체크는 게시 성공 후 처리한다.


## 2026-10-12 · 실행 계약 결합 완료·Sites 게시

- C1~C5의 구현·독립 작업/수정 범위/전체 변경 리뷰·Draft PR #6·사용자 폴더/실제 API 확인·Sites 공개 게시를 마쳤다. 최종 code 검증은 `e2255d7`의 컨트롤러 전체 672 Python + 60 JS 및 lint/타입/SPA/drift. 공급자 호출·실제 과금·저장·SSE·인증·renderer/AI·전체 P1은 미완료다.
- [Sites v21](https://lawdigest-rebuild-plan.ijaesinii.chatgpt.site/) 공개 게시 성공. source `2d5d6afc7ab659985e71bd9439b972b73ab4f5a0`, saved version `appgprj_6ac612dd42708191a7a0c8377be64d48~appgver_2819fa8720c481918101b0b01fab19dc`, deployment `appgdep_6acba95b486c8191b665b1b05bd473f8`의 native succeeded를 확인했다. 이전 v20을 추가 보존하고 v14/v18/v19·데이터/와이어프레임 기록을 유지했다. docs 사본은 `cac6258` 기준이며 대기 표시는 그 시점의 상태다. 최신 상태는 이 원본/PR에서 확인한다. 데스크톱1366/모바일390·가로 넘침 없음·계약4행·672/60·PR6/이전 기록·console0·로컬 링크/anchor 검사 통과.
- 구현·Root 연결 문서 커밋 `cac6258`의 [CI #38150676791](https://github.com/DigestWorks/IssueDigest/actions/runs/38150676791) 성공. 마지막 게시 기록 커밋의 exact-HEAD check는 PR에서 확인한다. 앱 자동 PR 첨부/사이트 열기 요청이 응답하지 않아 직접 URL을 공유한다. PR을 병합하지 않았다. 격리 폴더와 이 작업의 검토/실행 증거를 보존한다.
