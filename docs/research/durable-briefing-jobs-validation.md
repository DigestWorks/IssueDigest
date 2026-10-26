# 최종 브리핑 작업 검증

2026-10-26. [명세](../changes/durable-briefing-jobs.md)·[진행](../planning/progress.md).

## 구현

현재 계획의 선택 원문·완료 분석을 고정하고 최종 생성의 비용 예약·상태/송신 의도·완료 결과를 저장한다. 저장 계층은 원래 계획/분석 주체의 현재 권한과 원문·영수증을 재검사하며, worker는 모든 분석과 최종 생성 결과를 SDK로 깊이 재검증한다. 완료 결과 재열람은 모델을 재호출하지 않는다. 새 파이프라인의 자료별 분석·최종 생성 접수는 공유 transaction gate 안에서 서로 활성 작업이 없는지 확인한다.

## 검증

- TDD: Task1신규79/관련167 SQL 검사 통과. 두 task는 각각 RED→GREEN과 scoped Ruff/format/mypy를 수행했다. 상세 명령·관측은 독립 검토와 비공개 작업 보고서에 보존했다.
- 새 검사109개 포함 전체10,054개(Python9,234+JS820)·lint/format/type/build/OpenAPI 통과, 실패/skip/warning0. 실행 `032980f19146589903d04a06ef0803d01d9d87cb`와 동일 runtime/tests bytes로 검증했다.
- 독립 Task1/Task2/전체 검토 C0I0M0·미해결0. 실제 SQL·모의 provider 전송에서 접수/예약·한 번 송신·저장/재열람·취소·중단/명시적 recover·현재 권한/원문·원래 입력·비용 보존을 확인했다. 자동 queue나 실서비스 적용을 인수한 것은 아니다.
- 기존498파일 중495개·이전48증거는 byte-identical이다. 허용한 기존 변경은 evidence_jobs.py의 새 schema import+submit의 activefinal guard, 기존0011 migration 검사 한 함수, 테스트 DB URL 복사 한 표현식뿐이다. AST/정확 bytes로 범위를 확인했다.
- Task1초기 관련 검사159통과/1실패는 기존0011검사가 head를0011로 가정한 문제였다. 해당 함수를 같은 연결의 실제0011 revision SQL 검사로 바꿔 과거 행/테이블/버전 stamp를 보존한 뒤 관련167개를 통과했다. 전체 head upgrade는 QA초기화에서 별도로 검증했다.
- GitHub실패 조사에서 기존 테스트가 str(engine.url)의 가려진 비밀번호를 실제 접속에 재사용함을 확인했다. 인증이 필요한 전용 QA에서 준비 후 RED1실패0.55초, 한 줄 수정 후 GREEN1통과0.54초를 확인했다. 최초 QA시작 전 연결 오류는 별도 보존하고 RED 증거로 세지 않았다. 실제 비밀번호/URL을 출력하지 않았다.

## 알림 자동화

사용자 요청으로 IssueDigest의 Verify foundation GitHub Actions를 비활성화했다. Production deployment는 active이며 독립 main push trigger를 유지한다. 개인 Gmail/GitHub 메일 설정은 바꾸지 않았다. 원격 자동 검사와 여기서 수행하는 전체 검증을 구분한다. PR 자체 알림 등 다른 알림 전체를 해제한 것은 아니다.

## 판단과 비용·한계

1. 선택 자료/완료 분석을 고정하고 최종 비용을 기존 $10/40예약 풀에서 별도로 예약한다. 추가 조회가 필요하고 긴 입력은 기존 SDK 한도에서 차단될 수 있다.
2. 송신 의도를 먼저 기록하고 불명확한 중단은 재호출하지 않는다. 중복 과금을 피하지만 중단 작업은 명시적인 상태 판단이 필요할 수 있다.
3. 기존 근거 작업에 최종 작업 동시 접수 차단을 추가한다. 새 migration 후 일관된 새 코드로 사용해야 하며 역사 ResearchRun 전체의 전역 scheduling 검증은 아니다.
4. 기존0011 migration 검사의 범위를 지정 revision으로 바꿨다. 전체 migration chain의 head 초기화 검증을 별도로 수행해야 한다.
5. 인증 테스트 URL의 비밀번호 가림 오류를 해당 한 줄로 수정했다. 비밀번호는 프로세스 안에서만 전달하며 로그로 출력하지 않는다. 사용자 요청의 불필요한 자동 검사 해제와 main 배포 유지도 기록했다.

6. 선택 사항인 DBOS 등록은 queue 연결 단계로 미뤘다. 검증되지 않은 자동 실행 경로를 추가하지 않았으며, 현재는 자동 queue·프로세스 재시작 연결이 없고 중단 확인 후 명시적 복구만 가능하다.

새 작업 저장/worker는 서버 내부 계약이다. 입력 JSON/hash나 DTO는 진위 서명/현재 권한 승인/의미 정확도 인증이 아니다. 실패·취소·권한 변경 후 관측 비용을 보존하되 실제 제공자 과금/독립 사실 검증을 인증하지 않는다. 실제 제공자 호출·운영 서버/DB 변경·main 병합·앱/기본worker 활성화0이며 전용 로컬 합성 QA만 사용했다. queue/API/UI·실제 모델 의미·개발 적용은 후속이다. PR·Sites·검증 자원 정리의 최종 인계는 이후 저장소 진행 기록을 따른다.


## 최종 인계 · 2026-10-26

[Draft PR117](https://github.com/DigestWorks/IssueDigest/pull/117), base `feat/question-briefing-generation`. 코드 `032980f`, 문서 사본 `7a711c5437a6482d4092a89bea23436d1db19a66`. 신규109/전체10,054개(Python9,234+JS820), 정적/타입/빌드/OpenAPI와 최종 독립 검토를 통과했다. 검토에서 찾은 저장 직전 권한 재확인 누락은 회귀 검사 후 수정했다.

[계획판 v139](https://lawdigest-rebuild-plan.ijaesinii.chatgpt.site/) 공개 게시 성공. source `be6eae062b51580d0043e445884548e8b16c9ba2`, saved `appgprj_6ac612dd42708191a7a0c8377be64d48~appgver_04ca01a3aa94819189851a9000fc2337`, deployment `appgdep_6adf120f5cb48191b9e0d9f9e4c200b5`. 이전 v138을 보존하고 7개 문서를 정확히 복사했다. HTML124/로컬 링크·앵커3891/공개 텍스트390개를 확인했고, 실제 비공개 자료 값72종과 접속·키 값 노출이 없다. 기존 레이아웃의 텍스트 갱신으로 브라우저 검사는 생략했다.

자체 QA 컨테이너2개와 각각의 전용 볼륨2개만 삭제하고 두 로컬 포트의 종료를 확인했다. PR 카드 첨부는 대화 첨부 개수 한도(100)로 실패했으며 위 PR 링크를 제공한다. GitHub 자동 검사는 사용자 요청대로 비활성화, main 자동 배포는 유지한다.

현재 웹 화면·운영 DB·기본 worker·main은 변경하지 않았다. 다음 완료 기준은 질문 접수→생성 중 표시→근거 연결 브리핑→재열람이며, 이를 위한 queue/API/UI 연결과 실제 품질 검증이 남아 있다.
