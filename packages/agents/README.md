# Agents

에이전트 조율·근거 검증 위치. 모델 호출과 UI 렌더링을 분리한다. 조사 실행은 별도 DBOS worker가 명시적으로 시작하며 import나 기본 API 시작 때 유료 호출을 하지 않는다.

## 조사 제안과 캔버스 검증

`issuedigest_agents.research`는 PydanticAI의 명명된 agent와 DBOSDurability capability를 사용합니다. 모델은 summary/comparison/timeline 제안·문장·기존 citation ID만 반환합니다. 서버가 질문에 맞춰 찾고 고정한 immutable EvidenceBundle 인용을 검증한 뒤 `CanvasBundle`을 새로 구성하며 모든 AI 문장은 `basis=inference` 및 derivation으로 기록합니다. 독립 사실 검증이나 인간 검토로 표시하지 않습니다. timeline 날짜는 인용된 정확한 `YYYY-MM-DD` 문자열이 없으면 거부하고 수치 chart/graph는 생성하지 않습니다. 본문·질문은 지시가 아닌 불신 입력으로 제한하고 외부 도구를 등록하지 않습니다.

새 질문은 `issuedigest_agents.research_v4`의 `AIOutputV4`·`create_agent_v4`·`model_prompt_v4`·`build_canvas_v4`를 사용합니다. 각 claim은 documented/attributed/uncertain과300자 이하 설명을 필수 제공하며 기존 inference claim과 같은 인용 순서의 자동 SupportReview1개로 투영합니다. content/supported·attribution/supported·content/insufficient만 허용합니다. 고정 reviewer_id는 `issuedigest-research-v4`이며 실제 인간을 뜻하지 않습니다. 공통 UTC reviewed_at/validated_at을 마이크로초까지 대조하고 혼합/누락/중복/잘못된 참조를 거부합니다.

v3 prompt는16,049 UTF-8바이트, 고정 지시/스키마3,403바이트·framing2,048·출력2,500을 포함한24,000 한도입니다. 기존v2는 원래 출력 schema·agent/DBOSDurability 이름·지침·prompt17,309바이트/고정2,143바이트를 보존해 기존 유료 checkpoint를 재생합니다. 원래 public 함수와 저장된v1/v2 결과를 유지하고 과거 분류를 추정하지 않습니다. 모든 버전은 gpt-5.4-mini/Responses no-store·요청1회·retry0·출력2,500을 유지합니다. collected_at은 수집 시각이며 발행일/이벤트가 아니고 proposed_on은 법안 제안일만 뜻합니다.

새 v4의 schema는 v3의 bounded schema를 그대로 재사용하며 지침·agent/workflow/review 식별자로 분리한다. v4는 기관 통계·효과·평가·주장을 귀속하고 목표·실적·전망·확정 결과를 구분한다. 동일 대상·기간·단위에서 검증 가능한 단순 대소 관계를 설명하고 새 계산·인과·양측을 강제하지 않는다. v4 static schema/instructions4,639바이트, prompt14,813바이트이며 총 한도는 동일하다. v2/v3 지침/schema/prompt bytes와 유료 namespace/slot1은 그대로 보존한다. 합성 모델의 고정 출력은 전달·계약 회귀이며 실제 의미 품질은 controller의 별도 원문 평가가 필요하다.
