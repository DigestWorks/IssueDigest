# 조사 기능 개발 실행

## 공개 읽기 개발 계약 · D020

공개 GET/웹은 private 연구 저장소·세션·모델/DBOS·예약을 만들지 않는다. 기본 앱은 public_repository 미설정503이며 신뢰 runtime이 명시 주입한다. 기존0006 자료·권한·Google 초대/세션·워커 정책은 보존한다. 공개용0007은 독립 게시 테이블이고 앱 import/startup에서 migration·자동 게시를 하지 않는다.

개인 개발 적용은 컨트롤러가 사전 백업→소유자 migration/기존 앱 역할 최소 DML→별도 DB 복원/전체 PG·공개/비공개 경계 검사→문서별 권리/전체 내용 검토한1건의 canonical 계획 hash 확인→명시 게시/반복 검증→같은 개발 도메인 웹/API 적용 순서로 수행한다. 실제 원문·계획·계정·UUID/키는 Git/PR/Sites에 넣지 않는다. 사진/외부 저작물 제외와 정확 공식 policyNewsView URL·공공누리 제1유형을 문서마다 확인한다. 기존 private 실행을 공개로 전환하지 않는다. 워커가 바뀌지 않으면 강제 재시작하지 않는다. main/운영은 유예하고 실제 적용/검증 증거는 진행 기록에서 별도로 남긴다.


현재 적용 결과·개발 주소·실제 AI 연결 상태는 [진행 기록](../docs/planning/progress.md)을 따른다. [현재 D019·D020·D021·D022 계약](../docs/planning/requirements-design.md)이 수용 기준이며, 이 문서는 실행 경계와 복구 주의사항이다. main/운영 배포는 D013에 따라 유예한다.

## 앱에서 하는 일

1. **홈**에서 질문을 적는다. 질문과 선택적인 완료 부모 실행만 제출한다. 새v9은 검색어 계획1회(1~3개) 뒤 원래 질문 검색과 함께 현재 권한의 승인 저장 색인에서 최대5후보를 고정하고, 인용 기반 관련성 선택1회로 명시 무관만 제외해 최종 근거를 원자 고정한다. 검색0/전부 제외면 알려진 planner/selector 사용량을 기록하고 최종 생성 없이insufficient_evidence로 끝낸다. AI 웹 검색·전체 최신 검색은 아니다. 비회원 초안은 같은 탭에서 최대30분 보존하고 로그인 후 직접 실행한다.
2. 요청 접수 → 관련 자료 찾기 → 자료 분석 → 인용 연결 확인을 표시한다. 취소·실패·연결 대기·월 한도를 구분한다.
3. AI가 질문에 맞는 요약·비교·타임라인을 선택한다. 서버가 허용된 구조와 인용을 대조한 결과만 표시한다. 자료에 없는 날짜·효과·수치·관계는 생성 범위가 아니다.
4. 완료 브리핑의 정확 인용에서 **근거 열기**를 누르면 본문을 떠나지 않는 창에서 해당 버전의 저장된 원문과 인용 위치를 연다. 자동 중복 원문 블록이나 검증된 AI 부분 답변은 제공하지 않는다. 위치 일치는 주장의 참·거짓 판정이 아니다. AI 해석은 별도로 표시한다. 새 privatev9은 자료에 기록됨·출처의 주장·확인하기 어려움과 선택 인용의 짧은 AI 평가 설명을 펼쳐 읽는다. 독립 사실 검증이 아니며 과거/공개 결과에는 소급하지 않는다.
5. 원문을 보고 돌아와도 작성 중인 질문을 유지한다. 로그인 후 초안은 사용자·공간·조사별 앱 메모리에만 두며 로그아웃·계정/권한 변경·새 조사 때 지운다. 완료 결과는 공동 조사 기록에 자동 저장한다. 개인 비공개 북마크가 아니다. **브리핑 기록**과 새로고침은 저장된 결과를 읽으며 모델을 호출하지 않는다. 후속 질문은 이전 완료 결과를 맥락으로 전달한다. 일반적인 무검색어 후속 질문만 부모의 실제 근거를 재사용하며 명시 새 주제의 검색 실패에는 적용하지 않는다.

최근 기본 정보 법안의 미수집 이력을 ‘실제 이벤트가 없다’고 해석하면 안 된다. 과거 법안 제안 내용·처리 이력은 별도 스냅샷으로 추가하고 과거 기록임을 표시한다. 전문·최신 상태·AI 해석과 구분한다. 원본 MySQL과 참조 자료에는 쓰지 않는다. 정기 수집·법안 변경 자동 감지는 현재 질문 전용 흐름의 완료 범위가 아니다.

새 실행/에이전트는v9이고 원래v2~v6 agent/지침/schema/prompt bytes/유료 정수slot1과 v7의 planner7/final7·paid1/search7-step2/paid3, v8의 planner7/final8·paid1/search8-step2/paid3·저장 결과를 보존한다. 최초 업그레이드 전 기존v2 worker를 중지하고 활성run/workflow가 없는 quiescent 상태를 확인한 뒤 웹/API/worker를 함께 갱신한다. 진행 중 작업은 임의 폐기하지 않는다. 현재 source 구현과 실제 개발 적용은 진행 기록에서 구분한다.

worker는 전용 AUTOCOMMIT PostgreSQL 연결의 고정 session advisory lock으로 전체 수명을 잠근다. 두 번째 기동은 상태 변경/취소/모델 호출 전에 거부한다. poll/cohort/저장 전 소유를 확인하고 잠금 연결 오류는 계속 실행하지 않는 고정 실패다. 정상 종료는 unlock/close하며 SIGKILL은 PostgreSQL 세션과 함께 잠금을 해제한다. 최초v2는 잠금을 모르므로 quiescent rollout 조건은 별도 필수다. API/UI에 이 운영 제약을 사용자 흐름으로 추가하지 않는다.

기존 활성 run에 연결된 knownv2/v3/v4/v5/v6/v7/v8/v9 PENDING/ENQUEUED만 공용 DBOSClient metadata API로20개씩 확인한다. 원래 application_version cohort를 순차 launch/회복·registry destroy한 뒤 현재 버전에서 새 queued 요청만v9로 시작한다. DBOS3.2 resume는 기록 version을 유지하므로 현재 version만 기동해서는 구 작업이 처리되지 않는다. 기존 ID와 checkpoint를 보존하며 version SQL 재작성/새 workflow ID/SDK private API를 사용하지 않는다. terminal/cancelled/unknown workflow는 resume하지 않는다. 실제 application row로 소유를 확인한 정확 ID의 불명확/terminal PENDING/ENQUEUED만 취소한다.

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

새v9은 planner1회(15초/출력500/총8,000)→search9→selector1회(15초/출력500/총12,000)→apply9→final1회(45초)다. 전체 입력+출력24,000/출력2,500·월 예약을 유지한다. final은 두 prior의 실제 사용량을 차감하고 출력min(2,000,2,500-prior_output)으로1,500..2,000을 허용한다. 최종 static11,907/framing2,048·동적 출력과 실제 raw/normalized envelope·원래 질문/전체 bounded 인용을 사전 검사하고 초과면 호출 전에 거절한다. 최대100인용/16날짜는 동시 적재 보장이 아니다. 지침·동결 SDK·planner7와 과거 이름/version/slot은 보존한다.

같은 request ID/입력 재확인은 새 유료 실행을 만들지 않는다. v9는 paidplanner7-slot1/search9-step2/paidselector9-slot3/apply9-step4/paidfinal9-slot5의 exact namespace·정수nonbool slot·완료 count/order를 raw deserialize 전에 검증한다. queued0/retrieving 완료prefix1..4/generating·validating5만 허용한다. selector 전송 전 public DBOSClient의 workflow attributes에 exact 시작bool+원래 prompt SHA256을 원자 저장하며 표식만 있고 응답이 없거나 입력 hash가 다르면 재호출 없이 실패/예약 유지다. 전송 전 중단도 실패, 적법한 metadata 변경도 replay 거절 비용이 생길 수 있다. cached apply 뒤 현재 권한/모든 원문을 재검사한다. 알려진 raw usage는 v9 token필드만 단조 복원하며 시작 시 exact owned terminal v9 journal을20개씩 재조정한다. status/result/예약·과거 정책을 바꾸지 않고 추가 모델0이며 usage0을 무료로 해석하지 않는다. [v9 명세](../docs/changes/briefing-relevance-integration.md)의 두 Ruling을 따른다.

기존v2~v6의 원래 이름/version/유료정수slot1·지침/schema/prompt bytes/결과와 v7의 원래 planner/final·paid1/search7-step2/paid3은 동결한다. 역사prompt한도17,309/16,049/14,813/9,440/8,351과v6의1요청/출력2,500/60초는 과거 재생용이다. 원래IDs/version과DBOS journal을 재작성하지 않는다. exact source별32/전체100 인용·5자료·본문12,000자 선택 계약과 canonical/API/public 경계는 유지한다. 새 경로는 외부웹/임의URL/SQL/셸 도구를 제공하지 않는다.

답변의 보조 free-text 메시지는 화면에 중복 게시하지 않고 검증된 주장/모듈만 정식 결과로 저장한다. 자료 부족·추가 질문의 설명은 유지한다. 서버가 찾은 근거의 출처/제목/정확 인용을 모델 입력에 명시하고 질문에 기반한 시사 브리핑으로 처리한다. 생성 후 검증에서 실패해도 이미 확인한 토큰 사용량은 실패 상태에 기록한다. 제공자 응답 자체를 받지 못해 사용량을 모르는 경우의0기록은 무료 청구를 뜻하지 않으며 예약을 유지한다.

## 검증 증거를 구분하기

- 단위/계약/실제 PostgreSQL·DBOS 중단 복구 검사는 합성 전용 DB를 사용한다.
- 실제 자료 복원본 + 별도의 합성 신원 + 실제 HTTP/DBOS + 합성 FunctionModel 브라우저 검사는 앱의 연결·저장·인용·취소를 검증한다. 실제 모델의 추론 품질이나 청구 검증이 아니다.
- 실제 모델 검증은 승인된 키와 제한된 요청으로 따로 기록한다. 실제 사용자의 세션을 임의 발급하거나 재사용하지 않는다.
- 개발 HTTPS에서 정적 빌드 일치·미인증401·API/헬스·쿠키/Origin 경계를 확인한다. 이 확인만으로 사용자의 로그인 뒤 여정이나 운영 출시가 완료되지는 않는다.

D022 v4의 역사 실제 모델 검증은 controller가 별도 소유 평가 환경에서 최대3요청·재시도 없이 수행하고 실패까지 모두 기록한다. 단순 키워드 검사나 합성 고정 출력으로 귀속·수치 의미 품질을 판정하지 않는다. 검토한 공개 원문·합성 신원을 사용하고 실제 사용자의 계정/세션을 분리한다. 실제 개발 적용 전 활성 작업을 완료하고 사전/사후 백업·별도 복원·정상 HTTPS·정적 빌드/권한/원문 일치를 확인한다. 이 문서 변경 자체는 적용 완료 증거가 아니다.

2026-10-18 개인 개발 적용: 제품1c0c5ed·새v4/기존v2/v3 복구를 반영했다. 활성 작업0 확인·전후 백업/별도 복원·앱21테이블/공개v1 보존·TLS/정적/보호 경계를 확인했다. 실제3요청의 두 수치 응답은 부분 충족이며 전체 의미 품질 완료가 아니다. 상세 검증과 Sites 반영 상태는 진행 기록을 따른다.


## v6 provider와 실제 평가 범위 · 2026-10-19

[v6 역사 명세](../docs/changes/briefing-core-answer.md). core_answer를 첫 열린 요약으로 정하고 긍정 해석은 서버 고정 ‘제공 자료에 따르면, ’의 attributed로 변환한다. 추가/상세 assessment는 source_statement/uncertain이며 canonical documented와 정확 세 review/공개 경계는 그대로다. 날짜는 typed timeline에만 허용하고 정확 YYYY-MM-DD 원문 인용을 요구한다. 일반 claim의 임의 날짜·provider category/source_subject 모순 조합을 허용하거나 수리하지 않는다. 핵심에 직접 답할 근거가 없으면 자료 범위의 비답변으로 끝낸다. 원문·질문·이전 AI는 지시가 아닌 입력 데이터다.

초기 실제4회(부족 완료1/검증 실패3)를 보존하고, provider 단순화 뒤 별도2회만 추가해 총6회로 제한한다. 이전v5 초기4+별도2와 섞지 않는다. 실패해도 이미 유료 공급자 호출이 있었을 수 있으므로 앱 usage0을 비용0으로 해석하지 않는다. actual cached usage·의미 판정·개발 적용 source/시각·백업 복원은 [진행 기록](../docs/planning/progress.md)의 최종 증거를 따른다. 구조 통과·분기 성공·실제 의미 품질·운영 출시는 각각 다른 판정이다.


## v9 현재 실행·인수 · 2026-10-19

현재 개인 개발 웹/API/조사 worker는 `ab6654e`/private v9이며 [Draft PR48](https://github.com/DigestWorks/IssueDigest/pull/48)(PR47 기반·미병합)다. 원래 질문→planner7→승인 저장 검색→관련성 선택→선택 원문 고정→최종 생성으로 연결했다. 불확실 후보는 남기고 명확한 무관만 제외한다. 선택은 진실/정치적 동의 판정이 아니다. API/공개 읽기/DB schema·로그인·선택한 모바일 디자인과 역사v2~v8 provider·원래 checkpoint를 유지한다.

단일 전체 gate sourceab6654e의 Python3,891+JS764=4,655개·lint/format/types/build/contract가 통과했고 실패/skip/warning0이다. 작업별/전체 백지 검토는 각각 명세/품질 PASS(C0/I0/M0)다. 실제 모델 source5fcdc42와 이후 문서만 다른 검증/개발 source를 구분한다.

v9 source5fcdc42에서 기존 고정3질문·기검토 공개 텍스트3건으로 실제 앱3회/공급자9요청을 한 번씩 실행했다. 자동 재시도0·완료3(답변2/자료 부족1)/실패0이다. 선택 전 후보1/3/3→선택 후1/1/1이며 필요한 동일 핵심 자료는 positive2문항 모두 보존했다. 둘째의 명시 무관2개는0개로 줄었다. 셋째는 주제 자료1개를 남겼지만 human 미판정3개를 그대로 보존하며 제외2개에 정답/precision 가점을 주지 않는다.

controller가 계획3개·관련성 결정7개·서로 다른 제공 인용15종·답변 주장12개/AI평가12개·선택 인용을 모두 직접 대조했다. 첫 답변은 하한을 정확 비율/상한으로 바꾸지 않고 중간 실적·목표·전망을 구분했으나 첫 요약에서 공정 관리 조건은 압축됐다. 둘째는 포함 관계/중복 합산 금지·조건부 전망을 설명했지만 전체 목표를 합산 대상으로 오해할 수 있는 문구가 남았다. 의미 판정은 좁은 목표 충족1·부분 충족1·제공 자료 한정의 적절한 부족1로 기록하며 모델 완료3을 전체 의미 품질 통과로 대신하지 않는다.

선택3과 최종3의 실제 입력·고정 snapshot/evidence를 대조해 선택 자료만 최종 입력과 저장 근거에 포함됨을 확인했다. 실제 known usage는 입력11,502/출력2,207토큰, 실행 지연8.38/8.93/4.32초이며 앱 토큰과 완료 raw응답9개의 합계가 일치했다. 실제 청구 금액은 미검증이다. 기존 selector단독3·v8 3앱/6요청·v7 3/6·v6/v5 초기4+별도2의 실패/부분 분모와 별개다.

같은 주택 주제/정부 자료의 소표본이며 다양한 정치 이슈·상반 입장·복합 주제·실제 공격적 입력·중립성을 인증하지 않는다. 실제 uncertain 결정과 정확 날짜 후보는0이므로 그 양성 분기는 합성 검증만 했다. 원래 질문/원문·ID·raw응답/요청·자체 합성 신원과 시도 receipt는 private에 보존하며 실제 사용자 세션은 사용하지 않았다. main/운영 출시는 D013에 따라 유예한다.

활성 작업0에서 API/worker를 정상 재기동하고 단일 worker 잠금·새 source/cwd·정적 파일 일치를 확인했다. 이전 소스/정적 자산·수집기 소스/runner/config/cron·자료/계정/세션·공개 복사본/비회원 경계를 보존했다. 서버 밖 사전·직전·사후 full/app 백업과 별도 PostgreSQL 복원에서23public테이블 count/rowhash 일치를 확인했다. schema0009 유지·migration0이며 실제 과거 AI 결과0이어서 실제 역사 결과 재생은 주장하지 않는다. DBOS/vector/역할을 포함한 완전 DR은 아니다. main/운영(D013)과 사용자 탭은 유지한다.

## v8 역사 실행·인수 · 2026-10-19

당시 개인 개발 웹/API/조사 worker는 `f839ae0`이며 [Draft PR45](https://github.com/DigestWorks/IssueDigest/pull/45)(PR44 기반)다. 새 private v8은 동결 planner7→승인 저장 검색→최대5근거 고정→최종 생성으로 이어진다. 정확 인용에 있는 유효한 YYYY-MM-DD만 timeline 날짜 후보로 최대16개 허용하고, 후보가 없으면 요약/비교로 설명한다. 개별 인용에 해당 날짜가 있는지도 다시 검사한다. 날짜가 있다는 것과 실제 사건을 뒷받침한다는 것은 다르다. 수치의 포함 관계와 목표·관측 실적·조건부 전망을 보존하도록 지시하며 자유 문장의 의미 정확성을 schema 통과로 인증하지 않는다. 원래 질문/검색·정확 인용·첫 열린 요약·기존 소비자 디자인과 공개 계약은 유지한다.

전체 Python3,553+JS744=4,297개·lint/format/types/build/contract와 작업별/전체 독립 검토(Critical/Important/Minor0)를 통과했다. [source CI](https://github.com/DigestWorks/IssueDigest/actions/runs/39208107011)도 성공했다. 기존v2~v7 provider/지침/한도·원래 workflow/version/유료 checkpoint와 저장 결과를 보존한다. 새v8은 planner7 유료slot1→search_v8 step2→final_v8 유료slot3을 회복한다. 자체 합성 신원으로390/1440·두 테마·첫 열린 요약/접힌 상세·정확 원문/초점·재열람(읽기POST0/페이지오류0)을 확인했다.

실제 고정3앱실행/공급자6요청·자동재시도0은 모두 완료했고 답변2·자료 부족1이다. 의미 판정은 부분 충족1·이번 목표 소표본 충족1·자료 부족1로 구분한다. 이전v7에서 원문에 없는 날짜 때문에 실패했던 표현은 날짜 없는 요약/비교로 완료했다. 첫 답변6문장/6평가/정확 인용3개와 둘째7문장/7평가/정확 인용3개를 전부 대조했다. 둘째는 부분 항목의 포함 관계를 명시하고 독립 합산을 피했다. 없는 전국 여론 수치는 만들지 않았다. 다만 첫 답변의 하한 수치를 ‘목표의 일부’로 표현한 상한 암시, 질문에 없던 검색어 추가·무관 자료 선택, 전망의 조건부 뉘앙스는 남았다. 실제3건 모두 정확 날짜 후보0이며 날짜 있는 실제 제공자 검증은 하지 않았다(합성 Python/client/UI 검증만 통과). 일반 시사·중립성·의미 품질 전체 통과가 아니다.

실제 cached 사용량은 입력9,915/출력1,932토큰,3실행 지연7.80/7.14/3.94초다. 유료 응답6개 모두 확인했고 실제 청구 금액은 미검증이다. 앱 usage0은 무료를 뜻하지 않는다. 이전v7 고정3/6(부분답변1/부족1/실패1), v6 초기4(부족1/실패3)+별도2, v5 초기4+별도2의 실패·부분 충족 분모는 그대로 보존한다.

개발 앱은 활성 작업0에서 정상 재기동·단일 worker lock1·source/cwd·정적19파일/외부6assets 일치를 확인했다. 이전94assets/원래 source/복귀 경로와 수집기a908083/config/runner/cron을 보존했다. schema0009·자료15/인용49/검색36/receipt1/공개1·계정/세션·HTTPS/비회원401 경계를 유지했다. 서버 밖 사전·직전·사후 full/app 백업과 별도PG18.6 복원에서 직전/사후/백업 직후/복원의23public테이블 rowhash/count 전체 일치를 확인했다. 실제 기존 AI 결과는0개이므로 역사 실제 결과 재생을 주장하지 않는다. DBOS registry·vector/역할까지 포함한 완전 DR은 아니다. 외부 정적 파일 읽기의 일시 DNS 오류는 설정 변경 없이 재조회해 정상 확인했다. main/운영 유예(D013)는 유지한다.

판단: 최대100인용·16날짜는 상한이며 모든 최대 조합의 동시 입력을 보장하지 않는다. 의미 보존 지침·원문 전체와 합산24,000 예산을 유지하고 실제 사전 검사에서 초과 입력을 거절한다. 잘못된 판단이면 큰 맥락·planner 사용량이 많은 질문이 최종 생성 전에 자료 부족으로 더 자주 끝날 수 있으며, 추가 유료 재시도 없이 자료 선택/예산 정책과 테스트를 재설계해야 한다.

정확 workflow 이름은 issuedigest_research_run_v8, planner는 동결 issuedigest_research_plan_v7, 검색은 issuedigest_research_search_v8, 최종은 issuedigest_research_v8이다. v7의 원래 이름/slot은 과거 회복에만 그대로 사용한다. v8 지침SHA256은91df818c434cedf73ba3602bcf4f8a77c5ca47e500580e80238dbfd443e9c47a다.

## 역사 v7 실행·인수 · 2026-10-19

당시 개인 개발 웹/API/조사 worker는 `57c71ec`이며 [Draft PR44](https://github.com/DigestWorks/IssueDigest/pull/44)(PR43 기반)다. 새 private v7은 질문→검색어 계획1회→현재 권한의 승인 저장 색인 검색→최대5근거 원자 고정→최종 생성1회다. 원래 질문 검색을 항상 포함하고 계획 검색과 원래 질문 우선 라운드로빈으로 합친다. 계획은 근거가 아니며 외부 웹 탐색·자동 등록/공개 게시를 추가하지 않는다. 첫 요약·보수적 제공 자료 귀속·정확 인용·부족 응답과 기존 소비자 디자인을 유지한다.

실제 고정3앱실행/공급자6요청·자동재시도0은 브리핑 완료1(의미 부분 충족)·자료 부족 완료1·검증 실패1이다. 원래 문자 검색0이던 영어 표현의 주택 질문은 계획 검색으로 정확 자료1건을 찾았으나, 최종 timeline이 원문에 없는 정확 날짜2개를 추정해 표시를 차단했다. 성공까지 다시 호출하지 않았다. 완료 답변의9문장/평가·선택 인용3개와 실패 checkpoint의6문장/인용을 직접 대조했다. 목표·실적·조건부 전망의 첫 결론은 읽히지만 세부 항목의 포함 관계 누락과 목표/확정 결과의 모호한 표현은 남았다. 자료에 없는 전국 찬성률·인지도는 생성하지 않고 근거 부족으로 끝났다. 검색 개선·구조 통과를 전체 의미 품질 완료로 해석하지 않는다. cached 실제 사용량은 입력9,413/출력2,087토큰이며3실행 지연은8.39/5.76/3.96초다. 모든 유료 응답6개를 확인했고 실제 청구 금액은 미검증이다. 실패/취소·권한 변경·응답 유실의 앱 usage0은 무료를 뜻하지 않으며 기존 보수적 예약을 유지한다. 이전v6 초기4(부족1/실패3)+별도2와v5 초기4+별도2의 실패·부분 충족 분모를 보존한다.

개발 웹/API/worker를 활성 작업0에서 정상 중지·재기동하고 단일 worker lock1·새 source/cwd·정적19파일/외부6assets 일치를 확인했다. 이전90assets/원래 source/복귀 경로와 수집기a908083/config/runner/cron을 보존했다. schema0009·자료15/인용49/검색36/receipt1/공개1·계정/세션·HTTPS/비회원401 경계를 유지했다. 서버 밖 사전·직전·사후 full/app 백업과 별도PG18.6 복원에서 직전/사후/백업 직후/복원의23public테이블 rowhash/count 전체 일치·15canonical을 확인했다. 실제 기존 AI 결과는0개이므로 역사 실제 결과 재생을 주장하지 않는다. DBOS registry·vector/역할까지 포함한 완전 DR은 아니다. main/운영 유예(D013)는 유지한다. 상세 사용량/평가·현재 출판 상태는 [진행 기록](../docs/planning/progress.md)을 따른다.

## v10 구현 인수·개발 보류 · 2026-10-19

[명세](../docs/changes/briefing-numeric-clarity.md). 브랜치 코드는 final/profile/workflow10·앞4개의 v9 protocol/receipt·원래9 workflow recovery를 지원하며 새 queued 기본은10이다. 그러나 실제4앱/12요청의 의미 인수를 통과하지 못해 이 브랜치를 개인 개발에 반영하지 않았다. 현재 실행은 ab6654e/v9이고 새 실행/DB migration/계정·세션/수집기·Nginx·main/운영 변경이 없다. 코드 지원과 배포 기본을 구분한다. 이번 read-only 사전 백업/별도 복원23테이블 확인은 사후 배포/완전 DR 인수가 아니다. 상세 품질·소스/전체 gate·독립 검토·PR/Sites는 진행 기록을 따른다.
