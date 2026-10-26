# 질문별 브리핑 최종 생성 SDK 검증

2026-10-26. [명세](../changes/question-briefing-generation.md)·[진행](../planning/progress.md).

새2파일로 검증된 자료별 분석·전체 원문 인용을 단일 native Responses stream 요청에 연결하고 결과를 기존 브리핑 조합기로 검증했다. 기존496실행·이전44증거는 hash로 보존한다. 기존 SDK/transport/모델/prompt/workflow·DB/API/UI/config/export/fixture를 바꾸지 않았다.

## 검증 결과

- TDD missing-module RED 후 신규 집중59개 통과. Scoped Ruff/format/mypy 통과.
- 새 전체9,945개(Python9,125+JS820)·lint/format/type/build/OpenAPI 통과. 실패/skip/warning0.
- 독립 태스크/전체 검토 C0I0M0·미해결0. 실행 커밋 `a383a296e328a4dc045e17dcf3837f99898c1867`와 같은 runtime/tests bytes로 검증했다.
- 실제 AsyncOpenAI/MockTransport/SSE로 단일 요청·wire schema/지침/입력·전송 옵션과 결과 조합/전체 재검증을 확인했다. 원문·명제·조건을 자르지 않으며 실제 한도를 호출 전에 검사한다.
- 사용량/합계·현재 원문/영수증 drift·잘못된 참조/날짜·불확실성·원래 타입/누락/추가/unchecked copy·JSON 왕복 및 실패의 관측 비용/중단 경계를 검사했다. 기존 transport 상세 검증은 재사용한다.
- 이전에 수용된 실제 분석 영수증1자료/3명제를 읽기 전용으로 사전 검사했다. 최종 envelope16,390/20,000으로 입력은 수용했고 원래3아티팩트 bytes를 보존했다. 제공자 호출0이며 실제 생성 완료/의미 성공은 아니다.

## 한도와 비용

기존 native transport의20,000 전체 envelope/출력4,000/60초 제한을 유지한다. UTF-8 bytes·실제 strict tool schema·provider framing을 사전 계산하며 긴 원문·복수 자료는 차단될 수 있다. 조용한 절단·자료 제외·상한 상승·자동 수리/재시도는 없다. 실제 모델의 입력 수용·완료·의미 정확도를 확인한 것은 아니다.

최종 request usage와 자료별 분석을 합산한 aggregate usage를 구분한다. 실패에서는 관측된 최종 usage/송신 가능성·usage 완료/stream 닫힘 상태를 보존하며 미관측 비용을0으로 단정하지 않는다. 입력 자료별 비용은 원래 영수증에 남아 있다. 이는 토큰 사용량 기록이며 금전 예약/현재 권한 승인/내구 실행/과금 영수증이 아니다. 서비스 caller는 호출 전에 별도로 접수·비용 예약·권한 검사를 해야 한다.

## 범위·판단

1. 전체 입력을 기존 한도 내에서 보존했다. 근거 손실을 숨기지 않지만 긴 입력/다자료 차단이 생길 수 있다.
2. SDK를 최종 내구 접수/예약과 분리했다. 현재 앱 활성화는 없으며 실제 모델 의미·영속 저장/API/UI·개발 적용이 남는다.

모든 브리핑은 미검토다. 원문 참조·재구성은 의미/독립 사실·인증된 역사적 진위 검사가 아니다. 같은 제안과 파생 문장을 함께 바꾸는 행위는 향후 authoritative 저장 계층에서 막아야 한다. 실제 제공자 호출·운영 서버/DB 변경·main 병합·앱/기본worker 활성화0이다. QA는 전용 로컬 합성 환경만 사용했다. PR·Sites/정리 최종 인계는 저장소 진행 기록을 따른다.
