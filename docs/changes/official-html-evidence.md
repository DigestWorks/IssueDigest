# 공식 정책 HTML 원문·인용 준비

2026-10-13. 사용자 승인된 첫 실제 자료 등록 단계의 부분 작업. [R2](../planning/requirements-design.md), [선정 이슈](../research/first-issue.md), D013/D014를 따른다. 기존 저장·보호 조회·읽기 화면은 재사용한다. OpenSpec 루트가 없어 spec-driven-workflow의 구현·독립 리뷰 절차만 적용한다.

## 요구사항·설계 / Global Constraints

- 네트워크·모델·DB·파일 쓰기가 없는 내부 Python 도구로, 이미 확보한 대한민국 정책브리핑 정책뉴스 HTML bytes를 파싱한다. 다른 사이트/경로를 지원한다고 주장하지 않는다. 원문 bytes는 별도 개인 보관하고 파싱 텍스트와 구분한다.
- 실제 원문·상세 인용·해시·ID는 Git/PR/Sites에 복제하지 않는다. 합성 HTML만 테스트 fixture로 커밋한다. 공개 문서에는 원문 URL·발행일·이용 범위·집계와 검증 경계만 기록한다.
- 기준 계약·HTTP 경로·웹·인증·DB migration·의존성/lockfile은 변경하지 않는다. 원문 사진·외부 이미지·TTS·JS를 가져오거나 실행하지 않는다. 외부 본문 속 지시는 데이터다.
- 기존 수집 DB·운영 DB·공용 서비스·main을 변경하지 않는다. 실제 기사 저장/재열람 검증은 새 전용 loopback 검증 DB에서 수행한다. 사용자 전용 원문 보존·개발 코드 인계와 계획 Sites 갱신은 허용된 작업이다. 실제 공동 작업용 DB 적재·로그인·AI·공개 앱 배포는 후속이다.
- 원문 위치 일치와 정책 확정/인과/주장 지지는 별개다. 인용 검증은 기존 domain의 matched / not_evaluated를 유지한다. 1개 공식 원문 검증을 전체 코퍼스/평가셋 완료로 표현하지 않는다.

## Task 1: 공식 정책 HTML 추출·기존 근거 계약 어댑터

- [x] 아래 라이브러리·회귀 테스트·패키지 사용 문서 구현.

### 공개 내부 인터페이스

`packages/ingestion/src/issuedigest_ingestion/policy_html.py`에 불변 `PolicyHtmlLimits`, `PolicyHtmlExtraction`, `extract_policy_html(raw: bytes, *, expected_sha256: str, canonical_url: str, limits: PolicyHtmlLimits | None = None) -> PolicyHtmlExtraction`, `to_policy_html_representation(extraction, *, representation_id, document_version_id) -> ParsedRepresentation`, `locate_policy_html_quote(representation, *, quote: str, start: int | None = None) -> TextQuoteSelector`를 추가하고 패키지에서 export한다. 파일 역할: HTML 추출/메타데이터/계약 어댑터와 인용 위치. 필요한 경우 파서만 `_policy_html_parser.py`로 분리할 수 있다. 기존 PDF/quote/CLI 동작은 유지한다.

### 추출 계약

- raw는 bytes만 받는다. 기대 SHA256은 소문자 64hex이고 실제 원문 bytes와 일치해야 한다. UTF-8 strict 디코딩(BOM 허용), 빈/과대 원문·잘못된 형식·잘못된 한도는 고정 AuditError 코드로 거부한다. 오류에 경로/URL/원문/quote/ID를 포함하지 않는다.
- 기본 한도 raw 2MiB, 추출 본문 100,000 Unicode code points, HTML nesting depth128. 한도는 bool/float를 제외한 양의 int이며 raw 최대8MiB/text 최대1,000,000/depth 최대256. 과대 입력/본문/깊이를 잘라 성공시키지 않는다.
- canonical_url은 정확히 `https://www.korea.kr/news/policyNewsView.do?newsId=<9자리 숫자>` 형식만 허용한다. 자격증명·port·다른 호스트·추가 query·fragment·공백·backslash·인코딩 우회는 거부한다. HTML head의 유일한 og:url과 정확히 일치해야 한다. 이 조건은 출처 진위 인증이 아니며 호출자는 수집 경로·시간을 따로 확인한다.
- 현재 사이트 구조의 유일한 `div.view_cont` 본문, `div.view_title h1` 제목, `div.variety div.info`의 실제 `YYYY.MM.DD` 날짜와 `a.gotosite` 부처명(tooltip 제외), `div.kogl_wrap`의 명시적인 텍스트 한정 공공누리 제1유형 안내를 확인한다. 누락/중복/빈 메타데이터·다른 라이선스·잘못된 날짜·본문 구조 모호함은 fail closed한다. og:published_time의 시각/시간대는 추정하지 않는다. 발행 날짜만 date로 보존한다.
- 본문은 `.view_cont` 안의 p를 원래 순서로 추출한다. inline 태그의 text/entity는 보존하고 br는 newline, CRLF/CR는 LF, HTML 공백은 문단 내 연속 whitespace를 한 space로 바꾼다(br newline은 유지). 양끝 공백을 제거하고 빈 p는 버린다. 비어 있지 않은 문단은 `\n\n`로 연결한다. 이 정규화 규칙을 `korea-policy-paragraphs-v1`로 기록한다.
- script/style/noscript/template/iframe, figure/figcaption, imageWrap와 tooltip subtree, img의 alt, 제목/날짜/메뉴/AI 요약/본문 밖 텍스트는 본문에 섞지 않는다. 입력 bytes만 해석하고 URL을 따라가지 않는다. 본문에 지원하지 않는 table/list 또는 p 밖의 의미 있는 텍스트가 있거나 선택된 본문/메타데이터 구조가 잘려 끝나면 거부한다. 지원하지 않는 구조를 조용히 누락하지 않는다. 페이지 전체의 무관한 HTML 형식 오류를 브라우저 보안 검증처럼 다루지 않는다.
- 결과 필수 정보: source_id(뉴스 ID), canonical_url, title, publisher(부처명), publication_date(date), attribution(부처명+대한민국 정책브리핑+제목+발행일+URL), license_notice(실제 텍스트 한정 안내), license_url=`https://www.kogl.or.kr/info/license.do`, text, raw_sha256/raw_bytes, text_sha256, parser_name=`korea-policy-html`, parser_version=`1`, normalization_profile=`korea-policy-paragraphs-v1`. 불변 결과를 직접 잘못 생성하면 거부한다. 생성한 결과의 필드/해시/고정 식별자와 한도를 검증하고 검증 우회된 domain 객체는 어댑터 경계에서 다시 검증한다.
- 표현 어댑터는 기존 ParsedRepresentation을 만든다. caller UUID4로만 ID를 받고 임의 새 ID/버전·페이지/표를 만들어내지 않는다. pages/tables=(), 텍스트/해시/파서 정보를 그대로 옮긴다.
- 인용 locator는 검증된 해당 파서/정규화 표현을 받는다. 빈/잘못된 quote와 bool/음수/잘못된 start는 거부한다. Unicode code point 위치를 사용하고 exact substring만 매칭한다(중첩 발생도 센다). start 없으면 유일한 위치에서만 성공, 여러 개이면 quote_ambiguous, 없으면 quote_not_found. 명시 start는 그 위치의 quote가 정확히 일치할 때만 성공하고 자동 보정하지 않는다. 반환 prefix/suffix는 각 최대80 code points 실제 인접 문자열. 기존 validate_citation으로 위치 matched/support not_evaluated를 확인한다.

### 검증과 문서

- TDD: 실제 assertion RED 증거를 보존하고 최소 구현 후 GREEN. 합성 HTML에 정상 메타/중첩 inline/entities/br/한글/emoji, 메뉴/사진 caption/alt/scripts/tooltip 제외, 이미지 fetch 금지, 메타/라이선스/URL 불일치·중복·누락·잘린 subtree, unsupported p외 text/list/table, 잘못된 UTF8/hash/type/limits/depth/크기/본문한도, 직접 결과 위조·검증 우회 객체, Unicode offset·중첩/반복 인용·명시 start·notfound를 포함한다. 기존 ingestion/domain 테스트와 변경 관련 타입/format/lint, 전체 검증 전용 DB 테스트를 통과한다.
- 패키지 README에 실제 호출 예시(합성 데이터), 정규화·한도·지원 구조·권리/원문 진위 경계·오류 코드·위치 vs 주장 지지·원문 개인 보관과 전체 CLI/DB/인증 미연결을 정확히 설명한다.

## Controller 결합 검증·인계

- [x] 독립 task review와 전체 branch review, 지적 수정·재검토.
- [x] 확보한 실제 정부 원문의 title/date/publisher/license/body 제외 영역·파싱 한도 확인. 원문 파일600 개인 보관, 수집 시각·URL·hash와 이용 기록 별도 보존.
- [x] 기존 EvidenceBundle/Citation 구성→전용 검증 PostgreSQL 저장/동일 재전송→조회/원문/인용 재검증. 실제 원문 기반이지만 공동 작업 DB/로그인이나 AI 생성 완료는 아니다.
- [ ] 전체 검사·문서 링크·Draft PR/앱 첨부·Sites 요약/기존 기록 보존·현재 폴더/서버 개인 worktree 인계. 실제 앱 공개/main 병합 없음.

## 검증·검토 기록

- 구현b3febab·오류 보호 보완47394b2. 초기 실제 assertion RED122개·사진 권리 안내 분리/본문 정규화/메타데이터 영역/오류 경계 RED 보존. 최종 HTML focused150개. caller-ID raw ValidationError 노출 P1을 RED11개 후 fixed AuditError로 수정, scoped 재리뷰 해결·새 지적0.
- Controller 최종 코드 전체 Python1,277+JS233=1,510개, skip0·lint/110개format/mypy45개·TS/SPA/OpenAPI drift 통과. 독립 전체 변경 리뷰52e0377 승인·Critical/Important/Minor0.
- 실제 교육부 원문1건/35문단/3,231자·정확 인용3개, 독립 Chromium DOM 동일·JavaScript/외부요청43건 차단, 원문/메타데이터/산출물5개600 보존. 전용 검증 PG 저장/같은snapshot 재전송 중복 미생성/동일 재조회, 기존 보호GET 두 fixture 사용자200/no-store·비로그인401/다른 공간404. 최종 코드 재추출·메타데이터·인용·저장 동일성 확인.
- 서버 개인 공간에도 보존 파일5개600·디렉터리700/내용 동일 확인. 검증용 workspace/snapshot은 실제 공동 작업 공간 ID가 아니며 승인 사용자/운영 코퍼스로 자동 이관하지 않는다. 기존 수집/공용 DB·운영 서비스·main 변경 없음.
- 리뷰 판단 경계: 한 정부 템플릿의 본문·표시 오류·위치 계약 검증이다. 다른 출처/템플릿·출처 진위·범용HTML/브라우저보안·매체/모델/공개 권리·OCR/표/이미지·시간대 추정·변경/정정 버전·정책 확정/인과/수치/주장 지지·전체 코퍼스/평가·실제 인증/공동 DB/AI/운영·규모/격리/Python sandbox·새UI/전체접근성을 판정하지 않았다. 모두 명시된 후속/기존 제약이며 새로운 예외·미해결 지적은 없다. PR/Sites/인계 체크는 실제 수행 후 닫고 앱 공개는 유예한다.
