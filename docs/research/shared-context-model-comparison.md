# 공유 맥락 · 동일 계약 모델 제한 비교

2026-10-21. [직전 실제4회](shared-context-acceptance.md)는 반환1의 의미0/1·거부3미판정이었다. 구조를 바꾸기 전 동일 계약의 모델 선택 영향을 제한적으로 확인한다.

## 사전 고정

- 실행54afcd9·SDK/지침/schema·원래 source4/의미 기준·20,000/출력2,500·low·timeout30/no-store·단일 요청/agent·HTTP retries0을 보존한다. 앱·제품 기본 모델·417실행/설정 파일은 변경하지 않는다. 연구 문서 변경에 전체7,019검사를 중복 실행하지 않는다.
- 새 caller model만 `gpt-6.1-sol`로 바꾼다. [공식 모델 문서](https://developers.openai.com/api/docs/models/gpt-6.1-sol)에 Responses tool calling과 low 지원을 확인했다. 문서에 별도 날짜 snapshot이 없어 이 ID의 제공 시점 관측으로 기록하며 영구 불변 snapshot이라고 주장하지 않는다.
- 동일4자료/기준과 이전 응답·판정을 byte-identical로 보존한다. 모두 이미 사용한 개발 사례이며 새 미관측/독립 holdout·일반 모델 순위/인과 효과 평가가 아니다. source/prompt/schema/지침·HTTP body를 호출 전에 고정하고 mock4건에서 model 필드 외 body가 이전과 동일한지 검사한다. 실제 body도 사전 고정 body와 같아야 한다.
- 별도 namespace에서 최대4회·자료별1회만 시도하며 과거 소진된 runner는 실행하지 않는다. 실패/출력 부족/응답 미확인에도 모델 대체·출력 증액·재시도/수리·관계 삭제를 하지 않는다. 사전 고정 당시 실제0회이며 결과는 별도로 추가한다.
- 기존 기준의 필수 수치/별도 범위·발표자·상태/보고 시제·기간·조건/목적/근거/직접 관계를 원문으로 수동 대조한다. 반환 의미 충족/미충족과 거부·미확인의 의미 미판정, 전체 시도 게이트 분모를 분리한다. 단일 평가자이며 사후 기준 변경·AI 자기평가를 정답으로 사용하지 않는다.
- raw usage/cache writes/reasoning/서비스 tier·관측 시간과 실패 비용을 보존한다. [공식 standard 요율](https://developers.openai.com/api/docs/pricing)은 1M당 입력$2/cache$0.10/cache write$2.50/출력$10이다. reasoning은 output 포함이며 중복 가산하지 않는다. 확인된 tier/usage 범위에서만 참고 비용을 계산하고 미확인 비용은0원이 아니다. 청구/환율은 미검증이다.
- 실제 응답·원문/ID·자세한 reference는 private에만 보존한다. 정확 구조/위치·반환은 의미/진실·중립·권한 인증이 아니다. 모델 비교가 개선돼도 미관측 실제 의미·충분한 출력과 전체 앱 비용/권한/내구 실행 인수 전 앱 반영하지 않는다. 그룹 출력은 여전히 미구현 제안이다.
