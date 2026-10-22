# 수치별 역할 연결 · 실제 제한 평가

2026-10-22 한국 시간. [검증된 SDK](../changes/role-link-sdk.md)의 실제 호출 전 사전 기준이다. 연구·문서 작업으로 spec-driven-workflow의 문서 예외를 적용하며 production 코드/SDD/DB/서버 자원을 만들지 않는다. 기존456코드·562실제/45+59설계 증거와 원래 추출/gold/실패 비용을 보존한다. 코드가 같아 전체8,409QA 증거를 재사용한다. 앱/main/API/UI/worker/default model 변경은 없다.

## 입력·기준과 분모

저장한 G/H/I/J/K 전체 원문과 exact RoleAliasGenerationV2를 읽기 전용으로 재사용한다. 새 생성0회, 후보47개와 같은quote 관계271쌍을 전부 유지한다(자료별15/16/6/192/42쌍). 관계 행렬은 기존 검수의 누락 진단과 업무가 다르므로 기존2탐지/6미탐의 동등한 대체·직접 정확도 개선으로 표시하지 않는다. 원래 추출 점수는 비분쟁1/4·G사람 재판정 유보 그대로다.

응답 전에 원문 대조로 부분 관계 기준을 비공개 고정한다. 단일 에이전트의 이미 본 개발 자료이며 독립 사람 정답·holdout·일반 정확도/중립성 평가가 아니다. 후보 밖 recall/중요도/전체 역할 진실을 인증하지 않는다. G는 역할 논쟁이 남아 있어 내용 점수 분모에서 제외하되5건 완료/비용·전체 관계 상태에는 포함한다. 모든 관계의 classified/unrelated/uncertain/unreviewed 및 미완료·구조 거부를 기록한다.

주요8그룹은 이전 오류와 관련한 새 **관계 적용**을 확인한다. H 국비 수치에 세 하위 지역 각각의 measurement_scope, I 두 수치의 교육 운영 주체에 operator 포함/measurement_scope 제외, J 선정 수·재언급·지원액·국비 상한·지방비 하한 각각에 두 선정 지역 measurement_scope를 요구한다. 총15개 원문 후보×수치 관계이며 전체 원문과 후보 ID/조건을 사전에 고정한다. 그룹은 모든 지정 관계/조건을 만족해야 충족이다. '?'/'_'/'-'와 잘못된 역할, SDK 거부를 구분하고 미판정은 성공으로 세지 않는다. 원래 proposal에서 중요 정보가 누락됐다는 진단/수리는 하지 않는다.

별도9개 대조그룹19관계는 J 신청수에 선정 두 지역을 전체 집계 범위로 적용하지 않는지, K 특정직 수·비율에 세 소속을 적용하는지/일반직 세 수치에는 적용하지 않는지, K 두 증감의 전년도 비교를 baseline으로 읽고 측정 시점으로 오인하지 않는지 확인한다. 양성/금지 역할 조건만 고정한 **부분 gold**이므로 다른 역할 전체의 정답/오탐률로 부르지 않는다. 17그룹/34관계 밖의 결과와 추가 역할은 명시적으로 미채점이며 관측 요약만 남긴다. 예기치 않은 양성은 새 확정 정답으로 사후 편입하지 않는다.

## 호출·예산·고정

G→H→I→J→K, 단계별1회·실패 포함 최대5유료 요청. 기존 generation/검수 재실행·retry/repair/fallback/대체0. 별도배타적 시도/송신표시, source/generation/기준/코드/지침/schema/prompt/예상 HTTP body 해시를 고정한다. 실제 송신 전에5건 모의 body를 만들고 실제body와 일치시킨다. 소진/불확실 송신은 재요청하지 않는다. preflight 차단은 무호출로 남기고 다음 자료로 대체하지 않는다. 이미 송신했는데 알려진 사용량이 없으면 이후 단계를 중단하고0비용으로 계산하지 않는다.

GPT-6.1 Sol·Responses·low/default·30초/no-store, caller OpenAI client max_retries0. SDK의 단일 Model.request와 caller HTTP retry 정책을 함께 제한한다. 잔여total=20,000−기존generation(input+output), output=min(1,100,2,500−기존generation output). 전체 원문/prompt/지침·max(raw/normalized schema)+framing2,048+outputreserve를 사전검사한다. cap상향·후보/원문 절단·미완료 복구로 성공시키지 않는다. 정상 추론 메타데이터+단일 도구 응답은 허용하되 provider 미완료/다중 도구/불필요 텍스트·잘못된 행렬은 거부하고 raw/known usage를 보존한다.

[OpenAI 공식 모델/요율](https://developers.openai.com/api/docs/models/gpt-6.1-sol)과 [pricing](https://developers.openai.com/api/docs/pricing)을2026-10-22 확인했다. Standard 1M input$2/cached$0.10/30분write$2.50/output$10, reasoning은output에 포함한다. cached/write를input에서 분리해 중복 계산하지 않는다. 5×20,000을 전부output으로 간주한 보수 상한$1이며 기존 월10만 원 한도를 확대하지 않는다. 이번 관계 분류 비용과 기존 generation/검수 비용을 분리하고 실제 청구/환율은 미검증으로 둔다.

## 결과

호출 전이다. 사전 protocol commit·private criteria·freeze와 각 body를 고정한 뒤 실행하고 원래 실패/기준을 응답에 맞춰 바꾸지 않는다. 요청·provider 완료·SDK 반환·부분 관계 조건 충족·불확실/미검토·알려진 비용을 별도로 기록한다.
