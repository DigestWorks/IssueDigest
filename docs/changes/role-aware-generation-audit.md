# 역할 전체 참조·증감 연결·출력 배분 설계

2026-10-21. 상태: 다음 계약 설계·오프라인 직렬화 시제품. SDK/실제 의미 개선·provider envelope 검증은 미완료다. [직전7회 인수](../research/compact-scope-acceptance.md)의 원래 기준/실패/비용을 보존한다. 기존431실행/설정 파일과279개 실제 인수 기록(이전173+직전106)을 변경하지 않는다. 이번 모델 호출0·앱/API/DB/worker/UI·기본 모델·서버/main 변경0이다.

## 문제와 선택

검수는 잘못된 범위/연도 누락을 탐지했지만, 이미 비교 기준에 저장된 정보를 기간 누락으로 다시 지적했다. 현재 projection에서 빠진 purpose/comparison_baseline 등 원래 역할을 검수에 제공해야 한다. 기관 운영과 발표, 수혜대상과 측정 범위를 혼동하는 의미 기준도 분리해야 한다.

J는 생성 출력1,597 뒤 남은903으로 검수를 완료하지 못했다. 필드를 계속 추가하거나 토큰 한도를 올리는 대신 같은 정보를 덜 반복하는 전송 형식을 검토한다. 전체 원문과 canonical 결과의 역할/출처는 유지한다.

| 검토 | 판단 |
| --- | --- |
| 원문 anchor 참조표 추가 | 이번에는 채택하지 않음. 같은 원문 복원이 가능하지만 J의 출력 JSON은4,484→4,515byte로 커졌고 H/I도 증가. K의 감소만으로 일반화하지 않음 |
| 짧은 **이름 있는** 전송 필드 | 다음 계약에 채택. 문구/원문을 줄이지 않고 명시 매핑으로 canonical 필드를 복원. 위치 의존 tuple이나 의미 없는 자유 코드 목록은 사용하지 않음 |
| 같은 진단의 적용 대상 명시 묶음 | 다음 검수 계약에 채택. 같은 진단·원문 statement를 공유하는 경우에만 대상 수치를 모델이 열거. 서버가 다른 수치로 추정 전파하지 않음 |
| 생성/검수 출력 배분 | 새 생성1,400/검수최대1,100을 설계안으로 둠. 합산2,500은 유지하며 실제 schema·토큰·의미/출력 충분성 인수 전 채택 완료로 표시하지 않음 |

참조표는 완전한 역할을 더 싸게 전달하는 증거가 부족해 보류했다. 같은 context를 합치거나 잘못된 기존 역할을 고치는 변환도 하지 않는다.

## 1. 명시 전송 매핑과 전체 역할 전달

생성 profile/tool/identity를 `shared-role-aliases-v1` / `fill_shared_role_aliases_v1` / `issuedigest_shared_role_aliases_v1`로 분리한다. 기존 compact/v2의 실제 DTO·지침·body·영수증은 그대로 둔다. 전송 DTO의 모든 필드는 required이며 nullable과 누락을 구분한다. 기존 actual/nested 모델·tuple 검사를 직렬화 전에 수행한다.

| canonical 역할 | 새 전송 필드 |
| --- | --- |
| ContextualAnchor sentence_id/text/context_text | s/t/c |
| context_id/reporting_event_id/measured_variable | id/event/entity |
| target_scopes/value_status/logical_condition | scopes/status/condition |
| forecast_basis/comparison_baseline | basis/baseline |
| event_id/reporting_actor/reporting_tense | id/actor/tense |
| binding candidate_id/context_id/status_evidence_sentence_id | number/context/status_sentence |
| relation from_id/to_id/statement_sentence_ids | from/to/support |

나머지 period/purpose/predicate/kind/anchor/cue와 root contexts/events/bindings/relations는 이름을 유지한다. 매핑은 객체 종류별로 고정한다. 예를 들어 event의id를 context_id로 읽지 않는다. 다른 객체의 alias·추가/누락·잘못된 타입·중복 ID·dangling 참조는 거부한다. AI가 canonical/alias 이름을 섞거나 서버가 빠진 필드를 채우지 않는다. 실제 strict 동적 모델을 생성하고 provider output의 actual 타입까지 확인한다.

출력의 contexts/events/bindings/relations 개수는 기존12/12/12/16, 수치별 context+binding scope 합계4를 유지한다. 현재 Source에서 전체 v2 index와 로컬 quote/완전한 문장 packet을 새로 만들고 UUID/provenance는 서버에 보존한다. 원문·공백·빈 문장·후보·범위/근사·상태 근거 문장은 줄이지 않는다.

서버는 명시 매핑으로 SharedMeasurementInput을 구성한 뒤 현재 source의 SharedMeasurementFrameV2 전체를 재구성한다. 이는 원래 역할 구조의 읽기 전용 helper 재사용이며 **기존 generation으로 profile을 바꿔 저장 영수증을 통과시키는 변환이 아니다**. 새 generation에는 alias 원본·확장 frame·아래 증감 연결·새 prompt/instructions/source 해시와 known usage를 저장해 모두 재구성한다. canonical frame의 기존 field·값/의미를 바꾸지 않는다.

검수 prompt에는 얕은 수치별 projection 대신 **전체 contexts/events/bindings/relations**를 같은 alias로 보낸다. purpose/condition/basis/baseline·보고 사건과 직접 관계를 포함해 이미 다른 역할에 있는 정보도 읽을 수 있어야 한다. source/원래 generation/전체 proposal 해시를 보존하고 현재 source와 실제 concrete generation부터 재검증한다. alias는 권한이나 provenance가 아니다.

## 2. 수치별 증감 연결

각 binding에 required nullable `change`를 둔다. null은 그 수치를 증감량으로 제안하지 않았다는 뜻이다. 누락과 같지 않으며, 실제 증감량을 null로 남긴 오류는 별도 의미/누락 인수 대상이다.

nonnull 형식은 `direction: increase|decrease|unchanged|uncertain`, `evidence: {s,t,c}|null`, `support: 현재 sentence ID 목록`이다. increase/decrease/unchanged는 nonnull exact evidence가 필요하다. uncertain은 evidence가 없을 수 있지만 full candidate를 포함한 지원 statement와 불확실 상태를 남긴다. support는1..20개 연속·원래 순서·같은 인용이며 완전한 수량 표현과 nonnull anchor를 포함해야 한다. 기존 정확 문맥 해석 규칙과 occurrence 중복 거부를 유지한다.

이 필드는 **변화량인 수치의 방향**이다. 현재 인원/비중이 증가 사건과 같은 문장에 있다는 이유로 모든 수치를 증가율로 바꾸지 않는다. 결과 수준·구성 비중과 증감량을 원문 관계로 구분한다. 변화율의 부호를 임의로 바꾸거나 절대 금액/합계로 계산하지 않는다. 비교 기준은 baseline, 조사/측정 기간은 period로 구분하며 ‘전년도 대비’만으로 절대 조사 연도를 만들지 않는다.

서버의 anchor/statement 일치는 관계 의미의 정답 인증이 아니다. 문장에 ‘감소’가 있다는 이유만으로 해당 수치의 decrease를 자동 결정하지 않는다. enum과 exact 인용의 잘못된 연결도 의미 인수에서 실패로 기록한다. K의 두 방향을 수동으로 붙인 시제품은 형식 예시이며 원래 AI 응답을 고친 성공으로 세지 않는다.

## 3. 역할을 아는 별도 검수

새 profile/tool/identity는 `role-aware-audit-v1` / `audit_role_aware_v1` / `issuedigest_role_aware_audit_v1`이다. 원래 generation은 수정하지 않는다. caller가 명시한 borrowed Model로 추가1요청, retry/repair/fallback0이다.

새 generation은 측정 대상·범위·기간·보고 주체·change_direction을 검수한다. 기존 정확한 v2/compact generation도 각자의 validator로 받을 수 있지만, 없는 change를 null로 채우지 않는다. legacy prompt/report에 `change_coverage=unavailable`과 검수 가능한 네 역할을 명시하고, 동적 role enum에서 change_direction을 제외한다. 새 generation은 `change_coverage=available`이고 다섯 역할을 검사한다. unavailable을 양성 검수나 증감 방향 통과로 표시하지 않는다. 저장값의 원래 profile/status와 새 marker 누락도 파싱 전에 거부한다.

의미 기준은 다음을 분리한다.

- 비교 기준이 baseline에 이미 있으면 같은 비교 표현을 period 누락으로 중복 요구하지 않는다. 단, 원문에 별도의 실제 측정 연도가 있으면 baseline이 그 연도를 대신하지 않는다.
- 목적의 수혜대상이 측정 집단을 제한하는지 원문 관계로 판단한다. 목적에 같은 단어가 있다는 이유로 무조건 범위 충족/누락을 결정하지 않는다.
- 운영·주관과 발표·인용 주체를 구분한다. narration에서 운영 기관이 등장했다고 reporting_actor를 억지로 채우지 않는다. 명시된 소속은 운영 기관과 이름이 같아도 정당할 수 있다.
- G의 기존 정상 gold와 새 범위 정의가 충돌할 수 있다. 원래 판정/분모는 보존하고 새 기준의 독립 검토·명확한 정상 반례를 인수 전에 준비한다. 응답을 본 뒤 gold를 바꾸지 않는다.

### 명시 진단 묶음

checks는 선택된 수치 순서대로 정확1개이며 전송 필드는 number/status다. 상태의 no_issue_found/issues_found/uncertain·incomplete와 보수적 전체 상태는 기존 규칙을 유지한다.

issues는 최대12묶음이며 각 묶음은 role/kind/evidence/support와 `targets:[{number,slot},...]`를 가진다. targets는1..12개로 실제 선택된 수치만 명시한다. 같은 evidence·지원 statement·역할·진단 종류를 공유할 때만 묶는다. 대상마다 scope 슬롯 존재/nonnull 원래 필드·역할 일치·완전한 수량/anchor의 statement 포함을 따로 검사한다. 다른 인용이나 statement가 필요하면 나눈다. target_scope 이외의 slot은null이며, unsupported scope는 대상별 실제 r슬롯이 필요하다. missing은 슬롯null·exact evidence가 필요하다. 증감 unsupported는 새 nonnull change가 있어야 한다.

확장은 열거된 targets에만 하며 서버가 누락된 수치를 추정 추가하지 않는다. 빈 targets/중복 target·동일 진단/상충 check/무관 슬롯은 거부한다. 최대 확장 진단은12×12=144이며 **새 report 계약**에 명시한다. 기존 최대12진단 모델로 잘라 통과시키지 않는다. 묶음/출력 상한으로 미완료라면 incomplete를 남기고 미완료/무진단 수치는uncertain이다. hard issue 우선순위와 incomplete 표시는 함께 보존한다.

선택0은 모델0회/not_applicable이다. 문제 미발견은 해당 coverage에서 AI가 문제를 찾지 못했다는 뜻이며 진실·중립·전체 수치 선택·사람 검토 승인이 아니다. 새 diagnostics는 원래 frame을 수리하거나 재생성하지 않는다.

## 4. 합산 예산과 실패

새 생성 출력 상한1,400, 검수는 `min(1,100, 2,500-generation.output)`을 설계한다. 합산 total20,000/output2,500은 그대로다. legacy 생성에는 새1,400을 소급하지 않으며 기존 관측 사용량의 잔여 안에서만 검수한다. 예산/타입/source/marker가 유효하지 않으면 송신0이다.

각 단계의 UTF8(prompt+instructions)+max(raw/normalized schema)+framing2,048+그 단계 출력 상한을 실제 잔여 total과 비교한다. 특히 전체 proposal 추가·묶음 target enum의 실제 schema를 반영해야 한다. 이 설계 시제품에는 schema/지침/provider 정규화 전체 측정이 없으므로 **수용 가능하다고 주장하지 않는다**. 구현 첫 단계에서 측정하고 넘으면 원문을 자르거나 예산을 올리지 않고 계획/형식을 재검토한다.

두 stage 요청 합계2와 단일 stage 요청1을 구분하고 관측 raw usage/합산 한도를 runtime·stored 양쪽에서 검사한다. 송신 전 실패·송신 가능/사용량 불명·관측 초과·출력 미완료를 구분해 원래 known generation usage와 nullable audit usage를 보존한다. unknown을0/무료로 합산하지 않는다. 단일 borrowed Model·30초/no-store·caller lifecycle과 자동 재시도/수리0을 유지한다.

1,400/1,100은 출력 여유를 사전에 나누는 새 계약이며 완료 보장이 아니다. reasoning도 출력 한도에 포함한다. 최대12수치/144진단의 실제 완성·지연/비용·정상/오류 판정은 별도 인수이며 이번 바이트 측정에서 추정하지 않는다. 앱 전체 planner/selector의24,000/출력2,500과 별도로 비용을 더해 쓸 수 없고 내구 회계/권한 인수 전 앱 연결은 보류한다.

## 오프라인 시제품 결과

기존 완전한 G/H/I/J/K 역할을 alias로 옮긴 뒤 역매핑해 모두 정확히 복원했다. 원래 입력·generation·증거는 그대로다. contexts를 합치거나 잘못된 역할을 고치지 않았다. K에 수동 방향 예시, 모든 binding에 새 change 필드를 포함했다.

| 자료 | 기존 생성 인자 UTF8 byte | alias+change 인자 | 기존 검수 인자 | 명시 묶음 검수 인자 |
| --- | --- | --- | --- | --- |
| G | 2,015 | 1,462 | 1,393 | 726 |
| H | 1,562 | 1,120 | 686 | 445 |
| I | 1,522 | 1,104 | 888 | 475 |
| J | 4,484 | 3,230 | 유효 반환 없음 | 비교하지 않음 |
| K | 4,179 | 3,139 | 698 | 464 |

검수 묶음은 기존 경고의 내용/개수를 모두 확장 복원하며 **오탐도 그대로 유지**한다. 확장 순서는 새 group/targets 순서이며 과거 진단의 교차 배치 순서까지 같다고 주장하지 않는다. 원래 저장된 진단 순서는 변경하지 않는다. J의 잘린 검수를 유효 결과로 복구/비교하지 않았다. 전체 proposal+원문 packet의 UTF8 byte는 G2,639/H1,980/I2,002/J6,280/K4,517이다. 이는 실제 schema·instructions·framing·출력 reserve까지 합친 요청 envelope가 아니다. 모델의 생성/정확도·관측 토큰/비용 절감 증거도 아니다. 구조 개선을 의미 개선으로 표시하지 않는다.

## 구현 순서·인수

1. 동적 alias DTO/정확 역매핑·방향 계약부터 구현하고 실제 provider schema/envelope를 **무호출/mock**로 점검한다. 모든 새 required/nested 실제 타입·source/marker/해시 재구성, 같은 역할 문구의 ambiguous occurrence·정당한 소속·baseline/period·방향의 양성/불명 반례를 TDD로 확인한다. 과거 계약431파일과 실제279증거는 동결한다.
2. 새 단일 생성 SDK와1,400 상한·자기 profile 영수증을 구현한다. 원래 frame 순수 helper 재사용과 기존 generation으로의 영수증 번역을 구분한다.
3. 전체 역할 proposal·coverage·묶음 진단/144확장·잔여 한도 검수 SDK를 구현한다. legacy unavailable·empty/incomplete·묶음의 대상별 검증·출력 초과/unknown usage·caller lifecycle을 합성/mock로 검사한다.
4. 독립 태스크/전체 변경 검토·필요한 전체QA와 보존 manifest를 확인한다. 그 뒤 새 cap/원문/정상·오류 gold를 호출 전에 고정한 실제 인수로 의미·오탐·출력 충분성과 비용을 평가한다. 이번 소진7회 runner/기준/응답은 재실행/수정하지 않는다. 앱/운영은 별도다.

앞 절은 설계 당시 문서·비공개 직렬화 시제품 기록이다. 당시 제품 코드·SDK는 추가하지 않았고 기존7,366개 코드QA 증거를 재사용했다. 이후 구현·새 전체검증은 아래 기록, PR/Sites 게시 영수증은 진행 기록을 따른다.

## 구현·검증 · 2026-10-21

새 role_alias_contract/role_alias_generation/role_bounded_runtime과 role_aware_audit_contract/role_aware_audit, 합성 테스트 네 파일을 추가했다. 생성은 전체 원문/기존 역할을 유지하고 수치별 change의 방향·정확 근거·연속 지원 문장을 별도 보존한다. 검수는 purpose/condition/basis/baseline·사건/관계를 포함한 전체 proposal을 읽으며, 명시 targets만 최대144개로 확장한다. prompt 범위 목록은 원래 context+binding 순서를 가리키는 번호로 중복을 줄이고 저장 report는 전체 scope/anchor와 hash를 보존한다. legacy에는 change를 채우지 않고 unavailable/네 역할, 새 결과에는 available/다섯 역할을 기록한다.

단일 borrowed Model·30초/no-store·재시도/수리/대체0, 새 생성 출력1,400·검수 min(1,100,2,500−기존 출력)·합산 total20,000/output2,500이다. stage 요청1과 aggregate2(빈 검수1)를 구분하며, unknown usage를0으로 만들지 않는다. 완성된 JSON이어도 provider 미완료 응답이면 알려진 사용량과 전송 여부를 보존한 채 거부한다. 저장값의 원래/중첩 식별자·실제 타입·현재 원문/후보/동적 schema·출력/합산 사용량을 다시 검증한다.

코드 `8305031f5023e3254acdf160a710f363dceab87b`의 전체 Python6,762+JS820=7,582개, lint/format/type/build/OpenAPI 검사를 통과했다. 실패/skip/warning0이다. 태스크별 독립 검토·미완료 응답·중첩 식별자 누락 지적 수정/재검토와 전체 변경 검토를 마쳤다. 세부 수정 및 최종 판정은 진행 기록을 따른다. 기존431코드/설정/테스트와279실제 증거 SHA는 동일하며 앱/API/DB/worker/UI·기본 모델·서버/main 배포 변경0이다.

| 보존 자료 | 생성 요청 envelope | legacy 전체 역할 검수 envelope | 검수 잔여total / output cap |
| --- | ---: | ---: | ---: |
| G | 14,998 | 10,825 | 16,322 / 1,100 |
| H | 14,675 | 10,231 | 16,647 / 1,100 |
| I | 14,713 | 10,219 | 16,640 / 1,100 |
| J | 17,037 | 14,671 | 14,890 / 903 |
| K | 15,211 | 12,716 | 15,763 / 1,100 |

단위는 UTF8 prompt/instructions+max(raw/normalized schema)+framing2,048+출력 reserve인 보수적 envelope다. 기존 관측 generation usage를 차감한 legacy 검수 용량 예시이며 새 토큰 사용량/비용이나 의미 개선 증거가 아니다. 최초 J15,611>14,890을 차단했고 원문/역할을 빼지 않는 번호 참조·동일 의미 지침 축약 후14,671로 수용했다. 여유219와 출력903이 실제 완료를 보장하지 않는다. 새 다섯 역할도 동일 자료의 FunctionModel 합성 응답으로 전체 proposal/coverage와 schema 용량을 확인했으며 input100/output30은 합성값이다. 실제 제공자 호출은0이다.

이전7회 결과·gold/분모/실패 비용을 바꾸거나 소진 runner를 재실행하지 않았다. 특히 생성 의미0/2·검수 오탐·출력 미완료를 개선 완료로 표시하지 않는다. 다음은 새 계약의 사전 고정 실제 의미/오탐·충분한 출력 평가, 전체 앱 예산/권한/내구 실행 인수와 적용 판단이다. 앱은 이 내부 SDK를 아직 사용하지 않으며 M3는 진행 중이다.
