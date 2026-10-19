# 서버가 확정한 원문 위치의 수치 근거 선택

2026-10-19. PR51/e12f68d 후속 M3. 사용자가 서버 확정 위치 참조의 후속 개발을 승인했다. OpenSpec root=null: init 없이 이 단일 Spec/Task/제약으로 구현한다. 이전 v2의 고정 실제2회 모두 거부·v1 부분1/거부1·앱4/12·개발ab6654e/v9·운영 유예는 보존한다.

## Spec

모델이 exact text/occurrence를 출력하던 방식 대신 서버가 원래 순서의 전체 quote를 Unicode code point 단위로 나눈다. 모든 글자(공백/결합문자/astral/control 포함)에1부터 전역 연속 정수 reference ID를 매기고 원문과 함께 제공한다. 모델은 두 reference ID로만 span을 선택한다. 서버가 같은 인용 안의 연속 substring/offset을 확정하며 모델은 원문·UUID·위치를 다시 쓰거나 occurrence를 계산하지 않는다. 정수1..N이 실제 전체 reference 집합과 같으므로 provider schema의 strict integer 최소1/최대현재N이 현재 IDs를 정확히 제한한다. Source12000 codepoints 제약을 재사용하고 별도 작은 글자 수 cap을 만들지 않되 실제 전체 JSON/schema/UTF8 예산을 초과하면 호출 전에 거부한다.

상태는 observed/planned/forecast/unknown으로 구분한다. forecast는 조건의 유무와 별개이며 explicit 조건은 condition에 따로 연결한다. known 상태는 필수 근거 reference, unknown은 nullable 근거를 받는다. 단위는 명시 측정 단위의 근거만 고르고 조사/어미를 단위로 쓰지 않으며 부재는 null이다. 수치의 하한·범위/열린 끝·하위 항목/증감·대상/시점을 보존하도록 요청하되 구조 검사는 숫자/상태/단위/관계 의미나 완전 추출을 보장하지 않는다. 모두 unreviewed다.

새 numeric-evidence-v3만 추가한다. 이번 범위는 독립 SDK/고정 실제2의 원문 전 field 검토이며 DBOS·질문별 브리핑/전역 예산/공개·UI·수집/실제 앱 배포는 바꾸지 않는다. 과거 결과의 실패를 자동 수정하거나 새 후보로 대체하지 않는다.

## Global Constraints

- 기준e12f68de04f8045ea53863932e1077da0ab946ac, feat/numeric-evidence-references, PR51 기반 Draft. 현재 linked worktree 재사용·baseline5,124/source CI39239596381 재사용·baseline 전체 반복 없음. 새 packages/agents/src/issuedigest_agents/numeric_evidence_refs.py/새 packages/agents/tests/test_numeric_evidence_refs.py/agents README와 관련 계획 문서만 바꾼다. 기존 source/tests/AGENTS·v1/v2·과거 v2~v10/selector/worker/provider bytes·API/DB/공개/UI/의존성/lockfile/권한/수집기를 동결한다. 서버 접속/개발 앱 변경/main 병합·운영 배포 없음.
- Source는 기존 tuple(UUID4 snapshot,EvidenceBundle,SourcePresentation) exact type이며 v1 canonical source/unchecked-extra 방어·sid/workspace·원래 순서 whole quote1..20/합계≤12,000 codepoints를 재사용한다. metadata/제목은 근거로 쓰지 않고 원문을 자르거나 대소문자/NFC/공백/숫자/단위 정규화·계산·모호한 자동 수리를 하지 않는다. Source의 현재 접근 권한은 향후 호출자 책임이며 hash는 인증/서명/권한/진실/인간 검토가 아니다.
- 입력 reference catalog는 인용 순서와 각 인용의 Python code-point 순서로 모든 문자를 정확1회 포함한다. ID는1..N 연속 strict int, N≤12,000. 인용별 character rows는 [id, exact_one_codepoint_character]이고 citation_id는 서버 원문 provenance로만 연결한다. prompt에는 원래 whole quotes와 이 표를 함께 포함하며 profile numeric-evidence-v3로 고정한다. 빈 quote/전체 공백은 기존 방어로 거부하고 내부 공백/control/결합/astral 문자는 생략하지 않는다. reference ID는 이 Source/prompt에만 의미가 있다.
- provider ReferenceSpan은 start_ref/end_ref(양 끝 포함, exact nonbool int) 두 필드뿐이다. actual schema는 두 필드의 최소1/최대현재N을 모두 명시하고 추가 text/occurrence/offset/citation UUID를 받지 않는다. 기본 DTO는1..12000을 제한하고 실제 resolver는 현재 catalog에서도 재검증한다. 없는/역순/다른 인용 양끝·공백만/1000codepoints 초과 span은 전체 거부한다. 서버가 citation_id/text/start/end(반열린 Unicode code-point 구간)/start_ref/end_ref를 재계산해 strict frozen ResolvedReferenceSpan으로 저장한다. 모델 숫자 위치를 믿거나 근처로 이동/합성/보정하지 않는다.
- fact0..12는 local_id=f1..f12/value 필수 ReferenceSpan, subject/unit/period/qualifier/condition nullable ReferenceSpan, status=known {kind:observed|planned|forecast,text:필수ReferenceSpan} 또는 unknown {kind:unknown,text:nullableReferenceSpan}의 nested strict union이다. 모든 span은 value와 같은 인용에 있어야 한다. 모델은 context/citation_id를 출력하지 않으며 report의 citation_id/context는 value에서 서버가 whole quote reference로 정한다. 중복 local_id/동일 물리 value 구간·extra/unchecked 우회는 전체 거부한다. 지침은 실질 수치(작은 하위 항목·증감 포함)를 후보화하되 부수적인 날짜/식별자 숫자는 측정값으로 만들지 않는다. 조건 있는 전망과 조건 없는 전망 모두 forecast이며 명시 조건만 별도 condition에 보존한다. grammatical particles/endings는 측정 단위가 아니며 원문 단위가 없으면 unit=null이다. 해당 의미 규칙을 regex로 인증하지 않는다.
- relation0..16은 kind(included_in|parallel|unknown), from_id/to_id, statement/cue ReferenceSpan이다. 서로 다른 실제 endpoint 두 fact의 nonnull subject·value와 cue가 연속 statement의 물리 span 안에 모두 있어야 하고 모든 span은 같은 citation이어야 한다. citation_id는 statement에서 서버가 정한다. 한 unordered pair는 모든 종류/방향에 걸쳐 하나, included_in은 child→parent·독립3+cycle 거부다. 시점이 다른 관측/전망 수치를 포함 관계로 만들거나 단순 근접/단위/산술로 관계를 추론하지 말도록 지시한다. 명시 주체/직접 관계 근거가 없으면 관계를 생략한다. facts0이면 relations0. 연속 원문/주체 포함·cycle 부재는 cue의 실제 지시 대상/관계 의미 인증이 아니다.
- NumericEvidenceProposalV3는 strict/frozen/extra-forbid profile numeric-evidence-v3/status unreviewed, snapshot/workspace·서버 prompt/source SHA256·원래 전체 quote provenance·resolved fact/관계·KnownUsage다. fact kind는 위 v3 상태 taxonomy, kind/status_text는 서버가 flatten하고 context는 whole quote reference다. validate_numeric_proposal_v3는 현재 Source/catalog로 입력 ID부터 모든 substring/offset/hash/provenance/context/구조를 재계산·대조하며 stale/tamper/unchecked copy/extra를 거부한다. caller의 외부 usage/모델 이력은 서명 없이 인증되지 않으며 후보 누락·잘못된 의미 해석은 구조상 통과할 수 있다.
- API create_numeric_extractor_v3(model:Model), numeric_evidence_prompt_v3(source), run_numeric_extractor_v3(extractor,source), validate_numeric_proposal_v3(source,proposal). 필수 borrowed Model만·lazy이며 key/defaultclient 생성/조회/폐기 없음. Agent는 Source와 전체 UTF8 envelope preflight 뒤에만 만든다. provider identity issuedigest_numeric_evidence_v3, strict tool propose_numeric_evidence_v3, total20,000/output2,500/30초/request1/retry0/repair0/Responses storeFalse/framing2048. static 최대12000 reference의 raw/OpenAI-normalized schema+instructions와 실제 N의 schema·whole quote+catalog 전체 prompt UTF8를 모두 측정·검사한다. 최소/최대N의 decimal 길이 경계를 확인한다. source/candidate 최대치는 예산 내 동시 수용을 보장하지 않으며 table 때문에 거부가 늘 수 있다. 지침 강화/토큰 절감을 품질 통과로 대신하지 않는다. 월10만원·기존 앱24,000/output2,500/예약·DBOS journal은 변경하지 않는다.
- 성공 known usage는 exact nonbool nonnegative int/request정확1/output≤2,500/input+output≤20,000이다. v1 raw usage/error helper를 재사용하고 post-result 구조 검증 실패는 알려진 raw usage(성공 cap 초과도 포함)를 보존한다. AgentRunResult 없는 실패 usage는 unknown/None이며 무료/예약 반환이 아니다. Caller가 transport retry0/차용 client 수명을 관리한다. 추가 verifier/검색/embedding/모델 재시도는 없다.
- 구현자는 Task1만 합성 Source/FunctionModel·TDD로 구현/자체 검토/commit한다. 과거 source와 tests는 바꾸지 않으며 scoped agents suite/Ruff/format/mypy·raw/normalized/정적/실제 schema envelope·source freeze proof와 RED/GREEN/미검증을 task report에 기록한다. network/keys/private actual/서버/containers/fullgate/childagents/push/PR/배포는 하지 않는다.
- controller는 이전과 byte-identical인 fixed source packet2개(whole quote2/1)·같은 gpt-5.4-mini로 새 SDK2회/최대2provider/request당1/retry0만 사전 고정해 실제 평가한다. output 구조·상태 taxonomy·지침이 함께 달라졌으므로 단일 변경의 인과 효과를 주장하지 않는다. 모든 raw/반환 field/null·원문/관계를 직접 읽고 수치6/5·하위 포함/하한·전망 조건·단위/시점·관측/전망을 판정한다. 실패/부분/미판정·알려진 비용/unknown을 유지하며 SDK 성공을 앱/최종 브리핑·일반 시사/중립성 통과로 확대하지 않는다. 실제 planned/unknown 양성/전체 문서 coverage는 미검증으로 둔다. 원문/ID/키/raw는 private만, 사용자 탭을 열거나 이동하지 않는다.
- controller가 단일 최종 전체 gate·독립 작업/전체 검토·PR/CI·Sites 이전v73 archive/현재 요약·사본/native 게시·이번 소유QA/SDD만 정리한다. actual source와 gate/review/CI/source snapshot/최종 docs-only head를 구분하고 기존 실패 분모·Ruling/비용·개발v9/운영 유예를 보존한다.

## Task 1: 서버 확정 reference 선택 SDK

Read adjacent global-constraints.md generated verbatim from Global Constraints; it is binding. This is the private B2C briefing's numeric evidence foundation. No consumer UI/checkpoint or application integration is requested.

- [x] 새 numeric_evidence_refs.py에 위 catalog·strict reference DTO/현재 N schema·정확 resolver·v3 taxonomy/nonnull status·같은 인용 fact/관계/주체/중복/cycle·unreviewed proposal/현재 Source 검증·lazy borrowed runner/정적·실제 envelope/known usage를 구현한다. v1의 순수 Source/JSON/strict/usage helpers와 v5 schema helper는 import 가능하지만 기존 코드를 수정하지 않는다. model text/occurrence/citation UUID를 완전히 출력 경계에서 제거한다.
- [x] 새 test_numeric_evidence_refs.py로 실제 RED→GREEN을 확인한다. 모든 code point(공백/control/NEL/BOM/결합/astral)/연속ID/여러 인용·같은 단어의 다른 위치, inclusive reference→half-open offset·null/known/forecast 조건, 없는/bool/string/역순/혼합 인용/blank/1000 초과·value/subject/statement/cue 포함·중복 물리값/ID/pair/독립3+cycle/12facts16relations/빈 후보, provider schema 현재1..N/decimal 경계·no free text/occurrence/CID·전체 prompt/table 정적/실제 예산 before Agent, source/order/hash/offset/숨은extra/stale/일관된 live mutation, borrowed ownership/키 조회 금지/one request/retry0/storeFalse/timeout/usage 성공·known 실패/unknown 실패를 의미 있게 검증한다. 참조가 있어도 잘못된 kind/단위/관계 의미·후보 누락이 통과할 수 있음을 잠근다. 기존 source/tests/AGENTS의 base byte동일 manifest와 schema 실측·예산 경계를 기록한다.
- [x] scoped agents suite/Ruff/format/mypy·diff check와 README의 실제 API/의미/예산·인수 경계를 갱신한다. task-1-report.md에 RED/GREEN 명령/출력·수정/검증/한계·manifest·남은 concerns를 기록하고 scoped 네 파일만 commit한다. Task1 완료 체크만 바꾼다. controller의 실제2/전체 gate/독립 검토/PR/사이트/정리는 별도다.

## Controller 인수

고정 실제2의 전 field/원문 직접 판정, 독립 작업/전체 코드 검토·단일 전체 gate, Draft PR/CI·Sites v73보존/현재/native 게시·소유QA/SDD 정리를 각각 진행 기록에 확인한다. 의미/앱 통합이 미완료면 그대로 남긴다.

## 판단과 비용

1. 모든 문자의 서버 reference를 입력한다. 모델이 유효 ID를 골라도 잘못된 의미/경계를 고를 수 있으며 입력량이 늘어 같은 한도에서 처리할 whole quote가 줄거나 요청이 사전 거부될 수 있다. 원문 삭제/예산 확대로 숨기지 않는다.
2. v3 forecast는 조건 없는 전망도 포함하며 명시 조건은 별도 필드다. 잘못된 선택이면 조건 유무가 kind 하나로 구분되지 않으므로 소비자는 condition을 함께 읽어야 한다. 향후 v1/v2와 결합할 때 명시 mapping·재검증이 필요하다. 기존 결과/종류/앱은 변환하지 않는다. 어느 경우도 의미 정확성 인증이 아니다.


## 서버 원문 참조 v3 · 실제2회 거부 · 2026-10-19

같은 두 whole quote packet(인용2개/1개)·gpt-5.4-mini에 v3를 각각1회 실행했다. sourceb3794da·독립SDK2/공급자2·재시도0, 반환0/전체 거부2·의미 완전 충족0이다. 실제 앱/사용자 세션0이며 원문 재수집·자동 수리·부분 결과 수용·추가 유료 시도는 없다. 기존 v2 거부2·v1 부분1/거부1·앱4/12·과거 실패/미판정은 별도 보존한다.

controller가 원문·모든 raw field/null·관계와 원래 catalog로 해석한 위치를 직접 읽었다. 첫 응답(raw수치5/관계3)은 단위로 공백을 골라 전체 거부됐다. 필요한 하위 수치가 fact에서 빠지고 직접 하위 포함 관계도 없었다. 다른 단위는 구두점/조사, 기간은 지역 문구를 가리켰고 하한 수식어·전망의 연말 시점/실행 조건도 제대로 연결하지 못했다. forecast 분류 자체는 있었지만 충분한 인수가 아니다. 관계 세 개의 물리 포함 조건은 고립해서 성립해도 cue가 지명 목록이어서 관계 의미 인증이 되지 않는다.

둘째(raw수치3/관계2)는 관계 cue가 공백이고 다른 관계는 실제 endpoint 값/주체가 statement 밖이라 전체 거부됐다. 수치 범위에 조사/동사를 넣고 소비자 증감을 기업 대상으로 연결했다. 현재 기업 수준을 다음달 전망 주체/planned와 묶었고 월간 하락 수치는 누락, 전망 수준은 qualifier에만 나타났다. 필요한 수치6/5개를 올바른 fact로 모두 얻지 못했다. 단위 부재의 null 등 개별 타당한 필드도 정상 제안으로 집계하지 않는다.

알려진 실패 사용량은 SDK에2건 보존됐다. 입력4,485/출력947토큰,4.95/3.04초이며 청구 금액은 미확인이다. 이전 v2 입력3,003/출력2,029와 비교해 입력은 늘고 출력은 줄었지만 누락을 동반했다. 출력 계약·지침·상태 taxonomy가 함께 달라 단일 변경 효과나 일반 비용 절감/품질 향상으로 해석하지 않는다. provider 범위 내 번호·정확 substring은 올바른 의미 경계/대상·단위·시점/완전 추출을 보장하지 않는다.

다음은 글자 번호를 고르게 하는 방식을 앱에 붙이기보다 서버가 확정한 수치·단위/문장 후보 경계를 제공하는 계약을 설계하고, 규칙 기반 후보의 누락·오탐을 먼저 오프라인 비교하는 것이다. 의미/관계 선택은 여전히 별도 검증 대상이다. 실제 planned/unknown 양성·전체 문서·다양한 정치 이슈/중립성·최종 브리핑 품질은 미검증이다. 개발ab6654e/v9·API/DBOS/권한/DB/공개/UI/수집기·월 예약은 그대로이며 main/운영은 D013 유예다.


## 전체 구현 인수

sourceb3794da의 전체5,257개·lint/format/types/build/OpenAPI contract, 작업/전체 독립 Spec/품질 PASS(C0I0M0)를 확인했다. 실제 sourceb3794da와 code가 같으며 이후 변경은 Markdown뿐이다. PR51 기반 [Draft PR52](https://github.com/DigestWorks/IssueDigest/pull/52)·source CI/Sites/소유QA·SDD 정리는 [진행 기록](../planning/progress.md)의 개별 receipt를 따른다. 실제2회 거부/수용0과 의미 품질/앱 통합 미완료·개발v9·운영 유예를 유지한다.


## 최종 인계

sourceb3794da의 전체5,257개·작업/전체 독립 구현 Spec/품질 PASS(C0I0M0)·source CI39244869318 success, PR51 기반 Draft PR52·Sites v74/이전v73 보존·소유QA1/SDD archive 정리를 확인했다. 사본2d8d059 이후 출판/정리 기록은 [진행 기록](../planning/progress.md)의 저장소 원본이다. 이후 변경은 Markdown뿐이며 마지막 문서 push의 새 CI와 구분한다. 실제2회 모두 거부/수용0·두 Ruling/비용·개발v9/main·운영 유예는 유지한다. 서버 후보 경계·누락/오탐·의미와 앱/최종 브리핑은 후속이다.
