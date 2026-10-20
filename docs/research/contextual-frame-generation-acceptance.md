# 문맥 프레임 생성 · 제한 실제 인수

2026-10-20. [문맥 참조 SDK](../changes/contextual-frame-generation.md)의 합성 검사와 실제 모델의 문맥/역할 선택 품질을 구분한다.

## 호출 전 고정 프로토콜

- 이전 [모델 비교](frame-model-comparison.md)의 source packet2개와 동일한 semantic reference 원본을 사용한다. packet은 실제 인용을 보존한 합성 identity이며 기존 DB snapshot 자체라고 주장하지 않는다. 기준/case hash는 호출 전에 private에 동결하고 원래 gold/raw/실패를 바꾸지 않는다.
- 모델은 이전 비교군과 같은 고정 snapshot gpt-5.4-2026-03-05다. 운영 기본 모델 선정이나 최신 전체 모델 우열 비교가 아니다. 새 계약/지침/schema와 샘플링 차이가 있어 이전 응답과의 무작위 통제 실험으로 해석하지 않는다.
- 각 자료1회·총 신규 최대2호출, SDK/client retry0·no-store·출력2500/총20000·30초. 후보/문장catalog·전체 원문과 실제 raw/normalized schema·지침의 envelope를 호출 전에 고정한다. 경로 전용 입력/profile과 문맥anchor만 새 계약을 따르며 인위적 응답수리·fallback·성공까지 재호출은 없다.
- source 지문/문맥·짧은span·후보·대상/발표자·기간/상태/보고시제·조건/전망근거/비교기준·직접 포함관계와 수준/증감 관계를 사전 기준에 대조한다. 반환/거부와 수동 의미 기준충족을 따로 센다. 기준에 다른 유효 원문이 있으면 철자차이만으로 실패시키지 않되 그 수동 해석과 한계를 기록한다. source일치만으로 진실/중립성/권한/독립인간검토 인증을 하지 않는다.
- 기존 두 실패를 아는 단일 annotator의 개발 표본이다. 미관측/독립 평가나 일반 정확도가 아니다. 재사용 source이며 새 모델 응답을 받는 것이지 기존 raw를 새 계약으로 고쳐 수용하는 실험이 아니다. 호출 전 기준의 사후 수정은 금지한다.
- raw 응답·usage/attempt·전체원문·reference는 private 보존한다. 실패 known_usage는 raw와 대조하고 unknown을 무료/0으로 보고하지 않는다. 토큰과 경과 시간은 관측치이며 금액/실제 청구는 별도다. 앱/월예약/DBOS/캐시·main/운영은 변경하지 않는다.

## 상태

사전 프로토콜/기준 준비. 신규모델 호출0. SDK 구현과 독립 검토 후 실제 source/schema preflight가 통과할 때만 실행한다. 실패나 미수행도 그대로 기록한다.

## 비용 기준·공식 근거

[공식 모델 문서](https://developers.openai.com/api/docs/models/gpt-5.4)의 고정 snapshot과 [공식 요율](https://developers.openai.com/api/docs/pricing)을2026-10-20 확인했다. Standard·272K미만 기준100만 토큰당 입력$2.50/캐시입력$0.25/출력$15다. Raw 관측 input/cache/output로 참고 USD만 계산하며 실제 청구/환율/세금·지역/서비스티어 할증은 검증하지 않는다. reasoning effort는 이전 SDK처럼 별도로 지정하지 않는다. 모델/샘플링·서버기본 차이까지 통제한 품질 우열 실험은 아니다.
