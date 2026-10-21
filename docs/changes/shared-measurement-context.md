# 공유 측정 맥락 · 순수 계약

2026-10-21. 상태: 순수 계약 구현·합성 구조 인수 완료. 생성 SDK·실제 의미 인수·앱 적용은 미완료. [동일 계약 추론 비교](../research/measurement-reasoning-comparison.md) 이후의 구현 단위다. 브리핑 제품 방향/기존 앱은 바꾸지 않으며 기존 실패를 변환해 성공으로 세지 않는다.

## 해결할 문제

현재는 수치마다 대상·범위·발표자·기간·상태·보고 시제를 반복해서 채운다. 최신 제한 비교에서도 국가는 측정 대상으로 들어갔고, 같은 자료의 범위는 비었으며, 미래 공급 행위를 과거 발표의 시제로 사용했다. 추론 토큰 사용만으로 전체 의미 기준을 충족하지 못했다. 모델 성능 일반 결론이나 새 구조의 성공을 미리 주장하지 않는다.

## 구현 계약

| 구성 | 역할 | 제안 상한 |
| --- | --- | --- |
| 측정 맥락 | 무엇을 측정하는지·공통 적용 범위·기간·값의 상태·조건/목적/전망 근거/비교 기준 | 12개 |
| 보고 사건 | 명시 발표자와 보고 술어·보고 시제, 또는 발표자 없는 서술 | 12개 |
| 수치 연결 | 기존 후보 ID·명시 맥락 ID·개별 추가 범위·상태 근거 문장 ID | 12개 |
| 직접 관계 | 기존 수치 후보 사이 원문에 명시된 포함/병렬 관계 | 16개 |

측정 맥락의 대상 필드는 `measured_variable`로 제안한다. 단순한 행위자/지역 엔터티가 아니라 측정되는 항목을 요구하고 범위와 분리한다. 같은 대상·기간·값 상태는 한 맥락을 공유할 수 있다. 서로 다른 항목/기간/값 상태는 별도 맥락으로 둔다. 숫자별로 전체 역할을 덮어쓰는 구조를 다시 만들지 않는다.

수치가 명시적으로 선택한 맥락 ID에만 공통 역할을 적용한다. 서버가 인접 문장이나 문서 metadata를 보고 자동 상속하지 않는다. 공통 범위와 숫자별 추가 범위는 합쳐 최대4개이며 같은 원문 위치 중복/다른 인용 연결은 거부한다. 기존 범위 종류와 정확 contextual anchor를 재사용한다. 범위의 의미가 맞다는 자동 인증은 아니다.

보고 사건은 `attributed_report`·`narration`·`unknown`을 구분한다. 명시 보고에는 발표자와 보고 술어를 함께 요구하고, 발표자 없는 서술에는 발표자를 비운다. `reporting_tense`는 사건의 예정 시점이 아니라 선택된 보고/서술 술어에 연결한다. 어떤 술어가 실제 보고인지에 대한 의미 검증은 여전히 필요하다.

목적은 별도 nullable 원문 역할로 보존하고 기존 `logical_condition`에 넣지 않는다. 조건은 수치가 성립하는 전제이며 목표/정책 목적과 구분한다. generic 계획 표제나 예정 행위만을 전망의 근거로 자동 승격하지 않는다.

## 기존 코어 재사용

- 기존 수치/단위/범위/열린 상한 후보, exact source/contextual anchor, 같은 인용/전체 문장·직접 관계 검사, `MeasurementScopeFrame`은 유지한다.
- 새 입력의 맥락/보고 사건/연결을 저장하고 명시 연결을 따라 기존 프레임으로 확장하는 순수 adapter부터 구현한다. 새 원본 입력과 파생 프레임을 함께 현재 source에서 재생성해 비교한다. 과거 프레임이나 판정은 수정하지 않는다.
- status evidence는 기존처럼 수치 포함 전체 문장 ID로 연결하며 문장 위치를 의미 인증으로 사용하지 않는다. 반복 관계 cue가 모호하면 계속 전체 거부하고 사후에 관계를 삭제하거나 첫 위치를 골라 수리하지 않는다.
- 동적 provider/runner 연결은 공통 요청 실행을 재사용한다. 과거 profile/지침/schema/설정·예산·사용량/실패 처리는 동결한다. 새 schema·출력 용량은 실제 bytes로 측정하며 기존20,000/출력2,500을 늘리거나 source를 몰래 축약하지 않는다.
- 공유 맥락·보고 사건도 검토 전 제안이다. 원문 일치/ID 연결/재구성은 의미·진실·중립·권한 인증이 아니다. 새 필드 명칭만으로 모델 오류가 사라진다고 가정하지 않는다.

## 다음 작업과 인수

- [x] 순수 공유 맥락·보고 사건·수치 연결 계약, strict canonical 입력·위변조 거부·명시 확장·기존 프레임 재생성 구현.
- [x] 합성 자료에서 같은 항목/서로 다른 국가·지역, 범위 상속/추가, 명시 발표와 운영자, 발표 시제와 미래 행위, 목적과 조건을 독립 검증. 공유 ID/unused record/중복/없는 참조/다른 인용·합친 범위 상한도 검사.
- [ ] provider bytes/출력·실제 budget 측정 후 생성 연결. 기존 raw/판정은 유지하고 고정 사례와 새로운 미관측 실제 자료를 별도 사전 기준·호출 상한으로 평가.
- [ ] 전체 앱 예산·현재 권한·내구 실행/복구·실제 브리핑 품질을 인수한 뒤 앱 반영 판단. 설계/합성 검사/새 모델 반환/의미 인수/앱 적용을 구분.

설계 비용: 공유 맥락을 잘못 선택하면 여러 수치에 같은 오류가 전파될 수 있다. 따라서 명시 연결과 원본/확장 결과를 모두 검증·기록해야 한다. 새 계약 유지와 모델 품질/용량 인수가 추가되며, 이번 비교만으로 구조 변경의 효과를 입증하지 않았다.

## 이번 순수 구현의 확정 계약

`shared_measurement_context.py`의 별도 v1 계약만 추가한다. 앱·생성 SDK·기존 요청 bytes/기준/결과·예산·수집기·의존성은 변경하지 않는다. 새 모델 호출은 없다.

- `SharedMeasurementInput`은 contexts/events/bindings/relations를 모두 필수로 받는다. 각 상한은12/12/12/16이며 빈 전체 입력은 허용한다. ID는1~64자 ASCII 영숫자·밑줄·하이픈이며 그룹 내 고유하다. context/event는 반드시 사용되어야 하고 없는 참조는 거부한다. binding의 candidate_id는 기존 후보를 사용하며 중복 선택은 거부한다.
- `SharedMeasurementContext`는 context_id, reporting_event_id, measured_variable, target_scopes, period, value_status, logical_condition, purpose, forecast_basis, comparison_baseline을 모두 필수로 받는다. anchor 역할은 nullable이고 scopes는 최대4개다. 값 상태는 기존 observed/planned/forecast/unknown이다.
- `SharedReportingEvent`는 event_id, kind, reporting_actor, predicate, reporting_tense를 모두 필수로 받는다. attributed_report는 actor/predicate 필수, narration은 actor=null/predicate 필수, unknown은 actor/predicate=null 및 tense=unknown이다. 알려진 시제는 predicate가 필수다. 어떤 술어가 실제 보고인지는 의미 인수에 남긴다.
- `SharedNumericBinding`은 candidate_id/context_id/target_scopes/status_evidence_sentence_id를 필수로 받는다. status sentence는 nullable이며 알려진 값 상태면 필수다. 제공된 ID는 해당 후보의 수치를 포함한 현재 전체 문장이어야 하고 exact nonblank 길이1~1000이다. 서버가 그 전체 문장을 status_text로 만든다. 개별 역할 override는 없다.
- 명시 context와 event만 확장한다. 공통 scopes 뒤 개별 scopes를 붙여 최대4개다. 같은 resolved 위치 중복과 다른 인용의 모든 anchor(목적 포함)를 거부한다. 같은 유형의 다른 위치 범위는 허용한다. 원문상 목적/조건이 같은 위치라는 이유로 의미 판정을 대신하거나 자동 교정하지 않는다.
- `SharedMeasurementFrame`은 고정 profile shared-measurement-context-v1/status unreviewed, 원래 input, 파생 MeasurementScopeFrame, 입력 contexts 순서의 context별 resolved purpose(nullable)를 보존한다. purpose는 logical_condition에 복사하지 않는다. current source에서 전체 wrapper를 재구성해 비교하고 strict canonical 실제 타입·숨은 extra/subclass·위변조는 기존 패턴으로 거부한다. 오류는 source/검증 상세와 chain을 노출하지 않는다.
- 관계는 기존 ContextualFrameRelationInput 그대로 받고 기존 전체 statement/cue/참조/중복/순환 검사를 재사용한다. 모호한 관계를 버리거나 첫 위치를 고르지 않는다. 원문 일치·구조 검증은 의미/진실/중립/권한 승인이 아니다.

### Task 1 — 순수 계약과 회귀 검사

- [x] 새 모듈과 합성 테스트만 추가하여 위 계약을 구현한다. 기존 모듈/fixture/SDK는 수정하지 않는다. 같은 항목·서로 다른 지역, 공통+개별 범위, 보고자/행위자·보고 시제/미래 행위, 목적/조건을 구분하는 합성 사례와 직접 관계 재사용을 검증한다. 각 상한·빈 입력·중복/없는/unused 참조·cross quote·exact 문장 상태·canonical 우회/위변조·오류 비노출을 독립 검사한다. 적절한 RED→GREEN과 focused/agents lint·typecheck를 기록한다.

## 구현·검증 기록

`build_shared_measurement_frame` / `validate_shared_measurement_frame`은 원래 입력·분리 목적·파생 프레임을 현재 원문에서 재구성한다. 별도 새 모듈/합성 테스트만 추가했고 기존413개 실행/설정 파일·wire fixture·원래 응답/판정은 변경하지 않았다. 소스 `86e42721058de43bbb3b47fd2222e13ad80e2438`의 전체6,916개(Python6,096+JavaScript820)와 lint/format/typecheck/build/OpenAPI 검사를 통과했다. 구현자 TDD 기록·별도 태스크/최종 검토를 보존한다.

모델 호출0·앱/서버/main/운영 변경0이다. 합성 사례는 정해진 연결의 원문 재현을 검사하며 AI가 그 맥락을 올바르게 선택하거나 실제 브리핑이 개선된다는 증거는 아니다. 기존 생성4회 의미0/4 및 추론 비교 반환2의 의미0/2·다른2미판정을 재판정하지 않는다. 다음은 새 provider schema의 실제 용량과 미관측 자료 의미 품질을 별도 상한으로 인수하는 것이다.

최종 검토의 경미한 상한 테스트 지적은 테스트 전용 `d6b3e93`에서 보강했다. 네 필드 각각 strict schema의 정확 too_long 위치/종류를 검사하고, 메모리에서 상한만 제거한 대조4/4가 실패함을 확인했다. 생산 코드는 `86e4272`와 동일하며 최종 테스트249개·Ruff/형식 검사를 별도로 통과했다. 전체6,916개 결과는 상한 보강 전 테스트를 포함한 `86e4272`의 실행이며 보강 후 전체를 다시 실행한 것으로 표시하지 않는다.
