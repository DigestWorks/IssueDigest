# 진행 기록

2026-10-11 한국 시간. 상태는 문서·코드·검증·운영 증거를 구분한다. 웹·API·상태 계약·개발 자동 검증 기반, 첫 원문·파싱·인용 및 두 번째 개체·주장·관계·비교 조건 부분 계약을 구현했다. 실제 HTTP·브라우저 스모크 검증을 통과했으며 전체 P1과 제품 기능은 미완료다.

| 단계 | 현재 상태 | 완료 증거·다음 조건 |
| --- | --- | --- |
| P0 계획·기록 | 작성·게시 완료 · 검토 중 | 저장소 조사·사용자 응답·요구사항·설계·작업 목록 작성 |
| P1 기반 | 웹·API 개발 기반 구현 · 전체 미완료 | npm/uv 워크스페이스·상태 계약·자동 검증 통과. 실제 HTTP·브라우저 스모크 통과. 첫 원문·파싱·인용과 두 번째 개체·주장·관계·비교 조건 부분 계약 구현. 워커·나머지 제품 계약·DB·검색·실행기·인증은 미완료 |
| P2 실제 근거 | 미착수 | 첫 이슈·원문·읽기 스냅샷·데이터 API 접근 필요 |
| P3 검색·관계 | 미착수 | 실제 평가 자료·기준 DB 계약 필요 |
| P4 에이전트·UI | 미착수 | 근거 검색·도구·복구·UI 명세 계약 필요 |
| P5 공유·이미지 | 미착수 | 저장/권한 경로와 이미지 공급자 필요 |
| P6 운영 검증 | 미착수 | 기존 서버 상세·배치·실측·백업 복원 필요 |
| 이전 와이어프레임 | 코드 보존 · 배포 종료 | Vercel 배포 14개 삭제, Git 자동 배포 연결 해제 |

## 현재 작업

작업: [개체·주장·관계·비교 조건 계약](../changes/research-contracts.md) · P1/R2/R3. 담당: Codex. 브랜치: `feat/research-contracts` · [Draft PR #5](https://github.com/DigestWorks/IssueDigest/pull/5), 선행 PR #4 위·미병합. 개체/주장/검토·제한된 관계·기간/관측·비교 정책·ResearchBundle 참조와 OpenAPI→생성 TS 타입 구현, 독립 작업/전체 변경 리뷰 및 비교 결과 모순 보완 후 수정 부분 리뷰 통과. 최종 전체 검사: Python 393개·JS 60개, lint/타입/SPA 빌드/계약 drift 통과. 실제 저장·추출·권한·인증된 검토·AI·Neo4j·제품 경로/UI와 전체 P1은 미완료. 사용자 폴더 연결·Sites 요약 갱신을 진행 중이다.

## 2026-10-11 · 개체·주장·관계·비교 조건 계약

- 동일 이름의 독립 개체와 미해결/미검토를 보존하고 외부 identity 3항 키 충돌을 거부한다. 근거 있는 원문 주장/관측/추론 입력과 inference에만 필요한 가공 기록을 구분한다. 검토는 UTC 시각·방법/버전·인용과 귀속/내용/관계 범위를 기록하며 실제 인증 행위·주장 진실을 보장하지 않는다.
- `issuedigest-relations-v1`의 6종 방향/양 끝 종류와 제공 객체 존재를 검사한다. 근거 없는/미등록 인과/자기 관계·다른 공간·없는 endpoint를 거부한다. mentions는 source 문서 버전의 인용만 허용한다. 자동 역관계·그래프 투영은 없다.
- 정확한 Python date/JSON YYYY-MM-DD 기간·strict 양의 표본 크기·최대128자 정밀 ASCII 소수 문자열과 원문/결측을 보존한다. 비교는 모든 조건과 value 결측을 순서대로 보고하고 different를 missing보다 우선한다. 같은 조건의 다른 값·순서만 다른 차원은 same_context이며 합산/분포는 not_evaluated다. 결과 ID·사유·status 모순도 거부한다.
- ResearchBundle의 전체 공간·문서/버전 일치·고유 인용/표현/검토 ID·typed 참조·검토 citation subset을 검증한다. 같은 문서/버전의 다른 파싱 표현은 허용한다. 검증 대상은 제공된 묶음이며 저장소 전체 unique enforcement는 아니다.
- 실제 OpenAPI components를 단일 등록 경로로 확장하고 생성 TS와 공개 aliases/compile 소비자를 갱신했다. 기존 HTTP 두 경로·상태/원문/인용·웹 UI를 보존했다. 종속성·외부/유료 호출·비공개/운영 자료 사용 없음.
- 초기 구현 검증: focused 새 계약+API 228개 통과, Ruff/mypy·공개 생성 타입 소비자 통과. 전체 `npm run check` 1회 통과: Python 380개·JS 60개, Ruff/format/mypy·ESLint·양쪽 타입 검사·SPA 생산 빌드·생성 계약 drift 검사 통과. RED/GREEN·수정 파일·self-review는 로컬 SDD `research-contracts/task-1-report.md`에 보존한다.
- 인계: 독립 작업 리뷰 통과. 전체 변경 리뷰의 P2 지적(같은 항목의 결측/다름 ID 겹침과 필수 항목의 결측 사유)을 `e902cb4`에서 보완했다. JSON 회귀 RED 8개 실패·정상 5개 통과 후 GREEN 107개, 수정 부분 재리뷰 지적 없음. 컨트롤러 최종 전체 검사도 393 Python + 60 JS 통과. 초기 비교 알고리즘만의 독립 RED 증거 범위는 제한적이며 이를 뒤늦게 충족했다고 주장하지 않는다. 현재 동작 테스트·코드 리뷰로 구현을 검증했다. C1~C4 결합 완료는 Sites·사용자 폴더 연결까지 미체크 유지. 나머지 P1·출처 시간 정밀도·재수집·내용 비교 fingerprint·Run/Event/Canvas/Usage·실제 자료/추출/저장/권한·AI·Neo4j는 미완료.

- 게시: [Draft PR #5](https://github.com/DigestWorks/IssueDigest/pull/5), base `feat/source-evidence-contracts`, 구현 `d82a8f1` + 보완 `e902cb4`. 보완 커밋의 [GitHub CI #38144301870](https://github.com/DigestWorks/IssueDigest/actions/runs/38144301870) 성공. Sites v19에서 이번 요약 갱신 대기. 앱의 PR 첨부 요청이 응답하지 않아 직접 링크로 공유한다.

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
- Sites: [IssueDigest 구현 계획](https://lawdigest-rebuild-plan.ijaesinii.chatgpt.site/). 현재 v19 공개 게시 성공. 첫 원문·파싱·인용 계약·검증·PR 요약을 반영했다. 계획·개발 기반 상태와 저장소 문서·PR 검토 경로를 반영했다.
- 구현 시작: 로컬 폴더·협업 문서와 웹·API·상태 계약·개발 검증 기반 완료. 실제 스모크 결과·코드 검토는 개발 기반 작업에 기록한다. PR #1~#5는 Draft이며 병합하지 않았다.

## 서버 정보를 기다리지 않고 진행 가능한 항목

- 기준 데이터·인용·실행 이벤트·화면 명세 계약 검토.
- 기존 수집/가공 규칙과 회귀 테스트의 재사용 범위 평가.
- 첫 이슈·대표 질문·원문 조건 선정과 실제 평가셋 준비.
- 검색·작업 복구·권한·비용의 결정 실험 설계.

유료 외부 호출이나 운영 서버 설치를 시작한 것으로 표시하지 않는다.

## 게시 검증 증거

- Sites v19 source: `36ece7df45854a5db46d1c9690641a3d5bfd09d9`, deployment `appgdep_6acb7b68bcb08191a9b187bc7327f92e`, 상태 `succeeded` (2026-10-11 12:05 UTC). 기존 공개 설정 유지. 로컬 1366×900·390×844에서 새 계약 요약·내부 anchor와 보존 파일 링크 정상, 가로 넘침 없음, 콘솔 오류/경고 0건. v18 이전 조사안을 별도 보존했다. 저장소 원본/공개 사본 기준을 구분했다.
- 원격 검증: 구현 `9271a0a` CI #38137640138, 검토/PR 문서 `63f88fe` CI #38137818441 성공. 제품 구현 코드는 독립 작업/전체 리뷰 이후 변경하지 않았다.
- 사용자 폴더의 실제 API `/openapi.json`에서 EvidenceBundle과 기존 상태 경로만 확인, 웹 HTTP200 확인. 개발 서버는 로컬 5173/8000에서 기동 중이며 운영 배포가 아니다.

- Sites v18 source: `02565938f167a9a6c0c5203b5bfdf6569640e8f6`, deployment `appgdep_6acb6fc608108191b1f9a302100aed7b`, 상태 `succeeded`. 기존 공개 설정 유지. 1366×900·390×844에서 가로 넘침 없음, 새 요약 4행·전체 내부 링크 정상, 콘솔 오류/경고 0건 확인.

- Sites v17 source: `721cf362a2d61a7aa2a7bb6013e18a04857ff700`, deployment `appgdep_6acb6a2969d08191b6f8999e42beb5a4`, 상태 `succeeded` (2026-10-11 10:51 UTC). 기존 공개 설정을 유지했다. 1366×900·390×844에서 가로 넘침 없음·내부 링크 정상·콘솔 오류/경고 0건을 확인했다. 아래 v15 증거는 이전 게시 기록이다.

- Sites v15 source: `a96fae750ac020212d239e3d69344718cd6c3f02`, deployment `appgdep_6acb5724c784819184713ada7b2a8a8a`, 상태 `succeeded`.
- Vercel: 배포 목록 0개, `paused=true`, Git 연결 없음. 대표 주소와 두 과거 배포 주소는 HTTP 404 `DEPLOYMENT_NOT_FOUND`.
- 화면: 1366×1000·390×844에서 문서 가로 넘침 없음, 내부 메뉴 이동 확인, 콘솔 오류 0건. 문서 링크·보존 원문·계획 사본 일치 확인.
