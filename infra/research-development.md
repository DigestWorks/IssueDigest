# 조사 기능 개발 실행

## 공개 읽기 개발 계약 · D020

공개 GET/웹은 private 연구 저장소·세션·모델/DBOS·예약을 만들지 않는다. 기본 앱은 public_repository 미설정503이며 신뢰 runtime이 명시 주입한다. 기존0006 자료·권한·Google 초대/세션·워커 정책은 보존한다. 공개용0007은 독립 게시 테이블이고 앱 import/startup에서 migration·자동 게시를 하지 않는다.

개인 개발 적용은 컨트롤러가 사전 백업→소유자 migration/기존 앱 역할 최소 DML→별도 DB 복원/전체 PG·공개/비공개 경계 검사→문서별 권리/전체 내용 검토한1건의 canonical 계획 hash 확인→명시 게시/반복 검증→같은 개발 도메인 웹/API 적용 순서로 수행한다. 실제 원문·계획·계정·UUID/키는 Git/PR/Sites에 넣지 않는다. 사진/외부 저작물 제외와 정확 공식 policyNewsView URL·공공누리 제1유형을 문서마다 확인한다. 기존 private 실행을 공개로 전환하지 않는다. 워커가 바뀌지 않으면 강제 재시작하지 않는다. main/운영은 유예하고 실제 적용/검증 증거는 진행 기록에서 별도로 남긴다.


현재 적용 결과·개발 주소·실제 AI 연결 상태는 [진행 기록](../docs/planning/progress.md)을 따른다. [현재 D019·D020·D021·D022 계약](../docs/planning/requirements-design.md)이 수용 기준이며, 이 문서는 실행 경계와 복구 주의사항이다. main/운영 배포는 D013에 따라 유예한다.

## 앱에서 하는 일

1. **홈**에서 질문을 적는다. 질문과 선택적인 완료 부모 실행만 제출한다. 새v7은 검색어 계획1회(1~3개) 뒤 원래 질문 검색과 함께 현재 접근 가능한 승인 저장 색인을 조회하고 최대5근거를 원자 고정한다. 검색0이면 알려진 planner 사용량을 기록하고 최종 생성 없이insufficient_evidence로 끝낸다. AI 웹 검색·전체 최신 검색은 아니다. 비회원 초안은 같은 탭에서 최대30분 보존하고 로그인 후 직접 실행한다.
2. 요청 접수 → 관련 자료 찾기 → 자료 분석 → 인용 연결 확인을 표시한다. 취소·실패·연결 대기·월 한도를 구분한다.
3. AI가 질문에 맞는 요약·비교·타임라인을 선택한다. 서버가 허용된 구조와 인용을 대조한 결과만 표시한다. 자료에 없는 날짜·효과·수치·관계는 생성 범위가 아니다.
4. 완료 브리핑의 정확 인용에서 **근거 열기**를 누르면 본문을 떠나지 않는 창에서 해당 버전의 저장된 원문과 인용 위치를 연다. 자동 중복 원문 블록이나 검증된 AI 부분 답변은 제공하지 않는다. 위치 일치는 주장의 참·거짓 판정이 아니다. AI 해석은 별도로 표시한다. 새 privatev7은 자료에 기록됨·출처의 주장·확인하기 어려움과 선택 인용의 짧은 AI 평가 설명을 펼쳐 읽는다. 독립 사실 검증이 아니며 과거/공개 결과에는 소급하지 않는다.
5. 원문을 보고 돌아와도 작성 중인 질문을 유지한다. 로그인 후 초안은 사용자·공간·조사별 앱 메모리에만 두며 로그아웃·계정/권한 변경·새 조사 때 지운다. 완료 결과는 공동 조사 기록에 자동 저장한다. 개인 비공개 북마크가 아니다. **브리핑 기록**과 새로고침은 저장된 결과를 읽으며 모델을 호출하지 않는다. 후속 질문은 이전 완료 결과를 맥락으로 전달한다. 일반적인 무검색어 후속 질문만 부모의 실제 근거를 재사용하며 명시 새 주제의 검색 실패에는 적용하지 않는다.

최근 기본 정보 법안의 미수집 이력을 ‘실제 이벤트가 없다’고 해석하면 안 된다. 과거 법안 제안 내용·처리 이력은 별도 스냅샷으로 추가하고 과거 기록임을 표시한다. 전문·최신 상태·AI 해석과 구분한다. 원본 MySQL과 참조 자료에는 쓰지 않는다. 정기 수집·법안 변경 자동 감지는 현재 질문 전용 흐름의 완료 범위가 아니다.

새 실행/에이전트는v7이고 원래v2/v3/v4/v5/v6 agent/지침/schema/prompt bytes/유료 정수slot1과 저장 결과는 보존한다. 최초 업그레이드 전 기존v2 worker를 중지하고 활성run/workflow가 없는 quiescent 상태를 확인한 뒤 웹/API/worker를 함께 갱신한다. 진행 중 작업은 임의 폐기하지 않는다. 현재 source 구현과 실제 개발 적용은 진행 기록에서 구분한다.

worker는 전용 AUTOCOMMIT PostgreSQL 연결의 고정 session advisory lock으로 전체 수명을 잠근다. 두 번째 기동은 상태 변경/취소/모델 호출 전에 거부한다. poll/cohort/저장 전 소유를 확인하고 잠금 연결 오류는 계속 실행하지 않는 고정 실패다. 정상 종료는 unlock/close하며 SIGKILL은 PostgreSQL 세션과 함께 잠금을 해제한다. 최초v2는 잠금을 모르므로 quiescent rollout 조건은 별도 필수다. API/UI에 이 운영 제약을 사용자 흐름으로 추가하지 않는다.

기존 활성 run에 연결된 knownv2/v3/v4/v5/v6/v7 PENDING/ENQUEUED만 공용 DBOSClient metadata API로20개씩 확인한다. 원래 application_version cohort를 순차 launch/회복·registry destroy한 뒤 현재 버전에서 새 queued 요청만v7로 시작한다. DBOS3.2 resume는 기록 version을 유지하므로 현재 version만 기동해서는 구 작업이 처리되지 않는다. 기존 ID와 checkpoint를 보존하며 version SQL 재작성/새 workflow ID/SDK private API를 사용하지 않는다. terminal/cancelled/unknown workflow는 resume하지 않는다. 실제 application row로 소유를 확인한 정확 ID의 불명확/terminal PENDING/ENQUEUED만 취소한다.

## 명시 초기화와 권한

- PostgreSQL migration `0005_research_journey`: 자료 제목 sidecar·조사 실행·진행 이벤트·월 예약 테이블. 기존 불변 근거·인증 데이터를 보존한다.
- DBOS의 `dbos` 스키마는 제공된 migration 소유자로 `DBOS.migrate(owner_url, application_role=existing_app_role)`를 별도 실행한다. 기존 앱 역할에는 필요한 테이블 DML만 부여하며 public/dbos의 CREATE를 주지 않는다.
- 워커는 `run_migrations=False`로 시작한다. 앱 import/startup에서 migration·모델 호출·자료 등록을 하지 않는다.
- 적용 전에 서버 외부 full/app 백업을 확보한다. 앱 범위 복원은 별도의 소유 loopback 검증 DB에서만 수행한다. 실제 DB의 reset·테스트·downgrade·복원을 수행하지 않는다.
- 자료 추가는 기존 비공개 계획 등록 CLI의 offline → check → apply → repeat 순서로 진행한다. 표시 제목은 별도 sidecar이며 기존 snapshot·원문 hash를 바꾸지 않는다.

정확한 SDK/CLI 구성과 환경변수는 [워커](../apps/worker/README.md), [API](../apps/api/README.md), [저장 패키지](../packages/storage/README.md)를 따른다. 접속값·키·실제 계정·질문·원문은 문서/로그/Git에 기록하지 않는다.

## AI 연결과 비용

서버에 `OPENAI_API_KEY`를 안전하게 공급하고 워커를 시작한 뒤 API의 `ISSUEDIGEST_RESEARCH_ENABLED=1`을 명시한다. 두 설정은 별개다. 키가 없으면 활성화하지 않으며, POST는 예약·모델 호출 전에 연결 대기로 거부한다. 예시나 합성 모델을 실제 앱의 fallback으로 쓰지 않는다.

모델은 `gpt-5.4-mini`, Responses store=False·AsyncOpenAI max_retries0이며 PydanticAI2.56.0/DBOS3.2.0을 고정한다. 월 글로벌 예약USD10·건USD0.25·최대40건/현재 범위 동시1건이다. 이는 실제 청구 정산이나 전체 운영비 상한이 아니다. 실패/취소/유실 예약을 자동 반환하지 않는다.

새v7은 planner1회(15초/출력500/총8,000)→durable search→최종1회(45초/출력2,000)이며 합산 입력+출력24,000/출력2,500을 유지한다. planner static1,091+prompt4,361+framing2,048+출력500을 포함하고 실제 raw/normalized schema를 호출 전에 재검사한다. 최종은 실제 planner input+output을 차감한 잔여에서v6 static11,101/framing2,048/출력2,000을 제외한 dynamic prompt 한도를 적용한다. 원래 질문은 그대로이며 선택적 이전 AI 맥락만 planner JSON UTF-8 예산으로 짧게 하고 잘림을 명시한다. 최종의 기존bounded 맥락·정확 인용은 보존한다.

같은 request ID/입력의 재확인은 새 유료 실행을 만들지 않는다. v7 planner model.request 정수slot1→검색step2→최종model.request3의 정확 metadata를 current stage별 확인한다. retrieving은 완료planner(선택적 완료검색)만 재생하며 아직 시작하지 않은 final 첫 호출은 가능하다. generating/validating은 세step 모두 완료돼야 한다. 불명확/추가/위조 metadata는 재요청 없이 실패·예약 유지다. 두 유료 응답의 raw exact-int/nonbool/비음수/한도와 aggregate 일치를 확인하며 cached replay에도 적용한다. 취소/권한 변경 뒤 새 유료 작업이나 게시를 하지 않는다. 사용량을 확인하지 못한0은 무료가 아니다.

기존v2~v6의 원래 이름/version/유료정수slot1·지침/schema/prompt bytes/결과는 동결한다. 역사prompt한도17,309/16,049/14,813/9,440/8,351과v6의1요청/출력2,500/60초는 과거 재생용이다. 원래IDs/version과DBOS journal을 재작성하지 않는다. exact source별32/전체100 인용·5자료·본문12,000자 선택 계약과 canonical/API/public 경계는 유지한다. 새 경로는 외부웹/임의URL/SQL/셸 도구를 제공하지 않는다.

답변의 보조 free-text 메시지는 화면에 중복 게시하지 않고 검증된 주장/모듈만 정식 결과로 저장한다. 자료 부족·추가 질문의 설명은 유지한다. 서버가 찾은 근거의 출처/제목/정확 인용을 모델 입력에 명시하고 질문에 기반한 시사 브리핑으로 처리한다. 생성 후 검증에서 실패해도 이미 확인한 토큰 사용량은 실패 상태에 기록한다. 제공자 응답 자체를 받지 못해 사용량을 모르는 경우의0기록은 무료 청구를 뜻하지 않으며 예약을 유지한다.

## 검증 증거를 구분하기

- 단위/계약/실제 PostgreSQL·DBOS 중단 복구 검사는 합성 전용 DB를 사용한다.
- 실제 자료 복원본 + 별도의 합성 신원 + 실제 HTTP/DBOS + 합성 FunctionModel 브라우저 검사는 앱의 연결·저장·인용·취소를 검증한다. 실제 모델의 추론 품질이나 청구 검증이 아니다.
- 실제 모델 검증은 승인된 키와 제한된 요청으로 따로 기록한다. 실제 사용자의 세션을 임의 발급하거나 재사용하지 않는다.
- 개발 HTTPS에서 정적 빌드 일치·미인증401·API/헬스·쿠키/Origin 경계를 확인한다. 이 확인만으로 사용자의 로그인 뒤 여정이나 운영 출시가 완료되지는 않는다.

D022 v4의 역사 실제 모델 검증은 controller가 별도 소유 평가 환경에서 최대3요청·재시도 없이 수행하고 실패까지 모두 기록한다. 단순 키워드 검사나 합성 고정 출력으로 귀속·수치 의미 품질을 판정하지 않는다. 검토한 공개 원문·합성 신원을 사용하고 실제 사용자의 계정/세션을 분리한다. 실제 개발 적용 전 활성 작업을 완료하고 사전/사후 백업·별도 복원·정상 HTTPS·정적 빌드/권한/원문 일치를 확인한다. 이 문서 변경 자체는 적용 완료 증거가 아니다.

2026-10-18 개인 개발 적용: 제품1c0c5ed·새v4/기존v2/v3 복구를 반영했다. 활성 작업0 확인·전후 백업/별도 복원·앱21테이블/공개v1 보존·TLS/정적/보호 경계를 확인했다. 실제3요청의 두 수치 응답은 부분 충족이며 전체 의미 품질 완료가 아니다. 상세 검증과 Sites 반영 상태는 진행 기록을 따른다.


## v6 provider와 실제 평가 범위 · 2026-10-19

[현재 명세](../docs/changes/briefing-core-answer.md). core_answer를 첫 열린 요약으로 정하고 긍정 해석은 서버 고정 ‘제공 자료에 따르면, ’의 attributed로 변환한다. 추가/상세 assessment는 source_statement/uncertain이며 canonical documented와 정확 세 review/공개 경계는 그대로다. 날짜는 typed timeline에만 허용하고 정확 YYYY-MM-DD 원문 인용을 요구한다. 일반 claim의 임의 날짜·provider category/source_subject 모순 조합을 허용하거나 수리하지 않는다. 핵심에 직접 답할 근거가 없으면 자료 범위의 비답변으로 끝낸다. 원문·질문·이전 AI는 지시가 아닌 입력 데이터다.

초기 실제4회(부족 완료1/검증 실패3)를 보존하고, provider 단순화 뒤 별도2회만 추가해 총6회로 제한한다. 이전v5 초기4+별도2와 섞지 않는다. 실패해도 이미 유료 공급자 호출이 있었을 수 있으므로 앱 usage0을 비용0으로 해석하지 않는다. actual cached usage·의미 판정·개발 적용 source/시각·백업 복원은 [진행 기록](../docs/planning/progress.md)의 최종 증거를 따른다. 구조 통과·분기 성공·실제 의미 품질·운영 출시는 각각 다른 판정이다.


## v7 현재 실행·인수 · 2026-10-19

현재 개인 개발 웹/API/조사 worker는 `57c71ec`이며 [Draft PR44](https://github.com/DigestWorks/IssueDigest/pull/44)(PR43 기반)다. 새 private v7은 질문→검색어 계획1회→현재 권한의 승인 저장 색인 검색→최대5근거 원자 고정→최종 생성1회다. 원래 질문 검색을 항상 포함하고 계획 검색과 원래 질문 우선 라운드로빈으로 합친다. 계획은 근거가 아니며 외부 웹 탐색·자동 등록/공개 게시를 추가하지 않는다. 첫 요약·보수적 제공 자료 귀속·정확 인용·부족 응답과 기존 소비자 디자인을 유지한다.

실제 고정3앱실행/공급자6요청·자동재시도0은 브리핑 완료1(의미 부분 충족)·자료 부족 완료1·검증 실패1이다. 원래 문자 검색0이던 영어 표현의 주택 질문은 계획 검색으로 정확 자료1건을 찾았으나, 최종 timeline이 원문에 없는 정확 날짜2개를 추정해 표시를 차단했다. 성공까지 다시 호출하지 않았다. 완료 답변의9문장/평가·선택 인용3개와 실패 checkpoint의6문장/인용을 직접 대조했다. 목표·실적·조건부 전망의 첫 결론은 읽히지만 세부 항목의 포함 관계 누락과 목표/확정 결과의 모호한 표현은 남았다. 자료에 없는 전국 찬성률·인지도는 생성하지 않고 근거 부족으로 끝났다. 검색 개선·구조 통과를 전체 의미 품질 완료로 해석하지 않는다. cached 실제 사용량은 입력9,413/출력2,087토큰이며3실행 지연은8.39/5.76/3.96초다. 모든 유료 응답6개를 확인했고 실제 청구 금액은 미검증이다. 실패/취소·권한 변경·응답 유실의 앱 usage0은 무료를 뜻하지 않으며 기존 보수적 예약을 유지한다. 이전v6 초기4(부족1/실패3)+별도2와v5 초기4+별도2의 실패·부분 충족 분모를 보존한다.

개발 웹/API/worker를 활성 작업0에서 정상 중지·재기동하고 단일 worker lock1·새 source/cwd·정적19파일/외부6assets 일치를 확인했다. 이전90assets/원래 source/복귀 경로와 수집기a908083/config/runner/cron을 보존했다. schema0009·자료15/인용49/검색36/receipt1/공개1·계정/세션·HTTPS/비회원401 경계를 유지했다. 서버 밖 사전·직전·사후 full/app 백업과 별도PG18.6 복원에서 직전/사후/백업 직후/복원의23public테이블 rowhash/count 전체 일치·15canonical을 확인했다. 실제 기존 AI 결과는0개이므로 역사 실제 결과 재생을 주장하지 않는다. DBOS registry·vector/역할까지 포함한 완전 DR은 아니다. main/운영 유예(D013)는 유지한다. 상세 사용량/평가·현재 출판 상태는 [진행 기록](../docs/planning/progress.md)을 따른다.
