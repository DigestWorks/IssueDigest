# 반복 원문 없이 수치·상태·관계 근거 제안

2026-10-19. PR50/805e154 후속 M3. OpenSpec root=null: init 없이 단일 Spec/Task/제약으로 구현한다. 이전 독립 SDK2회는 부분1·거부1이며 앱ab6654e/v9·v10 의미 인수 미통과와 모든 과거 분모를 유지한다.

## Spec

새 numeric-evidence-v2는 provider 출력에서 반복 context와 span별 citation UUID를 제거한다. fact가 인용 하나를 참조하고 짧은 exact text/occurrence만 반환한다. 서버는 해당 whole quote 안에서 각 위치를 계산한다. known status는 nonnull 근거 span을 갖는 별도 provider union으로 받아 빈 상태 근거 조합을 줄인다. 관계는 두 수치와 명시 주체·cue를 함께 포함하는 exact statement를 요구한다. 구조 강화는 cue의 실제 지시 대상·상태 해석·핵심 수치 누락을 인증하지 않으며 결과는 unreviewed다.

v1을 덮어쓰지 않고 새 모듈/식별자로 만든다. 이번 범위는 독립 SDK 및 고정된 두 원문 packet의 전후 비교다. 최종 브리핑/DBOS/예산·취소/중단 복구 통합은 별도다. 기존 사용자 화면/개발 배포를 바꾸거나 검증용 화면을 추가하지 않는다.

## Global Constraints

- 기준805e154c41920fcf0f9aef2b9a0ba6a88d80d49b, feat/numeric-evidence-compact, PR50 기반 Draft. 기존 linked worktree 재사용·baseline5,003/source CI39235962771 재사용, baseline 전체 반복 없음. 실행 code·기존 tests/AGENTS·종속성/lockfile/API/DB/UI/collector/v1 provider와 기존 v2~v10/selector/worker는 byte-identical. 새 numeric_evidence_v2.py/새 test_numeric_evidence_v2.py/agents README와 관련 계획 문서만 허용한다. 서버 접속/개발 배포/main 병합/운영 변경 없음.
- Source는 기존 정확 tuple(UUID4 snapshot,EvidenceBundle,SourcePresentation)이다. v1의 canonical source/unchecked extra 방어·원래 순서의 전체 quote1..20/합계12,000 codepoints·현재 snapshot/workspace 검증을 재사용한다. model/client/Agent 초기화 전 입력/실제 raw-normalized envelope를 검증한다. 원문을 자르거나 정규화하지 않고 metadata/제목을 근거로 쓰지 않는다.
- provider compact span은 text(정확 nonblank1..1000 codepoints)/occurrence(strict int0..31)만이다. fact citation_id는 현재 인용 enum이며 local_id는 f1..f12, value 필수; subject/unit/period/qualifier/condition은 nullable exact span이다. context 원문을 출력하지 않는다. status는 known {kind:observed|planned|conditional_forecast,text:필수span} 또는 unknown {kind:unknown,text:nullable span}의 nested strict union이다. JSON Schema 자체에서 known text=null을 허용하지 않는다. 전망 조건이 명시돼 있으면 condition에 보존하고 불명확/무근거는 unknown/null이다. 숫자/범위/열린 하한/주체/단위/시점을 계산·변형·합치지 않는다. 지침은 명시된 실질 수치(작은 하위 항목·증감 포함)를 빠짐없이 후보화하도록 요구하되 부수적인 날짜/식별자 숫자는 측정값으로 만들지 않는다. 후보/출력 상한 때문에 실제 전체 추출을 보장하지 않는다.
- 서버는 span의 occurrence를 인용 전체에서 겹침 포함 왼쪽부터 계산해 Python Unicode code-point [start,end)를 저장한다. v1 ProposedSpan/ResolvedSpan/정확 resolver와 nonblank 규칙을 재사용한다. 모든 fact field는 fact citation에 있어야 한다. 중복 local_id/같은 물리 value 구간·잘못된 span/모델 우회/extra는 전체 거부한다. status와 condition의 의미 판정/수치 전체 탐지는 보장하지 않는다.
- relation0..16은 citation_id, kind(included_in|parallel|unknown), from_id/to_id, statement exact compact span, cue exact compact span이다. 서로 다른 두 실제 fact는 같은 relation citation을 참조하며 각각 subject가 nonnull이어야 한다. statement는 두 endpoint value와 두 subject 및 cue의 물리 span을 모두 포함해야 한다. 한 unordered pair는 종류/방향에 관계없이 하나만 허용하고 included_in child→parent의 3+ cycle도 독립 거부한다. statement가1000을 넘거나 주체가 불분명하면 관계를 제안하지 않으며 임의 잘라 맞추지 않는다. facts0이면 relations0. 구조 검사는 주체/수치/cue 의미의 정확성을 인증하지 않는다.
- strict/frozen extra-forbid NumericEvidenceProposalV2는 profile numeric-evidence-v2/status unreviewed, snapshot/workspace, 서버 prompt/source SHA256, 원래 quote provenance, 해석값 없는 resolved fact/관계, typed KnownUsage다. fact는 citation_id/local_id·resolved value/nullable field·kind/status_text를 갖고 context는 해당 whole quote reference다. relation은 resolved statement/cue다. validate_numeric_proposal_v2는 현재 Source로 모든 offset/provenance/hash/구조를 재계산하고 tamper/stale를 거부한다. hash는 서명/권한/진실/인간 검토/외부 usage 인증이 아니며 현재 접근 권한은 향후 호출자 책임이다.
- 공개 내부 API create_numeric_extractor_v2(model:Model), numeric_evidence_prompt_v2(source), run_numeric_extractor_v2(extractor,source), validate_numeric_proposal_v2(source,proposal). 필수 borrowed Model만 허용·lazy이며 키/defaultclient를 읽거나 client를 생성/폐기하지 않는다. provider identity issuedigest_numeric_evidence_v2, strict tool propose_numeric_evidence_v2. 독립 total20,000/output2,500/30초/request1/retry0/repair0/Responses storeFalse·framing2,048이다. static20UUID enum/raw-normalized schema 및 실제 schema+instructions+prompt UTF8+출력 예약을 모두 검사하며 최대 입력/후보 수의 동시 수용을 보장하지 않는다. 기존 앱24,000/월10만원/예약은 변경하지 않고 standalone 비용을 앱 전역 통합 완료로 표시하지 않는다.
- 성공 known usage는 nonbool nonnegative int/input+output≤20,000/output≤2,500/request정확1. v1 raw usage 수집/실패 error를 재사용하며 결과 후 검증 실패는 알려진 raw usage를 보존한다. Agent 결과가 없는 실패 usage는 unknown/None이며 무료/예약 반환이 아니다. 추가 모델 요청/수리/semantic verifier·임베딩·검색은 없다. 사용자 대화/raw/API key/실제 원문/ID는 공개하거나 Git에 기록하지 않는다.
- controller는 기존 fixed-actual-cases와 정확히 같은 whole quote packet2개를 복사·사전 고정해 각각1회, 합계2SDK/최대2provider/retry0만 실행한다. 각 반환/거부의 raw 모든 field/null/관계와 quote를 직접 읽고 기존 v1의 부분1/거부1·기존 앱4/12와 분리 기록한다. 누락·cue 지시 대상·관측/전망·명시 조건/하한/기간을 판정하되 실제 planned/unknown 양성·일반 시사/중립성·최종 브리핑 품질은 미검증으로 둔다. output 감소가 품질 향상/누락 원인 해결을 증명하지 않는다.
- controller가 단일 전체 gate/독립 작업·전체 검토·Draft PR/CI·Sites 이전v72 archive/현재 요약·사본/native 게시·이번 소유 QA/SDD 정리를 수행한다. 구현자는 합성 source/FunctionModel만 사용하며 network/key/private/서버/containers/fullgate/PR/push/배포/자식agent 없이 Task1만 TDD로 구현·자체 검토·commit한다.

## Task 1: compact 수치·상태·관계 SDK

Read the adjacent task constraints file generated verbatim from Global Constraints; every item is binding. This task belongs to the B2C briefing's private numeric fidelity foundation, not a UI/application change.

- [x] 위 Spec/Global Constraints의 v2 DTO·resolver/source 재검증·현재 인용 enum/nested status union·관계 주체/statement/중복/cycle·unreviewed proposal/현재 Source 검증·lazy borrowed one-request runner/preflight/known usage를 새 numeric_evidence_v2.py에 구현한다. v1의 순수 helper/타입을 import할 수 있지만 기존 실행 코드/테스트를 수정하지 않는다. 원문 문자열 존재와 의미/전체 추출 보장의 경계를 README에 명시한다.
- [x] test_numeric_evidence_v2.py에서 RED→GREEN을 실제 확인한다. 정확 Unicode/겹침 occurrence/공백·숫자 표현 보존, whole citation context(1000보다 긴 인용 가능), nullable field/known text schema null 거부/unknown, 불명확한 주체·다른 citation·statement/cue/endpoint 물리 포함·같은 값 다른 주체와 중복 물리값·3+cycle/모든종류중복pair, empty·caps, hash/offset/provenance/unchecked extra/stale source/live mutation, preflight-before-Agent/borrowed ownership/one request/retry0/timeout/storeFalse/strict tool·usage success/known failure/unknown failure를 검증한다. 구조상 통과하는 잘못된 의미 해석·수치 누락도 합성 사례로 보여 semantic 인증 아님을 잠근다. raw/normalized schema 실측·입력한계 경계·old frozen source manifest를 기록한다.
- [x] 관련 agents suite/Ruff/format/mypy만 실행하고 명령/출력·RED 실패 원인·최종 pass/경고/실패·byte동일 proof·남은 한계를 task-1-report.md에 기록한다. 해당 완료 체크만 바꾸고 코드/README/체크를 커밋한다. 이후 controller의 독립 작업/전체 검토와 실제2/단일전체gate가 별도다.

## Controller 인수

단일 전체 gate·작업/전체 독립 검토·고정 실제2 전 field 직접 검토·원래 실패 분모/개발v9 유지·Draft PR/CI·Sites v72보존/현재 요약/native 게시·소유QA/SDD 정리는 진행 기록에서 각각 확인한다. 의미 품질 또는 앱 통합이 미완료면 그대로 남긴다.

## 판단 · whole quote context와 관계의 명시 주체

반복 context 대신 fact의 전체 인용을 context reference로 사용하고 관계는 별도 statement와 두 명시 주체를 요구한다. 이 선택은 짧은 출력과 관계 endpoint 근거를 얻기 위한 것이다. 잘못되면 넓은 인용 안의 필드가 잘못 연결돼도 구조 검사를 통과하거나, 주체 생략/긴 문장에 걸친 실제 관계가 거부·누락될 수 있고 유료 호출 비용이 남는다. 의미 평가는 별도로 유지하며 이를 자동 승인/완전 추출로 쓰지 않는다.


## Controller 실제 인수

새 v2를 이전과 byte-identical인 두 원문 packet(whole 인용2개/1개)에 각각1회 실행했다. 실제 source5592d9c·독립SDK2/공급자2요청·재시도0이며 반환0·전체 거부2·의미 완전 충족0이다. 기존 v1의 부분1/거부1, 기존 앱4건/12요청과 모든 과거 실패/미판정 분모를 유지했다. 앱·실제 사용자 세션은0이다.

controller는 두 원응답의 raw 수치6/5개·관계3/2개와 모든 field/null을 whole quote와 직접 대조했다. 이전에 누락된 하위 항목과 증감 수치는 raw에 나타났지만 수용된 후보가 아니다. 첫 응답은 단위의 존재하지 않는 occurrence3개·다른 값의 단위 연결, 전체 endpoint/cue가 statement 밖인 관계와 cross-citation 관계 때문에 거부된다. 전망 조건을 qualifier에 넣고 condition을 비운 문제, 관측의 상태 근거로 포함 문구를 쓴 문제도 남았다. 둘째는 두 관계 statement가 떨어진 원문 조각을 붙인 문자열이어서 거부된다. raw의 조사 표현을 단위로 쓰거나 반복 단위/시점을 오연결하고, 명시 전망을 관측으로 분류한 의미 오류도 남았다.

두 raw는 known 상태 근거의 nonnull provider DTO를 만족했지만 exact 위치/관계 검사를 통과하지 못했다. 추가 호출 없이 원래 raw의 DTO/각 field/관계 물리 조건을 오프라인으로 분리 확인했고, 잘못된 행을 고치거나 정상 부분 proposal로 반환하지 않았다. 알려진 실패 사용량2건은 SDK에도 보존됐다. 입력3,003/출력2,029토큰·지연6.64/4.51초이며 청구 금액은 미검증이다. 동일 두 자료의 v1 출력3,229보다 짧았다는 관측을 일반 비용 절감·의미 품질 향상으로 확대하지 않는다.

계약 구현/합성 검사와 실제 모델 의미 인수는 별개다. 실제 planned/unknown 양성·전체 문서 수치/다양한 정치 이슈/중립성·최종 브리핑 품질은 미검증이다. 개발ab6654e/v9·앱/DBOS/DB/API/공개/UI/수집기·월 예약은 변경하지 않았고 main/운영은 D013 유예다. 다음 설계 후보는 모델이 occurrence를 세거나 관계 문장을 다시 쓰게 하기보다 서버에서 확정한 원문 위치 참조를 선택하게 하는 방식이다. 단순한 지침/성공 재호출·자동 수정은 해결로 표시하지 않는다.


## 전체 구현 인수

source49fd20d의 전체5,124개·lint/format/types/build/OpenAPI contract, 작업/전체 독립 Spec/품질 PASS(C0I0M0)를 확인했다. 실제 source5592d9c와 code가 같으며 이후 변경은 Markdown뿐이다. PR50 기반 [Draft PR51](https://github.com/DigestWorks/IssueDigest/pull/51)·source CI/Sites/소유QA·SDD 정리는 [진행 기록](../planning/progress.md)의 개별 receipt를 따른다. 실제2회 거부/수용0과 의미 품질/앱 통합 미완료·개발v9·운영 유예를 유지한다.
