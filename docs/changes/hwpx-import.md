# HWPX 수집 작업·등록 계획 연결

2026-10-14. HWPX 파서 다음으로 수집 작업과 공동 DB 적재 경로를 연결하도록 승인받았다. 기존 앱 접속 설정/백업 확인은 아직 대기다. 이 변경은 일회 실행 가능한 작업 함수/명시 준비 명령이며 DBOS 스케줄·복구 런타임이나 공동 DB 적용 완료로 계산하지 않는다. 생산/PoC 엔진을 나누지 않으며 같은 작업 함수를 후속 DBOS 실행에 연결한다. R2/R3·D011/D015와 기존 ProvisioningPlan/EvidenceBundle/Citation을 재사용한다. OpenSpec root=null에 따라 기존 문서 명세+Superpowers 구현 단계를 사용한다.

## 범위·수용 조건

- `apps/worker`를 Python workspace 패키지로 구성하고 domain/ingestion/storage의 고정 workspace 의존성만 연결한다. 새 외부 라이브러리·DBOS 초기화·마이그레이션·상주 프로세스·DB/네트워크/모델 호출 없음. uv lock과 루트 mypy/pytest 설정에 실제 worker 코드를 포함한다.
- 엄격하고 불변인 private job 입력: schema_version=1, 1~10개 HWPX 항목. 각 항목은 raw file의 절대 경로, SourceDocument/DocumentVersion, representation_id/snapshot_id(UUID4), 명시한 인용 요청(text+optional start 또는 table_id/cell_id, citation_id), 공공누리1유형 텍스트 이용 확인(원문 canonical URL과 같은 license evidence URL, operator 승인=true)을 갖는다. document/version/workspace 참조·ID 중복·URL·시간/해시·수집 범위를 기존 계약과 함께 검증한다. HWPX 자체에서 게시 시각/발행처/이용권을 추정하지 않는다. 이용 승인 표시는 형식·동의 확인이며 홈페이지 진위/라이선스 자동 검증이 아니다.
- 유한 UTF-8 JSON(최대 기존 MAX_PLAN_BYTES), 중복 JSON key/NaN/초과 한도/잘못된 값/구성 우회에 고정 안전 오류. job과 base registration plan을 모두 재검증한다. 원문 파일은 symlink/FIFO/디렉터리/다른 소유자/공개 모드/변경 감지/크기·해시 불일치 등을 거부하는 bounded private read로 읽는다. owner400/600 regular file만 허용한다. CLI 입력 계획 파일에도 같은 private read 원칙을 적용한다.
- 각 원문을 기존 HWPX 파서로 준비하고 요청한 정확 인용을 기존 Citation 검증으로 대조한다. source kinds=government_document·canonical HTTPS·원문 버전 media_type=application/hwp+zip 및 대응 관계를 확인한다. 인용 의미는 not_evaluated다. 임의 UUID/페이지/단위 메타데이터를 생성하지 않는다. 빈 인용이나 미확인 이용 승인은 준비를 거부한다.
- 검증된 새 ProvisioningSnapshot들을 기존 private ProvisioningPlan에 추가한다. workspace/expected_database/approved invites와 기존 snapshot 순서·내용을 보존한다. 서로 다른 내용의 같은 ID와 기존 document/version/representation/citation 참조 충돌은 거부한다. 같은 입력을 재실행할 때 동일 artifact를 만들거나 이미 포함된 정확 동일 snapshot을 중복 추가하지 않는다. 기존 별개 snapshot들의 합법적인 버전/표현 공유는 금지하지 않는다.
- SDK 준비는 DB를 변경하지 않는다. 출력은 기존 storage.parse_plan/validate_plan을 통과하는 JSON이고 기존 `workspace-provision`의 오프라인 확인/--check-database/--apply가 그대로 처리한다. DB 적용 경로/초대 상태/원자성/복구는 기존 도구의 계약이다. 새 worker가 DB 권한 검사나 SQL 쓰기 코드를 복제하지 않는다.
- CLI `issuedigest-prepare-hwpx PRIVATE_JOB_PLAN PRIVATE_BASE_PLAN PRIVATE_OUTPUT_PLAN` 기본 모드에서 준비만 한다. 결과 파일은 사용자 소유700 디렉터리에 atomic exclusive400/600 artifact로 보관하며 기존 파일/승인 계획/원문을 덮어쓰지 않는다. 실패 시 부분 출력 없이 원래 입력/기존 출력이 유지된다. 성공/오류/도움말·로그는 고정 코드/집계만, 경로·URL·원문·인용·hash·UUID·계정·exception 내용을 출력하지 않는다.
- 공개 테스트는 합성 XML/ZIP/계정/자료만 사용한다. 실제 공식 첨부·승인 계획/계정·실제 source ID/개별hash/UUID·접속 정보는 개인700/600에 보존한다. worker import/오프라인 실행은 DB나 OAuth·공급자 호출을 만들지 않는다. 실제 사용자 승인 초대/공동 DB/서비스/main/공개 앱은 변경하지 않는다.

## 설계

작업 함수는 private job과 승인된 base plan을 받아 정확 근거를 준비하고 확장된 등록 계획을 반환한다. 출처별 파일 읽기와 파싱은 기존 ingestion을 사용한다. 등록 대상/초대/저장은 기존 storage 도구가 맡는다. 이 경계는 후속 DBOS 실행에서 재사용하며 중복 없는 등록 ID를 보존한다. 현재는 파일 snapshot 기반이며 HTTP 크롤러·주기 수집·원문 객체 저장·DBOS 장애 복구·검색/AI·권한 있는 사용자 작업 API는 후속이다.

## Global Constraints

기존 SourceDocument/DocumentVersion/ParsedRepresentation/Citation/EvidenceBundle/ProvisioningPlan을 재사용한다. 실제 네트워크/모델/DB·마이그레이션·스키마/API·초대 권한·공동 자료/운영 서비스/main·공개 앱 변경은 금지한다. 고정 workspace 의존성 외 새 외부 의존성/엔진 변경은 없다. 실제 키·계정·원문/인용·개별hash/UUID/경로는 공개하지 않는다. 출처/이용 확인과 인용 위치는 주장 지지/자동 단위/검색 품질 완료와 구분한다.

## 구현 태스크

### Task 1: Worker 준비 작업·명시 CLI·기존 등록 계획 어댑터

- [x] 합성 TDD: 실제 HWPX 파서→정확 텍스트/셀 인용→기존 계획 보존/확장/반복, 다른 공간·미승인 이용·중복키/ID/참조 충돌/construct-copy 우회·변경/공개/symlink/FIFO 파일·출력 실패·원자적 보관·민감 값 없는 로그·무네트워크/무DB import.
- [x] worker 패키지/typed SDK/CLI·bounded private 입출력·고정 workspace lock/정적·테스트 설정 구현. worker README에 실제 명령·기존 등록 도구 이어서 실행하는 방법과 DBOS/공동 DB 미완료를 명시.
- [x] targeted lint/format/mypy/worker+관련 테스트·자체 점검 보고/커밋. controller가 독립 작업 리뷰를 진행한다.

## Controller 검증·기록

- [ ] 실제 첨부의 기존 private 근거와 새 준비 artifact를 대조하고 전용 합성 DB에서 기존 CLI로 검사/등록/반복/재조회·원자성과 초대 보존을 확인한다. 실제 승인 계획은 수정하지 않는다.
- [ ] 전체 검사·독립 전체 리뷰·문서/개인정보 검증·Draft PR/앱 첨부·Sites 이전 기록 보존·개발 인계. 공동 DB 설정/백업 입력 대기와 실제 적용 미완료를 분리한다.
