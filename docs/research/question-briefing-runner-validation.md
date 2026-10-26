# 질문 분석→최종 브리핑 실행 연결 검증

2026-10-26. [작업 계약](../changes/question-briefing-runner.md).

기존 자료 계획·순차 분석과 최종 생성 접수/queue를 한 caller-lived 함수로 조합했다. 반환은 생성 작업의 접수 확인이며 완료 결과나 사실 인증이 아니다. 기존 조회 API는 완료 시 현재 권한·원문·canonical 영수증을 다시 검증한다. HTTP 질문 버튼·런타임·개발 서버는 전환하지 않았다.

## 검증

실행 `daf112c393807d51fa8f79435f2b1f09a263b73f`의 신규82/전체10,208개(Python9,354+JS854)·정적/타입/빌드/OpenAPI 통과, 실패/skip/warning0. 독립 태스크/전체 검토 미해결0이다. 최초 태스크 검토의 실제 권한/원문 변경·SQL 접수 중 취소 증거 부족I1을 기존 테스트/실행 코드 변경 없이 세 검사로 보완했다. 원래79개를 포함한 전체root 검사와 보강 후82개 module검사를 별도 보존하며 최종 전체 수에는 새3개만 더했다. 단일 최종source의 root 명령 성공으로 표현하지 않는다. 집중166개는 마지막23개 unit 추가 전 결과이며 최종 신규82개와 최종 전체 결과를 별도로 보존했다.

전용 합성 SQL·native DBOS·기존 evidence/briefing 큐·모의 native OpenAI SSE를 사용했다. 같은 요청 동시 호출에서 분석1+최종1 요청만 관측했고 canonical 완료 결과 읽기/재접수에서 추가 모델/예약0이었다. 실제 원문·실제 유료 모델 의미 품질 검증이 아니다. 실제 SQL 권한 downgrade/원문 변조 뒤 최종 접수0과 실제 final INSERT 중 취소 뒤 pending/예약 유지·enqueue0을 확인했다. 최초 합성 빈 근거 fixture는 기존 linked evidence 사전 검사에 거절돼 합성 자료/응답만 바로잡았다. 기존 helper는 바꾸지 않았다.

UUID/질문/model/두 예약값/세 repository 동일 engine을 분석 접수 전에 검사한다. 긴 소수·극소수의 Decimal 곱셈 반올림에 기대지 않고 정확 센트 여부를 검사했다. 없는 자료/차단/None·raw 변조 결과·불명확 queue ACK·현재 권한 상실·예산 거부·전체 timeout과 단계별 취소·예외 원문 미노출·borrowed client·중복/완료 재접수 등을 확인했다.

호출자 태스크의 SQL은 기존 helper의 offloop 경로를 사용한다. 역사 evidence worker 내부의 동기 SQL은 이번에 바꾸지 않았으며 offloop 증거도 새 caller 태스크에 한정한다. 모의 제공자와 native 자원을 종료한 뒤 자체 고유 schema만 삭제하고 module/packageattrs/sys.path를 복원한다. 기존517개 실행/계약/테스트·이전82개 증거는 byte-identical이다. API/OpenAPI·schema·dependency·provider bytes·이전 실행version/slot·인증/예산 정책을 바꾸지 않았다. 새 UI가 없어 브라우저 검사를 반복하지 않았으며 사용자 탭 이동0이다.

## 판단과 비용

1. 분석→최종 접수/queue부터 기존 코어로 조합했다. HTTP 질문 버튼과 서버 전환은 후속이다.
2. 최종 접수도 원래 요청UUID를 사용한다. 동일 요청 회복을 위해 namespace를 유지해야 한다.
3. 자격 증명을 저장하지 않는 최대600초 caller-lived 실행이다. 프로세스 중단 후에는 같은 요청으로 재개해야 하며 독립 부모 복구를 구현한 것은 아니다.
4. 세 concrete repository 동일 engine과 두 예약을 먼저 검사한다. 조기 설정 실패를 막지만 repository wrapper는 명시 지원 전까지 거부한다.

5. 변경 없는 실행/기존79개 전체 검사를 유지하고 새SQL 경합3개만 추가검증했다. AST/byte 동일성과 별도 집계 증거가 필요하며 단일최종source root 성공을 주장하지 않는다.

실제 제공자 호출·운영 DB 변경·main 병합·기본 worker 활성화·개발 서버 반영0이다. 실제 의미 품질/운영 부하·질문 API/화면·개인/공개 게시 확장은 이번 인수 범위가 아니다. PR/Sites·QA 정리는 진행 기록의 최종 인계를 따른다.
