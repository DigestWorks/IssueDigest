# PDF 인용 후보·문맥 선택

2026-10-13 한국 시간. R2/P2의 다음 부분 구현이며 전체 자료/표·제품 화면 연결은 후속이다. 선행 feat/pdf-text-evidence / Draft PR #13에서 분기한다. 사용자 요청은 추가 관리자 요청 없이 개발을 이어가는 것이다. OpenSpec root null로 해당 단계는 생략하고 기존 요구사항을 바탕으로 SDD/TDD·독립 리뷰·실제 PG 전체 검증을 적용한다.

## 문제·수용 기준

기존 정확 locator는 문항이 반복되면 quote_ambiguous를 반환한다. 같은 비무작위 PDF6개를 재조사한 결과35문항/87일치 위치,35문항 모두 여러 페이지·4문항은 같은 페이지에서도 반복된다. 각 문항에 유일한 페이지 매치/앞뒤80자 문맥 조합이 하나 이상 존재하지만 어느 후보가 조사/표의 올바른 근거인지는 판단하지 않았다.

이번에는 인용 후보와 정확한 페이지·문맥 선택을 제공한다. 원문에서 수치를 파싱하거나 특정 문항/표를 자동 대응하지 않는다. 기존 ParsedRepresentation/PdfQuoteSelector/Citation 계약과 extract_pdf_text/locate_pdf_quote/CLI·의존성을 유지한다. 실제 PDF/질문/문맥·경로/해시/UUID는 Git·Sites·공개 출력에 넣지 않는다.

## Global Constraints

- No operating/source writes, database migrations, runtime network/model calls, new dependencies, API/generated-type changes, or automatic imports.
- Consume validated ParsedRepresentation and existing PdfQuoteSelector/Citation contracts; preserve existing extract_pdf_text, locate_pdf_quote and CLI behavior.
- Match exact Unicode/code-point strings, including overlapping occurrences; never normalize, trim, fuzzy-match, rank, or silently select the first candidate.
- Bound text scanning, examined occurrences, returned candidates and preview contexts; a search-limit failure never publishes completed partial results or a unique selection.
- Quote and supplied context must fit one page to create a selector. Matching cross-page occurrences remain unanchorable and cannot be silently discarded when deciding uniqueness.
- Candidate/anchor matching proves position only; source authenticity, survey/table identity, numeric/factual support, geometry, OCR and product permissions remain unevaluated. Real contents and detailed outputs stay private and outside Git/Sites.

## Task 1: 인용 후보 검색·정확한 문맥 선택

작업 범위는 ingestion 패키지·테스트·패키지 README와 필요한 root README 한 줄이다. controller가 계획/진행/작업 문서·실제 서버 대조·PR/Sites·인계를 담당한다. 새 외부 의존성·도메인/API 계약은 만들지 않는다. 기존 pdf.py가 커지는 것을 피하고 quote 검색은 별도 모듈에 둔다.

공개 불변 PdfQuoteSearchLimits: max_text_characters=1_000_000, max_occurrences=10_000, max_candidates=100, context_characters=80. 모든 값은 exact int이며 bool/문자열/float 거부. text/occurrence는 양수, candidates는1..1000, context는0..200. 잘못된 값은 invalid_quote_search_limits. 구현이 반환하는 불변 PdfQuoteSearchResult는 representation_id/document_version_id/text_sha256, candidates(tuple[PdfQuoteSelector,...]), occurrence_count, candidate_count, cross_page_match_count, has_more를 제공한다. occurrence_count는 지정 페이지 또는 전체 text의 정확 매치 총수이며 candidate_count는 한 페이지 안의 anchor 가능한 총수다. cross_page_match_count는 어느 PageSpan에도 완전히 들어가지 않는 매치 수다. has_more는 반환 후보 수<candidate_count일 때만 true. 새 결과는 미평가 위치 후보이며 EvidenceBundle/문서 버전을 생성하지 않는다.

find_pdf_quote_candidates(representation, quote, *, page_number=None, limits=PdfQuoteSearchLimits())는 모든 겹치는 매치를 start+1로 진행하며 원문 offset 순으로 후보를 반환한다. 지정 페이지는 기존 PageSpan만 허용하고 실제 번호를 유지한다. quote validation은 기존 invalid_quote, page validation은 invalid_page_number 의미를 유지한다. 없는 문자열은 빈 성공 결과이며 명시 페이지 범위를 벗어나는 매치는 조사하지 않는다. 각 후보는 실제 quote/start/end/page_number, regions=(), 페이지 경계 안의 앞뒤 최대 context_characters를 prefix/suffix로 보존한다. 텍스트가 없는 context/0자 설정은 None이며 공백 문맥은 정규화하지 않는다. 반환 배열 한도에 도달해도 끝까지 제한된 수를 세어 has_more와 총수를 정확히 보고한다. max_occurrences를 초과하면 quote_search_occurrence_limit_exceeded, text 한도 초과는 quote_search_text_limit_exceeded로 실패한다. quote 길이/반복에 비례하는 무제한 별도 배열을 만들지 않는다.

resolve_pdf_quote(representation, quote, *, page_number=None, prefix=None, suffix=None, limits=PdfQuoteSearchLimits())를 추가한다. 입력 prefix/suffix는 None 또는 비어 있지 않은 유효 UTF-8 문자열이며 각각 최대200 code points; 공백은 유효한 정확 문맥이다. 잘못된 값은 invalid_quote_context. supplied prefix/suffix가 정확히 인접하고 quote와 함께 한 페이지 안에 있을 때만 후보가 된다. 반환 selector에는 supplied 문맥을 그대로 넣고 제공하지 않은 문맥은 None이다. 일치0은 quote_not_found, 전체 조건에 맞는 occurrence가 여러 개면 quote_ambiguous, 단일 매치가 페이지 경계를 건너거나 제공 문맥이 페이지 범위를 넘으면 quote_crosses_page로 거부한다. cross-page quote도 full text에서 supplied adjacency가 맞으면 uniqueness count에 포함한다. 유효 quote의 supplied context가 다른 페이지/페이지 밖 gap을 침범하는 매치도 unanchorable로 세어 유일성을 숨기지 않는다. 어떤 한도 실패나 잘린 후보 목록으로 단일성을 추론하지 않는다. 문맥 없이 유일한 매치/지정 페이지의 동작은 기존 locator의 사례와 일치하되 새 resolver의 명시 한도는 적용한다. 기존 locator는 변경하지 않는다.

공개 fixed errors는 새 한도/문맥 코드와 기존 invalid_quote/invalid_page_number/quote_not_found/quote_ambiguous/quote_crosses_page뿐이다. 오류에 text/quote/context/path/ID를 넣지 않는다. caller-owned 유효 모델이 입력이라는 기존 계약을 유지하며 model_construct 같은 validation 우회가 신뢰 경계를 바꾸지 않도록 문서화한다. 소비자는 선택 결과를 기존 validate_citation으로 검증한다.

TDD는 합성 임시 representation/PDF만 사용한다. 구현 전에 실제 assertion RED를 기록한다. 다른 페이지/같은 페이지 반복·overlap·prefix-only/suffix-only/양쪽·잘못된 문맥/공백/Unicode·BMP 밖 문자/결합 문자·실제 페이지 번호 gaps·문자열 없음·단일 crossing/유효+crossing 중복·문맥의 페이지 경계 침범을 검증한다. candidate truncation·exact boundary/exceeded limits·타입 거부·불변성·identity 및 실제 validate_citation matched/support not_evaluated·기존 locator/CLI 회귀를 검증한다. 동일 구현을 복제하는 테스트/새 외부 fixture 의존성은 피한다. codepoint/offset 기대값은 손으로 확인한 합성 문자열로 검증한다.

- [ ] 후보/한도/불변 결과·집계/preview·유일 문맥 선택 구현.
- [ ] 합성 assertion RED/GREEN·한도/경계/실제 인용·기존 회귀 검증.
- [ ] ingestion/root 문서·고정 의존성 보존·전체 검사·자체 검토 보고/commit.

## Controller 결합

독립 작업/전체 변경 리뷰·controller 실제 전용 합성 PostgreSQL18.6 포함 전체 npm run check 이후, 서버 사용자 worktree에서 같은6개/35문항의 후보 집계를 새 API로 계산한다. 모든 반환 후보와 테스트용 명시 페이지/문맥 선택을 실제 validate_citation으로 검사하되 올바른 문항/표의 후보를 판정한 것으로 표시하지 않는다. 첫 후보를 선택하는 QA는 오직 위치 어댑터 round-trip 검사로 표시하고 제품 자동 선택으로 구현하지 않는다. 상세 원문은 메모리/개인 환경 밖으로 내보내지 않는다. DB/수집 원문/공유 서비스/실제 제품 앱 배포나 모델 호출은 하지 않는다. 선행 #13 위 새 Draft PR·Sites 요약/이전 기록 보존·로컬/서버 인계를 완료한다.
