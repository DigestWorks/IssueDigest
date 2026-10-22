# 문서 안내·협업 방법

최신 실제 평가: [table 검수5회](research/role-table-acceptance.md). 긴 자료도 전체 원문/추출을 유지해 검수를 완료했지만, 사전 역할 오류8대상 중 탐지2/미탐6이며 추가진단3개는 판정 유보다. 참고$0.0355525·원래 결과/비용을 보존하고 앱 연결을 보류한다.

현재 구현: [무손실 table 검수 SDK](changes/role-table-audit-implementation.md). 원문·추출 결과를 그대로 복원하는 입력과 별도 검수 영수증/실제 잔여 예산을 구현했다. 독립 검토·전체8,099개 검사/빌드/계약 검증과 오프라인 mock을 통과했다. 실제 AI 읽기/의미 품질과 앱 적용은 후속이다.

최신 설계: [역할 적용·무손실 table 검수 입력](changes/role-application-table-audit.md). 원문/원래 결과를 보존한 mock 전송/왕복 복원을 확인하고 별도 codec·SDK 구현을 준비한다. 실제 v2 평가의 비분쟁1/4·검수 미탐·입력 차단을 보존하며 table 표현의 실제 의미 개선은 미검증이다.

다음 계약: [역할 경계·출력 배분 v2](changes/semantic-boundary-balanced-output.md). 정보 누락과 역할 분류를 분리하고 확실한 중요한 한정어 손실은 누락으로 남긴다. 총출력2,500을 유지하며 생성최대1,800/검수실제잔여 배분을 설계·mock 확인했다. 두 압축안은 커져 보류했으며 새SDK/실제완료·의미 개선은 미검증이다.

최신 실제 평가: [전체 역할 생성·검수](research/role-aware-acceptance.md). 실제6요청/반환5·출력 미완료 거부1, 후속 무호출1이다. 증감 자료 생성은 필수6수치/방향 충족, 오류 검수2건은 필수5진단을 찾았으나 정상 기준 충돌2개와 긴 원문 출력 부족이 남아 앱 반영을 보류한다.

현재 구현: [전체 역할 생성·검수 SDK](changes/role-aware-generation-audit.md). 원문 전체·명시 증감 근거, 목적/비교 기준까지 읽는 검수와 legacy coverage·진단 대상 묶음·합산 예산을 구현했다. 독립 검토와 전체7,582개 검증/무호출 용량 확인을 마쳤으며 실제 의미 개선·앱 적용은 후속이다.

현재 인수: [compact 생성·역할 검수7회](research/compact-scope-acceptance.md). 생성2반환/의미0/2, 검수5시도/4반환·출력 미완료 거부1이다. 기존 오류를 탐지했지만 정상/허용 기준과 충돌하는 진단도 있어 앱 적용을 보류한다. 원래 결과/기준·실패 사용량과 참고$0.0897140을 보존했다.


설계 당시 기록: [원문 중복 축소·수치 역할 검수](changes/compact-source-scope-audit.md). 문장 목록으로 원문을 정확히 복원하는 시제품에서 기존 차단 자료의 요청을20,692→18,575로 줄였다. 별도 AI 검수는 원래 답을 고치지 않고 네 역할의 누락/추가/불확실성을 표시하며 생성+검수의 합산 한도를 유지한다. 이는 설계 시제품 당시 기록이다. 두 SDK 구현/전체7,366개 검증 이후의 실제 품질 결과는 위 현재 인수를 따른다.

현재 인수: [수치 후보 v2 생성의 제한 검증](research/shared-context-v2-acceptance.md). 실제3회 모두 반환했지만 의미 기준은1/3이다. 필수 수치7개·단위/근사는 보존했으나 지역/사업 연도 누락과 운영 주체의 범위 오인이 남았다. 새 다문단 자료1건은 송신 전 용량 차단이다. 앱 적용을 보류하며 원래 결과·비용을 보존한다.

현재 구현: [수치 후보 v2의 생성 연결](changes/shared-context-v2.md). 원문 단위·근사 표현을 새 단일 요청과 저장 결과 재구성까지 연결했다. 전체7,206개 검사와 기존421파일 보존을 확인했다. 실제 모델 의미 인수·앱 적용은 아직 없으며 이전 실패를 보존한다.

현재 구현: [복합 단위·근사 후보 v2](changes/numeric-candidates-v2.md). 학교·사람 단위와 근사 표현을 원문 span으로 보존하는 순수 후보 계약을 추가했다. 전체7,099개 검사와 기존419파일 보존을 확인했다. 기존 자료의 두 후보 누락은 오프라인 재구성으로 확인했으며 새 AI 호출/앱 적용은0이다.

현재 인수: [새 자료 점검](research/role-guidance-acceptance.md). 두 자료 중 하나는 수치 후보 단위·근사 표현 누락으로 모델 호출 전에 차단했고, 나머지 실제1회는 반환했으나 필수 하위 지역 누락으로 의미 미충족이다. 다음은 후보 계약 보완이며 앱 적용은 보류한다.

현재 구현: [측정 대상·계층적 범위 지침](changes/shared-context-role-guidance.md). 별도 생성 경로와 합성 검증을 추가했다. 전체7,049개 검사 통과와 기존417파일 보존을 확인했다. 실제 AI 의미 개선·앱 적용은 아직 검증하지 않았다.

현재 비교: [동일 계약 모델4회](research/shared-context-model-comparison.md). GPT-6.1 Sol은4건 모두 반환했으나 의미 기준은2/4 충족이다. 대상·필수 광역 범위 누락이 남아 앱/기본 모델은 바꾸지 않았다. 그룹 출력 즉시 구현을 보류하고 의미 품질을 우선 검토한다.

현재 인수: [공유 맥락 생성의 실제4회](research/shared-context-acceptance.md). 반환1건은 필수 별도 범위를 누락해 의미 미충족이고3건은 구조 거부로 의미 미판정이다. 기존 결과·상한/비용을 보존하며 앱 적용은 보류한다. 다음은 [측정 그룹 출력 제안](changes/measurement-group-output.md)이며 아직 구현하지 않았다.

현재 구현: [공유 맥락 생성 SDK](changes/shared-context-generation.md). 새 순수 계약을 단일 borrowed-model 요청에 연결했다. 전체7,019개 검사·독립 검토와 기존4자료 원문 전체의 오프라인 요청 용량을 확인했다. 실제 AI 호출0이며 의미 품질·앱 적용은 후속이다.

현재 구현: [공유 측정 맥락](changes/shared-measurement-context.md). 공통 항목/범위·보고 사건을 명시 연결하고 목적을 조건과 분리하는 순수 adapter를 추가했다. 독립 검토와 전체6,916개 검사를 통과했다. 이 순수 계약의 생성 연결은 위 SDK 기록을 따르며, 미관측 의미 품질·앱 적용은 후속이다. 기존 결과와 요청 설정은 보존한다.

현재 연구: [동일 계약 추론 비교](research/measurement-reasoning-comparison.md). 네 시도 중 반환2개 모두 의미 미충족·다른2개 미판정으로 설정/앱을 바꾸지 않았다. 공유 맥락의 설계 후 순수 구현은 위 현재 기록을 따르며, 이 연구 당시 실행 코드는 보존했다.

현재 구현: [측정 범위 생성·문장 상태 근거](changes/measurement-frame-generation.md). 새 범위 계약과 단일 요청을 연결하고 전체6,667개 검사를 통과했다. 실제4회는 수치17개를 보존했지만 의미 기준0/4로 앱 적용을 보류한다. [결과·남은 오류](research/measurement-frame-generation-acceptance.md)를 보존한다.

현재 구현: [측정 대상·적용 범위 분리](changes/measurement-scope-contract.md). 같은 대상의 지역·집단·기관 범위를 별도 원문으로 연결하는 순수 계약이다. 신규207/전체6,544개 구조 검사를 통과했지만 AI 선택/상태 근거·미관측 자료·앱 연결은 후속이다. 새 모델 호출과 앱 변경은 없다.

현재 구현: [범위·상태 근거 지침](changes/scoped-contextual-generation.md). 기존 v1 요청을 공유하고 별도 선택 지침을 추가했다. 전체6,337개 검사와 v1 호환을 확인했지만 실제4회는 기존1/2·새합성1/2 충족으로 의미 오류가 남아 앱 적용은 보류한다.

이전 구현: [문맥 프레임 생성 SDK](changes/contextual-frame-generation.md). 역할·관계 근거의 반복 표현을 명시 문맥으로 구분하는 별도 단일 요청 경로다. 전체6,240개 검사를 통과했지만 실제2회는 반환2/의미 기준0/2로 대상 범위·상태 근거 오류가 남아 기존 앱은 보존한다.

이전 구현: [문맥 기반 원문 참조](changes/contextual-anchor.md). 같은 문장의 명시적 문맥으로 반복 표현의 짧은 원문 위치를 구분한다. 실제 AI 선택·프레임/앱 연결은 별도 인수하며 이전 모델의 실패 결과는 유지한다.

IssueDigest는 질문에서 시작하는 B2C 브리핑 서비스다. [제품 경험 인터뷰](research/product-experience-interview.md)와 [D016·D017·D019·D020·D021·D022](planning/decisions.md)의 사용자 선택을 기준으로 질문→짧은 브리핑→필요한 비교·변화·반응·근거를 잇는다. 현재 자료·브리핑 기록은 초대된 초기 검증 참여자의 공유 자료 범위이며 공개 피드나 개인 보관함이 아니다.

저장소 문서가 결정 원본이고 PR에서 변경을 검토한다. 별도 이슈 트래커는 사용하지 않는다. Sites는 검증된 현재 상태의 요약이며 독립된 요구사항 원본으로 복제하지 않는다.

화면 기준: [소비자 브리핑 디자인](changes/consumer-briefing-design.md). 선택한 모바일 브리핑형의 실제 웹 적용과 검증 범위를 따른다.

현재 연구: [모델 제한 비교](research/frame-model-comparison.md). 같은 계약·신규2회에서 고정 의미 기준 수동충족1/2지만 반복 anchor 전체 거부는 남는다. 운영 기본 모델/최신 전체 모델의 우열 판정은 아니다.

현재 인수: [수치 프레임 생성 SDK](changes/numeric-frame-generation.md). 새 프레임을 모델이 채우는 별도 경로다. 전체5937개 통과·[실제2회 부분1/거부1·의미0/2](research/numeric-frame-generation-acceptance.md)를 구분하며 앱 적용은 보류한다.

현재 구현: [수치 의미 역할 프레임](changes/numeric-evidence-frame.md). 역할별 정확 원문 연결과 직접 포함 관계를 분리하는 순수 계약이다. 실제 모델 의미 개선·앱 연결은 별도 인수한다.

현재 조사: [역할 지침 제한 비교](research/numeric-role-guidance-trial.md). 신규2호출/반환2·의미 완전0/2와 새 역할 분리 계약을 기록했다. 기존 기준/결과는 보존한다.

이전 변경: [수치 역할의 고정 기준 평가](changes/numeric-selection-evaluation.md). 기존 두 결과를 새 모델 호출 없이 재생하고 필드 차이·미판정·거부와 알려진 비용을 구분한다. 사후 형식 변환으로 원래 gold/의미 완전0/2를 재판정하지 않는다.

이전 변경: [수치 후보 선택·의미 근거](changes/numeric-candidate-selection.md). 실제 고정2회는 부분1·거부1·의미 완전0/2다. 반환 수치6개/관계 보존과 전망 조건 누락·반복 anchor 거부를 함께 기록했다. 원문 위치/구조와 의미·최종 브리핑·앱 인수를 구분한다.

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
| [수치 후보 선택·의미 근거](changes/numeric-candidate-selection.md) | 후보ID·문장 exact anchor·bounded SDK·실제2회 부분/거부와 의미 한계 |
| [서버 수치·단위·문장 후보](changes/numeric-candidate-index.md) | 순수 표기/단위·범위/수식어·문장 참조·오프라인 누락/오탐·미지원 경계 |
| [서버 원문 위치 참조 수치](changes/numeric-evidence-references.md) | 글자 reference·정확 resolver·별도 전망/조건·실제2회 거부와 후보 경계 후속 |
| [compact 수치·상태·관계 근거](changes/numeric-evidence-compact.md) | whole 인용 참조·상태 근거 union·관계 statement·실제2회 거부와 다음 위치 참조 설계 |
| [정확 인용의 수치 근거 후보](changes/numeric-evidence-proposals.md) | 원문 span/포함·병렬·unreviewed/독립 모델 상한·실제2 SDK의 부분/거부와 앱 연결 전 경계 |
| [첫 요약의 수치 관계·조건 설명](changes/briefing-numeric-clarity.md) | v10 지침/호환 실행·원래3/신규1 실제 인수 실패·개발 보류와 다음 구조 설계 |
| [관련성 선택의 실제 조사 연결](changes/briefing-relevance-integration.md) | 새 private v9·선택 근거/합산 예산/현재 권한·취소/복구·원래 입력/시작 표식과 실제 인수 |
| [질문·근거 후보 관련성 선택](changes/evidence-relevance-selection.md) | 인용에 묶인 후보 전체 triage·불확실 보존·bounded usage·실제3회와 연결 전 경계 |
| [계획 검색의 누락·무관 자료 평가](changes/planned-retrieval-evaluation.md) | 읽기 전용 원래/계획 검색 비교·명시 판정/미판정·출처/분모·private report |
| [원문 날짜·포함 관계 보존](changes/briefing-source-fidelity.md) | private v8의 실제 날짜 후보·날짜0 비교/요약·수치 관계/상태와 실제 의미 한계 |
| [질문별 조사 계획·승인 자료 검색](changes/briefing-search-agent.md) | 새 private v7의 계획/검색/생성·원자 근거 고정·합산 비용·단계별 복구 |
| [첫 결론·근거 부족·문장별 귀속](changes/briefing-core-answer.md) | 새 private v6의 provider 단순화·열린 첫 요약·보수적 귀속·근거 부족과 실제 인수 |
| [브리핑 답변 품질](changes/briefing-answer-quality.md) | 새 private v5·strict 응답/인용·기존 복구·실제 인수의 의미 한계 |
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
