# 근거 범위의 참조를 생성·내구 실행에 연결

2026-10-27. [새 순수 코어](question-scoped-text-references.md)를 별도 생성 버전과 질문 실행·저장/재열람에 연결한다. OpenSpec root=null이므로 구현/TDD·독립 검토를 적용한다. 이전 생성/지침·원래 실패/usage를 바꾸지 않는다.

## 생성 계약

별도 guarded-question-evidence-v5 / question-evidence-source-v5 / fill_question_evidence_v5를 추가한다. v4의 완결 JSON 지침과 의미/불확실성 규칙을 유지하되 supporting_refs는 citation 전체에서 유일하고 나머지는 같은 proposition의 지원 범위 안에서 유일해야 한다고 변경한다. 원문/질문·DTO/schema를 유지하며 새 scoped converter만 사용한다. 20,000/출력4,000/60초·공백256·native1요청/무재시도·borrowed client/닫힘/usage 규칙을 유지한다. 한도가 초과하면 무송신으로 거부하며 원문을 자르지 않는다.

v5 영수증 검증은 기존 canonical 검증 후 canonical ref의 위치만 제거한 새 text DTO를 scoped converter로 다시 구성해 같은 결과인지 확인한다. 참조 자체/지원 범위를 바꾸거나 위치를 확장하지 않는다. supporting/지원 내부의 유일성도 저장 읽기에서 다시 확인한다. 기존 v2/v3/v4 생성 소스/지침과 converter/transport는 변경하지 않는다.

## 저장·마이그레이션

실행에 허용되는 버전은 기존v2/v3와 새v5다. 실험v4는 연결하지 않는다. 계획에 저장된 profile로 모든 자식·재접수·부분 재개를 고정하고 v2/v3 identity/hash/최종 bytes를 유지한다. 새v5 identity는 기존 비v2 방식처럼 profile을 포함한다.

migration0014로 실제 DB의 plan/evidence CHECK만 v2/v3/v5로 확장한다. 이력 migration0010/0011이 현재 Table metadata를 import하고0013이 정확한 v2/v3 모양을 검사하므로, 역사적 create_all에 쓰이는 Table CHECK 문구는 의도적으로 v2/v3 baseline을 유지한다(주석 명시). 실행 allowlist와 DB 최신 CHECK는0014에서만 확장하며 명시 migration 없이 create_all로 최신 DB를 구성하지 않는다. 과거 migration은 수정하지 않는다. fresh base→head와0013→0014를 검사한다. unknown/중복/잘못된 열·제약은 양 테이블 DDL 전 거부한다. v5 계획/작업이 남으면 downgrade를 거부하며 원래 행을 삭제하지 않는다.

## 내구 실행·최종 연결

새 issuedigest_guarded_evidence_job_v3 / issuedigest_guarded_evidence_call_v3는 SDKv5만 호출한다. register_evidence_workflow_v5를 추가하고 기존 v1(v2SDK)/v2(v3SDK) 이름·함수·슬롯/ID를 보존한다. 같은 전역 queue/동시1·원래 UUID workflow ID·child namespace·월 예약/권한/현재 원문/취소/송신 의도·known usage·복구 규칙을 유지한다. 잘못된 버전 workflow는 claim/finish/provider 전에 거부한다.

조합기/최종 SDK/저장 읽기는 원래 v2/v3/v5 validator로 homogeneous 영수증만 받는다. v5를 v2/v3로 재라벨하지 않는다. 최종 생성의 prompt/tool/instructions/profile은 바꾸지 않고 canonical-equivalent 입력의 전송 bytes를 보존한다. 서비스의 기존 opt-in 설정은v5를 추가로 허용하지만 기본은v2며 현재 서비스/공동DB는 바꾸지 않는다. 공개 API/UI/버전 선택 입력은 추가하지 않는다.

## 작업

- [x] T1: v5 SDK/영수증·새 위치 재구성 검증·native 모의·회귀 TDD.
- [x] T2: 실행 allowlist·migration0014·이전 요청/행/제약·downgrade/새/기존 설치 TDD.
- [x] T3: dispatch/worker/runner/service·최종 조합/저장 읽기 연결·native ANSWER 저장/재열람·재접수 추가0·v2/v3 회귀.
- [x] 태스크별/전체 독립 검토·전체 검사/정적/타입/빌드/OpenAPI·이전 실제 기록 보존.
- [x] 고정 원문/질문/기준·소유 격리 DB/합성 신원으로 제한 실제1시도·분석1 whitespace 실패/최종0·무재시도·독립 결과 검토/기록/Draft PR131.
- [x] Sitesv154 기록 게시. 실제 생성/최종/앱 인수는 미충족.

## 실제 검증·전환 경계

코드/입력·기준·의존성을 동결하고 모의 전체 경로·독립 검토를 통과한 뒤 새 실제 인수를 한 번만 실행한다. gpt-6.1-sol·분석/최종 각각0.50달러 예약·전체600초 상한을 유지한다. 실패/불명확 송신 후 재호출하거나 과거 응답을 수리하지 않는다. 구조 수용·의미/필수3단위 및 다른9/전체12단위·최종 저장·앱 인수를 구분한다. 공유 DB migration/개발 전환은 백업/복원·배치 점검 뒤 후속으로 진행하며 main/운영·Actions를 변경하지 않는다.
