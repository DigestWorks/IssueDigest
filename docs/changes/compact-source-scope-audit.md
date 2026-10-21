# 원문 중복 축소와 수치 역할 검수

2026-10-21. 상태: 두 SDK 구현·독립 검토/지적 수정 재검토·전체QA 완료. 실제 의미/앱 인수는 후속. [v2 실제 인수](../research/shared-context-v2-acceptance.md)의 범위/사업 연도 누락·운영 주체 오인·요청 용량 차단을 근거로 다음 구현 범위를 정한다. 실제 모델 호출은0이며 기존 v2/이전 계약·425개 실행/설정 파일과173개 실제 증거를 보존한다.

## 판단과 범위

정확 인용과 schema 통과만으로 역할 의미가 맞지는 않았다. 원문에 기관명이 존재한다는 사실과 그 기관이 측정 집단의 소속이라는 관계를 구분해야 한다. 대상·범위 선택을 서버가 문장 인접성으로 보충하거나 실패 응답을 고치지 않는다.

두 변경을 분리해 구현한다. 먼저 같은 원문과 후보를 덜 반복해서 전송하는 별도 생성 경로를 만든다. 다음은 생성 결과의 네 역할(측정 대상·적용 범위·기간·보고 주체)을 별도 AI 요청으로 검수하는 SDK다. 검수는 진단만 추가하고 수치/역할을 수정하지 않는다. 같은 모델 계열이면 오류가 반복될 수 있고 잘못된 경고도 생길 수 있으므로 독립 사실 검증·정답 인증으로 표시하지 않는다.

이 설계는 내부 수치 추출·검수 계약이다. 앱 API/DB/worker/UI·기본 모델·서버/main을 바꾸지 않는다. 현재 앱의 전체 조사 파이프라인이나 최종 브리핑 검수가 완성됐다는 뜻이 아니다. 이전 그룹 출력 제안은 자동 채택하지 않는다.

## 1. 원문을 한 번만 보내는 생성 경로

현재 요청은 source.citations의 전체 원문과 sentences의 문장별 원문을 모두 포함하고, 문장/후보마다 긴 citation UUID를 반복한다. 새로운 요청에서는 인용마다 `q1..q20`의 로컬 이름과 문장 목록을 보낸다.

```text
profile: compact-shared-context-v1
quotes: [{quote_id: q1, sentences: [{id: s1, text: 원문}, ...]}, ...]
candidates: [{id: n1, quote_id: q1, sentence_ids, lexical_kind,
              expression, atoms: [{number, unit}], separator, qualifiers}, ...]
eligible_status_sentence_ids, context_id_slots, reporting_event_id_slots
```

- 현재 Source에서 v2 index를 새로 만들고 문장 목록이 각 인용의0번째 글자부터 마지막 글자까지 겹침/빈틈 없이 분할하는지 검사한다. 각 text를 **구분자 없이 연결**한 값이 원래 인용과 완전히 같아야 한다. 공백·빈 문장·줄바꿈·Unicode·문장 ID/순서를 보존하며 숫자가 있는 문장만 골라 보내지 않는다. 분할이 다르면 전체 거부한다.
- 로컬 q 이름은 원래 인용 순서로 서버가 부여한다. snapshot/workspace/citation UUID·해시·provenance는 서버에 원래대로 보관하고 현재 Source와 로컬 매핑/요청을 재구성해 검증한다. 모델이 provenance를 정하거나 q 이름으로 권한을 얻지 않는다. 수치 ID·수량 표기·atom별 단위·근사/범위는 그대로다. 제목·이웃 문장에서 역할/단위를 추정하지 않는다.
- 새 tool `fill_compact_shared_context_v1`, identity `issuedigest_compact_shared_context_v1`, result profile `compact-shared-context-v1`을 둔다. 기존 역할 지침과 동적 출력 계약·12context/12event/12binding/16relation·단일 요청/무재시도·20,000/출력2,500·30초/no-store를 유지한다. 지침에는 완전한 문장 목록을 연결하는 원문 형식만 명시한다.
- 출력은 기존 SharedMeasurementFrameV2와 완전한 v2 index다. 새 generation 영수증과 원문을 검증하고 기존 v2 generation으로 profile을 바꿔 통과시키지 않는다. 기존 요청/fixture/결과는 동결한다. caller 소유 Model만 빌리고 key/client를 만들거나 닫지 않는다.

### 오프라인 용량 확인

완전한 G/H/I/J 인용의 현재 문장 분할과 후보를 사용하고, 새 형식 설명을 포함한 지침·실제 raw/normalized schema 최대 byte·framing2,048·출력2,500을 합산했다. 원문/후보를 줄이지 않았다.

| 자료 | 기존 envelope | 설계 시제품 envelope | 감소 |
| --- | --- | --- | --- |
| G | 16,948 | 16,536 | 412 |
| H | 16,471 | 16,213 | 258 |
| I | 16,550 | 16,251 | 299 |
| J | 20,692 | 18,575 | 2,117 |

J의445글자/16문장 기록·9후보는 원문 그대로 복원됐고 같은20,000 한도 안에 들어간다. 시제품은 요청 JSON/schema의 크기 확인이며 새 provider 요청·SDK 구현·의미 성공·실제 출력 충분성은 검증하지 않았다. 구현 시 byte 수는 다시 측정하며 장문 전체가 항상 수용된다고 일반화하지 않는다.

## 2. 별도 수치 역할 검수

검수 SDK는 현재 Source와 이미 검증한 generation을 입력으로 받는다. 기존 v2 또는 위 compact profile의 **정확한 concrete 타입/해당 validator**만 허용하고, 실제 nested 타입·tuple을 직렬화 전에 검사한다. 어느 생성 경로도 다시 실행하지 않는다. 검수용 Model은 caller가 별도로 명시한다.

모델에게는 같은 완전한 원문/후보와 canonical 제안의 측정 대상·범위·기간·보고 주체 및 해석에 필요한 값 상태/보고 사건을 보낸다. 선택한 scope에 수치별 `r1..r4`의 읽기 전용 슬롯을 부여한다. 입력은 원래 context+binding 범위를 순서대로 합친 정확한 projection이며 누락/추가/잘못된 형식을 자동 고치지 않는다. 원래 생성 결과·projection 해시를 보관한다.

검수 질문은 ‘이 표현이 인용에 있는가’뿐 아니라 ‘이 표현이 이 수치의 대상/범위/기간/보고 주체로 연결되는가’다. 기관의 운영·주관을 대상 집단의 소속으로 바꾸지 않고, 광역/하위 지역과 명시된 사업 연도의 누락을 확인한다. 애매하면 uncertain이며 자동 채택/상속하지 않는다.

### 모델 출력과 서버 검사

tool `audit_scope_roles_v1`, identity `issuedigest_scope_role_audit_v1`, result profile `scope-role-audit-v1`을 제안한다.

| 항목 | 고정 계약 |
| --- | --- |
| checks | 선택된 수치마다 정확1개·원래 순서·최대12개. candidate_id와 no_issue_found/issues_found/uncertain |
| issues | 최대12개. candidate_id, role(measured_entity/target_scope/period/reporting_actor), kind(missing/unsupported/uncertain), nullable scope_slot, nullable source_anchor, support_sentence_ids |
| incomplete | 더 필요한 진단이 상한을 넘으면 true. 나머지를 조용히 생략해 정상 판정하지 않음 |

- ID는 현재 후보/문장과 선택된 수치로 좁힌 strict 동적 schema다. 추가/누락/중복 check, 다른 수치/인용/잘못된 슬롯·중복 진단은 전체 거부한다. role이 target_scope가 아니면 scope_slot은null이다. missing은 슬롯null·정확한 source_anchor가 필요하다. unsupported는 실제 nonnull 필드를 가리켜야 하며 기존 target_scope라면 현재 r슬롯이 필수다. uncertain의 anchor는nullable이다.
- anchor는 기존 정확 문맥 형식(sentence_id/text/context_text)으로 해석한다. support_sentence_ids는1..20개 현재 문장의 연속·원래 순서·같은 인용이어야 하며 해당 수치의 완전한 표현과 nonnull anchor를 포함해야 한다. 이 검사는 위치/범위 검사이지 관계의 의미 인증이 아니다.
- 진단과 check가 모순되면 거부한다. missing/unsupported가 있는 수치는 issues_found, 그것 없이 uncertain 진단만 있으면 uncertain이다. 진단 없이 no_issue_found를 허용하는 것은 incomplete=false일 때뿐이다. incomplete=true에서 미완료/진단 없는 수치는 uncertain으로 남긴다.
- 서버 상태는 issues_flagged → uncertain → no_issues_flagged 순으로 보수적으로 파생한다. 선택 수치0개면 검수를 호출하지 않고 not_applicable로 구분하며 긍정 검수로 세지 않는다. 모델이 상태/profile/해시/usage/승인 여부를 정하지 않는다.
- 결과에는 원래 generation과 source/projection/prompt/instructions 해시, 검사/해석된 원문 위치·관측 usage를 보존한다. 저장 결과는 원래 generation부터 현재 Source로 재검증하고 projection·동적 schema·진단·파생 상태/합산 usage를 모두 다시 만든다. 원래 frame을 수정하거나 새 성공으로 덮지 않는다.
- no_issues_flagged는 **이 네 역할에서 AI가 문제를 찾지 못했다**는 뜻이다. 수치 후보 선택의 전체 누락, 다른 역할/최종 브리핑·진실/중립/권한을 승인하지 않는다. timeout/invalid/용량 부족/미완료/uncertain을 정상 완료로 표시하거나 검수를 생략해 앱에 적용하지 않는다. SDK 검증은 실제 요청/청구의 증명이 아니며 신뢰된 caller/내구 journal이 호출·비용을 관리한다.

### 비용·호출 한도

생성과 검수 **합산** total20,000/output2,500을 유지한다. 검수 추가 호출은 최대1회·retry/repair/fallback0·30초/no-store다. 검수는 원래 generation의 검증된 known usage에서 잔여 한도를 계산한다. 기존 생성 SDK의 관측 usage가 없거나 현재 검증에 실패하면 호출하지 않는다.

```text
remaining_total = 20,000 - generation.input_tokens - generation.output_tokens
audit_output_limit = min(1,000, 2,500 - generation.output_tokens)
audit_envelope = UTF8(prompt + instructions)
                 + max(raw_schema_bytes, normalized_schema_bytes)
                 + 2,048 + audit_output_limit
```

output 잔여가0이거나 audit_envelope가 remaining_total을 넘으면 송신0으로 실패한다. runtime의 usage 제한도 같은 잔여값을 사용하고 응답 뒤 합산을 다시 검사한다. 검수 실패 시에도 알려진 생성/검수 사용량을 보존하고, 검수 usage가 unknown이면 무료/0으로 간주하지 않는다. 원래 생성이 한도를 모두 쓰면 검수할 수 없는 비용을 명시적으로 감수한다. 자동으로 한도를 올리거나 다시 생성하지 않는다.

G/H/I의 기존 응답을 읽기 전용 projection으로 옮긴 오프라인 검수 요청 시제품은8,956/8,666/8,478 byte-envelope다(검수 출력1,000 포함). 과거 v2 실제 usage3,678/3,353/3,360을 **용량 예시로만** 차감하면 각각16,322/16,647/16,640이 남아 수용된다. 이는 아직 호출하지 않은 compact 생성의 usage가 아니며, 이중 호출 성공/비용 절감·의미 개선 증거가 아니다. J에는 생성 응답이 없어 검수 출력/용량 사례를 만들지 않았다.

전체 앱의24,000/output2,500에는 기존 planner/selector 등도 들어간다. 앱 연결 전에는 실제 이전 stage 잔여를 사용하도록 별도 내구/회계 계약을 인수해야 한다. 이 내부 두 stage 한도를 앱 한도와 별도로 더해 쓰지 않는다.

## 구현 순서와 완료 기준

1. **원문 중복 축소 SDK**: 순수 packet 재구성·새 단일 생성 경로·저장 전체 validator를 TDD로 구현한다. Unicode/공백/빈 문장·여러 인용·잘못된 로컬 매핑/타입·v1/v2 불변·용량 경계·무I/O와 mock HTTP를 확인한다. 원래 G/H/I/J 전체 요청을 재측정한다.
2. **역할 검수 SDK**: 순수 projection/진단·한도/미완료 파생 상태·별도 bounded 요청/usage 재구성을 TDD로 구현한다. 누락/불필요한 범위 추가·틀린 슬롯/인용/타입·모순/overflow·빈 선택/토큰 소진·검수 실패의 사용량과 호출0/1 경계를 확인한다. 같은 기관이 운영 주체이면서 원문에 명시된 대상 소속이기도 한 긍정 반례, 결합/개별 하위 지역 표현과 실제로 연결이 모호한 사례를 포함해 단순 기관명 금지 규칙이 되지 않도록 한다. 합성 테스트가 AI 의미 검증을 대신하지 않는다.
3. **독립 검토·전체QA**: frozen 계약·실제 증거를 보존하고 새 코드 전체 회귀/계약/빌드를 확인한다. prototype의 Pydantic schema에는 runtime cross-field guard가 구현돼 있지 않으므로 그것을 완료 증거로 재사용하지 않는다.
4. **호출 전 고정 의미 인수**: 원래 G는 긍정 사례, H/I 원래 실패 응답은 검수의 부정 사례로 보존한다. 누락뿐 아니라 잘못된 추가와 정상 응답을 틀렸다고 하는 오탐도 판정한다. 새 사전 선정 자료·복잡한 전체 문단/충분한 출력을 별도 포함한다. 기존 소진 runner/기준/응답을 재사용 실행하지 않는다. 새 상한·원문·gold·설정을 호출 전에 고정하며 자동 재시도/수리는 없다.
5. **앱 인수**: 의미 품질과 검수의 누락/오탐·합산 비용/내구 복구·현재 권한·최종 브리핑을 확인한 뒤 개발 적용을 판단한다. 모델 요청2회가 늘리는 비용/지연과 남는 오류를 기록하며 main/운영은 별도로 둔다.

현재는 위 설계와 용량 시제품만 완료했다. 새 SDK·실제 의미/보안·앱 적용 완료로 표시하지 않는다.


## SDK 구현 검증 · 진행 중

[구현 작업](compact-source-scope-audit-implementation.md)을 별도 브랜치에서 진행한다. 원문 중복 축소 SDK `fece872`는 새 profile/tool/영수증·현재 원문의 전체 재구성·기존 bounded runtime을 연결했다. 합성49개·순서 회귀967개와 Ruff/format/mypy를 통과했고 태스크 독립 검토 지적0이다. 전체QA 및 검수 SDK 완료의 증거와는 구분한다.

실제 SDK의 오프라인 생성 envelope는 G16,548/H16,225/I16,263/J18,587이다. 위 설계 시제품보다 각각12byte 크며 원래 J20,692보다2,105byte 작다. 현재 G/H/I/J의 전체 문장·공백·빈 문장·후보/단위·근사와 기존 v2 index를 그대로 재구성했다. 새 provider 호출은0이며 의미 개선이나 출력 충분성을 관측한 결과가 아니다. 기존425실행/설정 파일과173실제 증거의 SHA를 다시 확인했다.


### 역할 검수 구현

`aca165a`에 `scope_audit_contract.py`와 `scope_role_audit.py`를 추가했다. 원래 두 concrete generation만 받아 네 역할의 projection·원문 위치/연속 지원 문장·수치별 scope 슬롯·누락/추가/불확실 진단을 재구성한다. 보고서와 runtime 영수증을 분리하고, 검사 결과·원래 generation·source/projection/prompt/instructions 해시·단계별/합산 usage를 보존한다. 새 보고서/profile 식별자가 누락된 저장값도 거부한다.

생성의 관측 사용량에서 잔여 total/output을 차감한 단일 borrowed Model 요청이다. 라이브러리가 응답 사용량 초과 시 메시지를 보존하기 전에 예외를 내는 경계를 위해, 요청을 추가하지 않는 얇은 observer가 반환된 응답의 usage만 먼저 관측한다. caller 설정/클라이언트 lifecycle은 유지한다. 송신 전 실패·송신 가능하나 usage불명·관측된 초과 사용량을 구분하고 알려지지 않은 검수 사용량을0으로 합산하지 않는다. 선택0이면 추가 요청0/검수 usage없음/not_applicable이며, 선택이 있으면 두 stage의 requests 합계2를 검사한다.

합성101개와 최종 관련 순서 회귀1,068개, Ruff/format/mypy를 통과했다. 개별 검사는 기관 운영과 대상 소속 구분·여러 하위 지역/사업 연도 누락·명시 기관 소속 양성/연결 모호성·실제 mock HTTP·호출0/1·합산 예산 경계를 다룬다. 합성 데이터의 구조 검사이며 AI 의미 성공은 아니다. 관련 검사 중 후보/evidence reload와 중복 모듈을 섞은 탐색 순서는531실패/1,936통과였고, 처음 `NumericCandidateIndex` 클래스 정체성 충돌에서 시작했다. 이는 성공 결과에서 제외한다. 전체 실패의 old-only 기준선 재실행은 하지 않았고 기존 파일/guard는 바꾸지 않았다. 최종 관련 순서는 새 audit+compact→selection reload→기존 생성/role→shared/v2다. 자연 순서 전체QA는 별도로 확인한다.

실제 SDK로 기존 G/H/I generation을 읽기 전용 검수 요청으로 구성한 envelope는10,001/9,703/9,514다. 과거 v2 관측량을 차감한 잔여16,322/16,647/16,640과 검수 출력1,000에 수용됐다. 위 설계 시제품8,956/8,666/8,478과 구분한다. 과거 generation 사용량은 새 compact 생성 사용량이 아니며 새로운 검수 결과/비용·의미 개선을 관측하지 않았다. J에는 원래 생성 결과가 없어 검수 사례를 만들지 않았다.


### 최종 검토의 저장값 누락 지적·수정

전체 변경 검토에서 Important1건을 확인했다. compact 생성의 저장 dict와, 검수 보고서/runtime dict 안의 원래 generation에서 `profile`/`status`가 빠져도 기본값으로 복원됐다. 실행 `9e5f784`에서 새 세 저장값 경계의 파싱/union 기본값 적용 전에 원래 marker의 존재를 검사한다. 실제 모델 생성자의 기본값과 기존 frozen v2/runtime은 유지한다.

누락10사례의 새 검사는 수정 전8실패였고 나머지2사례는 이미 거부됐다(선택 실행에는 기존 누락 후보 검사1개도 포함). 수정 후 누락선택11개·영향 세 모듈160개·관련 순서1,078개와 Ruff/format/mypy를 통과했다. 수정 전 `aca165a`의 진행 중 전체QA는 중단/별도 보존하고 성공으로 세지 않는다. 해당 QA 컨테이너만 제거한 뒤 별도 소유 QA에서 최종 코드의 전체 검사를 새로 시작했다. 지적 수정 재검토/최종 전체QA 영수증은 아래에 기록한다.

최종 코드에서도 전체 원문 오프라인 용량과 기존425파일/173증거의 동일성을 다시 확인했으며 새 실제 모델 요청은 없다. 검토의 범위 제외는 실제 모델 의미/오탐·미탐/장문 출력, 실제 청구/인증된 usage와 caller 내부 전송, 서비스 보안/권한/내구 복구/최종 브리핑·앱, controller 소유 private 자료·실패 순서 전체 원인 분류다. 구조 SDK 검토를 해당 인수로 해석하지 않는다.


### 최종 전체 검사·인계

실행 코드 `9e5f784755cc7b70f4174c0f89b31c3102bdfbd1`에서 Python6,546+JS820=**7,366개**·Ruff/format390/mypy150·ESLint/TypeScript·SPA build·OpenAPI drift를 모두 통과했다. 실패/skip/warning0이다. 최종 Important1건 수정 후 한정 재검토는 C0/I0/M0이며 두 태스크 검토/원래 전체 검토/수정 전 중단QA·탐색 순서 실패를 그대로 보존한다. 자연 전체 순서가 통과했지만 탐색531실패의 모든 원인을 별도 기준선으로 분류했다고 주장하지 않는다.

기존425실행/설정 파일과173실제 증거·전체 원문/후보 재구성·새 요청 용량·문서 링크/비공개값 제외를 확인했다. 수정 전/후의 소유 QA컨테이너2개만 각각 대조 후 제거했다. 이 계획의 작업/검토 기록은 private로 보존하고 해당 SDD만 정리하며 다른 자원과 개발 앱은 유지한다. 새 실제 요청0, main 병합/서버/앱 배포0이다. PR/Sites 게시 영수증은 저장소 진행 기록을 따른다.
