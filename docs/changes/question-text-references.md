# 질문 근거의 정확 텍스트 참조

2026-10-27. [실제 진단](../research/question-diagnostic-acceptance.md)에서 인용문은 존재하지만 모델의 글자 위치가 틀린 응답을 확인했다. 서버가 정확 위치를 결정하는 별도 순수 입력 계약을 추가한다. OpenSpec root=null이므로 구현/TDD/독립 검토 단계만 적용하며 기존 사용자 승인 범위의 결함 원인을 해결한다.

## 계약

- 새 입력은 기존 명제/관계/불확실성/coverage 구조를 보존하고 모든 원문 참조를 citation_id·text 두 필드로 받는다. start/end/occurrence는 받지 않는다. 전체 원문이나 질문을 자르지 않는다.
- 해당 citation의 정확 원문에서 text가 정확히 한 번 나타날 때만 Python Unicode code-point 위치를 서버가 계산한다. 중첩 출현도 중복으로 센다. 대소문자·공백·줄바꿈·Unicode 정규화·퍼지 매칭·가장 가까운 위치 추정은 하지 않는다. 빈 문구·없는 citation·불일치·중복 출현은 전체 거부한다.
- 변환 후 기존 QuestionEvidenceInput/원문·주체·서술어·facet 포함/target·의존성·불확실성/coverage 검증기를 그대로 실행해 기존 unreviewed QuestionEvidencePropositions를 반환한다. 위치 결정은 의미/진실/전체 추출 인증이 아니다.
- strict/frozen/extra-forbid DTO를 사용하고 모델 construct/copy 변조·잘못된 scalar/container/subclass/추가필드를 거부한다. 실패 메시지는 입력/원문/ID/동적 경로를 노출하지 않는다. 사용자 입력과 source를 변이시키지 않는다.
- 기존 모듈·공개 export·provider 지침/schema/이름·영수증·SQL/API·worker·앱은 불변이다. 과거 실제 응답을 고치거나 성공으로 바꾸지 않는다. 새 순수 계약은 아직 모델 도구나 실행 경로에 연결하지 않는다. 새 버전 생성 SDK와 내구 작업 연결·실제 의미/개발 적용은 후속이다.

## 판단과 비용

중복 문구는 occurrence 번호나 근사 위치로 해결하지 않고 더 긴 정확 원문 참조를 요구한다. 잘못된 문맥을 조용히 선택하는 것보다 전체 거부를 선택하며, 짧은 주어처럼 중복이 잦은 표현에서 생성 난도가 높아질 수 있다. 모델의 관계/불확실성 판단 오류는 이 변경만으로 해결되지 않는다.

## 작업

- [x] 새 typed 텍스트 참조 입력·정확 유일 매칭·canonical 변환 TDD 구현.
- [x] 누락/중복/Unicode/오프셋 주입·변조·원문 변이·기존 계약 검사.
- [x] 독립 태스크/전체 검토 C0/I0/M0·전체10,406개/정적/타입/빌드/OpenAPI·기존537파일 보존 확인.
- [x] Draft PR126·Sitesv149 게시 및 생성기/실행 경로 미연결 상태 명시.
