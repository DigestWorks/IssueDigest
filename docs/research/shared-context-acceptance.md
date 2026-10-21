# 공유 맥락 생성 · 실제 제한 인수

2026-10-21. [공유 맥락 생성 SDK](../changes/shared-context-generation.md)의 실제 의미/출력 한계를 확인한다. 현재는 호출 전 사전 기준을 고정한 상태다.

## 사전 고정

- 실행 코드는54afcd9·전체7,019개 검사 통과 그대로다. 이번은 연구/문서 단위이며 기존417실행/설정 파일·생성 지침/schema/runtime/모델 기본값·앱을 변경하지 않는다. 전체 검사를 반복하지 않고 문서/링크/private 제외와 불변 hash를 확인한다.
- 기존 고정 A/B2건과 새 E/F2건, 총4자료·각1회·최대4요청 시도다. 기존 상한 소진 runner는 재실행하지 않는다. 실패/응답 미확인/잘림이 있어도 재시도·사후 수리·관계 삭제·성공까지 반복하지 않는다.
- 모델은 동일한 snapshot `gpt-5.4-2026-03-05`, caller reasoning_effort=low로 고정한다. [공식 모델 문서](https://developers.openai.com/api/docs/models/gpt-5.4)에 snapshot/low 지원을 확인했다. 최신 모델 우열·구조 변경의 인과 효과 비교가 아니며 제품 기본값은 바꾸지 않는다.
- source/quote·의미 기준·코드/지침·prompt/raw·normalized schema/실제 HTTP body hash를 호출 전에 고정한다. MockTransport4건과 실제 API를 구분한다. 실제 요청도 사전 body와 같아야 하며 키/헤더를 저장하지 않는다. 전체20,000/출력2,500·timeout30/no-store·agent/HTTP retry0과 기존 nullable failure usage를 유지한다. 추론 출력도2,500 안이며 부족해도 상한을 늘리지 않는다.
- 기존 A/B의 source·원래 의미 기준·판정은 그대로 보존한다. 새 E/F는 [행정안전부 인파 관리 기사](https://www.korea.kr/news/policyNewsView.do?newsId=148973954)·[관계부처 주택 공급 기사](https://www.korea.kr/news/policyNewsView.do?newsId=148970016)의 첫3개 연속 본문 p를 원문 확인 후 사전 선택했다. 사진/캡션 제외·HTML text/단락 경계 추출을 기록했고, 전체 기사가 아니라 고정 발췌다. 직전 용량 검증과 다른 신규 자료를 추가했지만 개발자가 확인·annotate한 소표본이며 독립 holdout/다매체/정치 중립성 평가가 아니다.
- 필수 수치/부수 날짜·명칭 제외, 측정 대상과 범위·발표자, 관측/계획과 보고 시제, 기간·조건/목적/전망 근거·직접 관계를 사전에 정한다. 새로운 사례는 지역 관리 계획/기관 참석 실적 분리와 주택 공급 계획/과거 발표·열린 하한을 본다. 임의 슬롯ID/맥락 분할 자체가 아니라 원문상 의미와 필수 정보의 보존을 평가한다.
- 정확 위치/전체 문장·구조와 의미를 구분한다. 반환된 프레임만 의미 충족/미충족으로 판단하며 전체 거부/응답 미확인은 의미 미판정으로 남긴다. 시도 전체 인수 게이트의 분모와 반환 프레임 의미 분모를 따로 기록한다. 동등하고 충분한 원문 표현은 허용하되 기준을 사후에 바꾸지 않는다.
- 단일 평가자가 원문/참조와 결과를 수동 대조한다. AI 자기평가를 정답으로 쓰지 않는다. source·실제 응답/ID·자세한 anchor/reference는 private에만 보존하며 긴 발췌를 공개 문서/fixture에 복사하지 않는다.
- raw input/output/cache/reasoning·관측 시간을 기록한다. [공식 요율](https://developers.openai.com/api/docs/pricing)은 standard 1M당 입력$2.50/cache$0.25/출력$15.00이며 actual service tier·usage가 확인된 범위에서만 참고 계산한다. 추론은 output에 포함하므로 중복 가산하지 않는다. 비용 미확인은0원이 아니며 실제 청구/환율은 미검증이다.

아직 실제 호출0이며 결과는 아래에 별도 추가한다. 실제 품질이 확인돼도 전체 앱 예산·현재 권한·내구 실행/복구·최종 브리핑 인수와 main/운영 유예는 별개다.
