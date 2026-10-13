# PDF 페이지 텍스트·정확 인용 준비

2026-10-13. R2와 P2의 다음 부분 구현. 파일 후보 검사 다음으로 PDF bytes에서 페이지별 텍스트를 추출하고 기존 ParsedRepresentation/PdfQuoteSelector/validate_citation 계약을 소비한다. 공급처의 원문 동일성·등록번호 대응·이용 조건은 이 작업으로 증명하지 않는다.

## Task 1: 제한된 PDF 추출·기존 계약 어댑터·CLI

### 요구사항과 설계

`packages/ingestion`을 확장한다. pypdf **6.20.1**만 새 외부 직접 의존성으로 고정하고 기존 domain 패키지를 workspace 의존성으로 사용한다. Python3.13에서는 pypdf 기본 설치의 추가 런타임 의존성이 없으며 BSD-3-Clause다. 페이지 텍스트와 기존 페이지 인용 계약을 연결하는 첫 범위로 선택한다. 표 구조·좌표·OCR은 이번에 추정하지 않는다. 공식 근거: [pypdf 저장소](https://github.com/py-pdf/pypdf), [텍스트 추출의 한계](https://github.com/py-pdf/pypdf/blob/main/docs/user/extract-text.md). pypdf를 모든 문서에 가장 정확한 파서로 확정하는 결정이 아니다.

공개 라이브러리 `extract_pdf_text(data_root, pdf_path, expected_sha256, *, limits=...)`와 불변 `PdfExtraction`, `PdfLimits`를 제공한다. pdf_path는 root 상대 `pdfs/` 아래의 일반 파일만 허용한다. 절대 경로·`..`·NUL·역슬래시·symlink 조상/파일·특수 파일을 거부한다. root는 명시적으로 전달한다. 모든 입력 경로를 descriptor 기반으로 열고 원본에 쓰지 않는다. expected_sha256은 정확한 소문자 hex64 문자열이며 필수다. source 파일을 청크로 읽어 전체 해시와 크기·identity/mtime/ctime 전후를 확인하고 익명 임시 파일에 복사한다. 기대 해시 불일치/파일 변경/헤더 없음은 파싱 전 거부한다. 파서는 확인한 임시 bytes만 읽는다. 원본 PDF 전체를 부모 메모리에 담지 않는다.

PDF 파싱은 별도 Python subprocess에서 수행한다. Linux만 지원한다. 작업 프로세스 내부에서 PDF 라이브러리를 import하기 전에 resource 한도를 적용한다. 입력/출력은 익명 임시 파일과 명시적으로 전달한 FD이며 shell을 사용하지 않는다. 기본 한도: PDF128MiB, 200페이지, 추출 텍스트1,000,000 code points, wall30초, CPU30초, 주소공간512MiB, 출력16MiB. PdfLimits의 값은 양의 정수만 허용하며 bool/0/음수/문자열/실수는 거부한다. 한도 변경은 라이브러리에서 명시적으로 가능하며 CLI는 PDF/페이지/텍스트/timeout 한도만 노출한다. 시간 초과 시 자신이 시작한 자식만 종료·회수한다. 모든 FD/임시 파일을 성공·실패에 정리한다. 파서의 stderr/log/warning과 native 예외·경로·PDF 내용은 공개 출력에 노출하지 않는다. 실패는 고정 오류 코드다. 무조건 재시도하지 않는다.

pypdf strict=True로 읽고 암호화된 PDF는 비밀번호 시도 없이 거부한다. 페이지 순서대로 plain 텍스트를 추출하며 Unicode 정규화/trim/fuzzy matching을 하지 않는다. 페이지 사이 구분자는 정확히 `\n\f\n`이다. 빈 페이지는 실제 1-based 번호를 empty_pages에 남기며 비어 있지 않은 페이지의 start/end는 최종 text의 Python code-point 구간이다. 모든 페이지가 빈/공백 텍스트이면 `no_extractable_text` 실패로 표시하며 OCR을 자동 실행하지 않는다. 파서 버전·normalization_profile `pypdf-plain-v1`·실제 원문 해시·크기·page_count·text_sha256을 결과에 남긴다. 손상 PDF·페이지/텍스트/출력 초과·파서 종료/timeout·invalid Unicode는 실패이며 부분 결과를 완료로 내보내지 않는다.

`to_pdf_representation(extraction, *, document_version_id, representation_id)`는 호출자가 명시한 UUID4로 기존 ParsedRepresentation을 만든다. 새 SourceDocument/DocumentVersion/EvidenceBundle을 만들지 않는다. parser_name=pypdf, parser_version=6.20.1, normalization_profile=pypdf-plain-v1, tables=()이며 text/hash/PageSpan 검증을 기존 계약으로 수행한다. 빈 페이지 번호 때문에 페이지 번호를 재배치하지 않는다. 위치 좌표를 만들어 넣지 않는다.

`locate_pdf_quote(representation, quote, *, page_number=None)`는 정확한 원문 문자열을 찾고 한 페이지 안의 유일한 매치에 대해서만 기존 PdfQuoteSelector를 반환한다. 비어 있거나 공백뿐인/유효 UTF-8이 아닌 quote, 유효하지 않은 페이지 번호, 없음, 여러 매치, 페이지 경계에 걸친 매치를 고정 오류로 거부한다. 중복 문자열은 명시 페이지 범위를 지정해 유일할 때만 허용한다. regions=()이다. 테스트에서 실제 validate_citation으로 위치 일치와 support not_evaluated를 확인한다. 정확 quote 일치는 기존 AI 수치·주장/원문 동일성의 검증이 아니다.

CLI: `issuedigest-ingestion inspect-pdf --data-root PATH --pdf-path pdfs/relative.pdf --expected-sha256 SHA [--private-manifest PATH]`와 위 네 한도 옵션. 기존 audit-polls의 출력/명령/기본값/오류를 보존한다. inspect-pdf의 기본 stdout은 JSON 집계 하나: format_version=issuedigest-pdf-text-summary-v1, status=completed, page_count, empty_page_count, text_characters, raw_bytes, source_verification=not_evaluated. 해시·텍스트·경로·원문 URL/등록번호·UUID는 공개 출력하지 않는다. 실패는 같은 format_version/status=failed/error=고정코드와 exit2, 성공은 exit0이다. 상세 결과는 opt-in으로만 기존 안전한 private manifest 저장기를 소비해 data root 밖 새600 파일에 저장한다. 상세에는 추출 텍스트/페이지/hash/parser 메타데이터를 담고 원문 bytes는 복제하지 않는다. 상세 저장 실패에 성공을 내보내지 않는다. 결과 형식과 각 오류는 README에 기록한다.

새 테스트는 합성 임시 PDF만 사용한다. 실제 최소 유효 PDF(둘 이상 페이지, 빈 페이지, 반복/문자경계/한글·BMP 밖 이모지·결합 문자)를 만들어 실제 pypdf/subprocess를 검증한다. PDF 생성에는 새 런타임/테스트 외부 의존성을 추가하지 않는다. 실제 assertion RED→최소 구현→GREEN 기록을 남긴다. 해시 mismatch, 파일/경로 안전, PDF 깨짐/암호화/무텍스트, 실제 페이지/텍스트 한도, timeout·비정상 자식 종료·출력 상한의 저수준 fault injection, 부모 원문 변경 없음·자식 회수·집계 프라이버시·개인 파일 덮어쓰기 거부와 기존 CLI 회귀를 검증한다. 프로토콜을 받은 부모가 자식 결과를 검증해야 하며 자식 JSON을 신뢰해서 타입·hash·페이지 구간을 생략하지 않는다.

### Global Constraints

- No operating/source writes, database migrations/calls, network/model calls, source verification claims, or automatic imports.
- Read only an explicit regular PDF under data_root/pdfs with no symlink traversal; require and verify the caller's expected SHA-256 before parsing a bounded private snapshot.
- Extraction and exact quote anchoring do not prove source authenticity, survey identity, factual support, table semantics, OCR, or geometry; consume existing contracts without modifying API/generated types.
- Default CLI output contains aggregates/fixed errors only; details are opt-in, outside the source root, exclusive mode600 and excluded from Git/Sites.
- Parsing runs in a bounded Linux subprocess; limit/failure never publishes completed partial results. Existing pinned dependencies and audit-polls behavior remain intact.

### 작업 항목

- [ ] 명시 입력·snapshot·자식 한도·파싱·부모 결과 검증과 불변 결과/한도 구현.
- [ ] 기존 계약 어댑터·정확한 유일 quote 선택과 실제 anchor 검증 테스트 구현.
- [ ] inspect-pdf 집계/개인 출력·기존 CLI 회귀와 문서·고정 의존성 구성.
- [ ] 합성 assertion RED/GREEN·새 테스트·타입/린트·전체 검증 보고서와 구현 commit.

## 컨트롤러 결합

독립 작업/전체 변경 리뷰와 실제 합성 PostgreSQL 포함 전체 검증 후 서버 사용자 worktree에서 대표 후보 최대6개(서로 다른 PDF 해시)의 추출을 실행한다. 기존 question_text와 정확 일치 여부를 개인 환경에서 계산하고 집계만 기록한다. 일부 문항의 정확 매치도 모든 문항·조사·수치의 검증이 아니며 전수225개 성공으로 표시하지 않는다. 실제 원문·개인 manifest/텍스트·해시/경로·질문은 커밋하지 않는다. DB 이관·공급처 요청·운영 설치/서비스 변경은 하지 않는다. PR은 선행 #12 위 Draft로 작성하고 Sites 요약·이전 기록을 보존한다. 첫 제품 이슈·자료 이용 조건은 사용자/동료 결정으로 남긴다.
