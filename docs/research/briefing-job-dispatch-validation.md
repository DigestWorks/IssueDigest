# 최종 브리핑 실행 큐 검증

2026-10-26 KST. [명세](../changes/briefing-job-dispatch.md).

접수된 최종 생성 작업을 현재 권한·원문으로 재확인한 뒤 DBOS에 전달한다. 명시적 worker 등록은 기존 최종 생성·저장 코어를 호출하며 결과 본문을 workflow journal에 복제하지 않는다. 전달 응답은 큐 접수 확인이며 AI 생성 완료를 뜻하지 않는다.

신규17개 포함 전체10,071개(Python9,251+JS820), lint/format/type/build/OpenAPI 통과. 실패·skip·warning0. 검증한 코드 `466655ea8bf93f74ef15f7871fc9a06106fe8173`와 실행/test bytes가 같다. 독립 태스크·전체 검토의 미해결 지적0이다. 기존504개 실행 파일·이전52개 증거는 byte-identical이다.

실제 전용 SQL과 native DBOS·AsyncOpenAI MockTransport SSE로 현재 권한/원문·중복 전달·같은 workflow ID·모호한 접수 응답·취소/완료 상태·완료 재열람·사용량과 예약 보존·offloop SQL을 확인했다. 외부 유료 제공자 호출은 하지 않았다. 실제 질문의 의미 품질이나 운영 복구를 인증한 것은 아니다. 독립 DBOS schema와 전용 로컬 QA만 사용하며 기존 registry와 서비스는 변경하지 않는다.

판단과 비용:

1. 접수된 최종 작업만 전달한다. apps의 worker 구현을 agents에서 가져오지 않지만, 질문 API가 사전 검증·접수 후 전달하는 연결은 남는다.
2. 근거 분석의 유료 실행 큐를 공유한다. 동시 유료 실행 증가는 막되, 활성화할 worker는 같은 app_version에 두 workflow를 함께 등록해야 한다.
3. 실행 중인 SQL 작업을 자동으로 중단 처리하지 않는다. 중복 과금 가능성을 줄이지만 불명확한 중단은 명시적 판단·복구가 필요하다.
4. 기존 큐 설정은 never_update로 유지한다. 충돌을 조용히 덮어쓰지 않으며, 설정이 다르면 운영자가 명시적으로 조정해야 한다.

현재 질문 API·웹 화면·기본 worker·개발 서버·운영 DB·main을 변경하지 않았다. 브라우저를 새로 열거나 이동하지 않는다. 최종 PR·Sites 게시·자원 정리 기록은 진행 문서를 따른다.


## 최종 인계 · 2026-10-26

[Draft PR118](https://github.com/DigestWorks/IssueDigest/pull/118), base `feat/durable-briefing-jobs`. 코드 `466655e`, 계획판 문서 사본 `1df6de21026dab9b0f3a4169f13c1843749d7838`. 신규17/전체10,071개(Python9,251+JS820), 정적/타입/빌드/OpenAPI·독립 태스크/전체 검토 통과. 기존 실행504파일·이전52증거 보존.

[계획판 v140](https://lawdigest-rebuild-plan.ijaesinii.chatgpt.site/) public 게시 성공. source `50d5323e772fad04350b05357bd001f0776f5246`, saved `appgprj_6ac612dd42708191a7a0c8377be64d48~appgver_7cd0cf0a55f08191844e1fe844425e71`, deployment `appgdep_6adf1bd6c4c88191aab79a8c93b030e4`. 이전 v139 보존·7문서 정확 복사, HTML125/로컬 링크·앵커3965/공개 텍스트395개를 검사했다. 실제 비공개 자료 값72종·접속/키 값은 노출하지 않았다. 기존 레이아웃의 텍스트 갱신이므로 브라우저 검사는 생략했다. 사용자 탭을 열거나 이동하지 않았다.

전용 QA 컨테이너1개와 소유 볼륨1개만 제거하고 해당 포트 종료를 확인했다. PR 카드 첨부는 대화 첨부100개 한도로 실패했으며 직접 링크를 제공한다. 실제 제공자·운영 DB·main·기본 worker·개발 서버 변경0이다. 질문 API·생성 중 표시·브리핑/근거/재열람 화면과 실제 개발 적용은 여전히 남아 있다. 초기 정리 전 스타일 검사 실패 로그는 보존했고, 정리 후 최종 전체 검사는 모두 통과했다.
