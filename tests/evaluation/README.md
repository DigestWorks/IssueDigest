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

## 기록된 계획 검색과 원래 검색 비교

`issuedigest-evaluate-planned-retrieval`은 새 내부 비교 도구다. 기존 v1 명령·job·report는
그대로 유지한다. 같은 검증 corpus에서 원래 `question_terms`/`retrieve_snapshot_ids`와
실제 `research_search.search_candidates(conn, {workspace_id, question}, queries, None)`를
한 읽기 전용 `REPEATABLE READ` transaction으로 비교한다. 원래 질문도 계획 경로에
포함되며 원래 검색 우선 round-robin·중복 제거·최대5개 선택은 기존 검색 구현을 따른다.
부모 없는 독립 질문만 평가한다. 과거 workflow/journal이나 모델 실행을 재생하지 않으며
provider·키 로딩·모델 호출·수집·색인 수정·게시를 수행하지 않는다.

새 job은 다음 세 필드만 가진다. `baseline`은 위의 기존 v1 job **전체**다. `plans`는
baseline의 cases와 개수·순서·case_id가 정확히 같아야 한다. 아래 예시는 한 질문짜리
baseline을 사용한 합성 JSON이다.

```json
{
  "schema_version": 1,
  "baseline": {
    "schema_version": 1,
    "expected_database": "issuedigest_test",
    "workspace_id": "00000000-0000-4000-8000-000000000001",
    "corpus_snapshot_ids": [
      "00000000-0000-4000-8000-000000000002",
      "00000000-0000-4000-8000-000000000003"
    ],
    "cases": [{
      "case_id": "q01",
      "question": "등록금 지원 대상은 누구인가요?",
      "expected_families": [["00000000-0000-4000-8000-000000000002"]],
      "no_match": false
    }]
  },
  "plans": [{
    "case_id": "q01",
    "origin": "recorded_planner_output",
    "queries": ["등록금 지원", "지원 대상"],
    "irrelevant_snapshot_ids": ["00000000-0000-4000-8000-000000000003"]
  }]
}
```

`origin`은 실제로 기록한 계획의 `recorded_planner_output` 또는 운영자가 명시 작성한
`operator_authored`다. 후자를 실제 모델 품질로 해석하지 않는다. queries는 비공백
1..64자 문자열1..3개이며 Unicode control/category C 문자는 거부한다. 명시 무관
`irrelevant_snapshot_ids`는 중복 없는 corpus 내 UUID4 0..50개다. 해당 질문의 어느
expected family member와도 겹칠 수 없다. 사람이 명시한 gold·무관만 판정하고 나머지는
미판정으로 남긴다. 전체 파일 최대256KiB와 기존 baseline의 엄격한 상한·타입 규칙을
동일하게 적용한다. 한 문항의 오류·잘못된 검색 결과도 전체 실패이며 임의 수정하지 않는다.

```sh
uv run --package issuedigest-worker issuedigest-evaluate-planned-retrieval \
  /absolute/private/evaluation/planned-job.json \
  --output /absolute/private/evaluation/comparison.json
```

모듈 진입점은 `issuedigest_worker.planned_retrieval_evaluation_cli`, SDK는
`issuedigest_storage.planned_retrieval_evaluation.parse_job(raw_bytes)`와
`evaluate(engine, raw_bytes)`다. `PlannedEvaluationJob.model_json_schema()`와
`PlannedEvaluationReport.model_json_schema()`로 형식을 확인한다. SDK engine은 호출자가
관리한다. CLI는 기존 private 파일·DB URL·조용한 pool lifecycle을 공유한다. 입력400/600,
report 부모700, 신규 report600·symlink 거부·덮어쓰기 금지·원자 발행을 지키며 transaction,
connection, engine disposal이 모두 성공한 뒤에만 발행한다. stdout에는 baseline/planned
집계와 `origin_case_counts`만, stderr에는 고정 오류만 나온다. 질문·계획·ID·terms·rank와
DB 진단은 stdout/stderr에 넣지 않는다.

report의 `profile`은 `planned-retrieval-comparison-v1`이고 `retrieval_profile`은 underlying
문자 검색 전략이다. 전체 검증 `job`, 전체 `job_sha256`, baseline cases의
`question_gold_sha256`, 순서 있는 계획·origin·무관 labels의 `plans_labels_sha256`, 선언
corpus의 `declared_corpus_sha256`, 검증 canonical/투영 fingerprint의 `corpus_sha256`과
`fingerprints`를 기록한다. JSON 공백·객체 key 순서는 hash를 바꾸지 않는다. labels·계획·
origin 변경은 plans/labels hash와 job hash를 바꾸고, 질문·gold 변경은 question/gold와
job hash를 바꾼다. 자료 내용과 선언 corpus hash를 구분해 비교한다.

각 `cases` 항목에는 case·plan·`original_terms`·query별 `query_terms`, `baseline`과
`planned`의 실제 `ranked_snapshot_ids`·family ranks·기존 지표·아래 반환수를 기록한다.
`summary.baseline`/`summary.planned`는 기존 positive/negative 분모와 같은 반환수 합계를
제공한다. 빈 positive/negative 분모는 null이며 누락 질문은 분모에 남긴다.

| 필드 | 판정 / 분모 |
| --- | --- |
| `returned_count` | 실제 반환 snapshot 수 |
| `relevant_count` | expected의 어느 family member에든 속한 반환수 |
| `irrelevant_count` | 사람이 명시한 irrelevant에 속한 반환수 |
| `unjudged_count` | 어느 labels에도 속하지 않는 반환수 |
| `judged_precision` | relevant / (relevant + irrelevant), 분모0은 null |

동일 family의 여러 member를 반환하면 relevant 반환수는 각각1로 세지만 recall은
family당1로 센다. 집계 judged_precision은 case별 비율의 평균이 아니라 전체 relevant /
전체(relevant+irrelevant)인 micro 값이다. **미판정은 precision 분모에서 제외된다.**
report의 `judged_precision_denominator`도 이를 명시한다. 전부 미판정이거나 빈 결과면
precision은 null이다. negative no-match case에서 미판정 결과가 반환돼도
negative_no_match는 false지만 그것을 자동 irrelevant로 바꾸지 않는다.

이 숫자는 명시 corpus·고정 질문·사람 labels·기존 검색 후보 한도 안의 비교다. 전체
precision, 의미적 주장 지지, 최신 정보의 충분성, 여론·중립성·공정성 또는 답변 품질을
인증하지 않는다. 회복된 gold와 추가 irrelevant·unjudged를 함께 검토한다. 합성 테스트
통과와 실제 자료의 별도 운영자 인수를 구분한다.


## 기록된v8 계획3건의 비교 인수 · 2026-10-19

내부 계획 검색 비교 SDK와 `issuedigest-evaluate-planned-retrieval` CLI를 추가했다. 원래 검색과 실제 original-first round-robin 계획 검색을 같은 strict job/corpus·읽기 전용 REPEATABLE READ transaction에서 비교한다. 필수 family·사람이 명시한 무관 자료·미판정을 구분하며 `judged_precision`은 판정된 relevant/(relevant+irrelevant)만 사용한다. 미판정은 분모에서 빠지므로 전체 precision이 아니다. 기록된 계획/운영자 작성 계획의 출처를 따로 보존하며 provenance 자체를 자동 인증하지 않는다.

기검토 공개 텍스트3건·이전v8 고정 질문3개와 실제 기록된 planner7 검색어를 그대로 재현했다. 원래 후보0/2/3→계획후1/3/3이며 이전 선택 순서까지 정확히 일치했다. 첫 질문은 필요한 자료0→1·명시무관0, 둘째는 필요한 자료1 유지·명시무관1→2, 셋째는3건 모두 관련성 미판정으로 보존했다. 셋째의 전국 여론 직접 근거 부재를 모든 반환 자료의 무관함이나 세상에 조사 자체가 없다는 뜻으로 확대하지 않았다. 필요한 자료를 지정한 positive2문항의 family recall은0.5→1.0이고, 전체 반환5→7 중 판정 relevant1→2/irrelevant1→2/unjudged3→3·판정분모의 micro precision0.5→0.5다. 작은 고정 corpus의 비교이며 전체 검색 품질/중립성·답변 의미 품질 통과가 아니다.

추가 유료 모델0·앱 workflow0·실제 사용자 세션 대행0이다. 평가의887개 SELECT/SHOW만 관측했고 쓰기0이며 전용 합성 DB의 준비는 별개다. 입력 질문·검색어·원문/ID와 상세 rank/report는 private에 보존했다. 실제 앱은 f839ae0/v8과 선택한 브리핑 디자인 그대로이며 서버/실제DB·수집기·provider/검색정책/복구/HTTP/OpenAPI를 바꾸거나 배포/재시작하지 않았다. 기존v8 실제3/6(의미 부분1/목표 소표본 충족1/부족1)·v7 3/6·v6 초기4+별도2·v5 초기4+별도2 분모와 남은 하한/전망 뉘앙스·실제날짜 양성 미검증을 보존한다.

후속은 같은 corpus·질문/gold와 미판정 구분을 유지하며 query 이탈/후보 재순위화의 발견률·무관 유입을 함께 비교하는 것이다. 이번 도구가 검색 잡음이나 답변의 수치 표현 자체를 해결한 것으로 표시하지 않는다. 기존 최대100인용/16날짜의 동시 적재 비보장·24,000예산 사전거절 판단과 큰 맥락의 자료 부족 증가/정책 재설계 비용은 D022에 그대로 남긴다. main/운영은 D013에 따라 유예한다.


## 관련성 선택 SDK 실제 고정3회 · 2026-10-19

질문·제공 인용을 함께 읽는 재사용 선택기 `evidence-relevance-v1`을 agents SDK로 구현했다. 정확한 모든 후보에 retain/exclude/uncertain을1회씩 받고, retain+uncertain은 원래 순서로 보존하며 exclude만 제외한다. 실제 후보 UUID enum/전체 coverage·원문 전체 인용·question/prompt UTF-8 hash·불변 결정/사용량과 raw/합산 검증을 적용한다. strict preflight 전에는 기본 key/model/Agent를 초기화하지 않는 lazy handle이다. 제목/metadata만으로 관련성을 증명하거나 관련성을 진실·독립 사실 검증·정치적 동의로 대신하지 않는다.

실제 요청의 source는 `384608d`이며 캡처용 주입 모델과 호출자 소유 클라이언트를 사용했다. 이후 `50f0552`는 기본 생성 클라이언트의 수명 관리만 수정했고 지침·모든 후보 수의 raw/normalized schema·prompt·예산과 합성 결정 결과의 동일성을 확인했다. 기본 경로의 성공·실패·생성 오류 정리와 주입 클라이언트 소유권은 합성 회귀로 검증했으며 실제3요청을 새 source로 재표기하거나 유료 재실행하지 않았다.

기존 고정3질문·같은 기검토 공식 원문3건·이전 계획후 후보1/3/3으로 실제 selector3요청을 한 번씩 실행했다. 모두 완료했고 retry0이다. 동일 주택 자료를 필수로 지정한 positive2문항에서 해당 자료를 모두 보존했다. 둘째는 명시 무관한 경제·교육 후보2개를 모두 제외해2→0이 됐다. 셋째는 주제 관련 주택 자료를 retain하고 다른2개를 exclude했다. 이 문항의 기존 human relevance 미판정3개는 그대로이며 선택 후1개가 남았다. 전국 찬성률/인지도 직접 근거가 없다는 것과 주제 자체의 무관함을 같게 보지 않았고 미판정 제외에 정답/precision 가점을 주지 않았다.

controller가 모든7개 판단과 제공된 정확 인용15종(문항별4/15/15)을 직접 대조했다. 현재 판정은 이번 목표의 좁은 소표본 충족이다. 전부 같은 주택 주제/정부 자료이며 다양한 이슈·상반 입장/다중주제·공격적 주입에 대한 실제 모델 견고성은 검증하지 않았다. 실제 uncertain 응답은0으로 그 보존 분기는 합성 검증만 했다. 선택기는 제한된 제공 인용을 읽으며 원문 전체의 의미나 답변 품질/중립성·전반 검색 정확도를 인증하지 않는다.

실제 입력5,087/출력282토큰·지연2.62/3.32/1.61초이며3응답의 알려진 사용량을 확인했다. 청구 금액은 미검증이다. 실제 app workflow/실제 사용자 세션 대행/개발 서버·DB 변경은0이다. 이3 selector요청은 기존v8의3앱/6요청(의미 부분1/목표 소표본 충족1/부족1), v7 3/6, v6 초기4+별도2, v5 초기4+별도2의 분모와 별개이며 기록 계획 재현의 추가 모델0과도 구분한다. 실제 질문/원문·ID·raw응답/입력prompt·시도 receipt는 private에만 보존한다.

SDK 단독 상한은 요청1회·입력+출력12,000/출력500/15초다. 실제 instructions1,019+worst tool raw842/normalized789 중 큰 값의 static1,861·framing2,048·출력500을 뺀 prompt7,591바이트와 실제 envelope를 사전 검사한다. 최대5후보/100인용은 상한이며 모든 원문 조합의 동시 적재 보장이 아니다. 후보가 prompt에서 빠지면 모델 호출 전에 거부한다. 기존 앱 전체24,000/출력2,500·월 예약·내구 checkpoint/취소·권한/원문 재검증과 연결한 것은 아니다. 앱은 f839ae0/v8·기존 provider/검색/공개/UI/DB/수집기를 유지하며 재시작·배포하지 않았다. 다음은 실제 사용량을 합산해 예약/실패/불명확 호출 재요청 금지·모든 과거 workflow 회복을 보존하는 실행기 연결이다. 기존 D022의 input capacity 판단/비용·남은 수치 표현·실제 날짜 양성 미검증도 그대로다. main/운영은 D013에 따라 유예한다.


## v9 관련성 선택·최종 답변 실제 앱 인수 · 2026-10-19

[명세](../../docs/changes/briefing-relevance-integration.md). v9 source5fcdc42에서 기존 고정3질문·기검토 공개 텍스트3건으로 실제 앱3회/공급자9요청을 한 번씩 실행했다. 자동 재시도0·완료3(답변2/자료 부족1)/실패0이다. 선택 전 후보1/3/3→선택 후1/1/1이며 필요한 동일 핵심 자료는 positive2문항 모두 보존했다. 둘째의 명시 무관2개는0개로 줄었다. 셋째는 주제 자료1개를 남겼지만 human 미판정3개를 그대로 보존하며 제외2개에 정답/precision 가점을 주지 않는다.

controller가 계획3개·관련성 결정7개·서로 다른 제공 인용15종·답변 주장12개/AI평가12개·선택 인용을 모두 직접 대조했다. 첫 답변은 하한을 정확 비율/상한으로 바꾸지 않고 중간 실적·목표·전망을 구분했으나 첫 요약에서 공정 관리 조건은 압축됐다. 둘째는 포함 관계/중복 합산 금지·조건부 전망을 설명했지만 전체 목표를 합산 대상으로 오해할 수 있는 문구가 남았다. 의미 판정은 좁은 목표 충족1·부분 충족1·제공 자료 한정의 적절한 부족1로 기록하며 모델 완료3을 전체 의미 품질 통과로 대신하지 않는다.

선택3과 최종3의 실제 입력·고정 snapshot/evidence를 대조해 선택 자료만 최종 입력과 저장 근거에 포함됨을 확인했다. 실제 known usage는 입력11,502/출력2,207토큰, 실행 지연8.38/8.93/4.32초이며 앱 토큰과 완료 raw응답9개의 합계가 일치했다. 실제 청구 금액은 미검증이다. 기존 selector단독3·v8 3앱/6요청·v7 3/6·v6/v5 초기4+별도2의 실패/부분 분모와 별개다.

같은 주택 주제/정부 자료의 소표본이며 다양한 정치 이슈·상반 입장·복합 주제·실제 공격적 입력·중립성을 인증하지 않는다. 실제 uncertain 결정과 정확 날짜 후보는0이므로 그 양성 분기는 합성 검증만 했다. 원래 질문/원문·ID·raw응답/요청·자체 합성 신원과 시도 receipt는 private에 보존하며 실제 사용자 세션은 사용하지 않았다. main/운영 출시는 D013에 따라 유예한다.

합성 복구/계약과 전체 4655개 검사는 위 실제 소표본 의미 판정과 별개다. 실제 모델 source5fcdc42 이후 문서만 변경했으며 실제 결과를 재호출하거나 보정하지 않았다.

## v10 수치 설명 · 실제 원래3/신규1 분리 · 2026-10-19

[명세](../../docs/changes/briefing-numeric-clarity.md). 실제 source65ffb5c.

v10 수치 설명 지침은 구현했으나 실제 의미 인수는 통과하지 못해 개인 개발 적용을 보류했다. 개발 앱은 기존 ab6654e/v9를 유지한다. 코드 검사/모델 실행 성공과 답변 품질을 구분한다.

고정한 기존3질문+새 다중주제1을 각각 한 번 실행했다. 실제4앱/12요청·재시도0·완료4(답변3/제공 자료 한정 부족1)·실행 실패0이다. 원래3은 부분1·미충족1·적절한 부족1이며, 새1은 두 필수 주제를 보존했지만 부분 충족이다. 완전 충족 답변으로 판정한 것은0이다. 하한을 진행률로 단순화·병렬 항목의 잘못된 포함 관계·첫 요약의 전망 조건 누락이 남았다. 같은 모델의 supported 평가는 독립 사실 검증이 아니다.

선택 전 후보1/3/3/3→선택 후1/1/1/2이고 최종 입력에는 선택한 원문 전체 인용만 남았다. 원래 셋째의 human 미판정3은 유지하며 제외에 정답 가점을 주지 않는다. 계획4·선택 결정10·서로 다른 제공 인용15종·답변 주장20/AI평가20을 직접 읽었다. 실제 입력17,657/출력3,622토큰, 지연8.18/8.45/4.86/8.95초다. 앱 사용량과 완료 raw12개의 합계가 일치하며 청구 금액은 미검증이다.

이전 v9 3앱/9요청(좁은 충족1·부분1·적절한 부족1), selector 단독3, v8/v7/v6/v5의 실패/부분 분모는 별개로 보존한다. 같은 정부 텍스트3건의 소표본이며 일반 정치 이슈·중립성·상품 전체 품질을 인증하지 않는다. 실제 uncertain 결정/정확 날짜 양성은0으로 미검증이다. 실제 사용자 세션0·원문/질문/ID/raw응답은 비공개로 보존한다. 다음은 수치 대상·기간·포함 관계·관측/조건부 전망을 근거에 연결하는 구조를 먼저 설계하고, 이번 실패를 유지한 별도 평가를 하는 것이다. 지침만 추가하거나 성공까지 재요청하는 방식으로 통과를 주장하지 않는다.

합성 고정 출력은 전달/guard를 확인할 뿐 이 의미 실패를 통과로 바꾸지 않는다. 원래20문항 및 실제 날짜/uncertain 양성·상반 출처의 평가도 이번에 실행한 것으로 표시하지 않는다.

## 독립 수치 후보 SDK 실제2 · 2026-10-19

[명세](../../docs/changes/numeric-evidence-proposals.md). 실제 sourcebbf6b7e(구현edc1383과 문서만 다름).

새 수치 근거 후보 SDK를 실제 두 자료의 사전 고정 whole 인용2개/1개로 각각 한 번 실행했다. 기존 질문별4앱/12요청은 재실행하지 않았다. 새 SDK2회/공급자2요청·자동 재시도0에서 unreviewed 후보 반환1·전체 거부1이다. 의미를 완전히 충족한 제안은0이며, 반환1도 부분 결과다.

반환한 후보의 수치5개·관계3개와 거부된 raw 수치3개의 모든 field/null·관계를 원문과 직접 대조했다. 첫 자료는 현재 하한·전망 범위/열린 표현·전망 조건을 보존했지만 핵심 하위 항목을 누락했다. 세 관계 모두 원문에 실제 있는 포함 문구를 사용했으나 그 문구가 직접 가리키는 수치 쌍과 제안 관계가 달랐다. 일부 기간도 빠졌고 같은 단위의 첫 occurrence를 여러 수치에 반복 연결했다. 문자열 존재/구조 통과를 관계 의미나 완전 추출 인증으로 바꾸지 않는다.

둘째 raw는 알려진 상태 세 행의 status_text가 모두 null이어서 전체를 거부했다. raw의 명시 전망 값이 관측으로 분류된 문제도 남았다. 거부 행을 정상 후보/성공으로 집계하거나 자동 고쳐쓰지 않았다. SDK는 Agent 결과를 받지 못한 실패 usage를 unknown으로 남겼으며, controller가 별도로 보존한 완료 공급자 원응답2개의 사용량은 입력3,187/출력3,229토큰이다. 지연10.85/4.96초·청구 금액 미검증이며 unknown은 무료를 뜻하지 않는다.

이는 독립 내부 추출 SDK의 제한된 평가다. 실제 planned/uncertain 양성·전체 문서 수치의 포괄성·다양한 정치 이슈/중립성·최종 브리핑 품질은 미검증이다. 기존 v10 실제4건의 부분/미충족·과거v9/selector/v8/v7/v6/v5 분모는 유지한다. 앱/DBOS·DB/API/공개/UI/수집기와 개인 개발ab6654e/v9를 변경하지 않았다. 다음은 반복 context 출력의 비용을 줄이는 입력 참조 구조, provider 단계의 상태/근거 조합 제약, 관계 cue의 실제 지시 대상과 누락을 평가하는 계약을 설계하는 것이다. 단순히 더 강한 지침/성공 재호출로 해결됐다고 표시하지 않는다.


## compact 수치 근거 v2 · 고정 실제2

[명세](../../docs/changes/numeric-evidence-compact.md).

새 v2를 이전과 byte-identical인 두 원문 packet(whole 인용2개/1개)에 각각1회 실행했다. 실제 source5592d9c·독립SDK2/공급자2요청·재시도0이며 반환0·전체 거부2·의미 완전 충족0이다. 기존 v1의 부분1/거부1, 기존 앱4건/12요청과 모든 과거 실패/미판정 분모를 유지했다. 앱·실제 사용자 세션은0이다.

controller는 두 원응답의 raw 수치6/5개·관계3/2개와 모든 field/null을 whole quote와 직접 대조했다. 이전에 누락된 하위 항목과 증감 수치는 raw에 나타났지만 수용된 후보가 아니다. 첫 응답은 단위의 존재하지 않는 occurrence3개·다른 값의 단위 연결, 전체 endpoint/cue가 statement 밖인 관계와 cross-citation 관계 때문에 거부된다. 전망 조건을 qualifier에 넣고 condition을 비운 문제, 관측의 상태 근거로 포함 문구를 쓴 문제도 남았다. 둘째는 두 관계 statement가 떨어진 원문 조각을 붙인 문자열이어서 거부된다. raw의 조사 표현을 단위로 쓰거나 반복 단위/시점을 오연결하고, 명시 전망을 관측으로 분류한 의미 오류도 남았다.

두 raw는 known 상태 근거의 nonnull provider DTO를 만족했지만 exact 위치/관계 검사를 통과하지 못했다. 추가 호출 없이 원래 raw의 DTO/각 field/관계 물리 조건을 오프라인으로 분리 확인했고, 잘못된 행을 고치거나 정상 부분 proposal로 반환하지 않았다. 알려진 실패 사용량2건은 SDK에도 보존됐다. 입력3,003/출력2,029토큰·지연6.64/4.51초이며 청구 금액은 미검증이다. 동일 두 자료의 v1 출력3,229보다 짧았다는 관측을 일반 비용 절감·의미 품질 향상으로 확대하지 않는다.

계약 구현/합성 검사와 실제 모델 의미 인수는 별개다. 실제 planned/unknown 양성·전체 문서 수치/다양한 정치 이슈/중립성·최종 브리핑 품질은 미검증이다. 개발ab6654e/v9·앱/DBOS/DB/API/공개/UI/수집기·월 예약은 변경하지 않았고 main/운영은 D013 유예다. 다음 설계 후보는 모델이 occurrence를 세거나 관계 문장을 다시 쓰게 하기보다 서버에서 확정한 원문 위치 참조를 선택하게 하는 방식이다. 단순한 지침/성공 재호출·자동 수정은 해결로 표시하지 않는다.


## 서버 원문 참조 v3 · 실제2회 거부 · 2026-10-19

[명세](../../docs/changes/numeric-evidence-references.md).

같은 두 whole quote packet(인용2개/1개)·gpt-5.4-mini에 v3를 각각1회 실행했다. sourceb3794da·독립SDK2/공급자2·재시도0, 반환0/전체 거부2·의미 완전 충족0이다. 실제 앱/사용자 세션0이며 원문 재수집·자동 수리·부분 결과 수용·추가 유료 시도는 없다. 기존 v2 거부2·v1 부분1/거부1·앱4/12·과거 실패/미판정은 별도 보존한다.

controller가 원문·모든 raw field/null·관계와 원래 catalog로 해석한 위치를 직접 읽었다. 첫 응답(raw수치5/관계3)은 단위로 공백을 골라 전체 거부됐다. 필요한 하위 수치가 fact에서 빠지고 직접 하위 포함 관계도 없었다. 다른 단위는 구두점/조사, 기간은 지역 문구를 가리켰고 하한 수식어·전망의 연말 시점/실행 조건도 제대로 연결하지 못했다. forecast 분류 자체는 있었지만 충분한 인수가 아니다. 관계 세 개의 물리 포함 조건은 고립해서 성립해도 cue가 지명 목록이어서 관계 의미 인증이 되지 않는다.

둘째(raw수치3/관계2)는 관계 cue가 공백이고 다른 관계는 실제 endpoint 값/주체가 statement 밖이라 전체 거부됐다. 수치 범위에 조사/동사를 넣고 소비자 증감을 기업 대상으로 연결했다. 현재 기업 수준을 다음달 전망 주체/planned와 묶었고 월간 하락 수치는 누락, 전망 수준은 qualifier에만 나타났다. 필요한 수치6/5개를 올바른 fact로 모두 얻지 못했다. 단위 부재의 null 등 개별 타당한 필드도 정상 제안으로 집계하지 않는다.

알려진 실패 사용량은 SDK에2건 보존됐다. 입력4,485/출력947토큰,4.95/3.04초이며 청구 금액은 미확인이다. 이전 v2 입력3,003/출력2,029와 비교해 입력은 늘고 출력은 줄었지만 누락을 동반했다. 출력 계약·지침·상태 taxonomy가 함께 달라 단일 변경 효과나 일반 비용 절감/품질 향상으로 해석하지 않는다. provider 범위 내 번호·정확 substring은 올바른 의미 경계/대상·단위·시점/완전 추출을 보장하지 않는다.

다음은 글자 번호를 고르게 하는 방식을 앱에 붙이기보다 서버가 확정한 수치·단위/문장 후보 경계를 제공하는 계약을 설계하고, 규칙 기반 후보의 누락·오탐을 먼저 오프라인 비교하는 것이다. 의미/관계 선택은 여전히 별도 검증 대상이다. 실제 planned/unknown 양성·전체 문서·다양한 정치 이슈/중립성·최종 브리핑 품질은 미검증이다. 개발ab6654e/v9·API/DBOS/권한/DB/공개/UI/수집기·월 예약은 그대로이며 main/운영은 D013 유예다.


## 서버 수치 후보 · 오프라인 인수 · 2026-10-19

[명세](../../docs/changes/numeric-candidate-index.md).

source515aa26의 순수 후보 SDK를 기존과 byte-identical인 두 whole quote packet(인용2/1)에 오프라인 적용했다. 원문을 다시 수집하지 않았고 신규 provider/사용자 세션/앱 실행은 모두0이다. controller가 원문·모든 문장/후보의 expression/각 atom·unit/null·separator/qualifier·lexical hint/ID/원문 위치와 현재 Source 검증 결과를 직접 읽었다.

사전 고정 수치 gold6/5개는 모두 정확 후보로 보존됐다(11/11). 별도 날짜/식별자4/2개도 모두 남아 총 후보10/7개다. 하위 항목을 숫자 후보로 남기고 단위·하한/범위 양끝/명시 수식어를 원문과 연결했다. 지수 표기의 단위 부재는 null이며 증감의 명시 p를 다른 값에 복사하지 않았다. 이 결과는 수치 표기/위치 보존이며 대상·시점의 의미 연결/관측·전망/조건·포함 관계의 인수가 아니다.

별도 사전 고정 반례10건의 지원 표기 후보37개도 expression/atom/단위/수식어/종류/원문 위치가 기준과 일치했다. 범위·음수·배율·comma/소수·긴 단위/조사 배제·날짜/법령/이름 식별자·모호 표기·반복/Unicode/control/CRLF·줄바꿈 범위 분리를 확인했다. malformed comma/다중 점은 ambiguous로 보존하고 실제 달력에 없는 날짜도 temporal 표기 힌트일 뿐 날짜 진실로 인증하지 않는다. 지원 밖 한글 수사·전각 숫자 두 건은 추출0으로 따로 남겼다. 따라서 관측된 지원 후보의 누락/오탐0을 한국어 전체 수치 recall100%로 확대하지 않는다. 원래 gold·자료·분모를 수정해 성공시키지 않았다.

순수 index JSON은 두 자료에서6,012/3,593 UTF-8바이트이며 같은 자료의 v3 prompt3,548/1,567바이트보다 크다. 출처/위치 구조를 가진 저장·검증 packet이므로 provider-ready나 토큰/청구 절감으로 부르지 않는다. 향후 짧은 후보ID의 provider 계약과 전체 schema/instructions/framing/원문 budget preflight를 별도로 검증해야 한다. 이번 모델 사용량은 호출 자체가0이며 이전 v3 input4,485/output947의 실패 사용량·v3/v2 각각 거부2·v1 부분1/거부1·앱4/12와 모든 과거 실패/미판정은 보존한다.

작업 검토에서 배율 continuation의 하이픈 범위 흡수/날짜 우선순위 우회, 초과·미만 suffix 충돌3건을 찾았다. 각 RED→GREEN으로 수정하고 수정 범위 재검토에서 모두 해결(C0I0M0)됐다. 신규151/agents1074·Ruff/format42/mypy16와 기존409파일 base/fix byte동일을 확인했다. 수정 전의 사전 전체 검사는 중단하고 구 source CI39248144627은 cancelled로 보존했다. 이들은 최종 gate/CI 성공 증거가 아니며 수정 후 단일 최종 전체 검사·전체 독립 검토/CI는 별도 인수한다.

다음은 서버가 확정한 후보ID를 모델이 선택하는 출력 계약을 만들고, 수치 대상·시점·상태/조건·관계 의미와 누락을 같은 자료에서 검증하는 것이다. 그 뒤 앱의 전역 예산/예약·DBOS 실행/중단 복구·현재 권한/취소·최종 브리핑을 함께 인수한다. 유한 문법/단위 사전의 누락/잡음·cap256 전체 거부와 구두점/LF 문장 경계의 문맥 비용은 Spec/D022에 남긴다. 개발ab6654e/v9·API/DB/공개/UI/수집기/월 예약은 유지하며 main/운영은 D013 유예다.


## 후보 선택 SDK · 실제 두 자료 인수 · 2026-10-20 KST

source81ca4ef의 단독 SDK를 원래와 byte-identical인 두 private packet(whole 인용2/1)에 적용했다. 원래 수치6/5·의미 gold를 호출 전에 고정했고 controller가 모든 원문·raw/null·반환 span/단위/범위·subject/period/status/condition과 관계를 직접 읽었다. 신규 SDK2회/실제 Responses2요청·자동 retry0·사용자 세션/앱 실행0이며 반환1·거부1·의미 완전 충족0/2다. 호출 성공이나 수치 선택을 의미 통과로 바꾸지 않는다.

반환된 한 제안은 수치6/6과 각 단위/null·열린 하한·두 atom 범위를 원문 그대로 보존했다. 하위 항목의 포함1과 병렬2 관계, 대상·시점과 현재/전망 분류도 맥락과 일치했다. 다만 사전 gold가 요구한 전망의 전제·관리 문구를 condition에 연결하지 않고 null로 남겼고 상태 근거6개가 실적/전망 표현 대신 수치 자체를 가리켰다. 이 문구의 조건/수단·계획 역할은 고정 인수 기준의 해석이며 독립 사실 판정이 아니다. 따라서 부분 충족이다. 전체 관계/문서 coverage나 독립 사실 검증은 인증하지 않는다.

다른 raw 응답은 필요한 수치5개 외에 부수 날짜2개도 측정 사실처럼 선택했다. 비교 기준을 조건으로 넣고 반복 문구를 모호하게 지정한 두 anchor 때문에 전체 거부됐다. source별 private 오프라인 재생에서 같은 오류를 재현했으며 추가 모델 호출·출력 수리·gold 수정은 없다. raw 수치5개를 수용 제안의5/5로 집계하지 않는다. 증감 방향·상태의 명시 근거도 raw에서 충분히 분리되지 않았다.

실제 prompt는3,712/2,253 UTF8바이트, raw/normalized schema는2,784/2,562와2,727/2,505, instructions2,773이고 framing2,048/출력2,500 포함 envelope13,817/12,301이다. SDK상한20,000 이내의 실제 요청이지만 앱24,000 전체 예산/월 예약·DBOS/복구 인수가 아니다. 두 raw 응답 사용량은 input4,053/output1,166이다. 실패1건의 SDK known usage도 raw1771/511/1과 일치해 보존했다. 청구액은 검증하지 않았으며 미상/앱0을 무료로 해석하지 않는다.

새151/agents1254·정적 검사와 작업/전체 독립 Spec/품질 PASS(C0I0M0)를 확인했다. 기존377 파일 SHA와 baseline/current source의411 git blob이 동일하다. 전체 gate·PR54/source CI39389528867·Sites v75보존/현재 갱신·소유QA1/SDD 정리는 별도 최종 기록을 따른다. 원래 v3/v2 각각 거부2·v1 부분1/거부1·앱4/12·과거 실패 usage·이전 순수 후보11/11+6/6+지원37/37/미지원2건과 그 세 판단/비용은 유지한다.

이번 판단은 문장 안의 unique exact anchor와 연속된 전체 문장 관계다. 반복/문장 횡단 의미 근거를 놓치거나 유료 결과 전체를 거부할 수 있고, 정확한 위치도 의미 오연결을 막지 못한다. 실제 반복 문구 거부1건에서 이 비용을 관측했다. 상태·조건·날짜/측정값 역할의 계약과 모델 판단을 다음 설계에서 재검토한다. 실제 예정/불명 양성·다양한 정치 쟁점/중립성·최종 브리핑/앱 인수는 미완료이며 개발ab6654e/v9와 D013 main/운영 유예를 유지한다.


## 수치 역할의 고정 기준 평가기 · 기존 두 결과 오프라인 재생 · 2026-10-20 KST

source09d6624의 새 평가기로 기존 SDK 반환1/거부1을 재생했다. 추가 모델/앱/사용자 세션은0이고 원래 원문·gold·응답·의미 완전 충족0/2와 기존 input4,053/output1,166을 변경하지 않았다. 사후 변환 reference를 평가기 실행 전에 별도 hash로 고정했으며, 원래 gold의 비문자적 역할 설명과 상태 근거 미지정은 결과에 맞춰 채우지 않고 미판정으로 남겼다.

반환 제안은 예상6/수용6이며 fact 필드 검사27일치·1불일치·8미판정이다. 불일치1은 원래 기준이 요구한 전망 전제·관리 문구에 대한 condition null이다. 27개 일치는 27개 사실이나 의미 품질 통과율이 아니며, 8미판정에는 원래 exact 문구가 지정되지 않은 상태 근거6개와 비문자적 subject 설명2개가 포함된다. 거부 건은 예상5·수용 수 미상(null)·빈 검사와 원래 실패 usage1771/511/1을 보존했다. raw5개를 성공으로 세지 않는다. 기준의 조건/수단 역할도 평가자 해석이며 독립 진실 인증이 아니다.

신규79/agents1,333·Ruff/format/mypy·기존379파일 SHA 동일을 확인했다. 작업/전체 독립 검토·전체 gate·PR/CI·Sites와 소유QA/SDD 정리는 최종 인계를 따른다. 현재 SDK/모델 호출/provider bytes·앱/API/DB/UI/worker/수집기를 바꾸지 않았다. 다음은 이 기준을 유지하며 상태/전망 전제·비교 기준·부수 날짜 역할의 생성 계약을 재검토하는 일이다. 기존 parser 세 판단/unique anchor 판단과 모든 이전 실패 비용·개발ab6654e/v9·D013 유예는 유지한다.


### 원래 검토 지적·수정과 재생

작업 검토가 excluded subclass 필드의 직렬화 누락1건(Important)을 확인했다. source09의 사전 전체 검사는 수정 전에 중단했고 CI39393254153 취소를 요청했으므로 최종 성공에서 제외한다. source2bd1f37에서 직렬화 전 canonical 모델/필드 구조를 재귀 검사하도록 수정했다. 신규 회귀7개 RED→GREEN·평가기86/agents1,340·Ruff/format/mypy·기존379파일 SHA 동일을 확인했다. unsupported subclass를 허용하는 API는 아니다. 원래 helper/provider/모델 bytes는 동결했다.

수정 source에서 동일한 사후 변환 reference를 hash 변경 없이 다시 재생했다. 조건 불일치1·미판정8과 거부1/수용 수null·모든 known usage가 그대로다. 모델 재호출·원문/gold/분모 조정은 없다. 수정 범위 재검토·전체 독립 검토·최종 전체 gate/PR55 CI·Sites·소유QA 정리는 최종 receipt를 따른다.


### 수치 역할 평가기 · 최종 전체 검사

검토된64b2f19(실행 코드2bd1f37)에서 Python4,854+JS820=5,674개·Ruff/format330/mypy133·ESLint/TS/build/OpenAPI drift가 통과했다. 실패/skip/warning0이다. 작업 검토 Important1건을 고친 뒤 수정 범위 재검토와 전체 독립 Spec/품질 PASS(C0I0M0)를 확인했다. source09의 중단된 사전 gate/취소 CI39393254153은 최종 성공에서 제외한다. [Draft PR55](https://github.com/DigestWorks/IssueDigest/pull/55)는 PR54 기반·미병합이다. [최종 source CI39394088829](https://github.com/DigestWorks/IssueDigest/actions/runs/39394088829)와 Sites/소유QA·SDD 정리는 최종 게시 receipt를 따른다. 이후 변경은 Markdown뿐이다. 신규 모델0·원래 의미0/2/모든 실패 usage·이번 세 판단/비용과 과거 판단을 유지한다.

## 공유 측정 맥락 · 합성 구조 검사

[명세](../../docs/changes/shared-measurement-context.md)의 공통 항목/범위·보고 사건·수치 연결과 목적/조건 분리를 합성 자료로 검사했다. 새 원본/파생 프레임 전체 재구성·strict canonical·다른 인용/중복/unused·상한·관계 재사용을 검증한다. 전체6,916개 검사(Python6,096/JavaScript820)를 통과했으나 모델 호출0이고 모델 선택·의미/중립성·브리핑 인수는 아니다. 기존 생성4회0/4와 추론 비교 의미0/2·다른2미판정, 미확인 비용/원래 gold는 유지한다.

## 공유 맥락 생성 SDK · 오프라인 인수

[명세](../../docs/changes/shared-context-generation.md)의 focused103/agents2685·전체7,019개 구조 검사를 확인했다. 기존4자료 전체 원문은 새 요청 envelope18,119/16,641/15,895/16,237로20,000 이내다. controller mockHTTP4회는 빈 출력과 요청 형식만 검사했고 실제 모델 호출0·출력 의미 판정0이다. 모의 usage는 비용이 아니며 최대 record/역할 출력의 수용 보장은 없다. 원래 의미 실패/미판정·기준을 보존하고, 새 미관측 자료/의미 기준·상한을 사전 고정한 별도 인수와 구분한다.

## 공유 맥락 실제4회 · 실패 보존

[사전 기준·결과](../../docs/research/shared-context-acceptance.md). 기존2+사전 선택 신규발췌2, 각1회/총4응답·반환1/거부3이다. 반환1은 필수 별도 범위 누락으로 의미0/1이며 다른3은 미판정이다. 전체 게이트0/4와 의미 분모1을 구분하고 신규2의 의미 정확도를0/2로 표현하지 않는다. 단일 평가자/공식자료 소표본·독립 holdout 아님·기준/실패/usage 보존·상한 소진 후 재호출0이다. SDK/기준/실행417파일은 불변이므로 전체7,019검사는 기존 증거로 유지하고 연구 문서/링크·private 제외를 확인한다. 실제 비용 참고$0.1138775/청구·환율 미검증, 앱 변경0이다.

## 동일 공유 계약 모델4회

[사전 기준/결과](../../docs/research/shared-context-model-comparison.md). 같은4자료·지침/schema/low에서 모델 필드만 바꿨다. GPT-6.1 Sol4응답/4반환·의미2/4/미판정0이며 직전 의미0/1·다른3미판정과 분모를 구분한다. 원래 source/reference/결과를 보존하고 상한 소진 후 재호출0이다. 입력13,073/출력3,265(cache write12,569 포함)의 참고 비용$0.0650805·실제 청구 미검증, 최초2요청 겹침/단일 평가자·독립 holdout 아님을 기록했다. 실행417파일 불변으로 기존7,019검사는 재사용이며 앱 변경0이다.
