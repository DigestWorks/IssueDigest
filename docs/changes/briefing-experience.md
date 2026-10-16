# B2C 브리핑 경험 · 첫 실제 연결

2026-10-16. 사용자가 B2C 인터뷰와 연결 시안을 승인하고 구현 진행을 요청했다. 기준: [제품 경험 인터뷰](../research/product-experience-interview.md). 기존 OpenSpec root=null이므로 기존 문서 + SDD/TDD/독립 검토를 사용한다. 이 작업은 승인된 사용자 경험의 첫 실제 앱 연결이며 전체 B2C 서비스 완료가 아니다.

## Global Constraints

- B2C가 제품 목표다. 두 사람은 초기 검증 참여자이며 고객 범위가 아니다. React Router/React/TS, FastAPI/Python, PostgreSQL/pgvector, PydanticAI/DBOS, 기존 CanvasBundle 계약을 유지한다.
- main 병합·운영 공개 배포는 D013에 따라 유예한다. 기존 개인 개발 HTTPS 적용은 승인 범위다. 기존 OAuth 초대·세션·공간 권한·same-origin·API no-store 경계를 유지한다. 비공개 자료·질문·기존 조사를 익명에게 공개하지 않는다.
- UI만으로 없는 최근 이슈·여론조사·추천·개인 북마크·알림·공유 기능을 꾸미지 않는다. 공개 브리핑 게시 저장소는 아직 없으므로 비회원 홈은 질문 입력과 정직한 공개 준비 상태를 제공한다. 로그인 후 기존 실제 자료·조사 API로 이어진다.
- 실제 AI 결과만 표시한다. 원문 인용 존재를 사실 검증/주장 지지/찬반으로 분류하지 않는다. 현재 모델 해석은 해석으로, 원문 인용은 원문으로 표시한다. 생성 중 먼저 읽는 것은 현재 run에 선택한 원문의 정확 인용이며 AI 부분 답변이나 AI의 실제 검색 이력이라고 주장하지 않는다. 모델 부분 결과 스트리밍은 후속이다.
- 기존 질문·선택·요청 멱등성·상태 재조회·취소·결과 자동 저장/재열람·실패/불명확 요청의 재확인·현재 권한 재검증을 유지한다. 입력 1..1500자·선택 1..3개, 기존 예산/동시 실행/단일 모델 호출 한도를 바꾸지 않는다. 로그인 복원이나 자료 미리보기 GET으로 모델을 호출하지 않는다.
- API/도메인/DB/워커 계약·의존성은 이번 작업에서 바꾸지 않는다. 실제 모델/DB/SSH·비밀값은 controller만 다룬다. 실제 사용자 세션을 발급·대신 사용하지 않는다. 테스트 자료는 합성 전용이며 실제 DB를 테스트/reset/restore하지 않는다.
- 승인 시안의 차분한 브리핑·명확한 읽기 위계·정돈된 타이포·절제된 녹색/중립색·휴대폰 우선을 구현한다. 큰 마케팅 배너·그라데이션·카드/배지/기술 설명 반복·내부 UUID를 이름으로 쓰지 않는다. 320/390px에서 가로 넘침 없이 주요 조작 44px·키보드/포커스·줄바꿈·로딩/오류/빈 상태를 제공한다.
- Sites 탭과 사용자 브라우저를 열거나 이동하지 않는다. QA는 독립 브라우저에서 한다. Draft PR과 저장소 문서로 기록한다.

## 첫 연결 범위와 후속 경계

이번: 질문 우선 홈·로그인 전 초안 보존·편집 가능한 로그인 후 복원, 자료 선택을 보조 기능으로 내리기, 기존 자료에서 명시적인 관련 후보를 제안하기, 실제 인용 선열람·정돈된 완료 브리핑·근거 drawer·모바일 비교, 기존 저장된 조사 재열람이다.

후속: 공개 게시/공유용 불변 브리핑 저장소와 공개 허용 데이터 선별, 개인 소유 이슈/관심 기록·변경 감지/알림함, 실제 주목도·개인화 알고리즘, 검증 완료 AI 모듈의 점진적 전달. 첫 공개 이슈 범위·외부 웹 탐색·초기 AI 이용 정책은 인터뷰 답변 대기다. 현 개발 자료 12건은 공개 브리핑 12개나 최근 인기 이슈가 아니다. 공유된 기존 조사 기록을 개인 비공개 저장처럼 부르지 않는다.

## Task 1 · 질문 우선 진입·로그인 초안·앱 셸

구현 범위: apps/web/app/routes/home.tsx, routes/login.tsx, root.tsx, styles.css, 새로운 guest-question.ts, 관련 web 테스트, ResearchDesk의 선택적인 initialQuestion prop/초기 복원 연결만. research.tsx의 나머지 조사 로직·research.css·packages/ui는 Task2가 맡는다. 필요하면 guest-question 테스트는 현재 Vitest web glob에 맞춰 .test.tsx로 둔다.

요구사항:
- 기존 홈의 ‘작업 공간’ 중심 큰 문구·진단·UUID 이름을 제거한다. 브랜드와 ‘홈 / 저장한 조사 / 자료’의 정돈된 메뉴, 질문 우선 읽기 구조를 구성한다. 승인된 모바일 시안의 타이포·여백·절제된 녹색을 실제 반응형 앱에 적용한다. 기존 protected 자료 검색·목록·근거 링크 도구는 보조 위치에서 계속 사용할 수 있다. 로그인/상태 확인/실패/회원권 없음/다중 공간 선택은 명확히 구분한다.
- 비회원(확인된401)의 홈에서 질문을 입력하고 ‘로그인하고 질문 이어가기’로 /login으로 이동한다. 가짜 공개 이슈 목록이나 protected API 자료를 비회원에게 읽히지 않는다. 공개 브리핑은 아직 준비 중임을 짧게 표시하고 신규 가입이 가능한 것처럼 안내하지 않는다. 현재 Google 초대 제약은 로그인 안내에서 짧게 설명한다. 네트워크 오류를 비회원 확정으로 처리하지 않는다.
- guest-question.ts에 writeGuestQuestionDraft(question): boolean, readGuestQuestionDraft(): string|null, consumeGuestQuestionDraft(): string|null, clearGuestQuestionDraft(): void를 제공한다. 전용 sessionStorage 키 하나만 쓴다. 값은 version=1/question/createdAt의 작은 JSON, 유효 기간 30분, 최대 질문1500자·빈/공백 거부, raw 저장값 상한12000자, 유한 시각/현재보다 미래인 값 거부. 잘못된/만료된 값은 전용 키만 제거한다. SSR/스토리지 거부·손상에서는 throw하지 않는다. 이메일·토큰·세션·workspace/run ID는 저장하지 않고 URL/console에 질문을 넣지 않는다. localStorage나 storage.clear()를 사용하지 않는다.
- 저장은 익명 질문의 명시적인 이어가기 조작에만 한다. OAuth 페이지 전체 왕복 뒤 홈의 현재 유효 회원권이 확인됐을 때 새 조사에 초안을 한 번 소비해 ResearchDesk initialQuestion으로 전달한다. run URL/저장된 조사 진입 때 그 조사에 초안을 섞지 않는다. 로그인 화면에서도 유효 초안을 미리 보여주며 OAuth POST/start/state 등의 기존 보안을 유지한다. 실패/취소로 돌아온 경우 초안은 유효 기간 내 보존한다. 성공한 logout에서는 전용 guest 초안과 기존 로그인 초안을 지운다.
- 로그인 후 초안은 편집·확인하여 명시 제출한다. 복원이나 effect/새로고침으로 자동 유료 실행을 만들지 않는다. 이전 로그인 사용자/공간의 in-memory 초안을 다른 사용자에게 노출하지 않는다. Task1에서 ResearchDesk에 optional initialQuestion을 추가하되 기존 동작을 유지하고 새 조사일 때만 초기 값으로 쓴다. Task2도 이 prop을 유지한다.
- 의미 있는 TDD: 불량/만료/미래/overlong JSON·스토리지 거부·다른 키 보존·consume once·로그인 실패 보존·로그아웃 정리·401에서 질문→로그인 미리보기·인증 후 새 조사 초기값·기존 run 섞지 않음·복원시 submitResearch=0을 검증한다. 기존 테스트 문구는 실제 바뀐 사용자 동작에 맞추되 검증 강도를 낮추지 않는다. focused RED→GREEN 후 JS 전체/타입/린트/빌드를 Task1 완료 전 한 번 수행하고 report에 명령/수/경고를 기록한다.

참고: docs/research/product-experience-interview.md, apps/web의 기존 routes/home.tsx·login.tsx·research-drafts.tsx·research.tsx. 시각 참고는 로컬 /home/xinics/.codex/visualizations/2026/10/07/01a115a7-2dad-7dc3-b12a-1e87ac646492/issuedigest-consumer-journey.html (가상 자료·로직을 제품에 복사하지 않는다). frontend-design 스킬을 읽고 B2C 브리핑의 실제 앱 스타일로 구현한다. API/서버/비밀값/배포는 다루지 않는다.

## Task 2 · 실제 브리핑·원문 선열람·근거 drawer

구현 범위: apps/web/app/research.tsx/research.css, 새로운 research-evidence.tsx·research-selection.ts·research-briefing.tsx 등 책임별 작은 모듈이 필요한 경우, evidence/reader.tsx의 재사용 가능한 SavedEvidence export(기존 route 동작 유지), packages/ui/src/CanvasView.tsx·modules.tsx·styles.css와 관련 tests. Task1 홈·초안 인터페이스와 스타일 토큰을 사용하며 API·도메인·DB·워커/lock는 바꾸지 않는다.

요구사항:
- 질문/결과를 주 콘텐츠로 두고 ‘조사할 자료’는 필요할 때 여는 보조 선택으로 내린다. 초기에는 실제 연결 자료의 제목·출처/시점·근거 열람을 간결하게 보여준다. 질문 전 결과/AI 예시/인기 점수/가짜 여론을 채우지 않는다. 실제 모듈이 생성됐다는 점과 원문·AI 해석의 차이가 분명해야 한다. 단일 열 브리핑은 데스크톱에서도 지나치게 넓지 않고 보조 근거만 곁에 둔다.
- 명시 선택이 있으면 그1..3개를 그대로 사용한다. 선택이 없을 때는 기존 source catalog의 제목·의안번호·짧은 excerpt와 질문에서 명확히 겹치는 한국어/영문 단어를 제한적으로 대조해 최대3개 후보를 제안한다. exact 의안번호/제목 단어를 일반 설명보다 우선한다. 질문/제목 NFKC 정규화·대소문자 처리, 2자 미만/일반 요청어(정리/설명/알려/근거/비교/내용/주세요 등)를 제외하고 동점은 catalog 순서를 따른다. 관계 없는 첫3개 fallback을 금지한다. 일치가 없으면 질문을 유지하고 자료 선택을 요청하며 POST하지 않는다. 이 방식은 연결 자료 후보 선택이며 AI 웹 검색·전체 최신 검색으로 부르지 않는다. 제안된 범위는 화면에 보이고 사용자가 변경할 수 있다.
- Task1 initialQuestion은 새 조사에만 한 번 복원되고 전송 전 유지된다. 기존 선택 초안/후속 parent/run URL/idempotency/error 재확인/1600ms bounded polling/취소/자동 저장/GET 재열람의 동작을 보존한다. 새 제출 시 이전 run의 결과나 원문을 새 결과로 표시하지 않는다.
- 생성 중 ‘선택한 원문에서 먼저 읽기’를 구현한다. 접수된 현재 run의 snapshot_ids 중 최대3개에 대해서만 기존 getEvidence 보호 GET을 사용한다. 원문은 run/space identity로 격리·중단하고 응답 도착 순으로 보여줄 수 있다. 완료/실패/취소에 이미 읽을 수 있었던 근거를 유지하되 권한401/403·identity 변경시 원문 상태를 즉시 지운다. 원문 조회 실패는 AI run 상태를 변경하거나 가짜 문구로 보완하지 않는다. canonical Citation quote를 인용문으로 보여주고 전체 원문/위치 열기를 연결한다. 자료 제목은 검증 catalog 이름/안전한 source kind 이름이고 UUID 이름 fallback은 없다. bounded preview로 큰 인용을 정돈하되 생략을 숨기지 않는다. 이 근거를 ‘AI가 확인한 사실’ 또는 worker가 실제 사용한 전체 검색 결과로 표시하지 않는다. 원문 미리보기 GET은 모델 호출/새 조사 POST를 만들지 않는다.
- 실제 완료 result만 briefing presentation으로 렌더링한다. 현재 CanvasBundle의 prepareCanvas 검증·outcome/claim basis/canonical refs를 그대로 사용한다. 허용된 summary를 첫 핵심 정리로 강조하고 비교·변화·근거는 펼칠 수 있게 한다. summary 없는 적법 결과는 실제 첫 모듈을 보여준다. 알 수 없는/깨진 payload는 거부하고 날짜/숫자/사실/찬반/여론 모듈을 새로 추측하지 않는다. insufficient/clarification은 실제 서버 메시지로 분명히 표시한다. CanvasView에 optional presentation='briefing'을 추가한다면 default Canvas 모드의 계약과 기존 동작은 유지한다.
- briefing 비교는 320/390px에서 긴 한국어를 좁은 다열 표에 가두지 않고 주장별 읽기로 제공한다. 원문·AI 해석·출처/근거 액션은 유지한다. packages/ui의 default 비교 표는 기존 호스트/테스트와 호환되게 유지한다.
- 생성 중/완료 근거 액션은 본문을 떠나지 않는 drawer/dialog로 정확한 원문·선택 인용을 보여준다. 기존 getEvidence 검증·현재 snapshot/document/version/citation 대조를 유지한다. 가능하면 기존 SavedEvidence를 export해 preloaded data·명시 searchState/title로 재사용하며 reader route/API를 복제하지 않는다. drawer가 열린 동안 polling이 계속돼도 닫히거나 다른 자료로 바뀌지 않는다. 닫기/Escape/초점 복원·native modal·모바일 전체 너비·긴 본문 스크롤을 처리한다. run/workspace 변경시 닫고 pending lookup을 중단해 오래된 source의 늦은 응답이 새조사 drawer를 열지 못하게 한다. 동작 없는 링크/버튼은 추가하지 않는다.
- 기존 저장된 조사는 기존 실제 listResearchRuns/GET으로 다시 열고 과금하지 않는다. 개인 북마크/공유본/알림함은 이번 backend가 없으므로 빈 가짜 탭·작동하지 않는 버튼으로 붙이지 않는다. 유효하지 않은 사용자/공간/자료에 대해 로딩·실패·재시도/취소·viewer 차이를 유지한다.
- 의미 있는 TDD: 명시 선택/관련 후보/무관질문 POST0, 대기 중 정확 근거/실패·취소 후 유지/권한·run identity stale 제거, 브리핑 검증/자료 부족/비교 모바일 표현, 실제 원문 drawer 유지·정확 인용·Escape/초점 복원·run교체 중 늦은 응답 차단, 후속/저장 재열람/초안/중복 방지 회귀를 검증한다. focused RED→GREEN 후 JS 전체·lint·typecheck·build·contract:check를 완료 전 한 번 수행하고 report에 명령/수/경고를 기록한다.

참고: Task1 report와 명시 initialQuestion interface, 기존 research.tsx/reader.tsx/CanvasView·prepareCanvas, 승인된 인터뷰와 시안. 실제 AI 결과에 사실/엇갈린주장/미확인 분류가 없으면 UI가 임의 판정을 만들어 채우지 않는다. frontend-design 스킬을 읽고 승인 시각 방향을 구현한다. 실제 외부 유료 호출/서버/비밀값은 controller만 다룬다.

## Task 3 · controller 검증·개발 반영·기록

- [ ] Task1/2 독립 작업 검토·전체 변경 검토를 마치고 실제 앱/renderer build·JS 전체·Python 전체(소유 합성 PostgreSQL 포함)·lint/type/contract를 확인한다. 변경 없는 전체 검사를 무의미하게 반복하지 않는다.
- [ ] 합성 HTTP/브라우저로 guest 질문→실제 OAuth POST 준비/초안 복원→권한별 source/조사 진행/완료·drawer/저장·320/390/데스크톱을 확인한다. 실제 사용자 세션을 만들지 않는다.
- [ ] 기존 개인 개발 서버의 사용자 전용 worktree·앱·API/worker 설정·포트를 확인하고, 기존 데이터/설정/worker는 보존하면서 검증한 코드/정적 웹만 개발 HTTPS에 반영한다. DB migration/새 데이터 쓰기/실제 모델 호출은 이번 UI 검증에 필요하지 않다. 실제 키·계정/접속 메타데이터를 출력하지 않는다.
- [ ] 새 Draft PR(기준 feat/assembly-source-connector) 생성·attach, AGENTS/현재 결정·진행/작업/README 갱신, Sites 요약·과거 기록 보존. main/운영 배포는 하지 않는다. 최종에는 실제 구현·미정/후속·검증 범위를 구분한다.
