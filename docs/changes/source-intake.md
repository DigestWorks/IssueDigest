# 읽기 전용 원문 후보 연결기

2026-10-13. 사용자 요청: 관리자에게 필요한 작업을 정리하고, 대기 중에도 개발자가 할 수 있는 구현을 진행한다. 첫 범위는 기존 NESDC 여론조사 파일의 사전 검사다. 첫 제품 이슈를 대신 결정하지 않는다. [자산 실측](../research/server-data-inventory.md)의 JSON 840개·PDF 774개와 누락/중복/잘못된 PDF 문제를 입력으로 삼는다.

## Task 1: 원문 후보 검사 패키지·CLI

### 요구사항·설계

명시적으로 전달한 data root의 `parsed/`, `pdfs/`만 읽는다. 이전 경로·DB·SSH·외부 URL을 하드코딩하거나 자동 접속하지 않는다. 데이터 root와 필수 두 디렉터리가 없거나 디렉터리 탐색이 실패하면 검사가 완료됐다고 표시하지 않는다. symlink·특수 파일은 읽지 않는다. 입력 JSON의 경로는 파일 접근 지시가 아니고 원문 basename 대조에만 사용한다. 경로 탈출·절대 경로·NUL·역슬래시를 거부한다.

메타데이터 필드는 `registration_number`, `source_url`, `pdf_path`이며 별칭을 만들지 않는다. 여론조사 객체는 ASCII 숫자 문자열 registration_number(1~32문자)와 `https://www.nesdc.go.kr/` 또는 `https://nesdc.go.kr/` 출처를 요구한다. 공백·bool·숫자 자동 변환이나 URL 자격 증명·비표준 포트를 허용하지 않는다. 다른 JSON 형식은 별도 unsupported로 분류한다. 원문 basename이 정확히 한 파일 후보를 가리킬 때만 PDF 헤더·크기·SHA-256 검사를 통과한 **candidate**를 만든다. 여러 경로에서 같은 파일명이 발견되면 첫 파일을 선택하지 않고 ambiguous로 격리한다. basename이 같다는 사실은 원문 동일성 검증이 아니다.

PDF는 첫 1,024바이트 안의 `%PDF-`와 전체 bytes의 SHA-256/크기를 확인한다. 형식 헤더는 파싱 성공·실제 원문·인용 품질 검증이 아니다. 읽는 동안 파일 identity/크기/수정 시각이 바뀌면 후보로 사용하지 않는다. 전체 PDF bytes를 메모리에 한꺼번에 적재하지 않고 해시를 계산한다. 같은 내용 해시 그룹·중복 조사 등록번호를 보고하되 서로 다른 출처/문서를 자동 병합하지 않는다. candidate로 분류해도 EvidenceBundle/인용을 만들거나 DB에 저장하지 않는다.

기본 stdout은 JSON 집계만 제공한다. 원문 텍스트·경로·등록번호·URL·해시는 출력하지 않는다. 사유별 집계·스캔 파일 수·candidate/quarantined/unsupported 수·중복 그룹과 검사 시각을 포함한다. 상세 manifest는 사용자 명시 옵션으로만 root 밖 새 파일에 저장한다. 기존 파일·symlink를 덮어쓰지 않으며 생성 권한은 600이다. 실패 시 부분 파일을 남기지 않는다. source root 안에 출력 경로/그 상위 디렉터리 symlink가 접근하게 되는 경우도 거부한다. 상세 manifest는 공개 커밋/Sites 대상이 아니다.

기본 최대 파일 수 10,000, JSON 8MiB, PDF 128MiB, 전체 읽기 2GiB. 한도를 명시적으로 바꿀 수 있으나 bool/0/음수 등 잘못된 값을 거부한다. 파일 수/전체 읽기 한도 초과는 검사를 실패시키고 상세 manifest를 만들지 않는다. 개별 파일 크기 초과·유효하지 않은 JSON·메타데이터·원문 참조·헤더는 사유별 격리다. OS 읽기 실패는 고정 오류로 검사를 중단한다. stdout/stderr 오류에 실제 파일 경로·JSON 본문·URL·원본 예외를 넣지 않는다.

완료된 검사의 CLI exit0은 이관 가능 판정이 아니다. 잘못된 인자·입력/읽기 실패·한도 초과·manifest 저장 실패는 고정 JSON 오류와 exit2다. 출력은 운영 DB의 고정 시점 스냅샷을 보장하지 않는다. 실제 원문 파일은 전용 mount를 읽고 검사 출력만 개인 경로에 둔다.

## Global Constraints

- No database writes, migrations, network/model calls, source-file writes, automatic imports, or changes to existing API/domain contracts.
- Candidates are unverified file associations; no EvidenceBundle/citation is emitted and no basename match is presented as proven provenance.
- Public stdout contains aggregate counts and fixed error codes only; private manifests are opt-in, outside the source root, exclusive-created with mode 600, and never committed.
- Read only explicit parsed/ and pdfs/ under the configured data root; do not follow symbolic links or consume special files.
- Keep existing locked engines/dependencies and full verification gates; tests use synthetic temporary files, not real collected documents in Git.

### 구현 항목

- [x] `packages/ingestion`에 독립 Python 패키지 `issuedigest-ingestion`/`issuedigest_ingestion`을 만든다. 새 외부 의존성은 추가하지 않는다. 표준 라이브러리로 검사/보고서/CLI를 책임별로 분리한다.
- [x] 위 요구사항을 그대로 구현한다. 라이브러리 `audit_poll_files(data_root, limits=...)`와 `issuedigest-ingestion audit-polls --data-root PATH [--private-manifest PATH]` CLI를 제공한다. 공개 summary와 상세 manifest를 분리하고 v1 형식·고정 상태/사유를 README에 기록한다.
- [x] uv workspace/lockfile·pytest discovery·mypy 대상에 추가한다. 기존 코드/생성 계약은 변경하지 않는다. `output/` 검증 산출물을 Git에서 제외한다.
- [x] 실제 assertion RED를 먼저 확인하고 최소 구현→GREEN/TDD를 지킨다. 합성 임시 파일로 정상 후보와 hand-derived SHA, 없거나 같은 basename인 PDF, 헤더 없는 PDF, 부적절한 metadata/URL/path, JSON decode·크기/개수/전체 읽기 한도, symlink/특수 파일, 파일 변경, 중복 해시/등록번호, CLI 집계의 비공개 정보 제외·exit2, 상세 파일 권한·덮어쓰기/소스 내부/실패 시 잔여 방지를 검사한다.
- [x] 패키지 README에 실제 명령·반환/격리·한도·관측 시각·품질 한계·후속 원문 대조/인용 경계를 기록한다. 전체 Python·JS 테스트/린트/타입/빌드/계약 검사 후 commit과 보고서를 남긴다.

## 결합·검증·게시

컨트롤러가 독립 작업 리뷰와 전체 변경 리뷰, 실제 합성 PostgreSQL을 포함한 전체 검사를 확인한다. 개발 서버의 사용자 전용 worktree에서 실제 data root를 읽는 dry-run을 실행하고 **집계만** 공개 기록으로 남긴다. 실제 건수는 새 검사 기준/시점 결과로 기록하며 이전 조사의 숫자와 같다고 가정하지 않는다. 관리자 요청·진행/작업 목록·PR·Sites를 갱신한다. 병합·관리자 설치·수집 재실행·운영 DB 적용·앱 공개 배포는 하지 않는다.

## 결과 · 2026-10-13

최종구현1a6f71d, 독립 작업/전체 변경/보완 재검토 통과. 실제 합성PG18.6 포함전체Python888+JS134=1,022개·모든 검증 통과. 실제 JSON840개에서 후보225·격리384·미지원231, PDF774개·헤더 없는23개. 개인 상세600 파일은 Git/원문 밖에 저장, 공개 집계만 기록했다. Draft PR #12·Sites v28 게시 완료. 원문 대응·인용·이관·운영 배포는 후속이다. 자세한 근거와 게시/인계 상태는 [진행 기록](../planning/progress.md)을 따른다.
