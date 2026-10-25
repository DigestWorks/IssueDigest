# 스트림 중단·사용량 관측 검증

2026-10-25 한국 시간. [실행 계약](../changes/guarded-responses-stream.md)에 따른 별도 native Responses transport다. 이번 단계의 제공자 호출은0회이며 기존 실제 미완료·타임아웃/최종 사용량 미관측 기록과 소진 잠금은 유지한다.

## 검증 구분

합성 HTTP/SSE는 설치된 OpenAI SDK를 실제 통과시키되 MockTransport에서 응답한다. 요청 body/strict schema/전체 입력·단일 호출·HTTP 응답 닫힘·borrowed client 유지와 상태 전이를 검증한다. 실제 제공자의 계산 취소·과금·생성 품질·네트워크 종료 시간을 측정한 것이 아니다.

기존 v1/v2의 미완료 arguments는 읽기 전용으로 재생한다. 공백 감지 실패에서 terminal usage까지 drain하지 않으므로 관측 사용량이 없을 수 있으며 이를0/무료로 변환하지 않는다. v1의 공백 정체 없는 미완료는 terminal incomplete와 usage를 보존해야 한다. 합성 분할은 실제 SSE chunk나 타이밍을 복원하지 않는다.

현재 구현·독립 검토·fresh 전체 검사와 재생은 진행 중이다. 기존 SDK·영수증/원문/질문·앱/worker/main 활성화는 변경하지 않는다. 검증 결과가 나온 후 정확한 건수·한계를 추가한다.
