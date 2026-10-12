# 검증된 생성 화면 React 렌더러

2026-10-12 한국 시간. R4/R5·P4의 허용 컴포넌트 렌더러를 구현한다. 동료의 DB·기존 데이터 답변과 독립적으로 진행할 수 있는 다음 작업이다. 기존 CanvasBundle 계약을 소비하며 AI 호출이나 제품 API 전체를 구현한 것으로 표시하지 않는다.

## Global Constraints

- React Router·React19.3.0·TypeScript5.9.3, 생성 OpenAPI 타입을 사용한다. Python 계약·생성 타입·기존 HTTP 두 경로·개발 앱의 빈 자료 화면은 변경하지 않는다.
- `packages/ui`에 재사용 가능한 React 패키지를 만든다. API/DB/모델/공급자 호출은 없으며 임의 HTML·실행 코드·외부 URL을 렌더링하지 않는다. 사용자 자료는 React 텍스트로 표시한다.
- 입력은 서버가 기존 CanvasBundle로 검증한 자료와 화면 버전이다. 브라우저의 표시용 참조/버전 검사는 인증·사실 정확성·전체 서버 검증의 대체물이 아니다. raw API JSON 검증은 이후 API 소비 경계에서 구현한다.
- 합성 자료는 테스트·내부 QA에만 사용한다. 앱에 미리 채운 AI 결과·예시 탭·데모 경로를 추가하지 않는다. 렌더러는 자료가 없으면 명확한 빈 상태를 표시한다.
- 순서·span·모듈 수는 명세가 결정한다. 출력은 절제된 조사 문서 스타일(밝은 바탕, 잉크/녹색, 얇은 경계, 뚜렷한 문단)이며 작은 화면에서도 접근 가능하다. 모션/아이콘 라이브러리·외부 폰트/이미지 다운로드를 추가하지 않는다.
- 실행·SSE·취소·인증·검색·AI·서버 DB·원문 파일은 후속이다. 선택되지 않은 자료·잘못된 참조를 추정하거나 다른 자료로 치환하지 않는다.
- 기존 고정 의존성을 재사용한다. 패키지 workspace/React peer·개발 의존성·검증 설정 변경만 허용하며 새 런타임 공급자를 도입하지 않는다.
- 이 작업의 ignored SDD 리뷰 기록은 미병합 PR 검토가 끝날 때까지 보존한다. 다른 계획의 기록을 읽거나 삭제하지 않는다.

## Task 1 · 여섯 모듈·근거 액션·화면 상태

- [x] 아래 수용 조건을 구현·검증한다. 구현자가 완료 시 체크한다.

1. `@issuedigest/ui` private npm workspace의 `CanvasView`와 props 타입을 export한다. props는 `bundle: CanvasBundle | null`, optional `onAction(action: CanvasAction): void`다. CSS는 명시적인 별도 export이며 `id-canvas` 범위에서만 스타일링한다. API-client의 생성 공개 타입을 사용하고 도메인/생성 타입을 복사하지 않는다.
2. 순서·span을 따른 의미 있는 section/headings, 화면 버전 표시, null 빈 상태, 근거 부족/추가 질문 상태를 제공한다. 불명확·거절·미완성 출력/모르는 계약 버전·모듈·액션·깨진 표시 참조는 전체 화면의 안전한 안내로 거부하고 일부 정상 모듈만 먼저 유출하지 않는다. 번들/배열을 수정하지 않는다.
3. 표시 준비 함수는 선택한 버전에 속한 citation을 resolve하고 공간 일치·중복 모듈/참조 ID·모듈 근거 합집합·action 참조를 확인한다. claim/relation/observation 및 관계 endpoint를 정확 ID로 resolve한다. 원문/인용의 기존 서버 검증을 복제하지 않지만 workspace와 선택 범위 및 누락/충돌 참조는 거부한다. timeline은 알려진 valid_period만 사용한다. chart는 알려진 정확 소수값과 동일하고 알려진 비교 조건만 표시한다. 표시 거부 이유는 원문·내부 예외를 노출하지 않는 고정 문구다.
4. evidence: 실제 문서 식별자(source_id)·provider·원문 인용·페이지/텍스트/표 위치. summary: 전달된 주장과 발화 주체·basis(원문 주장/관측/추론)·근거. comparison: 주장별 주체·내용·basis·근거를 읽기 좋은 표로 비교하며 통계 합산/동등성을 주장하지 않는다. timeline: 날짜 구간과 주장·basis·근거를 날짜 순으로 정렬하며 날짜를 단일 발생 시각으로 바꾸지 않는다. graph: 실제 relation의 source→predicate→target을 시각적 연결과 접근 가능한 텍스트로 표시, basis·근거를 함께 보여 주고 인과를 추가 생성하지 않는다. chart: 전달 수치로 실제 bar 시각화, 정확 소수 문자열·단위와 비교 조건·근거 및 접근 가능한 수치 표를 제공한다. 음수·0·같은 값·큰/작은 소수도 잘못된 비율/NaN/Infinity 없이 처리한다. 차트 기하 표현의 근사는 정확 라벨을 덮어쓰지 않는다.
5. 근거 열기는 `open_evidence` ID 콜백으로만 전달한다. 문서 선택·후속 질문·정렬 액션도 명세의 허용된 값만 콜백으로 전달하며 자동 실행/URL 이동/네트워크 호출은 없다. 콜백이 없으면 버튼이 비활성이다. module/action 버튼은 키보드와 읽기 도구로 식별 가능하다. 액션의 실제 처리·권한·로딩·비용은 이후 host 앱이 담당하며 완료로 표시하지 않는다.
6. root npm workspace·lockfile·Vitest UI jsdom project·typecheck/README를 연결한다. 앱 전체 redesign이나 제품 경로는 추가하지 않는다. 단일 책임 파일로 표시 준비/모듈/공통 부품/스타일/테스트를 나눈다.
7. TDD: import 실패가 아니라 최소 실행 scaffold에 대한 실제 행동 assertion RED를 먼저 확인한다. 여섯 모듈의 실제 내용·순서/구성 변화·선택 인용·basis·구간·실제 bar·정확 숫자·거부/빈/자료 부족·모듈 참조/악성 텍스트·액션·비활성·키보드·입력 불변을 검증한다. 고정 snapshot만 찍거나 implementation을 그대로 재현하는 테스트는 쓰지 않는다. 최소 한 합성 CanvasBundle JSON을 기존 Python CanvasBundle에서 검증하고 실제 생성 TypeScript 타입/React가 같은 fixture를 소비하도록 cross-language 검사한다. 테스트 JSON이 실제 자료·AI 생성 결과처럼 보이지 않도록 합성 표기를 한다.

## 완료 증거

독립 작업/전체 변경 리뷰와 수정 범위 재검토, controller의 실제 PostgreSQL 포함 전체 `npm run check`, 실제 브라우저 desktop/mobile 표시·가로 넘침·키보드 액션·콘솔·명세 변경 확인. 합성 QA 화면은 내부 검사 산출물이며 제품 배포/AI 실행이 아니다. Draft PR·Sites 요약·현재 폴더 연결을 각각 기록한다.

## 구현 판단 기록

- 앱의 작업 공간 도구가 저장소를 인식하지 못해 기존 sibling `.worktrees` 경로를 사용한다. 잘못된 선택이면 앱의 작업 공간 연결을 정리해야 한다.
- 서버/인증 답변을 기다리는 동안 기존 명세의 렌더러를 먼저 구현한다. 잘못된 우선순위면 다음 작업 순서를 조정하며 서버 계약은 유지한다.
- 합성 검증 화면은 내부 QA에서만 열고 개발 앱에는 연결하지 않는다. 실제 API 소비 시 host 연결이 추가로 필요하다.
- 미병합 PR의 리뷰 기록은 보존한다. 불필요한 보존이면 로컬 scratch 정리만 필요하다.

- 기존 SourceDocument에는 제목 필드가 없어 실제 source_id로 문서를 식별한다. 사람이 읽기 좋은 제목은 이후 메타데이터 계약을 추가해야 한다.
