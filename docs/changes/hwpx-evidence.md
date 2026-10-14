# HWPX 본문·표·정확 인용

2026-10-14. 사용자가 첫 이슈 자료 준비 다음으로 HWPX 본문·표·단위를 앱 수집 경로에 연결하도록 승인했다. R2/R3, 기존 EvidenceBundle·ParsedRepresentation·Citation을 사용한다. OpenSpec CLI의 root=null을 확인해 새 루트를 만들지 않고 기존 문서 명세/태스크와 Superpowers 구현 절차를 사용한다.

## 범위·수용 조건

- 로컬 bytes와 기대 SHA-256을 받는 결정적 파서. 네트워크·외부 명령·파일 추출·모델·DB 호출 없음. HWPX는 출처/라이선스를 자체 보증하지 않으며 원문 게시물의 수집/이용 증거를 별도로 유지한다.
- ZIP 내부 mimetype `application/hwp+zip`, `Contents/content.hpf`의 manifest/spine으로 본문 구역 순서를 결정한다. linear=no의 header 등은 본문으로 읽지 않는다. 잘못된 참조·중복·경로·암호화·손상은 고정 AuditError로 거부한다. XML은 올바른 namespace와 구조를 검증한다.
- 원문/압축 해제/멤버/구역/XML 노드·깊이/텍스트/표·셀·격자 한도를 검사한다. ZIP을 디스크에 풀지 않으며 XML DTD/ENTITY·외부 참조를 거부한다. 수치 속성은 제한된 비음수 정수로 검증한다. 이미지·스크립트·프리뷰·주석·페이지 머리/꼬리 텍스트는 본문으로 승격하지 않는다.
- 문단 순서와 행·열·병합 셀의 실제 주소/범위를 보존한다. 문단 안의 표와 뒤따르는 텍스트의 순서를 유지하고 중첩 표는 자기 표/셀에 귀속시켜 중복 인용·유실을 막는다. 출력 text에 대한 Unicode code-point 범위와 SHA-256을 보존한다.
- 단위·기간 문구를 원문 셀 텍스트에 보존한다. `TableCell.unit/period`에 추정값을 넣지 않는다. 구조 추출은 수치 합산/의미/수혜 대상 판정의 완료가 아니며 Q05/Q06의 의미 검토는 후속이다.
- 기존 ParsedRepresentation에 pages=()와 안정적 table/cell IDs 및 셀 텍스트를 연결한다. 입력 결과의 재검증과 caller UUID4 검증을 수행한다. 위치/정확 셀 인용 생성은 기존 Citation 검증에서 matched/not_evaluated여야 한다. 모호한 텍스트 인용은 명시 start 없이는 거부한다.
- 공개 테스트는 합성 ZIP/XML만 사용한다. 실제 교육부 첨부·본문·전체 인용·개별 hash·UUID는 개인700/600 저장, 고정 코드/집계만 공개한다. 운영/공동 DB·승인 계정·main·공개 앱은 변경하지 않는다. API/DB 스키마·의존성 버전 변경 없음.

## 설계

`packages/ingestion`에 HWPX 추출·표/셀 구조·기존 계약 어댑터를 둔다. 입력은 획득/해시/이용 증거가 있는 snapshot bytes이다. 버전이 고정된 정규화에서 문단·셀과 구역 구분을 결정적으로 처리하고 실제 페이지 좌표를 만들지 않는다. 테이블 내부의 좌표/병합 정보는 파서 결과에 보존하고 기존 도메인에는 table/cell IDs와 텍스트로 연결한다. 단위 추론이나 임의 JSON/UI 생성은 하지 않는다.

포맷 기준: [한컴 HWPX 패키지/본문 구조](https://tech.hancom.com/hwpxformat/), [한컴 Python 구조 파싱](https://tech.hancom.com/python-hwpx-parsing-2/). 기존 manifest의 spine 순서를 읽으며 파일명 정렬만으로 본문 순서를 만들지 않는다. 전체 KS X 6101 검증기·페이지 렌더러·OCR·HWP 바이너리 지원은 이 범위 밖이다.

## Global Constraints

로컬·결정적·bounded 파서와 기존 정확 근거 계약을 재사용한다. 네트워크/모델/공동 DB 호출, 실제 원문/인용/해시/UUID/비밀값의 공개 커밋, 기존 API/DB 계약·의존성 버전 변경, main 병합·공개 앱 배포는 금지한다. 단위·기간은 원문 보존이며 자동 의미 추론으로 채우지 않는다. 추출 성공과 라이선스/주장 지지/품질 평가 완료를 구분한다.

## 구현 태스크

### Task 1: HWPX 파서·구조·기존 계약 어댑터

- [x] 합성 fixtures의 TDD: Unicode/구역 spine 순서·문단/표 혼합·행/열/병합·중첩 표·단위 문구·정확 셀/텍스트 인용·잘못된 hash/한도/ZIP/XML/참조/namespace/중복/범위/손상/공개 안전 오류·입력/결과 우회 검증.
- [x] 파서·immutable 결과·정규화 버전·표/셀 범위·기존 ParsedRepresentation/정확 인용 어댑터 구현, 패키지 공개 exports.
- [x] ingestion README에 실제 함수 사용법·제약·라이선스 외부 확인·미연결 CLI/worker/DB 명시, targeted lint/format/mypy/테스트·작업 리뷰.

### Controller 결합·마무리

- [ ] 실제 첨부의 텍스트·표·셀 구조/범위와 정확 인용 계약을 개인 공간에서 대조. 전체 검사와 독립 전체 변경 리뷰.
- [ ] 작업·진행·연구 문서 상태/문서 링크·개인정보 제외 검사·Draft PR/첨부·Sites 기존 기록 보존·개발 인계. 실제 공동 DB 등록·AI 실행·공개 앱 배포와 구분.
