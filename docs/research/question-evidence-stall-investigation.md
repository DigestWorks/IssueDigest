# 출력 정체 조사 · compact JSON 지시 진단

2026-10-23 한국 시간. 기반 PR104/b0430b3. [v2 실제 미완료](question-evidence-generation-v2-acceptance.md)의 공백 정체를 조사한다. 문서·제한 연구로 spec-driven-workflow의 문서 예외를 적용한다. 기존468실행·v2실제58증거와 모든 이전 원문/기준/결과/usage/소진 잠금을 동결한다. 실행 코드는 바꾸지 않아 기존9,161QA를 재사용하며 새QA·앱/worker/main 배포는 없다.

## 먼저 확인한 경계

원래 HTTP 응답의 arguments와 SDK가 받은 ToolCallPart.args는 정확히 같았다. SDK가 공백을 추가한 것은 아니다. 원래 요청은 streamFalse·strictTrue 도구1개였고 루트는 propositions/coverage 필수 object다. 실제 정규화 schema의19object/37ref·anyOf2/oneOf0에서 필수 필드·추가 속성 차단·참조 해석의 기본 위반은 없었다.

마지막 QuantityValue 구간은 expression과 metric_refs가 필수다. 별도의 합성 quantity 값에서 expression과 빈 metric_refs를 넣은 형태는 로컬 DTO 검증을 통과했다. 실제 부분 응답을 완성하거나 수리한 것이 아니며, 전체 부분 prefix의 native decoder 유효성·서비스 내부 원인을 증명하지 않는다.

[공식 JSON 모드 설명](https://developers.openai.com/api/docs/guides/structured-outputs#json-mode)은 명시적 JSON 지시가 없으면 공백이 계속 출력될 수 있음을 경고한다. 원래 instructions와 user prompt에는 대문자 JSON 지시가 없었다. 그러나 이번은 strict 도구 호출이며 JSON 모드 경고만으로 동일 원인이라고 확정할 수 없다. [지원 schema 설명](https://developers.openai.com/api/docs/guides/structured-outputs#supported-schemas)과 기본 구조도 대조했으나 공급자의 decoding 구현은 관측하지 못했다.

## 응답 전에 고정한 진단 요청

모델/전체 원문/정확 질문Q2/strict 도구/low·default/출력4,000·요청 timeout60·총20,000·storeFalse/streamFalse·재시도0을 유지한다. 원래 v2 wire의 instructions 끝에 아래203 UTF-8 bytes만 덧붙인다. 바뀌는 HTTP JSON 필드는 instructions 하나이며 전체 비교 envelope19,782·여유218로 한도 내다. 사전 native Responses MockTransport는 body 일치·timeout60·요청1회를 확인했다.

```text
 Return the function arguments as compact JSON: no indentation, blank lines, or formatting whitespace outside strings. Finish all required keys and close the JSON object; do not continue with whitespace.
```

현재 SDK는 고정 지침/영수증을 가지므로 이 진단은 caller가 만든 native Responses 요청이다. 기존 SDK 함수를 감싸 지침을 바꾼 후 v2 영수증으로 저장하지 않는다. SDK 경로를 우회한 진단이므로 동일한 라이브러리 전체 실행 경로의 인과 통제나 v2 SDK 성공을 주장하지 않는다. 실제 송신 body는 원래 body에서 지침만 바뀌었는지 다시 대조한다.

송신 전에 원문/기준/루브릭/도구/설정/body·현재 코드/스크립트·공식 문서 참고와 이 프로토콜을 hash로 고정하고 새 소진 잠금을 만든다. 실제 추가 요청은1회뿐이며 실패/미완료·공백 반복 뒤 재호출/한도 변경/모델·자료 교체/JSON repair를 하지 않는다. 원래 v1/v2 runner와 소진 namespace는 실행/수정하지 않는다. 키·헤더는 기록하지 않고 원래 응답·raw usage·송신 불확실성을 비공개 보존한다. 비용이 미관측이면0으로 채우지 않고 실제 청구서/캐시 TTL도 추정으로 확정하지 않는다.

## 사전 판정

완료/미완료·도구 수/이름/종료 상태·원래 raw usage와 허용 한도·공백 run을 각각 기록한다. 완료한 정확 도구1개와 해석 가능한 JSON만 현재 Source/질문의 기존 순수 builder/저장 validator로 재검증한다. 그 실패도 보존하고 raw 부분 결과를 수정하지 않는다. 새 generation SDK 영수증은 만들지 않는다.

순수 구조/원문 검증까지 통과한 경우에만 기존 Q2필수 P5/P9/P10의 동일 좁은 의미 루브릭으로 개발 판정한다. 다른 질문9개는 미평가로 남기고 전체12분모를 유지한다. structure가 실패하면3개도 미평가이며0/3 성공으로 부르지 않는다. explicit/equivalent/partial/not_represented/contradicted/undetermined를 구분하고 partial은 완전 보존 성공이 아니다. 공백 감소나 한 번의 완료가 원인/재현율·미관측 질문/진실·중립성/앱 품질을 인증하지 않는다. 이 비맹검 진단으로 즉시 앱에 적용하지 않는다.


## 진단 요청 결과 · 별도 감지 단계

지침만 추가한 native 요청1회는60.106초에 APITimeoutError로 종료됐다. HTTP 응답을 받지 못해 raw 상태/arguments/최종 usage는 미관측이며0으로 채우지 않는다. 송신 hook1회·소진 잠금과 정확한 요청 body는 보존했고 재호출/취소 확인·기존 SDK 성공으로 전환하지 않았다. compact 지시가 공백을 막았는지·실제로 완료됐는지·과금량/근본 원인은 이번 요청으로 확인할 수 없다.

진단 단계의 실행 코드468개는 그대로였다. 이어지는 [독립 공백 감지기](../changes/json-whitespace-guard.md)는 별도 구현/새전체QA 범위다. 연속 공백을 오프라인에서 감지하되 실제 provider streaming 취소·비용 절감/완료 보장을 주장하지 않는다. 기존 프로토콜/원래 실패·미관측 비용을 보존한다.
