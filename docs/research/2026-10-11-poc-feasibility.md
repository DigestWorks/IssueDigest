# PoC 기술 검토: generative UI와 온톨로지·그래프 RAG

- 작성일: 2026-10-11
- 대상
  - generative UI 참고 구현: [CopilotKit/OpenIntelligentUI](https://github.com/CopilotKit/OpenIntelligentUI) (MIT, 2026-10-09 커밋 `f6e4388`)
  - 에이전트 기반: `agent-chat-framework` (민재 로컬 저장소 `~/code/framework/agent-chat-framework`, main `f535fe6`)
  - 데이터 수집 MCP 후보: 재신의 [검토 페이지](https://lawdigest-rebuild-plan.ijaesinii.chatgpt.site/) 「공공 AX·MCP 활용 후보」
- 방법: 저장소 코드와 README, 공식 문서 열람. 외부 도구는 코드와 문서만 확인했다. 버전과 커밋 날짜는 2026-10-11 조회 기준이다.

## 결론

- generative UI는 OpenIntelligentUI의 렌더러와 컴포넌트 카탈로그 패턴을 참고해 우리 코드로 구현한다. CopilotKit runtime과 Jev 대신 우리 에이전트가 화면 spec을 생성한다.
- 에이전트는 `agent-chat-framework`(이하 ACF)의 Claude·Codex bridge를 별도 Node 서버로 옮겨 사용한다. 프론트엔드는 기획대로 React Router로 만든다.
- 온톨로지·그래프 RAG는 구현 가능하다. Neo4j 적재는 원천 공공 API를 직접 호출하는 배치 파이프라인으로 하고, MCP 서버는 에이전트가 답변할 때 탐색·검증하는 데 사용한다. 검색은 `neo4j-graphrag`를 사용한다.

## generative UI: OpenIntelligentUI

### 구조

- 구성: Next.js 16 앱(`apps/app`), FastAPI + LangGraph + `deepagents` 에이전트(`apps/agent`), 선택 MCP 서버(`apps/mcp`), 디자인 시스템 패키지. 앱과 에이전트는 AG-UI 프로토콜로 통신한다.
- UI 출력 방식
  1. Open Generative UI: 모델이 `generateSandboxedUi` 도구로 HTML·CSS·JS를 정해진 필드 순서로 스트리밍하고, 프론트엔드가 iframe sandbox에서 렌더링한다.
  2. A2UI: Zod로 정의한 컴포넌트 카탈로그(현재 `Table` 하나)를 모델에 도구로 제공한다.
  3. CopilotKit `useComponent`: Recharts 막대·원형 차트.
- 표현 방식 결정: Jev(TypeSafe, `https://api.typesafe.ai/v1/systemone`)가 매 턴 `text`, `table`, `bar_chart` 등 중 하나를 고르고, 고른 값에 맞는 도구만 모델에 남긴다(`apps/agent/src/visualization_router.py:14`). `TYPESAFE_API_KEY`가 없으면 예외가 발생한다.
- 의존성: `@copilotkit/*@1.55.2-next.1` 등 prerelease 버전. CopilotKit 패키지를 통해 설치 통계 수집 패키지 `@scarf/scarf`가 함께 설치된다.

### IssueDigest 요구와 비교

| 요구 | OpenIntelligentUI | 조치 |
| --- | --- | --- |
| 주장별 원문 URL·인용 위치·시점 | `Table`의 자유 텍스트 `source` 필드뿐 | 카탈로그 컴포넌트에 citation 필드를 필수로 추가 |
| 근거 부족 시 답변 유보 | 프롬프트 문구에 의존 | `insufficient_evidence` 상태를 스키마에 추가 |
| 타임라인, 주장 비교 | 없음. 모델 생성 HTML로 표현 | shadcn 기반 컴포넌트로 직접 구현 |
| 부분 UI 스트리밍 | 필드 순서 계약, 1초 throttle, preview/final iframe | 그대로 참고 |
| 표현 방식 결정 | 외부 유료 API(Jev) | 에이전트 프롬프트와 카탈로그 설명으로 대체 |

모델이 자유롭게 만든 HTML 안의 수치와 인용은 검증할 수 없다. 수치와 인용이 들어가는 화면은 타입이 정의된 카탈로그 컴포넌트로만 그리고, 자유형식 HTML은 수치가 없는 도식에만 사용한다.

### 재사용할 코드와 패턴

- 그대로 참고: `process-partial-html.ts`, `frame-content.ts`의 CSP 구성, sandbox bridge의 Zod 검증
- 고쳐서 사용: Zod props + `safeParse` 실패 시 오류 UI를 보여 주는 카탈로그 패턴. shadcn 컴포넌트와 citation 스키마에 맞춘다.
- 렌더러 디렉터리는 Next.js 전용 API를 쓰지 않으므로 React Router 앱에서도 사용할 수 있다.

## 에이전트: agent-chat-framework

### 구조

- 형태: assistant-ui와 AI Elements를 합친 자체 shadcn 레지스트리(`@acf/<name>`)와 이를 사용하는 Next.js 데모 앱. 레지스트리 공개 호스트가 없어서 설치할 때 ACF dev 서버를 로컬에서 실행해야 한다.
- 서버: `POST /api/agent`가 모델 이름 접두사(`claude/…`, `codex/…`)로 백엔드를 고른다.
  - Claude: `@anthropic-ai/claude-agent-sdk`의 `query()`. SDK가 로컬 `claude` CLI를 실행한다.
  - Codex: `codex app-server`(JSON-RPC over stdio) 프로세스 하나를 공유한다. `sandbox: "read-only"`, `approvalPolicy: "never"`.
  - 브라우저에는 `assistant-stream` data stream 프로토콜로 텍스트, reasoning, 도구 호출, 세션 ID, 사용량을 전달한다.
- 서버 코드(`src/lib/agent/*`, `src/app/api/agent/*`)는 레지스트리 항목에 포함되지 않으므로 복사해서 사용한다. 이 코드는 `node:child_process`와 `assistant-stream`만 사용하므로 Hono 같은 Node 서버로 옮길 수 있다.

### IssueDigest에 붙이는 방법

- 데이터 조회 도구: FastAPI가 MCP(HTTP) 서버로 `search_issue`, `get_entity_graph`, `get_sources` 같은 도구를 제공한다. Claude 쪽은 `mcpServers`와 `allowedTools`(`mcp__<server>__<tool>`)로 연결한다.
- 화면 출력: 에이전트가 `present_report(spec)` 도구를 호출하고, 프론트엔드는 도구 인자의 spec을 `toolUI`로 렌더링한다. ACF bridge는 도구 결과를 문자열로만 전달하므로 spec은 결과가 아니라 인자에 넣는다. 도구 이름이 Claude(`mcp__srv__tool`)와 Codex(`srv__tool`)에서 다르므로 렌더러를 두 이름으로 등록한다.
- 설치할 레지스트리 항목 후보: `thread-aui`, `model-selector-aui`, `generative-ui`, `chart`, `timeline`, `comparison-card`, `data-table`, `inline-citation`, `sources-aui`, `research-report`

### 제약

- 로컬 `claude`·`codex` 바이너리와 호스트 계정 로그인이 필요하다. 현재 이 Mac에는 `claude`만 PATH에 있고 `codex`는 없다.
- 라우트에 인증이 없고 모든 요청이 한 계정의 로그인과 사용 한도를 쓴다. PoC는 로컬 실행으로 한정하고, 서버 배포 전에 API 키 방식과 사용자 격리를 정해야 한다.
- 새로고침 후 대화 복원과 스레드 목록이 없다.

## 온톨로지·그래프 RAG: 데이터 수집 MCP 후보

### 후보 현황

2026-10-11 조사 기준이며 설치·실행은 검증하지 않았다.

| 후보 | 유지 | 데이터·키 | 제공 내용 | 라이선스 |
| --- | --- | --- | --- | --- |
| [korean-law-mcp](https://github.com/chrisryugj/korean-law-mcp) | 커뮤니티 | 법제처 Open API, `LAW_OC` | 법령·조문 전문, 판례 | MIT |
| [assembly-api-mcp](https://github.com/hollobit/assembly-api-mcp) | 커뮤니티 | 열린국회정보, `ASSEMBLY_API_KEY` | 의원, 의안, 표결, 위원회, 청원 메타데이터. 회의록은 PDF 링크 | MIT |
| [korean-stats-mcp](https://github.com/chrisryugj/korean-stats-mcp) | 커뮤니티 | KOSIS, `KOSIS_API_KEY` | 통계 수치, 통계표 ID, 갱신일 | MIT |
| [korean-bill-debate-mcp](https://github.com/epoko77-ai/korean-bill-debate-mcp) | 커뮤니티 | 열린국회정보, `ASSEMBLY_OPEN_API_KEY` | 회의록 원문, 원문 위치, SHA-256 | Apache-2.0 |
| [kr-hearings-data](https://github.com/kyusik-yang/kr-hearings-data) | 커뮤니티 데이터셋 | Parquet 릴리스 파일, 키 불필요 | 16~22대 회의 발언 원문(발언 단위), 표결·안건 | 데이터 CC BY 4.0 |
| [gov-data-mcp](https://github.com/leokim90/gov-data-mcp) | 커뮤니티 | data.go.kr 등, 키 필요 | 정부24 서비스, 지원사업 공고 메타데이터 | MIT |
| [k-vote-cli](https://github.com/JungHoonGhae/k-vote-cli) | 커뮤니티 | data.go.kr 파일, NESDC | 개표·투표율 정규화, 여론조사 첨부 | MIT |
| [GQAI-GovtPress-mcp](https://github.com/yongkyu4803/GQAI-GovtPress-mcp) | 커뮤니티 | 운영자 Supabase 색인 | 보도자료 제목·기관·발행일·원문 URL. 본문 없음 | LICENSE 파일 없음 |
| [data-go-mcp-servers](https://github.com/Koomook/data-go-mcp-servers) | 커뮤니티 | data.go.kr, `API_KEY` | 나라장터, 대통령 연설문 목록. 마지막 커밋 2025-09-16 | Apache-2.0 |
| [HRDK MCP](https://openapi.hrdkorea.or.kr/mcp.html) | 한국산업인력공단 공식 | 인증 없음 | 국가자격, NCS, 훈련 | 이용조건 미확인 |
| [datagokr](https://github.com/datagokr-dev/datagokr) | 커뮤니티 | data.go.kr 카탈로그 | 데이터셋 탐색·미리보기 | MIT |
| [kordoc](https://github.com/chrisryugj/kordoc) | 커뮤니티 | 로컬 파일 파서 | HWP·HWPX·PDF를 Markdown으로 변환, 표의 쪽 번호와 bbox | MIT |

뉴스 본문과 진행 중인 청원 원문을 제공하는 후보는 목록에 없다.

### 적재 방식

Neo4j 대량 적재는 원천 API를 직접 호출하는 배치 파이프라인으로 한다. MCP 응답은 모델이 사용하기 좋게 축약되어 있어서 원본 필드와 인용 위치를 보존해야 하는 적재에 맞지 않는다.

- 열린국회정보: `assembly-api-mcp/src/api/codes.ts`의 API 코드표를 참고해 직접 호출한다.
- 회의록: kr-hearings-data Parquet를 적재하고 22대 신규 회의만 증분 수집한다.
- 보도자료·검토보고서 첨부: kordoc으로 파싱해 쪽·bbox 단위 인용 위치를 만든다.
- 에이전트가 답변 중 사용하는 MCP: korean-stats-mcp(통계표 선택), korean-law-mcp(인용 검증)

### 노드 키와 관계

- 노드 키로 쓸 값: 의안 `BILL_ID`, 의원 `MONA_CD`, 회의 `CONFER_NUM`·발언 `turn_seq`, 법령 ID·버전 `MST`·시행일 `efYd`, KOSIS 통계표 ID. 보도자료와 연설문은 원문 URL을 키로 쓴다.
- 규칙으로 추출하는 관계: 의안–제안자–정당, 의안–표결–의원, 의안–위원회–심사회의, 법령–조문–버전, 발언–화자–회의, 통계표–지표–지역·시점
- LLM으로 추출하는 관계: 보도자료·검토보고서·뉴스 안의 주장, 문서가 언급한 법안·법령·통계, 발언의 쟁점

### 스키마 초안

- 노드: `Bill`, `Member`, `Party`, `Committee`, `Meeting`, `Turn`, `Law`, `LawVersion`, `Article`, `StatTable`, `Observation`, `PressRelease`, `Document`, `Chunk`, `Claim`
- 엣지: `PROPOSED`, `MEMBER_OF`, `VOTED`, `REFERRED_TO`, `REVIEWED_IN`, `HAS_TURN`, `SPOKE`, `AMENDS`, `VERSION_OF`, `HAS_ARTICLE`, `MENTIONS`, `ASSERTS`, `SUPPORTED_BY`
- 모든 노드와 엣지의 출처 속성: `source_url`, `source_api`, `retrieved_at`, `content_sha256`, `span`(회의록은 회의 번호+발언 순번, 문서는 쪽+bbox 또는 문자 위치, 법령은 조문 번호), `valid_from`/`valid_to`. LLM이 추출한 엣지에는 `extractor`, `model`, `confidence`를 추가한다.

### 그래프 RAG 라이브러리

| 라이브러리 | 상태 (2026-10-11) | 판단 |
| --- | --- | --- |
| [neo4j-graphrag](https://github.com/neo4j/neo4j-graphrag-python) | PyPI 1.22.0. `VectorCypherRetriever`, `HybridCypherRetriever`, `Text2CypherRetriever` 등 제공 | 채택 |
| [Microsoft GraphRAG](https://github.com/microsoft/graphrag) | README에 maintenance mode 명시 | 제외 |
| [LightRAG](https://github.com/HKUDS/LightRAG) | LLM이 엔터티를 추출해 그래프를 생성하는 방식 | 보류 |

IssueDigest는 정해 둔 스키마로 그래프를 직접 적재하므로, 필요한 것은 적재된 그래프를 조회하는 검색기다. `VectorCypherRetriever`는 Chunk 벡터 검색 결과에서 Cypher로 연결된 의안·회의와 출처 속성을 함께 가져올 수 있어서 주장별 출처 표시 요구에 맞는다.

## spec 단계 검증 항목

- 의원 ID: 열린국회 `MONA_CD`와 회의록 데이터의 `NAAS_CD`가 같은 값인지. 확인 전까지 두 값을 모두 저장한다.
- 의안–회의 연결: 위원회 심사회의 API(`BILLJUDGECONF`)가 회의 번호(`CONFER_NUM`)를 반환하는지. 반환하지 않으면 위원회와 회의일로 조인한다.
- Codex MCP 연결: ACF의 `CODEX_THREAD_CONFIG` 또는 격리된 `config.toml`로 Codex에 MCP 서버를 붙일 수 있는지.
- 열린국회 표결 API의 공식 필드 명세(data.go.kr 15125948 첨부 PDF)
