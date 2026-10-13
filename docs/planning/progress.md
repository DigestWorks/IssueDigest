# 진행 기록

2026-10-13 한국 시간. 상태는 문서·코드·검증·운영 증거를 구분한다. 웹·API·상태 계약·개발 자동 검증 기반, 첫 원문·파싱·인용 및 두 번째 개체·주장·관계·비교 조건, 세 번째 실행·화면·사용량 부분 계약을 구현했다. 실제 HTTP·브라우저 스모크 검증을 통과했으며 전체 P1과 제품 기능은 미완료다.

| 단계 | 현재 상태 | 완료 증거·다음 조건 |
| --- | --- | --- |
| P0 계획·기록 | 작성·게시 완료 · 검토 중 | 저장소 조사·사용자 응답·요구사항·설계·작업 목록 작성 |
| P1 기반 | 웹·API 개발 기반 구현 · 전체 미완료 | npm/uv 워크스페이스·상태 계약·자동 검증 통과. 실제 HTTP·브라우저 스모크 통과. 원문·인용·개체·주장·관계·실행·화면·사용량 부분 계약 구현. PostgreSQL 근거 스냅샷 저장·초기 outbox 추가. DB 세션·회원 권한·보호 근거 조회 구현. 실제 로그인·초대·나머지 제품 API·이벤트·워커·운영 DB·검색은 미완료 |
| P2 실제 근거 | 자산 조사·PDF 추출/인용 위치 구현 · 이관 미착수 | 원문 후보·해시·격리와 제한된 페이지 텍스트 추출 구현. 실제6개 추출, 기존35문항은 반복 매치로 자동 인용 보류. 첫 이슈·정확한 조사 대응·표·이관은 후속 |
| P3 검색·관계 | 미착수 | 실제 평가 자료·기준 DB 계약 필요 |
| P4 에이전트·UI | 렌더러 일부 구현 · 검증 완료 | 기존 CanvasBundle의 여섯 모듈·표시 상태·근거 액션 구현. AI/API·실제 액션·스트리밍·권한은 미완료 |
| P5 공유·이미지 | 미착수 | 저장/권한 경로와 이미지 공급자 필요 |
| P6 운영 검증 | 미착수 | 기존 서버 상세·배치·실측·백업 복원 필요 |
| 이전 와이어프레임 | 코드 보존 · 배포 종료 | Vercel 배포 14개 삭제, Git 자동 배포 연결 해제 |

## 현재 작업

- 작업: [PDF 페이지 텍스트·정확 인용 준비](../changes/pdf-text-evidence.md), R2/P2의 다음 부분 구현. 기대 해시로 묶은 PDF 복사본·제한된 파서·기존 계약 어댑터·유일한 정확 인용 위치를 구현했다.
- 담당/브랜치/PR: controller/implementer · `feat/pdf-text-evidence` · [Draft PR #13](https://github.com/DigestWorks/IssueDigest/pull/13) · 선행 #12 위, 미병합.
- 상태: 구현·독립 작업/전체 변경 리뷰·controller 전체 검증·실제 소표본 대조·Draft PR #13 게시/앱 첨부·Sites v29 공개 게시 완료. 첫 이슈·표 구조·OCR·좌표·원문 동일성·운영 DB 이관은 별도다.
- 검증: 전체 Python1,021+JS134=1,155개 및 타입·빌드·생성 계약 통과. 실제 PDF6개/92페이지 추출. 기존35문항 모두 여러 위치에 반복되어 자동 인용 확정을 거부했다. 별도 페이지 텍스트 인용 확인6개는 성공했지만 기존35문항의 검증이 아니다.
- 관리자 요청: **pgvector만 전달·완료**. 직접vector0.8.7·거리 연산과 별도 프로젝트 로그인 계정 존재를 확인했다. [기존 나머지 제안](../../infra/administrator-request.md)은 미전달이며 개발의 선행 조건이 아니다. 실사용 전 백업/권한·비용/접근 준비를 단계별로 확인한다.
- 다음: 첫 이슈·이용 조건을 확정하고, 문항·페이지·표/응답 수치의 대응 규칙과 평가 자료를 준비한다. 반복 매치를 첫 위치로 임의 선택하지 않는다.
- Sites: v30 공개 게시 완료, v29를 보존했다. pgvector 완료·나머지 제안 미전달과 필요한 시점을 정정했다. PDF 구현/소표본 기록은 유지한다.

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
