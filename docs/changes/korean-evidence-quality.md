# 한국어 근거 검색·평가와 주장·수치 브리핑 개선

2026-10-18. 사용자가 개발 지속을 승인했다. R2/R3/R4/R6·D019~D021과 직전 개발 적용 결과의 한국어 검색·주장 귀속·수치 비교 한계를 개선한다. 기준은 `feat/evidence-exploration`의 `614d0f1`이다. OpenSpec root=null 확인으로 init/승인 재요청 없이 SDD/TDD/독립 검토를 적용한다. 이전 근거 탐색 작업은 완료 상태이며 다시 구현하지 않는다.

## Global Constraints

- IssueDigest의 질문 중심 B2C 여정과 확정 기술을 유지한다. 사용자에게 자료 관리·ID/범위 선택·평가/연결 확인 화면을 추가하지 않는다. 없는 최신 이슈·웹 탐색·개인화·여론·알림을 꾸미지 않는다. 이번 범위는 저장 근거의 검색 품질과 새 private 브리핑·내부 평가 도구다.
- 기존 자료13/인용37/검색27·공개 브리핑1·계정/초대/세션·질문/실행·원문·버전/정확 인용을 보존한다. 기존 Claim/default·canonical JSON/hash·D020 공개v1/v2/빈 review 계약을 변경하지 않는다. DB schema·투영 profile literal-ngrams-v1·lockfile·의존성·인증/권한·14일/7일 세션은 유지한다. main/운영 유예(D013)와 개인 개발 HTTPS 갱신을 구분한다.
- 검색은 현재 workspace·검증한 canonical 근거/투영을 대상으로 한다. 최대8개 주제 묶음·묶음당 최대3변형·총24개 검색 변형·변형당 최대200후보/201번째 truncation 감지·상위20개 서로 다른 snapshot·최종5개를 제한한다. 기본 원문 문자 검색 API는 정확 일치/원위치를 유지한다. 한국어 조사는 원형을 버리지 않고 제한 변형으로만 다루며 숫자/단위/시간/대상·부정·고유명사를 의미가 같은 것으로 합치지 않는다. 외부 사전·LLM 질의 확장·embedding/provider·자동 수집은 도입하지 않는다.
- 검색어 변형과 동일 문서의 여러 문단은 같은 주제의 점수로 중복 가산하지 않는다. 여러 주제 일치와 원형의 직접 일치를 우선하고 동률은 안정된 snapshot ID 순서로 결정한다. Unicode 숫자/ASCII 번호의 동일성을 임의 추정하지 않는다. 띄어쓰기 대응은 명시한 공백 문자만 제거한 전체 문자열의 실제 일치이며 단어 동의어/의미 검색으로 부르지 않는다. 해석한 query와 원문의 인용/선택 위치를 혼합하지 않는다.
- 무관한 기본 자료를 채우지 않는다. 검색어가 없는 일반 후속 질문만 기존의 보수적인 is_generic_followup 규칙으로 부모 근거를 재사용한다. 알 수 없는 주제·기호·과대 token은 일반 후속으로 바꾸지 않는다. 조회/필터는 권한을 대신하지 않으며 worker는 현재 membership을 확인하고 한번 저장한 근거는 재검색하지 않는다. 후보/색인 한도 내 미발견을 세상에 자료가 없음으로 설명하지 않는다.
- 내부 평가는 운영자의 명시 실행이다. read-only REPEATABLE READ transaction에서 같은 질문/기대 근거 집합/자료·투영 fingerprint를 비교한다. job은 strict UTF-8 JSON/중복key·비유한·추가필드 거부/최대256KiB, snapshot1..50/질문1..40/질문1500자, case ID고유·기대 source family1..5(가족당1..10·같은 case 내 중복 없음) 또는 명시 no-match case다. 기대ID는 선언한 같은 workspace corpus에 속해야 한다. 조회 결과가 corpus를 벗어나거나 중복/상위5 한도를 위반하면 실패한다. 성공/실패 로그는 집계/고정 메시지만, 질문·ID·원문·DB URL은 private report에만 둔다. 평가 CLI는 기존600 입력/700 부모·새600원자 출력/no overwrite를 재사용한다. DB/서버/모델·HTTP를 import/startup/공개 GET/로그인에서 호출하지 않는다.
- 평가의 family Recall@5·Hit@1·필수 가족 모두 발견·negative no-match는 검색 지표다. 위치 일치·주장 지지·정답·전체 제품 품질과 같다고 표시하지 않는다. 합성 회귀와 실제 검토한 비공개 자료 평가를 구분하며 기존20문항의 미실행/보류 항목을 새 도구의 합성 통과로 바꾸지 않는다. 결과 없는 문항/보류를 분모에서 조용히 빼지 않는다.
- v2/v3의 schema·지침·prompt budget·agent/workflow 이름·모델 유료 step 이름/정수slot1·기존 ID/기록 version 복구를 그대로 보존한다. 지침 개선은 별도 research-v4/issuedigest_research_v4/issuedigest_research_run_v4로 기록하며 새 queued 요청만v4를 사용한다. v2/v3/v4 등록과 원래 이름·version cohort·단일 worker 잠금·취소/권한·미완료 과금 재호출 금지를 유지한다. SDK 내부 함수/SQL로 checkpoint/version을 바꾸지 않는다.
- v4도 기존 세 category·inference/AI 해석·정확1 SupportReview/claim·고정 automated 식별자·같은 ordered citations/UTC microseconds·300자 rationale·최대5근거/12claims/요약·비교·타임라인+마지막근거를 유지한다. v4 review 식별자는 issuedigest-research-v4/method_version research-v4이며 v3와 섞이지 않는다. 새 Claim 필드·schema/default를 추가하거나 기존 결과에 새 평가를 소급하지 않는다. 공개v1/v2 경계를 v3/v4로 넓히지 않는다.
- v4 지침은 문서에 표현이 있다는 사실과 당사자의 통계·효과·평가·주장·계획/전망의 진실을 구분한다. 기관의 발표 수치는 그 기관에 귀속하고 계획/전망을 실제 성과로 바꾸지 않는다. 같은 대상·기간·단위가 확인되는 수치를 비교하되 검증된 단순 대소 관계를 자료 부족으로 덮지 않고, 목표·현재 실적·전망·확정 결과를 분리한다. 숫자·계산·인과·상충/양측·정확성을 생성/강제하지 않는다. 세 분류는 선택 근거에 대한 AI 평가이며 독립 사실 검증이 아니다.
- 모델은 기존 gpt-5.4-mini Responses/store=False/retry0·단일 요청/60초·24,000총토큰/2,500출력과 static schema/instructions byte 사전 예산을 유지한다. 모델/서비스·지출 상한을 늘리지 않는다. 실제 평가의 공개 원문·합성 신원과 실제 사용자 계정을 분리한다. controller의 실제 provider 검증은 최대3요청으로 제한하며 재시도/실패 숨김 없이 전부 기록한다. 모델 품질을 문자열 keyword 검사만으로 통과시키지 않고 controller가 실제 인용과 주체·기간·수치/귀속을 읽어 판정한다.
- 실제 계정·접속·키·개별 private ID·원문·정확 평가 job/report는 controller만 저장소 밖에서 다룬다. 구현/리뷰 에이전트는 합성 자료와 lease받은 전용 PG만 사용하고 실제 서버/DB/복원본/키/Sites/provider에 접근하지 않는다. subagent를 추가로 만들지 않는다. Git/PR/Sites에는 기능·집계·한계만 기록한다. 사용자 브라우저 탭을 열거나 이동하지 않는다.

## Task 1: 같은 자료·질문으로 재현하는 내부 검색 평가

- [x] packages/storage에 strict private evaluation job/report와 실행 함수를 추가한다. 기존 retrieve_snapshot_ids/question_terms를 호출하고 전략 profile·질문/기대 근거 artifact hash·선언 corpus 및 실제 snapshot/projection fingerprint·모든 case의 rank/정확 family coverage·Hit@1·macro family Recall@5·all-required·no-match 별도 분모를 기록한다. body/기대 근거를 모델로 생성하지 않는다. 기존 검색에 변경 없는 profile 상수만 추가해 baseline을 식별한다.
- [x] CLI를 apps/worker에 추가해 기존 private 파일 가드와 ISSUEDIGEST_DATABASE_URL 검증·expected_database 일치·scope 정확 대조·read-only REPEATABLE READ를 적용한다. private report만 새 파일로 쓰고 stdout은 집계만 출력한다. 평가가 조회·DBOS/예산/세션/투영 쓰기를 하지 않음을 실제 PG로 확인한다. SDK의 raw input을 재검증하고 bounded JSON·잘못된 gold/corpus/missing projection·실패/no-partial-output·중복/순위/분모·DB 오류 비노출을 TDD로 검증한다.
- [x] tests/evaluation/README와 worker/storage README에 실제 명령·job형식·지표 한계·비공개 gold 보관·baseline/candidate 비교 조건을 적는다. 기존20문항은 별도 미실행 상태로 유지한다. 합성 평가 dataset/PG 회귀·Ruff/format(문서 Python fence 포함)/mypy 후 commit/report. 기존 검색/프롬프트/worker/UI/실제 데이터는 바꾸지 않는다.

## Task 2: 한국어 변형·문서 균형을 갖춘 제한 검색

- [x] 주제 원형을 최대8개 보존하고 알려진 조사·혼합 ASCII/숫자+한국어 어미의 제한된 변형을 주제당3개 이하로 만든다. 표현용 단어와 실제 topic을 구분하되 부모 재사용 규칙을 완화하지 않는다. 긴 복합어의 명시 공백 차이를 전체 문자열 실제 일치로 확인하며 폭넓은 유사어·의미·숫자 추정을 하지 않는다.
- [x] 내부 research 검색의 후보가 한 문서의 반복 문단으로 잠식되지 않도록 snapshot별 후보를 균형 있게 가져온다. 원형/변형별 최대200후보·상위20 snapshot/최종5와 canonical projection/hash·정확 위치·workspace 검증을 유지한다. 실제 전체 literal/명시 공백 일치가 확인된 row만 후보로 쓰고 ngram 집합 일치를 정답으로 간주하지 않는다. 원형 직접 일치와 distinct topic coverage를 결정적으로 점수화한다. generic/default fallback·시간 최신성·외부 호출을 추가하지 않는다.
- [x] TDD: mixed AI는/숫자년도·띄어쓰기·원형 보존/고유명사·반복 문단20개+다른 문서·false-positive ngram·raw/변형 중복 점수·동률·8주제/24변형/200후보/20문서/5결과·권한/부모일반질문/새주제/동결근거·잘못된 투영/인용을 검증한다. Task1 도구로 합성 고정 평가의 baseline/candidate를 비교하고 개선/비개선/실패를 모두 보고한다. 기존 원문 문자 검색 API·projection/hash·생성계약은 그대로이며 관련 PG/검색·Ruff/mypy 후 commit/report.

## Task 3: 귀속·목표/실적/전망을 분리하는 새 실행 버전

- [ ] research-v4 지침과 별도 agent/workflow 이름을 추가하고 static instruction/schema byte budget을 다시 계산한다. 기존v2/v3의 실제 지침/schema/prompt bytes와 유료 namespace/step 순서는 그대로다. 중복 구현 대신 기존 build/validation을 제한 profile 공통 함수로 재사용하며 기존 버전의 결과는 동일하게 유지한다.
- [ ] domain·TS/private display의 엄격한 동일 버전 SupportReview 검증에 v4를 추가한다. v3/v4 혼합·잘못된 reviewer/version·누락·다른 인용/시각을 거부한다. 공개는 v1/v2/empty만 허용하며 v3/v4 reviews를 제거해도 거부한다. generic Claim·OpenAPI/default/hash는 바꾸지 않는다. 기존 작은 분류 도움말·원문·로그인·실행/재열람 UI를 그대로 소비한다.
- [ ] worker는 세 버전을 등록해 원래 기록 이름/version을 회복하고 새 요청만v4로 시작한다. frozen v3 worker 완료 모델 checkpoint→새 worker 무과금 재생·새v4 실행과 기존v2 재생, v3/v4 in-provider 중단/불명확 재호출 없음·slot1/단일worker·취소/권한을 실제 PG로 검증한다. 지침/단순 산술 비교·시점/귀속·자료 부족·원문 지시 회귀는 합성 모델로 검증하고 의미 품질을 테스트 고정 출력만으로 보장하지 않는다.
- [ ] 전체 관련 JS/TS/UI·Python/PG·Ruff/문서format·mypy·build/contracts를 확인하고 D022·활성 계획/작업·실행/평가 안내에 실제 범위/남은 품질을 기록한 뒤 commit/report. 새 UI 메뉴·도구/요금·실제 서버/Sites를 변경하지 않는다.

## Controller acceptance

controller가 기존614 CI 성공/깨끗한 linked worktree를 baseline으로 고정한다. Task1 이후, Task2 이전에 동일한 private job과 기존13자료의 격리 복원본에서 baseline을 실행하고 변경 후 같은 fingerprint/질문으로 비교한다. 검토한 공개 텍스트의 실제 질문·골드와 미발견 사례의 분모를 명시하며 이전20문항 실행 완료로 표시하지 않는다. 전체 PG/JS 검사·작업별/전체 독립 검토 후 최대3회 실제 모델 평가와 native320/390/1440/두 테마·귀속 도움말·정확원문/재열람을 확인한다. 결과가 불충분하면 실패/한계를 그대로 기록하고 승인 범위를 무제한 호출로 늘리지 않는다. 활성 기존 실행을 완료한 뒤 새 웹/API/worker를 개인 개발 환경에 반영하며 자료/계정/세션/공개v1·기존결과 보존, 전후 백업/별도 복원·정상HTTPS/권한·source 일치를 확인한다. feature Draft PR·Sites를 갱신하되 main/운영·사용자 탭은 변경하지 않는다. 자신이 만든 검증 자원만 정리하고 기록/PR용 worktree는 보존한다.
