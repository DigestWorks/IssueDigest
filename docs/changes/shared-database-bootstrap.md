# 공동 개발 DB 초기 스키마·승인 자료 적용

2026-10-14 한국 시간. 사용자가 백업/복구 확인→초기 스키마→승인 자료 등록의 진행을 승인했다. 기존 reviewed migrations0001~0004·workspace-provision·rebuild_projection을 그대로 실행한다. 제품 코드/계약/의존성 변경은 없으며 기존 workspace-bootstrap 명세의 실제 적용 항목을 수행한다. OpenSpec root=null인 기존 절차의 검증된 코드/리뷰를 재사용하고 새 구현 태스크를 만들지 않는다.

## 조건·범위

- 적용 전 전용 DB는 PG18.6/vector0.8.7·앱 테이블0개였다. 개발 로그인은 기존 설정의 스키마 소유 역할로 실행되며 public schema CREATE 가능/DB 생성·superuser 권한 없음, 앱 계정은 DDL 없음. 기본 ACL로 기존 앱 역할 권한이 설정돼 있다. 연결 URL/역할/SSH/계정/원문·인용/개별 ID/hash는 private700/600에만 보관한다.
- 변경 전 다시 같은 issuedigest/loopback/포트·현재 빈 스키마·작업 폴더/commit·개발 session_user/기존 current_user 소유 역할·앱 계정 분리와 기존 vector를 확인한다. 예상과 다른 테이블/버전/대상은 적용을 중단하고 읽기 확인한다. shared DB는 reset/downgrade/테스트/복원 대상이 아니다.
- 서버의 pg_dump14는18을 덤프할 수 없다. 고정 로컬 PostgreSQL18.6 클라이언트와 개인 SSH tunnel로 변경 전/후 custom archive를 서버 밖 개인 디렉터리에 보관한다. 비밀번호는 private passfile에만 두고 args/출력/Git에 넣지 않는다. [pg_dump 버전·형식](https://www.postgresql.org/docs/18/app-pgdump.html)을 따른다.
- 전체 DB archive는 vector extension 선언/ACL/기존 메타데이터를 포함해 보존하고 TOC를 검사한다. 별도 앱 범위 archive는 현재 앱에서 사용하지 않는 vector extension을 명시 제외한다. 현재 앱 스키마에는 vector 타입 의존성이 없다. 앱 범위 archive를 별도 소유 PostgreSQL18.6/issuedigest_test에서 no-owner/no-acl/single-transaction으로 복원하고 canonical 근거/초대/검색 투영을 대조한다. 이것은 앱 데이터 복원이며 pgvector 바이너리·서버 역할/전체 재해복구·정기 백업 완료가 아니다. [pg_restore](https://www.postgresql.org/docs/18/app-pgrestore.html)의 복원 경계를 따른다.
- 초기 스키마는 개발 계정에서 Alembic upgrade head(0004)를 명시 실행한다. 전체 DDL은 기존 Alembic PostgreSQL 트랜잭션 경계이며 별도 연결의 동일 advisory lock을 최종 대상/빈 스키마 재조회부터 Alembic 완료/결과 확인까지 계속 유지한다. lock 연결 유실은 불확실한 적용으로 재조회하며, 협조하는 실행들이 같은 key를 사용한다. lock은 다른 관리자의 비협조 DDL을 금지하지 않는다. 초기 빈 DB만 적용한다. 기존 vector/법안 MySQL/수집 자산·공용 checkout·서비스/main은 변경하지 않는다.
- migration 후 앱 계정의 필요한 테이블 SELECT/INSERT, auth UPDATE/flow DELETE, 검색 투영 DML·DDL 부재를 실제 확인한다. 기본 권한이 부족하면 적용을 미루고 필요한 항목만 정리한다. 새 계정·전체 schema/global 권한·sudo/Docker·운영 설정 변경은 하지 않는다.
- 기존 승인 private plan을 byte 그대로 사용한다: 승인 Google 계정1개·공유 공간 예약 ID·검증된 공식 HTML1개/인용3개. 합성/HWPX 연구용 namespace를 실제 공간으로 등록하지 않는다. 원문 캐시/출처 조건/인용·승인 입력을 controller가 대조하고 CLI offline/check/apply/repeat 및 실제 앱 역할 load/rebuild 반복을 확인한다. 초대/자료/outbox는 기존 atomic registration 경계이다. 임의 provider subject/사용자/세션은 생성하지 않는다.
- 실패 시 각 migration/registration의 트랜잭션을 존중하고 결과를 조회한다. 실제 DB를 자동 삭제/복원/rollback하지 않는다. commit 결과가 불명확하면 같은 ID/내용을 재조회·재실행한다. 추가 데이터는 새 승인 계획으로 처리한다.

## 실행·검증

- [x] 변경 전 private full/app archive·TOC 검사, 앱 범위의 빈 대상 복원 및 DB 조건/명시 계획 독립 검토.
- [x] 개발 역할 명시 migration과 실제 앱 권한 점검, 승인 plan offline/check/apply/repeat·canonical 재조회·검색 투영 반복.
- [x] 변경 후 서버 밖 private full/app archive·별도 소유 DB 복원·근거/초대/투영 대조. 실제 OAuth/세션0·기존 vector 유지 확인.
- [ ] 실행 결과/조건·다음 행동을 docs/PR/Sites에 기록하고 소유 QA/tunnel/credentials cache 정리·개발 인계. dump 원본/승인 계획/리뷰 기록은 private로 보존한다.

## 사용자에게 남는 입력

현재 초기 단계의 새 관리자 권한/설치 요청은 없다. 실제 첫 Google 로그인은 사용자가 브라우저에서 수행해야 하며, 두 번째 사용자의 Google 이메일은 초대 시 필요하다. 정기 백업/외부 보관/전체 복원·운영비는 보존할 사용자 작업과 첫 공개 전에 별도 확인한다. D013의 main 병합·공개 앱 유예를 유지한다.

## 실제 실행 결과

- 기존 제품 코드 d700182(코드 변경 기준 f5e3314)의 migrations0001~0004를 서버 개인 worktree에서 적용했다. revision은 `0004_evidence_search`, public 테이블15개(앱14개+Alembic1개)다. 기존 설정의 스키마 소유 역할이 객체를 소유하며 앱 계정의 필요한 DML 권한과 DDL 부재를 실제 확인했다. 계정·권한·설정 변경은 없었다.
- 기존 승인 계획만 등록했다. 공식 HTML 자료1건·인용3개·미바인딩 Google 초대1건·outbox1건. 첫 적용은 자료/초대 각1개 생성, 재실행은 각0개 생성/1개 유지였다. canonical 묶음 전체를 대조했다. 검색 투영8단위를 재생성하고 반복은 unchanged였다. auth users/sessions/memberships/flows는 모두0이다. 초대 등록은 로그인 성공이 아니다.
- 변경 전 full/app custom archive2,687/2,266bytes, 변경 후69,953/69,532bytes를 서버 밖 개인700/600 경로에 보존했다. 소유 검증용 PG18.6에 앱 범위 archive를 각각 복원했다. 변경 후15테이블·전체 canonical 묶음·승인된 초대의 issuer/ID/email/space/role/상태·outbox1·투영8단위와 재생성 unchanged를 확인했다. 기존 vector0.8.7는 실제 서버에 유지된다. 외부 원문 캐시/승인 입력은 별도 개인 경로에 보존한다.
- 복원 뒤 추가 대조 도구가 초대 모델에 없는 issuer 필드를 참조해 실패했다. 복원은 이미 완료됐으므로 초기화/재복원하지 않고 코드의 고정 Google issuer와 읽기 재대조했다. private 실패 로그를 보존했고 대조는 통과했다. 실제 DB는 복원/테스트 대상이 아니었다.
- 이번 변경은 운영 실행·문서만이다. 제품 코드 전체 검사2,109개와 CI d700182 성공은 기존 코드의 증거이며 새 실행 결과와 구분한다. 새 검증은 실제 DB 조건/권한·명시 등록·반복·백업/앱 복원·문서 링크/비공개 정보 제외다. 실제 Google 로그인/제품 API·UI/의미 검색/정기 백업/전체 재해복구/공개 앱은 미완료다.

독립 실행 결과·문서 검토는 Critical0/Important0/Minor1이었다. 이전 관리자 요청 상태의 현재형 표현을 2026-10-13 당시 이력으로 구분하고 재검토 잔여C/I/M0을 확인했다. 상대 링크82개·git diff --check·공개 파일296개의 실제 비밀값/계정/ID/hash 제외 검사 통과. 소유 검증 컨테이너는 식별/이미지/label/loopback 포트 대조 후 정지·익명 볼륨과 함께 제거했고 임시 passfile 부재를 확인했다. 개인 백업/승인 계획·검증/리뷰는 보존한다. PR/Sites/개발 인계는 진행 기록에서 최종 증거를 연결한다.
