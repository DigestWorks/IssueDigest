# 역할 적용 관계·무손실 검수 입력 설계

2026-10-22 한국 시간. [v2 실제9회 평가](../research/semantic-balanced-acceptance.md) 다음 설계/비공개 무호출 시제품이다. 새 SDK·실제 의미 개선·앱 적용을 완료한 상태가 아니다. 실행 코드446개·과거 실제 증거480개(361+119)·기존 gold/점수/실패 비용을 보존하며 추가 provider 요청0이다. 앱/API/UI/DB/worker·기본 모델·서버/main은 변경하지 않는다.

## 문제를 나누는 이유

H는 원래 사업 수에 있는 하위 지역이 국비에는 빠졌지만 검수가 무경고였다. I는 운영 주체를 집계 인원의 기관 소속으로 넣었고 검수가 두 대상을 탐지했다. 이는 단어의 존재만으로 적용 관계를 결정할 수 없고, 검수의 무경고도 정확도 인증이 아니라는 사례다. 사업 연도는 새 proposal의 다른 역할에 이미 있어 period에도 중복을 강제하는 누락으로 세지 않았다. 과거 입력/기준은 바꾸지 않는다. G의 역할 분류/목표 기간 경계는 여전히 독립 사람 재판정 과제다.

J의 생성은 입력3,486/output1,610으로 끝났으나, 전체 원문과 실제 proposal8context/6event/8binding/1relation의 후속 검수는 envelope15,466 > 실제 잔여14,904라562초과했다. 원문/역할 삭제나 한도 인상으로 넘기지 않았다. 이 실패는 출력 완료와 후속 입력 수용이 다른 조건임을 보여준다.

## 표현 비교와 선택

다섯 실제 v2 generation을 읽기 전용 참조로 사용했다. 반복 anchor를 별도 사전으로 만드는 안, 이름 있는 열을 한 번 적고 각 객체를 행으로 쓰는 안, 두 안의 결합을 비교했다. 모든 원래 값·순서·null·빈 배열을 정확히 왕복 복원했다. context/사건/수치를 합치거나 의미 오류를 고치지 않았다.

| 참조 proposal | 현재 JSON | anchor 사전 | 이름 있는 열/행 | 열/행+anchor 사전 |
| --- | ---: | ---: | ---: | ---: |
| G | 1,648 | 1,803 | 1,437 | 1,592 |
| H | 1,218 | 1,405 | 1,152 | 1,339 |
| I | 1,104 | 1,357 | 1,038 | 1,291 |
| J | 3,897 | 4,562 | 2,766 | 3,429 |
| K | 2,359 | 2,510 | 1,898 | 2,049 |

UTF8 minified JSON byte이며 token/비용 측정이 아니다. anchor 사전은 overhead가 더 커 이번에는 채택하지 않는다. **이름 있는 열/행을 검수 입력에만 적용하는 안을 다음 구현으로 선택한다.** 생성 DTO·출력·원래 frame은 바꾸지 않는다. 앞서 rejected present/absent 생성 출력안과도 다른 입력 표현이다.

proposal만 바꾸면 J의 기존 지침/schema 기준 envelope는14,335·여유569다. 이를 실제 새 요청으로 간주하지 않고, 후보 catalog·문장·scope slot까지 같은 원칙으로 묶은 전체 입력과 읽는 방법 지침을 별도로 시험했다.

### 전체 입력의 무호출 확인

| 자료 | 기존 검수 envelope | 새 table 초안 envelope | 원래 생성의 실제 잔여total | 검수 output cap | 여유 |
| --- | ---: | ---: | ---: | ---: | ---: |
| G | 11,129 | 11,117 | 16,460 | 1,100 | 5,343 |
| H | 10,371 | 10,613 | 16,789 | 1,100 | 6,176 |
| I | 10,267 | 10,509 | 16,843 | 1,100 | 6,334 |
| J | 15,466 | 13,809 | 14,904 | 890 | 1,095 |
| K | 12,211 | 11,714 | 16,140 | 1,100 | 4,426 |

새 tool명 `audit_role_table_v1`·identity `issuedigest_role_table_audit_v1`·profile `role-table-audit-v1`·input_format `named-columns-v1`의 초안이다. 기존 실제 dynamic DTO의 raw/normalized schema를 재사용한 ToolOutput을 새 tool명으로 mock HTTP5회 전송했다. 추가 decoder 지침412byte를 포함한 지침은3,134byte다. no-store·low·명시 default tier·30초·각 실제 잔여/출력cap을 유지했다. 표의 envelope는 전체 UTF8 prompt+지침+max(raw/normalized schema)+framing2,048+출력reserve다.

다섯 자료의 전체 원문·문장 순서/빈 문장/공백·후보 atoms/단위/qualifiers/범위·원래 proposal·다섯 역할/current slot 순서를 복원했다. 짧은 H/I는 지침·header overhead로242byte 커졌으며 모든 자료에 대한 용량 절감을 주장하지 않는다. 잘못된 표식/header/행 길이/필수 cell/추가 필드의55개 시제품 사례를 거부했다. 이는 새 strict SDK의 전체 타입/변조 검증이나 실제 AI 의미 시험을 대신하지 않는다. Function/HTTP usage100/30은 합성 mock 값이며 원래 실제 생성의 usage를 바꾸지 않았다. 실제 새 audit 요청·token/의미/비용 개선 관측은0이다.

## 다음 table 입력 계약

각 표는 정확한 `columns`와 `rows`를 가진다. 이름 없는 tuple을 추측해 읽지 않고 열 이름/정확한 순서를 한 번 명시한다. 필수 cell은 null이어도 생략하지 않는다. header순서·행 길이·필드 집합·실제 타입이 다르면 복구/기본값 삽입 없이 거부한다.

- proposal의 contexts/events/bindings/relations는 현재 alias 이름의 고정 열과 행이다. `from`만 유효하며 `from_`를 다른 이름으로 받지 않는다. nested anchor/scopes/change는 기존 이름 있는 객체를 그대로 둔다.
- candidates는 id/quote_id/expression/atoms/separator/qualifiers/lexical_kind/sentence_ids 전부를 유지한다. 인물/기간/수량을 새로 분류하거나 원문 숫자/단위를 계산하지 않는다.
- 각 quote의 sentences는 id/text 열이다. text를 행 순서대로 separator 없이 이어 원문과 정확히 같아야 한다. 빈 행·빈 text·공백을 제거하거나 문장을 합치지 않는다.
- scope_slots는 number/slots 열이며 context.scopes→binding.scopes의r1..r4 순서를 유지한다. roles/change_coverage도 보존한다.
- codec는 현재 source·검증된 exact RoleAliasGenerationV2로부터 결정적으로 만들고 역변환 후 의미 데이터가 원래 canonical packet과 완전히 같은지 확인한다. 시제품이 비교용 packet identity를 되돌리는 것은 receipt 변환이 아니다. 실제 SDK는 새 audit의 자기 profile/hash/영수증을 만들며 v2 audit 영수증으로 위장하거나 검증을 통과시키지 않는다.

새 감사 결과의 pure report/진단 DTO와 target/span 검증은 기존 의미 계약을 읽기 전용 재사용할 수 있다. 원래 generation·proposal/source/coverage hash·최대144 명시 대상·필수 역할/slot·미완료/uncertain 우선순위·unknown/known 실패 usage는 그대로 재검증한다. 새 wrapper profile `role-table-audit-v1`과 input_format/지침 hash를 명시적으로 고정하고, 저장 값은 현재 packet/schema/원래 report로 재구성한다. 새 모델이 표를 잘 읽는다는 가정만으로 성공을 표시하지 않는다.

현재 코드446개는 동결한다. 다음 구현은 별도 codec 모듈/합성 테스트와 별도 borrowed-model table auditor/합성 테스트이며 기존 v1/v2 요청·영수증·wire를 바꾸지 않는다. 각 Model은 caller가 소유하고 단일1회/30초/no-store·retry/repair/fallback0이다. 생성output1,800·검수min(1,100,2,500−실제 생성output)·합산total20,000/output2,500을 유지한다. 빈 선택 검수0회/합산1·정상 합산2·실패 raw usage와 시작 불명확성을 보존한다. 앱 전체24,000/output2,500·권한/내구 인수는 별도이며 새 경로에 추가 예산을 주지 않는다.

## 역할 후보·적용 관계는 별도 검증

원문에 있는 열거·연도/상대 시점·기관/지역처럼 생긴 접미사·인용구를 exact source span으로 모으는 범용 시제품을 시험했다. 개별 열거 구성원도 별도로 보존하고 동일 실제 위치의 중복 origin만 함께 기록했다. 서로 다른 위치/역할을 합치지 않았다. 탐지되지 않은 표현도 원문 전체에는 남는다.

| 자료 | 표면 힌트 | 선택 수치×동일 quote 힌트 | 힌트 입력 추가 byte(새 지침/schema 제외) |
| --- | ---: | ---: | ---: |
| G | 5 | 15 | 495 |
| H | 8 | 16 | 680 |
| I | 3 | 6 | 379 |
| J | 24 | 192 | 1,844 |
| K | 7 | 42 | 596 |

이는 실제 지명/기관/기간 catalog가 아니다. 실제로 ‘양성도’·‘전년도’를 지역 접미사처럼 잡는 오탐이 있었다. 원래 오류를 피하려면 origin을 semantic type/사실로 승격하거나 단어가 보인다는 이유로 모든 수치에 연결해서는 안 된다. 이 다섯 자료의 locate 실패는0이었으나 일반 completeness/recall 증거가 아니며, locate 불가·한도 초과를 조용히 누락해 완료로 만들지 않는다.

향후 적용 관계 계약은 각 선택 수치와 같은 quote의 정해진 후보 쌍에 대해 ‘측정 범위/기간·기관 운영 주체/발표·entity 한정어/사업 정체성·비교 기준/목적·관련 없음/불확실’을 명시 판단하는 방향이다. 운영과 정당한 소속은 함께 가능하고 목적 수혜자가 집계의 배타적 모집단인 것은 아니다. 한 단어에 여러 역할이 명시될 수 있으므로 무조건 단일 역할로 강제하지 않는다. 후보 누락/모호성·검토되지 않은 쌍을 무경고/관련 없음으로 자동 채우지 않는다. G의 분쟁 gold를 이에 맞춰 수정하지 않는다.

하지만 전체 힌트와 pair grid를 지금 붙이는 안은 채택하지 않는다. J는 힌트 입력만1,844byte라 table 여유1,095보다749크며 새 지침/출력 schema/output 부담도 더 든다. 단순 추가·조용한 후보 절단·추가 호출/예산 확대를 하지 않는다. 기존 packet/표현과 안전하게 source 참조를 공유하는 후보 계약, 명시 coverage/overflow/uncertain, 실제 source-linking/오탐·미탐/비용을 별도 설계·인수해야 한다. table 변경만으로 H의 의미 미탐이나 I의 생성 오류가 해결됐다고 주장하지 않는다.

## 구현·인수 순서

1. table codec의 현재 필수 타입/표식·raw/actual/nested/tuple·열/행·빈 선택·원문 roundtrip·변조 거부를 TDD로 구현한다.
2. 별도 table audit SDK·자기 영수증/지침/schema·actual remaining budget·late validation 실패/unknown usage·대상별 진단·무송신/mock을 검증한다. 독립 검토·새 전체QA와 기존446/480 증거 보존을 확인한다.
3. 새 사전 기준/상한으로 동일 실제 v2 generation의 새 table audit를 제한 평가한다. 실제 읽기 정확도·장문 완료·미탐/오탐·비용을 따로 확인한다. 이미 소진한9회 runner나 한도/응답을 변경해 재호출하지 않는다.
4. 역할 후보/적용 관계는 전체 원문·proposal·합산 예산을 지키는 별도 계약의 용량/coverage부터 확인한다. 이전 의미 실패·G사람 재판정과 앱 인수는 계속 남긴다.

이번은 spec-driven-workflow 문서 예외의 연구/설계·비공개 시제품 작업이다. 새 production SDK·새QA/SDD/서버 자원을 만들지 않았고 전체7,808개 코드QA 증거는 코드가 같아 재사용한다. source·원래 모든 응답/gold/비용·이번 비교 결과를 보존하며 PR/Sites 최종 기록은 진행 기록을 따른다.
