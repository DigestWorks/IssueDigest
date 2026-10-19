# 문서 안내·협업 방법

IssueDigest는 질문에서 시작하는 B2C 브리핑 서비스다. [제품 경험 인터뷰](research/product-experience-interview.md)와 [D016·D017·D019·D020·D021·D022](planning/decisions.md)의 사용자 선택을 기준으로 질문→짧은 브리핑→필요한 비교·변화·반응·근거를 잇는다. 현재 자료·브리핑 기록은 초대된 초기 검증 참여자의 공유 자료 범위이며 공개 피드나 개인 보관함이 아니다.

저장소 문서가 결정 원본이고 PR에서 변경을 검토한다. 별도 이슈 트래커는 사용하지 않는다. Sites는 검증된 현재 상태의 요약이며 독립된 요구사항 원본으로 복제하지 않는다.

현재 화면 작업: [소비자 브리핑 디자인](changes/consumer-briefing-design.md). 선택한 모바일 브리핑형의 실제 웹 적용과 검증 범위를 따른다.

## 현재 계획과 작업

| 문서 | 용도 |
| --- | --- |
| [구현 계획·마일스톤](planning/implementation-plan.md) | M1~M6 완료 기준·진척·B2C 여정·다음 순서·재사용 구조와 예산 |
| [요구사항·설계](planning/requirements-design.md) | R1~R7 접근·원문·탐색·브리핑·진행·복구 계약과 현재 제한 |
| [결정 기록](planning/decisions.md) | 사용자 선택·확정 기술·대체 결정·대기 입력 |
| [작업 목록](planning/tasks.md) | 실제 다음 작업과 현재 변경의 완료 조건 |
| [진행 기록](planning/progress.md) | 코드·검증·개인 개발 적용·Sites·운영의 개별 증거와 인계 |
| [수집본 검토·버전·검색 편입](changes/policy-collection-intake.md) | 고정 성공 원본의 승인·중복/버전·원자 저장/검색·최신 승인 선택 |
| [정책뉴스 반복 확보·실행 이력](changes/policy-collection-journal.md) | 명시 기사 poll·PostgreSQL 원본/성공/실패 보존·중복/간격 제어·상태 조회 |
| [공식 자료 변경 감지](changes/policy-change-detection.md) | 승인 capture의 오프라인 신규/변경/동일/미관측 비교·정기 수집/게시와의 경계 |
| [한국어 근거 품질](changes/korean-evidence-quality.md) | 제한 한국어 검색·read-only 내부 평가·새 private v4 귀속/수치 지침과 v2/v3 복구 보존 |
| [공식 자료 확보·AI 근거 분류](changes/evidence-exploration.md) | 수동 공식 정책뉴스 SDK·private v3 AI 평가·v2 복구 호환과 개발 적용 대기 경계 |
| [공개 브리핑 읽기](changes/public-briefings.md) | 문서별 권리/내용 검토·불변 공개 버전·비회원 읽기/인용·일반 홈 초안 |
| [B2C 화면 정리·로그인 유지](changes/b2c-cleanup-persistent-login.md) | 아이콘 헤더·질문/브리핑 중심 화면·활성 계획 재편·14일/7일 세션 |
| [브리핑 경험 첫 연결](changes/briefing-experience.md) | 비회원 질문→로그인 복원·원문 선열람·완료 브리핑·본문 내 근거 |
| [브랜드·테마·계정](changes/brand-theme-entry.md) | 로고·기기 테마 선호·계정 메뉴·행동 시 로그인 |
| [에이전트 지침](../AGENTS.md) | 읽는 순서·개발 절차·권한·기록 기준 |

공개 브리핑 게시/읽기의 계약·웹 연결을 구현했으며 실제1건 게시·개인 개발 적용·독립 결합 검증은 진행 기록에서 구분한다. 기존 private 자료/질문/기록을 자동 게시하지 않는다. 개인 관심 이슈·변화 알림·고정 공유본·최근 이슈/개인화·검증된 AI 모듈 점진 전달은 미완료다. 해당 데이터·이용권·게시/소유·근거 평가·비용/복구 계약부터 이어간다. 과거 공간 중심 P0~P6 계획은 현재 본문에서 제거했고 전개는 Git 이력(재편 전 `d6d05f3`), 아래 변경 명세와 진행 기록에서 확인한다.

## 재사용 코어·계약의 근거

| 영역 | 원본·검증 기록 |
| --- | --- |
| 원문·정확 인용·도메인 | [원문 계약](changes/source-evidence-contracts.md), [주장/관계/비교](changes/research-contracts.md), [실행/화면/사용량](changes/execution-contracts.md), [도메인 안내](../packages/domain/README.md) |
| 저장·권한·로그인 | [PostgreSQL 저장](changes/postgres-storage.md), [서버 세션/보호 GET](changes/session-evidence-api.md), [Google 초대/로그인](changes/google-oauth-workspace.md), [API 안내](../apps/api/README.md), [저장 안내](../packages/storage/README.md) |
| 검색·원문 읽기 | [문자 검색](changes/evidence-search.md), [검색 API/화면](changes/evidence-search-interface.md), [보호 reader](changes/evidence-reader.md), [웹 안내](../apps/web/README.md), [클라이언트 안내](../packages/api-client/README.md) |
| 실행·브리핑 | [첫 실제 조사 실행](changes/research-journey.md), [생성 렌더러](changes/canvas-renderer.md), [조사 실행/비용](../infra/research-development.md), [UI 안내](../packages/ui/README.md) |
| 원문 연결·파싱 | [국회 원문](changes/assembly-source-connector.md), [후보 연결](changes/source-intake.md), [HTML](changes/official-html-evidence.md), [PDF 텍스트](changes/pdf-text-evidence.md), [PDF 후보/문맥](changes/pdf-quote-candidates.md), [HWPX 근거](changes/hwpx-evidence.md), [HWPX 수집](changes/hwpx-import.md) |
| 승인 등록·개발 연결 | [등록 CLI](changes/workspace-bootstrap.md), [초기 DB 적용](changes/shared-database-bootstrap.md), [Google runtime](changes/google-login-runtime.md), [개발 HTTPS](changes/development-https.md), [개발 기반](changes/development-foundation.md) |

기존 계약은 재사용한다. 정확 인용·객체 검증을 출처 진위/주장 지지·실제 자율 탐색·공개 접근 허용으로 확대하지 않는다. 기존 변경 명세는 해당 시점의 부분 구현과 검증 기록이며 후속 목표는 현재 작업 목록에서 관리한다. 법안/자료 중심 이전 화면은 [자료 UI 기록](changes/workspace-clarity-legacy.md)에 남기고 현재 기본 제품으로 되살리지 않는다. [개발 보조 도구 제거](changes/home-tools-removal.md)의 연결 확인·수동 링크 도구 제거도 유지한다.

## 자료·평가·운영 기록

- [첫 검증 이슈](research/first-issue.md), [첫 자료 풀](research/first-issue-corpus.md), [평가 질문20개](../tests/evaluation/first-issue.md): 실제 출처·권리·필수 근거·자료 부족·수치/시점 평가.
- [엔진 선택](research/engine-selection.md), [제품 계약 조사](research/product-contracts.md), [기존 법안 재사용](research/bill-history-reuse.md), [서버 자산 실측](research/server-data-inventory.md): 당시 조사·선택 근거. 현재 수집 성공·전체 검색 품질·최신 이슈 선정 완료와 구분한다.
- [개발 서버](../infra/development-server.md), [개발 HTTPS 인계](../infra/development-https.md), [운영 배포 상태](../infra/public-deployment.md), [PostgreSQL 준비](../infra/postgresql.md), [관리자 요청](../infra/administrator-request.md): 실제 환경·접근·운영 미완료 조건.
- [이전 기록](planning/archive.md): 와이어프레임 종료·재사용 자산·초기 계획 사이트 이력. 이전 결정을 지우지 않고 대체 관계를 보존한다.

## 협업과 완료 기록

1. 시작할 때 현재 계획·작업·진행과 관련 변경 명세를 읽고 Git 상태를 확인한다. 승인된 통상 구현 선택 때문에 같은 승인을 반복 요청하지 않는다.
2. 코드와 관련 문서를 같은 브랜치에서 갱신한다. 일반 개발은 에이전트 지침의 spec-driven 절차를 따르고 결정이 바뀌면 날짜·근거·영향·대체 관계를 남긴다.
3. 변경에 맞는 테스트·타입·빌드·계약·문서 확인을 수행한다. 버튼/문구 같은 낮은 영향 변경에 구현을 되풀이하는 새 테스트를 만들지 않는다. 기존 의미 있는 질문 복원·권한·생성/취소·재접속·원문 경로를 보존한다.
4. 코드 구현·합성 검사·독립 브라우저·실제 데이터/모델·개인 개발 적용·Sites·운영 게시를 각각 기록한다. 하나의 성공을 다른 단계 완료로 바꾸지 않는다.
5. PR과 인계에는 현재 상태·검증·남은 입력·다음 행동을 남긴다. 과거 완료 상세는 진행 이력으로 옮기고 중복된 미완료 목록을 활성 계획에 남기지 않는다.

진행 기록에는 `작업/관련 요구사항`, `담당/브랜치/PR`, `범위/현재 상태`, `검증/미검증`, `남은 입력`, `다음 행동`, `Sites 반영 상태`를 적는다. Sites 미반영은 대기로 표시하고 사용자가 열어 둔 탭을 자동으로 열거나 이동하지 않는다. 비공개 운영 계정·초대·원자료·자격 증명은 공개 기록에 남기지 않는다.

마일스톤 상태는 `planning/implementation-plan.md`의 표 한 곳에서 관리한다. 작업 목록의 완료 항목과 진행 기록의 검증/적용 증거로 갱신하며 Sites에는 같은 상태를 요약한다. 문서 자동 동기화나 무인 주기 갱신은 구현하지 않았으며, 작업할 때마다 갱신한다.
