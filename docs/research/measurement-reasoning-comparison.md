# 동일 측정 계약의 추론 설정 제한 비교

2026-10-21. [직전 실제 결과](measurement-frame-generation-acceptance.md)의 네 자료는 수치17개를 보존했으나 범위/발표자/시제 오류로 전체 의미0/4였다. raw usage의 reasoning_tokens는0이었다. 구조를 더 바꾸기 전에 동일 계약에서 추론 설정의 영향만 살펴본다.

## 호출 전 사전 고정

- 실행 코드353217e·저장소aa0fd1f 기준, 기존 전체6,667개 검사 통과 기록을 유지한다. 이번은 연구 문서/개별 실험만 추가하며 executable/config/API/DB/UI/worker/생성 지침/schema를 바꾸지 않는다. 코드 변경이 없어 전체 회귀 검사를 중복 실행하지 않는다.
- 모델은 동일 snapshot `gpt-5.4-2026-03-05`. [공식 모델 문서](https://developers.openai.com/api/docs/models/gpt-5.4)에 none(default)/low/medium/high/xhigh 지원이 명시돼 있으며, 기존 설정은 reasoning0으로 관측됐다. 새 caller-owned model 설정 `openai_reasoning_effort=low`만 추가한다. 제품 기본 모델/설정을 바꾸지 않는다.
- 직전 네 source packet·versioned 의미 기준·이전 결과/판정을 byte-identical로 보존한다. 기존 네 건을 다시 쓰므로 독립 holdout/일반 정확도 평가가 아니다. 자료/기준/지침 변경 없이 개별 단일 관측을 비교하며 통계적 인과효과를 주장하지 않는다.
- 새 전용 실험 총최대4회·자료별1회·SDK/HTTP retries0. 과거 소진된 runner는 실행하지 않는다. 출력2,500에는 추론도 포함되며 전체20,000·timeout30초·no-store·단일 요청·known failure usage 규칙을 유지한다. 잘림/시간초과/거부가 생겨도 추가 출력·재요청/수리는 하지 않는다.
- 실제 호출 전에 mock HTTP transport로 기존 default/새 low 요청 body를 각각 구성해, reasoning 이외 전체 body가 정확히 같은지 확인한다. 실제 요청도 사전 고정된 low body와 일치해야 한다. 원문·기준·지침/prompt/raw·normalized schema·module·HTTP body hash를 고정하고 헤더/API 키는 저장하지 않는다. 합성 transport 검사와 실제 모델 호출은 분리한다.
- 사전 기준은 이전 의미 reference 그대로다. 전 자료의 측정 대상·별도 범위·명시 발표자·상태/보고 시제·기간/조건/기준·직접 관계와 수치 누락/부수 날짜를 확인한다. 원문 일치·모델 자기평가를 진실/의미 인증으로 삼지 않는다. 불충족·누락을 모두 보존한다.
- raw input/output/cache/reasoning·관측 시간과 알려진 실패 비용을 남긴다. [공식 참고 요율](https://developers.openai.com/api/docs/models/gpt-5.4)은 1M당 입력$2.50/cache$0.25/출력$15.00이며 reasoning을 output에 중복 가산하지 않는다. 실제 청구/환율은 미검증이다.
- 기준 고정 시 실제 호출0. 설정 비교 뒤에도 신규 미관측 자료·용량/내구 실행·전체 앱 인수 전 배포하지 않는다. 현재 앱/서버/main/운영은 변경하지 않는다.

## 다음 판단 기준

같은 계약에서 개선이 있으면 설정의 비용/출력 여유를 포함해 신규 자료로 재검증할 근거로 삼는다. 실패가 남으면 해당 역할/문장 맥락과 범위의 표현을 재설계한다. 어느 결과든 사후 기준 변경이나 성공까지 반복 호출은 하지 않는다.
