# 대상·계층적 범위 지침 · 새 자료 제한 인수

2026-10-21. 실행 f8a2357·새 지침/기존 strict 계약은 유지한다. 연구/문서 작업으로 앱·기본 모델·서버/main은 바꾸지 않고, 기존7,049개 전체 검사 증거를 재사용한다.

## 호출 전 고정

새 공식 자료의 완전한 한 문단씩을 선택했다. 전체 기사나 무작위/독립 holdout은 아니며 단일 작성자가 자료 선택·사전 기준·판정을 맡는다. 이전 개발 자료·응답·기준은 변경하지 않는다.

- 지역개발 자료 H: [경상북도 공식 보도자료](https://www.gb.go.kr/Main/open_contents/section/finace/page.do?BD_CODE=bbs_bodo&B_LEVEL=0&B_NUM=510671301&B_STEP=510671300&Start=180&V_NUM=14611&bdName=&cmd=2&dept_code=&dept_name=&key=4&mnu_uid=6792&p1=0&p2=0&tbbscode1=bbs_bodo&word=)의 첫 본문 문단. 사업 수와 확보 국비의 대상·상위 지역·열거된 하위 지역, 관측 상태·과거 서술을 요구하고 연도 표제를 별도 수치로 세지 않는다. 기관의 사업 주관/확보 행위를 보고 발언으로 추정하지 않는다.
- 인재지원 자료 G: [과기정통부 정책뉴스](https://www.korea.kr/news/policyNewsView.do?newsId=148970933)의 장학 지원 확대 문단. 호출 전 후보 검사에서 복합 단위·근사 표현이 누락돼 전체 의미 게이트를 충족할 수 없음을 확인했다. 유료 호출 대상에서 제외하고 결정적 후보 문제로 별도 보존한다. 미호출을 모델의 의미 실패나 성공으로 세지 않는다.

H만 최대1요청/실패 포함·재시도/수리0, GPT-6.1 Sol/low·30초/no-store·전체20,000/출력2,500을 유지한다. [공식 모델 문서](https://developers.openai.com/api/docs/models/gpt-6.1-sol)의 지원을 확인했고 별도 날짜 snapshot이 없어 제공 시점 관측으로 기록한다. source/reference·지침/동적 schema·실제 HTTP body를 호출 전에 hash 고정하고 모의 전송을 검증한다. 실패·불충분 출력에도 증액/대체/재호출/부분 삭제를 하지 않는다.

고정 기준의 필수 수치·대상·별도 범위·시점·상태/보고·직접 관계를 원문과 수동 대조한다. 구조 반환과 의미 충족을 구분하고 거부/미응답은 의미 미판정이다. G의 사전 차단과 H의 실제 시도·반환/의미 판정 분모를 분리한다. 과거2/4와 다른 자료이므로 전후 정확도/개선율을 계산하지 않는다.

raw usage·cached/write·reasoning(출력 포함)·tier·시간을 보존한다. [공식 standard 요율](https://developers.openai.com/api/docs/pricing)의 입력$2/cache$0.10/write$2.50/출력$10 per1M을 참고하고 write는 입력의 부분집합으로 중복 가산하지 않는다. 실제 청구·환율은 미검증이다. 원문/ID·상세 reference/응답은 비공개 연구 기록에만 둔다. 현재1문단의 완료 출력은 최대 record/장문 역할·전체 앱 품질 인수가 아니다.
