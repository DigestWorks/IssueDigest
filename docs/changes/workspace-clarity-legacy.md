# 작업 공간 정돈·기존 수집 자료 연결

2026-10-15. 사용자 승인: 현재 UI를 이해하기 쉽게 정돈하고 연결 가능한 기존 자료를 연결한다. R2/R3/D011/D015 유지, D013 main/운영 배포 유예. OpenSpec root=null이므로 기존 명세와 검토 절차를 사용한다.

## 요구사항·범위

- 첫 화면에서 “자료 검색 → 자료 열기 → 원문·인용 확인”이 보이게 한다. 거대한 소개문·불필요한 마케팅/개발 진단은 기본 화면에서 제거하고, 연결 점검·링크 열기는 접힌 보조 도구에 보존한다.
- 단일 공간에서는 UUID 대신 “공동 조사 자료”를 보여 준다. 여러 공간은 순번으로 선택하고 정확 ID는 선택적 세부 정보에서만 확인한다. 임의 실제 공간 이름을 만들어내지 않는다.
- 원문 검색과 저장 자료 목록을 명확히 구분한다. 자료 유형·공급처·읽기 동작·수집 날짜를 읽기 쉽게 표시하고 기술 ID/정확 시각은 보조 상세에서 보존한다. 제목 필드가 없으므로 원천 ID를 제목이라고 위장하거나 추출 요약을 실제 제목이라고 표시하지 않는다.
- 검색 결과/읽기 화면도 본문·PDF 쪽·표 셀을 이해하기 쉬운 기본 위치로 표현한다. 정확 selector/ID/타임스탬프·저장 인용 구분은 보존한다. 새로고침·실제 페이지 선택·강조·실패/로딩·현재 권한 검증은 유지한다.
- 현재는 원문 문자 검색/열람이며 AI 답변·생성 UI는 아직 연결하지 않았음을 짧게 명시한다. 가상 결과·AI 실행 버튼·새 의존성·도메인/DB/API 변경은 추가하지 않는다.
- 데스크톱에서 주요 작업이 첫 화면에 있고 390px에서도 수평 넘침 없이 키보드/상태 표시가 동작해야 한다. 로그인 화면에 홈 전용 CSS가 번지지 않게 한다.
- 기존 readonly 수집 자료는 원문 해시/정확 위치/출처 연결이 확인되는 소량만 개발 공간에 추가한다. MySQL/원본 파일은 수정하지 않는다. 기존 AI 산출물을 원자료로 쓰지 않는다. 검증되지 않은 후보는 보류 이유를 기록한다.
- 실제 자료/이메일/UUID/연결 설정은 비공개 개인 파일에만 보관한다. 실DB 등록은 기존 도구·앱 역할·기존 초대 예약을 재사용하고 새 백업·대상 확인 뒤 idempotent append만 수행한다. 검색 투영·보호 조회까지 검증한다. 기존 계정/세션/권한 보존, reset/DDL/grant 없음.

## Task 1 · 자료 중심 UI

- [x] 홈·검색·읽기 화면을 위 요구사항대로 정돈하고 의미 있는 회귀 테스트를 RED→GREEN으로 확인한다.
- [x] 코드·품질 검토, 타입/린트/JS 테스트/빌드를 통과한다. 원문 위치·인증 동작을 바꾸지 않는다.

수정 범위: apps/web 중심, 기존 api-client를 소비한다. 필요하면 공통 표시 helper를 apps/web/app 내부에 둔다. 연결/링크 도구 기능은 지우지 말고 details로 축소한다. source ID는 보조 details에 보존하되 사람에게 중요한 출처/본문/유형/쪽수를 우선한다. 실제 날짜는 Intl 등으로 표시하고 원래 ISO값을 dateTime/details에 보존한다. 정확한 파싱 범위는 기존 계약을 사용한다. 개발자의 시스템 브라우저/사이트 탭을 열지 않는다.

## Task 2 · 기존 법안 메타데이터 어댑터

- [ ] 순수·오프라인 JSON 어댑터를 추가하고 RED→GREEN으로 입력·출력·해시·출처·정확 인용 계약을 검증한다.
- [ ] 독립 검토 후 기존 수집 DB 추출8건을 같은 어댑터로 검사한다. 실제 데이터는 테스트/Git에 넣지 않는다.

입력은 최대64KiB UTF-8 JSON bytes의 단일 Bill 필드 allowlist 객체다: bill_id, assembly_number, bill_name, bill_number, propose_date, committee, stage, bill_result, proposer_kind, bill_link. 모두 필수 key이며 committee/stage/bill_result/proposer_kind는 null 허용. gpt_summary/summary/파생 제목 등 다른 key·중복key·NaN·잘못된 UTF-8·NUL/줄바꿈/제어문자·빈 문자열·bool 숫자를 거부한다. 명시 SHA256과 raw bytes를 먼저 대조한다. bill_id는 ASCII 알파벳/숫자/underscore1..255, name/nullable text는1..255자, assembly는1..99 정수, bill_number는7자리 양의 정수(assembly와 앞2자리 일치), propose_date는 정확 ISO YYYY-MM-DD 실제 날짜, proposer_kind는 CHAIRMAN/CONGRESSMAN/GOVERNMENT/null이다. URL은 정확 https://likms.assembly.go.kr/bill/billDetail.do?billId=ID 하나만 허용하고 ID가 bill_id와 같아야 한다. 자동 다운로드/DB/파일/공급자/네트워크/로그 호출 없음.

결과는 frozen dataclass/동등 모델로 raw hash·byte수·text hash·공식 링크·원천ID·의안번호·제안일·parser/profile 이름/버전을 보존한다. 텍스트의 첫줄은 법안명, 두번째 줄은 “기존 수집 DB의 법안 기본 정보입니다. 법안 전문이 아니며 현재 처리 상태는 원문 출처에서 확인해 주세요.”를 명시한다. 이어 대수/의안번호/제안일/위원회/수집 당시 단계·처리결과/발의구분을 결정적인 순서·줄 구분으로 렌더링한다. null은 “미수집”으로 표시한다. 원천ID/URL은 메타데이터로도 보존한다. text 정규화로 원래 원문이라고 주장하지 않고 normalization_profile=legacy-bill-metadata-v1로 표기한다. 기존 ParsedRepresentation으로 변환하고 exact TextQuoteSelector를 만들 수 있어야 한다. 사용자 입력 dataclass를 직접 생성해 검증을 우회하지 못하도록 동일 불변 검증을 유지하거나 검증된 입력에서만 결과를 생성하는 내부 생성경계를 둔다.

수정 범위 packages/ingestion 모듈·export·합성 테스트·README, 기존 AuditError 고정 코드만 반환하며 원본 값/경로/예외를 공개하지 않는다. schema/API/의존성 추가 없음. 실제 8건은 제안일2026-03-30~2026-06-22이며 기존 DB SELECT만 했다. 메타데이터 사용은 내부 조사 범위이며 PDF/민간 본문 재이용 권한으로 확대하지 않는다.

## Task 3 · 실제 자료·개발 앱 반영 (controller 운영 작업)

- [ ] readonly 원문/manifest를 현재 확인하고 출처/페이지/인용·이용 범위를 검증해 선별한다. 불확실한 자료는 등록하지 않는다.
- [ ] 등록 가능 자료는 백업 후 기존 CLI로 추가하고 재실행 idempotence/검색 투영/보호 SDK 조회·기존 인증 보존을 확인한다. 불가하면 구체적 근거를 기록한다.
- [ ] 전체 검사·독립 전체 리뷰·브라우저 QA 후 개인 개발 HTTPS 앱 갱신, Draft PR/진행·작업 문서/Sites 요약 반영. main/운영 배포는 수행하지 않는다.
