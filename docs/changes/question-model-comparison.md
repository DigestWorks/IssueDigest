# 근거 생성의 모델 단일 변수 비교

2026-10-27. [비교 진단](../research/question-format-diagnostics.md) 뒤 첫 실험은 기존v5 분석의 원문·질문·지침·출력 schema·전송 설정을 유지하고 model만 gpt-6.1-sol에서 gpt-6-astra로 바꾼다. 생성 코드의 새 버전·DB migration·서비스 전환은 추가하지 않는다. OpenSpec root=null인 기존 프로젝트에서 private 도구 TDD·독립 검토를 적용한다.

## 후보 선정과 경계

[공식 모델 문서](https://developers.openai.com/api/docs/models/gpt-6-astra)는 Responses API·streaming·function calling·structured outputs·low 추론 지원을 명시한다. 이는 이번 작업의 호환성 후보 근거이며 품질 우위를 증명하지 않는다. API 키의 실제 모델 접근 여부는 별도 읽기 요청으로 확인한다. 현재 공개 식별자에 날짜 snapshot이 없으므로 요청/응답 model ID를 보존하고 서로 다른 시점의 관측을 완전한 동시 대조로 취급하지 않는다.

[공식 가격](https://developers.openai.com/api/docs/pricing)의 Standard short-context 입력10/출력50달러(백만token당), cache write30m12.50/12h25달러를 확인했다. 실제 요청은 기존대로 cache write를 명시하지 않는다. 예약1달러는 입력20,000을 모두12h cache write 단가로 계산한0.50달러와 출력4,000의0.20달러를 합친0.70달러의 보수 상한을 포함한다. 새 과금 옵션이 관측되면 전송하지 않으며 실제 비용은 terminal usage와 당시 단가를 분리해 기록한다. 예약을 청구액으로 표시하지 않는다.

## 불변 조건

- 원래 한 자료/질문·사전 의미 기준·SDKv5/core/공백256·입력20,000/출력4,000/60초 유지.
- 송신 body를 원래v5 요청과 비교해 model 한 필드 외 차이가 있으면 네트워크 전 거부. tool 이름/strict/schema·input/지침·추론low·storefalse/backgroundfalse/streamtrue·service default 등 모두 유지.
- 분석 요청 최대1, HTTP/native/모델 retries0. 실패/불명확 송신 후 재호출하지 않음. 최종 브리핑 요청은 이번 범위0.
- private 고정 코드/입력/의존성과 검토한 사양, 전체 native 모의/cleanup attestation·독립 검토·정확 freeze 승인 후 실제1시도. 전체 supervisor90초 kill/reap.
- 원래 기록을 읽기 전용 보존하고 새 시도/송신 의도·예약·raw body/닫힘·usage·실패를 별도 보존. 비밀값/원문은 공개 문서에 넣지 않음.
- 모의/구조 수용·필수3단위/나머지9·실제 최종 저장·앱 인수를 구분. 성공 한 번으로 안정성·일반 품질·모델 채택을 판정하지 않음.

## 작업

- [x] 공식 호환성/가격·해당 키의 읽기 접근 확인.
- [x] 모델 외 body 차이 무송신 거부·freeze/cleanup/시도 gate·제한 native 모의 TDD.
- [x] 독립 코드/사전 검토·동결/모의·승인 후 제한 분석1회·무재시도.
- [x] 별도 결과/내용 검토: 분석1 수용·필수3단위3/3 AI 개발판정·나머지9 미평가·최종/앱0.
- [x] 결과 기록/Draft PR133. 모델 채택/안정성 인증은 후속.
- [x] Sitesv156 기록 게시.

## 적용 경계

실제 결과가 좋아도 자동 모델 전환·최종 생성·공동DB·개발 앱/main/운영·Actions 변경은 하지 않는다. 다음 단계는 이번 분석 결과에 따라 최종 경로 검증 또는 다른 단일 변수 비교를 정한다. 기존 실패를 수정하거나 이번 결과와 합쳐 성공으로 만들지 않는다.
