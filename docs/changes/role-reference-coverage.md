# 역할 분류와 원문 참조 보존을 분리하기

2026-10-22 한국 시간. [실제 역할 연결5회](../research/role-link-acceptance.md) 다음 설계·비공개 오프라인 시제품이다. spec-driven-workflow의 문서/연구 예외이며 production 모듈·SDK·UI·DB·worker·서버 자원을 추가하지 않는다. 기존456코드/642실제 평가/45+59설계 증거·과거 gold/점수/비용을 보존한다. 추가 provider0·기존8,409QA 재사용, 앱/main 변경0.

## 문제와 결정

직전 사전 역할 조건은 주요6/8·대조7/9그룹이었다. 미충족10관계의 이름과 연결은 E(entity_qualifier)에 남아 있었다. 기존 original generation까지 오프라인 대조하니 그중 K6관계는 원래 entity anchor 안에도 명칭이 포함됐고, J4관계는 해당 수치에 연결된 선택 항목에서 정확한 명칭 위치를 참조하지 않았다. **같은 S/E 불일치가 같은 정보 보존 상태를 뜻하지 않는다.** 사전 점수는 그대로 두며 사후 E를 S로 바꿔 만점으로 만들지 않는다.

다음 순수 계약은 역할 정답이나 의미상 누락을 판정하는 대신, 현재 원문 후보의 정확 위치가 원래 추출의 어떤 선택 필드에 연결되어 있는지 따로 기록한다. 역할 분류·선택 필드의 문자 참조·의미 동등성·중요도는 각각 독립된 축이다.

S는 측정값이 적용되는 모집단·영역의 제한, E는 집계 대상의 이름·종류·정체성 한정을 설명하는 제안적 구분이다. 지역 이름도 지역 자체의 개수를 셀 때는 대상 식별, 그 지역의 지원액을 설명할 때는 수혜 범위로 기능할 수 있다. 직종 목록도 대상 분류를 식별할 수 있다. 표면 문자열의 종류나 기존 저장 필드만으로 역할을 확정하지 않는다. 복수 역할은 가능하지만 근거 없이 E→S를 일괄 변환하거나 둘을 항상 동치로 취급하지 않는다. 이 구분은 향후 의미 판정 지침이며 기존 SDK/사전 gold를 수정한 것이 아니다.

## 대조 가능한 선택 필드

현재 source와 전체 RoleLinkGeneration을 기존 strict validator로 재검증한 뒤 원래 generation의 binding→context→reporting event를 정확히 따라간다. 같은 context를 명시 공유한 수치만 해당 필드를 상속한다. 다른 수치의 필드·동일 quote라는 이유·relation chain을 통한 전이 상속을 만들지 않는다.

| 구분 | 필드 | 비교에 쓰는 범위 |
| --- | --- | --- |
| primary 선택 필드 | context.entity/period/condition/purpose/basis/baseline, context.scopes[*].anchor, binding.scopes[*].anchor, 연결된 event.actor | 명시 anchor의 실제 t 위치만 |
| auxiliary 참조 | event.predicate, binding.change.evidence, 해당 수치가 직접 from/to인 relation.cue, 수치 expression, binding.status_sentence의 문장 | 따로 기록하며 primary 보존으로 승격하지 않음 |
| 선택된 정보로 간주하지 않음 | anchor.c의 넓은 위치 구분 문맥, 자동 support/statement 전체, 출처 제목/metadata, 공유하지 않은 context/event, 관계 chain | 원문에 등장하거나 support에 들어 있다는 이유로 primary로 계산하지 않음 |

모든 carrier는 현재 원문에서 검증한 exact span·현재 binding number·필드 경로·primary/auxiliary 종류를 보존한다. 공유 context/event의 같은 경로라도 해당 binding과의 연결을 유지하며 경로 문자열만으로 서로 다른 수치의 carrier를 합치지 않는다. 같은 위치라도 entity/scope/actor 등 서로 다른 필드 경로를 합치지 않는다. actor와 scope에 같은 이름이 중복 저장됐더라도 텍스트 존재가 역할의 올바른 적용을 인증하지 않는다. source quote가 다른 동일 offset/문자열은 일치가 아니다. anchor.c는 반복 표현의 정확 위치를 정하는 데만 사용하고 포함된 다른 단어까지 선택했다고 보지 않는다.

## 별도 순수 report 제안

입력은 current source와 exact RoleLinkGeneration 전체이며 새 AI 응답을 받지 않는다. proposed profile role-reference-coverage-v1/rules selected-anchor-overlap-v1, source_inventory_exhaustive=false, status=unreviewed, semantic_equivalence/materiality=not_assessed를 필수 marker로 둔다. 이전 SDK·report·score로 위장하거나 provider usage를 새로 만들지 않는다. 원래 SDK 전체/hash·규칙/hash·carrier inventory·모든 후보×수치 행·문자 참조 counts를 보존하며 현재 원문에서 전체 재구성한다. 이 hash는 일관성 확인이지 provider 진위 인증이 아니다.

각 행은 원래 hint_id/number/link_state/roles를 그대로 보존하고 다음 중 하나를 기록한다.

| 상태 | 의미 |
| --- | --- |
| exact_reference | 해당 수치의 primary 필드가 후보와 같은 source 위치를 명시 참조 |
| containing_reference | 같은 위치의 후보 전체가 더 넓은 primary anchor 안에 포함됨 |
| partial_reference | primary와 일부만 겹침. 그룹의 한 구성원으로 전체 그룹을 보존했다고 계산하지 않음 |
| no_reference_in_selected_fields | 해당 수치의 조사 대상 primary 필드에 겹치는 정확 위치가 없음. 의미상 누락·원래 자료 어디에도 없음이라는 뜻이 아님 |

exact가 있으면 exact, 그다음 full containing, partial 순으로 요약하되 모든 witness와 필드 경로를 남긴다. auxiliary·다른 fact의 참조도 종류와 number를 따로 기록하며 현재 fact 상태를 채우지 않는다. 같은 문자열의 다른 원문 위치·동의어·바꿔쓰기·축약의 의미 동등성은 이 문자 비교가 판정하지 않는다. 관련없음/불확실/미검토 행도 제거하지 않고 전체 같은quote domain을 유지한다. model-positive라고 참조가 없으면 hard missing, 참조가 있으면 의미 보존이라는 규칙을 만들지 않는다.

향후 production DTO는 carrier inventory를 한 번 저장하고 행의 witness를 검증된 carrier ID/overlap 종류로 참조할 수 있다. 모든 현재 경로가 유도돼야 하며 runtime 임의 경로/원문 위치 입력을 신뢰하지 않는다. raw/actual/nested/container/scalar/필수 marker 검사를 dump 전에 하고 원문·원래 SDK·행·경로·분류·counts·hash·rules를 전체 재구성한다. bool/int/tuple/list/subclass/default 복구를 허용하지 않는다. 현재12선택수치/quote별24후보의 최대288쌍과 전체 witness를 보존하며 기존 audit144진단/20support문장 report로 변환하거나 새 낮은 숨은 절단 한도를 만들지 않는다.

## 무호출 시제품 결과와 한계

기존5자료/47후보/271행 전부를 현재 SDK validator로 재구성해 private projection을 만들었다. 10개 합성 경계(같은 위치/포함/부분 그룹/문맥만/다른 fact/반복 다른 위치/다른 quote/접점/복수 경로/부분+전체)를 확인했다. 행·원문 위치·role/state·carrier·marker·materiality·hash·원래 SDK 변경과 bool/int/tuple/subclass/필수값 변형은 시제품 비교70건에서 거부했다. 합성10개는 interval matcher 경계 확인이며 source DTO/모델 호출 검증으로 표시하지 않는다. 이것은 production Pydantic 계약·TDD·API/SDK 구현을 대신하지 않는다.

| 자료 | exact | containing | partial | 조사 primary에 참조 없음 | 합계 |
| --- | ---: | ---: | ---: | ---: | ---: |
| G | 2 | 4 | 2 | 7 | 15 |
| H | 3 | 7 | 0 | 6 | 16 |
| I | 3 | 0 | 0 | 3 | 6 |
| J | 7 | 6 | 0 | 179 | 192 |
| K | 8 | 14 | 0 | 20 | 42 |

모든 행을 센 표이므로 관련없음·표면 후보 오탐도 포함한다. 참조 없음215행을 누락215건으로 부르지 않는다. 직전10불일치만 대조하면 K6관계는 containing이며 원래 entity에 명칭이 남았다. J4관계는 해당 primary에 참조가 없다는 구조 관측만 확인했다. 추가 관계의 진실·기존 추출의 정확성/중요도·원래 공모/집계 맥락은 별도 판단이다. G역할·사람 재판정과 기존 generation 비분쟁1/4·이전 역할 검수2탐지/6미탐·추가3유보·직전부분6/8/7/9 점수/비용은 바꾸지 않는다.

시제품 첫 초안은 일반 Python 동등 비교였고, bool/int·tuple/list·subclass를 구별하도록 타입까지 비교하는 초안으로 보강했다. 두 초안과 위치 projection을 비공개 보존한다. 새 production typed DTO/필수 원본 guard·mutability·빈 선택/0후보/다중quote/공유context/모든 지원 경로/최대288경계·입력 크기/메모리와 fail-closed 동작은 다음 TDD에서 확인해야 한다. no-reference와 자동 의미 누락을 연결하지 않는 경계를 유지한다.

## 다음 구현과 인수

1. 순수 carrier inventory·행별 참조 report의 별도 strict DTO/원문 재구성·TDD를 구현한다. 기존 generation/link SDK/지침/실제 점수는 동결한다.
2. 역할 분류와 문자 참조의 조합을 사람이 해석할 수 있게 내부 평가에 기록하되 제품 임시 checkpoint UI·자동 hard 누락·자동 수정은 추가하지 않는다.
3. 의미 동등성·중요도·잘못된 역할 배정은 별도 기준/인수로 남긴다. 미관측 자료/후보 recall·G사람 재판정·앱 전체 비용/권한/내구 검증 전 앱에 연결하지 않는다. 추가 유료 호출로 기존 기준을 맞추지 않는다.

독립 설계·시제품 검토 C0/I0/M0. 전체271행을 별도 interval oracle로 대조해23exact/31containing/2partial/215no-reference와 K6/J4를 재현했다. 합성10경계/70변형 거부와 추가25타입 probe를 확인했다. 두 초안·projection·검토17개 증거를 불변 manifest로 보존한다.456코드/642실제/45+59기존설계 불변이며 production typed 계약/TDD·의미 동등성/중요도 인수를 완료했다는 뜻은 아니다.

[Draft PR91](https://github.com/DigestWorks/IssueDigest/pull/91)·Sites v113 게시 성공(2026-10-22 17:34:57 KST, sourceaf9bee1bf035b3fbcfecc435057db2649356282c), 이전v112 보존.98HTML/2,318로컬대상/289공개텍스트/private60항목 검사 통과. 텍스트만 변경해 브라우저QA는 반복하지 않았다. 실제 평가 PR90 브랜치를 대상으로 하며 앱/main은 변경하지 않았다. 신규 설계17개 증거·기존456코드/642실제/45+59설계·8,409QA를 유지하고 추가provider/서버/QA자원0, 브랜치/작업폴더 유지. 게시 후 영수증만 추가해 재게시하지 않는다.
