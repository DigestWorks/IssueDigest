# 범위·상태 근거 지침 · 제한 실제 인수

2026-10-21 KST. [새 지침 경로](../changes/scoped-contextual-generation.md)의 합성 실행 검증과 실제 선택 품질을 구분한다.

## 호출 전 고정 프로토콜

- 자료4개를 호출 전에 고정했다. A/B는 이전 실제 인용을 보존한 합성identity source packet2개와 변경 없는 원래 semantic reference다. C/D는 새로 작성한 보건 서비스/제조업 지표의 합성 문장2개다. 둘 다 개발자가 만든 자료/기준이며 독립 holdout·최신 뉴스 표본이 아니다. 실제원문/ID/raw·키는 공개하지 않는다.
- 모델은 이전과 같은 gpt-5.4-2026-03-05, 각자료1회·총신규4호출 상한이다. 이전결과 재호출/수리·기준 사후수정·다른모델 fallback·성공까지 재시도는 없다. client/SDK retry0·no-store·출력2500/총20000·30초를 유지한다. 실패·시간초과도 상한에 포함하고 unknown usage를0/무료로 계산하지 않는다.
- 바뀌는 것은 명시적인 지침/version/tool/identity와 공유 실행 구조다. 원문/catalog·숫자/역할/문맥/관계 schema grammar는 유지한다. 실제 source/SDK/instructions/prompt hash·실제 raw/normalized schema 크기와 전체 envelope를 호출 전에 보존하고, QA/독립 검토 후 실행한다. 원래 v1 provider/result 호환은 별도 사전 동결 합성 fixture로 검사한다.
- A/B는 원래 frozen 기준으로 수치/단위·대상/범위·기간·상태/보고시제·조건/전망근거/비교기준·필수 직접 포함 관계를 수동 대조한다. 다른 유효한 원문 표현을 철자 차이만으로 실패시키지 않되 실제 선택된 anchor text에 필요한 범위/의미 근거가 있어야 한다. context나 다른 역할로 잘못 선택된 짧은 text를 사후 수리하지 않는다.
- C는 지역·보건소·이동진료차량의 범위를 유지한 실적2개/계획1개와 각각 기간/상태·보고시제/명시 발표자·정비 조건을 확인한다. D는 기업규모·설비가동률의 범위를 유지한 관측2개/전망1개와 기간/상태/보고시제·발표자를 확인한다. 월 숫자는 측정값에서 제외하고, 근거 없는 포함/병렬 관계를 근접·동일 단위만으로 만들지 않는다. 각새자료의 측정값3개·역할별 기준과 source/reference hash는 private에 먼저 고정했다.
- 반환/거부와 의미 기준 충족, 숫자 수집과 전체관계·중립성·진실 검증을 따로 기록한다. source 정확위치·재구성 hash는 의미/권한/출처 서명 인증이 아니다. 작은4자료/단일 annotator 결과를 일반정확도나 지침만의 인과효과로 해석하지 않는다. A/B 저장응답과 새지침 응답은 무작위 통제 비교가 아니다. C/D에는 이전지침 비교호출을 추가하지 않는다.
- 이번은 가공 파이프라인 후보의 제한 검증이다. 앱/worker/월예약/DBOS/캐시·서버/main/운영 변경은 없다. 앱 의미/중립성·미관측 실제자료·비용/권한/복구 인수는 별도다.

## 비용 기준

[공식 모델](https://developers.openai.com/api/docs/models/gpt-5.4)과 [공식 요율](https://developers.openai.com/api/docs/pricing)을 기준으로 같은 snapshot을 사용한다. Standard·272K미만100만 토큰당 입력$2.50/캐시입력$0.25/출력$15를2026-10-21 확인한다. Raw 관측 input/cache/output로 참고 USD만 계산하고 실제청구/환율/세금/할증은 검증하지 않는다. Reasoning effort는 이전 SDK처럼 따로 지정하지 않는다.

## 상태

기준/자료4개 준비·신규모델 호출0. 구현과 v1회귀·독립검토·전체QA 후 source별실제 schema preflight에 통과한 경우에만 실행한다.
