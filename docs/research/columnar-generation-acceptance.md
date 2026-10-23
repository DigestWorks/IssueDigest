# 전체 원문 columnar 생성 · 실제 모델 인수

2026-10-23 한국 시간. [생성 SDK](../changes/columnar-role-generation.md)의 실제 모델 검증이다. 문서·제한 연구로 spec-driven-workflow의 문서 예외를 적용한다. 기존462개 non-Markdown 실행/검사/설정 파일과 원래 실제642/설계121/이전12+10+33/codec75/SDK66증거를 동결한다. 공개 실행 코드는 바꾸지 않으므로 전체8,696개 검증을 재사용하고 새 전체QA·서버자원·앱/main 배포를 만들지 않는다.

## 응답 전에 고정한 범위

이전 SDK에서 입력 한도로 막혔던 [공식 정책뉴스 원문](https://www.korea.kr/news/policyNewsView.do?newsId=148973453)1건만 새 columnar 생성 SDK로 호출한다. 기존 본문17문단/1,306문자·25후보/52문장과 개발 질문4개/필요 명제12개를 복사하되 bytes/hash를 유지한다. 원문·기준·기존 실패/점수·비용을 수정하지 않고 이전 runner나 소진 namespace는 재실행하지 않는다. 과거 balanced preflight 차단/DO-NOT-CALL은 유지하며 이번은 새 SDK·별도 소진 잠금의 첫 실제 요청이다.

모델은 앞선 실제 평가와 같은 `gpt-6.1-sol`/reasoning low/standard(default)다. 새 SDK의 실제 지침·도구·입력·전체20,000/출력1,800·30초/no-store·요청1회/SDK와 transport 재시도0을 유지한다. 송신 전에 원문·기준·SDK 코드·prompt/지침/schema/settings를 hash로 고정하고 요청 잠금을 먼저 만든다. 네트워크·형식·미완료·의미 실패 모두 재호출/수리·원문 축약·한도 상향·다른 모델/자료 교체 없이 종료한다. 요청·원래 HTTP 응답·SDK 반환/거부·known usage·송신 불확실성을 비공개 보존한다. provider 비밀값/헤더는 기록하지 않는다.

## 분모와 판단 규칙

1. 요청/HTTP 응답/모델 완료/strict SDK 반환을 분리한다. 실패 응답의 tool JSON이 읽혀도 성공으로 변환하지 않는다. SDK가 거부하면 거부와 known usage를 유지하고 실제 추출12명제의 성공은 세지 않는다.
2. 기존 기준12명제(수치8/10anchor·비수치4)와 질문별 required 상태는 바꾸지 않는다. 수치8/8 후보 검출은 기존 관측이며 새 의미 성공이 아니다. raw 응답을 보기 전에 필요한 요소를 보존한 별도 per-unit 판정 지침을 고정한다.
3. 선택된 수치 binding과 그에 직접 연결된 context/event/scope/change/relation만 의미 보존 근거로 읽는다. 입력 원문·전체 candidate index·넓은 위치찾기 context에 문자가 있다는 것만으로 보존 성공으로 세지 않는다. entity/범위·단위/열린 경계·각각/이내·신청과 선정·계획/관측·상대 날짜를 혼합하지 않는다. 임의 합산이나 연도/월 추정을 허용하지 않는다.
4. numeric 역할 생성기는 전체 질문 답변기가 아니다. 특히 기존8개 수치 명제 중 기한/준공 연도3개는 시점 정보이며 이 SDK는 부수 날짜를 제외하라는 지침이 있다. 비수치4개도 독립 출력 칸이 없다. 이 제한을 응답 전에 명시하지만 전체12개 분모에서 빼거나 일반 질문 답변 완료로 승격하지 않는다. 각 단위에 선택된 수치/직접 역할 표현 유무와 explicit/equivalent/partial/not_represented/contradicted/undetermined를 기록하고 시간/비수치의 미표현은 제품 경로 공백으로 따로 남긴다. `partial`은 완전 보존 성공이 아니다.
5. 결과는 단일 개발 원문·개발 질문의 비맹검 분석이다. 사람 정답·holdout·통계적 정확도·중립성·일반 B2C 품질 인증이 아니다. 독립 에이전트 검토도 사람 adjudication을 대신하지 않는다. 원문이 주장한다는 확인과 세계의 진실을 구분한다.

## 비용과 다음 판단

실제 raw input/output/cached/reasoning 등 노출된 usage를 보존하고 SDK KnownUsage와 대조한다. [공식 API 가격](https://developers.openai.com/api/docs/pricing)의 standard 단가(1M당 입력$2/출력$10, cached input$0.10)는 참고 계산일 뿐 청구서/환율/월 총비용이 아니다. 캐시 쓰기·기타 요금과 노출되지 않은 비용을 임의0으로 채우지 않는다. 사용량이 알려지지 않은 송신 실패를 무료 성공으로 표시하지 않는다.

현재는 응답 전 기준이다. 실제 결과와 남은 수정/인수는 뒤에 추가하며 최초 기준 커밋/비공개 freeze를 보존한다. 앱/worker 연결은 실제 완료·의미/범위·예산/권한/복구 인수 후 별도로 판단한다.
