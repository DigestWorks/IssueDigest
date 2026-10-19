# 서버의 수치·단위·문장 후보 인덱스

2026-10-19. PR52/97c4e61 후속 M3/D022. 사용자가 다음 오프라인 후보 경계 개발을 승인했다. OpenSpec root=null이므로 init 없이 이 단일 Spec/Task를 따른다. 기존 v3 실제2회 거부·v2 거부2·v1 부분1/거부1·앱4/12와 개발ab6654e/v9/main·운영 유예는 보존한다.

## Spec

AI가 글자 번호를 선택하기 전에 서버가 전체 인용에서 수치 표기·명시 단위·범위·인접 수식어와 문장 구간을 찾는다. 숫자 해석·계산·정규화·사실/대상/관계/상태 추론은 하지 않는다. 모델/DB/API/화면에 연결하지 않는 순수 결정적 후보 기반이며, controller가 기존 두 packet과 사전 고정된 합성 반례에서 누락/오탐을 직접 평가한다. 후보가 있는 것과 최종 브리핑의 의미 정확성을 구분한다.

## Global Constraints

- 기준97c4e61aab7db3c143dd587639b31867dc80c948, feat/numeric-candidate-index, PR52 기반 Draft. 기존 linked worktree·baseline5257/sourceCI39244869318을 재사용하고 baseline 전체 검사를 반복하지 않는다. 새 packages/agents/src/issuedigest_agents/numeric_candidates.py, 새 packages/agents/tests/test_numeric_candidates.py, agents README와 관련 Markdown만 수정한다. 기존 source/tests/fixtures/AGENTS·v1/v2/v3·역사 agent/worker/provider bytes·API/DB/공개/UI·수집기·의존성/lockfile·권한은 동결한다. 서버 접속/main 병합/개발·운영 배포 없음.
- 기존 numeric_evidence의 Source/_source_data/_plain/_StrictModel/_json과 QuoteProvenance를 순수 helper로 import할 수 있지만 바꾸지 않는다. exact Source tuple(UUID4 snapshot,EvidenceBundle,SourcePresentation), canonical 원문/unchecked extra/sid/workspace·원래 whole 인용1..20/합계≤12000 codepoints를 재검증한다. 제목/metadata는 수치 근거가 아니며 원문/인용을 자르거나 NFC/공백/숫자/단위를 정규화·계산하지 않는다. 현재 접근 권한은 향후 호출자 책임, hash는 인증·서명·진실·사람 검토가 아니다.
- API는 build_numeric_candidates(source:Source)->NumericCandidateIndex, validate_numeric_candidates(source:Source,index:NumericCandidateIndex)->NumericCandidateIndex, numeric_candidates_packet(source:Source,index:NumericCandidateIndex)->str 이다. module/호출은 provider/client/key/network/DB/파일 쓰기를 하지 않는다. 실패는 비공개 원문·ID가 없는 NumericCandidateError(ValueError)로 감싼다. 수리/부분 성공/추가 모델 요청은 없다.
- 모든 새 모델은 strict/frozen/extra-forbid다. ExactSpan은 citation_id:str,text:str(min1),start:int>=0,end:int>start의 원문 quote 상대 half-open Python Unicode code-point 구간이다. 원문을 그대로 slice한 text만 만든다. 문장 span은 공백도 허용하며 숫자 atom은 실제 ASCII 숫자를 포함한다. 모든 bound는 현재 quote로 다시 검사한다. 한 source의 ordered quote에서 모든 codepoint를 보존하고 결합문자/astral/control/NEL/BOM/반복 문자열을 이동·삭제하지 않는다.
- SentenceCandidate는 sentence_id=s1,s2,... 전역 연속 str와 span:ExactSpan이다. 각 quote를 LF 또는 .?!。！？ 뒤에서 분할하되 양옆이 ASCII 숫자인 소수점은 분할하지 않는다. 경계 문자를 앞 구간에 포함하고 빈 길이 구간을 만들지 않는다. 공백만인 구간도 보존하며 마지막 tail을 포함한다. 각 quote에서 시작0·인접 start=이전end·마지막end=len(quote), 원래 순서/원문 전체 partition이다. CRLF는 LF 경계로 보존한다. 이는 문법/의미 문장 분석이 아니며 URL/약어/구두점의 실제 문장 경계를 인증하지 않는다.
- NumericAtom은 number:ExactSpan,unit:ExactSpan|null이다. NumericCandidate는 candidate_id=n1,n2,... 전역 연속 str, `sentence_ids:tuple[str,...](1개 이상)`, expression:ExactSpan, `atoms:tuple[NumericAtom,...](1..2)`, separator:ExactSpan|null, `qualifiers:tuple[ExactSpan,...](0..2)`, lexical_kind:Literal[number,temporal,identifier,ambiguous]다. atoms1이면 separator=null,2면 명시 범위 separator필수. 모든 child는 같은 citation/연속 expression 내부의 물리 위치이며 atom/child의 순서·중복/겹침을 결정적으로 검사한다. expression은 전체 원문 표기를 보존하고 qualifiers/각 unit 사이 공백도 포함한다. sentence_ids는 expression과 실제로 겹치는 모든 문장 ID를 원래 순서로 담아 문장 경계를 넘는 후보도 버리지 않는다. 후보는 원문 순서로 겹치지 않으며 매칭된 숫자 영역을 중복 출력하지 않는다.
- 지원 숫자는 ASCII digits·정상 3자리 comma 그룹·소수·선행 +,-,−와 한국어 수 배율 십/백/천/만/억/조를 포함한다. '9만 9000', '3억 5천만', '-2.5', '1,200.5'의 원문 spelling을 보존하고 숫자로 변환하지 않는다. 명시 범위 ~,∼,～,–,—,-의 두 atom을 묶으며 각 끝의 단위 유무/불일치를 그대로 남긴다. '1~2호','1호~2호','21만 8000~23만 5000호','-2~-1'을 보존한다. 수와 단위/배율 사이 horizontal space/tab만 연결하며 LF를 건너 합성하지 않는다. 지원 밖 한글 수사·분수·지수 표기·새 단위의 완전 포괄은 주장하지 않는다.
- 명시 측정 단위의 유한 사전은 %p,%,bp,p,호,명,원,건,개,배,점,석,곳,km²,km2,㎢,km,m²,m2,㎡,m,kg,g,t 다. 긴 단위를 먼저 고르고 조사/어미는 단위에 넣지 않는다. temporal 단위는 개월,년,월,일,시,분,초이며 lexical_kind=temporal인 후보로 보존한다. 단위 부재는 null이며 지수의 단위를 추정하지 않는다. 한 atom의 명시 단위를 다른 atom/후보에 복사하지 않는다. 단위 뒤의 원문 조사는 expression 밖이다. 인접 prefix 약/최대/최소와 suffix 이상/이하/초과/미만은 qualifier exact span으로 따로 보존하고 expression에 포함한다. prefix/suffix 외부 문장을 조건/하한으로 추정하지 않는다.
- 온전한 YYYY-MM-DD 또는 YYYY/MM/DD는 하나의 temporal 후보로 우선 보존하며 실제 달력 날짜 유효성/정치적 사건 일자는 인증하지 않는다. 날짜는 atom.number에 전체 날짜 표기, unit=null, separator=null로 보존한다. ASCII +,- 또는 Unicode − 바로 뒤가 온전한 양식의 날짜이면 그 부호를 일반 숫자 atom으로 소비하지 않고 양의 YYYY-MM-DD/YYYY/MM/DD 표기 부분을 우선한다. 부호는 whole quote/문장 partition에 그대로 남기며 음수 연도·범위·식별자의 실제 의미를 판정하지 않는다. 법령의 제+ASCII digits+조/항/호는 일반 배율/단위보다 우선하는 identifier이며 expression은 제/접미사까지, atom.number는 digits만, unit=null이다. 그 외 붙은 이름의 identifier는 숫자 표기만 expression/atom에 담고 주변 이름을 끌어오지 않는다. 제12조/제3항/제2호, 숫자와 붙은 alphabetic/Hangul 이름/식별 접미사(기/구역 등)의 숫자는 identifier hint로 보존한다. 다만 명시 측정/시간 단위를 가진 정상 숫자는 우선 number/temporal이다. identifier는 숫자/표기 후보이지 법안/대상 의미 인증이 아니다. malformed comma/다중 소수점의 연속 digit/dot/comma 표기는 정상 값으로 쪼개지 않고 한 ambiguous atom으로 보존한다. 지원 사전 밖은 lexical hint일 뿐 확정된 수치 사실로 승격하거나 조용히 폐기하지 않는다. 알려진 단위가 없는 단독 정상 수는 number/unit=null이다. 분류 규칙·우선순위와 지원 밖 경계를 README에 명시한다.
- NumericCandidateIndex는 profile=numeric-candidates-v1,status=unreviewed,snapshot_id/workspace_id(UUID4),source_sha256(서버 _json(data.payload()) UTF8 SHA256),ordered `citations:tuple[QuoteProvenance,...]`,`sentences:tuple[SentenceCandidate,...]`,`candidates:tuple[NumericCandidate,...]`다. 최대 후보256개를 초과하면 전체 거부하고 앞256개만 반환하지 않는다. sentence 수는 Source bound로 제한된다. 빈 후보는 허용하되 완전 추출 인증이 아니다. 날짜/식별자/ambiguous도 cap에 포함하며 숨겨서 누락을 줄이지 않는다.
- validate는 exact index type/unchecked extra/field strictness를 재검증하고 현재 canonical Source로 전체 index를 재생성해 모든 ID/순서/문장 partition/span/text/종류/단위/수식어/후보 누락·추가/hash/provenance와 비교한다. model_copy/model_construct/숨은 extra/위조된 schema나 일관된 offset/text 변경도 원래 재생성 결과와 다르면 거부한다. 같은 quote/provenance의 metadata 변경은 새 의미 인증을 만들지 않는다. packet은 validate 후 index의 canonical JSON을 반환하며 원래 전체 인용과 중복 없는 문장/후보 참조를 포함한다. 숫자 계산/사용량 영수증/모델 지침·토큰 예산을 만들지 않는다. 향후 provider에 넘길 때 전체 schema/instructions/prompt budget을 별도로 검사해야 하며 이 packet을 provider-ready로 부르지 않는다.
- 구현자는 Task1만 합성 Source·실제 TDD로 구현/검증/자체 검토/commit한다. 원래 private 실제 packet/키/네트워크·서버/containers/full gate/push/PR/Sites/child agent는 쓰지 않는다. 기존 source/tests/AGENTS byte동일 manifest, new tests RED→GREEN/agents suite·Ruff/format/mypy·실측/지원 한계는 task report에 기록한다. 실제 fixed packet을 검사/하드코딩하지 않는다.
- controller가 동일 두 private packet(whole 인용2/1·기존 gold 수치6/5)·사전 고정한 합성 반례에서 모델0/추가 수집0으로 모든 후보/문장/null을 직접 읽고 quantity gold exact recall·누락·중복·잘못된 경계/단위/수식어와 날짜/식별자/ambiguous 잡음을 별도 집계한다. 과거 AI 응답과 후보 개수만 비교해 의미/앱 품질 향상을 주장하지 않는다. 새 parser의 유한 표기 포괄성·단위 사전 밖 누락·문장 구간 한계를 공개 기록에 남긴다. packet bytes와 v3 prompt bytes 비교도 provider 사용량/청구 절감의 증거가 아니다. 실제 원문/ID/키/gold/raw는 private에만 둔다.
- 단일 최종 전체 gate·작업/전체 독립 검토·PR52 기반 Draft/CI·Sites 이전v74 archive/현재 요약/native 게시·이번 소유QA1/SDD만 정리한다. source code/평가/gate/review/CI/Sites 사본/최종 docs-only head를 구분한다. 신규 provider 요청0/실제 앱 세션0·원래 AI 실패 분모/두 v3 판단과 비용·월10만원/기존 앱24000·개발v9·D013 유예를 유지한다. 사용자 탭을 열거나 이동하지 않는다.

## Task 1: 순수 수치·단위·문장 후보 기반

Read adjacent global-constraints.md (verbatim Global Constraints) first; binding exact requirements. This is the internal evidence foundation for B2C briefing, not a new consumer checkpoint or application integration.

- [x] 새 numeric_candidates.py에 위 strict 모델/finite lexical scanner·문장 전체 partition·모든 정확 span/안정 ID·범위 각 atom/단위·인접 수식어·temporal/identifier/ambiguous 보존·256 전체 거부·source 재생성 검증·canonical packet·sanitized error의 세 API를 구현한다. 기존 Source의 순수 검증 helpers를 재사용하되 기존 파일은 바꾸지 않는다. 규칙의 우선순위/지원 밖 한계는 의미 추론으로 숨기지 않는다.
- [x] 새 test_numeric_candidates.py를 먼저 써 정상 assertion RED→GREEN을 실행한다. 고정 합성 gold의 원문 offset/atom/unit/range/수식어와 순서, comma/소수/음수/한국어 배율/단위 양끝의 범위, 지수 unit=null·조사/어미 배제·다른 값에 단위 복사 금지, 날짜/식별자/ambiguous 잡음 보존·date/range 우선순위, 같은 문자열의 다른 물리 위치/여러 인용, 문장 소수점/구두점/LF·CRLF·공백/astral/결합/control·문장 경계를 넘는 range, canonical Source/stale/order/tamper/unchecked extra·현재값 전 field 재생성·빈0/256/257·Source20/12000 경계·잘못된 outer type/hash/provenance를 검증한다. import/모든 API가 provider/key/network/파일을 사용하지 않음을 격리 검사하고 packet의 전체 원문 보존을 확인한다. 구조 검증은 semantic truth/대상/관계/조건/전체 coverage 인증이 아니라는 반례도 잠근다.
- [x] agents README에 실제 API/모델/지원 문법·한계/단위 목록·strict 재생성/순수 packet과 provider 준비의 차이를 적는다. agents suite/Ruff/format/mypy·diff check와 기존 tracked source/tests/AGENTS/lockfile 동결 manifest를 확인하고 task-1-report.md에 RED/GREEN·명령/출력·측정·남은 concerns를 기록한다. 이 세 파일과 Task1 체크만 commit한다. controller의 다른 Markdown 변경은 stage하지 않는다. controller 평가/전체 gate/검토/PR/CI/Sites/정리는 별도다.

## Controller 인수

동일 private source를 재수집하지 않고 전체 후보/문장/필드를 직접 검토한다. 실제 수치6/5의 원래 표기/단위/하한·범위와 잡음을 구분해 누락/오탐을 집계한다. 합성 대조의 수치/날짜/식별자/미지원 표기 분모를 사전에 고정하며 실패를 수정된 gold로 숨기지 않는다. 새로운 외부 모델 호출은0이다. 의미·관계·앱/최종 브리핑은 별도 후속이다.

## 판단과 비용

1. 유한 표기 규칙과 단위 사전을 쓰고 날짜/식별자/모호한 숫자도 후보에 남긴다. 모델의 위치 계산을 줄이려는 선택이지만 미지원 표기가 누락되거나 후보 잡음이 늘 수 있다. cap 초과는 전체 거부하므로 자료 부족 종료가 늘 수 있다. 정규화·조용한 잘라내기로 숨기지 않는다.
2. 문장은 소수점 예외가 있는 구두점/LF 기반의 원문 partition이다. 원문을 빠짐없이 유지하지만 약어/URL·문장부호와 실제 언어적 경계가 다를 수 있다. 소비자는 이 구간을 대상/관계의 의미 인증으로 쓰면 안 되며 향후 문맥 선택 검증 비용이 남는다.


3. 날짜 양식 바로 앞의 +,-,−는 숫자 atom으로 흡수하지 않고 날짜 표기를 우선한다. 하이픈 범위와 날짜가 충돌해 원문이 조각나는 것을 막는 선택이다. 잘못되면 음수 연도/식별자에서 부호의 의미가 날짜 후보에 표현되지 않으므로 반드시 원문 문맥을 함께 검토해야 한다. 날짜·사실 의미는 인증하지 않는다.

## 서버 수치 후보 · 오프라인 인수 · 2026-10-19

source515aa26의 순수 후보 SDK를 기존과 byte-identical인 두 whole quote packet(인용2/1)에 오프라인 적용했다. 원문을 다시 수집하지 않았고 신규 provider/사용자 세션/앱 실행은 모두0이다. controller가 원문·모든 문장/후보의 expression/각 atom·unit/null·separator/qualifier·lexical hint/ID/원문 위치와 현재 Source 검증 결과를 직접 읽었다.

사전 고정 수치 gold6/5개는 모두 정확 후보로 보존됐다(11/11). 별도 날짜/식별자4/2개도 모두 남아 총 후보10/7개다. 하위 항목을 숫자 후보로 남기고 단위·하한/범위 양끝/명시 수식어를 원문과 연결했다. 지수 표기의 단위 부재는 null이며 증감의 명시 p를 다른 값에 복사하지 않았다. 이 결과는 수치 표기/위치 보존이며 대상·시점의 의미 연결/관측·전망/조건·포함 관계의 인수가 아니다.

별도 사전 고정 반례10건의 지원 표기 후보37개도 expression/atom/단위/수식어/종류/원문 위치가 기준과 일치했다. 범위·음수·배율·comma/소수·긴 단위/조사 배제·날짜/법령/이름 식별자·모호 표기·반복/Unicode/control/CRLF·줄바꿈 범위 분리를 확인했다. malformed comma/다중 점은 ambiguous로 보존하고 실제 달력에 없는 날짜도 temporal 표기 힌트일 뿐 날짜 진실로 인증하지 않는다. 지원 밖 한글 수사·전각 숫자 두 건은 추출0으로 따로 남겼다. 따라서 관측된 지원 후보의 누락/오탐0을 한국어 전체 수치 recall100%로 확대하지 않는다. 원래 gold·자료·분모를 수정해 성공시키지 않았다.

순수 index JSON은 두 자료에서6,012/3,593 UTF-8바이트이며 같은 자료의 v3 prompt3,548/1,567바이트보다 크다. 출처/위치 구조를 가진 저장·검증 packet이므로 provider-ready나 토큰/청구 절감으로 부르지 않는다. 향후 짧은 후보ID의 provider 계약과 전체 schema/instructions/framing/원문 budget preflight를 별도로 검증해야 한다. 이번 모델 사용량은 호출 자체가0이며 이전 v3 input4,485/output947의 실패 사용량·v3/v2 각각 거부2·v1 부분1/거부1·앱4/12와 모든 과거 실패/미판정은 보존한다.

작업 검토에서 배율 continuation의 하이픈 범위 흡수/날짜 우선순위 우회, 초과·미만 suffix 충돌3건을 찾았다. 각 RED→GREEN으로 수정하고 수정 범위 재검토에서 모두 해결(C0I0M0)됐다. 신규151/agents1074·Ruff/format42/mypy16와 기존409파일 base/fix byte동일을 확인했다. 수정 전의 사전 전체 검사는 중단하고 구 source CI39248144627은 cancelled로 보존했다. 이들은 최종 gate/CI 성공 증거가 아니며 수정 후 단일 최종 전체 검사·전체 독립 검토/CI는 별도 인수한다.

다음은 서버가 확정한 후보ID를 모델이 선택하는 출력 계약을 만들고, 수치 대상·시점·상태/조건·관계 의미와 누락을 같은 자료에서 검증하는 것이다. 그 뒤 앱의 전역 예산/예약·DBOS 실행/중단 복구·현재 권한/취소·최종 브리핑을 함께 인수한다. 유한 문법/단위 사전의 누락/잡음·cap256 전체 거부와 구두점/LF 문장 경계의 문맥 비용은 Spec/D022에 남긴다. 개발ab6654e/v9·API/DB/공개/UI/수집기/월 예약은 유지하며 main/운영은 D013 유예다.


### 날짜 경계 최종 수정과 고정 대조 재검증

전체 독립 검토에서 범위 우측의 날짜를 거절한 뒤 하이픈을 음수로 다시 읽는 추가1건을 찾았다. 같은 최종 수정 wave에서 suffix·부호 경로도 회귀로 묶고 공통 atom 진입점에서 온전한 날짜 우선순위를 지켰다. source b8987c6의 신규180/agents1103·Ruff/format/mypy와 한정 최종 재검토 Spec/품질 PASS(C0I0M0)를 확인했다. 원래 작업 Rework3건/수정 재검토와 전체 Rework1건/최종 재검토를 모두 보존한다. 구 source515aa26의 두 번째 전체 검사도 수정 전에 중단했고 CI39248752093은 cancelled다. 처음의 source5f9df97 중단/CI39248144627 cancelled와 함께 최종 성공에서 제외한다.

같은 source b8987c6로 사전 고정 gold를 바꾸지 않고 다시 대조했다. 원문/문장/후보와 비교24파일은 이전515aa26과 byte-identical이므로 controller의54후보 전 필드 직접 검토가 유지된다. 수치11/11·부수6/6·지원 반례37/37·미지원2건·모델0/앱0·의미 미검증은 같다. 기존409 git blob의 baseline/final source 동일성도 확인했다(이후 controller Markdown 제외). 새 최종 전체 검사/source CI39251010224와 Sites/정리는 별도 결과를 기록한다.

세 번째 판단은 +,-,− 바로 뒤 완전 날짜를 우선하는 것이다. 음수 연도·식별자 부호의 의미는 날짜 후보에 없으므로 원문 확인이 필요하다. 유한 문법/잡음·cap256 거부, 구두점/LF의 실제 문맥 경계 차이라는 앞선 두 판단의 비용도 유지한다.


## 전체 구현 인수

sourceb8987c6의 최종 전체5,437개·lint/format/types/build/OpenAPI contract와 작업 수정 재검토/전체 독립 Spec/품질 PASS(C0I0M0)를 확인했다. [Draft PR53](https://github.com/DigestWorks/IssueDigest/pull/53)/source CI39251010224·Sites/소유QA·SDD의 후속 기록은 [진행 기록](../planning/progress.md)을 따른다. 같은 실행 코드 이후 변경은 Markdown뿐이다. 순수 후보의 오프라인 지원 범위 인수와 실제 모델 의미/앱/최종 브리핑은 구분하며 모델0·미지원2건·세 Ruling/비용·개발v9/운영 유예를 보존한다.
