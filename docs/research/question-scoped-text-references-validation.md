# 명시된 근거 범위의 정확 참조 · 검증

2026-10-27. [계약](../changes/question-scoped-text-references.md). 별도 순수 converter만 추가하며 기존 생성 SDK/영수증·저장·내구 실행·앱을 바꾸지 않는다.

## 단위·관련 검사

TDD red 이후 신규77개·관련331개를 통과했다. supporting refs는 기존 resolver로 원문 전체에서 고정하고, 나머지 refs는 같은 proposition의 확정된 지원 범위 안에서만 exact match를 센다. 겹친 지원 범위가 같은 위치를 여러 번 포함해도 같은 위치 한 개로 세고, 서로 다른 두 위치는 거부한다. 빈/없는/중복·지원 안 겹치는 출현·다른 citation/명제·인접 범위 이어 붙이기·지원 밖 fallback·Unicode 정규화와 원문/DTO 변조를 검사했다.

여덟 facet과 nested value를 기존 canonical validator에 위임하며 facet.refs의 정확 membership·duplicate/ID·bounds/distribution targets·의존 관계/coverage·불확실성 규칙을 유지했다. 지원 안에서 위치를 찾았다고 누락된 facet.refs를 추가하지 않는다. 태스크 독립 검토는77개+기존254개 및 추가 type/mutant/관계 거부7개를 확인했다. 별도 백지 컨텍스트 전체 검토도 관련331개와 기존546개 파일 불변을 독립 확인하고 승인했다. 전체 Python9,747개(app1,535/agents5,720/storage 등2,492)+JS915개, 총10,662개와 린트/포맷·타입·빌드/OpenAPI를 통과했다. 세 격리DB에서 모든 Python testpath를 한 번씩 실행했으며 검사 동안548개 non-Markdown 파일은 불변이다.

## 이전 인자의 새 순수 계약 진단

이전 실제 인자·원문·질문을 변경 없이 재사용한 비공개 오프라인 검사에서 기존 converter는 원문 전체 중복으로 계속 거부했다. 새 converter는 지정된 지원 범위의 유일 위치를 선택하고 canonical 검증까지 통과해 명제3개의 unreviewed 구조를 반환했다. 근거 범위는 모델이 원래 제출한 supporting_refs이며 문구 확대·공백 변경·facet 보충을 하지 않았다. 이전 파일과 입력 객체가 동일함을 재검사했다. 별도 독립 진단 검토에서도23개 참조의 정확한 위치·전체 canonical 검증과 동일 결과 hash를 확인했다. nested membership도 실제로 통과했다.

이는 새 순수 계약의 재현 관측이다. 이전v4 SDK 실행/거부·usage는 바꾸지 않았고 생성 영수증을 만들거나 다른 profile로 재라벨하지 않았다. 새 실제 호출은0이며, 의미/사실성·필수3단위/전체12단위·최종/앱 품질을 인증하지 않는다.

## 적용 경계

기존 전체 원문 유일성 converter와 모든 SDK/transport·저장/API/UI를 유지한다. 새 SDK/지침·분석 workflow·최종 조합·개발 서비스 전환은 후속이며 순수 검사 성공으로 대신하지 않는다. 기존 실패·과금/usage·사전 기준은 보존한다. 공유DB·서버·main/운영 배포·GitHub Actions 설정을 변경하지 않는다.

이전546개 실행 파일과 일곱 묶음521개 비공개 기록을 보존했고 자신의 QA3/익명volume를 정리했다. 새 SDK/실제 모델/앱 인수는 다음 단계다.
