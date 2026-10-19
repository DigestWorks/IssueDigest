# IssueDigest 작업 지침

이 파일은 저장소 전체에 적용된다. 사람과 에이전트는 같은 요구사항·결정·작업 기록을 기준으로 협업한다.

## 시작할 때

1. `README.md`와 `docs/README.md`에서 구조·협업 방법을 확인한다.
2. `docs/planning/progress.md`와 `docs/planning/tasks.md`에서 현재 상태·작업을 확인한다.
3. 해당 작업의 `requirements-design.md`, `decisions.md`, `implementation-plan.md`를 읽는다.
4. 작업 전 Git 상태를 확인하고 기존 변경·진행 중인 작업을 보존한다.

## 확정된 범위

- 서비스 IssueDigest, 조직 DigestWorks. 풀스택 모노레포로 개발한다.
- 프론트 React Router·React·TypeScript, 백엔드 Python·FastAPI, 그래프 Neo4j.
- 질문 중심 B2C 브리핑이 제품이다. 질문→짧은 브리핑→필요한 비교·변화·반응·근거로 이어간다. 최신 제품 방향은 D016·D017·D019·D020·D021·D022와 `docs/research/product-experience-interview.md`를 따른다.
- 현재 초대 자료·브리핑 기록은 공유 초기 검증 범위다. 개인 소유·공개 피드로 이름만 바꾸지 않는다. 팀 공간/자료 관리·법안 전용 시작 행동을 기본 제품으로 제시하지 않는다. 내부 workspace 계약·첫 승인 맥락·현재 권한·원문/검색/생성 코어는 유지한다. 사용자에게 자료/범위 선택·카탈로그·출처 ID 입력을 요구하지 않는다. 질문과 선택적인 이전 브리핑 맥락만 제출하고 서버가 실제 접근 가능한 색인에서 근거를 찾는다. 정확 인용으로 원문을 연다(D019).
- 비회원은 별도 공개 게시 저장소의 명시 검토된 불변 복사본만 읽는다(D020). 기존 private 자료/질문/실행·세션·멤버십을 공개로 바꾸지 않는다. 최초 출처는 정확한 공식 policyNewsView URL·텍스트 SHA·발행일·출처/저작자·공공누리1 조건을 개별 검토한 텍스트이며 사진/외부 저작물은 제외한다. 전체 계획 hash 검토 후 신뢰 CLI/서버만 게시·철회하고 브라우저 쓰기·자동 게시를 만들지 않는다.
- 공개 읽기·인용·재열람은 세션/모델/DBOS/예산을 만들지 않는다. 질문은 표제/직접 입력만 일반 홈 초안으로 이어가고 public/private run을 부모로 섞지 않는다. 정확 인용·focus/visible/재진입에서 고정 공개 버전을 확인하고404는 화면/원문을 정리한다. 일시 오류는 철회로 단정하지 않는다. 개인 관심 이슈/변화·알림·사용자 공유·실제 추천·AI 부분 결과·전체 B2C 품질은 후속이다. 개인 개발 적용과 main/운영 유예를 구분한다.
- 개발·초기 운영비 상한은 월10만 원이다. B2C 이용량·수익 정책은 별도 설계한다. 세션은 최대14일·7일 미사용 만료이며 현재 권한 검사·교체/폐기·안전한 쿠키를 보존한다.
- 기존 데이터·파이프라인은 선별 재사용한다. 과거 와이어프레임은 별도 저장소의 기록이다.
- 기준 DB PostgreSQL, 벡터 검색 pgvector, 에이전트 PydanticAI, 내구 실행 DBOS를 사용한다(D011). 엔진 선택과 실제 검색·복구·비용 검증을 구분한다. 인증·운영 배치는 `decisions.md`의 대기/제안 상태를 확인한다.
- 개발 서버의 사용자 전용 환경·실행·검증은 `infra/development-server.md`에서 확인한다. 전용 DB·읽기 전용 수집 자산의 실측은 `docs/research/server-data-inventory.md`를 따른다. 서비스 주소는 `issuedigest.projects.ai.kr`이며 운영 게시와 개인 개발 적용을 구분하며 최신 배포 상태는 `infra/public-deployment.md`를 따른다. 저장소는 공개이므로 서버 접속 주소·SSH 계정·키 경로를 기록하지 않는다. 운영 자원·비용·외부 백업은 대기 중이다.

## 개발 워크플로

일반적인 개발 작업(새 기능, 동작 변경, 다중 파일 수정, 스키마·API 변경, 요구사항이 불명확한 작업)은 `$xinics:spec-driven-workflow` 스킬의 절차를 따른다. 적용 여부 판정 기준과 모델 역할 구분도 그 스킬이 정한다. 오탈자·문구·단일 함수 수정 같은 간단한 작업은 생략한다.

작업 범위와 관련 요구사항을 먼저 확인한다. 기존에 승인된 범위의 통상적인 구현 선택 때문에 같은 승인을 다시 요청하지 않는다. 제품·기술 결정을 바꾸는 경우에는 근거와 영향을 문서에 남기고, 필요한 사용자 입력을 구체적으로 요청한다.

선택지가 있는 확인 질문은 번호가 붙은 짧은 선택지로 제시하고 마지막 선택지는 자유 입력으로 둔다.

## 기록·검증

- 별도 이슈 트래커는 사용하지 않는다. `docs/`가 원본이고 PR이 변경·검토 단위다.
- 작업 시작·중단·인계·완료 시 관련 작업과 진행 기록을 갱신한다. 상세 방식은 `docs/README.md`를 따른다.
- 새 결정에는 날짜·근거·영향을 기록한다. 이전 결정은 지우지 않고 대체 관계를 남긴다.
- 실행 코드·검증 증거가 있는 항목만 구현 완료로 표시한다. 문서·폴더 준비, PR 작성, 배포 성공을 각각 구분한다.
- 검증은 변경에 맞는 범위로 수행하고 결과·미검증 항목을 기록한다. 문서만 바꾼 경우 링크·경로·내용 일치 여부를 확인한다.
- Sites는 요약을 갱신하되 사용자가 이미 열어 둔 브라우저 탭을 자동으로 열거나 이동하지 않는다. 사용자가 열기를 요청한 경우에만 연다.
- Sites 요약을 갱신하지 않았다면 진행 기록에 반영 대기로 표시한다. 저장소 문서를 별도의 결정 원본으로 복제하지 않는다.
- 사용자가 요청하지 않은 병합·운영 데이터 변경은 수행하지 않는다. 키·비밀번호·실제 비공개 데이터는 커밋하지 않는다.

## 코드 경계

- `apps/`는 실행 진입점, `packages/`는 재사용 가능한 도메인·도구·화면 모듈이다.
- 앱끼리 내부 코드를 직접 가져오지 않는다. 웹과 API는 버전이 있는 계약으로 통신한다.
- 비밀값과 모델·데이터 공급자 호출은 서버에서 처리한다.
- 역사 private research-v6는 provider 전용 core_answer를 첫 summary의 첫 문장으로 만들고 추가 요약·comparison/timeline 상세를 잇는다. 새 AI 긍정 해석은 모두 attributed로 변환하고 서버가 '제공 자료에 따르면, '를 붙인다. 모델의 category/source_subject 조합은 받지 않는다. 추가/상세의 assessment는 source_statement/uncertain이며 event_date는 typed timeline에만 있다. 핵심 질문에 직접 답하는 인용이 없으면 insufficient_evidence다. canonical documented/attributed/uncertain·정확 prefix/인용/날짜 검사는 유지한다. claim마다 같은 인용 순서의 AI SupportReview를 정확1개 기록하며 인간 검토·독립 사실 검증으로 표시하지 않는다. 고정 reviewer_id/method_version은 issuedigest-research-v6/research-v6다. Claim/default·canonical/API·공개 D020 v1/v2/빈 review 경계를 유지한다. v2/v3/v4/v5의 실제 agent/schema/지침/prompt bytes·유료 namespace/정수slot1·기존 결과는 동결한다. 역사 v6 worker는 다섯 버전을 등록했고 새 요청만v6로 시작했으며 기존 workflow는 원래 이름·application_version으로 회복한다. 혼합·누락·위조를 거부하고 공개 경계를 넓히지 않는다. 관련 명세는 [첫 결론·근거 부족·귀속](docs/changes/briefing-core-answer.md)를 따른다.
- 역사 private 질문 research-v7은 계획→저장 검색→생성 경로로 처리한다. 여섯 workflow와 별도 issuedigest_research_plan_v7 agent를 등록하며 기존 v2~v6의 provider bytes·유료 정수slot1·원래 이름/version을 보존한다. 새 경로는 planner 요청slot1→issuedigest_research_search_v7 slot2→최종 요청slot3이며 stage별 정확 metadata·현재 권한·부모·고정 원문을 검사한다. 미완료/위조/추가 유료 step은 재호출 없이 실패한다. planner는 queries1~3개만 제안하며 원래 질문 검색도 항상 포함한다. 원래 질문은 보존하고 선택적 이전 AI 맥락만 실제 UTF-8 예산으로 줄여 잘림을 명시한다. planner 최대8,000/출력500/15초, 최종 출력2,000/45초이고 실제 planner usage를 전체24,000에서 차감한다. 알려진 usage를 합산하고 무검색 결과에도 planner 비용을 기록한다. 자동 수리/모델 retry는0이다. 최종 지침·DTO·canonical guards는v6를 재사용하며 정확 reviewer는 issuedigest-research-v7/research-v7다. API/OpenAPI·공개v1/v2·디자인·DB schema/권한·수집기를 넓히지 않는다. [계획 검색 명세](docs/changes/briefing-search-agent.md)를 따른다.
- 역사 private 질문 research-v8은 다음 계약을 유지한다. planner7는 실제 지침/schema/prompt/한도를 그대로 재사용하고 일곱 workflow와 planner7를 등록한다. paidplanner7 slot1→search8 slot2→paidfinal8 slot3이며 v2~v7 실제 provider bytes·이름/version/slot·결과는 보존한다. 실제 v7 worker를 byte-identical fixture로 동결하고 원래 checkpoint를 재생한다. v8 최종 DTO는 v6 실제 Pydantic class를 좁게 파생해 evidence quote에 처음 나온 고유 유효 YYYY-MM-DD 최대16개만 허용하며 날짜0이면 timeline을 schema/runtime에서 제거한다. metadata·질문·부모 AI 날짜는 후보가 아니고 월/주/연말/상대 시점은 원래 표현으로 설명한다. 날짜 enum은 진실 인증이 아니며 해당 claim 인용의 exactdate 최종 검사는 유지한다. 지침은 수치의 포함 관계·목표/관측/조건부 전망·단위/시점/열린 상한을 보존하고 합산하지 않는다. 실제 planner usage 차감·v8 static/actual envelope·기존 예약/권한/취소/단일worker를 유지하며 reviewer는 정확 issuedigest-research-v8/research-v8만 추가한다. API/OpenAPI·public·디자인·DB schema·수집기를 바꾸지 않고 합성 검사와 실제 의미/개발 적용 인수를 구분한다.
- 생성 화면은 허용된 명세·컴포넌트와 검증된 근거로 구성한다. 기존 AI 해석을 확인된 사실로 승격하지 않는다. 테마/계정은 아이콘·접근성 이름/툴팁·키보드/44px/초점을 유지한다. 현재 계획은 `requirements-design.md`를 따른다.
- 종속성과 실행 명령은 실제 구성·검증 후 해당 README에 기록한다. 아직 없는 명령을 실행 가능한 것처럼 적지 않는다.

- 역사 private 질문 research-v9은 planner7 paid1→search9 step2→기존 selector SDK의 raw DBOSModel paid3→원자 apply9 step4→final9 paid5다. selector는 v8의 기존 base model을 빌리며 standalone SDK/역사 provider bytes·slot·version은 동결한다. uncertain을 유지하고 exclude만 제외하며 모두 제외면 최종 호출 없이 알려진 두 호출 비용을 기록한다. 원래 후보/전체 결정/정확 질문·prompt hash는 journal에 남기고 현재 권한·부모·모든 원문을 매번 재검사해 ordered subset으로 한 번만 축소한다. final9는 frozen v8 도구·지침을 재사용하고 합산 prior≤20,000/출력≤1,000, 전체24,000/출력2,500와 동적 final 출력1,500..2,000을 지킨다. 새 private reviewer만 정확 research-v9/issuedigest-research-v9로 추가한다. v9-only 알려진 사용량 기록은 취소/권한 변경 후에도 단조 증가이며 status/result/예약을 바꾸지 않는다. API/DB schema/public/레이아웃·실제 모델/개발 배포 인수 경계는 유지한다.


v9 selector는 공개 `DBOSClient.update_workflow_attributes`로 정확 `{"issuedigest_select_v9_started": true, "issuedigest_select_v9_prompt_sha256": "<정확 UTF-8 prompt SHA256>"}`를 송신 전에 기록한다. 이 client 작업은 durable slot을 만들지 않는다. prefix2에 시작 표식이 있으면 송신 여부가 불명확하므로 재호출 없이 실패한다. prefix3 이상은 정확 표식·소문자64-hex hash가 있어야 하고 재구성한 prompt hash가 원래 영수증과 일치해야 완료 응답을 재생한다. 질문·원문/제목 metadata가 바뀌면 새 유료 호출 없이 실패하며 원래 입력과 결과를 혼합하지 않는다. 알 수 없는 attribute는 덮어쓰지 않고 실패한다. 표식 기록 직후·실제 송신 전 중단도 보수적으로 실패하고 예약을 유지할 수 있다. 기존 취소/권한 전이의 usage 초기화는 바꾸지 않으며 v9 worker가 검증한 journal subtotal을 종료 시 다시 기록한다. 그 기록 전에 프로세스까지 중단되면 다음 worker 시작 시 v9 terminal workflow만20개씩 조회해 정확 owned UUID/상태/완료 metadata와 raw usage를 재검증하고 token 필드만 복구한다. 그 전 행의0은 무료/예약 반환을 뜻하지 않으며 원래 raw journal이 알려진 비용 근거다.

- 새 private research-v10은 기존 v9 relevance body·앞 네 step/selector receipt를 공유하고 최종 `issuedigest_research_v10` paid5와 `issuedigest_research_run_v10`만 추가한다. v9은 원래 final9·workflow/version/slot로 회복하며 byte-identical worker fixture를 보존한다. exact Literal v9/v10 strategy와 기존 v9 wrapper를 사용하고 legacy/planned body는 바꾸지 않는다. v10은 frozen v8 도구/변환·날짜 제한에 짧은 첫 답변 수치 설명 지침을 더하며 포함 관계·목표/실적/조건부 전망·상하한·비교 기준을 보존하도록 지시한다. 자유 문장 의미는 schema로 인증하지 않는다. instructions4,340/static12,648 UTF-8 bytes와 실제 raw/normalized envelope를 검사하고 전체24,000/출력2,500·combined prior20,000/1,000·동적 final1,500..2,000을 유지한다. Model은 필수 borrowed이며 새 client 생성/폐기·추가 검수/자동수리/재시도는 없다. 정확 private research-v10/issuedigest-research-v10만 허용하고 API/OpenAPI/public/schema/레이아웃을 확장하지 않는다. 합성 검증·실제 모델 의미 인수·개발 적용은 구분한다.
