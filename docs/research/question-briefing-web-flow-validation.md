# 질문 제출·브리핑 화면 연결 검증

2026-10-26. [작업 계약](../changes/question-briefing-web-flow.md).

로그인한 새 질문을 실제 분석·최종 접수 코어에 연결했다. SSE는 접수 뒤 실제 분석 단계와 heartbeat, 최종 접수 결과만 전달하며 완료 결과는 기존 현재 권한/원문/canonical 영수증 조회로 읽는다. 예시·가짜 진행률·자동 유료 재시도·이전 모델 fallback은 없다. 기존 공개 브리핑·Google 세션·legacy 결과 URL/기록은 보존한다.

## 검증과 한계

실행 `ee48938db67db710bd81c952e28705d447411ef0`의 단일 전체 명령에서 Python9,412+JS915=전체10,327개, 정적/타입/빌드/OpenAPI 통과. 실패/skip/warning0. 독립 태스크와 전체 검토 미해결0. API 엄격한 본문/세션/Origin·SSE 오류/heartbeat/disconnect, SQL 현재 requester/원래 writer/모든 원문·목록50제한/UUID순서·정확 DTO를 검사했다. 목록은 날짜 없는 안정된 제한이며 최신순으로 표시하지 않는다.

native PostgreSQL/DBOS와 모의 OpenAI SSE를 사용해 HTTP 제출→분석→최종 생성→기존 상세 읽기와 목록을 확인했다. 동시 동일 요청의 실제 모의 제공자 호출은 분석1+최종1이며 재접수 증가0이다. API loop가 worker SQL에 막히지 않는 점, provider 생성/사용/종료 동일 loop, 등록 후 launch/recovery, foreign singleton/기동 실패 cleanup·미구성 schema fail-closed를 검증했다. 취소된 concurrent Future와 별도인 worker 완료 확인으로 async finalizer 종료를 기다린다. 이미 접수된 내구 작업·예약은 취소 시 자동 반환/재호출하지 않는다.

브라우저는 별도 헤드리스 세션의 합성 API 응답으로1280/390px·두테마·즉시 busy·중복 제출 방지·최종 화면 이동·저장 목록, 가로넘침/콘솔오류0·단일 POST를 확인했다. 사용자의 열린 탭 이동0이다. bounded SSE/UTF8/terminal/UUID/timeout/abort, actor+workspace pending 보존·명시 같은 UUID retry·접근 상실 시 정리를 검사했다. 기존 Home 통합 검사의 새 질문 trigger/fixture만 새 전송으로 맞췄고 legacy/auth/Back/원문 drawer·초점 보존을 유지했다. 독립 ResearchDesk/reader/header와 잠금 의존성은 변경하지 않았다.

기존 비문서519파일 중499파일과 이전 증거58개는 byte-identical이다. 승인20파일 수정은 API wiring/contract, 목록, 소유 runtime/등록 분리, launcher 및 새 질문 Home 통합/검사에 한정한다. 기존 저장소 메서드와 briefing 중첩 call/workflow AST는 동일하다. 기존 shared draft owner는 pending 정리도 같은 권한 경계에 연결한다. 기존 runner 테스트는 폐기된 고정 QA 포트만 명시 환경변수로 교체했으며 모든 테스트 함수/검증 AST는 그대로다.

## 실행 환경

기본 configured factory에는 worker가 없다. 두 명시적 개발 flag를 켜면 root `scripts.question_briefing_app:create_question_briefing_app`을 선택한다. root만 API와 worker를 조합한다. 별도 기본 DBOS schema `issuedigest_question_briefing`, appversion `question-briefing-http-v1`, 기존 server model/예약·단일 executor lock을 유지한다. 런타임은 schema migration을 자동 실행하지 않는다. pinned DBOS singleton의 좁은 read-only 존재 검사와 별도 cleanup executor가 SDK lifecycle에 의존하므로 업그레이드 때 재검증한다.

실제 제공자 호출·개발/운영 변경·main 병합0. 새 UI가 실제 개발 사이트에 적용된 것은 아니다. 스키마 사전 준비와 기존 단일 executor 안전한 전환 뒤 실제 모델 의미 품질을 확인해야 한다. synthetic 통과는 사실 인증·자율 부모 복구·운영 부하 인수가 아니다.

## 판단과 비용

1. Use a bounded POST SSE connection with heartbeat and explicit same-request retry — analysis may exceed proxy idle timeout before final job exists — disconnected callers may leave durable children and must explicitly resume; no independent parent recovery claim.
2. Compose API and worker only at the root entrypoint through a shared service protocol — avoid app-to-app imports and duplicated model logic — deployment must select the new paired factory after dedicated DBOS schema provisioning.
3. Own a separate worker event-loop thread and close its provider on that loop — frozen evidence SQL is synchronous and async clients bind their loop — lifecycle/thread/lease/recovery tests add complexity but keep API responsive.
4. Keep legacy result URLs/history and add bounded current briefing metadata listing without invented dates — current job schema has no creation timestamp — up to50 stable UUID-ordered entries are not presented as a chronological feed.
5. Extract pure briefing registration and preregister workflow names before DBOS launch — queued jobs may recover during startup — preserve exact existing workflow/step body and names with AST evidence.
6. Run runtime and UI implementation concurrently with disjoint ownership and a shared commit lock — both depend only on the accepted Task1 protocol and have no shared code edits — any unexpected integration overlap requires serial resolution.
7. Update only Home integration expectations that invoke the replaced new-question transport — the real interaction now uses explicit SSE POST rather than legacy mount GET/polling — retain legacy/auth assertions and review named test deltas for accidental weakening.
8. Replace the prior runner test helper's hardcoded retired QA port with the explicit configured test database URL — whole-suite failure at570passed proved it ignored QA25607 — one additional old-test helper change is allowed, with every test assertion/runtime unchanged and full regression rerun.
9. Integrate pending erasure in the existing shared workspace draft owner — exact-original and legacy reader denial already invalidate that owner — this adds one approved old provider change and couples both stores to the same authority boundary, requiring cross-surface regression coverage.
