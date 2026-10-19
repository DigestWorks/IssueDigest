# 질문·근거 후보의 관련성 선택

## Spec · 목적과 범위

기록된 계획 검색 평가에서 필수 자료 발견이0.5→1.0으로 개선됐지만 명시 무관 자료도1→2로 늘었다. 임의 키워드 임계값으로 자료를 버리지 않고 질문·실제 제공 인용을 함께 읽는 제한된 선택기를 구현한다. 선택기의 누락·비용을 먼저 검증하고 이후 내구 실행기에 연결한다. 이번 산출물은 재사용 가능한 agents SDK와 실제 고정3질문 비교 인수이며 현재 앱/워크플로에 유료 단계를 자동 추가하지 않는다. 사용자 화면에 임시 체크포인트를 만들지 않는다.

## Global Constraints

- 기준a76a37f04b7e85134ff449a255544437bc9c6bc2·기존 전체4,375개/CI39211130090(검증4a82706)를 baseline으로 재사용하고 반복 baseline은 실행하지 않는다. 현재 앱f839ae0/v8·기존v2~v8/planner7 provider bytes/지침/한도·workflow/검색정책/유료slot·저장 결과/API/OpenAPI/권한·공개·DBschema·수집기·브리핑 UI는 그대로다. 새 schema/model version을 기존 결과에 덮어쓰지 않는다. main/운영 유예(D013)·사용자 탭 유지·실제 사용자 세션 비대행이다.
- `packages/agents/src/issuedigest_agents/relevance_selection.py`에 `create_selector(model=None)`, `selection_prompt(question,sources)`, `run_selector(selector,prompt)`를 추가한다. create_selector는 frozen lazy handle을 반환하며 실제 Agent/기본 OpenAI model·key 로딩은 run_selector의 strict prompt/coverage/envelope preflight가 통과한 뒤에만 한다. 주입된 FunctionModel도 같은 실행 경로를 사용한다. sources는 기존 `(UUID, EvidenceBundle, SourcePresentation)` tuple의1..5개이며 strict UUID4·고유 snapshot·단일 workspace·각 presentation/bundle/snapshot provenance를 검증한다. question은 기존 prompt의 strict 비공백1..1500자 계약이다. 선택기는 권한을 부여하지 않으며 caller가 현재 권한의 자료를 공급해야 한다. 원래 question을 보존하고 기존 `_model_prompt`의 bounded whole-quote 구성·최대source5/인용100·본문12,000자/자료별32를 재사용한다. 새 prompt builder는 같은 bounded JSON `_PromptV5`로 검증한다. metadata/제목은 안내일 뿐 관련성을 증명하지 않고 원문·질문·context는 비신뢰 데이터다. 부모 AI 맥락을 선택기 입력으로 넣지 않는다. 모든 입력 snapshot이 prompt에 정확1번/비어 있지 않은 실제 인용과 함께 들어가야 한다. 예산 때문에 source가 누락되면 그 source를 무관/제외로 간주하지 않고 provider 호출 전에 전체 거부한다. 개별 인용의 추가 절삭/의미 변경·본문 밖의 구문 인용·사용자 질문의 부분 절삭을 하지 않는다.
- provider tool `classify_relevance`의 strict actual Pydantic DTO를 prompt별로 만든다. `decisions` 배열의 각 row는 해당 prompt snapshot UUID 문자열 Literal enum의 `snapshot_id`, `decision: retain|exclude|uncertain`만 가진다. 정확히 모든 후보1회, unknown/duplicate/missing/extra field·잘못된 enum/빈값을 거부한다. row 순서는 자유지만 검증된 결과를 서버가 원래 후보 순서로 투영한다(의미 수정/잘못된 응답 수리 아님). 새 불변 결과모델 `RelevanceSelection`은 profile `evidence-relevance-v1`, 정확 UTF-8 prompt SHA256·질문 UTF-8 SHA256·원래 후보 IDs/전체결정·selected_snapshot_ids·제외 IDs·input/output tokens를 보존한다. selected는 retain+uncertain의 원래 후보 순서이며 exclude만 제외한다. unknown을 제외/사실 부정/답변 근거 부족과 같게 보지 않는다. 결과에 AI 자유서술·사실 판정·HTML·점수나 자동 SupportReview를 추가하지 않는다.
- 지침은 질문의 주제/대상/시기·다중 비교 항목 중 일부를 설명하는 자료도 보존하고, 직접 답변 통계가 없다는 이유만으로 주제 관련 자료를 배제하지 않으며, 명확히 다른 주제는 exclude·판단 부족/짧은 제공 인용은 uncertain으로 두도록 한다. 정치/정책 입장의 찬반·문서의 동의 여부·진실/거짓·권위나 최신성으로 관련성을 대체하지 않는다. 원문/제목/질문의 주입 지시·새 주제 추가를 따르지 않는다. 지침 존재·schema 통과를 의미 품질/중립성 인증으로 보지 않는다.
- 새 selector는 gpt-5.4-mini·Responses store=False·AsyncOpenAI max_retries0·PydanticAI retries0·tool request_limit1·최대 입력+출력12,000/출력500/timeout15초다. 원래 모델/지침을 수정하거나 hidden planner/final call·검색/외부도구/DBOS 호출을 넣지 않는다. 기존 raw ModelResponse+aggregate exact-int/nonbool/nonnegative·한도/합산 일치 검증을 재사용하고 불확실 사용량을0/무료로 돌리지 않는다. 최악5UUID의 실제 raw/normalized schema bytes와 instruction bytes·2,048framing·출력500을 모두 뺀 prompt byte한도를 계산하고 실제 request envelope도 직전 검사한다. 경계 안의 정확 질문/인용만 허용하며 초과/불완전 prompt·결정 오류·network/usage오류는 고정 비민감 오류로 실패, 자동 retry/출력 수리0이다. import/실패 preflight/FunctionModel 사용은 키 로딩·provider 호출을 만들지 않는다. 사용자가 승인한 실제 키는 controller만 사용한다.
- 구현자는 합성 EvidenceBundle·FunctionModel만 사용한다. 실제 키/원문/서버/외부network·자식agent/container/푸시/배포 금지이며 source/test/관련 README/Task1 체크박스만 commit한다. controller가 단일 wholegate·작업/전체 독립 검토와 실제 고정3 selector요청을 수행한다. 이전v8 고정3질문·기검토 공개원문3·이전 planned 후보순서1/3/3·동일 human expected/irrelevant/unjudged를 보존한다. 새 실제 provider 요청 최대3(질문당1)/추가 성공재시도0, 각 호출 전 private 시도 receipt를 만들고 실패도 분모에 남긴다. 모든 선택/제외/unknown을 정확 제공 인용·질문과 대조해 판정하고 기존 미판정3을 답변 부족만으로 무관 gold로 변경하지 않는다. 기존 v8/v7/v6/v5 모델 평가 분모에 새 selector3건을 합치지 않는다. 사용량/지연/실패/원래 prompt내용 hash와 판단 한계를 기록하며 실제 청구액은 확인 전 확정하지 않는다. 기존12,000 selector한도는 향후 앱 전체24,000/출력2,500 예산·단계복구 연결의 완료를 뜻하지 않으며 worker 연결은 별도 후속이다. 새 Draft PR46 기반·마일스톤/Sitesv68archive·공개 요약/문서 사본/native 게시·소유QA 정리를 남긴다. 실제 개발앱/서버/DB/로그인/수집기 변경·배포/재시작은 이번에 하지 않는다.

## Task 1: 인용에 묶인 bounded 관련성 선택기 SDK·합성 TDD

- [x] 위 `relevance_selection.py` SDK·실제 strict tool/result DTO·정확 후보 coverage와 원래 순서 선택/불확실 보존·원문 prompt/정확 hash·request envelope/usage/비민감 오류를 구현한다. 기존 agent helper/body/DTO/지침은 변경하지 않고 새 모델 기본 생성 설정만 필요한 좁은 범위로 구성한다(기존 모델 설정 코드의 짧은 구성 반복은 허용하되 기존 긴 생성/검색/검증 로직 복제는 금지).
- [x] 실제 FunctionModel 경로를 사용하는 합성 TDD로 retain/exclude/uncertain 혼합·모두exclude·모두uncertain·다중주제 일부보존 fixture·source순서 projection·잘못된 후보/UUID4/교차공간/provenance·질문/인용 누락·예산 byte경계/UTF-8·unknown/duplicate/missing/extra DTO·raw/aggregate usage bool/음수/불일치/overflow·단일call/retry0·key없는 import/preflight·주입 데이터/정확인용 보존을 검증한다. 실제 모델 의미 품질을 합성 label 문자열 검사로 인증하지 않는다. 원래 v7/v8 지침/schema/예산·app/client/공개는 byte동일로 유지한다.
- [x] agents README에 계약·예산/부작용·미연결 경계·한계를 기록하고, 관련 agents/usage 회귀·Ruff/format/mypy/diff를 통과한다. 위 Task1만 완료 표시하고 명시파일 source commit/report를 남긴다. scratch보고서는 ignored로 두며 강제추적하지 않는다. controller의 실제3/전체gate/검토/PR/Sites/서버 적용을 완료로 표시하지 않는다.

## Controller 인수

세 고정 질문에 대해 같은 corpus·이전 planned source IDs를 사용하고 실제3 selector요청을 한 번씩만 수행한다. selection별 relevant 보존·명시irrelevant 제외·원래unjudged의 AI결정을 따로 기록하고 원문을 직접 대조한다. 모든 실패/미판정을 유지하며 선택 개선을 실제 답변 품질 개선으로 확대하지 않는다. root OpenSpec=null이므로 새 init을 하지 않고 단일 변경명세/SDD를 사용한다. 실제 앱 연결·전역 예산/내구 단계는 다음 독립 구현이다.


## Controller 실제 인수 결과 · 2026-10-19

질문·제공 인용을 함께 읽는 재사용 선택기 `evidence-relevance-v1`을 agents SDK로 구현했다. 정확한 모든 후보에 retain/exclude/uncertain을1회씩 받고, retain+uncertain은 원래 순서로 보존하며 exclude만 제외한다. 실제 후보 UUID enum/전체 coverage·원문 전체 인용·question/prompt UTF-8 hash·불변 결정/사용량과 raw/합산 검증을 적용한다. strict preflight 전에는 기본 key/model/Agent를 초기화하지 않는 lazy handle이다. 제목/metadata만으로 관련성을 증명하거나 관련성을 진실·독립 사실 검증·정치적 동의로 대신하지 않는다.

기존 고정3질문·같은 기검토 공식 원문3건·이전 계획후 후보1/3/3으로 실제 selector3요청을 한 번씩 실행했다. 모두 완료했고 retry0이다. 동일 주택 자료를 필수로 지정한 positive2문항에서 해당 자료를 모두 보존했다. 둘째는 명시 무관한 경제·교육 후보2개를 모두 제외해2→0이 됐다. 셋째는 주제 관련 주택 자료를 retain하고 다른2개를 exclude했다. 이 문항의 기존 human relevance 미판정3개는 그대로이며 선택 후1개가 남았다. 전국 찬성률/인지도 직접 근거가 없다는 것과 주제 자체의 무관함을 같게 보지 않았고 미판정 제외에 정답/precision 가점을 주지 않았다.

controller가 모든7개 판단과 제공된 정확 인용15종(문항별4/15/15)을 직접 대조했다. 현재 판정은 이번 목표의 좁은 소표본 충족이다. 전부 같은 주택 주제/정부 자료이며 다양한 이슈·상반 입장/다중주제·공격적 주입에 대한 실제 모델 견고성은 검증하지 않았다. 실제 uncertain 응답은0으로 그 보존 분기는 합성 검증만 했다. 선택기는 제한된 제공 인용을 읽으며 원문 전체의 의미나 답변 품질/중립성·전반 검색 정확도를 인증하지 않는다.

실제 입력5,087/출력282토큰·지연2.62/3.32/1.61초이며3응답의 알려진 사용량을 확인했다. 청구 금액은 미검증이다. 실제 app workflow/실제 사용자 세션 대행/개발 서버·DB 변경은0이다. 이3 selector요청은 기존v8의3앱/6요청(의미 부분1/목표 소표본 충족1/부족1), v7 3/6, v6 초기4+별도2, v5 초기4+별도2의 분모와 별개이며 기록 계획 재현의 추가 모델0과도 구분한다. 실제 질문/원문·ID·raw응답/입력prompt·시도 receipt는 private에만 보존한다.

SDK 단독 상한은 요청1회·입력+출력12,000/출력500/15초다. 실제 instructions1,019+worst tool raw842/normalized789 중 큰 값의 static1,861·framing2,048·출력500을 뺀 prompt7,591바이트와 실제 envelope를 사전 검사한다. 최대5후보/100인용은 상한이며 모든 원문 조합의 동시 적재 보장이 아니다. 후보가 prompt에서 빠지면 모델 호출 전에 거부한다. 기존 앱 전체24,000/출력2,500·월 예약·내구 checkpoint/취소·권한/원문 재검증과 연결한 것은 아니다. 앱은 f839ae0/v8·기존 provider/검색/공개/UI/DB/수집기를 유지하며 재시작·배포하지 않았다. 다음은 실제 사용량을 합산해 예약/실패/불명확 호출 재요청 금지·모든 과거 workflow 회복을 보존하는 실행기 연결이다. 기존 D022의 input capacity 판단/비용·남은 수치 표현·실제 날짜 양성 미검증도 그대로다. main/운영은 D013에 따라 유예한다.

전체 source 검토/gate·PR/Sites/QA 정리의 최종 receipt는 [진행 기록](../planning/progress.md)에 누적한다.
