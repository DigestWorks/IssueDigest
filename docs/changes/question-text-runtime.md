# 정확 텍스트 참조의 내구 실행·최종 저장 연결

2026-10-27. [검증된 v3 SDK](question-text-generation.md)를 질문 계획→분석 큐→최종 생성→저장/재열람에 연결한다. OpenSpec root=null이므로 구현/TDD·독립 검토를 적용한다. 이번 작업은 기존 승인된 생성 결함 개선의 실행 연결이다.

## 버전·저장 계약

- 기존 계획/작업/지침/원문·실패/usage는 재작성하지 않는다. 계획에 evidence_profile을 저장해 v2 또는v3를 고정한다. 기존 계획은v2이며 생성 중인 계획도 중간에 바꾸지 않는다. 새 계획 버전은 명시 서버 설정만 선택한다. 공개 입력/API에 버전 선택을 추가하지 않는다.
- 계획 DTO/기존v2 입력 hash는 보존한다. 새 private 저장 열과 제한 CHECK를 migration0013으로 추가하고 v3 계획은 별도 profile-bound hash를 사용한다. 동일 요청 재접수는 최초 버전을 재사용하며 설정 변경으로 새 실행을 만들지 않는다.
- EvidenceJob에 실제 profile을 명시하고 접수/identity/완료 영수증에서 계획의 고정 버전과 일치시킨다. 기존 v2 요청 hash/ID는 보존하며 v3 identity는 profile을 포함한다. 혼합 버전·위조/알 수 없는 profile은 거부한다.
- 새 DBOS evidence workflow/step 이름은 issuedigest_guarded_evidence_job_v2 / issuedigest_guarded_evidence_call_v2이며 v3 SDK만 사용한다. 기존v1 이름은 v2 SDK만 사용한다. job 기반 workflow ID·child namespace는 보존하고 실제 job.profile에 따라 이름을 선택한다. 잘못된 버전 workflow는 송신 전에 거부한다. 등록/회복은 두 버전을 모두 인식하며 기존 paid journal의 재호출/자동 수리를 하지 않는다.
- 기존 공유 월 예약·단일 실행기·권한/현재 원문/취소·송신 의도/실패 usage·중복 방지 규칙을 유지한다. profile 선택은 SQL에 고정하며 브라우저의 입력이나 임의 class 문자열로 고르지 않는다.

## 최종 생성·읽기

- canonical 조합기·최종 SDK/저장 읽기는 정확 v2/v3 영수증을 원래 validator로 검증한다. type/profile/원문/질문·hash·usage가 일치해야 하며 한 계획의 혼합 버전은 거부한다. v3를 v2 영수증으로 변환하거나 라벨만 바꾸지 않는다.
- 최종 생성의 기존 도구·지침/출력 형식·토큰/시간·profile v1은 보존한다. v2 입력의 실제 요청 JSON/지침/영수증은 동일하고 v3의 입력은 원래 v3 영수증을 보존한다. 최종 결과의 구조/표시 형태를 바꾸지 않는다.
- 질문 runner/service가 계획의 고정 버전으로 작업을 시작하고, 기존 v2 완료/실패 요청과 새 v3 요청을 각각 재열람한다. 새 서버 설정 ISSUEDIGEST_QUESTION_EVIDENCE_PROFILE은 guarded-question-evidence-v2/v3만 허용하며 기본v2다. 배포/실제 실행 전환은 별도 확인한다.
- migration은 기존v2 행을 보존하고 새 CHECK만 허용한다. v3 행/계획이 남아 있으면 downgrade를 거부한다. 이전 migration이 현재 metadata를 참조하는 fresh 경로도 중복 열/제약 없이 검사한다. 권한을 늘리거나 공개 게시/웹 API/UI를 확장하지 않는다.

## 작업

- [x] T1: 계획/분석 저장소·migration0013·profile 고정/재접수/완료/다운그레이드 TDD.
- [x] T2: 조합·최종 SDK/저장 validator의 엄격한 v2/v3 영수증 연결·v2 bytes 회귀 TDD.
- [x] T3: dispatcher/worker/runner/service 버전 연결·native DBOS 모의 분석→최종→저장/재열람/재접수 추가0.
- [x] 태스크별/전체 독립 검토·전체10,519개 검사·이전 source/실제 기록 보존.
- [x] 새 제한 실제 인수 실행(분석1 실패·최종0·같은 원문/기준·무재시도).
- [ ] 실제 최종 생성/의미·앱 인수: 분석 정체로 미수행.
- [ ] 기록/계획판 게시.

## 실제 인수·적용 경계

비공개 사전 기준·제품/입력 해시와 모의 인수/독립 검토를 먼저 확인한다. 실제는 자신의 격리 DB와 합성 신원만 사용하고 기존 예약/20,000·출력4,000/60초·전체600초를 유지한다. 실패 후 재시도·응답 수리·한도 확대를 하지 않는다. 분석 SDK 성공/최종 모델 완료·저장/재열람·내용 의미 보존·사용자 브라우저/개발 적용을 구분한다. 공동DB migration/서비스 전환은 백업·복원과 별도 점검 전까지 하지 않는다.
