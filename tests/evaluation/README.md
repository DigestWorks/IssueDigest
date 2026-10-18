# Evaluation

실제 자료의 검색·근거·관계·생성 화면 평가 기준을 보관한다. 공개 질문/기준과 비공개 원문/인용/버전 정보를 구분한다.

- [지방국립대 등록금 지원 · 질문20개](first-issue.md): 문항 정의 완료, 실제 검색/AI 실행 전. 필요한 근거·부족한 자료·기대 화면·판정 기준을 포함한다.
- [자료 상태](../../docs/research/first-issue-corpus.md)와 [출처 목록](../../docs/research/first-issue-sources.tsv): 확보 수·이용·파싱·초기 풀을 구분한다.

아래 내부 러너는 저장 근거 검색 지표만 평가한다. `pytest`의 단위/계약 검사 통과를 이20문항의 제품 품질 평가 결과로 표시하지 않는다. 실제 실행 결과는 자료·검색·모델·프롬프트 버전과 함께 추가한다.

## 운영자용 저장 근거 검색 평가

`issuedigest-evaluate-retrieval`은 운영자가 명시 실행하는 내부 도구다. 기존
`question_terms`와 `retrieve_snapshot_ids`를 그대로 호출한다. 초기 전략 profile은
`question-terms-v1`이며, 투영 profile `literal-ngrams-v1`과 구분한다.
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

합성 회귀 실행(전용 local test DB만 지정):

```sh
uv run pytest packages/storage/tests/test_retrieval_evaluation.py \
  apps/worker/tests/test_retrieval_evaluation_cli.py
```
