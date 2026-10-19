# Evaluation

실제 자료의 검색·근거·관계·생성 화면 평가 기준을 보관한다. 공개 질문/기준과 비공개 원문/인용/버전 정보를 구분한다.

- [지방국립대 등록금 지원 · 질문20개](first-issue.md): 문항 정의 완료, 실제 검색/AI 실행 전. 필요한 근거·부족한 자료·기대 화면·판정 기준을 포함한다.
- [자료 상태](../../docs/research/first-issue-corpus.md)와 [출처 목록](../../docs/research/first-issue-sources.tsv): 확보 수·이용·파싱·초기 풀을 구분한다.

아래 내부 러너는 저장 근거 검색 지표만 평가한다. `pytest`의 단위/계약 검사 통과를 이20문항의 제품 품질 평가 결과로 표시하지 않는다. 실제 실행 결과는 자료·검색·모델·프롬프트 버전과 함께 추가한다.

## 운영자용 저장 근거 검색 평가

`issuedigest-evaluate-retrieval`은 운영자가 명시 실행하는 내부 도구다. 기존
`question_terms`와 `retrieve_snapshot_ids`를 그대로 호출한다. 초기 baseline 전략은
`question-terms-v1`, 현재 제한 한국어 검색 전략은 `question-topics-ko-v2`이며,
투영 profile `literal-ngrams-v1`과 구분한다. 이전 전략을 실행 옵션으로 제공하지 않는다.
합성 PG 회귀는 실제 자료 평가와 별도다. 위 20문항은 여전히 **실제 실행 전**이며,
이 도구의 합성 테스트 통과가 그 문항의 실행·보류 상태를 바꾸지 않는다.

작업 파일과 gold는 Git/PR/Sites 밖의 비공개 위치에 보관한다. 운영자가 직접 검토한
기대 snapshot ID를 적고, 같은 출처를 대신할 수 있는 snapshot들을 하나의 family로
묶는다. 서로 다른 필수 출처는 다른 family다. 모델이 질문·본문·gold를 생성하지 않는다.
다음은 합성 ID로만 구성한 job 형식 예시이며, 실제 실행에는 실제 corpus의 ID를 넣는다.

```json
{
  "schema_version": 1,
  "expected_database": "issuedigest_test",
  "workspace_id": "00000000-0000-4000-8000-000000000001",
  "corpus_snapshot_ids": ["00000000-0000-4000-8000-000000000002"],
  "cases": [
    {
      "case_id": "q01",
      "question": "등록금 지원 대상은 누구인가요?",
      "expected_families": [["00000000-0000-4000-8000-000000000002"]],
      "no_match": false
    },
    {
      "case_id": "negative01",
      "question": "합성 corpus에 없는 주제",
      "expected_families": [],
      "no_match": true
    }
  ]
}
```

job은 최대 256KiB의 strict UTF-8 JSON이다. 중복 key, 비유한 수, 추가 필드, 타입 강제를
거부한다. `expected_database`는 PostgreSQL 식별자이며 URL의 DB 이름과 일치해야 한다.
workspace·snapshot은 UUID4다. corpus는 1..50개이며 **해당 workspace의 실제 snapshot
전체와 정확히 같아야** 한다. 모두 유효한 canonical 근거와 완전한 투영이 있어야 한다.
다른 workspace의 자료는 포함하지 않는다. 질문은 1..40개, 질문당 비공백 1..1500자,
case ID는 고유한 ASCII 영숫자·`_`·`-` 1..64자다. positive case는 1..5개 family,
family당 1..10개 corpus snapshot을 가진다. 한 case에서 같은 ID를 중복하지 않는다.
negative는 `no_match: true`와 빈 `expected_families`를 명시한다. 보류 문항을 몰래
제외하지 않는다. 이 도구는 job의 모든 문항을 실행하거나 전체 실패하며, 별도 보류는
원래 평가 기록에 이유와 함께 남긴다.

```sh
# 저장소 루트에서 실행. DB URL은 외부 비공개 환경 설정으로 공급한다.
# job은 소유자 전용 600 파일, report의 부모는 소유자 전용 700 디렉터리다.
chmod 700 /absolute/private/evaluation
chmod 600 /absolute/private/evaluation/job.json
uv run --package issuedigest-worker issuedigest-evaluate-retrieval \
  /absolute/private/evaluation/job.json \
  --output /absolute/private/evaluation/baseline.json
```

`ISSUEDIGEST_DATABASE_URL`은 명시적 host가 있는 `postgresql+psycopg` URL이어야 하며
query override를 허용하지 않는다. CLI는 기존 private 파일 가드를 사용한다(읽기는
400/600도 허용). symlink를 따라가지 않고 새 600 report를 원자적으로 생성하며 덮어쓰지
않는다. 출력할 부모는 700이어야 한다. DB 스키마 생성·투영 재구축은 실행하지 않는다.
read-only `REPEATABLE READ` transaction에서 scope, canonical, 투영과 모든 질문을
검증한다. 검색 결과의 corpus 이탈·중복·5개 초과는 전체 실패다. 오류나 DB pool 정리
실패 시 report를 발행하지 않는다. stdout은 건수와 아래 집계 지표만, stderr는 고정 오류
메시지만 포함한다. 질문·ID·검색어·rank는 private report에만 기록한다.

report v1은 다음을 포함한다.

- `job`: 전체 검증 job. `retrieval_profile`: 검색 전략 식별자.
- `job_sha256`: 전체 검증 job의 canonical JSON hash.
  `question_gold_sha256`: 순서 있는 모든 case(질문·gold·no-match)의 hash.
- `declared_corpus_sha256`: ID 문자열을 정렬한 선언 corpus의 hash.
  `corpus_sha256`: snapshot ID 순으로 정렬한 검증된 fingerprint 목록의 hash.
  `fingerprints`: snapshot별 ID, canonical bundle SHA256, 실제 투영 SHA256·profile.
  실제 저장 manifest와 모든 unit을 canonical에서 재계산한 값과 대조한다.
- `cases`: 원래 case, 해석한 `terms`, `ranked_snapshot_ids`, family/member 선언 순서의
  `family_ranks`(1부터 시작, 미발견은 null), `found_families`, 개별 지표.
- `summary`: `cases`, `positive_cases`, `negative_cases`와 집계 지표. 분모 0은 null이다.

| 지표 | 정의 / 분모 |
| --- | --- |
| `hit_at_1` | 첫 검색 결과가 어느 필수 family에 속한 positive case 비율 / 모든 positive |
| `macro_family_recall_at_5` | case별 발견 family 수 / 필수 family 수의 평균 / 모든 positive |
| `all_required_at_5` | 필수 family를 모두 발견한 positive case 비율 / 모든 positive |
| `negative_no_match` | 검색 결과가 빈 negative case 비율 / 모든 negative |

동일 family의 여러 snapshot은 recall을 중복 가산하지 않는다. 빈 positive 결과는
0점이며 분모에 남는다. negative 결과는 positive 지표 분모에서 분리한다. 이 지표는
검색 평가이며 인용 위치 일치·주장 지지·답변 정답·전체 제품 품질이 아니다. 저장 색인과
기존 후보 한도 내 결과만 측정하므로 빈 결과가 세상에 자료가 없음을 뜻하지 않는다.

baseline/candidate 비교는 `question_gold_sha256`, `declared_corpus_sha256`,
`corpus_sha256`가 같은 report끼리 수행한다. expected DB/workspace와 원래 평가 범위도
확인하고, 다른 전략은 서로 다른 `retrieval_profile`로 구별한다. 질문 순서나 gold를
바꾸면 같은 평가가 아니다. 새 report 파일을 사용하고 실제 평가 판정은 운영자가 남긴다.

현재 검색은 최대8개 질문 원형을 보존하고, 알려진 조사 제거를 원형마다 최대1개
추가한다(최대16개 조회, 계약 상한24개 이내). `AI는`→`AI`, `2026년도`→`2026년`,
`2026년에는`→`2026년`처럼 ASCII/숫자가 섞인 원형도 다룬다. 원형은 ASCII 대소문자만
같게 비교하며 숫자·단위·시간·대상·부정·고유명사의 의미 동일성을 추정하지 않는다.
비교/정리 요청 표현을 검색 주제에서 제외하지만 일반 후속 질문 판정은 확대하지 않는다.
숫자가 포함된 혼합 표현의 `만`·`도`는 수량 크기/온도 단위일 수 있어 보수적으로
보존한다(`1천만`, `10여만` 포함). 이미 남아 있는 명시 단위 표기
`원/년/월/일/명/개/건/회/도/%` 뒤에서만 이 두 조사를 제거하며, 알 수 없는 혼합
수량을 해석·변환하지 않는다. 소수와 붙은 단위도 하나의 원형으로 보존한다.
같은 조사 제거 원형에 속하는 질문
표현은 모두 모은 뒤 직접 일치 집합을 합쳐 주제/직접 일치 점수를 각각1회만 더한다.
묶음당 검색 변형은 원형과 결정적으로 고른 추가 표현을 합쳐 최대3개이며,
다른 표현들도 실제 후보 원문의 직접 일치 검사에 포함해 질문 토큰 순서에 의존하지 않는다.

검색 변형별로 실제 전체 문자열 일치가 있는 문단을 snapshot별 순번으로 번갈아
최대200개 검사하고201번째로 잘림을 감지한다. 길이4 이상 문자열은 ASCII space,
tab, LF, CR, form feed, vertical tab만 제거한 전체 문자열의 실제 포함도 확인한다.
제로폭 공백·NBSP 등 다른 문자는 제거하지 않는다. 이 동작은 띄어쓰기 대응이며
동의어/의미 검색이 아니다. ngram 집합은 전처리 필터이며 실제 일치를 대신하지 않는다.
원형·변형·동일 snapshot 반복 문단은 같은 주제의 점수를 중복 가산하지 않는다.
주제 일치 수→원형 직접 일치 수→안정된 snapshot ID 순으로 정렬하고 변형별 상위20개,
최종 후보 상위20개에서5개를 선택한다. 기존 canonical/투영 hash·selector·workspace
검증을 통과해야 하며 해석한 query로 원문 위치를 만들지 않는다. 후보 제한·색인 누락
아래의 미발견과 자료 자체의 부재를 구분한다.

Task2의 고정 합성7문항(positive6/negative1)은 같은 질문/gold/corpus fingerprint에서
family Recall@5 0.25→0.8333, Hit@1 0.3333→0.8333, 필수 가족 모두 발견
0.1667→0.8333, negative no-match 1.0→1.0을 기록했다. mixed/year/띄어쓰기/반복 문단
4문항은 개선, 문자 일치·negative2문항은 동일, 없는 근거를 기대한1문항은 계속0점이다.
합성 결과는 실제 자료·기존20문항·인용 지지·답변 품질의 판정이 아니다.

합성 회귀 실행(전용 local test DB만 지정):

```sh
uv run pytest packages/storage/tests/test_retrieval_evaluation.py \
  apps/worker/tests/test_retrieval_evaluation_cli.py
```

## D022 검색 집계와 v4 의미 평가의 경계

controller가 고정한 실제 저장13자료·34문항(positive30/negative4)은 같은 질문/gold/corpus fingerprint로 비교했다. Hit@1·family Recall@5·필수 가족 모두 발견은 모두13/30→28/30(43.33%→93.33%), negative no-match는2/4→2/4(50%)였다. positive 미발견2개·negative 오탐2개를 그대로 분모에 남긴다. 작은 고정 검색 표본이며 위치 일치·주장 지지·정답·전체 제품 품질을 증명하지 않는다. 정확 job/report·질문·ID·원문은 controller만 저장소 밖에서 보관한다. 원래20문항의 **미실행** 상태는 그대로다.

새 research-v4는 기관 발표의 귀속, 목표·현재 실적·전망·확정 결과, 같은 대상·기간·단위의 단순 대소 관계를 지침으로 구분한다. 합성 FunctionModel 출력은 request envelope/원문 전달·분류/인용 연결·불신 입력의 계약 회귀만 검증한다. 문구 키워드 검사를 의미 품질 판정으로 쓰지 않는다. controller는 별도 승인된 최대3회 실제 모델 요청의 모든 성공/실패와 실제 인용·주체·기간·수치/귀속을 직접 읽은 판정을 별도로 기록한다. 현재 Task3 구현으로 그 실행이 완료된 것은 아니다. v2/v3 과거 결과에는 새 평가를 소급하지 않는다.

## 2026-10-18 controller 인수 집계

고정13자료·34문항의 동일 job/corpus fingerprint에서 positive30의 Hit@1·family Recall@5·필수 가족 모두 발견은13/30→28/30, negative4의 no-match는2/4→2/4였다. 미발견/오탐을 분모에 유지했고 read-only 복원본34테이블은 평가 전후 동일했다. 이 좁은 저장 문자 검색 표본은 정답률·인용 지지·일반화된 검색 품질이 아니다.

별도 합성 신원/공개 텍스트의 실제 모델3회는 위 CLI와 다른 수동 의미 평가다. 두 수치 응답은 원문 수치와 예정 성격을 보존했지만 귀속 분류·비교 결론·한계 설명이 불충분해 부분 충족으로 기록했다. 나머지는 없는 전국 찬성률/인지도를 생성하지 않고 제공 근거 부족으로 종료했다. 실제 청구액·독립 사실 검증·기존20문항 완료를 뜻하지 않는다. 제품 소스1c0c5ed, 상세 비공개 job/output/receipt는 저장소 밖에 두고 [진행 기록](../../docs/planning/progress.md)에 집계만 남긴다.


## v5 실제 인수 · 2026-10-19

[답변 품질 명세](../../docs/changes/briefing-answer-quality.md)·제품f90839e. 별도 합성 신원/PG에 기검토 공개 텍스트3건을 넣고 초기4회·별도 구조2회만 호출했다. 초기4회는 완료2(의미 부분 충족)/검증 실패2이며 실패 분모를 보존했다. cached paid checkpoint의 잘못된 비답변 modules·가공된 인용 UUID를 호출 없이 재현한 뒤 세 strict provider 출력/실제 prompt citation enum을 구현했다. 수정 후 별도2회는 정확 인용으로 완료했으나 의미 품질은 부분 충족이다. 자동 재시도0·입력14,684/출력3,556토큰, 청구 금액 미검증이다.

없는 여론 비율을 만들지 않았고 출처 범위의 한계·동월 지표의 서로 다른 방향을 설명했다. 그러나 핵심 여론 근거가 없는 질문이 answer를 선택했고, 수치 문장별 기관 명시와 첫 요약의 직접 비교 결론은 일관되지 않았다. 실제 insufficient_evidence 분기 성공이나 전체 의미 품질 통과로 해석하지 않는다. 다음 평가는 문장별 귀속·자료 부족 분기·첫 요약 결론을 직접 읽어 판단하며 반복 호출로 기존 실패를 지우지 않는다. 원본 질문/응답/개별 인용은 private 보관한다.

전체3,777개·독립 검토·합성 strict schema/예산·실제 PG historical 재생은 구조/복구 증거다. 자체 브라우저에서 초기4개 상태/추가2개 결과와390/1440·두 테마·분류/설명·정확 원문/초점·재열람(읽기POST0/페이지오류0)을 확인했다. 모델 요청 성공·UI 표시·의미 품질을 구분한다.


## v6 실제 인수 · 2026-10-19

[v6 역사 명세](../../docs/changes/briefing-core-answer.md). 초기f462 고정4회는 정확 자료 부족 완료1/검증 실패3이다. raw category/주체 모순·인용에 없는 기관·일반 claim 임의 날짜를 차단했고 주택 열린 전망의 잘못된 상한 해석도 표시되지 않았다. 실패 앱 usage0 대신 cached 유료 ModelResponse 전체 사용량을 확인했다. provider 단순화 뒤7566의 별도2회는 주택의 목표/중간 실적/전망 조건·동월 두 지표의 엇갈린 방향과 한계를 첫 요약에 담았다. controller가7/6문장·각 평가/근거 설명·모든 선택 인용을 직접 대조해 이 두 작은 표본에서 충족으로 기록했다.

합계 초기4+별도2, 입력20,185/출력3,867토큰·자동 재시도0·청구 금액 미검증이며 이전v5 분모도 유지한다. 새 DTO의 교육 예산 실제 재검증과 비답변의 추가 실제 호출은 하지 않았다. 실제 자료 부족 분기 성공은 초기f462의3번이며 현재 형식의 합성 분기 통과와 구분한다. 종합 정답률/독립 사실 검증/일반화된 의미 품질/기존20문항 완료를 뜻하지 않는다. 이번 source 전체3,967개·합성PG 다섯 버전 유료 완료 checkpoint 재생과 실제6상태/모바일·PC·두 테마/정확 원문·읽기POST0/오류0은 별도 구조·화면 증거다. 상세 원본·질문·인용·사용량 checkpoint는 private 보존한다.


## v7 계획 검색 실제 인수 · 2026-10-19

[명세](../../docs/changes/briefing-search-agent.md)·제품57c71ec. 별도 합성 신원/PG와 기검토 공개 텍스트3건, 고정3앱실행/6모델요청·자동재시도0이다. 원래 질문의 후보 수2/0/3과 새 고정 수2/1/3을 구분했다. 두 번째 영어 표현은 원래 문자 검색0에서 정확 주택 자료1건을 회복했다. 선택 자료 전체·모든 생성 문장/평가와 정확 인용을 직접 읽어 판정했다.

실제 고정3앱실행/공급자6요청·자동재시도0은 브리핑 완료1(의미 부분 충족)·자료 부족 완료1·검증 실패1이다. 원래 문자 검색0이던 영어 표현의 주택 질문은 계획 검색으로 정확 자료1건을 찾았으나, 최종 timeline이 원문에 없는 정확 날짜2개를 추정해 표시를 차단했다. 성공까지 다시 호출하지 않았다. 완료 답변의9문장/평가·선택 인용3개와 실패 checkpoint의6문장/인용을 직접 대조했다. 목표·실적·조건부 전망의 첫 결론은 읽히지만 세부 항목의 포함 관계 누락과 목표/확정 결과의 모호한 표현은 남았다. 자료에 없는 전국 찬성률·인지도는 생성하지 않고 근거 부족으로 끝났다. 검색 개선·구조 통과를 전체 의미 품질 완료로 해석하지 않는다.

cached 실제 사용량은 입력9,413/출력2,087토큰이며3실행 지연은8.39/5.76/3.96초다. 모든 유료 응답6개를 확인했고 실제 청구 금액은 미검증이다. 실패/취소·권한 변경·응답 유실의 앱 usage0은 무료를 뜻하지 않으며 기존 보수적 예약을 유지한다. 이전v6 초기4(부족1/실패3)+별도2와v5 초기4+별도2의 실패·부분 충족 분모를 보존한다. 기존20문항의 실행 완료나 종합 정답률이 아니다. 실제 사용자 세션을 발급/재사용하지 않았으며 질문·개별ID·원문/응답은 private에 보존한다.

전체 Python3,459+JS694=4,153개·lint/format/types/build/contract와 작업별/전체 독립 검토를 통과했다. raw boolean 사용량 검증 지적은 실제 응답/합산·cached 재생 경계에서 보완·재검토했다. 자체 합성 신원의 실제3상태·390/1440·두 테마·첫 열린 요약/접힌 상세·정확 원문/초점·재열람(읽기POST0/페이지오류0)을 확인했다. 기존v2~v6 provider bytes/지침/한도/유료slot1·결과와 공개 계약을 보존하며 새v7은 exact paid1/search2/paid3을 회복한다.


## v8 실제 고정3회 · 2026-10-19

현재 개인 개발 웹/API/조사 worker는 `f839ae0`이며 [Draft PR45](https://github.com/DigestWorks/IssueDigest/pull/45)(PR44 기반)다. 새 private v8은 동결 planner7→승인 저장 검색→최대5근거 고정→최종 생성으로 이어진다. 정확 인용에 있는 유효한 YYYY-MM-DD만 timeline 날짜 후보로 최대16개 허용하고, 후보가 없으면 요약/비교로 설명한다. 개별 인용에 해당 날짜가 있는지도 다시 검사한다. 날짜가 있다는 것과 실제 사건을 뒷받침한다는 것은 다르다. 수치의 포함 관계와 목표·관측 실적·조건부 전망을 보존하도록 지시하며 자유 문장의 의미 정확성을 schema 통과로 인증하지 않는다. 원래 질문/검색·정확 인용·첫 열린 요약·기존 소비자 디자인과 공개 계약은 유지한다.

전체 Python3,553+JS744=4,297개·lint/format/types/build/contract와 작업별/전체 독립 검토(Critical/Important/Minor0)를 통과했다. [source CI](https://github.com/DigestWorks/IssueDigest/actions/runs/39208107011)도 성공했다. 기존v2~v7 provider/지침/한도·원래 workflow/version/유료 checkpoint와 저장 결과를 보존한다. 새v8은 planner7 유료slot1→search_v8 step2→final_v8 유료slot3을 회복한다. 자체 합성 신원으로390/1440·두 테마·첫 열린 요약/접힌 상세·정확 원문/초점·재열람(읽기POST0/페이지오류0)을 확인했다.

실제 고정3앱실행/공급자6요청·자동재시도0은 모두 완료했고 답변2·자료 부족1이다. 의미 판정은 부분 충족1·이번 목표 소표본 충족1·자료 부족1로 구분한다. 이전v7에서 원문에 없는 날짜 때문에 실패했던 표현은 날짜 없는 요약/비교로 완료했다. 첫 답변6문장/6평가/정확 인용3개와 둘째7문장/7평가/정확 인용3개를 전부 대조했다. 둘째는 부분 항목의 포함 관계를 명시하고 독립 합산을 피했다. 없는 전국 여론 수치는 만들지 않았다. 다만 첫 답변의 하한 수치를 ‘목표의 일부’로 표현한 상한 암시, 질문에 없던 검색어 추가·무관 자료 선택, 전망의 조건부 뉘앙스는 남았다. 실제3건 모두 정확 날짜 후보0이며 날짜 있는 실제 제공자 검증은 하지 않았다(합성 Python/client/UI 검증만 통과). 일반 시사·중립성·의미 품질 전체 통과가 아니다.

실제 cached 사용량은 입력9,915/출력1,932토큰,3실행 지연7.80/7.14/3.94초다. 유료 응답6개 모두 확인했고 실제 청구 금액은 미검증이다. 앱 usage0은 무료를 뜻하지 않는다. 이전v7 고정3/6(부분답변1/부족1/실패1), v6 초기4(부족1/실패3)+별도2, v5 초기4+별도2의 실패·부분 충족 분모는 그대로 보존한다.

개발 앱은 활성 작업0에서 정상 재기동·단일 worker lock1·source/cwd·정적19파일/외부6assets 일치를 확인했다. 이전94assets/원래 source/복귀 경로와 수집기a908083/config/runner/cron을 보존했다. schema0009·자료15/인용49/검색36/receipt1/공개1·계정/세션·HTTPS/비회원401 경계를 유지했다. 서버 밖 사전·직전·사후 full/app 백업과 별도PG18.6 복원에서 직전/사후/백업 직후/복원의23public테이블 rowhash/count 전체 일치를 확인했다. 실제 기존 AI 결과는0개이므로 역사 실제 결과 재생을 주장하지 않는다. DBOS registry·vector/역할까지 포함한 완전 DR은 아니다. 외부 정적 파일 읽기의 일시 DNS 오류는 설정 변경 없이 재조회해 정상 확인했다. main/운영 유예(D013)는 유지한다.

판단: 최대100인용·16날짜는 상한이며 모든 최대 조합의 동시 입력을 보장하지 않는다. 의미 보존 지침·원문 전체와 합산24,000 예산을 유지하고 실제 사전 검사에서 초과 입력을 거절한다. 잘못된 판단이면 큰 맥락·planner 사용량이 많은 질문이 최종 생성 전에 자료 부족으로 더 자주 끝날 수 있으며, 추가 유료 재시도 없이 자료 선택/예산 정책과 테스트를 재설계해야 한다.

검토한 기존 공개 텍스트3건을 그대로 복사한 합성 신원의 전용 평가 DB에서 수행했다. 실제 사용자 세션은 사용하지 않았다. 원래 후보0/2/3에서 계획 후 고정1/3/3이었다. 첫 답변6문장/6평가/정확 인용3개, 둘째7문장/7평가/정확 인용3개와 전체 검색 계획/선택을 직접 읽었다. 날짜0인 실제3건과 날짜양성 합성 fixture를 구분하며 추가 성공 재시도는 없다. 실제 입력/출력·원문·계정/접속·ID는 private 증거에만 보존한다.
