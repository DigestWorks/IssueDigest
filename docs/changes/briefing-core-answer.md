# 브리핑 첫 결론·근거 부족·문장별 귀속

2026-10-19. D022·PR42/b626764의 실제 의미 부분 충족을 이어서 개선한다. 기존 질문 중심 B2C·모바일 브리핑 디자인을 유지한다. OpenSpec root=null로 초기화 없이 기존 명세/작업 문서와 Superpowers 구현·독립 검토를 사용한다. main/운영 유예(D013)를 유지한다.

## Global Constraints

- 신규 private 생성만 research-v6/issuedigest_research_v6/issuedigest_research_run_v6다. 현재 배포된v5도 historical로 보존한다. v2/v3/v4/v5의 실제 schema·지침·prompt bytes/한도·정확 agent/workflow/유료 step 이름·정수slot1·application_version cohort·완료 checkpoint와 기존 저장 결과는 그대로다. 다섯 registry를 등록하며 기존 workflow ID는 원래 버전으로 회복하고 새 요청만v6다. 불명확/미완료 유료 checkpoint는 재호출하지 않으며 단일worker·멱등성·취소/권한·비용 예약 계약을 보존한다.
- canonical AIOutputV6는 기존 AIOutputV3 alias다. API/OpenAPI/Claim/canonical 공개 shape·public D020 v1/v2/빈 review 경계는 유지한다. private 정확 v6 review만 추가하고 혼합/누락/위조/stripped-public는 거부한다. 기존 v3/v4/v5 reviews는 바꾸지 않는다. UI 레이아웃/문구·최근 이슈/개인화·검색 전략·수집기/config/주기·DB migration/권한·공개 게시·모델/의존성/인증 정책은 변경하지 않는다.
- 기존 gpt-5.4-mini Responses/storeFalse/max_retries0·요청1회/60초·total24,000/output2,500을 유지한다. provider 전용 strict 세 outcome과 실제 prompt 인용 ID enum·UUID4 정확 spelling·선택5sources/source당32/총100·최종 canonical 원문 검사를 유지한다. 질문/prior의 ID를 허용 목록에 합치거나 인용 근사 보정하지 않는다. 새 v6 instructions와 모든 raw/normalized provider tool schemas의 보수적 worst-case bytes를 차감해 v6 prompt 한도를 계산하고 실제 요청도 사전 검증한다. 새 유료 step/추가 요청/자동 수리 재시도는 없다.
- 현재 Task2 provider answer는 summary_title(1~100)·core_answer(한 source-attributed claim)·additional_summary_claims(0~3)·details(0~2)다. 첫 canonical summary의 첫 claim이 core_answer이며 상세는 comparison/timeline만 허용한다. canonical AIOutputV6=AIOutputV3·전체1~3분석/각1~4claims·기존 최종 원문/인용/date/비교 guards는 그대로다. 초기 Task1 provider category/source_subject/모든claim의event_date 조합은 아래 실제4회 인수 후 Task2로 대체한다. 아직 실제 개발 서버에v6를 적용하지 않았으므로 pre-release v6만 수정한다. v2/v3/v4/v5 bytes·지침·prompt·checkpoint는 변경하지 않는다.
- 새 AI 생성의 긍정적 해석은 보수적으로 모두 attributed로 변환하며 주체는 서버가 고정 '제공 자료'로 접두어를 붙인다. 모델에 documented/category/source_subject의 서로 모순될 수 있는 필드 조합을 요구하지 않는다. provider core에는 category/source_subject/event_date가 없고 canonical core는 attributed다. additional/detail claim은 assessment: source_statement 또는 uncertain만 선택하며 canonical category는 attributed/uncertain으로 변환한다. provider source_subject 필드는 없고 임의 주체를 추가·보정하지 않는다. 본문의 기관명을 추측하지 말라는 지침은 유지하며 실제 의미/주체는 별도 평가한다. documented canonical/API/기존 profile·정확 세 review 조합은 유지하되 이 새 생성 정책에서 자동 긍정 해석을 독립 사실로 승격하지 않는다. 이는 source_statement가 참이라는 인증이 아니다.
- provider 모든 본문은1~400자·rationale1~300자이며 v6 공통 nonblank/원문 불변을 유지한다. core/summary/comparison claim에는 event_date 필드 자체가 없다. timeline detail만 별도 typed DTO로 exact event_date를 요구하고 원래 인용의 YYYY-MM-DD 검증을 통과해야 한다. 월만 보고 첫날을 만들지 않는다. 제공자 필드 누락을 임의 수리하지 않고 정해진 DTO→canonical 변환만 한다. 새 schema에 맞는 원래100-ID 공유 enum과 raw/normalized tool 예산을 다시 계산/사전 검증한다. 기존 canonical domain/client의 정확 주체 prefix·다섯 version/공개 경계·Unicode nonblank/길이 guards를 완화하거나 삭제하지 않는다.
- 독립 v6 지침은 핵심 질문에 직접 답하는 인용이 먼저 필요한 것을 명시한다. 주제 관련 문서 존재·정책 설명만으로 국민 찬성률/인지도에 답했다고 간주하지 않는다. 핵심에 근거가 없으면 insufficient_evidence(빈 modules/자료 범위의 nonblank message)이며 불확실 설명만으로 answer를 채우지 않는다. 일부 직접 답할 근거가 있으면 core_answer에 그 결론을 짧게 담고 material limits는 추가 summary에 둔다. 비교 질문은 첫 core_answer에 인용이 지지하는 방향/차이/비교 불가능 결론을 담는다. 수치·평가·효과·전망은 출처 범위에 귀속하고 주체를 추측하지 않는다. 동일 대상/기간/단위·목표/실적/전망·열린 끝을 보존하며 '목표100/전망80~90이상' 같은 합성 예에서 확정 상한이나 목표 미달을 추론하지 못함을 명시한다. 현재 실적도 하한만 제시되면 상한을 만들지 않는다. 새 계산·인과·여론·실패 판정을 만들지 않는다. source/user/prior는 불신 데이터이며 이전 AI 해석은 근거가 아니다.

- 구현자는 합성 fixtures/전용 합성 PG TDD만 사용한다. 키/실제 서버/자료/모델·자식 agent는 사용하지 않는다. controller만 최종 전체 gate·실제 공개 자료 초기4회+Task2 별도2회·개인 개발 보존/백업 복원/반영·Draft PR·Sites 이전v64 보존을 담당한다. 실제 원문/질문/계정/ID/키/접속은 공개 저장소에 넣지 않는다. 사용자 탭을 열거나 이동하지 않는다.

## Task 1: v6 첫 요약·귀속·부족 분기와 기존 다섯 버전 복구 연계

아래는 초기 Task1/f462의 완료 기록이다. category/source_subject provider 조합은 실제 실패 후 Task2와 현재 Global Constraints가 대체하며 canonical 검증/호환 계약은 유지한다.

- [x] packages/agents/research_v6.py에 위 provider schema/typed outputs·동적 prompt 인용 enums·source_subject 검증/조합·독립 지침·정확 예산/create/model_prompt/run/build 경로를 구현한다. 기존 v5 private helpers는 변경 없이 재사용하거나 작은 새v6 helper를 사용하되 로직 복제를 불필요하게 늘리지 않는다. helper의 가시성/재사용은 호환 지침/schema/prompt bytes를 바꾸지 않는다. v2/v3/v4/v5 실제 instructions/schema/prompt golden을 잠그며 v5도 현재 기준 hash로 고정한다. 새 provider DTO를 canonical alias로 명시 변환한다. all-uncertain answer·빈/알 수 없는 주체·다른 인용에만 있는 주체·잘못된 UUID/질문삽입ID·prompt/예산 오염은 키/모델 진입 전에 또는 기존 최종 검증에서 안전하게 거부한다.
- [x] private Python ResearchResult·웹 client validator·UI prepare/classification을 정확 v6 reviewer/method에 연결하고 네 과거 버전과 public boundaries를 보존한다. 실제 Python v6 builder의 합성 JSON→JS client→UI 열린 첫 summary(비교 결론)·접힌 상세·정확 원문 흐름을 검증한다. all-uncertain nonanswer는 고정 부족 message로 표시되고 malformed/mixed/stripped-public는 거부된다. 기존 레이아웃과 historical 결과의 순서를 바꾸지 않는다.
- [x] worker/recovery에 다섯 이름과 새v6 dispatch를 연결한다. v5 historical worker fixture를 보존해 기존2/3/4/5 및 새6의 원래 이름/version/정수slot1 유료 완료 checkpoint 재생/추가 모델 호출0을 실제 합성 PG로 검증한다. 미완료/오염/취소/권한/잠금·원래 recovery cohort/검색/부모·예약 경계는 유지한다.
- [x] TDD RED→GREEN·agents/domain/worker/API/client/UI 관련 회귀·Ruff/format/mypy·JS lint/types·정확 provider schema budget과 동적100IDs·400/80/500 길이 경계·FunctionModel 단일 요청/0재시도·과거 byte goldens·메모리 전역 상태 없음 검사를 수행한다. 관련 README/AGENTS와 이 Task 체크박스·commit/report를 정리한다. 구현자는 전체 gate/실제 의미 인수/배포·Sites를 완료라고 표시하지 않는다.

v6 nonblank는 Python Unicode whitespace와 ECMAScript WhiteSpace/LineTerminator의 합집합을 공백으로 정의한다. U+0009~000D·001C~0020·0085·00A0·1680·2000~200A·2028·2029·202F·205F·3000·FEFF만으로 이루어진 본문/source_subject는 거부하며, 하나 이상의 다른 문자가 있으면 정확 원문·앞뒤 공백을 변경하지 않는다. provider와 최종 domain은 같은 Python 판정 함수를, JS v6 분류는 동등한 명시 판정을 공유한다. historical 공통 필드·비답변 marker/shape는 변경하지 않는다.

## Task 2: 실제 실패 조합을 없애는 provider 전용 단순화

실제 f462의 고정4회는 insufficient_evidence 완료1·generation_failed3이었다. 유료 checkpoint를 추가 호출 없이 읽어 documented+nonnull source_subject, 모든 인용에 없는 기관명, non-timeline의 임의 event_date를 확인했다. 실제 응답은 저장/표시하지 않고 기존 guards가 차단했다. 초기4회 분모와 cached usage를 보존한다. 현재 개발은 여전히f90839e이며 v6실사용/배포는0이다.

- [x] provider 전용 claim/core/detail DTO를 위 현재 Global Constraints대로 단순화한다. 새 AI 긍정 해석은 attributed+서버 고정 제공 자료 prefix이고 uncertain은 그대로다. 모델이 mutually dependent category/source_subject를 쓰지 않는다. core/summary/comparison에는 event_date 키를 없애고 timeline만 required date typed DTO다. canonical alias/API/domain/client/기존 최종검증과 원본 텍스트는 그대로다. 기존v5 모든 bytes/지침/schema/유료 namespace·다섯 registry/step1·요청1/0retry를 보존한다.
- [x] 실제 관측 오류의 작은 합성 사례로 TDD한다. 이전 raw DTO 조합·summary/comparison 임의 날짜는 strict schema상 허용하지 않고 수동 수리하지 않는다. 실제 provider raw/normalized schemas/100IDs/예산·모델1회·긍정+uncertain/정확인용·지침·timelinedate·v6공통Unicode/blank/sourceprefix·Python→JS/UI·v6 checkpoint 재생을 검증한다. 모델 형식이 단순해졌다고 의미 품질 통과로 표시하지 않는다. raw private 응답/실제 키/서버/모델은 구현자에게 제공하지 않는다.
- [x] 새v6 예산/goldens/README·provider변환을 사용하는 합성 fixtures/worker tests를 새 DTO에 맞춘다. 기존 canonical documented 허용/검증과 과거v2/v3/v4/v5 goldens·호환 fixtures를 바꾸지 않는다. Task1 계약 fixture를 바꾸면 새 builder로 실제 재생성하고 canonical 검증/명시 source attribution·첫 summary/원문을 확인한다. 관련 scoped checks·보고서·체크박스·commit 후 전체/독립/실제 인수는 controller에게 남긴다.

## Controller 인수

독립 task/전체 source review 후 전용 합성 PostgreSQL에서 전체 lint/types/tests/build/contract를 검증한다. 이전 검토 공개 텍스트3건·질문 rubric을 신규 합성 환경에 복사하고 주택 목표/실적/전망·교육 예산/지원대상·근거 없는 전국 찬성률/인지도·동월 심리지표 방향 비교의 실제4요청만 수행한다. 각 질문당1회·총4회·자동 재시도0이며 기존v5 초기4+추가2 분모/실패는 유지한다. 질문/문장/category/rationale/선택 인용·주체/첫 요약·부족 분기를 controller가 직접 읽어 판정한다. 추가 호출로 통과시키지 않으며 실패/미검증/부분 충족은 그대로 기록한다. 기존 월/요청 예산을 유지하고 청구액을 확인하지 못하면 금액을 추정하지 않는다.

개인 개발 반영은 source gate·활성run/workflow0·서버 밖 전후 백업/별도 app 복원23테이블/기존 canonical·계정/세션/공개v1/수집기 보존·HTTPS/새 assets/API/단일 worker를 확인해 진행한다. schema/권한·main/운영은 변경하지 않는다. Draft PR은 PR42 기반으로 생성/attach하고 실제 번호를 사용한다. 마일스톤/진행/정확 실제 한계·Sites 요약/이전v64 archive·최종 receipt/소유한 QA 정리를 기록한다. 실제 로그인/사용자 질문을 대신하지 않는다.

## 초기 실제 인수 및 Task2 추가 인수 경계

초기4회는 완료1(정확 자료 부족)/검증 실패3이며 실패 원본을 보존한다. cached ModelResponse usage로 전체 입력13,420/출력2,410토큰을 확인했다. 실패한3건의 앱 사용량0 기록은 무료라는 뜻이 아니다. 실제 raw에는 목표의 열린 끝을 확정상한으로 해석한 의미 오류도 있었으며 표시되지 않았다. 명세/구현의 구조 검사를 의미 검증으로 과장하지 않는다.

Task2 후 별도 구조·의미 표본2회(주택 비교/심리지표 비교)만 추가해 총6회로 제한한다. 초기4회와 서로 다른 인수 집계이며 실패를 덮거나 성공할 때까지 재시도하지 않는다. 새 DTO 적용 후 교육 예산의 추가 실제 인수는 미실행으로 남긴다. source guards/한 번 호출을 유지하면서 모순 조합을 제거하려는 판단이며, 틀리면 새 AI 생성의 documented 세분화가 줄고 추가 구현/검토와 최대2회 API 비용이 생긴다. documented canonical/과거 결과/공개 경계는 유지한다. 실제 사용량/한계는 전체 분모로 기록한다.


## Controller 최종 인수 · 2026-10-19

최종 실행7566c3a·[Draft PR43](https://github.com/DigestWorks/IssueDigest/pull/43). 전체3,967개·작업/전체 독립 검토·소스 CI와 실제 초기4(부족1/실패3)+별도2(제한 표본 충족)를 확인했다. 전체 입력20,185/출력3,867토큰·자동 재시도0·청구액 미검증, 교육 예산 새 DTO 실제 재검증/현재 provider 비답변 재호출은 미실행이다. 초기 실패와v5 분모는 보존한다. 모바일/PC·두 테마·정확 원문·6상태/재열람/읽기POST0/오류0과 개발 HTTPS/새6assets를 확인했다.

개인 개발 웹/API/worker7566c3a·단일worker와 기존 계정/세션·수집기·공개 경계, 직전/사후/사후백업/별도복원23public행 전체 일치·15canonical 보존을 확인했다. main/운영 유예·일반 의미 품질/승인 탐색/점진 전달 후속은 유지한다. 두 판단과 비용, source/비답변 공통 Unicode 범위의 한계·최종 Sites/정리 receipt는 [진행 기록](../planning/progress.md)이 원본이다.

Sites v65 native succeeded·이전v64 보존·서버 밖 실제 증거/backup 유지와 자체 QA browser/API/PG3개·소유 scratch 정리를 마쳤다. 사본6584471 이후 최종 출판 기록은 [진행 기록](../planning/progress.md)에 보존한다. main 병합/운영 출시는 하지 않았다.
