# 진행 기록

2026-10-12 한국 시간. 상태는 문서·코드·검증·운영 증거를 구분한다. 웹·API·상태 계약·개발 자동 검증 기반, 첫 원문·파싱·인용 및 두 번째 개체·주장·관계·비교 조건, 세 번째 실행·화면·사용량 부분 계약을 구현했다. 실제 HTTP·브라우저 스모크 검증을 통과했으며 전체 P1과 제품 기능은 미완료다.

| 단계 | 현재 상태 | 완료 증거·다음 조건 |
| --- | --- | --- |
| P0 계획·기록 | 작성·게시 완료 · 검토 중 | 저장소 조사·사용자 응답·요구사항·설계·작업 목록 작성 |
| P1 기반 | 웹·API 개발 기반 구현 · 전체 미완료 | npm/uv 워크스페이스·상태 계약·자동 검증 통과. 실제 HTTP·브라우저 스모크 통과. 원문·인용·개체·주장·관계·실행·화면·사용량 부분 계약 구현. PostgreSQL 근거 스냅샷 저장·초기 outbox 추가. 제품 API·이벤트 전달·워커·운영 DB·검색·인증은 미완료 |
| P2 실제 근거 | 미착수 | 첫 이슈·원문·읽기 스냅샷·데이터 API 접근 필요 |
| P3 검색·관계 | 미착수 | 실제 평가 자료·기준 DB 계약 필요 |
| P4 에이전트·UI | 미착수 | 근거 검색·도구·복구·UI 명세 계약 필요 |
| P5 공유·이미지 | 미착수 | 저장/권한 경로와 이미지 공급자 필요 |
| P6 운영 검증 | 미착수 | 기존 서버 상세·배치·실측·백업 복원 필요 |
| 이전 와이어프레임 | 코드 보존 · 배포 종료 | Vercel 배포 14개 삭제, Git 자동 배포 연결 해제 |

## 현재 작업

- 작업: D011 확정·[PostgreSQL 근거 스냅샷 저장 기반](../changes/postgres-storage.md), P1/R2 일부.
- 담당/브랜치: controller + 독립 구현/리뷰 · `feat/postgres-storage`; 구현 검증 기준 `aaf810a`.
- 상태: 코드·마이그레이션·실제 PostgreSQL 검증·독립 작업/전체 및 수정 범위 리뷰 완료. Draft PR #8·GitHub CI·원격 ARM 검증·웹/API 재확인·Sites 게시·사용자 폴더 인계 완료.
- 미구현: 제품 HTTP/API·권한·원문 파일/파서·수집 ID 중복 처리·검색/pgvector·Neo4j·PydanticAI/DBOS worker·outbox 소비·운영 DB 배치.
- 남은 입력: 서버 전용 자원·월 분담 비용·전용 DB/외부 백업·기존 수집 데이터·첫 이슈/평가 자료·인증 공급자. [연결 준비](../../infra/postgresql.md)에 확인할 항목 기록.
- Sites: v24 공개 배포 완료, D011·저장 구현 결과 반영. 운영 DB 설치·기존 데이터 변경·새 유료 호출 없음.

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
- Sites: [IssueDigest 구현 계획](https://lawdigest-rebuild-plan.ijaesinii.chatgpt.site/). 현재 v20 공개 게시 성공. 원문·파싱·인용과 개체·주장·관계·비교 계약·검증·PR 요약을 반영했다. 계획·개발 기반 상태와 저장소 문서·PR 검토 경로를 반영했다.
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
