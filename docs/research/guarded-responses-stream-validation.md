# 스트림 중단·사용량 관측 검증

2026-10-25 한국 시간. [실행 계약](../changes/guarded-responses-stream.md)에 따른 별도 native Responses transport다. 이번 단계의 제공자 호출은0회이며 기존 실제 미완료·타임아웃/최종 사용량 미관측 기록과 소진 잠금은 유지한다.

## 검증 구분

합성 HTTP/SSE는 설치된 OpenAI SDK를 실제 통과시키되 MockTransport에서 응답한다. 요청 body/strict schema/전체 입력·단일 호출·HTTP 응답 닫힘·borrowed client 유지와 상태 전이를 검증한다. 실제 제공자의 계산 취소·과금·생성 품질·네트워크 종료 시간을 측정한 것이 아니다.

기존 v1/v2의 미완료 arguments는 읽기 전용으로 재생한다. 공백 감지 실패에서 terminal usage까지 drain하지 않으므로 관측 사용량이 없을 수 있으며 이를0/무료로 변환하지 않는다. v1의 공백 정체 없는 미완료는 terminal incomplete와 usage를 보존해야 한다. 합성 분할은 실제 SSE chunk나 타이밍을 복원하지 않는다.

현재 구현·독립 검토·fresh 전체 검사와 재생은 진행 중이다. 기존 SDK·영수증/원문/질문·앱/worker/main 활성화는 변경하지 않는다. 검증 결과가 나온 후 정확한 건수·한계를 추가한다.

## 오프라인 재생 관측

새 transport의 native SDK+모의 SSE로 기존 v1/v2 인자를 각각 전체·1자·2자·혼합 분할했다.8요청 모두 HTTP 응답이 닫혔고 caller 소유 client는 열린 상태였다. v2는 네 경우 모두 whitespace 실패·terminal 미독해·known_usage None/usage_complete False이며 비용0으로 해석하지 않는다. v1은 네 경우 모두 미완료 실패·known_usage2,318/1,800·requests1/usage_complete True다. 후자는 최종 사용량 수신이지 생성 완료가 아니다.

provider 요청0·원래 응답 SHA 불변이며, 실제 SSE 타이밍·제공자 계산 중단·과금 절감·모델 의미 성공은 검증하지 않았다. 재생 도구의 최초 입력 준비 오류는 tuple Source 구성으로 수정한 후 실행했으며 제공자 호출은 어느 경우에도 없었다. 새 실행 코드는 변경하지 않았다.

## 독립 검토 보완

초기 검토에서 native/호출자 정리의 close 대기가 operation timer 밖에서 멈출 수 있는 문제와 JSON 지수 overflow가 inf 결과로 수용되는 경계를 재현했다. 기존 전체QA는 성공으로 세지 않고 중단/기록한 뒤 새 close 정책·finite 숫자 회귀를 보완한다. 취소에 협조하는 acquired HTTP body 정리는 별도1초 제한을 공유하며, native SDK 내부 정리도 같은 경계를 통과한다. 정리 취소를 무시하는 임의 closer·응답을 얻기 전의 borrowed SDK 내부까지 강제 종료하는 hard SLA는 아니다.

수정 실행88c93ef·관련 합성115/정적 검사·양쪽 새 파일 strict mypy가 통과했다. 수정 후 동일한8회 모의 HTTP 재생에서도 v1 최종 usage/미완료와 v2 공백 감지/최종 usage 미관측/HTTP 닫힘을 보존했다. 실제 제공자 요청은 여전히0이며 독립 재검토·새 전체QA는 진행 중이다.
