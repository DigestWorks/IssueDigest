# 작업 공간 근거 검색 API·화면

2026-10-15. R2/R3·D011/D015, 기존 [문자 검색 SDK](evidence-search.md)의 사용자 진입 경로다. 사용자가 이어서 개발하도록 승인했다. OpenSpec list의 root=null을 확인해 기존 문서와 Superpowers 구현·검증 절차를 사용한다.

## 범위·수용 조건

현재 로그인한 작업 공간에서 검색어를 입력하고, 일치한 원문의 본문·PDF 페이지·표 셀을 열어 확인한다. 검색어는 원문에 포함된 문자열이며 AI 답변이나 주장 지지 판정으로 표시하지 않는다. 검색 전에는 결과를 만들지 않는다.

- `POST /api/v1/workspaces/{workspace_id}/evidence/search`는 기존 EvidenceSearchQuery JSON을 받고 EvidenceSearchResult를 반환한다. 본문은 UTF-8 최대16,384바이트, Content-Type application/json만 허용한다. 잘못된 JSON·필드·중복 JSON 키·query string·한도는 고정 422 `Invalid evidence search request`, 다른 미디어 형식은 같은 422로 거부한다. 입력값·Pydantic input/ctx·검증 예외 문자열은 응답/로그에 복사하지 않는다. UUID 경로 오류는 기존 안전한 경로 오류 계약을 따른다.
- 쿠키 세션만 사용하고 기존 WorkspaceAccessRepository.search_evidence로 현재 권한을 매번 검사한다. 인증 없음/만료/폐기401, 비회원/다른 공간404, 서비스 미설정·저장 오류·잘못된 backend 출력503이다. 응답은 no-store·서버 요청 ID를 유지한다. POST에는 기존 AuthService의 신뢰된 public_origin과 동일한 Origin 검증을 재사용한다(403). backend/OAuth 구성 없음은503이며 실제 공급자는 호출하지 않는다.
- 서버는 출력 모델을 재검증하고 workspace/query와 각 hit의 workspace·matched_terms·문자 일치, hit 수/입력 limit 및 coverage의 일관성을 확인한다. canonical 저장·selector 검증은 기존 SDK의 책임이다. 새 검색 요청에 migration/rebuild/model 호출을 숨겨 넣지 않는다.
- 생성 OpenAPI/TypeScript를 갱신한다. 클라이언트는 같은 출처의 쿠키·JSON POST만 사용하고 검색어를 URL/스토리지에 넣지 않는다. 입력·출력의 필드/타입/개수/UUID·시간/selector와 workspace/query/hit identity·coverage를 검증한다. 현재 보호 transport의 timeout·abort·요청 ID/no-store·고정 오류 분류를 보존하고 로그아웃204 동작을 바꾸지 않는다. 검색 전용 오류의 invalid-query/forbidden을 표현할 수 있다.
- 웹에는 현재 선택 공간의 자료 목록 위에 검색 입력 하나와 버튼을 둔다. 공백으로 나눈 단어1~8개를 모두 포함하는 검색이며 Unicode code points와 ASCII 중복 규칙을 따른다. API의 선택 출처/기간 필터는 지원하되 이 첫 화면에는 필터 패널을 추가하지 않는다. idle/loading/success/empty/failure를 구분하고 제출 직후 검색 중 상태·중복 제출 방지를 제공한다. 재시도는 마지막 제출을 사용한다. 공간 변경/로그아웃/unmount 시 요청 취소·결과 초기화, 이전 응답 무시를 검증한다.
- 결과에는 원문 출처·수집 시각·정확 quote·본문/실제 PDF 쪽/표 셀 위치와 `원문 위치 열기`를 표시한다. 검색된 위치는 저장된 인용과 구분한다. 검색된 자료 수·미색인·제외 셀·결과/후보 한도에 따른 불완전성을 표시하고 빈 결과를 '근거 없음'으로 단정하지 않는다.
- 위치 열기는 기존 근거 reader를 사용한다. 검색 hit를 router state로만 전달하고 로드한 EvidenceBundle의 workspace/snapshot/document/version/representation과 exact selector를 다시 대조한 경우에만 강조한다. 검색 선택은 Citation UUID를 만들거나 저장하지 않는다. 부정확/오래된/다른 공간 state는 강조하지 않고 고정 안내를 표시한다. 직접 링크·새로고침·기존 저장 인용/페이지 선택을 보존한다. 표 셀은 전체 셀, PDF는 해당 실제 페이지, text는 code point→UTF-16 범위를 사용한다.

## Global Constraints

기존 엔진·의존성·DB 스키마·권한·승인 자료를 유지한다. 합성 세션/쓰기 테스트는 소유 loopback issuedigest_test DB에서만 실행한다. 실제 공동 DB의 사용자/세션/자료를 임의 생성하거나 초기화하지 않는다. 개인 개발 HTTPS 앱 갱신은 승인 범위이며 실제 사용자 자료 열람은 사용자의 브라우저 세션에서만 확인한다. 공급자 로그인·검색 품질20문항·의미 검색·AI·전체 제품 완료를 주장하지 않는다. main 병합·운영 배포는 D013에 따라 유예한다. 공개 기록에는 실제 이메일/접속정보/비밀값/실제 원문/내부 식별자를 넣지 않는다.

## 구현 태스크

### Task 1: 보호 검색 HTTP 계약·클라이언트

- [x] TDD로 실제 assertion RED를 확인한 뒤 API route·bounded JSON 입력·고정 오류·현재 권한·출력 검증을 구현한다. apps/api의 search 모듈과 기존 main/contracts/errors 경계, packages/api-client의 검색 모듈/보호 transport·export, 생성 계약을 변경한다. 기존 세션·목록·인용 동작을 보존한다.
- [x] PostgreSQL 통합 검증은 기존 합성 fixture로 정상검색/다른 공간·폐기 세션·미색인·한도를 검사한다. HTTP 주입 backend로 body 한도·중복/잘못된 JSON·경로/Origin·반환 변조/에러 비노출을 검증한다. 클라이언트는 입력/응답 변조·타임아웃·취소/역순 응답·logout204 보존을 검증한다. client는 EvidenceSearchQuery/Result/Hit 및 searchEvidence를 export한다. reader가 쓸 검색 hit 검증/선택 helper의 계약은 Task2에서 구현한다.
- [x] 관련 API/클라이언트 README에 실제 사용법·문자 검색/미색인/권한 경계를 기록한다. 관련 테스트·lint/type/계약 검증·self-review 후 commit하고 별도 report에 RED/GREEN 근거를 기록한다. 수행한 task 체크만 갱신한다.

### Task 2: 검색 화면·원문 위치 연결

- [x] TDD 후 현재 home의 로그인/공간 선택 흐름에 분리된 검색 component와 간결한 스타일을 추가한다. 검색 상태·재시도·권한/네트워크 오류·coverage/한도·stale 결과와 취소를 수용 조건대로 구현한다. 설명은 검색 방식과 결과 해석에 필요한 짧은 문구만 둔다.
- [x] evidence route/reader와 검색 선택 helper를 연결한다. router state를 신뢰하지 말고 canonical bundle과 ID·정확 selector/page/cell/quote/prefix/suffix를 대조한다. 검증된 검색 위치만 강조·포커스하고 기존 저장 인용 선택/페이지 전환/직접 링크를 보존한다. 일치하지 않는 state는 원문 읽기를 막지 않고 안내한다. 검색 위치를 저장된 인용으로 부르지 않는다.
- [x] 합성 UI 테스트로 제출 전 무결과·loading/중복/empty/실패/재시도·공간변경/로그아웃/늦은응답·text/PDF/셀·emoji/결합문자·변조/오래된state·기존인용 선택을 검증한다. 관련 README 갱신, targeted JS/TS/lint·self-review 후 commit하고 report에 RED/GREEN 근거를 기록한다.

## Controller 검증·인계

- [x] 각 Task 독립 리뷰와 전체 변경 백지 리뷰, 전체 Python/JS·lint/format/type·SPA·OpenAPI 검증. 합성 브라우저 여정으로 검색→정확 원문 위치·모바일/오류 확인.
- [x] DNS/HTTPS 완료(2026-10-15)·실제 로그인 저장 상태와 사용자 자료 열람 미확인을 구분해 문서를 갱신했다. Draft PR/앱 첨부·Sites v47 게시, 기존 탭을 열지 않았다. 개인 개발 앱 갱신 후 실제 HTTPS/미인증 보호 응답을 확인했다.

## 구현·검증 기록

Task1 6308392와 보완9f1ba08에서 API/클라이언트를 구현했다. JSON 날짜 모드·마이크로초·canonical 출력 길이·async DB 호출을 assertion RED 후 보완하고 독립 재검토를 통과했다. Task2 a90b3fc/663d512에서 검색 UI와 canonical 원문 선택을 연결하고 별도 리뷰·새로고침 문서/coverage 정리를 수행했다. 새로고침은 history state를 보존할 수 있으며 새 보호 GET과 원문 대조를 다시 수행한다. state 없는 직접 URL은 일반 reader다.

Controller 전체 Python1,808+JS363=2,171개·format159/mypy68/TS/SPA/OpenAPI 통과, skip/warning0. 소유 합성 PostgreSQL과 실제 HTTP API의 브라우저에서 본문 Unicode/새로고침·PDF page·전체 셀·저장 인용·pending·503/재시도/빈 결과·390px·로그아웃401을 확인했다. 페이지 예외0, 의도적503 네트워크 오류1개를 별도 구분했다. 마지막 표시 정리 후 관련64개/검색9개·lint/type/build 통과. 전체 변경 최종 리뷰·개발 앱/PR/Sites 인계까지 완료했다. 실제 사용자 검색 품질·의미 검색·AI·운영 배포는 후속이다. 실제 공동 DB 세션/자료를 합성 생성하거나 schema/권한을 변경하지 않았다.

전체 변경96c1362 독립 리뷰에서 Critical/Important0·Minor1(중복/64자 오류 안내)을 확인했다. 단일 안내 문구fd26683에서 기존 안내와 함께 제한을 설명하도록 보완했고 검색9개·SPA 재빌드/독립 수정 검토를 통과했다. Draft PR #27 게시·앱 첨부, main/운영 유예는 유지한다.

2026-10-15 18:04 KST 개인 개발 앱에 source fd26683을 적용했다. 고정 Node/lockfile·정적14파일/source map0·개인 API 재시작/정적 Nginx reload, 실제 TLS/index hash·home/login/asset/health200·미인증 session/search401/no-store를 확인했다. schema0004·승인 자료1건/인용3개·기존 초대 바인딩·앱 DDL 금지를 read-only 대조했다. 시스템 서비스/DB/schema/권한/main/운영 배포는 바꾸지 않았다. CI fd26683 전체 검사 성공; 실제 사용자 검색 품질·AI/의미 검색은 여전히 후속이다. Sites 게시 기록은 진행 기록에 남긴다.
