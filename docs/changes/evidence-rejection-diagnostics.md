# 근거 생성 거부 단계 진단

2026-10-27. 실제 분석 응답은 usage 완료 뒤 output으로 거부됐지만 파싱/DTO/원문/영수증 중 구체 분기를 관측하지 못했다. 검증을 완화하지 않고 다음 실패를 진단할 유한한 단계 코드를 추가한다. OpenSpec root=null이라 init 없이 기존 spec-driven-workflow의 구현·독립 검토·검증을 따른다.

## 계약

- 내부 GuardedResponsesError/Cancelled의 관측에 optional diagnostic_stage를 추가한다. 기존 reason·message·usage·may_have_started·usage_complete·stream_closed는 보존한다. stage는 고정 allowlist/None만 허용하며 질문·원문·모델 출력·field path·예외 message/traceback/키·식별자를 담지 않는다.
- transport는 입력/stream/JSON 파싱/JSON 값/DTO schema/출력 객체 무결성 단계를 구분한다. source SDK는 native 영수증/usage/출력 타입/원문 무결성/근거 계약/생성 영수증 계약을 구분하고 하위 오류의 stage를 보존한다. None인 기존 오류와 취소도 호환한다.
- evidence worker는 고정 이벤트 이름·검증한 stage만 서버 로그에 남긴다. 알 수 없거나 변조된 stage는 unavailable로 대체한다. exc_info·원 예외 message·식별자·본문을 기록하지 않는다. 로깅 실패는 원래 오류·SQL 상태/usage 기록을 바꾸지 않는다.
- 모델·제공자 request body/tool/schema/prompt/instructions·한도·재시도·유료 namespace·영속 reason/status·DB/API/공개 DTO·성공 영수증은 변경하지 않는다. raw 응답 저장/자동 보정/추가 호출은 만들지 않는다. 과거 실제 실패를 새 stage로 재분류하거나 원래 시도를 재실행하지 않는다.

## 구현 작업

- [x] Task1: transport/source/worker 내부 진단과 회귀·누출/handler 실패 검사를 TDD로 구현한다. 한 호출의 연속 경계라 단일 태스크로 다룬다.
- [x] 독립 태스크 검토·Python/JS 전체10,350개 분할 검증·린트/타입/빌드/OpenAPI와 최종 독립 검토.
- [x] 기존 제공자 bytes/이전 증거 보존·문서/계획판·Draft PR124·전용 QA 정리.
- [x] 전체 검증 후 개인 개발 API만 같은 설정으로 전환하고 외부 응답·단일 실행기·설정 보존을 확인한다. 화면/프록시/DB 구조/수집기는 바꾸지 않는다.

추가 실제 모델 요청과 개발 서버 교체는 이 진단 구현의 성공으로 간주하지 않으며 이번 구현 검증에는 필요하지 않다. 실제 원인·의미 품질은 미확인 상태를 유지한다.
