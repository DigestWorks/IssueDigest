# 정확 인용에 연결한 수치 근거 후보

2026-10-19. PR49/edc7ae7 후속 M3. OpenSpec root=null 확인: init 없이 이 단일 Spec/제약/Task를 따른다. 사용자의 이어서 진행과 v10의 하한·잘못된 포함 관계·전망 조건 실패가 출발점이다.

## Spec

숫자의 원문 표현과 대상·단위·기간·관측/계획/조건부 전망·수식어·조건 및 포함/병렬 관계를 exact quote에 묶는 독립 private SDK를 만든다. 모델은 검토 전 후보를 제안할 뿐이며 서버는 인용/부분문자열의 존재·위치와 구조를 검증한다. 같은 숫자/인용에 있다는 사실은 관계의 진실이나 포괄성을 증명하지 않는다. 모든 결과는 명시 unreviewed다. 근거가 없거나 애매한 필드는 null/unknown으로 남기고 숫자를 계산·보정하지 않는다.

이 단계는 최종 문장에 지침만 추가하는 방식의 후속 기반이다. 질문별 생성·DBOS·앱 기본·DB·API·공개·UI·데이터/수집기에 아직 연결하지 않는다. 브리핑에 넣기 위한 출처 의미 판정과 전역 비용/복구·실제 최종 답변 인수는 다음 Spec에서 다룬다. 소비자에게 새 관리/검증 화면을 만들지 않는다.

## Global Constraints

- 기준edc7ae794980d1db8878021e3f118ccbe372220c, branch feat/numeric-evidence-proposals, PR49 기반 Draft PR. 기존 linked worktree 재사용·기존 baseline4,887/sourceCI39229760833 재사용, baseline 전체 재실행 없음. controller의 최종 전체 gate는 별도다. main/운영 병합·새 개발 앱 반영 없음. 개발ab6654e/v9와 v10 의미 인수 미통과/기존4앱12요청 분모를 보존한다.
- 신규 packages/agents/src/issuedigest_agents/numeric_evidence.py, 관련 테스트/README만 구현한다. 기존 agents/selector/planner/worker/domain/client/UI의 provider instructions/schema/prompt/default/version/slot·기존 DTO/공개 OpenAPI는 byte-identical로 유지한다. 종속성/lockfile·환경·권한 변경 없음.
- 원문 입력은 기존 Source=(UUID snapshot_id, EvidenceBundle, SourcePresentation) 한 건이다. 모델을 초기화하기 전에 sid UUID4 exact type, canonical 모델 재검증(model_copy/model_construct bypass 포함), snapshot/workspace provenance·중복 citation/정확 selector를 검증한다. 원문 전체 bounded quotes만 포함하며 제목/metadata는 의미 근거로 쓰지 않는다. 원래 quote를 잘라 예산을 맞추지 않는다. 허용 입력은1~20 citations/전체 quote codepoints≤12,000이며 request-envelope bytes를 별도 적용한다. 입력 복사본/해시가 바뀌면 예전 후보를 동일 출처 결과로 수용하지 않는다.
- 모델 제안 span은 citation_id, exact nonblank text(≤1,000 codepoints), occurrence(엄격 정수0..31)다. 동일 문자열의 occurrence는 겹침도 포함해 왼쪽부터 센다. 서버가 Python Unicode code-point start/end(반열린구간)를 계산한다. 대소문자/NFC/공백/수치/단위를 정규화하지 않는다. 못 찾으면 전체 제안을 거부하며 fuzzy match/외부 조회/자동 수리를 하지 않는다. 프롬프트에서 citation ID별 원문을 순서대로 제공하고 출력 도구의 enum을 현재 citation IDs로 제한한다.
- 각 numeric fact 후보는 local_id(f1..f12), context span, value span, subject/unit/period/qualifier/status_text/condition의 nullable span, kind=observed|planned|conditional_forecast|unknown이다. context/value 필수이며 나머지는 실제 원문에 있을 때만 채운다. 모든 field span은 같은 citation과 context 안에 있어야 한다. 알려진 kind에는 status_text 필수, unknown은 status_text nullable이다. qualifier 없음은 정확/닫힌 상한을 뜻하지 않는다. 숫자의 해석값/산술 결과·자유 요약/근거 점수/verified·AI supported·인간 검토자 필드는 받지 않는다. 실제 값은 원문 문자열로만 보존하고 숫자 여부/의미를 취약한 regex로 인증하지 않는다. field 겹침은 허용하며 동일 value 물리구간을 중복 fact로 만들지 않는다.
- 관계는 kind=included_in|parallel|unknown, from_id/to_id와 context span/cue span이다. 두 ID는 실제 다른 fact에 연결하며 context는 두 endpoint의 value와 cue를 포함하는 같은 citation이다. 포함 방향은 child→parent, 모든 kind에 걸쳐 같은 unordered fact pair는 한 관계만 허용하며 순서/종류를 바꾼 중복도 금지, directed inclusion cycle·자기참조·없는/중복 local_id·중복 관계는 전체 거부한다. cross-citation 관계는 이번 버전에서 수용하지 않고 unknown으로 꾸며 통과시키지도 않는다. cycle 없는 graph와 원문 cue의 존재는 관계 의미 인증이 아니다.
- 결과는 frozen strict extra-forbid NumericEvidenceProposal/profile numeric-evidence-v1/status unreviewed, 원래 snapshot/workspace·prompt SHA256·source SHA256, 원래 순서의 resolved facts/relations, 원문 quote provenance와 typed known usage를 포함한다. source SHA는 snapshot/workspace와 순서 있는 citation ID/정확 quote를 deterministic JSON으로 묶는다. 모델이 prompt/source hashes·provenance/검토 status/usage를 제공하지 못하며 서버가 만든다. 새 진실 인증/자동 승인·공개 게시로 소비할 수 없다. 외부에서 받은/unchecked 복제 report를 validate하는 공개 함수는 현재 Source로 모두 다시 계산·대조해 원문 변경/해시 불일치/인용·위치·provenance 조작을 거부한다. 해시는 인증 서명이 아니며 원문에 존재하는 문자열의 다른 의미 해석이나 후보 누락을 검출하는 장치가 아니다.
- 공개 SDK create_numeric_extractor(model:Model) 는 필수 borrowed Model을 검증하는 lazy handle이다. None/string/object는 client/key/Agent 생성 전에 거부한다. numeric_evidence_prompt(source)·run_numeric_extractor(extractor,source)·validate_numeric_proposal(source,proposal)를 제공한다. borrow 모델을 생성/닫거나 default client/키를 읽지 않는다. Agent는 실제 run 시에만 만들며 source preflight 뒤에 실행한다. 정해진 provider identity issuedigest_numeric_evidence_v1, strict tool propose_numeric_evidence, facts0..12/relations0..16이며 facts0이면 relations0이다. 무응답/구조 오류를 빈 정상 결과로 바꾸지 않는다. null/unknown/비어 있는 후보는 자료 부족/불완전 추출일 수 있으며 모든 수치를 발견했다는 표시가 아니다.
- 독립 runner 상한은 input+output20,000/output2,500·30초·요청1/retry/repair0·Responses/storeFalse다. gpt-5.4-mini를 쓰는 client 구성은 controller/호출자 책임이다. 실제 raw/OpenAI-normalized tool schema 중 큰 bytes+instructions+promptUTF8+framing2,048+예약 output을 preflight하고 상한 초과는 유료 호출 전에 거부한다. 정적 최악 enum20개도 측정하고 실제 schema와 함께 검사한다. 최대 인용/후보 수는 모두 동시에 채울 수 있다는 보장이 아니다. 이 SDK의 상한은 기존 앱24,000/output2,500·월 예약을 이미 통합했다는 뜻이 아니며 앱 통합 시 전역 예산 재설계/검증이 필요하다. 월10만원·기존 월 예약 정책 변경 없음.
- 성공 usage는 exact nonbool nonnegative int이며 요청≤1/output≤2,500/합계≤20,000을 검사한다. 실패는 sanitized NumericEvidenceError로 표시하고 실제 result를 받은 뒤의 검증 실패는 valid nonnegative raw known_usage를 보존한다(상한 초과 usage도 자르지 않는다). result 없는 SDK/전송 실패의 usage는 None/unknown이며 무료나 예약 반환을 뜻하지 않는다. DBOS journal/정산·transport level 실패의 완전 비용 회복은 이 SDK 밖이다. 추가 call/자동 수리/문장 검수는 없다.
- 구현자는 합성 문서/FunctionModel만 사용한다. 키/실제 원문/서버/network/provider/container 관리·자식agent·baseline/full gate·push/PR/배포 금지. 기존 코드 동결과 source-byte proof를 기록하고 Task1만 체크한다. controller가 작업별/전체 독립 검토, 단일 전체 gate, Draft PR/CI/Sites와 소유 QA/SDD 정리를 한다.
- controller 실제 검증은 기존 기검토 공개 텍스트의 서로 다른 두 자료에서 extraction 각각1회(합계2 SDK/최대2provider·추가 성공 retry0)만 별도 수행한다. 기존 질문별4앱을 재실행하지 않는다. 호출 전 요청/원문/기대·미판정/상한 receipt를 private에 고정한다. 모든 후보 field/관계/원문을 직접 대조해 substring 검증과 의미 판정을 분리한다. 원문/ID/키/raw응답은 private만. 실패·누락·불확실을 분모에 남기며 합성 통과/SDK 추출을 실제 최종 브리핑 품질 통과로 확대하지 않는다. SDK가 의미 정확성을 보장하지 않는다고 표시한다.

## Task 1: 수치 원문 후보 SDK와 원문 연결 검증

- [x] 위 Global Constraints를 그대로 따르는 request/strict DTO·원문 span 해석·관계 검증·frozen unreviewed report와 현재 Source 재검증, bounded borrowed model SDK/known usage 실패 경계를 TDD RED→GREEN으로 구현한다. 구현 순서는 순수 anchor 검증→facts/relations/report provenance→tool/schema/runner다. 겹친 반복문자열·동일숫자 다른대상/기간·소수/범위/하한·forecast조건·포함/병렬을 허구 자료로 검증하고 자동 의미 판단은 만들지 않는다.
- [x] 잘못된/다른 source·교차workspace/snapshot·model_copy/model_construct·공백/Unicode/astral/NFC·미존재/다른citation/out-of-context/occurrence bool/초과·중복 span/id·역방향 cycle/없는 endpoint/병렬중복·0facts relation·extra/forged verified/hash/usage·현재 원문 변경 재검증을 실제 pure path로 검사한다. raw output 가짜 DTO도 serialize/revalidate한다.
- [x] FunctionModel actual tool path로 enum/strict schema·합성 정상/unknown/빈후보·형식 실패/후처리 실패/known usage·provider exception/unknown usage·preflight0calls·20개 enum raw/normalized/static/actual UTF8 예산·임계값·request1/retry0/storeFalse/timeout·borrowed모델수명을 검사한다. 기존 관련성 SDK/agents 지침 bytes를 유지하는 증거·관련 agents tests/Ruff/format/mypy와 README를 기록하고 명시 commit/report한다. 전체 gate/실제2/최종 review/PR/CI/Sites/정리를 완료로 대신 표시하지 않는다.

## Controller 인수

전체 gate/독립 검토·실제2 SDK/최대2provider의 전 field/관계 직접 읽기, 원래 v10 실패 보존·개발v9/배포 없음, Draft PR49 기반 새 PR/CI·Sites v71 archive/요약·사본/native 게시와 이번 소유 QA/SDD만 정리한다. 확인한 증거만 진행 기록에 누적한다.

## Ruling · 동일 수치 쌍의 중복 관계 거부

같은 unordered fact pair에는 kind/방향에 관계없이 관계 하나만 허용한다. included_in의 방향과 3개 이상 포함 cycle 검사는 별도로 유지한다. 모호한 관계를 여러 종류로 겹쳐 정상 후보처럼 반환하지 않는 구조적 기준이다. 잘못되면 원문이 같은 두 수치의 여러 관계를 설명할 때 전체 제안이 거부되고 알려진 호출 비용은 남을 수 있다. 이 경우 자동 수리/재호출 대신 다음 버전의 관계 모델을 설계해야 한다. 의미의 진실을 인증하는 기준은 아니다.

## Controller 실제2 SDK 인수

새 수치 근거 후보 SDK를 실제 두 자료의 사전 고정 whole 인용2개/1개로 각각 한 번 실행했다. 기존 질문별4앱/12요청은 재실행하지 않았다. 새 SDK2회/공급자2요청·자동 재시도0에서 unreviewed 후보 반환1·전체 거부1이다. 의미를 완전히 충족한 제안은0이며, 반환1도 부분 결과다.

반환한 후보의 수치5개·관계3개와 거부된 raw 수치3개의 모든 field/null·관계를 원문과 직접 대조했다. 첫 자료는 현재 하한·전망 범위/열린 표현·전망 조건을 보존했지만 핵심 하위 항목을 누락했다. 세 관계 모두 원문에 실제 있는 포함 문구를 사용했으나 그 문구가 직접 가리키는 수치 쌍과 제안 관계가 달랐다. 일부 기간도 빠졌고 같은 단위의 첫 occurrence를 여러 수치에 반복 연결했다. 문자열 존재/구조 통과를 관계 의미나 완전 추출 인증으로 바꾸지 않는다.

둘째 raw는 알려진 상태 세 행의 status_text가 모두 null이어서 전체를 거부했다. raw의 명시 전망 값이 관측으로 분류된 문제도 남았다. 거부 행을 정상 후보/성공으로 집계하거나 자동 고쳐쓰지 않았다. SDK는 Agent 결과를 받지 못한 실패 usage를 unknown으로 남겼으며, controller가 별도로 보존한 완료 공급자 원응답2개의 사용량은 입력3,187/출력3,229토큰이다. 지연10.85/4.96초·청구 금액 미검증이며 unknown은 무료를 뜻하지 않는다.

이는 독립 내부 추출 SDK의 제한된 평가다. 실제 planned/uncertain 양성·전체 문서 수치의 포괄성·다양한 정치 이슈/중립성·최종 브리핑 품질은 미검증이다. 기존 v10 실제4건의 부분/미충족·과거v9/selector/v8/v7/v6/v5 분모는 유지한다. 앱/DBOS·DB/API/공개/UI/수집기와 개인 개발ab6654e/v9를 변경하지 않았다. 다음은 반복 context 출력의 비용을 줄이는 입력 참조 구조, provider 단계의 상태/근거 조합 제약, 관계 cue의 실제 지시 대상과 누락을 평가하는 계약을 설계하는 것이다. 단순히 더 강한 지침/성공 재호출로 해결됐다고 표시하지 않는다.

Task1 독립 Spec/품질 PASS(C0I0M0), sourcebbf6b7e 기준이다. 전체 gate71fa6b8의5,003개와 전체 독립 구현 Spec/품질 검토(PASS/C0I0M0), PR49 기반 [Draft PR50](https://github.com/DigestWorks/IssueDigest/pull/50)을 확인했다. source CI/Sites/정리는 별도 receipt를 진행 기록에 남긴다. 의미 품질 및 앱 연결은 미완료다.
