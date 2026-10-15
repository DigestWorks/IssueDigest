# UI

`@issuedigest/ui`는 서버가 기존 Python `CanvasBundle`로 검증한 자료를 표시하는
private React workspace다. evidence·summary·comparison·timeline·graph·chart의
순서와 half/full 배치를 명세에서 읽는다. 웹 앱의 조사 결과에 연결되어 있다.

```tsx
import { CanvasView } from '@issuedigest/ui';
import type { CanvasViewProps } from '@issuedigest/ui';
import '@issuedigest/ui/styles.css';

const props: CanvasViewProps = { bundle: validatedBundle, sourceTitles: verifiedTitleMap, onAction: handleAction };
<CanvasView {...props} />;
```

`bundle`은 API-client의 생성 공개 타입 `CanvasBundle | null`이고 `onAction`은
선택적인 `(action: CanvasAction) => void`다. null은 빈 상태로 표시한다.
근거 부족·추가 질문은 전달된 안내문을 표시하며, 거절·미완성·미지원 버전이나
깨진 표시 참조는 전체 화면의 고정 안내로 거부한다. 정상 모듈을 먼저 표시하지 않는다.
CSS는 별도 export로 가져와야 하며 모든 규칙을 `.id-canvas` 범위에 제한한다.

표시 준비 단계는 공간 일치, ID 중복·메타데이터 충돌, 선택 버전의 인용,
주장·관계·관측·관계 endpoint, 모듈 근거 합집합과 액션 참조를 확인한다.
원문 해시·인용 anchor·권한·주장의 정확성과 전체 원시 API JSON 검증은
이 브라우저 검사로 보장하지 않는다. 원시 응답 검증은 후속 API 소비 경계에서,
원문·인용 검증은 기존 서버 계약에서 담당한다.

`sourceTitles`는 보호된 조사 결과의 문서 ID→검증된 제목 map이다. map을 주면 출처·인용 액션·AI 해석의 근거 자료를 사람에게 읽히는 제목으로 표시한다. 기존 호출자가 map을 주지 않으면 `SourceDocument.source_id`를 쓴다. 단일 날짜 timeline은 같은 시작·종료 날짜를 중복하지 않는다. chart는 모든 알려진 비교 조건이 같을 때만 표시하며 정확 소수
문자열을 라벨·표에 보존한다. 막대의 근사 기하만 BigInt 비율에서 유한 좌표로 변환한다.
같은 비교 조건은 합산 가능성이나 주장 동등성의 판정이 아니다.

근거 열기·문서 선택·후속 질문·정렬은 허용된 ID/값을 콜백에 전달한다.
콜백이 없으면 모든 액션 버튼은 비활성이다. 클릭 전에 자동 실행하지 않으며
URL 이동·네트워크·모델·DB 호출이나 실행 완료 표시를 하지 않는다.
실제 처리·권한·로딩·비용은 host 앱의 책임이다. 사용자 자료는 React 텍스트로 표시한다.

저장소 루트에서 검증한다.

```sh
npm run typecheck --workspace @issuedigest/ui
npm test -- --project ui
uv run pytest packages/ui/tests/test_canvas_fixture.py
npm run check
```

`tests/fixtures/canvas-synthetic.json`은 합성 테스트 전용 자료다. Python의 기존
`CanvasBundle` 검증과 생성 TypeScript 타입을 사용하는 React 테스트가 같은 JSON을
소비한다. 제품 예시 데이터·AI 결과·데모 경로로 연결하지 않는다.
