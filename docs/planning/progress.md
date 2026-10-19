# 진행 기록

## 구현·실제 인수·개인 개발 반영 · 원문 날짜·포함 관계 보존 · 2026-10-19 KST

현재 개인 개발 웹/API/조사 worker는 `f839ae0`이며 [Draft PR45](https://github.com/DigestWorks/IssueDigest/pull/45)(PR44 기반)다. 새 private v8은 동결 planner7→승인 저장 검색→최대5근거 고정→최종 생성으로 이어진다. 정확 인용에 있는 유효한 YYYY-MM-DD만 timeline 날짜 후보로 최대16개 허용하고, 후보가 없으면 요약/비교로 설명한다. 개별 인용에 해당 날짜가 있는지도 다시 검사한다. 날짜가 있다는 것과 실제 사건을 뒷받침한다는 것은 다르다. 수치의 포함 관계와 목표·관측 실적·조건부 전망을 보존하도록 지시하며 자유 문장의 의미 정확성을 schema 통과로 인증하지 않는다. 원래 질문/검색·정확 인용·첫 열린 요약·기존 소비자 디자인과 공개 계약은 유지한다.

전체 Python3,553+JS744=4,297개·lint/format/types/build/contract와 작업별/전체 독립 검토(Critical/Important/Minor0)를 통과했다. [source CI](https://github.com/DigestWorks/IssueDigest/actions/runs/39208107011)도 성공했다. 기존v2~v7 provider/지침/한도·원래 workflow/version/유료 checkpoint와 저장 결과를 보존한다. 새v8은 planner7 유료slot1→search_v8 step2→final_v8 유료slot3을 회복한다. 자체 합성 신원으로390/1440·두 테마·첫 열린 요약/접힌 상세·정확 원문/초점·재열람(읽기POST0/페이지오류0)을 확인했다.

실제 고정3앱실행/공급자6요청·자동재시도0은 모두 완료했고 답변2·자료 부족1이다. 의미 판정은 부분 충족1·이번 목표 소표본 충족1·자료 부족1로 구분한다. 이전v7에서 원문에 없는 날짜 때문에 실패했던 표현은 날짜 없는 요약/비교로 완료했다. 첫 답변6문장/6평가/정확 인용3개와 둘째7문장/7평가/정확 인용3개를 전부 대조했다. 둘째는 부분 항목의 포함 관계를 명시하고 독립 합산을 피했다. 없는 전국 여론 수치는 만들지 않았다. 다만 첫 답변의 하한 수치를 ‘목표의 일부’로 표현한 상한 암시, 질문에 없던 검색어 추가·무관 자료 선택, 전망의 조건부 뉘앙스는 남았다. 실제3건 모두 정확 날짜 후보0이며 날짜 있는 실제 제공자 검증은 하지 않았다(합성 Python/client/UI 검증만 통과). 일반 시사·중립성·의미 품질 전체 통과가 아니다.

실제 cached 사용량은 입력9,915/출력1,932토큰,3실행 지연7.80/7.14/3.94초다. 유료 응답6개 모두 확인했고 실제 청구 금액은 미검증이다. 앱 usage0은 무료를 뜻하지 않는다. 이전v7 고정3/6(부분답변1/부족1/실패1), v6 초기4(부족1/실패3)+별도2, v5 초기4+별도2의 실패·부분 충족 분모는 그대로 보존한다.

개발 앱은 활성 작업0에서 정상 재기동·단일 worker lock1·source/cwd·정적19파일/외부6assets 일치를 확인했다. 이전94assets/원래 source/복귀 경로와 수집기a908083/config/runner/cron을 보존했다. schema0009·자료15/인용49/검색36/receipt1/공개1·계정/세션·HTTPS/비회원401 경계를 유지했다. 서버 밖 사전·직전·사후 full/app 백업과 별도PG18.6 복원에서 직전/사후/백업 직후/복원의23public테이블 rowhash/count 전체 일치를 확인했다. 실제 기존 AI 결과는0개이므로 역사 실제 결과 재생을 주장하지 않는다. DBOS registry·vector/역할까지 포함한 완전 DR은 아니다. 외부 정적 파일 읽기의 일시 DNS 오류는 설정 변경 없이 재조회해 정상 확인했다. main/운영 유예(D013)는 유지한다.

판단: 최대100인용·16날짜는 상한이며 모든 최대 조합의 동시 입력을 보장하지 않는다. 의미 보존 지침·원문 전체와 합산24,000 예산을 유지하고 실제 사전 검사에서 초과 입력을 거절한다. 잘못된 판단이면 큰 맥락·planner 사용량이 많은 질문이 최종 생성 전에 자료 부족으로 더 자주 끝날 수 있으며, 추가 유료 재시도 없이 자료 선택/예산 정책과 테스트를 재설계해야 한다.

- [현재 명세](../changes/briefing-source-fidelity.md), 소스12f1ad4/검증·실행f839ae0. 임시 작업 보고서만 추적에서 제외하고 private 검증 기록에 보존했다. 동작 변경은 없으며 이후 문서 커밋은 실행 소스와 구분한다. 이전v7 cached 날짜 실패를 모델 호출 없이 재현한 뒤 새 고정3/6을 별도 수행했다. 실제 신원을 대행하지 않았다.
- 독립 작업/전체 source 검토 모두 승인·열린 지적0. 남은 의미 한계는 위의 실제 평가 결과이며 source 검토 승인과 다르다. Sites v66 archive 보존·사본 갱신/출판·자체 QA 정리 receipt는 다음 기록에서 확정한다. 사용자 탭은 열지 않았다.

## 작업 시작 · 원문 날짜·포함 관계 보존 · 2026-10-19 KST

- PR44/379720f·명세briefing-source-fidelity로 이어간다. v7 cached 날짜 추정 실패와 부분수치/상태의 의미 한계를 분리해 보완한다. exact quote 날짜가 없으면 timeline을 생성 선택지에서 빼고 기존 비교/요약으로 설명한다. 추가 모델 재시도/웹 탐색/임시UI를 만들지 않는다. 기존v2~v7 bytes·검색/비용/권한/복구·공개/수집기를 보존하고 새v8만 적용한다. 작업/전체검토·실제3/6·개발/Sites는 증거 뒤 기록한다. main/운영 유예·사용자 탭 유지다.

## 최종 출판·정리 · 질문별 조사 계획·승인 자료 검색 · 2026-10-19 KST

- [Sites v66](https://lawdigest-rebuild-plan.ijaesinii.chatgpt.site) 공개 유지·native succeeded. source `5600489fd45358aa39c7a5977952abc8d10d64fd`, saved `appgprj_6ac612dd42708191a7a0c8377be64d48~appgver_3c1b6331a6a88191adab42a45babb2ea`, deployment `appgdep_6ad5ad1acd9c81918276889d95baab4d` (2026-10-19 05:39:52 UTC). 이전v65와 전체 역사·실패 분모를 보존했다. 저장소 사본 기준50e28cc·실행57c71ec·[Draft PR44](https://github.com/DigestWorks/IssueDigest/pull/44)이며 사본 이후의 이 최종 receipt는 저장소가 원본이다.
- 소스57c71ec의 [CI39205150597](https://github.com/DigestWorks/IssueDigest/actions/runs/39205150597)가 성공했다. 이후 커밋은 인수/출판 기록·문서 정합화뿐이며 실행 코드는 바꾸지 않았다. 현재 의미 품질은 실제3회 중 답변 부분 충족1/부족1/실패1이며 날짜/포함 관계·검색 잡음의 남은 개선을 유지한다. 소표본 성공이나 source CI를 전체 B2C 품질 통과로 확대하지 않는다.
- 문서15파일의 로컬 링크258개·공개 접속값 제외·diff 공백 검사, Sites HTML51개/로컬 링크·anchor·asset1,148개/공개 텍스트134파일의 실제 비밀값 제외 검사를 통과했다. 기존 레이아웃의 텍스트/사본 갱신이라 Sites의 새 브라우저 화면 검사는 하지 않았다. 자체 앱 검증 브라우저만 사용했고 사용자 탭을 열거나 이동하지 않았다.
- 자체 검증 브라우저·합성 HTTPS API와 소유label/전체ID/pinnedimage/loopback이 일치하는 합성·모델·복원PG3개 및 익명 볼륨만 정리했다.34556/25485/25486/25487 닫힘을 확인했다. 실제 개발 앱·수집기·다른컨테이너/worktree·원래 source/복귀 경로·서버 밖 백업·상세 의미/검토 증거는 보존한다. 이 계획의 SDD 작업/독립 검토/단일 맥락 판단은 private archive한 뒤 해당 ignored scratch만 제거했다. 판단과 잘못됐을 때의 비용은 D022와 아래 기록에 남겼다. main/운영 병합은 하지 않았다.

## 개발 적용 · 질문별 조사 계획·승인 자료 검색 · 2026-10-19 KST

- 현재 개인 개발 웹/API/조사 worker는 `57c71ec`이며 [Draft PR44](https://github.com/DigestWorks/IssueDigest/pull/44)(PR43 기반)다. 새 private v7은 질문→검색어 계획1회→현재 권한의 승인 저장 색인 검색→최대5근거 원자 고정→최종 생성1회다. 원래 질문 검색을 항상 포함하고 계획 검색과 원래 질문 우선 라운드로빈으로 합친다. 계획은 근거가 아니며 외부 웹 탐색·자동 등록/공개 게시를 추가하지 않는다. 첫 요약·보수적 제공 자료 귀속·정확 인용·부족 응답과 기존 소비자 디자인을 유지한다.
- 전체 Python3,459+JS694=4,153개·lint/format/types/build/contract와 작업별/전체 독립 검토를 통과했다. raw boolean 사용량 검증 지적은 실제 응답/합산·cached 재생 경계에서 보완·재검토했다. 자체 합성 신원의 실제3상태·390/1440·두 테마·첫 열린 요약/접힌 상세·정확 원문/초점·재열람(읽기POST0/페이지오류0)을 확인했다. 기존v2~v6 provider bytes/지침/한도/유료slot1·결과와 공개 계약을 보존하며 새v7은 exact paid1/search2/paid3을 회복한다.
- 실제 고정3앱실행/공급자6요청·자동재시도0은 브리핑 완료1(의미 부분 충족)·자료 부족 완료1·검증 실패1이다. 원래 문자 검색0이던 영어 표현의 주택 질문은 계획 검색으로 정확 자료1건을 찾았으나, 최종 timeline이 원문에 없는 정확 날짜2개를 추정해 표시를 차단했다. 성공까지 다시 호출하지 않았다. 완료 답변의9문장/평가·선택 인용3개와 실패 checkpoint의6문장/인용을 직접 대조했다. 목표·실적·조건부 전망의 첫 결론은 읽히지만 세부 항목의 포함 관계 누락과 목표/확정 결과의 모호한 표현은 남았다. 자료에 없는 전국 찬성률·인지도는 생성하지 않고 근거 부족으로 끝났다. 검색 개선·구조 통과를 전체 의미 품질 완료로 해석하지 않는다.
- cached 실제 사용량은 입력9,413/출력2,087토큰이며3실행 지연은8.39/5.76/3.96초다. 모든 유료 응답6개를 확인했고 실제 청구 금액은 미검증이다. 실패/취소·권한 변경·응답 유실의 앱 usage0은 무료를 뜻하지 않으며 기존 보수적 예약을 유지한다. 이전v6 초기4(부족1/실패3)+별도2와v5 초기4+별도2의 실패·부분 충족 분모를 보존한다.
- 개발 웹/API/worker를 활성 작업0에서 정상 중지·재기동하고 단일 worker lock1·새 source/cwd·정적19파일/외부6assets 일치를 확인했다. 이전90assets/원래 source/복귀 경로와 수집기a908083/config/runner/cron을 보존했다. schema0009·자료15/인용49/검색36/receipt1/공개1·계정/세션·HTTPS/비회원401 경계를 유지했다. 서버 밖 사전·직전·사후 full/app 백업과 별도PG18.6 복원에서 직전/사후/백업 직후/복원의23public테이블 rowhash/count 전체 일치·15canonical을 확인했다. 실제 기존 AI 결과는0개이므로 역사 실제 결과 재생을 주장하지 않는다. DBOS registry·vector/역할까지 포함한 완전 DR은 아니다. main/운영 유예(D013)는 유지한다.
- 판단 기록: 원래 질문을 보존하고 선택적 이전 AI 맥락만 planner의 실제 JSON UTF-8 잔여 예산/code-point 경계로 줄이며 잘림을 명시한다. 최종 생성의 기존 bounded 맥락·원문/인용은 보존한다. 잘못되면 검색 계획의 관련성이 낮아질 수 있어 맥락 선택/예산 정책·테스트를 조정해야 하며, 과거 데이터 재작성이나 추가 모델 호출은 필요하지 않다. [D022 후속 판단](decisions.md)을 따른다.
- 다음 우선순위는 검색 잡음·날짜와 포함 관계의 의미 보존·다양한 실제 질문 평가 및 검증된 모듈 점진 전달이다. 다매체 발견·관심/변화/공유·개인화·pgvector/Neo4j 서비스 연결·외부 자율 탐색과 일반 B2C 품질/운영 출시는 후속이다.
- 소스 CI57c71ec는 [실행39205150597](https://github.com/DigestWorks/IssueDigest/actions/runs/39205150597) 성공했다. Sites v66 게시/이전v65 보존·사본/QA 정리는 위 최종 출판 receipt를 따른다. 사용자 브라우저 탭은 열거나 이동하지 않는다.

## 작업 시작 · 질문별 조사 계획·승인 자료 검색 · 2026-10-19 KST

- PR43/7ed6730의 검증된 기반에서 feat/briefing-search-agent·[명세](../changes/briefing-search-agent.md)로 이어간다. AI 검색어 계획→현재 권한의 승인 저장 자료 검색→최대5근거 고정→기존 브리핑을 연결한다. 검색 계획은 사실/근거가 아니며 외부 웹 탐색/자동 수집·공개 게시를 뜻하지 않는다.
- v7은 최대planner1+최종1회, 전체24,000토큰/출력2,500·자동재시도0와 월/건별 예약을 유지한다. 기존v2~v6 실제 지침/schema/prompt/원래 namespace/slot1과 결과를 동결하며 새 durable1/2/3은 별도 workflow에서만 쓴다. 작업별 TDD/독립 검토·전체gate·실제 고정3실행·개발 보존/복원/반영·Draft PR·Sites는 각각 증거 뒤 기록한다. main/운영 유예·사용자 탭 유지다.

## 최종 출판·정리 · 첫 결론·근거 부족·문장별 귀속 · 2026-10-19 KST

- [Sites v65](https://lawdigest-rebuild-plan.ijaesinii.chatgpt.site) 공개 유지·native succeeded. source `f0ffc035de158829687e9ff89727cbf5fd007b1b`, saved `appgprj_6ac612dd42708191a7a0c8377be64d48~appgver_6a21a3dd69d481919321da0d314bed57`, deployment `appgdep_6ad596344d24819195b292edcbb948cb` (2026-10-19 04:02:11 UTC). 이전v64와 그 이전 기록을 보존했다. 저장소 사본 기준6584471·실행7566c3a·Draft PR43이며 사본 이후의 이 최종 receipt는 저장소가 원본이다.
- 기존 레이아웃의 요약/마일스톤·실제 초기4+별도2/남은 한계·문서8개를 갱신했다. HTML50개·로컬 링크/asset/anchor1,139개·공개 텍스트131개와 실제 접속/키 비포함 검사를 통과했다. 텍스트 변경에 Sites 브라우저 QA를 반복하지 않았으며 native 성공 응답으로 게시를 확인했다. 사용자 탭을 열거나 이동하지 않았다.
- 자체 검증 브라우저·합성 HTTPS API와 소유label/전체ID/pinnedimage/loopback이 일치하는 합성·모델·복원PG3개/익명 볼륨만 정리했다.34546/25482/25483/25484 닫힘을 확인했다. pinned image·다른 컨테이너/worktree·실제 개발 앱/수집기·원래 소스/복귀 경로·서버 밖 백업/상세 증거는 보존한다. 이 계획의 SDD 검토/두 판단/실행 기록은 private에 archive한 후 해당 ignored scratch만 제거했다.
- 최종 실행 코드는7566c3a의 전체3,967개·독립 source 검토·[CI39196768625](https://github.com/DigestWorks/IssueDigest/actions/runs/39196768625) success다. 이후ee62ee6/6584471과 이 receipt는 문서만 변경했다. 코드 검사 반복 없이 문서 링크/개인 접속값/표현 정합성과 Git diff를 확인한다. main 병합·운영 게시·새 모델 호출/권한/수집기 변경은 없다.

## 개발 적용 · 첫 결론·근거 부족·문장별 귀속 · 2026-10-19 KST

- 현재 소스: 개인 개발 웹/API/조사 worker7566c3a·[Draft PR43](https://github.com/DigestWorks/IssueDigest/pull/43)(PR42 기반). 첫 열린 요약의 core conclusion·제공 자료에 대한 보수적 귀속·핵심 근거 부족 비답변을 연결했다. provider에 category/source_subject와 일반 claim의 event_date를 요구하지 않고 typed timeline만 정확 날짜를 받는다. canonical documented/최종 원문/인용/prefix/날짜·공개v1/v2/빈 reviews·기존2/3/4/5 지침/이름/version/정수slot1·저장 결과/복구와 소비자 디자인은 유지한다.
- 구조 검증: 최종7566의 전체 Python3,316+JS651=3,967개·Ruff/format·mypy117·JS lint/types·SPA/생성 계약 통과, 경고/skip/실패0. [소스 CI39196768625](https://github.com/DigestWorks/IssueDigest/actions/runs/39196768625) success. Task1 두 Important는 Unicode code-point/공백 회귀로 해결했고 Task2·변경 전체 독립 검토 C0/I0다. 최종 README Minor와 후속 custom-subject 예외 문구를 문서 정합화에서 수정했고 실행 코드는 바꾸지 않았다. 기존 공통 출처 제목/비답변의 언어별 Unicode 경계는 그대로이며 별도 한계다.
- 실제 초기4회(f462): 완료1은 제공 자료에 없는 전국 찬성률/인지도를 만들지 않는 정확 insufficient_evidence였고3건은 형식/주체/일반 날짜 검증에서 실패해 표시되지 않았다. 유료 checkpoint를 추가 호출 없이 읽었으며 초기 입력13,420/출력2,410토큰을 확인했다. 실패 앱 usage0은 무료라는 뜻이 아니다. 주택의 열린 전망을 확정 상한으로 읽은 cached 의미 오류도 기록했다. 실패 분모와 이전v5 초기4+별도2 기록은 보존한다.
- 실제 별도2회(7566): 주택 목표/실적/전망은 첫 요약에서 기준 기간·이상/예상 조건과 단정할 수 없는 한계를 보존했고, 같은9월 CSI/CBSI는 상승/하락의 다른 방향을 첫 요약에 제시했다. 후자는 원인/미래를 알 수 없다는 uncertain 설명도 담았다. controller가 전체7/6문장·동일 인용 평가·선택 원문을 직접 읽어 이 두 표본에서 충족으로 기록했다. 초기4+별도2 합계 입력20,185/출력3,867토큰·자동 재시도0·청구 금액 미검증이다. 성공할 때까지 재호출하지 않았다. 새 DTO 교육 예산과 현재 provider 비답변의 추가 실제 재호출은 미실행이며 일반 의미 품질 통과는 아니다.
- 화면/읽기: 별도 합성 신원·실제 빌드/API/평가 PG에서6상태(3실패/부족1/답변2), 첫 요약·접힌 상세·분류/설명·390/1440 두 테마·정확 원문 highlight/Escape/focus·가로 넘침 없음·reload/기록과 읽기POST0/페이지오류0을 확인하고 모바일 화면을 직접 검토했다. 실제 사용자를 대신 로그인하거나 질문하지 않았다. 외부 HTTPS web/login/health/status/공개200·비회원401/noCookie/no-store·공개payload 동일, 배포 index/6asset가 로컬 빌드와 정확히 같았다. 첫 외부 확인의 임시 DNS 실패 후 정상 DNS/TLS 재확인이 성공했으며 설정 변경/인증 우회는 없었다.
- 반영/보존: 새 격리 source/venv/static19개를 준비한 뒤 활성run/workflow0에서 API/worker를 정상 중지·재기동했다. 단일 advisory worker lock1·새 cwd/source와v6 지침 hash를 확인했다. 이전86assets·원래 source/복귀 경로는 유지한다. schema0009·자료15/인용49/검색36/receipt1/공개1·계정/세션과 수집기a908083/source/config/runner/cron은 보존했다. 서버 밖 사전·직전·사후 full/app archive를 보존하고 직전/사후/백업 직후/별도PG18.6복원의23public테이블 rowhash/count 전체 일치·15canonical을 확인했다. 기존 실제 AI 결과는0개로 과거 실제 결과 재생을 주장하지 않는다. 역사 결과는 합성 복구 증거다. public 행 비교는 DBOS registry 밖이며 vector/역할까지 포함한 완전 DR은 아니다.
- 판단 기록: v6 nonblank는 Python/ECMAScript 공백 합집합·원문 불변으로 통일했다. 잘못되면 좁은 판정/테스트 수정 비용이며 migration/추가 호출은 없다. 아직 미배포였던 v6의 긍정 해석을 고정 제공 자료 attribution으로 단순화하고 별도2회를 허용했다. 잘못되면 documented 세분화 감소·구현/검토 재작업·최대2API 비용이 생긴다. canonical/historical documented는 보존한다. [D022 후속 판단](decisions.md)을 따른다.
- 남은 경계: 질문 중 승인 도구 탐색·점진 전달·다매체 발견·개인 관심/변화/공유/추천·일반화된 의미 품질과 main/운영 출시는 후속(D013)이다. 실제 원문/질문/ID/키/접속/backup/상세 결과는 비공개에 보존한다. Sites 요약/이전v64 보존·소유 QA 정리·최종 출판 receipt는 다음 기록에서 확인한다. 사용자 탭은 열거나 이동하지 않았다.

## 전체 검사 통과 · v6 provider 단순화 · 2026-10-19 KST

- 최종 소스7566c3a에서 전체 Python3,316+JS651=3,967개·Ruff/format·mypy117·JS lint/types·SPA build·API 계약 검사를 통과했다. 경고/skip/실패0이다. 초기f462의 전체3,956개 기록도 별도로 보존한다.
- Task2 독립 검토는 명세 PASS/품질 Approved·C0/I0/M0이며 변경 전체 검토·별도 실제2회·개인 개발 반영은 이 시점 대기다. [Draft PR43](https://github.com/DigestWorks/IssueDigest/pull/43)은 PR42 기반으로 만들고 첨부했으며 main에 병합하지 않았다.
- 합성 v6 provider/날짜/인용/공백 검증과 기존 다섯 workflow/유료 checkpoint 재생이 통과했다. 역사2/4/5 파일 bytes·v3 schema/지침/예산 AST·기존 CanvasView·생성 API 계약은 그대로다. 실제 자료에서 의미가 맞는지에 대한 인증은 아니다.

## 실제 인수·생성 형식 보완 · 2026-10-19

- 제품f462b7b의 전체3,956개·독립 전체 검토 C0/I0/M0을 통과한 뒤, 사용자와 분리된 실제4요청을 실행했다. 자료 부족1건만 정상 완료했고 나머지3건은 category/source_subject 모순·인용에 없는 주체·non-timeline 날짜 때문에 안전하게 거부됐다. 응답은 표시하지 않았다. cached ModelResponse를 추가 호출 없이 읽어 입력13,420/출력2,410토큰을 확인했으며 실패의 앱 사용량0을 무료로 해석하지 않는다.
- [Task2 명세](../changes/briefing-core-answer.md)에 따라 pre-release v6 provider만 단순화한다. 새 AI 긍정 해석은 제공 자료에 귀속하고, 독립 사실의 자동 확정으로 삼지 않는다. core/summary/comparison의 날짜 필드를 없애고 timeline만 정확 날짜를 요구한다. documented canonical/과거 결과·최종 원문 검사·기존v2/v3/v4/v5는 유지한다. 초기4회 분모/실패를 보존하고 수정 후 별도2회만 추가해 총6회로 제한한다.
- 개발 서버 웹/API/worker가 여전히f90839e임을 직접 재확인했다. v6실사용/배포는0이며 Sites64는 그대로다. 새 독립/전체·구조/의미 인수 후 개발 적용과 출판 결과를 기록한다. main/운영 유예·사용자 탭 유지.

## 작업 시작 · 첫 결론·근거 부족·문장별 귀속 · 2026-10-19

- PR42/b626764 기반 `feat/briefing-core-answer`·[명세](../changes/briefing-core-answer.md). 현재 렌더러가 summary를 먼저 펼치지만 모델이 비교 결론을 details에 두는 경로, 본문 주체 누락과 핵심 근거 없이 uncertain만 채운 answer를 확인했다. 새v6의 첫 결론과 구조 제약을 구현하며 실제 의미 판단은 별도 인수한다.
- 기존v5도 historical로 고정하고2/3/4/5/6 원래 이름/version/정수slot1을 보존한다. 합성 TDD·독립/전체 검사 뒤 사용자와 분리된 검토 공개 텍스트/실제4회만 평가하며 이전 실패 기록을 지우지 않는다. 사전 백업/별도 app 복원23테이블·canonical15 보존을 확인했다. 현재 개발f90839e·Sites64는 그대로이며 반영은 인수 후 기록한다. main/운영 유예·사용자 탭 유지.

## 출판·최종 인계 · 브리핑 답변 품질 · 2026-10-19 KST

- Sites v64 공개 배포 native `succeeded`: https://lawdigest-rebuild-plan.ijaesinii.chatgpt.site/ . 원본 소스 `b6a96ac20de502c15588c680fa1a8fcc5dfa7066`, 문서 사본 기준 `6b50776e339875cbc457216e64f6bc62979f5c8d`, saved version `appgprj_6ac612dd42708191a7a0c8377be64d48~appgver_63a8da8c1980819191854e19939998b5`, deployment `appgdep_6ad5869f34e4819186588b910ef3c211`. audience public을 유지하고 이전v63을 archive로 보존했다. HTML49개·로컬 링크/asset/anchor1,130개·공개 텍스트129개와 실제 비밀값 부재를 확인했다. 문구/상태만 갱신했으므로 기존 레이아웃의 Sites 브라우저 QA를 반복하지 않았다. 사용자 탭을 열거나 이동하지 않았다.
- 소유한 자체 QA 브라우저/API·합성 PG 컨테이너3개/익명 볼륨을 정확ID/이미지/라벨/loopback 확인 후 정리하고 임시4포트 닫힘을 확인했다. 이번 SDD 계획의 ledger·구현/독립 최종 리뷰만 비공개 archive로 보존한 뒤 해당 scratch를 제거했다. 다른 작업 폴더/컨테이너·실제 개발 서비스·백업/평가 증거는 유지했다.
- 코드 게이트는 제품f90839e의3,777개·독립 검토 C0/I0/M0·CI39191407182 성공이며 이후는 문서/출판 receipt 변경이다. Draft PR42는 PR41 기반으로 미병합, main/운영 유예(D013)다. 실제 초기4+별도 구조2의 실패/부분 충족과 다음 의미 품질 과제는 위 기록을 유지한다. 저장소 원본의 이 최종 receipt는 Sites 사본 이후 기록이다.

## 개발 적용 · 브리핑 답변 품질 · 2026-10-19 KST

- [명세](../changes/briefing-answer-quality.md)·[Draft PR42](https://github.com/DigestWorks/IssueDigest/pull/42)(PR41 기반), 제품 `f90839ee5755fb5f366ffdd2f67aba3750d3d05b`. 새 private v5의 독립 귀속/비교/한계 지침·Python/웹 검증/표시와 네 버전 복구를 연결했다. 실제 관측한 비답변의 잘못된 modules·존재하지 않는 인용 ID는 provider 전용 세 strict 출력과 실제 prompt 인용 enum으로 생성 단계에서 제한했다. canonical/API/public 경계와 기존 최종 인용 검사는 유지한다.
- 전체 검사 Python3,169+JS608=3,777개, Ruff/format264파일·mypy115·JS lint/types·빌드·생성 계약 최신 상태, 실패/경고/skip0. 작업별 및 최종 독립 전체 검토 C0/I0/M0·미해결/보류0. 소스 [CI39191407182](https://github.com/DigestWorks/IssueDigest/actions/runs/39191407182)는 정확 f90839e에서 성공했다. v2/v3/v4 bytes·원래 이름/version/정수slot1·완료 checkpoint 재생과 유료 재요청0을 합성 PG로 확인했다.
- 실제 모델 인수는 사용자와 분리한 합성 환경·기검토 공개 텍스트3건에서 수행했다. 초기4회는 완료2(의미 부분 충족)·검증 실패2였으며 분모/실패를 보존했다. 저장된 유료 응답을 추가 호출 없이 읽어 비답변 modules·가공된 UUID 오류를 재현했다. 수정 후 별도 구조 인수2회는 모두 정확 인용으로 완료했다. 총6회·자동 재시도0·입력14,684/출력3,556토큰이며 청구 금액은 검증하지 않았다. 개별 관측 지연3.30~5.78초는 소표본으로 일반화하지 않는다.
- 의미 품질은 여전히 부분 충족이다. 수치 귀속 분류·계획/실적/전망·출처 범위 한계는 개선됐고 없는 여론 비율을 만들지 않았다. 다만 각 수치 문장에 주체 명시가 빠지거나, 핵심 여론 근거가 없는데 answer로 응답하거나, 직접 비교 결론이 첫 요약 대신 접힌 비교 모듈에 남았다. 실제 비답변 분기 성공·전체 질문 품질 완료로 표시하지 않는다. 다음 우선순위는 문장별 귀속·자료 부족 분기·첫 요약의 직접 결론이다.
- 추가 판단: 관측된 오류를 최종 검증 완화 없이 생성 단계에서 막기 위해 Task2와 별도 구조 인수2회를 추가했다. 초기4회 실패를 성공으로 교체하지 않았다. 이 판단이 틀리면 구현/검토 복잡성과 최대2회 단일 API 요청 비용이 추가된다. 각 요청의 기존24,000/출력2,500 한도·월 예산·무제한 재시도 금지는 유지했다. 최종 v5 static10,012+prompt9,440+framing2,048+output2,500=24,000의 보수적 byte 예산과 실제 세 tool schema 크기를 호출 전에 검증한다.
- 자체 브라우저에서 실제 초기4개 상태·추가2개 결과를 확인했다. 390/1440·두 테마·분류/설명·정확 원문 강조·Escape/초점 복귀·재열람/새로고침·가로 넘침을 확인했다. 읽기 POST0·페이지 오류0이며 실제 사용자 로그인/질문을 대신하지 않았다.
- 개인 개발 웹/API/조사 worker를 f90839e로 함께 갱신했다. 활성 run/workflow0 후 정상 종료/기동과 단일 worker 잠금1, 외부 HTTPS·새 웹 파일6개 hash·health/status/공개 읽기200·비회원session401/no-store/noCookie를 확인했다. 새 정적 파일19개·이전 asset82개와 기존 소스는 롤백용으로 보존했다. schema0009·수집기a908083/config/실행기/주기·계정/세션/공개v1·main/운영은 유지했다.
- 서버 밖 사전·직전·사후 full/app 백업과 별도 PG18.6 app 복원을 확인했다. 직전/사후/사후 백업/복원23개 public 테이블의 row hash/count가 모두 같다. 자료 버전15/인용49/검색36/receipt1/공개1·canonical15를 유지했다. 기존 실제 AI 결과는0건이므로 과거 실제 결과 재생 증거로 과장하지 않는다. DBOS registry는 이 행 감사 범위 밖이며 vector/역할까지의 완전 재해복구 검증은 아니다.
- Sites 출판과 이전v63 보존·최종 정리 receipt는 아래 후속 기록에 남긴다. 이번 추가 원문 확보·자동 공개·schema/권한 변경0. 실제 원문/질문/ID/키/접속·백업과 평가 로그는 저장소 밖 비공개 보관한다. 사용자 탭을 열거나 이동하지 않았으며 main/운영 유예(D013)를 유지한다.


## 구현자 인계 · 브리핑 답변 품질 · 2026-10-19 KST

- `feat/briefing-answer-quality`의 새 private v5 독립 지침·정확 byte 예산(static5,109/prompt14,343)·기존 schema alias·private Python/웹/UI 경로와 네 agent/workflow 등록을 구현했다. 한국어 결론·비교·선택 인용의 한계를 표시 claim에 담고 기관 수치/평가 귀속·계획/실적/전망·'이상' 열린 끝을 구분하도록 지시한다. 지침이 실제로 지켜졌다는 의미 품질 판정은 아니다.
- 합성 TDD: v5 생성 미구현·클라이언트 거부·UI 분류 미표시/불완전 결과 미거부·새 요청v4 잔류의 RED를 먼저 확인했다. 관련 agents/domain/worker/API/UI Python1,441개·웹/client/UI JS149개 GREEN, Ruff/format263·mypy115·JS lint/types·diff 검사를 통과했다. 실패/skip0이며 최종 소스 지침 정리 뒤 agents77개도 재확인했다. 전체 gate는 controller가 따로 수행한다.
- 보존: v2/v3 golden을 유지하고 v4 지침/schema/인용 선택 bytes를 기준2ed2bc7 SHA로 고정했다. 실제 전용 합성 PostgreSQL에서 v2/v3/v4/v5 원래 workflow/agent/정수slot1·application_version cohort의 완료/오류 checkpoint를 재생하고 유료 재요청0, 미완료/잘못된 slot·취소/권한·단일 잠금·부모/검색 고정을 확인했다. Python 실제 builder의 고정 합성 JSON→웹 client→표시/정확 원문 열기를 검사했다. generic Claim/API/OpenAPI·public v1/v2/빈 reviews·수집기/예산/세션은 유지했다.
- 다음/경계: 독립 리뷰·전체 gate·검토 공개 자료 최대4회 의미 품질 평가·개인 개발 적용/복원·PR·Sites는 controller 인수 대기다. 구현자는 실제 원문/계정/키/모델/서버·컨테이너·사용자 탭에 접근하거나 외부 게시/배포를 수행하지 않았다. Sites 미반영(이전v63 유지), main/운영 유예다.

## 작업 시작 · 브리핑 답변 품질 · 2026-10-19 KST

- PR41/d0d3fdf 기반 `feat/briefing-answer-quality`·[명세](../changes/briefing-answer-quality.md). 이전 실제 수치 답변의 귀속 분류·비교/한계 설명 부분 충족을 개선한다. 기존v2/v3/v4 생성/복구와 결과·공개 경계를 유지하는 새v5를 구현한다.
- 단일 요청/예산을 유지하고 합성 TDD·독립/전체 검사 뒤 별도 합성 신원/검토 공개 텍스트에서 최대4회 실제 평가한다. 자료의 '이상'·기간 차이로 최종 실패를 확정하지 않으며, 실제 결과가 부족하면 그대로 남긴다. 개인 개발 적용/복원·PR·Sites는 인수 후 기록한다. main/운영 유예·수집기/자료 보존·사용자 탭 유지.

## 개발 적용 · 공식 목록 후보·새 공식 자료 검색 · 2026-10-19 KST

- 변경/검토: [명세](../changes/policy-source-candidates.md)·`feat/policy-source-candidates`·[Draft PR41](https://github.com/DigestWorks/IssueDigest/pull/41)(PR40 기반). 제품93ab7c8, 작업별/보완/전체 독립 검토 C0/I0/M0. 새 HTML metadata의 숨김 조상 누락1건을 TDD로 수정했고 미해결/보류 지적은 없다.
- 구현: 기존 title-only discovery/capture bytes를 유지하는 날짜/발행처 SDK, 기간·이전 관측의 순수 후보 보고서와 private CLI를 추가했다. 현재 전체 목록을 먼저 대조해 범위 밖 날짜 이동을 누락으로 오분류하지 않는다. 관측된 발행처 링크 형태만 HTML parser3으로 지원하며 기존1/2·본문/인용/권리를 보존한다. AI workflow3과 별개이며 schema/API/웹/세션·유료 지침/복구 계약 변경은 없다.
- 실제 확보/내용 검토: 기존 SDK의 목록1+기사3=4 GET, 서로 다른 기사2건. 원래2건 capture는 보존하고 이미 있는 기사는 중복을 피했다. 정확 batch 계약 때문에 새 기사만1회 더 확보했다. 이전 관측 대비 후보10/신규1/동일9/미관측1/metadata변경0이며 전역 신규·주목도·철회로 해석하지 않는다. 목록 날짜와 원문 발행일을 따로 확인했다. 새 공식 텍스트1건의 전체 본문·발행 주체/일자·정확 URL/SHA·공공누리1 조건/사진·외부 저작물 제외·8개 정확 인용을 controller가 검토했다. 기관 평가를 독립 사실로 인증하지 않았다.
- 개발 등록: 기존 provision/check/apply·표시/검색 경로로 신규1, 같은 계획 재실행 신규0/초대0. 기존 초대2개는 유지했다. 기존 앱 계정 read-only로3문항이 새 자료를 검색하고 정확 인용8/모든15canonical을 읽는 것을 확인했다. 자료 버전15/인용49/검색36/편입receipt1/공개브리핑1이다. 이번 자료는 private 검색 추가이며 자동 승인·공개 게시가 아니다. 모델0/사용자 세션 발급0이므로 생성 의미 품질 인수로 부르지 않는다.
- 전체 검사: 최종93ab7c8에서 Python3,035·JS568/28파일=3,603개와 Ruff/format258·mypy114·JS lint/types·SPA build·생성 API 계약 통과, 경고/skip/실패0. [실제 소스 CI39187839563](https://github.com/DigestWorks/IssueDigest/actions/runs/39187839563)도success다. 기존 실제 모델3회에서 남긴 귀속·수치 비교/한계 설명의 부분 충족은 아직 해소하지 않았다.
- 보존/복원: 사전·직전·사후 full/app archive를 서버 밖에 보존했다. 실제23테이블의 기존 모든 행·schema0009·receipt/공개본을 유지했고 사후 app archive를 별도PG18.6에 복원해23테이블 rowhash/count 전체 일치·정확 원문/검색을 확인했다. vector/역할까지의 완전 재해복구는 아니다. 정적웹4cd8f62·API/조사worker b63c7fa의2PID/명령/cwd·collector a908083/source/config/runner/cron은 전후 같다. HTTPS web/login/health/status/공개200, 비회원401/no-store/noCookie와 화면/공개v1 hash도 동일했다.
- 경계/다음: 독립 도구 worktree/venv만 새로 준비했고 앱 재시작·새 cron/권한·OAuth/모델·공개 게시·main 병합은 없다(D013). 실제 원문/개별ID/승인/계정/접속/키·상세 receipt는 private에 보존한다. 다음은 실제 질문의 귀속·수치/한계 설명 개선과 승인 도구 탐색·자료 확대다. [Sites v63](https://lawdigest-rebuild-plan.ijaesinii.chatgpt.site/#plan)의 공개 요약·이전v62 보존·native succeeded를 확인했다.

- 최종 출판/정리: 사본 기준7781216, Site source f1480ae8831c96a77084fb78423d9b38bcd8165c, saved `appgprj_6ac612dd42708191a7a0c8377be64d48~appgver_4348bec585c88191838a5eb352f56495`, deployment `appgdep_6ad57bbad5e08191b77b3314171a85a3`, native succeeded. HTML48개·로컬 링크/asset/anchor1,121개·공개 텍스트118개와 실제 접속/키 비포함을 확인했다. 기존 레이아웃의 문구/기록 변경이며 브라우저 QA를 반복하거나 사용자 탭을 열지 않았다. 자체 합성/복원 컨테이너2개·익명 볼륨을 전체ID/소유label/image/loopback 대조 후 제거하고 두 포트 닫힘을 확인했다. pinned image·서버 밖 백업·PR worktree·실제 개발 앱/수집기를 보존했다. 새 생산 변경 없이 문서만 정리했으며 이후 출판 기록의 원본은 이 저장소다.

## 작업 시작 · 공식 목록 후보 선별·출처 확대 · 2026-10-19 KST

- PR40/e05aac6 기반 `feat/policy-source-candidates`, [명세](../changes/policy-source-candidates.md). 고정 목록1회에서 canonical 후보10개를 확인하고 정확 원본을 private에 보존했다. 날짜/발행처가 있는 목록 후보를 원문 검토와 연결한다.
- 코드·독립/전체 검증·개별 원문/권리 검토·기존 명시 등록/검색·실제 보존/복원·PR·Sites를 단계별로 기록한다. 자동 승인/공개 게시·새 cron/유료 생성·API/worker 변경은 범위 밖이며 main/운영 유예·사용자 탭을 유지한다.

## 개발 적용 · 소비자 브리핑 디자인 · 2026-10-19 KST

- 결과: 선택한 브리핑형을 실제 홈/질문/공개·비공개 읽기/진행/기록/원문에 적용했다. 큰 한국어 산세리프 질문 제목, 정돈된 입력·제출, 여백과 타입 위계, 절제된 녹색·두 테마를 사용한다. 실제 공개 목록/기준일·AI 해석/분류·버전/이용 조건은 보존하며 최근·인기·추천·샘플 결과/미완성 메뉴는 넣지 않았다.
- 소스/검증: 앱355a576, 정적 배포4cd8f62, [Draft PR40](https://github.com/DigestWorks/IssueDigest/pull/40)(PR39 기반). JS568개·lint/types/build/contract·diff 검사는 통과했고 작업별/전체 독립 검토 C0/I0/M0이다. 처음 controller lint는 무시된 임시 브라우저 스크립트까지 검사했으므로 QA 파일만 private 경로로 이동한 뒤 전체 JS 게이트를 다시 통과했다. 제품 lint 설정을 완화하지 않았다.
- 합성/실제:320/390/768/1440·두 테마와 실제 상태/기록/비교/타임라인/분류·초안/원문을 합성 생산 빌드로 검증했다. 별도 익명 headless 브라우저의 실제 HTTPS390/1440은 새 CSS·홈/공개 읽기·출처/버전/정확 강조·닫기/초점·메뉴/44px·질문→로그인 초안·테마 저장을 통과했다. 가로 넘침/페이지 예외/예상 밖 API 오류0, 쓰기/OAuth/모델 호출0·세션 쿠키 미발급이다. 초기 기존 캐시 화면은 새 디자인의 증거에서 제외하고 일반 새로고침과 새 CSS/문구 검사를 추가한 최종 인수로 대체했다.
- 배포/보존: 별도 소스의 정적19파일만 개인 개발 Nginx에 원자 반영하고 이전asset83개·원래root/설정을 보존했다. 첫 즉시 HTTP 확인은 worker 교체 전 응답으로 롤백됐고, reload 완료와 실제 제공 완료를 구분하는 bounded 확인으로 재검증·적용했다. API/조사worker PID·명령/cwd·수집기a908083/source/config/실행기/crontab은 전후 동일하다. DB/공개자료/계정/세션·외부TLS·main/운영은 변경하지 않았다.
- 한계/다음: 실제 Google 로그인·유료 AI 생성·응답 의미 품질 검사는 이번 화면 변경에 포함하지 않는다.200%는 CSS layout 검사이며 보조기기 전체 감사가 아니다. M2 출처 확대·최근 이슈 발견과 M3 귀속/수치/한계 설명·자율 도구 탐색/점진 전달은 후속이다. Sites v62 요약을 공개 갱신했으며 최종 출판 receipt는 아래와 같다. 자체 QA 브라우저를 종료했으며 PR/서버 worktree·롤백 자산은 유지한다.


- 최종 출판: [Sites v62](https://lawdigest-rebuild-plan.ijaesinii.chatgpt.site/#plan) native `succeeded`. source `ffa6e4ae3f82dbbfb104a542639bfe30520f94be`, saved `appgprj_6ac612dd42708191a7a0c8377be64d48~appgver_a0b7c325b39c81919a89673923885aea`, deployment `appgdep_6ad5730ea0608191b2441935f94be68c`. 문서 사본은87a2bd0이며 이후 출판/검증 receipt는 이 저장소 기록을 따른다. 이전v61 보존·HTML47개/로컬 링크·asset·anchor1,112개/공개 텍스트116개의 실제 비밀값 제외를 확인했다. 계획판의 내용/표만 바꿔 새 브라우저 검사를 반복하지 않았고 사용자 탭을 열지 않았다. [제품 소스 CI39185389380](https://github.com/DigestWorks/IssueDigest/actions/runs/39185389380)의 전체 검사·빌드·계약은 성공했다. 계획별 scratch는 private 보관 후 이 계획 폴더만 정리하며 PR/서버 worktree·기존 앱/수집기·정적 롤백 자산은 유지한다.

## 작업 시작 · 소비자 브리핑 디자인 · 2026-10-19 KST

- 사용자 요청: 개발을 이어가되 논의한 쿨한 앱 디자인부터 반영한다. 선택한 브리핑형 모바일 시안과 B2C 인터뷰를 기준으로 큰 질문 입력·정돈된 읽기·절제된 여백/타입·두 테마를 실제 웹에 적용한다.
- 범위/경계: `feat/consumer-briefing-design`, PR39 기반865a4d7·[명세](../changes/consumer-briefing-design.md). 웹 표현만 수정하며 API/DB/모델/워커/수집기·사용자 세션·공개 원문은 유지한다. 실제 최근 이슈 데이터/개인화·저장/알림은 후속이며 가짜 메뉴나 결과를 넣지 않는다.
- 인수/다음: JS 전체·기존 보안/초안/브리핑 회귀·독립 코드/시각 검토 후 정적 웹만 안전 전환한다. 실제 비회원 HTTPS·이전asset/롤백 보존과 PR·Sites를 기록한다. 이 항목은 시작 당시 상태이며 완료 증거는 위 개발 적용 기록을 따른다. main/운영 유예(D013)와 사용자 탭은 유지한다.

## 개발 적용 · 수집본 검토·버전·검색 편입 · 2026-10-18

- 범위/인계: [명세](../changes/policy-collection-intake.md)·M2, 제품 소스b63c7fa·[Draft PR39](https://github.com/DigestWorks/IssueDigest/pull/39)(PR38 기반). 세 작업과 전체 독립 코드 검토는 C0/I0/M0이며 미해결/보류 지적0이다. 정확 소스 전체 `npm run check`는 Python2,829·JS568=3,397개·린트/서식/타입/SPA/API 계약을 통과했다. CI 상태와 Sites 최종 출판은 후속 기록으로 구분한다.
- 실제 적용: 별도 소스/가상환경에 고정한 Python3.13 API·조사 worker를 준비하고, 직전 full/app 백업·활성run/workflow0을 확인했다. 소유자가0009를 명시 적용한 뒤 새 receipt 테이블에만 기존 앱 계정 SELECT를 남겼다. 기존 default privileges가 새 테이블에 INSERT/UPDATE/DELETE까지 자동 부여하는 것을 실제 조회로 발견해 **이 새 테이블에서만** 비조회 권한을 제거하고 앱의 SELECT 성공·나머지7권한 거부를 확인했다. 기존 테이블/default grants·다른 계정은 바꾸지 않았다.
- 안전 갱신: API 접수를 중지하고 활성 작업0을 다시 확인한 뒤 기존 worker를 정상 종료·새 API/worker를 기동했다. 단일 worker 잠금1·활성run/workflow0·새 소스 worktree를 확인했다. 기존 정적 웹·collector a908083의 source/config/runner/crontab·이전 앱 worktree의 hash가 전후 동일하다. OAuth/세션 설정·공개 게시·main/운영은 그대로다.
- 명시 편입: 사전 백업에 포함된 특정 성공 원본을 고정하고, 이전에 전체 검토한 기사의 본문/표제/발행 주체·일자/이용 조건/파서 의미 digest가 같음을 확인했다. 운영자가 새 후보 UUID와 기존 정확 인용을 명시 승인한 check→apply→같은 승인 재실행 결과는 예상 신규1/쓰기0→기준 버전1/receipt1→already_applied/신규0이었다. 최초 추적 기준 버전이며 실제 기사 내용 변경을 관측했다고 부르지 않는다. 수집 HTTP·모델·공개 게시 호출0이다.
- 실제 읽기/보존: 기존 앱 DB 계정의 읽기 전용 조회에서 새 질문 최신 승인본만·구판 fallback 없음·역사 literal 검색/과거 정확 인용·14개 canonical 재검증을 확인했다. 실제 자료14/인용41/검색33/receipt1/공개1이다. 기존 수집기 status는0009에서도 성공 이력3/마지막 성공 있음/stale=false였다. 외부 TLS·home/login/health/status200, 미인증 session/research401·no-store·세션 쿠키 미발급을 확인했다. 실제 사용자 세션을 대신 발급/사용하지 않았다.
- 백업/복원: 사전·직전·사후 full/app archive를 서버 밖 private 저장소에 보존했다. 사후app archive를 별도 소유 PostgreSQL18.6의 빈 DB에 복원해23테이블 전체 row hash/count가 실제 서버와 같고, 적용 전22테이블 원래 행이 전부 남아 있음을 확인했다(정상 사용자 활동의 session last_activity_at만 비교에서 제외). 복원 후에도 최신 질문/역사 인용·14canonical을 재검증했다. 실제 durable7테이블은 전후/복원 모두0행이며 유료 checkpoint 호환성은 합성 복구 검사 증거로 구분한다. 역할/vector 확장 전체를 포함한 재해 복구 검증은 아니다.
- 경계/다음: 고정 기사 한 건의 시간당 확보·검토 편입 기반이며 광범위한 최근 시사 수집·실제 내용 변경 관측·자동 승인/공개 게시·자율 외부 조사·의미/그래프 검색·전체 응답 품질은 미완료다. 다음 M2는 승인 출처 확대와 최근 이슈 발견, M3는 실제 질문의 귀속/수치/한계 품질과 승인 도구 탐색이다. 개별 원문/ID/권리 승인·접속/계정/키/상세 receipt는 공개 기록 밖에 보존한다. Sites 최종 반영 대기, main/운영 유예(D013)와 사용자 탭 유지.

- 최종 인계: [Sites v61](https://lawdigest-rebuild-plan.ijaesinii.chatgpt.site/) 공개 게시가 native `succeeded`다. source `983bd10a90fc4d5c0105621edafe5d505db546d5`, saved `appgprj_6ac612dd42708191a7a0c8377be64d48~appgver_303ad8e1c82881919cb0fe91feefc150`, deployment `appgdep_6ad4eb66aacc81918d9ac89876c258ba`. 사본 기준ce25ede·이전v60 보존·HTML46/로컬 링크·자산·앵커1,103/공개 텍스트114파일의 실제 비밀값 제외를 확인했다. 내용/표만 갱신했으며 새 브라우저 QA·사용자 탭 열기/이동은 하지 않았다. [코드와 인수기록 CI39141908139](https://github.com/DigestWorks/IssueDigest/actions/runs/39141908139)는 성공했다. 이후 변경은 실제 적용·출판 기록뿐이며 제품b63c7fa는 동일하다.
- 정리: 전체ID/소유label/이미지/loopback 포트를 확인한 이번 QA·복원 컨테이너2개/익명 볼륨을 제거하고25460/25461 닫힘을 확인했다. 원본 백업·실제 승인/상세 인수·독립 검토는 private에 보존하며 이번 작업 scratch만 별도 보관 후 정리했다. 실제 개발 API/worker/collector·개발 환경·PR worktree·다른 계획 기록은 유지한다. main/운영은 병합하지 않았다.

## 구현·통합 검사 · 수집본 검토·버전·검색 편입 · 2026-10-18

- 범위: [명세](../changes/policy-collection-intake.md)·M2·`feat/policy-collection-intake`, 제품 소스b63c7fa. 기존 시간당 확보를 유지하고 명시 승인한 특정 성공 원본→원문/인용/표시/검색/receipt의 원자 편입→새 질문의 최신 승인본 선택을 구현했다. 현재 실제 서버 반영과 Sites는 대기이며 main/운영 유예(D013)를 유지한다.
- 검증: 전체 `npm run check`가 Python2,829·JS568=3,397개, Ruff/format253파일·mypy113·JS lint/types·SPA build·API 계약을 통과했다. 경고/skip/실패0. 저장부566개·worker/SDK/parser694개·조회/평가/복구257개의 작업별 회귀와 세 작업의 독립 검토 C0/I0/M0을 확인했다. 전체 변경 독립 검토는 진행 중이다.
- 복원본 인수: 서버 밖 사전 full/app archive의 별도 PostgreSQL18.6 복원에서 기존22테이블 row hash 일치→0009 적용 후 보존→고정된 이미 수집한 원본1건의 명시 check/apply/재실행을 확인했다. 기준 버전1/receipt1이 추가되고 재실행 신규0이었다. 최신 검색 선택의 RED(구판/신판 동시 후보)→GREEN(최신 승인본만)을 확인했고 기존22테이블 원래 행·역사 literal 검색·정확 인용을 보존했다. 검증한 canonical14/인용41/검색33/receipt1/공개1은 **복원본**의 수치다. 새 HTTP/모델 호출0이며 실제 기사 내용 변경 관측으로 부르지 않는다.
- 다음: 최종 독립 검토와 실제 직전 백업 후0009·기존 app receipt SELECT·새 소스의 안전 API/워커 갱신·고정 한 건 편입을 확인한다. 기존 수집기 소스/설정/주기·정적 웹·계정/세션·공개 복사본·과거 브리핑은 보존한다. 실제 권한·적용·사후 백업/복원·PR·Sites는 별도 인수 증거로 기록한다.

## 작업 시작 · 수집본 검토·버전·검색 편입 · 2026-10-18

- 요구/범위: 내부 파이프라인 다음 개발 계속. `feat/policy-collection-intake`, [명세](../changes/policy-collection-intake.md)·M2, PR38 기반9bd61d2에서 시작한다. 시간당 raw 수집기를 유지하고 특정 성공 원본을 검토한 명시 편입·중복 재사용·새 승인 버전·원자 원문/표시/검색/receipt·새 질문의 최신 승인 선택을 연결한다.
- 경계/판단: 첫 추적은 옛 metadata의 동일성을 추정하지 않고 검증된 기준 버전을 만든다. 이후 source fingerprint와 승인 인용 selector/순서가 같아야 기존 snapshot을 재사용하며 인용 선택이 바뀌면 새 승인 버전이다. 과거 인용/브리핑과 generic 역사 검색을 보존한다.
- 현재/검증: OpenSpec root=null과 clean isolated worktree를 확인하고 세 task/API/인수 기준을 정리했다. 구현·실제 적용은 미완료, 기존0008·개발 앱·계정/세션·공개 게시와 collector는 아직 변경하지 않았다. 현재 Sites 반영 대기. 추가 read-only 확인에서 기존 수집기는 원래 수동1회와 수정 후 실제 예약1회가 모두 성공했고0008·자료13/인용37/공개1·활성 조사0을 유지했다. 서버 밖 full/app 백업과 별도 복원본의22테이블 전체 row hash 일치를 확인했다.
- 저장부 중간 인수: 제품5cd29ca의 storage566개(새45개)·Ruff/format/mypy·별도 코드 리뷰 C0/I0/M0을 통과했다. 원자 저장·같은 요청 재실행·변경/동일/되돌림·인용 선택 보존을 확인했다. 실제 데이터의 별도 복원본에서0009를 적용해 기존22테이블 전체 row hash 보존과 새 receipt0을 확인했다. 승인 CLI와 최신 승인 검색은 구현 중이며 실제DB/앱/collector는 그대로다.
- 다음: 저장 transaction→승인 SDK/CLI→최신 승인 검색을 작업별 TDD/독립 검토로 구현하고 전체 검사를 수행한다. 실제 백업/복원·한 건 승인 적용과 기존 app SELECT/안전 재시작 가능 여부는 controller가 확인한다. main/운영 유예(D013)와 사용자 탭을 유지한다.

## 개발 적용 · 정책뉴스 반복 확보·실행 이력 · 2026-10-18

- 범위/브랜치: `feat/policy-collection-journal`, [명세](../changes/policy-collection-journal.md)·M2. 검토한 고정 공식 기사1건의 재확보를 별도 내부 수집기로 연결했다. 첫 실제 확보 성공과 원본/변경 보고서 저장을 확인했고 개인 cron의 시간당 실행을 설치했다. main/운영 공개(D013)는 유예한다. [Draft PR38](https://github.com/DigestWorks/IssueDigest/pull/38)을 PR37 기반으로 생성했다. Sites 최종 반영은 아래 출판 기록으로 구분한다.
- 구현: 제품 소스`a908083`의 명시 poll/status와 PostgreSQL0008의 분리된 두 테이블이 설정·시도·마지막 성공·정확 capture/report bytes와 SHA를 보존한다. 전용 잠금과 running 선행 commit, 최소 간격/횟수 상한, 실패/중단 이력과 불명확 commit 재시도 금지를 연결했다. status는 읽기 전용이며 최신 실패/미완료와 마지막 성공을 구분한다. 새 상태/실패를 보기 위한 사용자 운영 화면은 추가하지 않는다.
- 검증/검토: 최종 `npm run check`는 Python2,727·JS568=3,295개, Ruff/format245파일·mypy109·JS lint/types·SPA build·API 계약을 통과했다. 경고/skip/실패0. storage519·worker/SDK/parser645·최종 storage+worker941의 해당 단계 회귀와 작업별/전체 독립 검토를 기록했다. 통합 검사에서 중복 테스트 파일명을 구분했고, 전체 검토의 정상 poll/status 경합은 스냅샷 후 기본 시각 확보와 실제 두 연결 회귀3RED→3GREEN으로 보완했다. 최종 재검토 C0/I0/M0, 미해결/보류 지적0.
- 실제 인수: 별도 백업 복원DB에서0008 migration→공식 기사1건 확보/정확 원본·보고서·해시·시각→read-only 상태→즉시 재실행 not_due를 확인했다. 실제 개발DB에도 직전 full/app 백업 후 소유자 권한으로0008을 적용했다. 실제 poll1회 성공·stale=false·즉시 재실행 not_due·시도1개 보존·정확 해시/기존 canonical13개를 확인했다. 복원본/실제 서버 각1회 외부 확보였으며 모델 호출0이다.
- 실행 일정/한도: 별도 고정 소스·가상환경의 개인 수집기만 사용한다. cron은 서버 시각 매시17분, 최소 간격3,300초·상태 age 한도7,200초·총 시도720회, 프로세스 timeout120초/종료 유예10초다. 기존 crontab 줄을 보존하고 실행기 smoke는 not_due였다. 첫 예약 tick에서 기본 Python3.10의 import 실패를 관측해 실행기의 shebang을 전용 Python3.13 절대 경로로 고정했다. cron과 같은 최소 HOME/PATH·비로그인 shell에서 exit0/not_due·외부 요청0을 재검증했고 실패 로그를 보존했다. 수정 후 미래 cron의 새 확보 성공은 별도 관측 사항이다. 실패도 시도 한도에 포함하며 자동 초기화/원본 삭제는 없다. 운영자가 상태·용량·한도에 따라 후속 정책을 검토한다.
- 보존/복원: 사전·직전·사후 full/app archive를 서버 밖 private 저장소에 보존했다. 사후app archive를 별도 PostgreSQL18.6에 복원해 schema0008·앱/수집22테이블의 전체 count/payload digest 일치와 canonical13묶음을 확인했다. 변경 전 앱20테이블·자료13/인용37/검색27/공개1은 그대로다. vector 확장을 제외한app archive의 복원이며 역할/vector를 포함한 완전 재해 복구 검증은 아니다.
- 실행 공존: 기존 개인 개발 worktree/실행 소스·API/연구 worker의 PID/command hash·tmux pane을 전후 대조해 유지했고 재시작하지 않았다. 외부 TLS검증·home/login/health/status200을 확인했다. 실제 사용자 세션이나 모델 키를 대신 사용하지 않았다. 기사/collection/attempt ID·원문·DSN·접속 계정·키·상세 receipt는 Git/PR/Sites 밖에 보관한다.
- 기준 판단: age/stale은 실제 마지막 성공 확보 **완료** 시각(finished_at) 기준이다. 요청 시작의collected_at은 정확 capture 안에 별도로 보존한다. 확보 작업 상태와 기사 발행일/내용 최신성은 다르며 두 시각은 확보 소요 시간만큼 차이 난다. 미래 내용 최신성 판단에는 출처/수집 시각을 별도로 사용한다.
- 남은 M2/다음: 고정 기사 재확보를 최신 시사 전면 수집으로 부르지 않는다. 반복 확보 원본의 검토·버전/중복 처리·기존 검색 색인 편입, 승인 출처 확대와 실제 최근 이슈 발견은 후속이다. 새 수집본은 EvidenceBundle/브리핑/공개 게시로 자동 승격하지 않는다. M3의 주장 귀속·수치 비교/한계 설명·승인 도구 탐색·점진 전달도 남아 있다. 자체 QA/복원 컨테이너2개와 익명 볼륨은 전체ID/소유label/loopback 포트 대조 후 정리하고 두 포트 닫힘을 확인했다. pinned image·백업/상세 검토·PR worktree·실제 앱/수집기는 보존했다. 작업별 scratch는 비공개 보관 후 해당 계획 폴더만 정리했다. [Sites v60](https://lawdigest-rebuild-plan.ijaesinii.chatgpt.site/#plan) 공개 게시 `succeeded`. M2 실행 상태·다음 단계·PR38과 이전v59를 반영했다.

- 최종 출판: Sites source `1518f4d82e915e09a3006885b89c8442dc0359b6`, saved `appgprj_6ac612dd42708191a7a0c8377be64d48~appgver_ea90e82dc8e08191b7b8a7eefae29377`, deployment `appgdep_6ad4c62e6e588191bbe0e31328d1d846`. 문서 사본 기준f217291·HTML45개/로컬 링크·asset·anchor1,094개/공개 텍스트449개의 실제 비밀값 제외를 확인했다. 내용/표만 바꿨으며 새 브라우저 QA는 수행하지 않았고 사용자 탭은 열거나 이동하지 않았다. 자동 동기화는 없다. [개발 적용 기록 CI39130426786](https://github.com/DigestWorks/IssueDigest/actions/runs/39130426786) 성공을 확인했다. [후속 인수 기록 CI39130580642](https://github.com/DigestWorks/IssueDigest/actions/runs/39130580642)도 성공했다. 이후 변경은 개인 수집기 실행 환경 보완과 출판/검증 기록이며 제품 소스는a908083 그대로다.

## 구현·검증 · 공식 자료 변경 감지·마일스톤 · 2026-10-18

- 요구/브랜치: 내부 AI 파이프라인 개발 계속·진척 공유 요청. `feat/policy-change-detection`, [변경 명세](../changes/policy-change-detection.md)·[Draft PR37](https://github.com/DigestWorks/IssueDigest/pull/37). 기존 개발 제품1c0c5ed·PR36을 보존하고 이전 계획판v58은 기록으로 남긴다.
- 구현: 소스a27a001의 순수 비교 SDK와 `issuedigest-policy compare`가 정확한 이전/현재 capture를 기존 parser로 검증한 뒤 본문·제목·발행 주체/일자·이용 조건·파서 프로필을 비교한다. 정확 artifact SHA/시각·필드별 변경·의미 fingerprint를 private 보고서에 기록하고 stdout은 집계만 낸다. 관측되지 않은 기사를 삭제/철회로 판단하지 않으며 두 비교본 밖의 전역 신규/최신성·사실 여부를 추론하지 않는다. 잘못된 조건/모호한 시각/입력·출력 권한은 고정 오류로 종료한다.
- 검증: 새74회귀의 RED73실패→GREEN74, 기존 parser/capture/import 포함364개 통과. controller의 실제 전용 합성 PostgreSQL18.6 전체 `npm run check`는 Python2,646·JS568=3,214개와 Ruff/format·mypy105·JS lint/types·SPA build·생성 계약을 통과했다. 경고/skip/실패0. Task1·전체 변경 독립 검토 C0/I0/M0, 보류/미해결 지적 없음. 실제 모델 호출·자료 변경·브라우저 검증은 하지 않았으며 앱 동작/화면은 변경하지 않았다.
- 계획표: [M1~M6](implementation-plan.md#마일스톤)에 목표·완료 기준·현재 상태·다음 검증을 정리했다. 저장소가 원본이고 작업할 때 Sites를 함께 수동 갱신한다. 자동 동기화·무인 정기 보고는 없다. 완료율을 임의 백분율로 만들지 않는다.
- 정리: 소유 label·전체 ID·loopback25456을 확인한 자체 합성 PostgreSQL 컨테이너/익명 볼륨을 제거하고 포트 닫힘을 확인했다. 제품 소스 이후 변경은 문서뿐이며 실제 앱·서버·DB·키·사용자 브라우저는 보존했다.
- 적용 경계: 이번은 내부 도구의 코드 구현이다. 정기 수집/실패·최신성 운영·자동 등록·질문 중 자율 탐색·서비스 출시 완료가 아니다. 앱 실행 경로 변경이 없어 개인 개발 API/worker 재시작·실제 DB 작업을 하지 않는다. main/운영 유예를 유지한다.
- 다음/Sites: [Sites v59](https://lawdigest-rebuild-plan.ijaesinii.chatgpt.site/#plan) 공개 게시 `succeeded`, 마일스톤/세부 작업/검증 기록·Draft PR37 연결·v58 보존을 확인했다. 원본 사본40c6548, Site source ec39c92414bb6663c769f17966592010f1c0b32f, saved `appgprj_6ac612dd42708191a7a0c8377be64d48~appgver_058e8da0f06081918907dbcf90b403c5`, deployment `appgdep_6ad4b5ee8aa08191b0de18bd84c6693c`. HTML44개/로컬 링크·asset·anchor1,085/공개 텍스트109개 비밀값 패턴 검사를 통과했고 사용자 탭은 열거나 이동하지 않았다. 자동 동기화는 없다. 다음은 반복 수집과 실패/최신성 기록, 승인 탐색 도구의 실행 연결이다.

## 개발 적용 · 한국어 근거 검색·귀속/수치 지침 · D022 · 2026-10-18

- 작업/범위: `feat/korean-evidence-quality`, [명세](../changes/korean-evidence-quality.md)·[D022](decisions.md)·[Draft PR36](https://github.com/DigestWorks/IssueDigest/pull/36). 제품 소스 `1c0c5ed`를 개인 개발 HTTPS에 반영했다. main/운영 공개는 유예한다.
- 검색: 원형·단위 보존, 알려진 조사/명시 공백 대응, 문서별 후보 균형과 주제 중복 가산 방지를 구현했다. 내부 read-only 평가의 실제13자료/고정34문항·동일 job/corpus fingerprint에서 positive30의 Hit@1·family Recall@5·필수 가족 모두 발견은13/30→28/30, negative4의 no-match는2/4→2/4였다. 남은 미발견2·오탐2를 분모에 유지했다. 작은 저장 문자 검색 표본이며 정답률·인용 지지·일반화된 품질이 아니다. 원래20문항은 미실행이다.
- v4/호환: 새 질문만v4 지침/agent/workflow를 사용하고 v2/v3의 실제 지침·schema·prompt bytes·유료 namespace/정수slot1·원래 ID/application_version 재생을 보존한다. 단일worker·불명확 호출 재시도 금지·취소/현재 권한·세 분류와 정확 SupportReview·공개v1/v2/빈 reviews·Claim/default·canonical hash·OpenAPI·schema·세션·예산을 유지했다. 새 디버그/자료 관리 화면은 없다.
- 전체 검증: 정확 소스 `1c0c5ed`에서 Python2,572개·JS568개/28파일=3,140개, Ruff235/format·mypy104·JS lint/types·SPA build·생성 계약 통과, 경고/skip/실패0. 독립 작업별/전체 검토와 최종 보완 재검토 C0/I0/M0. 수량 단위·원형 순서와 잘못된 raw version의 검증 예외를 회귀로 보완했다. 합성 모델 테스트의 Python3.13 이벤트 루프 경고는 명시 test-only Runner 소유/종료로 해결했고 필터/production/dependency 변경은 없다.
- 실제 모델: 실제 사용자와 분리한 합성 신원·검토한 공개 텍스트2건에서 고정 gpt-5.4-mini Responses3회, 재시도0·입력4,744/출력849토큰으로 확인했다. 두 수치 질문의6문장은 선택 원문의 수치를 보존하고 목표/실적/전망·예산안의 예정 성격을 바꾸지 않았다. 하지만 모두 content/supported였고 기관 귀속 분류의 실제 사례는 관측하지 못했다. 실적 문장의 발표 주체 명시와 비교 결론·질문에서 요구한 한계 설명은 불충분해 두 사례를 부분 충족으로 남긴다. 세 번째는 없는 전국 찬성률/인지도를 만들지 않고 제공 근거 부족으로 종료했다. 호출 성공을 의미 품질 통과로 바꾸지 않으며 청구액/독립 사실 검증도 아니다.
- native UI: 자체 headless 브라우저에서320/390/1440×두 테마6조합,44px 조작·분류 설명·정확 원문/강조·Escape/초점·새로고침/기록 재열람·비교 목록·자료 부족 화면을 확인했다. 접수 전 결과 없음·접수/취소 상태를 확인했고 실제 생성 중 별도 화면은 완료가 빨라 확보하지 못했다. 읽기/재열람 추가POST0·pageerror0. 모바일 어두운/PC 밝은 화면을 직접 확인했다. 사용자 탭은 열거나 이동하지 않았다.
- 개발 적용/보존: 활성run/workflow0 확인 뒤 이전 작업을 정리하고 웹/API/worker·개인 Nginx를 갱신했다. 정적19파일·이전asset68개 유지, 외부 TLS·빌드 asset6개 일치·home/login/health/status200·미인증session/research401/no-store를 확인했다. worker/pane 정상·worker잠금1개. 실제 외부 비회원 브리핑/원문도 POST0/pageerror0으로 읽었다. 브라우저 console1건은 의도된 익명 session401 응답이며 별도 앱 예외가 아니다.
- 백업/복원: 사전·직전·사후 full/app archive를 서버 밖에 보존하고 별도 소유 PostgreSQL18.6에 사후app archive를 복원했다. schema0007·canonical 자료13/인용37/검색27/공개1·기존 공개v1 byte hash와 계정/세션 포함 앱21테이블 전체 payload 일치를 확인했다. DBOS registry metadata는 별도다. 실제 사용자 세션은 사용/대신 발급하지 않았고 vector/역할을 포함한 완전 재해 복구 검증은 아니다.
- 남은 품질/다음 행동: 한국어 오탐·미발견, 발표 주체 귀속·수치 비교/한계 설명을 고정 회귀와 별도 실제 평가로 개선한다. 생산 규모 지연·일반화된 정치 이슈 품질·의미 검색/자율 외부 탐색·개인 저장/추천/알림은 미완료다. [Sites v58](https://lawdigest-rebuild-plan.ijaesinii.chatgpt.site/) 공개 게시 완료이며 실제 원문·개별 ID·질문/gold·계정·접속·키·상세 receipt는 저장소 밖에 보존한다.


- 최종 출판/정리: Sites v58 native `succeeded`, source `8987e058d15f9b05610a99b715e65007ec34d22d`, saved `appgprj_6ac612dd42708191a7a0c8377be64d48~appgver_23f77f0041488191bcd0ec6984d8c818`, deployment `appgdep_6ad4ac529c0481919376e64f819dd391`. 사본 기준b59f910·이전v57 보존·HTML43/로컬 링크·asset·anchor1,076/공개 텍스트110의 실제 비밀값 제외를 확인했다. 보관판의 상대 링크를 해당 경로에 맞게 고친 후 검사를 통과했다. 제품 CI [39122572945](https://github.com/DigestWorks/IssueDigest/actions/runs/39122572945)·인수 기록 CI [39122899429](https://github.com/DigestWorks/IssueDigest/actions/runs/39122899429) 성공. 자체 headless 브라우저·합성 API·검증/복원 컨테이너4개/익명 볼륨을 전체ID/소유label/loopback 포트 대조 후 종료했고5개 포트 닫힘을 확인했다. pinned image·개인 백업/검증 기록·PR worktree·실제 개발 앱/worker는 보존했다.

## 개발 적용 · 근거 탐색·AI 평가·브리핑 디자인 · 2026-10-18

- 작업/관련 요구: R2/R3/R4/R6·D021, `feat/evidence-exploration`, [명세](../changes/evidence-exploration.md), [Draft PR35](https://github.com/DigestWorks/IssueDigest/pull/35). main/운영 유예(D013)를 유지하며 개인 개발 HTTPS만 갱신했다.
- 화면: 중립색·작은 녹색 강조·한국어 산세리프와 읽기 위계로 홈/로그인/공개·비공개 브리핑/기록/원문을 정리했다. 요약→필요한 비교·변화·근거→후속 질문 순서와 헤더 아이콘·비회원 초안/로그인·기존 세션·권한/취소를 유지한다. 가상 인기·수동 자료 관리·디버그 메뉴는 추가하지 않았다.
- 공식 확보: 새 SDK의 고정 목록에서 후보10건을 확인하고 정확2기사만 확보했다. 정확한 텍스트 이용 조건을 확인한1건만 운영자 job/인용 검토·기존 등록/표시/색인 경로로 추가했으며, 허용 조건이 없는 나머지1건은 제외했다. 현행 plain-span 발행처를 좁은 파서version2로 지원하고 과거profile1/hash는 보존했다. 수집/준비는 명시 도구이며 질문 시 전체 웹 탐색·정기 수집·자동 공개 게시가 아니다.
- AI/복구: 새 private v3는 inference/AI 해석을 유지하며 각 문장에 자료에 기록됨·출처의 주장·확인하기 어려움과 짧은 설명을 기록한다. 선택 인용에 대한 자동 평가이고 독립 사실 검증이 아니다. 기존v1/v2·공개v1과 과거 결과를 보존한다. 원래 이름/기록 application_version의 DBOS cohort와 정확한 정수slot1의 완료 모델 checkpoint만 재생하고, 완료가 불명확한 유료 요청은 재호출하지 않는다. 단일worker 잠금·잠금 소유 상실·과거v2 중단/재생을 합성 PostgreSQL/프로세스 종료로 검증했다.
- 전체 검증: 제품 소스 `9f3086b`에서 Python2,404개·JS535개/28파일, Ruff224/format·mypy101·JS lint/types·생산 SPA·계약 검사 통과. skip/warning0. [제품 소스 CI 성공](https://github.com/DigestWorks/IssueDigest/actions/runs/39115708245). 작업별 독립 검토와 유료 checkpoint slot 보완 재검토 승인, 통합 검토의 운영자 사용 문서 Minor1을 보완한 `532dc71`도 재검토해 최종 Critical/Important/Minor0을 확인했다.
- 실제 모델/UI: 실제 사용자와 분리한 소유DB·합성 신원·검토한 공개 텍스트에서 gpt-5.4-mini Responses를1회 실행했다(입력1,117/출력646토큰·재시도0·청구액 조회 아님). 요약/비교/근거와5문장·정확5개 평가를 확인했다. 이 응답은 자료에 기록됨3/확인하기 어려움2였고 출처의 주장 분류의 실제 모델 사례는 관측하지 않았다. 320/390/1440×밝은/어두운 테마6조합의 가로 넘침0·44px 조작·분류 펼침 설명·정확 인용·Escape/초점·새로고침·기록 재열람·추가POST0/pageerror0을 확인했다. 요청 전 결과 없음·접수/취소 상태를 확인했으며 실제 생성 중 단계의 별도 스크린샷은 완료가 빨라 확보하지 않았다.
- 품질 한계: 한 질문의 표본으로 전체 정치 이슈·사실 검증 성능을 주장하지 않는다. 수치의 목표/실적/전망은 구분했지만 전망 상단과 목표의 산술 차이를 명시 설명하지 않았다. 자료에 기록된 내용과 당사자의 주장을 구분하는 보정·수치 비교 완결성·자료 부족·상충 주장 품질은 다음 실제 질문 평가에 포함한다. 현재 검증된 완료 결과를 표시하며 부분 AI 결과 전달·질문 시 자율 외부 탐색은 후속이다.
- 개인 개발 반영: 활성run/workflow0을 확인하고 API 접수를 중지·기존 작업을 정리한 뒤 웹/API/워커를 제품 소스 `9f3086b`로 반영했다. 정적19파일/source map0·이전asset64개 유지, TLS검증·현재asset6개 빌드 일치·home/login/health/status200·미인증session/research401/no-store를 확인했다. 소유worker1개/잠금1개이며 schema0007·기존 실제 계정/세션·공개v1은 보존했다. 현재 자료13/인용37/검색27/공개1이며 등록 반복 신규0·초대 신규0·기존34테이블payload 집합 보존을 확인했다.
- 백업/복원: 적용 직전·직후 서버 외부 full/app archive를 보존하고, 별도 소유 PostgreSQL18.6에 사후app archive를 복원해13개 canonical 자료·인용/검색 건수·schema0007·기존 공개v1 일치를 확인했다. 실제 사용자 세션을 대신 발급/사용하지 않았다. vector 확장·전체 역할을 포함한 완전 운영 재해 복구를 검증했다는 뜻은 아니다.
- 인계: PR35는 Draft이며 main/운영 병합은 하지 않았다. [Sites v57](https://lawdigest-rebuild-plan.ijaesinii.chatgpt.site/)을 이전v56 보존 후 공개 게시했다. 실제 키·계정·개별 자료ID·원문·상세 운영 receipt는 비공개 검증 위치에 보존한다. 사용자 브라우저 탭을 열거나 이동하지 않았다.


- Sites 인계: native publish `succeeded`, source `3dc6edd85b594580a9911007ce549ab1be7c9a59`, saved `appgprj_6ac612dd42708191a7a0c8377be64d48~appgver_0755069e87a48191a85c6631f0d071f4`, deployment `appgdep_6ad494d1356081919d7199272eca7024`. 사본 기준5bc059c·HTML42/로컬 링크·anchor1,067/공개 텍스트108파일의 실제 비밀값·계정·개별ID·원문 제외를 확인했다. 사이트의 기존 공개 범위를 유지하고 사용자 탭은 열지 않았다.
- 문서 검사/정리: 운영자 문서 Python 예제의 들여쓰기가 CI 서식 검사에 걸려 formatter로 보완했다(`c204a04`). 전체 Python lint/format224파일 재검사 통과, 런타임 코드는9f3086b와 동일하다. 자체 합성 브라우저와 QA 서버2그룹을 종료하고 전체ID/소유 label/이미지/loopback 포트를 대조한 자체 QA·복원 컨테이너4개/익명 볼륨을 제거했다. 서버 개인 개발 앱/worker·PR worktree·개인 백업/검증 기록은 유지한다.

## 구현·합성 검사 · 공식 근거·AI 분류 Task3 · 2026-10-16

- 작업/관련 요구: R2/R3/R4/R6·D021, `feat/evidence-exploration`, [변경 명세](../changes/evidence-exploration.md). Task1의 화면 구성을 유지하고 Task2의 명시 수집/준비 경로를 소비한다.
- 구현: 새 private research-v3 typed category/300자 설명을 기존 SupportReview에 정확1개/claim로 기록하고 접근 가능한 작은 펼침 도움말로 연결했다. inference·AI 해석 label과 선택 인용의 AI 평가임을 유지한다. 기존 Claim/default·v1/v2 canonical 결과·공개v1 hash·D020 공개 경계를 바꾸지 않았다.
- 복구: 공용 DBOS3.2 API로 원래 이름/기록 application_version cohort를 회복한 뒤 새 queued 요청만v3로 시작한다. 실제 동결v2 worker 모델 checkpoint 뒤 SIGKILL→새 worker의 구 결과 재생·새v3 실행, 모델 요청 안 SIGKILL→재호출 없음·실패/예약 유지, session advisory lock→중복 기동 거부/첫 요청 보존을 합성 PostgreSQL로 확인했다. 최초v2 업그레이드는 중지된 기존 worker·활성 작업 정리가 필요하다.
- 검증/미검증: 관련 Python/전용 PostgreSQL852개 통과(기존 third-party event-loop deprecation warning1개), 마지막 잠금 연결 상실 보완 후 worker/recovery23개 통과. JS 전체535개/28파일·Ruff/format·mypy101소스·JS lint/types·생산 SPA·계약 검사를 통과했다. 합성 분류·인용/마이크로초 UTC·legacy/public hash·DBOS 복구/중복 기동/취소/권한·기존 원문/로그인/race 회귀를 확인했다. 최종 명령/결과·변경 파일은 `.superpowers/sdd/evidence-exploration/task-3-report.md`에 인계한다. 전체 결합 검사·독립 UI·실제 모델 품질은 controller 후속이다.
- 실제 적용/남은 입력: active 개발 자료는 기존12건이다. Task2 실제 기사 추가13/37/27 확인은 격리 복원본 검증까지이며 active 등록/새 API·worker·정적 웹 반영은 대기다. 기존 계정/세션·공개1건은 보존하며 실제 private ID/원문·접속/키는 공개 기록에 남기지 않는다.
- 다음 행동/Sites: controller가 전체 검사·독립 인수·백업/복원·명시 자료 추가·개인 개발 반영 후 Draft PR·Sites를 갱신한다. 현재 Sites 반영 대기, main/운영 유예 유지.


## 구현·합성 검사 · 브리핑 디자인 Task1 · 2026-10-16

- 요구사항/담당: [근거 탐색 계획 Task1](../changes/evidence-exploration.md), `feat/evidence-exploration`. 홈·로그인·공개/비공개 브리핑·공유 기록·원문 창의 앱 색상/타이포/간격을 통합했다. 한국어 serif fallback과 중복 시각 제목을 제거하고 기존 로고·테마/계정 아이콘·44px/초점·정확 인용·native details/dialog 계약을 유지한다. 새 폰트/의존성이나 API/데이터 변경은 없다.
- 읽기 순서: 완료 브리핑 뒤에 후속 질문을 배치했다. DOM/키보드 읽기 순서 검사 RED→GREEN을 확인했고 기존 질문 복원·공개 고정 버전/철회·권한/원문/취소 회귀를 유지했다. 과거 경로 전환 검사의 옛 `질문 ·` 표시문구 의존만 제목 역할 조회로 바꾸었다.
- 검증/인계: JS 전체 린트·타입·503개/26파일 테스트·생산 SPA 빌드·OpenAPI/TS 계약 검사를 통과했다. 구현자의 별도 headless 브라우저에서 생산 SPA·합성 HTTP로320/390/1440·밝은/어두운 원문 창, 가로 넘침 없음, 표시 버튼 최소44px, 정확 강조·Escape/초점 복원을 확인했다. 컨트롤러의 실제 자료를 사용하는 독립 인수는 대기다. 실제 계정/자료/서버·모델·운영/main을 변경하지 않았다.
- 다음 행동/Sites: Task2·Task3 및 독립 인수 후 개인 개발 반영·Draft PR·Sites 요약을 컨트롤러가 진행한다. 이 Task1 단계의 개발 반영·Sites 갱신은 대기다.

## 완료 작업 · 명시 공개 브리핑 읽기 · 2026-10-16

- 요구사항/담당: [D020](decisions.md)·[공개 브리핑 명세](../changes/public-briefings.md), `feat/public-briefings`, [Draft PR34](https://github.com/DigestWorks/IssueDigest/pull/34). 제품 소스 `b82624de2dc342733ced8ad9d8757e9b93d68154`. 기존 비공개 자료·질문·실행·계정/세션은 공개로 전환하지 않는다.
- 구현: 명시한 전체 공개 계획·개별 이용 조건 검토 hash로 독립 게시 복사본을 만든다. 공개 namespace·출처 표시·순차 불변 버전·동일 계획 재사용·철회와 최신판의 과거 버전 자동 재노출 방지를 연결했다. 익명 목록/최신/고정 버전 GET은 private 저장소·세션·모델/DBOS·비용을 호출하거나 생성하지 않는다. 실제 게시 목록에서 비회원 읽기·기존 Canvas/정확 인용 원문·고정 버전 링크·새 버전 안내·일반 홈 질문 초안으로 이어진다.
- 재확인: 인용 선택(열린 원문 내부 선택 포함)·재진입·focus/pageshow/visible 복귀에 같은 공개 버전을 확인한다.404는 본문과 열린 원문을 정리하고 일시 실패는 재시도로 구분한다. 늦은 경로/버전·닫힌 원문의 응답을 무시한다. 이미 전달한 데이터의 원격 삭제는 보장하지 않는다. 질문은 직접 입력/공개 표제만 홈으로 전달하며 URL·public/private 부모 실행·자동 생성 요청을 만들지 않는다.
- 최종 검사: [제품 소스 전체 CI](https://github.com/DigestWorks/IssueDigest/actions/runs/38877209920) 성공. 실제 전용 PostgreSQL에서 Python2,203개, JS502개/26파일·Python/JS 린트·타입·생산 SPA·OpenAPI/TS 계약 검사 통과. 작업별·전체 독립 검토와 수정 재검토 후 미해결 지적0. 기존 회원의 빈/내용 있는 초안이 새 질문을 덮던 문제를 RED2→수정·회귀로 해결했다. 동시 게시 중 게시 전 확인이 잘못 손상을 보고하던 문제도 실제 PG 교차 실행 RED2→읽기 전용 일관된 snapshot으로 해결했다.
- 독립 인수: 실제 앱 DB 백업을 별도 소유 검증 DB에 복원해0006→0007 적용과 기존31테이블 payload 동일성을 확인했다. 공개 HTTP는 공개 테이블만 조회·no-store/X-Request-ID/Set-Cookie 없음, private401·잘못된 버전422·없는 자료404·게시 메서드405·모델0을 확인했다. 실제 복원 자료의390/1440·밝은/어두운 화면·정확 강조·Escape/초점·v1/v2 보존/철회와 빈 목록, 질문→홈→로그인/no-URL/no-POST를 확인했다. 검증에 실제 회원 세션을 대신 만들지 않았으며 새 유료 모델 호출은 없다.
- 개발 반영: [개발 앱](https://dev.issuedigest.projects.ai.kr/)의 개인 worktree 웹/API를 위 소스로 갱신했다. 읽기 전용 사전 full/app 백업 후 소유자로0007을 명시 적용하고 기존 앱 계정에는 새 두 테이블 SELECT만 부여했다. 문서별 공공누리 제1유형 텍스트 이용 조건·전체 내용·정확 본문 SHA·출처·사진/외부 저작물 제외를 확인한 기존 공식 자료1건만 별도 게시했다. 전체 계획 hash·반복 결과·앱 계정 읽기를 검증했고 내부 자료12/인용33/검색단위21을 보존했다. 이전 생성 워커는 동일 PID로 유지했다. 시스템 서비스·공용 checkout·main/운영은 바꾸지 않았다.
- 외부 확인/복원: 엄격한 HTTPS 검증으로 화면/login/health/status200·비회원 session/research401/no-store·현재 정적 자산 일치·이전 자산/로고 보존을 확인했다. 공개3GET의 최신==고정v1·1건·no-store/request-id/no-cookie와 두 직접 웹 경로를 확인했다. 실제 개발 도메인390/1440에서 공개 읽기·정확 인용·초점 복원·질문 초안→로그인/자동POST0을 재확인했다. 반영 후 full/app 백업을 별도 빈 DB에 다시 복원해0007·공개 결과 동일성·기존31테이블 payload 보존을 확인했다.
- 경계/후속: 게시 한 건은 자료의 기준일을 표시하며 최신 이슈나 현재 정책 확정으로 포장하지 않는다. 첫 허용 출처 외의 권리와 전체 내용을 일괄 허용하지 않는다. 외부 탐색·최근 이슈·개인화·개인 소유/저장·알림·사용자 공유·전체 한국어 조사 품질과 공개 가입/AI 이용 정책은 미완료다. 현재 공유 검증 이력을 개인 보관함으로 표시하지 않는다. main/운영 게시는 D013에 따라 유예한다.
- Sites: [v56 계획판](https://lawdigest-rebuild-plan.ijaesinii.chatgpt.site/) public/native succeeded. source `e6afd16aee24cc766ae2db5d446888b4e1cfbff5`, saved `appgprj_6ac612dd42708191a7a0c8377be64d48~appgver_5a218e0610f08191a87d719d48316fec`, deployment `appgdep_6ad1e8a683148191932f89feedcad729`. 구현 문서 사본5fd464b·이전v55 보관·HTML41/내부 링크·자산·앵커1,058개/공개 텍스트106파일의 실제 비밀값 제외를 확인했다. 공개 페이지는 질문과 공개 읽기·독립 게시1건·현재 한계/후속으로 정리했고 이전 기록을 보존했다. 사용자 탭을 열거나 이동하지 않았다.

## 완료 작업 · 질문 전용 브리핑 · 2026-10-16

- 요구사항: [D019](decisions.md)·[작업 명세](../changes/question-driven-briefing.md). 수동 자료 선택·카탈로그·클라이언트 추천·레거시 자료 관리/검색 화면·자료 범위 선택기·준비 중 안내·자동 중복 원문 블록을 제거했다. 사용자 질문 → 서버의 관련 근거 검색/고정 → AI 브리핑 → 정확 인용 원문을 운영까지 이어갈 경로로 구현했다.
- 구현: 엄격한 질문/부모/요청 ID 계약, queued의 빈 근거·완료의 최대5개 근거, v2 agent/workflow와 원자적 근거 고정·재시작 재사용을 연결했다. 근거가 없으면 모델 호출 없이 부족함을 설명한다. 로그인 초안·단계/취소·후속·저장 결과를 유지하며 현재 권한 상실은 Canvas·제목·원문·초안을 정리한다. 일시 실패·이전 맥락의 늦은 오류를 구분하고 기록 재조회가 복구되도록 했다.
- 호환성: 과거 v1의 seed 이외 추가 근거는 기존 요청 해시·현재 권한·정확 원문 연결/본문을 재검증해 읽기에서 해석한다. 저장 행·결과·이벤트·시각을 바꾸지 않고 추가 인용을 연다. v2 불일치와 손상된 원문은 거부한다.
- 검증: 제품 소스 `9a5feb1c3ee76a828a2cf83fb56ce4fdee50a0f4`의 [전체 CI](https://github.com/DigestWorks/IssueDigest/actions/runs/38868808570) 성공. 실제 전용 PostgreSQL에서 Python2,125개·웹452개/24파일, Python/JS 린트·타입·빌드·OpenAPI 계약 검사 통과. 작업/전체 독립 검토와 보완 재검토를 마쳤다. 실제 HTTP/DBOS/PG·합성 신원 브라우저에서 질문 전용 제출·진행·후속·무근거0토큰·정확 인용·저장 재열람·390/1440·밝은/어두운 화면, 권한 상실 뒤 전체 표시 정리와 권한 복구 후 기록 재조회, 과거 추가 근거 원문 열기를 확인했다.
- 실제 AI: 공개 정부 자료의 읽기 전용 복사본과 로컬 합성 신원으로 Responses/gpt-5.4-mini1회(입력730/출력237토큰)를 제한 검증했다. 서버 검색→요약/근거 모듈→정확 인용·저장/동일 요청 재열람과 무근거 종료를 확인했다. 이후 브라우저 생성 검사는 합성 모델이며 실제 사용자 세션·공동 DB 쓰기·전체 품질 평가를 대신하지 않는다.
- 개발 적용: [개발 앱](https://dev.issuedigest.projects.ai.kr/)에 위 제품 소스의 웹/API/v2 워커를 함께 반영했다. 이전 활성run/workflow0 확인 후 접수를 멈추고 안전하게 전환했다. 정적17파일·이전48자산 보존, HTTPS·화면/login/health/status200·미인증session/research401/no-store·현재6자산 hash/로고 일치를 확인했다. DB 스키마0006·자료12/인용33/색인12/검색21단위·계정/초대를 변경하지 않았다. 시스템 서비스·공용 checkout·main/운영은 변경하지 않았다.
- 경계/다음: 현재는 연결된 저장 색인의 제한된 문자 검색이다. 최신 외부 수집/탐색·의미 검색·공개 브리핑·개인 소유·추천·알림·공유는 활성 작업 목록의 후속이다. 현재 공유 검증 이력을 개인 보관함이나 공개 자료로 표시하지 않는다. [Draft PR33](https://github.com/DigestWorks/IssueDigest/pull/33)에 변경을 보존하며 main/운영 게시는 유예한다.
- 외부 브라우저: 배포된 개발 주소의390/1440 화면에서 자료 선택/준비 중 안내 부재·가로 넘침0·테마 전환·질문→로그인과 pageerror0을 확인했다. 최초 QA 탐색의 networkidle 대기는 종료되지 않아 DOM 준비와 실제 화면/행동 기준으로 재확인했다. 기대된 비회원401과 JavaScript 예외는 구분한다.
- Sites: [v55 계획판](https://lawdigest-rebuild-plan.ijaesinii.chatgpt.site/) public/native succeeded. source `80db41f95d7a5df1722c5ec0e6e85ad334805dea`, saved `appgprj_6ac612dd42708191a7a0c8377be64d48~appgver_b558693665d08191b35e27e5ffc7ff00`, deployment `appgdep_6ad1d72fbd30819187d9c742b17c8e16`. 문서 사본3946250·이전v54 보관·HTML40/내부 링크·자산·앵커1049개/공개 텍스트104파일의 실제 비밀값 제외를 확인했다. 사용자의 브라우저 탭을 열거나 이동하지 않았다.

## 이전 작업 · B2C 화면·활성 계획·로그인 유지 · 2026-10-16

- 요청과 수용 기준: [D018](decisions.md)·[작업 명세](../changes/b2c-cleanup-persistent-login.md). 질문 중심 B2C 브리핑을 기준으로 기본 자료 메뉴·공동 작업/역할 배지·법안 전용 요약 행동과 옛 활성 계획을 정리했다. 근거 검색·선택·원문/정확 인용·생성·재열람은 유지하며 공유 검증 이력을 개인 보관함으로 표시하지 않는다.
- 구현: 서버 세션 최대14일·미사용7일과 새0006 마이그레이션9ad2cca/d6d05f3, 헤더 아이콘·화면·활성 문서 재편befb97f. 기존 세션 만료일을 연장하지 않으며 보안 쿠키·해시 저장·현재 권한·교체/로그아웃 폐기를 유지한다.
- 검증: 컨트롤러 실제 전용 PostgreSQL2090개·JS493개, Python/JS 린트·타입·빌드·계약 통과. 작업별 독립 검토 통과.390/1440 합성 브라우저에서 아이콘/계정·테마 보존·질문→로그인 초안·자료→원문/인용·브리핑 기록을 확인했고390완료 브리핑/후속질문의 밝은·어두운 화면을 확인했다. 이 검증에서 실제 계정 세션이나 유료 모델 호출을 대신 만들지 않았다.
- 운영 준비: 승인된 두 번째 개발 초대를 비공개 등록·반복 검증했다. 관리자 권한 확대·공개 가입은 없다. 변경 대상 인증 행·세션 제약과 기존 데이터 건수의 비공개 백업/기준을 준비했다. 전체 DB dump가 아닌 이번 인증 변경의 표적 백업이며 공용 DB 테스트 초기화는 하지 않았다.
- 적용: 전체 변경 독립 검토 승인 후 개인 개발 소스f545e752f4dab69842c39b0e405b0e70416c6ab6·0006 세션 제약·API/워커 재시작을 확인했다. 기존 세션 만료일과 자료/신원 건수 보존, 정책1209600/604800초, 정적17파일/이전41자산 보존, 외부 HTTPS/화면·API200/비회원401/no-store/현재6해시 일치를 확인했다. 실제 배포된390/1440 화면·계정 메뉴·질문→로그인도 확인했다. [해당 소스 CI](https://github.com/DigestWorks/IssueDigest/actions/runs/38859480281)는 성공했다.
- 복구 기록: 개인 배포 도구가 PostgreSQL의336시간 표기와 tmux HOME 이스케이프를 잘못 해석해 확인/재시작이 중단됐다. 간격을 초 단위로 검증하고 원래 개인 실행 설정으로 API/워커를 복구했다. 이후 외부 응답·프로세스 생존·새 파일을 다시 확인했다. 제품 코드·운영/main·기존 데이터 변경은 없었다.
- 인계: 동료 실제 Google 첫 로그인은 당사자가 확인한다. 기존8시간 로그인 쿠키는 만료일을 보존했으므로 재로그인 후14일/7일 정책을 적용받는다. 공개 게시·개인 소유/추천·알림과 기존 권한 상실 시 표시 상태 전체 정리는 출시 전 후속이다. Sites v54 요약 게시를 마쳤으며 main/운영 게시는 유예한다.

- Sites: [v54 제품·개발 계획](https://lawdigest-rebuild-plan.ijaesinii.chatgpt.site/) public/native succeeded. source `1d4774572728aa7c4a179cad02c8d70ffa6d8080`, saved `appgprj_6ac612dd42708191a7a0c8377be64d48~appgver_4c615e2913a08191b6ae5a2ad1e4d859`, deployment `appgdep_6ad1c1e5e00c8191b7d783ffef439b13`. 문서 사본5dd8a9a·이전v53 보관·HTML39/내부 링크·자산·앵커1040개/공개 텍스트102파일의 비밀값 제외를 확인했다. 옛 보관 페이지6개의 잘못된 data URI favicon 경로만 보정하고 기록 본문은 유지했다. 사용자의 브라우저 탭을 열거나 이동하지 않았다.


## 이전 작업 · 개발 보조 도구 제거 · 2026-10-16

- 사용자 피드백에 따라 홈 하단의 연결 확인·수동 근거 URL 입력을 제거한다. 실제 자료 목록/검색/브리핑의 근거 열기와 보호 라우트는 유지한다. [범위](../changes/home-tools-removal.md).
- 기준f275e03·기존 Draft PR32 후속. 구현3b8be31로 전용 상태/핸들러/스타일/구식 테스트17건을 정리했다. JS493·린트/타입/빌드/계약 및 작업 검토를 통과했고390/1440 합성 브라우저에서 도구 부재와 실제 자료→원문/정확 인용을 확인했다. 전체 독립 검토를 통과했고 개인 개발 웹81a1c64 반영·외부 HTTPS/정적6해시·배포된390/1440 화면을 확인했다. 새 소스는 기존 Draft PR32에 갱신했고 main/운영은 유예한다. 서버 API·DB·main/운영은 변경하지 않는다.
- Sites 요약은 다음 기록 정리 시 반영 대기다. 이번 작은 화면 정리는 저장소 기록을 원본으로 한다.


## 이전 작업 · 로고·다크모드·로그인 진입 · 2026-10-16

- 요청: 생성 로고, 명시적 테마 전환, 우측 계정 메뉴와 행동 시 로그인. [수용 기준](../changes/brand-theme-entry.md)에 기록했다. 기존 비공개 자료와 자동 유료 실행 경계는 유지한다.
- 기준: feat/briefing-experience의7188d7f에서 별도 feature branch. 기존 격리 worktree를 재사용하며 main/운영 배포를 변경하지 않는다. JS478개 기준 검사를 통과했다.
- 상태: 생성 PNG·명시 테마·계정 메뉴·행동 시 로그인 구현(2c56571). 웹510검사/린트/타입/빌드·계약 검사를 통과했다.320/390/1440 독립 합성 브라우저에서 비회원 초안/진입·테마·저장 브리핑/비교·원문·로그인 페이지 로그아웃을 확인했다. 작업/전체 검토와 계정·로그아웃·401/403 진입 보완 재검토를 통과했다. [Draft PR32](https://github.com/DigestWorks/IssueDigest/pull/32)와 개인 개발 웹ace770f 반영을 마쳤다. HTTPS/정적6해시+로고·보호401/no-store를 확인했다. 외부 독립 브라우저에서도 생성 로고·테마 보존·계정 메뉴·질문→로그인 초안을 확인했다. 제품/검증 기준ace770f의 [CI 전체2557검사](https://github.com/DigestWorks/IssueDigest/actions/runs/38855551075)도 통과했다. Sites v53 요약 게시를 마쳤다. 실제 계정 로그인·모델·DB 쓰기를 대신 실행하지 않았다.
- Sites: [v53 로고·테마·로그인 진입](https://lawdigest-rebuild-plan.ijaesinii.chatgpt.site/#brand-theme-entry) native succeeded/public. source8c5b91b1f74dc4156137d8f5bbbf0e9704ddaf39, saved `appgprj_6ac612dd42708191a7a0c8377be64d48~appgver_6ebfea1363fc8191822d4b450655ff7d`, deployment `appgdep_6ad1b5b83d888191b6337efc7ada671b`. 문서 사본e065769·v52 보존·HTML38/링크1031/공개 텍스트99파일 비밀값 제외 통과. 사용자의 탭은 열거나 이동하지 않았다.
- 인계: 실제 개발 정적 웹은ace770f(제품 코드2c56571). 이후 커밋은 검증/게시 기록이다. 자체 합성 QA 서버·브라우저는 정리하며 feature branch와 Draft PR32는 보존한다. 공개 브리핑/개인화 등 후속 범위는 기존 작업 목록을 따른다.


2026-10-16. 최신 상태는 위 현재 작업을 따르며 과거 검증 기록을 보존한다. 상태는 문서·코드·검증·운영 증거를 구분한다. 웹·API·상태 계약·개발 자동 검증 기반, 첫 원문·파싱·인용 및 두 번째 개체·주장·관계·비교 조건, 세 번째 실행·화면·사용량 부분 계약을 구현했다. 실제 HTTP·브라우저 스모크 검증을 통과했으며 전체 P1과 제품 기능은 미완료다.

| 단계 | 현재 상태 | 완료 증거·다음 조건 |
| --- | --- | --- |
| P0 계획·기록 | 작성·게시 완료 · 검토 중 | 저장소 조사·사용자 응답·요구사항·설계·작업 목록 작성 |
| P1 기반 | 웹·API 개발 기반 구현 · 전체 미완료 | npm/uv 워크스페이스·상태 계약·자동 검증 통과. 실제 HTTP·브라우저 스모크 통과. 원문·인용·개체·주장·관계·실행·화면·사용량 부분 계약 구현. PostgreSQL 근거 스냅샷 저장·초기 outbox 추가. DB 세션·회원 권한·보호 근거 조회 구현. Google 로그인·명시 초대·자료 목록 구현·합성 검증. 공동 DB 초기 적용 완료. 실제 로그인·나머지 API·이벤트·워커·검색은 미완료 |
| P2 실제 근거 | 첫 이슈 공식 HTML1건 검증 · 등록 도구 준비 | 정부 본문35문단/3,231자·인용3개와 전용 검증 DB 저장 재조회. 기존PDF6개/35문항/87위치는 별도 검사. 첫 코퍼스/평가20문항·표/수치/주장 지지·공동 DB 승인1건 적용 완료, 나머지 자료 이관은 후속 |
| P3 검색·관계 | 문자 검색 SDK 구현·검증 · 전체 미완료 | 불변 근거의 본문/페이지/셀 검색·현재 권한·명시 색인 재생성 검증. 보호 API/화면은 아래 작업에서 연결. pgvector·재순위화·실제 질문 평가/Neo4j는 후속 |
| P4 에이전트·UI | 수동 조사·실제 모델 연결 · 품질 평가 후속 | 자료 선택·PydanticAI/DBOS·생성 모듈·정확 인용·후속 질문·저장/취소 구현. 합성 결합·실제 모델3건·개발 HTTPS 반영 확인. 전체 질문 품질·모듈 스트리밍·관계도/이미지·전체 제품은 후속 |
| P5 공유·이미지 | 미착수 | 저장/권한 경로와 이미지 공급자 필요 |
| P6 운영 검증 | DNS·HTTPS·자동 배포 준비 · 앱 공개 유예 | 서버·전용 DB/pgvector·자료 접근 확인. 최소 제품·비용·권한·운영 연결·별도 복원 검증 후 첫 게시 판단 |
| 이전 와이어프레임 | 코드 보존 · 배포 종료 | Vercel 배포 14개 삭제, Git 자동 배포 연결 해제 |

## 2026-10-13 · 공개 배포 인수인계

- 동료 보고: 공용 checkout·릴리스 개발 그룹 쓰기, main 자동 검사/배포·제한된 배포 SSH, 별도 운영 API 서비스 준비. 개발 브랜치·기존 DB·자료는 변경하지 않음.
- 직접 확인: DNS 정상, 서버와 외부에서 인증서 검증을 유지한 HTTPS `/` HTTP503. 외부 `/health/live`·`/api/v1/status` HTTP502, 운영 API inactive·현재 릴리스 없음. TLS 대기라는 전달 문서보다 HTTPS 연결이 진행됐지만 앱은 아직 게시되지 않았다.
- 최신 main `6d0884e`의 workflow·배포 스크립트·서비스·웹 설정을 읽었다. 개발 코드와의 읽기 전용 병합 미리보기에서 충돌 표시 없음. 통합 커밋·통합 후 검사·main 병합·첫 배포·복구는 아직 수행하지 않았다. 앱 화면은 빈 자료/연결 확인이며 실제 자료·AI·로그인·운영 DB는 후속이다.
- 상세: [공개 앱 배포 상태](../../infra/public-deployment.md). 이 변경은 문서만이며 운영 설정·공용 checkout·자료 변경 없음. 문서3개/상대 링크6개·공개 접속정보 제외·git diff --check 통과. 코드 전체 테스트는 반복하지 않았다.
- Sites: [v32 배포 상태](https://lawdigest-rebuild-plan.ijaesinii.chatgpt.site/#deployment) 공개 게시 native succeeded·URL 확인. source `d71b41cae7e4282453df8d9a910e9b9ddb7f2dc5`, saved version `appgprj_6ac612dd42708191a7a0c8377be64d48~appgver_4b8329f3a14c8191b1b3a35220d84593`, deployment `appgdep_6acde040f0c08191b1b854866d9d7b38`. 사본 기준579e023·이전v31 보존, HTML17개/로컬 링크·anchor248개/manifest/공개 접속정보 제외 통과. 보존본의 상대 링크를 기존 형식에 맞춰 수정 후 재검사했다. 문서 변경의 브라우저 화면 검사는 수행하지 않았다. 서버 개인 worktree도 문서만 fast-forward하며 운영 앱을 게시하지 않는다.

## 현재 작업 · B2C 브리핑 경험 첫 연결 · 2026-10-16

- 기준: [승인 인터뷰](../research/product-experience-interview.md)와 [첫 실제 연결 명세](../changes/briefing-experience.md). feat/briefing-experience, base feat/assembly-source-connector/e8c7b0a. B2C가 목표이며 두 사람은 초기 검증 참여자다(D016). 기존 linked worktree를 재사용한다.
- 구현: 질문 우선 홈·초대 로그인 초안·편집 후 명시 실행, 직접 선택/제한적인 연결 자료 후보, 현재 선택 원문의 정확 인용 선열람, 검증된 실제 AI 모듈의 브리핑·모바일 주장별 비교, 본문을 떠나지 않는 정확 원문 창을 연결했다. 기본 Canvas 계약·기존 저장/후속/멱등성/취소/예산은 유지한다. 공개 최근 이슈나 가짜 AI 결과를 채우지 않는다.
- 구분: 생성 중 먼저 보이는 것은 원문 인용이다. AI 부분 답변·전체 검색 이력·확인된 사실이 아니다. 현재 AI 주장 basis는 해석 그대로 표시하며 UI가 사실·찬반 분류를 만들지 않는다. 저장한 조사는 공동 조사 기록이지 개인 비공개 북마크가 아니다.
- 검증: Task1/2 작업 독립 검토와 보완 재검토 승인. Python2047/skip0·Ruff189·mypy83, 최종 웹478/25파일·lint/type/build/contract 통과. Python은 이번 UI 변경이 없어 같은 작업의 검사를 반복하지 않았다. 전체 검토의 초안 재등장·늦은 원문 응답2건과 저장 개별 조회 피드백을 RED8→GREEN8로 보완하고 scoped 재검토 C0/I0/M0을 확인했다. 합성 HTTP+소유 PG/FunctionModel 브라우저에서 질문 복원/조사0, 무관 질문 실행0, 원문→완료 모달 유지·정확 mark/Escape/초점 복귀, 320/390/1440 비교 가로넘침0, 실패/취소 원문 유지, viewer 생성 비활성, 저장 재열람 추가모델0을 확인했다. 실패→새 조사 즉시 입력 보존·지연된 목록404 뒤 원문/모달 삭제도 새 빌드 브라우저로 재확인했다. 최종 새 브라우저에서 guest reset→B→A/POST0, 늦은 A 조회→B 유지/닫힘 유지, 저장 GET의 loading→503→동일 GET 재시도2회도 확인했다. 권한404/일시503 주입과 원문 응답 지연 외에는 실제 합성 API/DB다. 실제 OAuth 제공자 로그인·실제 모델 추론 품질 검증이 아니다.
- 판단: HTTP403을 기존 클라이언트 권한 오류로 구분하고 현재 보호 리소스404도 원문을 닫는 조건으로 다룬다. 기존 backend가 회원권 상실에404를 쓰기 때문이다. 기존 원문 화면의403 안내가 로그인/권한 안내로 바뀌고, 실제 자료 누락/일시404라도 닫힌 원문은 성공한 재조회가 필요하다. HTTP/스키마·DB·워커 계약은 바꾸지 않는다.
- 개발 적용: [개발 앱](https://dev.issuedigest.projects.ai.kr/)의 정적 웹 source35a530a 반영, 파일16개/이전 asset9개 유지·개인 Nginx reload. 외부 TLS·홈/login/health/status200·session/research401/no-store, 현재 asset7개의 로컬 빌드 일치와 기존 asset7개의 같은 바이트를 확인했다. 기존 API/worker·TLS/시스템 프록시·자료·비밀 설정 유지, DB쓰기/migration·실제 사용자 세션 대행·유료 모델 검증·main/운영 게시0. [Draft PR31](https://github.com/DigestWorks/IssueDigest/pull/31), base feat/assembly-source-connector. Sites v52 public/native succeeded, 이전v51 보존. source56d070e744fd470eb5a509b141d9dbdb0c2051fb, saved appgprj_6ac612dd42708191a7a0c8377be64d48~appgver_08fcb4f6351881918e5f38180f209918, deployment appgdep_6ad1a3ddff84819188daf00100cc762c. 사본기준83e81f0, HTML37/로컬링크·anchor984/공개텍스트97의 실제 비밀값 제외 검사 통과. 사용자 브라우저 탭을 열지 않았다.
- 후속: 공개 게시·공유 불변 브리핑, 개인 관심 이슈/변경·알림, 실제 주목도·개인화, 검증된 AI 모듈의 점진 전달. 공개 이슈 범위·외부 탐색 범위·초기 AI 이용 정책은 답변 대기다. 현재 자료12건을 공개 브리핑12개나 최근 인기 이슈로 표시하지 않는다. 권한 상실 시 현재 원문 미리보기/창은 지우지만 이미 표시한 Canvas/자료 제목 전체 정리는 공개 출시 전 후속으로 남긴다.

## 이전 작업 · 수집 연결·제품 경험 인터뷰 · 2026-10-16

- 범위: [첫 국회 원문 연결기](../changes/assembly-source-connector.md), [제품 경험 인터뷰](../research/product-experience-interview.md). feat/assembly-source-connector, base feat/research-journey/2439385. 기존 linked worktree를 유지하며 새 branch에서 진행한다.
- 읽기 조사: 기존 MySQL Bill41,004·제안일2020-06-01~2026-07-10 확인, SELECT만 수행했다. 행수/상한은 현재 수집 실행의 정상·최신성을 보장하지 않는다. 기존 Airflow는 검토 코드의 폐기 경로이며 실제 활성 실행기는 추가 확인 대상이다.
- 구현: 공개 국회 상세 GET/읽기 POST의 고정2요청·TLS/크기/형식/비밀로그 제한·정확 요약 추출과 private capture→기존 승인 등록 계획의 offline 연결을 구현했다. 실제 공식 원문487자를 수집하고 정확 인용1개를 준비했다. 원문과 관계없는 footer 구조 문제·숨김/native context 반영 문제를 RED회귀→보완·독립 검토로 해결했다. 재수집의 문서 변경 판정·정기 수집·전체 처리 이력/변경 감지/알림은 이번 완료가 아니다.
- 실제 연결: 기존 앱 역할로 제안 내용1건/인용1개를 추가해 총자료12·인용33·검색21단위/outbox12. 기존11건의 hash·계정/초대/권한·세션 보존, 반복 신규0. schema/DDL·legacy쓰기·실제사용자 세션 대행·모델호출0. 기존 개인 API/웹/조사worker는 재시작하지 않았다. 신규 수집기가 상주/예약 실행되는 상태는 아니다.
- 검증: controller 별도 소유 PG18.6 전체 Python2047개/skip0, JS408개·Ruff188파일/mypy83·TypeScript/빌드/계약 통과. 독립 작업/보완/전체/최종 보완 재검토 C/I/M0. 실제GET/POST2회·265262바이트capture, 본문487자·canonical 인용·같은artifact반복추가0 확인. 앞선GET 호환 실패와 controller의 잘못된 로컬base경로 참조는 적용 전에 교정했으며 실제DB 부분쓰기0이었다.
- 백업: 적용 전후 서버 외부 full/app archive 보존. 적용 후 앱 archive를 별도 소유 PG18.6에 복원해 자료12/인용33/검색21·기존11hash와 실제auth행 보존·기존/신규 canonical bundle·합성 신원 보호catalog12/다른공간/미인증/viewer생성거부를 확인했다. 이후 자체컨테이너/익명볼륨을 제거했다. 원래사용자의 세션은 대신 사용하지 않았다. 외부TLS·동일기존웹빌드/asset7개·login/health200·보호401/Origin403도 확인했다. 프런트 코드는 그대로이며 새로운관심이슈/생성UI를 배포한것이아니다. 실제 DB 테스트/초기화/복원·운영 원본/MySQL·공용 checkout·main은 변경하지 않는다.
- 인터뷰: 질문 우선+최근 이슈 탐색, 사실/주장/미확인 요약, 여론조사/언론/온라인 반응 구분, 근거 부족을 솔직히 인정하는 AI 어조를 사용자 답변으로 기록했다. 30초 요약·결과 중심 동적 화면·관심 이슈 저장/변화→후속 탐색→공유·휴대폰 중심·최신 전체 요약의 변경 표시·새 사실/공식 결정/정정 우선까지 답변을 받았다. 여러 매체의 새 보도 기반 최근 이슈·중요 변화 발생 시 알림 선호, ChatGPT의 위젯/에이전트 경험과 Linear/Toss/Apple 수준의 정돈·마감 선호도 기록했다. AI가 자료 탐색→비교/시각화까지 자율 진행하는 선호도 확인했다. 우선 모듈·구체적인 불만은 추가 질문 중이다. 제안과 확정 답변을 구분하며 새 UI는 아직 구현하지 않는다.
- 인계: [Draft PR #30](https://github.com/DigestWorks/IssueDigest/pull/30), 기준제품 코드912854f·문서a413b46의 [CI 성공](https://github.com/DigestWorks/IssueDigest/actions/runs/38838392607). 서버 개인 checkout도a413b46으로 동기화하고 수집/준비 entrypoint2개를 설치했다. 앱/워커 재시작·정기 수집 시작·main/운영 게시 없음.
- Sites: [v50 제품 경험 인터뷰·첫 연결기](https://lawdigest-rebuild-plan.ijaesinii.chatgpt.site/#product-experience) public/native succeeded. source `ee61a05a320aa203cc5578bc2e347d2a576f881f`, saved `appgprj_6ac612dd42708191a7a0c8377be64d48~appgver_77be20c2049c8191b3ebebecde763ae2`, deployment `appgdep_6ad186d11a0c819195a52504ced7d6c2`. 이전v49 보존·사본기준a413b46·HTML35/로컬 링크anchor892/공개 텍스트94개와 실제 비밀값/계정/원문 제외 검사 통과. source동기화의 일시DNS실패는 복구 확인 후 같은소스/프로젝트로 재개했다. 브라우저 탭을 열지 않았다.
- 정리: 자체 PG 검사/복원 컨테이너·익명볼륨을 제거하고 private capture·job·계획·전후dump·리뷰를 보존했다. SDD 스크래치만 비공개 보관 후 정리하며 PR 작업용 linked worktree는 유지한다. 인터뷰는 계속 진행 중이고 신규UI 배포로 표시하지 않는다.

## 이전 작업 · 첫 조사 흐름 · 2026-10-15

- 범위: [명세](../changes/research-journey.md), [실행·비용·검증 경계](../../infra/research-development.md), feat/research-journey, base feat/workspace-clarity-legacy/5fd3824. 사용자 승인 범위는 자료 선택→질문→생성 결과→정확 원문→자동 저장·재열람이다. main/운영 게시 유예(D013)를 유지한다.
- 화면: **이슈 조사 / 자료 / 저장한 조사**. 실제 자료 제목·의안번호·제안일로 고르고 법안 핵심 정리·질문을 시작한다. 접수/검색/분석/인용 연결 확인과 취소·실패·연결 대기·한도를 구분한다. 질문 전에는 AI 결과를 표시하지 않는다. 생성된 해석·검증된 인용 위치·원문을 구분하고 후속 질문·같은 결과 재열람을 연결했다.
- 실행: PydanticAI2.56.0/DBOS3.2.0, gpt-5.4-mini Responses/store=False, PG migration0005. 명시 DBOS 초기화·앱 DDL 제한·내구 checkpoint·현재 권한·idempotency·월 글로벌 USD10/최대40건 보수적 예약. 새로고침/완료 GET은 모델 호출0, 응답 유실 구간의 정확히 한 번 과금은 보장하지 않는다.
- 자료 연결: [기존 법안 내용·이력 대조](../research/bill-history-reuse.md). 최근 기본 정보8건의 수집 이력0건을 확인했다. 별도21대 법안2건의 원본 제안 내용400/422자와7개 과거 날짜/단계 문구를 국회 원문과 대조하고 정확 인용13개를 준비했다. 과거 자료/최신 상태/전문을 구분하며 기존9건의 불변 hash·계정·초대·권한을 보존한다. 개발 DB에2건/인용13개를 추가해 총11건/인용32개/검색20단위를 연결했다. 반복 적용 신규0, 기존9건과 계정·권한·세션 보존을 확인했다.
- 검증: controller 전체 Python1,888+JS408=2,296개, skip/warning0·Ruff178/mypy77·TypeScript/빌드/계약 통과. 작업별 독립 검토/보완 재검토 C/I/M0. 합성 신원·실제 자료 복원본·실제 HTTP/PG/DBOS·합성 FunctionModel 브라우저에서 요약/비교/타임라인·진행 상태·정확 원문 선택·후속 질문·저장 재열람·새로고침 POST0·취소·실패·390px 가로 넘침0/pageerror0 확인. 타임라인 JSONB 날짜 재열람과 요청 중 선택/취소/Back/Forward 상태를 회귀 검증으로 보완했다. 전체 독립 검토·보완 재검토·실제 결과 표시/접근성 검토 C/I/M0. 실제 결과 1365/390px·원문 재진입·추가 POST0/pageerror0 확인.
- 실제 AI: 승인 키를 저장소 밖600권한으로 준비했다. 별도 소유 DB·실제 자료·합성 신원의 HTTP/PG/DBOS 흐름에서 gpt-5.4-mini 고정 질문3건의 요약·비교·타임라인과 정확 원문·저장/재열람을 확인했다. 선택1/2/2자료의 주장3/2/7개가 모두 선택 자료를 인용하고7개 과거 날짜가 원문 인용과 일치했다. 첫 제공자 응답의 보조 메시지 중복으로 실패한1건은 보존하고 반환 투영·선택/관련 자료 구분·알려진 사용량 보존을 보완했다. 실제 응답4회 합계 입력8499/출력1572토큰이며 청구액을 조회한 결과는 아니다. 실제 사용자 세션을 임의 발급/재사용하지 않았다.
- 품질 한계: 이3건은 실행/저장/정확 위치/모듈 차이를 확인한 표본이다. 타임라인 질문의 전체4항목 요청을 법안별4/3개로 표시한 사례가 있어 길이·개수 지시 준수 평가는 후속이다. 인용 일치는 주장 지지/법적 효력 검증이 아니며, 전체20문항·두 사용자의 상품적 품질/운영비 평가는 미완료다.
- 개발 반영: [개발 앱](https://dev.issuedigest.projects.ai.kr/) 제품 source `d6e2df1`·정적15파일/source map0, 개인 API/DBOS worker·앱 역할 DDL 제한·migration0005 연결. TLS 검증을 유지한 index/asset7개 빌드 일치·login/health200·미인증session/research401/no-store·잘못된Origin403 확인. 서버에서도 별도 고정 질문1회를 검증해 입력1064/출력267토큰·요약/근거 모듈을 확인했다(실제 사용자 세션/DB 쓰기0).
- 백업/복구: 적용 직전과 적용 후 서버 외부 full/app archive 보존. 별도 소유 PG18.6에 적용 후 app archive 복원, 자료11/인용32/검색20·DBOS schema·새 canonical bundle2·기존 계정/세션 건수 보존, 합성 신원으로 보호 catalog11·비회원/다른 공간/viewer생성 거부 확인. 실제 DB를 초기화/복원하지 않았다. 전체 역할·확장·운영 복구 검증은 별도다.
- 인계: [Draft PR #29](https://github.com/DigestWorks/IssueDigest/pull/29), [제품 코드 CI 성공](https://github.com/DigestWorks/IssueDigest/actions/runs/38732066902). [Sites v49](https://lawdigest-rebuild-plan.ijaesinii.chatgpt.site/#research-journey) 공개 게시 native succeeded. source `eee84956564eb2d29c6d18ddf15db61ffd52bb58`, saved version `appgprj_6ac612dd42708191a7a0c8377be64d48~appgver_0057c22d36cc81919ff55d2c65963dcf`, deployment `appgdep_6ad0c52ac25c8191b400fea83ef699d5`. 이전v48 보존·사본 기준65a4e9c·HTML34/로컬 링크·anchor847·공개 텍스트90개 비밀값/계정/원문 제외 확인. 기존 브라우저 탭은 열지 않았다. 운영 원본/MySQL·공용 checkout·시스템 서비스·main은 변경하지 않는다. 비밀값·실제 계정·개별ID·원문은 비공개 검증 위치에만 둔다.

- 정리: 자체 합성 브라우저·API·worker 종료, 이미지/전체ID/작업label/loopback 포트 대조 후 자체 QA·복원 컨테이너/익명 볼륨 제거. 실제 모델 결과·검증·전후 dump·리뷰 기록은 비공개에 보존한다. 서버 개인 개발 앱/worker는 유지하며 문서 인계 커밋은 제품 코드를 변경하지 않는다.

## 이전 작업 · 자료 중심 UI·기존 법안 연결 · 2026-10-15

- 범위: [작업 명세](../changes/workspace-clarity-legacy.md), R2/R3/D011/D015 유지. feat/workspace-clarity-legacy, base feat/evidence-search-ui/b94c7fb. 격리 worktree·OpenSpec root=null·작업별 구현/독립 리뷰를 적용한다.
- UI: 검색→자료→원문/인용이 중심인 작은 작업 공간으로 정리한다. ID/정밀 시각·개발 진단은 보조 상세로 옮기고 기본 자료 유형/날짜/읽기를 우선한다. 실제 AI 답변·생성 UI 미연결 상태를 명시한다.
- 자료: 기존 MySQL Bill을 SELECT만 하여 고등교육·등록금 관련8건을 선별했다. 제안일2026-03-30~2026-06-22, 원문 링크8건에서 HTTP200·국회 host·법안명/원천ID 대응 확인. 기본 메타데이터만 추가하며 전문/AI 요약/현재 처리 상태를 새로 검증했다고 표시하지 않는다. 원문/개인 ID/계정은 비공개에 보관한다.
- 재검사: 기존 parsed JSON840/PDF774, 연결 후보225·격리384·미지원231·PDF 헤더 없음23으로 확인했다. 이 집계는 원문·인용·이용 조건 검증이 아니므로 PDF 본문 등록은 보류한다.
- 검증: 전체 Python1,853+JS365=2,218개·skip/warning0·Ruff162/mypy69/TS/빌드/계약·독립 작업/전체 검토 C/I/M0. 합성 실제 HTTP/PG 브라우저에서 검색→위치→PDF/표/인용·새로고침·390px·로딩/재시도/빈 결과·로그아웃401, pageerror0(의도한503 console1) 확인.
- 실제 추가: 기본 정보8건/인용16개를 기존 앱 역할/초대로 개발DB에 추가. 총자료9/인용19/outbox9, 자료9건 전체 색인·총16단위. 반복 신규0, 기존 공식 자료·계정/초대/권한·세션 보존. schema/권한/legacy 쓰기/AI 호출 변경 없음.
- 백업/조회: 전후 서버 외부 full/app 백업·소유 loopback DB 앱 복원/새8 bundle 대조. 복원본의 별도 합성 계정으로 보호 목록9·GET8·검색8 및 다른 공간/권한·세션 폐기 거부. 실제 사용자 세션을 생성/대신 사용하지 않았다.
- 개발 앱: 2026-10-15 18:46 KST source0116885·정적14파일/source map0 반영. 외부 TLS·index 빌드 일치·home/login/asset/health/status200·미인증session/search401/no-store. 사용자 본인의 자료/검색 확인은 남아 있다. main/운영 배포 유예·시스템/공용 checkout 유지.
- 인계: [Draft PR #28](https://github.com/DigestWorks/IssueDigest/pull/28) 게시·앱 첨부. 공개 [Sites v48](https://lawdigest-rebuild-plan.ijaesinii.chatgpt.site/#workspace-clarity) native succeeded·source34492f9, 이전v47 보존·사본 기준c446d0d·HTML33/로컬 링크803/공개 텍스트86개 실제 비밀값/UUID/개별hash/원문 제외 확인. 브라우저 탭은 열지 않았다. 새 키/관리자 권한 요청은 없다.
- 정리: 브라우저/합성 API 종료·소유/이미지/label/loopback 포트 대조 후 전용 QA 컨테이너와 익명 볼륨/복원 자료를 제거했다. 실제/합성 검증 증거·private 계획·전후 dump는 개인 위치에 보존한다. 개발 문서·PR·Sites를 갱신하며 마지막 저장소 인계 commit은 코드/자료/운영 설정을 바꾸지 않는다.

## 이전 작업 · 보호 근거 검색 API·화면 · 2026-10-15

- 작업/담당: [검색 인터페이스](../changes/evidence-search-interface.md), R2/R3·D011/D015. controller/구현자·feat/evidence-search-ui, base docs/development-https-audit/edfa66f. 격리 worktree·OpenSpec root=null, 기존 SDK를 소비한다.
- 현재: 보호 JSON POST·typed client·작업 공간 검색 화면·검증된 원문 위치 reader 연결을 구현했다. Task1 검토에서 JSON 날짜/마이크로초/출력 메타데이터 한도와 async DB 호출을 보완했고 재검토를 통과했다. Task2 검토 승인 후 새로고침 문서/coverage 표시를 정리했다. 전체 변경 독립 리뷰 Critical/Important0, Minor1 문구 보완 후 재검토 승인. [Draft PR #27](https://github.com/DigestWorks/IssueDigest/pull/27) 게시·앱 첨부, 개발 앱 갱신·Sites v47 게시·개발 인계 완료다. 의미 검색·AI 생성·스키마 변경은 이번 범위가 아니다.
- 개발 접속: 2026-10-15 17:04 KST에 권한DNS4곳/Google/Cloudflare 일치·실제 HTTPS 인증서 검증 정상. login/asset/health200·미인증session401·Origin403·Google start/브라우저 결합 취소303·callback/PKCE/보안cookie·외부 로그 차단을 확인했다. 앞선 DNS 불일치/TLS 대기는 해소됐다. [상세](../../infra/development-https.md).
- 실제 로그인: 이번 읽기 전용 DB 확인에서 실제 identity·작업 공간 membership·세션 기록·초대 subject 바인딩의 존재를 확인했다(개별 값은 비공개). 실제 Google 로그인 후 저장 상태가 생성됐으며, 사용자 화면의 원문/인용 열람·오류 상태/로그아웃 완료는 아직 확인하지 않았다. main/운영 배포 유예는 유지한다.
- 검증: controller 전체 Python1,808개·Ruff format159/mypy68, JS363개·lint/TypeScript/SPA/OpenAPI 통과(2,171개, skip/warning0). 마지막 표시 정리 후 관련64개·검색9개와 정적/빌드 재검사 통과. 별도 소유 PostgreSQL과 실제 HTTP API의 합성 브라우저 여정으로 text/emoji/결합문자·PDF 실제 페이지·전체 표 셀·기존 인용·새로고침 재검증·loading·503 후 재시도/빈 결과·390px 가로 넘침 없음·로그아웃401 확인. pageerror0, 의도적으로 주입한503 네트워크 console 오류1개는 실패 UI 검증이다. 실제 제공자 호출/공동 DB 합성 쓰기 없이 수행했다. Sites v47 게시 완료이며 기존 탭을 열지 않았다.
- 개발 앱: 2026-10-15 18:04 KST, 제품 source fd26683·서버 고정 도구/lockfile 빌드14파일/source map0. 개인 API 재시작·개인 정적 Nginx root 갱신/reload 후 실제 HTTPS index가 해당 빌드와 byte hash 일치, home/login/asset/health200·미인증 session/search401/no-store 확인. 기존 schema0004·승인 자료1건/인용3개·초대 바인딩·DDL 없는 앱 권한 유지. 시스템 Nginx·DB schema/승인 자료·main/운영은 변경하지 않았다. 실제 사용자 검색/원문 열람 품질은 개발 앱에서 확인한다.
- CI: [fd26683 전체 검사 성공](https://github.com/DigestWorks/IssueDigest/actions/runs/38710036436). 이후 문서/게시 metadata는 제품 코드와 구분한다.
- Sites: [v47 근거 검색·개발 접속](https://lawdigest-rebuild-plan.ijaesinii.chatgpt.site/#evidence-search) native succeeded/public. source `08a39ab63573112d0c62fe7e86406b8c449ac667`, saved `appgprj_6ac612dd42708191a7a0c8377be64d48~appgver_cc4108a53ab0819180dea991bf1803d0`, deployment `appgdep_6ad0981ad0748191b2a67f3a4a2badcc`. 사본 기준cff9eee·v46 보존·HTML32/로컬 링크·anchor760·공개 텍스트84파일 실제 비밀값/계정/개별ID 제외 통과. 문서 요약의 새 Site 브라우저 검사는 수행하지 않았고 기존 탭을 열거나 이동하지 않았다. 제품 브라우저 검증은 위 별도 기록을 따른다.

## 이전 작업 · 개발 HTTPS 외부 연결 점검 · 2026-10-15

- 작업/담당: [개발 HTTPS 인수인계](../../infra/development-https.md)의 관리자 적용 후 실제 외부 확인. controller·docs/development-https-audit, baseops/development-https/a54e98c. 제품 코드 변경 없음.
- 확인: 관리자 HTTP80 virtual host→내부18173 설치. 정확 Host·DNS 우회 읽기 검사에서 login/health200·미인증session401. 실제 서버 내부 웹/API는 응답한다.
- 미완료: 개발 주소는 OS/Google/Cloudflare와 권한DNS2곳(ns1/ns2.hosting.co.kr)에서 NXDOMAIN. 서버 직접 연결/SNI·정상 인증서 검증은 hostname mismatch62, 개발 host에443/TLS 미설정. 전역 access/error 로그를 상속하며 개발 host의 OAuth 로그 차단 미반영이다.
- 다음: 활성 projects.ai.kr DNS 존에서 dev.issuedigest 레코드 확인·개발 TLS/443·callback 로그 정책 반영을 동료에게 추가 전달. 사용자 Google callback 추가 완료 기록은 유지한다. 해당 조건을 만족한 뒤 실제 HTTPS/Google 로그인·자료 열람을 검증한다.
- 범위: 읽기 조사만 수행. 인증서 검증 우회/HTTP Google 로그인·OAuth start/callback·서버/앱/DB/권한/main 변경 없음. 새 사용자 입력은 DNS/TLS 적용 결과이며 비밀값을 요청하지 않는다. 문서 상대 링크25개·실제 비밀값/계정/개별ID 제외·diff 검사를 통과했다. [Draft PR #26](https://github.com/DigestWorks/IssueDigest/pull/26) baseops/development-https·앱 첨부. 제품 코드 변경 없어 전체 테스트를 반복하지 않았다.
- Sites: [v46 개발 HTTPS 점검](https://lawdigest-rebuild-plan.ijaesinii.chatgpt.site/#development-https) native succeeded/public. source `be426d9bc8644aa6d498161273b0a5d4378752fb`, saved `appgprj_6ac612dd42708191a7a0c8377be64d48~appgver_f6d298c1216481919bf24117705d9f70`, deployment `appgdep_6ad06f3bdf34819197e4b6dc0d9dea74`. 사본 기준87123d0·v45 보존, HTML31/로컬 링크anchor718/manifest·Site공개69파일 비밀값 제외 통과. 첫 source helper 열기는 Git 호스트 DNS 오류로 중단됐고 호스트 재조회 후 같은 Site/credential로 정상 재개했다. 문서 요약의 새 브라우저 검사는 수행하지 않았고 사용자 요청대로 Site를 다시 열지 않았다.
- 인계: 서버/앱을 변경하지 않으며 현재 읽기 점검 문서 branch의 사용자 폴더·서버 개인 worktree 동기화는 마무리 중이다.

## 이전 작업 · 고정 HTTPS 개발 접속 준비

- 작업: [고정 HTTPS 개발 준비](../changes/development-https.md), [관리자 적용/요청](../../infra/development-https.md). controller·ops/development-https·baseops/google-login-runtime/95b7bff. 제품 코드·API/DB 스키마·의존성 변경 없음. Sites는 갱신하되 사용자가 이미 열어 둔 탭을 다시 열거나 이동하지 않는다.
- 준비: dev.issuedigest.projects.ai.kr의 별도 개발 origin. 개인 정적 빌드12파일/source map0·개인 Nginx loopback18173→기존 개인 API18090, Vite/HMR 외부 노출 없음. 개인 API의 origin과 기존 Google client/app 역할을 연결했다. 설치 Nginx의 미지원 CLI 옵션은 설정 검사에서 발견해 호환 명령으로 검사·기동했고, 시스템 로그/권한 변경 없이 개인 prefix를 사용한다.
- 검증: 내부 SPA/login/assets200·없는asset/dotfile404·health200·미인증session401·과거Origin403·새originstart/취소callback303와 callback/PKCE/nonce/보안cookie. 검사 후 승인자료1/인용3/초대1·실제auth user/session/member/flow0·앱DDL 없음. 내부 HTTP Cookie 전달은 TLS 종료 뒤 proxy 동작 검사이며 공개 TLS·사용자 브라우저 로그인 증거가 아니다.
- 대기: 개발 주소 DNS/TLS/공개 Nginx는 아직 없거나 미검증이다. 사용자는 Google callback 추가 완료를 전달했고 실제 제공자 반환은 외부 HTTPS 후 검증한다. 시스템 Nginx는 읽기만 가능하고 sudo 권한 목록 조회도 허용되지 않아 직접 설치하지 않았다. 관리자에게 기존 서버의 개발 virtual host 연결만 요청한다. 새 자원·DB/권한·sudo 확대·main 병합/운영 앱 배포는 요청하지 않는다.
- 사용자 입력: 기존 Google OAuth 웹 client에 `https://dev.issuedigest.projects.ai.kr/api/v1/auth/google/callback` 추가 완료 전달. 실제 외부 HTTPS 후 사용자 Google 로그인/자료 목록/원문·인용3개 확인. 비밀값 재발급/대화 공유 없음.
- 다음: 관리자와 사용자 설정 반영을 받은 뒤 인증서 검증을 유지한 외부 접속과 실제 사용자 여정 확인. 독립 운영/문서 검토C/I/M0·상대 링크87개·공개303파일 실제 비밀값/계정/개별ID 제외·diff 검사를 통과했다. [Draft PR #25](https://github.com/DigestWorks/IssueDigest/pull/25) baseops/google-login-runtime·앱 첨부. 제품 코드는 바꾸지 않아 전체 테스트를 수동 반복하지 않았고 서버 정적 빌드와 실제 내부 응답/flow를 새로 검증했다.
- Sites: [v45 개발 HTTPS](https://lawdigest-rebuild-plan.ijaesinii.chatgpt.site/#development-https) native succeeded/public. source `662b8ca6cc3768fa8ad0742fdf9c86e5de26b923`, saved `appgprj_6ac612dd42708191a7a0c8377be64d48~appgver_03393bc90128819198b961784da0bf53`, deployment `appgdep_6acf4d9a63dc81918ed642d29174165a`. 사본 기준5d61671·v44 보존·HTML30/로컬 링크anchor677/manifest 통과. 요약 변경의 브라우저 검사는 수행하지 않았다. 사용자 요청대로 Sites를 다시 열거나 탭을 이동하지 않았다.
- 개발 인계: 개인 nginx/API·자산/비밀 loader를 후속 HTTPS 연결용으로 유지한다. 공용 자원·운영 서비스·실제 Google사용자/세션을 변경하지 않았다. 사용자 폴더/서버 개인 worktree를 ops/development-https/origin 추적으로 연결하고 같은348841f·깨끗한 Git 상태를 확인했다. [기록 기준5d61671 CI 성공](https://github.com/DigestWorks/IssueDigest/actions/runs/38543640234)을 확인했으며 이후 게시/인계 문서 커밋과 구분한다.

## 이전 작업 · 실제 Google 로그인 개발 연결

- 작업: [개발 runtime 연결](../changes/google-login-runtime.md), R1/D015. controller·ops/google-login-runtime, baseops/database-bootstrap/44f7562. 제품 코드/API·스키마·의존성 변경 없음.
- 결과: 서버 개인 API에 기존 DDL 없는 앱 DB 계정과 승인 Google 설정을 주입했다. head0004·공식 자료1건/인용3개/초대1건 유지. 개인 SSH/HTTPS로 로그인/health200·미인증session401·잘못된Origin403·실제start/취소callback303·PKCE/nonce/cookie/flow 소비를 확인했다. 실제 사용자/세션/회원0이다.
- 사용자 확인: 자체 서명 인증서 예외를 둔 인증 전 브라우저 QA와 달리 사용자 앱 내 미리보기는 ERR_CERT_AUTHORITY_INVALID로 차단되고 포트도 변경됐다. 실제 Google 로그인·자료 목록/인용 열람은 대기다. 원격localhost 안내를 정정하고 사용자 SSH/인증서 설정 요구를 중단했다. 고정HTTPS 개발주소가 필요하며 설치된 Nginx 설정은 읽기만 가능하고 수정 권한은 없다. runtime 응답을 사용자 접속 완료로 간주하지 않는다.
- 다음: 고정HTTPS 개발주소·프록시/인증서·등록 callback을 준비한 뒤 사용자 첫 Google 로그인→자료 목록→원문/인용을 확인한다. 현재 공개 앱·운영 서비스·main은 변경하지 않는다. Google Audience/test-user 오류는 실제 제공자 화면을 확인한 뒤 필요한 항목만 안내한다.
- 검토·기록: 독립 운영/문서 검토C/I/M0·상대 링크48개·공개 파일299개의 실제 비밀값/계정/개별ID 제외·diff 검사 통과. [Draft PR #24](https://github.com/DigestWorks/IssueDigest/pull/24) baseops/database-bootstrap·앱 첨부. 제품 코드 변경 없어 전체 테스트를 수동 반복하지 않았다.
- Sites: [v44 실제 로그인 연결](https://lawdigest-rebuild-plan.ijaesinii.chatgpt.site/#google-login-runtime) native succeeded/public. source `b9a63e8ff849c25b2297cef13bbc0a9e4f4feba7`, saved `appgprj_6ac612dd42708191a7a0c8377be64d48~appgver_8c1bab7b07a88191a2a622c79e9a4532`, deployment `appgdep_6acf45cac25c8191abb1ccb00524adb4`. 사본 기준2b73886·v43 보존·HTML29/로컬 링크anchor637/manifest·Site공개65파일 실제 private 값 제외 확인. 계획 문서 요약의 새 브라우저 화면 검사는 수행하지 않았다.
- 정리: 실패한 localhost preview의 소유 controller를 확인하고 종료해 SSH/HTTPS 자식 프로세스·QA브라우저를 정리했다. 서버 개인 configured API와 private 설정은 후속 개발용으로 유지한다. 공개 앱 배포나 사용자 접속 완료가 아니다. 사용자 폴더/서버 개인 worktree를 ops/google-login-runtime/origin 추적으로 연결하고 같은219e2ed·깨끗한 Git 상태를 확인했다. [기록 기준2b73886 CI 성공](https://github.com/DigestWorks/IssueDigest/actions/runs/38539567880)과 이후 게시/인계 문서 커밋을 구분한다.

## 이전 작업 · 공동 개발 DB 초기 적용

- 작업: [공동 DB 적용 기록](../changes/shared-database-bootstrap.md). 기존 명시 migration/승인 등록 도구를 실제 전용 DB에서 실행했다. 담당 controller, `ops/database-bootstrap`·base feat/evidence-search/d700182. 제품 코드 변경 없음.
- 결과: PG18.6/vector0.8.7 유지, revision0004·public15테이블. 기존 개발/앱 역할 분리·필요 DML/앱 DDL 부재를 실제 검증했고 권한/계정/설정 변경 없음. 승인 공식 자료1건/인용3개/초대1건/outbox1건·검색8단위, 등록/투영 반복에서 중복0·unchanged. 실제 사용자/세션/회원/로그인 flow0이며 승인 초대는 미바인딩 상태다.
- 복구: 전/후 full+app archive를 서버 밖 개인 경로에 보존하고 앱 범위를 별도 소유 PG18.6에 복원했다. canonical 전체·승인 초대·outbox·검색 투영 대조 통과. vector 바이너리/역할·전체 서버 복구/정기 백업 완료는 아니다. 원문 bytes/승인 입력은 별도 개인 경로에 유지한다.
- 검증: 서버 실제 CLI offline/check/apply/repeat·권한/기존 vector·앱 범위 복원 성공. 초기 스키마 소유 역할 guard와 복원 후 초대 검증 도구의 가정을 수정한 과정은 상세 기록/private 로그에 보존했다. 제품 코드 기존 전체2,109개/CI d700182 성공을 재사용하며 문서만 변경해 전체 테스트를 반복하지 않는다.
- 남은 입력: 현재 새 관리자 요청 없음. 첫 실제 Google 브라우저 로그인은 사용자 확인, 두 번째 Google 이메일은 추가 초대 시 필요. 정기 백업/전체 복구·분담 비용은 사용자 작업 저장·첫 공개 전 별도 확인.
- 다음: 앱 runtime을 기존 앱 역할/Google 설정으로 연결하고 사용자 실제 로그인→자료 목록→원문·인용 열람을 확인한다. 보호 검색 API/UI·의미 검색/AI·worker는 후속이다. D013 공개 앱 배포 유예를 유지한다.
- 검토·게시: 독립 결과/문서 검토 C0/I0/M1 후 과거 요청 상태의 시점을 정정하고 재검토 잔여C/I/M0. [Draft PR #23](https://github.com/DigestWorks/IssueDigest/pull/23) basefeat/evidence-search·앱 첨부. 문서 상대 링크82개·diff·공개 파일298개의 비밀값/계정/개별ID/hash 제외 확인. 소유 QA 컨테이너/익명 볼륨 제거·임시 passfile 부재 확인, 개인 백업/계획·리뷰는 보존.
- Sites: [v43 공동 DB](https://lawdigest-rebuild-plan.ijaesinii.chatgpt.site/#shared-database) native succeeded/public. source `ecfb668fa776a0b287c72086afc2ef83c23b4b21`, saved `appgprj_6ac612dd42708191a7a0c8377be64d48~appgver_23855b8565a8819184f39a313ac8a38d`, deployment `appgdep_6acf3ac604b88191a1da91d77e585213`. 사본 기준9905a7d·v42 보존, HTML28개/로컬 링크·anchor598개/manifest 통과. 문서 요약만 변경했으며 새 브라우저 화면 검사는 수행하지 않았다.
- 개발 인계: 사용자 폴더·서버 개인 worktree를 ops/database-bootstrap/origin 추적으로 연결하고 같은 a4313b9·깨끗한 Git 상태를 확인했다. 제품 코드/의존성 변경 없음. 실제 앱 runtime·Google 로그인은 다음 작업. [초기 적용 기록9905a7d CI 성공](https://github.com/DigestWorks/IssueDigest/actions/runs/38534024267)을 확인했으며 이후 게시/인계 문서 커밋과 구분한다.

## 이전 작업 · PostgreSQL 문자 검색 기반

- 작업: [저장 근거 검색 명세](../changes/evidence-search.md), R2/R3·D011/D015. 원문 버전과 정확한 본문 구간/페이지/셀 위치를 반환하는 첫 검색 SDK.
- 담당/브랜치: controller·implementer, `feat/evidence-search`; HWPX 수집 PR #21 위의 격리 worktree. [Draft PR #22](https://github.com/DigestWorks/IssueDigest/pull/22) 게시·앱 첨부. Sites·개발 인계는 후속 기록한다.
- 상태: domain 문자 검색/위치 단위, PostgreSQL ARRAY/GIN 후보·명시 투영 재생성, 현재 세션/회원 보호 SDK 구현. 작업 리뷰의 메모리 보관·긴 출처 식별자·일반 문서 페이지 정보 세 항목을 f5e3314에서 assertion RED8개 후 보완했다. 수정 범위 재검토에서 세 항목 해결·새 지적0으로 승인받았다. 독립 전체 변경 리뷰도 Critical/Important/Minor0으로 승인받았다.
- 검증: 최종 코드f5e3314의 controller 전체 Python1,787+JS322=2,109개, Ruffformat152/mypy67/ESLint/TS/SPA/OpenAPI 통과, skip/warning0. 실제 HWPX3개·문자 검색9건/전체 셀6건을 별도 DDL 금지·원문 UPDATE 없는 앱 역할로 다시 대조, 반환 위치 matched/not_evaluated·반복3회 unchanged·필터/권한/세션 폐기·미색인1건 표시·SQL @>/GIN 확인. 작은 실자료 위치 검사이며20문항 평가·대규모 성능/메모리 실측이 아니다.
- 범위: 같은 검색 단위에서 literal terms AND·ASCII 대소문자 비교, 출처/수집 시각 필터. 원문은 변경하지 않으며 이전 전체 투영을 후보별로 쌓아두지 않는다. 일반 문서는 전체 본문 TextQuoteSelector, PDF는 실제 PageSpan·셀은 전체 셀. 본문 있는 application/pdf에 페이지 정보가 없으면 재파싱 전 색인하지 않는다. 큰/빈 셀·후보/결과 한도·미투영 자료가 완전성을 제한한다.
- 후속: 보호 검색 API·화면, pgvector 의미 검색·재순위화·관계 검색·검색/AI20문항 평가·DBOS/outbox 소비. 인계 중 새 앱 설정 파일을 확인했고 소유자/비공개 권한·실제 대상 DB·DDL 없는 앱 역할·PostgreSQL18.6/pgvector0.8.7를 읽기 전용으로 검증했다. 기본 PostgreSQL URI를 메모리에서 psycopg 형식으로 바꿔 연결했으며 설정 파일을 수정하지 않았다. 실제 DB에는 기존 앱/검색 스키마가 아직 없고 초기 마이그레이션·백업/복구 조건 확인·자료 등록은 후속이다. 실제 승인 계획/초대·공동 DB·Google 로그인·공유 checkout·운영 서비스·main·공개 앱은 변경하지 않았다.
- CI: [0fa92fa 검사 성공](https://github.com/DigestWorks/IssueDigest/actions/runs/38524891935). 제품 코드f5e3314 이후는 문서 변경이며 실제 전체 검사와 별도로 구분한다.
- Sites: [v41 근거 검색](https://lawdigest-rebuild-plan.ijaesinii.chatgpt.site/#evidence-search) 공개 게시 native succeeded, v40 보존. source `ea23ba32934dbea7cd8c1b1d656ded35a765fdad`, saved `appgprj_6ac612dd42708191a7a0c8377be64d48~appgver_a7cde360ec2481918849e55e66667d45`, deployment `appgdep_6acf290e1be88191b143cdb50b03b006`. 사본 기준f89b1bc·HTML26/로컬 링크·anchor523/manifest·공개 파일289개의 실제 비밀값/계정/인용/내부 ID 제외 검사 통과. SDK와 앱/의미 검색/평가 미완료를 구분했다. 문서 요약 변경의 새 브라우저 화면 검사는 수행하지 않았으며 브라우저 열기 요청은 queued였다.
- 추가 게시: 인계 중 새로 확인한 앱 DB 읽기 접속/DDL 없는 역할·앱 테이블 미적용 상태를 v42에 반영했다. source `a1406c41238de6d9a58c701542b715d712edf16b`, saved `appgprj_6ac612dd42708191a7a0c8377be64d48~appgver_87a9b38c6ae08191b81d7979e44a641e`, deployment `appgdep_6acf2c2221f4819198af9813ada04620` native succeeded/public. 사본 기준842af02·v41 보존·HTML27/로컬 링크·anchor560/공개 파일290개·비밀값 제외 검사 통과. 이후 상태는 저장소 원본을 따른다.
- 정리·인계: 소유 검증 컨테이너의 전체 ID·이미지·label·실제 loopback binding 대조 후 해당 컨테이너/익명 볼륨만 제거했다. 미병합 검토 worktree/RED·GREEN·리뷰/개인 근거는 보존한다. 현재 폴더와 서버 개인 worktree를 feat/evidence-search·origin 추적으로 연결하고 locked 설치/SDK 무DB import를 확인했다. ARM 검색 도메인34개·mypy67개 통과. 웹/API 코드 화면은 바꾸지 않았으며 공동 DB/로그인/서비스/main·공개 앱은 미연결이다.

## 이전 작업 · HWPX 수집 작업·등록 계획 연결

- 작업: [수집 작업 명세](../changes/hwpx-import.md), R2/R3·D011/D015. 파일 snapshot을 기존 파서/정확 인용 계약으로 준비하고 승인된 등록 계획에 추가한다.
- 담당/브랜치: controller·implementer, `feat/hwpx-import`; HWPX 파서 PR #20 위의 격리 worktree.
- 상태: worker 패키지의 준비 함수·명시 명령 구현·검증 완료. 실제 첨부3개/정확 인용9개를 준비해 기존 합성 자료1개/초대2개를 보존하는 계획을 만들고 전용 검증 DB의 기존 CLI 검사/등록/반복/재조회까지 확인했다. 작업 리뷰의 JSON 직렬화 전 한도1건을9511d78/7090d72에서 입력·파생 결과의 구조/바이트 예비 검사로 보완하고 재검토에서 해결·새 지적0을 확인했다. 최종 코드7090d72 전체 Python1,703+JS322=2,025개·format145/mypy63/TS/빌드/계약 통과, skip/warning0. 정상 자료의 출력 byte 동일·기존 CLI 등록/반복/재조회도 다시 확인했다. 독립 전체 변경 리뷰 Critical/Important/Minor0으로 승인. [Draft PR #21](https://github.com/DigestWorks/IssueDigest/pull/21) 게시·앱 첨부. Sites v40 공개 게시·개발 인계 완료. 기본 실행은 비공개 artifact 준비이며 DB 적용은 기존 등록 도구의 명시 실행으로 분리한다. SDK/CLI 준비를 DBOS 런타임·주기 수집 완료로 표시하지 않는다.
- Sites: [v40 HWPX 수집 작업](https://lawdigest-rebuild-plan.ijaesinii.chatgpt.site/#hwpx-import) 공개 게시 native succeeded, v39 보존. source `b15a694fd3279270721e5cbe799d352d48ead68a`, saved `appgprj_6ac612dd42708191a7a0c8377be64d48~appgver_5a7dc517fc0c819180c94b1c5a7bd612`, deployment `appgdep_6acf1692cc6881919e854f432bff5f61`. 사본 기준d5581e6·HTML25개/로컬 링크·anchor487개/manifest·실제 비밀값/계정/인용/해시/UUID 제외59파일 통과. 새 브라우저 화면 검사는 수행하지 않았고 열기 요청은 queued였다.
- 인계: 사용자 폴더와 서버 개인 worktree를 `feat/hwpx-import`/origin 추적으로 연결했다. c6806b2에서 같은 코드·깨끗한 Git 상태·locked worker 설치·실제 준비 명령 --help 실행을 확인했다. 공개/공용 checkout·앱 runtime·DB는 변경하지 않았다.
- CI: [구현/검토38b920e 검사 성공](https://github.com/DigestWorks/IssueDigest/actions/runs/38517871947), [PR 링크 포함d5581e6 검사 성공](https://github.com/DigestWorks/IssueDigest/actions/runs/38517965438). 이후 게시/인계 문서만 바뀐 커밋의 exact-head 결과와 구분한다.
- 정리: 전체 ID·이미지·loopback 포트·소유 label을 대조해 검증용 DB 컨테이너/익명 볼륨을 제거했다. 개인 검증 입력/원문/산출물은700/600, 미병합 검토 증거는 보존한다.
- 실제 연결: 서버 앱 접속 설정은 이번 읽기 확인에서도 부재. 동료에게 이미 전달한 설정/백업 요청은 유지하며 새 확인 질문은 하지 않는다. 공동 DB·실제 초대·Google 로그인·공개 앱은 변경 전이다.

## 이전 작업 · HWPX 본문·표·인용

- 작업: [HWPX 명세](../changes/hwpx-evidence.md), R2/R3. 첫 이슈의 핵심 첨부를 기존 근거 계약으로 연결한다.
- 담당/브랜치: controller·implementer, `feat/hwpx-evidence`; 첫 자료 풀 PR #19 위의 격리 worktree. 본문 구역 순서·표/셀 주소·병합·단위 문구를 보존하며 의미를 추정하지 않는다.
- 상태: 로컬 bytes·기대 해시 기반 HWPX 파서와 기존 계약 어댑터 구현. 본문 구역/표·셀 주소·병합·중첩·단위 문구를 보존한다. 구역과 머리말을 혼동한 실제 파일 경계는 합성 회귀 사례로 보완했다. 독립 작업/전체 변경 리뷰 승인. ZIP64 지원 범위 문구1건을9a3ce66에서 보완하고 재검토에서 해결·새 지적0으로 승인받았다. [Draft PR #20](https://github.com/DigestWorks/IssueDigest/pull/20) 게시·앱 첨부. Sites v39 공개 게시·개발 인계 완료.
- 검증: 코드169d109에서 전체 Python1,615+JS322=1,937개·Ruff/format137/mypy57/TS/SPA/계약 통과, skip/warning0. 실제 첨부3개·표34개·셀278개의 XML 구조/범위와 인용281개를 대조했고 전용 검증 DB 저장/재실행/동일 조회·다른 공간 격리 확인. 문서 예제의 포맷 오류는169d109에서 수정한 뒤 전체 검사했다.
- 한계: CLI/worker·공동 DB·로그인/화면 연결은 후속. 단위/기간은 셀 문구로 보존하며 추정 메타데이터는 넣지 않는다. Q05/Q06의 의미/단위/합산 판정과 검색/AI 평가 실행·적격30~50개 코퍼스는 미완료다.
- Sites: [v39 HWPX 자료 읽기](https://lawdigest-rebuild-plan.ijaesinii.chatgpt.site/#hwpx-evidence) 공개 게시 native succeeded, v38 보존. source `32a30aeb758b03131a68f90772a99d954543c35e`, saved `appgprj_6ac612dd42708191a7a0c8377be64d48~appgver_a17d6662b7388191b2fbe90456e8a19a`, deployment `appgdep_6acf05011cf081918879fb001244e527`. 사본 기준7724f02·HTML24개/로컬 링크·anchor453개/manifest·실제 비밀값/계정/인용/해시/UUID 제외57파일 통과. 새 브라우저 화면 검사는 수행하지 않았고 열기 요청은 queued였다.
- 인계: 사용자 폴더와 서버 개인 worktree를 `feat/hwpx-evidence`/origin 추적으로 연결하고 cd45e04 코드·locked 의존성·HWPX 모듈 로딩·깨끗한 Git 상태를 확인했다. 공개/공용 checkout·앱 runtime·DB는 변경하지 않았다.
- CI: [구현·검토 b4aba72 검사 성공](https://github.com/DigestWorks/IssueDigest/actions/runs/38511445562), [PR 링크 포함7724f02 검사 성공](https://github.com/DigestWorks/IssueDigest/actions/runs/38511501704). 이후 게시/인계 문서만 바뀐 커밋의 exact-head 결과와 구분한다.
- 운영 경계: 소유 컨테이너의 전체 ID·이미지·loopback 포트를 대조해 검증용 DB/익명 볼륨을 정리했다. 기존 자료/공동 DB·실제 로그인·AI·main·공개 앱은 변경하지 않는다.

## 이전 작업 · 첫 이슈 자료 풀·평가 질문

- 작업/범위: [자료 풀 기록](../research/first-issue-corpus.md)·[출처45개](../research/first-issue-sources.tsv)·[질문20개](../../tests/evaluation/first-issue.md), R2/R3/R4. 기존 지방국립대 등록금 지원 이슈를 유지하고 정부안·기존 제도·관점/확정 근거 부재를 구분한다.
- 담당/브랜치: controller, `docs/first-issue-corpus`; 선행 등록 도구 위의 격리 worktree. 문서/조사 작업이며 제품 코드·스키마·API·의존성·공동 DB·운영은 변경하지 않는다. [Draft PR #19](https://github.com/DigestWorks/IssueDigest/pull/19) 게시·앱 첨부. Sites v38 공개 게시 완료.
- 결과: 공식 후보45개, HTTPS 응답 스냅샷38개 개인 보관. 라이선스 표시/100자 이상 텍스트13개 중 재게시1·다른 부처 대조자료1을 제외한 관련11개와 참고 법령 조문3개로 초기 연구 풀14개를 구성했다. 핵심4·배경10, 기존 앱 파서 지원3개. 첨부 안내38자2개와 접근/로봇 규칙 확인 대기7개를 실제 사용 가능한 자료로 세지 않는다. 현재 풀은 정부 자료 중심이며 반대 성명/회의록/확정 자료가 없다.
- 평가: 답변형15·자료 부족4·합성 지시 공격1, 총20개 질문/필수 근거/기대 화면/판정 기준 정의. 텍스트 위치·앞뒤 문맥 후보26개가 기존 Citation 계약에 일치했다. 지지 판정은 not_evaluated, 실행0·점수 없음. Q05의 목록 구조·Q06의 수치 표는 별도 검증이 필요하다.
- 검증: 출처45행·응답38개 해시·연구 풀14개/앱 파서3개·문항20개·인용 계약26개·문서 상대 링크78개·개인 권한700/600·공개 파일8개의 실제 비밀값/계정/인용 제외·git diff --check 통과. 제품 코드 변경이 없어 기존 c12e18e의1,919개 CI를 기준으로 삼고 전체 검사를 수동 반복하지 않았다. 검색/AI 평가 실행은0이며 문서 검증과 구분한다.
- 다음: 핵심 HWPX 본문·표/단위/출처를 생산용 파서에 연결하고, 직접 성명·국회/정확 통계와 재사용 조건을 추가 확인한다. 검토된 실제 코퍼스30~50건과20문항의 검색/AI 실행·품질 점수는 미완료다. 앱 접속 설정/백업·실제 등록/Google 로그인 대기와 독립적으로 진행했다.
- Sites: [v38 첫 이슈·평가](https://lawdigest-rebuild-plan.ijaesinii.chatgpt.site/#first-issue-evaluation) 공개 게시 native succeeded, v37 보존. source `0842dbe5b3ec55f4790008134c901f1d013133d6`, saved `appgprj_6ac612dd42708191a7a0c8377be64d48~appgver_17ef7d53d0008191bf13503a89181555`, deployment `appgdep_6acefdd94e388191988ffbecd4a9a103`. 사본 기준c62b3af·HTML23개/로컬 링크·anchor420개/manifest·공개 파일55개의 실제 비밀값/계정/인용 제외 통과. 새 브라우저 화면 검사는 수행하지 않았다. 원문·전체 인용·개별 해시/UUID·실제 계정·접속정보는 공개 기록에 포함하지 않는다.

## 이전 작업 · 공동 공간의 자료·접근 허용 등록

- 작업/범위: [등록 도구 명세](../changes/workspace-bootstrap.md), R1/R2·D015. 검증한 근거와 승인 계정의 초대를 함께 등록하고, 실패 시 전체 취소·재실행 시 중복 방지를 제공하는 운영자 CLI. 로그인·권한·근거 계약은 유지한다.
- 담당/브랜치: controller·implementer, `feat/workspace-bootstrap`; 선행 Google OAuth 위의 격리 worktree. 최종 검증·독립 리뷰 완료, [Draft PR #18](https://github.com/DigestWorks/IssueDigest/pull/18) 게시·앱 첨부. main 미병합, Sites·개발 인계 완료.
- 현재 상태: 자료/초대 Connection helper와 비공개 입력 검증·대상 읽기 검사·명시 등록 CLI를 구현했다. 같은 트랜잭션의 전체 취소·중복 방지·기존 초대 상태 보존을 검증했다. helper·CLI 작업 검토와 수정 재검토, 전체 변경 검토·최종 문서 보완 재검토를 모두 승인받았다. CLI 리뷰의 연결 정리 로그/성공 오판·무호출 테스트 지적2개와 최종 초대 행 잠금 UPDATE 권한 안내를 보완했다. 열린 지적은 없다. 새 HTTP 등록 API·자동 가입·자동 마이그레이션은 추가하지 않는다.
- 검증: 최종 코드22ede20에서 전체 Python1,597+JS322=1,919개·Ruff/format/mypy56/TS/SPA/계약 통과, skip/warning 없음. 별도 합성 CLI의 검증/읽기/최초 등록/반복→실제 서명 검증 SDK의 고정 MockTransport→두 계정 동일 자료 목록/원문/인용·다른 공간/미초대 차단·로그아웃 결합 검사1개 통과. 이 검사는 실제 Google 네트워크 로그인·브라우저 검사와 다르다. 초기 QA는 미정규화 fixture를 기대값으로 써 실패했고, 기존 EvidenceBundle의 정규화 결과와 비교하도록 QA만 수정해 통과했다.
- 실제 준비: 캐시의 공식 원문을 기록된 해시·이용 조건·본문·인용3개와 재대조했다. 새 공유 공간의 예약 ID와 승인 계정1개/자료1건의 개인 등록 계획을600으로 보관했다. 새 도구 기본 모드에서 개인 계획의 오프라인 검증도 통과했다. 원문 재수집·실제 DB 등록·계정 바인딩·실제 로그인 완료는 아니다.
- 서버 확인: 일시적인 SSH/GitHub 연결 실패 후 재접속했다. 전용 PostgreSQL18.6/vector0.8.7·앱 근거/인증 테이블0개, 기존 앱 접속 설정 파일 부재를 읽기 확인했다. 공동 DB·서비스·권한은 변경하지 않았다. 사용자는 기존 앱 접속 설정 위치/전달과 백업 시각·복구 방법을 동료에게 요청하겠다고 답했다. 실제 준비 완료로 간주하지 않는다.
- 다음 조건: 도구 검증은 완료했다. 실제 앱 계정/대상/필요 권한·백업 조건이 확인되면 명시 스키마 준비·등록과 사용자 실제 로그인으로 이어간다. 두 번째 계정은 미정이며 개발자 DDL 계정을 앱 runtime에 쓰지 않는다. 공개 앱·main 병합은 D013에 따라 유예한다.
- CI: [ac68478 검사 성공](https://github.com/DigestWorks/IssueDigest/actions/runs/38502605190), 구현 코드22ede20·독립 리뷰 및 보완 문서 포함. 이후 게시/인계 기록만 변경한 커밋의 결과와 구분한다.
- 인계: 현재 폴더를 `feat/workspace-bootstrap`으로 연결하고 locked 의존성/개인 입력의 기본 오프라인 검사1초대/1자료를 확인했다. 서버 개인 worktree도 해당 브랜치 origin 추적·코드를 fast-forward, 프로젝트 전용 환경을 선택한 ARM operator 모듈 로딩·mypy56 통과. 기본 미설정 앱을 유지하며 실제 DB/OAuth runtime에 연결하지 않았다. 테스트 DB의 전체 ID·실제 loopback 할당·이미지를 대조해 소유 컨테이너/익명 볼륨을 제거했다. 미병합 검토 worktree·RED/GREEN/리뷰/결합 증거는 보존한다.
- Sites: [v37 등록 준비](https://lawdigest-rebuild-plan.ijaesinii.chatgpt.site/#workspace-bootstrap) 공개 게시 native succeeded, v36 보존. source `32bbde3e40d69685888f21bd35fcf0e65d4a1527`, saved `appgprj_6ac612dd42708191a7a0c8377be64d48~appgver_bd0ac4636b648191a14d906b0fd946fa`, deployment `appgdep_6aceecf9c850819194c66e02f31cd646`. 사본 기준ac68478·HTML22/로컬 링크·anchor388/manifest·실제 비밀값/계정/인용/내부 ID 제외 검사 통과. 문서 갱신의 브라우저 화면 검사는 수행하지 않았고 브라우저 열기 요청은 queued였다. 현재 원본의 이후 게시/인계 기록과 사본 기준을 구분한다.

## 이전 작업 · Google 로그인·공동 조사 자료 진입

- 작업: [Google OAuth·공동 조사 자료 진입](../changes/google-oauth-workspace.md), R1/R2·D015. 명시 초대·Google 고정 identity·서버 세션·현재 권한과 공동 자료 목록을 연결했다.
- 담당/브랜치: controller·implementer, `feat/google-oauth-workspace` · [Draft PR #17](https://github.com/DigestWorks/IssueDigest/pull/17), 선행 공식 HTML #16 위의 격리 worktree. 최종 CI·게시·개발 인계를 아래 결과로 기록한다.
- 상태: 저장·공급자/HTTP/runtime·웹 세 작업의 독립 검토와 전체 변경 리뷰 승인. 주소의 비표준 표기로 정상 로그인이 차단되는 문제를 startup 거부로 보완했다. 전체 리뷰의 정렬/한도 테스트·OpenAPI 경계값 세 보완을 한 번의 수정 범위로 반영하고 scoped 재검토에서 모두 해결·새 지적 없음으로 승인받았다.
- 검증: 코어 코드 `e61d531`에서 controller 전체 Python1,491+JS320=1,811개·정적/빌드/계약 통과, skip/warning 없음. 인계 중 발견한 개발 포트 전달 오류를 `29a152d`에서 TDD·독립 리뷰로 수정했다. controller 웹322개·lint/타입/SPA/계약과 최종 코드 CI 전체 Python1,491+JS322=1,813개가 통과했다. 별도 실제 PostgreSQL·DDL 금지 앱 역할·개인 HTTPS·브라우저에서 합성 서명/두 계정의 로그인→자료 목록→원문/인용→로그아웃, 미초대 차단·실패 로그인 시 기존 세션 유지 확인. 데스크톱1366/모바일390에서 가로 넘침 없음·page error0. 브라우저의 이동 중/bfcache 보류 실험은 완료하지 못했으며 해당 동작은 컴포넌트 테스트 범위로 남긴다. 실제 외부 Google 로그인으로 표현하지 않는다.
- 남은 입력: Google 클라이언트 JSON 필수 항목·개발 callback 일치/개인 보관600 확인. 실제 Google 로그인·테스트 사용자 등록 여부·기존 앱 전용 DB 계정의 비밀 설정/필요 테이블 권한·두 번째 Google 계정은 미확인. 앱 접속 설정은 최신 개인 서버 조회에서도 없거나 읽을 수 없다. 승인 계정은 저장소 밖 미등록 기록만 있으며 공동 DB를 변경하지 않았다.
- 다음: 기존 앱 계정의 비밀 설정을 받아 역할/대상·백업 조건을 확인한 뒤 새 공유 공간·명시 초대·검증한 공식 원문을 이관한다. 실제 Google 로그인은 사용자가 확인한다. 스키마 변경용 계정을 앱 실행에 사용하지 않는다.
- 인계: 사용자 폴더를 `feat/google-oauth-workspace`로 연결하고 고정 의존성을 설치했다. 격리 검토 폴더는 해당 코드의 detached 상태로 보존한다. 개인 서버 worktree도 같은 코드·upstream으로 연결했다. ARM Google/설정/runtime103개 통과·공동 DB 미사용에 따른 조건부 PostgreSQL1개 skip, launcher13개·mypy54/웹 타입/SPA/계약 확인. 지정 개인 웹/API의 헬스·상태·로그인 화면200 및 API 계약 일치를 확인했다. 기본 미설정 runtime을 유지하며 실제 OAuth/공동 DB를 연결했다고 표시하지 않는다. 소유 합성 DB/볼륨·브라우저·QA API/웹은 정리했다.
- CI: [최종 코드29a152d · 검사 성공](https://github.com/DigestWorks/IssueDigest/actions/runs/38402405745). 작업/전체/수정 및 실행 포트 보완 리뷰 모두 승인. 후속 문서 커밋의 exact-head 결과는 PR에서 확인한다.
- Sites: v35 공개 게시 성공·v34 보존, source `3648837847e5c1b3d87dfa9294c27d0e00435153`, saved `appgprj_6ac612dd42708191a7a0c8377be64d48~appgver_2d7136cfed788191b8db582803e0b301`, deployment `appgdep_6ace29a304e481919c5beaa7ac6cd541`. 서버 포트 보완·최종 인계/1,813개 CI 결과를 [v36](https://lawdigest-rebuild-plan.ijaesinii.chatgpt.site/#google-oauth)에 게시했다. source `bffe1117e1759197d42f80d327f38c505b55205a`, saved `appgprj_6ac612dd42708191a7a0c8377be64d48~appgver_40148f188db08191a3d05c5dd9f8f75f`, deployment `appgdep_6ace2f6a61a08191a457f2c32f876211` native succeeded/public. v35도 보존했으며 사본 기준2911619·HTML21/로컬링크·anchor358/manifest/공개 비밀값 제외 검사를 통과했다. 계획 문서의 새 브라우저 화면 검사는 수행하지 않았다. 현재 원본의 이후 게시 기록과 사본 기준을 구분한다. 공개 앱·main 병합은 D013에 따라 유예한다.

## 이전 작업 · 공식 정책 HTML 원문 준비

- 작업: [공식 정책 HTML 원문·인용 준비](../changes/official-html-evidence.md), R2/P2. 첫 이슈 정부 자료의 본문·발행일·출처표시 조건을 실제 원문과 대조한다.
- 담당/브랜치: controller·implementer, `feat/official-html-evidence` · [Draft PR #16](https://github.com/DigestWorks/IssueDigest/pull/16); 선행 근거 읽기 #15 위, main 미병합.
- 상태: HTML 제한 추출·메타데이터/이용 조건·기존 표현/인용 어댑터 구현b3febab, 독립 리뷰 P1 caller-ID 오류 노출을 assertion RED11개 후 fixed AuditError로 보완47394b2, scoped 재검토 해결·새 지적0. 실제 정부 원문35문단/3,231자·정확 인용3개·저장 재조회 검증. 서버 개인 공간에도 원문/메타데이터/검증 산출물5개600·디렉터리700/내용 동일로 보존했다. 검증용 workspace/snapshot은 실사용 승인 계정/공간이 아니다. 전체 원문·인용·hash/ID는 공개 기록에 복제하지 않는다.
- 검증: focused150개·controller 최종 전체 Python1,277+JS233=1,510개 및 정적/빌드/계약 검사 통과. 초기 assertion RED122개와 보완 RED 보존. 실제 정부 원문과 독립 브라우저 DOM 본문 동일·외부 요청43건 차단, 전용 검증 DB 최초 저장/같은 재전송 미생성/동일 재조회·두 fixture 사용자 보호 GET200/no-store·비로그인401/다른 공간404. 최종 코드47394b2에서 전체 검사·실제 원문 재추출/메타데이터/인용/저장 재열람 확인. 독립 전체 변경 리뷰52e0377 승인·Critical/Important/Minor0.
- 범위: 원문 사진/이미지·캡션·메뉴/AI요약 제외, 이용/파서/정규화 기록. 공동 작업용 DB 적재·실제 로그인·AI·공개 앱은 후속이다. 기존/운영 DB나 공용 서비스를 변경하지 않는다.
- 다음: Draft PR·Sites·개발 인계 결합을 마친 뒤 실제 작업 공간/로그인·선별 원문 수집·AI 결과 연결로 진행한다. 실제 앱 공개·main 병합은 D013에 따라 유예한다.
- Sites: v34 공개 게시 완료·v33 보존. 첫 공식 원문/정확 인용·개인 검증 DB/합성 사용자/실제 공동 DB 후속을 구분했다. HTML19개/로컬 링크·anchor301개·manifest/접속정보 제외·공백 검사 통과. 문서 요약 변경의 브라우저 레이아웃 검사는 반복하지 않았다.
- 게시 증거: source `50aa3605f82c40334cf082d00641c8e666f1b322`, saved version `appgprj_6ac612dd42708191a7a0c8377be64d48~appgver_c9da071b39148191b71a6216026e47c0`, deployment `appgdep_6acdfcf7f80c8191a272031d0c74b8a4` native succeeded·URL 확인, 기존 공개 설정 유지. 사본 기준d7f9766. [CI #38377896184](https://github.com/DigestWorks/IssueDigest/actions/runs/38377896184) exact d7f9766 성공. PR #16 앱 첨부 완료.
- 개발 인계: 현재 폴더와 서버 개인 worktree d7f9766·깨끗함 확인, 서버 origin/feat/official-html-evidence 추적·locked 설치/ARM HTML150개/mypy45개 통과. 원문/산출물5개600 서버 개인 보존·내용 일치 확인. 마지막 게시 기록 커밋도 개인 worktree에 fast-forward한다. 공유 저장소/운영 DB/서비스 변경·main 병합·앱 배포 없음.
- 정리: 소유한 전용 검증 DB 컨테이너만 전체 ID 대조 후 제거했다. 개인 원문/메타데이터/검증 bundle은 보존하며 실제 서비스 DB 저장 상태로 표현하지 않는다. 자체 오프라인 브라우저 세션은 닫았다. 미병합 검토 worktree/RED·GREEN·리뷰/검증 로그는 보존한다.

## 이전 작업 · 저장 근거 읽기 화면

- 작업/관련 단계: [보호 근거 읽기 화면](../changes/evidence-reader.md), R1/R2/R4의 웹/API 소비 부분. 사용자 D013에 따라 공개 앱 배포 유예.
- 담당/브랜치: controller·implementer, `feat/evidence-reader` · [Draft PR #15](https://github.com/DigestWorks/IssueDigest/pull/15), 선행 #14 위·미병합. 별도 격리 worktree이며 main·공용 배포 checkout은 유지한다.
- 상태: 구현eec0136·리뷰 보완7c13ae8. 같은 출처 보호 GET 소비·display validation·취소/전체 deadline·안전한 오류, 링크 진입·원문/페이지/표/정확 인용 위치 화면 구현. 독립 작업 리뷰의 P2 두 건(페이지 없는 표의 원문 복귀·긴 원문 강조 위치 이동)을 assertion RED3개 후 수정하고 scoped 재리뷰에서 모두 해결·새 지적 없음. 독립 전체 변경 리뷰 승인·Critical/Important/Minor0. 리뷰는 실제 로그인·전체 schema/semantic·운영 감사·실제 이슈 코퍼스/AI/정책 결론·PDF 이미지/전표 재구성·규모/전체 접근성 매트릭스·게시/인계를 완료했다고 판단하지 않았다. 기존 명세·후속 요구사항의 범위와 일치하며 새로운 예외/지적은 없다.
- 검증: 초기 client 실제 namespace assertion RED54개·UI 실제 렌더/폼 RED30개·호환성/키보드/표 선택 RED 보존, 최종 focused103개. controller 최종 전용 loopback 합성 PostgreSQL18.6 포함 전체 Python1,127+JS233=1,360개, skip0·lint/format/mypy/TS/SPA/contract 검사 통과. runtime/서버 계약·generated 타입·의존성/lockfile·운영 DB 변경 없음.
- 실제 브라우저: 합성 PostgreSQL→기존 FastAPI 보호 GET→개인 HTTPS Vite→브라우저. JSON200/no-store, Home 링크 진입·두 fixture 사용자 동일 bundle·비로그인/다른 공간 차단·PDF/text 강조·키보드 표 선택·선택 시 추가 GET 없음, 1366/390·가로 넘침 없음·화면 직접 확인. 긴 합성 원문450문단 뒤쪽 text/PDF 인용은 두 크기에서 최초/반복 선택 후 실제 mark가 viewport 안에 보임. pages=[]·table-only에서도 원문 복귀 확인. JavaScript page 예외0·예상401/404 resource 메시지 외 console 오류0.
- 기록: 원래 assertion RED·QA 실패 로그를 보존했다. 최초 브라우저 journey는 실제 문구와 다른 retry locator를 기다려 실패했으며 DOM 확인 후 QA locator만 수정해 통과했다. 긴 원문 첫 시도는 브라우저 세션이 없어 실행되지 않았고 재개 후 검증했다. 이를 생산 코드 RED라고 주장하지 않는다. fixture/세션·QA 포트/키·이미지는 ignored 개인 영역만 사용하며 공개 앱에 추가하지 않았다.
- 첫 이슈: 사용자 위임에 따라 최근 시사를 검색해 [지방국립대 등록금 지원](../research/first-issue.md)의 대상·재원·형평성을 선정(D014). 대표 질문5개와 원문/보도5개 시작 목록. 실제 코퍼스/평가셋·기사 이용·정부안/확정·인과 검토는 후속이며 이번 합성 UI QA를 이 이슈 자료의 평가로 간주하지 않는다.
- 범위: 같은 출처 보호 GET 소비, 안전한 자료 링크 진입, 원문/페이지/인용 위치와 접근/로딩/오류 상태. 실제 로그인 발급·자료 이관·운영 DB·AI 생성은 후속. 자료/토큰을 브라우저 저장소나 공개 기록에 남기지 않는다.
- 다음 행동: 선정 이슈의 공식 원문·이용/버전·근거 대응 확보와 실제 자료 등록·로그인/AI 연결을 단계적으로 진행한다. 이 읽기 부분은 구현/리뷰/검사/PR/Sites/개발 인계를 마쳤고 전체 최소 제품·운영 준비는 후속이다. 실제 앱 배포·main 병합 없음.
- Sites: v33 공개 게시 완료. 배포 유예·첫 이슈 선정·읽기 구현과 기존 v32 보존을 반영했다. 문서 요약의 브라우저 화면 검사는 반복하지 않았다.
- 게시 증거: Sites source `daf4768e150388d4e7ec031108c8eeae8204826c`, saved version `appgprj_6ac612dd42708191a7a0c8377be64d48~appgver_e00da3bb61a88191a01a7659e314ab45`, deployment `appgdep_6acdefc525a88191aee950652bf0a308` native succeeded·URL 확인, 공개 설정 유지. 사본 기준cc97c87·HTML18개/로컬 링크·anchor274개/manifest/공개 접속정보 제외·문서7개/상대 링크58개 통과. [cc97c87 CI](https://github.com/DigestWorks/IssueDigest/actions/runs/38370950027) 성공. PR #15 앱 첨부 완료.
- 개발 인계: 현재 폴더 `feat/evidence-reader`·서버 개인 worktree의 같은 origin 추적·cc97c87/깨끗함 확인. ARM 타입/웹233개 통과, 개발 웹과 자료 route200·상태JSON200·비로그인 보호GET401 확인. 이번 마지막 문서 기록도 fast-forward하고 동일 HEAD·깨끗함을 확인한다. 리뷰 worktree는 detached로 검증 증거를 보존한다. 운영 서비스·DB·공용 checkout·배포 설정은 유지한다.

## 이전 작업 · PDF 인용 후보

- 작업: [PDF 인용 후보·문맥 선택](../changes/pdf-quote-candidates.md), R2/P2의 다음 부분 구현. 반복 문항의 정확 위치 후보와 페이지/인접 문맥 조건의 유일 선택을 구현한다.
- 담당/브랜치/PR: controller/implementer · `feat/pdf-quote-candidates` · [Draft PR #14](https://github.com/DigestWorks/IssueDigest/pull/14) · 선행 #13 위·미병합.
- 상태: 구현·독립 작업 리뷰·controller 전체 검사·실제 후보 대조 완료, 독립 전체 변경 리뷰 승인·Draft PR #14 게시/앱 첨부·Sites v31 공개 게시 완료. 표/응답 수치·원문 진위·올바른 근거 위치의 의미 판단·제품 화면/운영 DB 연결은 별도다.
- 검증: 같은 비무작위6개에서35문항/87정확 위치,35문항 모두 여러 페이지·4문항은 같은 페이지에서도 반복한다. 각 문항에 유일한 페이지/80자 문맥 매치가 있지만 적합한 조사/표의 위치라는 판단은 하지 않았다. 신규106개·전체Python1,127+JS134=1,261개 및 타입/빌드/계약 검사 통과. 새API의 실제87후보/페이지+문맥round-trip을 검증했다. 제품자동선택/올바른조사·표판정은 하지 않았다.
- 관리자 요청: 실제 전달은 pgvector만, 완료. 별도 DB 로그인 계정 존재 확인. 다른 미전달 제안은 현재 개발의 선행 조건이 아니며 [필요 시점](../../infra/administrator-request.md)에 확인한다. 추가 권한/키/외부 요청 없이 진행한다.
- 다음: 전체 변경 리뷰·PR·Sites·인계를 마무리하고 자료/근거의 실제 조회·선택 흐름에 연결한다. 첫 제품 이슈·자료 이용 조건·표/수치 검증은 별도다. 실제 원문/문맥은 공개하지 않는다.
- Sites: v31 공개 게시 완료, v30을 보존했다. 후보/명시 선택의 위치 검증과 조사/표 의미·제품 화면 연결 후속을 구분했다.

## 2026-10-13 · PDF 인용 후보·문맥 선택

- 구현: af1bd39·작업 체크리스트/명세 cc38d23. 별도 quotes 모듈의 불변 검색 한도/결과·정확 후보 목록·페이지/인접 문맥 resolver를 추가했다. 기존 추출/locator/CLI·도메인/API·생성 타입·의존성은 유지했다. 후보에는 caller 문서/표현 ID·텍스트 해시와 정확한 페이지/문자 위치가 연결된다.
- 동작: 겹치는 매치·페이지 경계·문맥의 페이지 침범도 유일성 판정에서 누락하지 않는다. 기본 text1,000,000자·raw occurrence10,000개·반환 후보100개·앞뒤80자 preview이며 반환 후보 제한 뒤에도 전체 건수를 세고 has_more를 표시한다. 실패/잘린 목록으로 유일성을 추정하거나 첫 위치를 자동 선택하지 않는다. 명시 페이지 요청은 그 PageSpan 길이에 text 한도를 적용한다.
- 검증: 합성 assertion RED43개/교정된 resolver RED55개 후 신규106개 GREEN, ingestion349개. worker/controller 각각 최종 코드에서 전용 합성 PostgreSQL18.6 포함 전체 Python1,127+JS134=1,261개, skip0·린트/format·mypy·TS·SPA·OpenAPI drift exit0. README 예제도 합성 유효 모델/선택 조건과 실제 인용 검증으로 실행했다. 독립 작업/전체 변경 리뷰 승인·Critical/Important/Minor 지적0. 기존 명세의 유효 모델 입력·미평가 의미/권한·운영 제외와 전사 로그 한계를 유지하며 PR/Sites/인계는 controller가 별도 확인한다.
- 기존 회귀: 원본 보존 테스트가 전체 stat의 atime(읽기 접근 시각)까지 비교하여 초 경계에서 실패했다. 읽기 후에도 bytes·dev/ino/mode/size/mtime_ns/ctime_ns를 비교하도록 이 assertion만 정정했다. PDF 생산 코드는 변경하지 않았다. 원래 전체 실패 로그는 덮어써졌고 관측 실패의 명시적 전사 발췌만 남아 있음을 보고서에 기록했다. 해당 테스트·ingestion·전체 gate는 정정 후 통과했다.
- 실제 대조: 같은 비무작위 소표본6개/35문항, 추출은 PDF당 wall15초로 제한했다. 새API가 정확 위치87개를 반환했고87개 모두 기존 validate_citation의 anchor matched/support not_evaluated를 통과했다. 기본 문항만 요청하면35개 모두 quote_ambiguous, 후보의 페이지로만 제한하면75회 matched/12회 ambiguous였다. 후보별 명시 페이지+앞뒤 원문 문맥으로87회 모두 동일 위치 round-trip 통과, 각35문항에 하나 이상의 유효 round-trip이 있었다. 반환 후보1개로 제한한35회도 총수/has_more를 유지했다.
- 해석 경계: 모든 후보를 QA 조건으로 대조했으며 적합한 조사/표 위치를 고르거나 제품에서 자동 선택하지 않았다. 테스트용 caller UUID는 저장된 문서 버전이 아니다. 위치 일치·선택 가능성과 원문 진위·조사/표 대응·응답 수치·주장 지지를 구분한다. 전체225개 품질로 일반화하지 않는다.
- 보호: 실제 문항/문맥·텍스트·경로·해시·UUID는 개인 환경 밖으로 내보내지 않고 집계만 기록했다. operating DB·원문·공유 서비스·DNS·모델 호출/새 의존성 변경 없음. 추가 관리자 요청 없음. 테스트 migration은 명시적인 전용 로컬 합성DB에만 실행했다.
- 게시: [Draft PR #14](https://github.com/DigestWorks/IssueDigest/pull/14) 생성·앱 첨부 완료, 선행 #13 위·미병합. [46a9d20 CI](https://github.com/DigestWorks/IssueDigest/actions/runs/38342927912) 성공. Sites v31 게시와 현재 폴더/서버 사용자 전용 worktree의 867f2df 인계를 확인했다. 실제 제품 화면/운영 DB 배포는 수행하지 않았다.
- Sites: [v31 공개 게시](https://lawdigest-rebuild-plan.ijaesinii.chatgpt.site/#quote-candidates) native succeeded·URL 확인, 공개 설정 유지. source `b9828cc9e0143db890d9fcb742a2876859904a52`, saved version `appgprj_6ac612dd42708191a7a0c8377be64d48~appgver_f818301f172c819194d781e919ca2920`, deployment `appgdep_6acda94ad80c8191a864aebadc8d8efd`. 사본 기준867f2df·이전v30 보존·HTML16개/로컬 링크·anchor224개/manifest/공개 접속정보 제외·문서6개/상대 링크64개·git diff --check 통과. 실제 원문/문항/문맥·개별ID/해시는 미게시. 문서 변경의 브라우저 화면 검사는 수행하지 않았고 사이트 탭 열기는 queued 접수다.
- 인계: 현재 폴더 feat/pdf-quote-candidates·서버 사용자 worktree 같은 origin 브랜치 추적. 867f2df에서 locked 설치·실제 finder/resolver import·Git 깨끗함을 확인했다. 게시 기록까지 포함하는 마지막 문서 커밋도 fast-forward하고 최종 응답 전에 같은 HEAD/깨끗함을 확인한다. 앱 프로세스 재시작·운영 데이터/공유 서비스 변경 없음. 미병합 리뷰/RED·GREEN 증거는 격리 폴더에 보존한다.


## 2026-10-13 · pgvector 완료·관리자 요청 정정

- 사용자 정정: 실제 전달 요청은 pgvector만이다. 이전에 세 항목 전체를 전달/답변 대기로 기록한 것은 잘못된 추정이었다. 앱 계정/백업·운영/도메인은 미전달 제안으로 정정하고 구현 차단 항목에서 제외한다.
- 동료 보고: PostgreSQL18.6 유지·pgvector0.8.7 설치/활성화, 개발자/앱 계정 연산·HNSW 검색 검증, 재생성 유지용 Dockerfile/Compose/초기화 SQL·이미지 빌드·DB 백업 반영·재시작 없음.
- 직접 확인: 기존 DB helper의 읽기 전용 transaction에서 server18.6/vector0.8.7/public·L2/코사인 연산 정상, 별도 프로젝트 로그인 계정1개(non-superuser/non-owner/CONNECT), public 앱 테이블0개. 비밀값·계정명은 미출력. 앱 계정 실제 로그인/상속/테이블 권한·HNSW/재생성·백업 복원은 직접 검증하지 않았다.
- 필요한 시점: 앱 계정은 신규 생성 대신 기존 계정을 앱 연결 때 확인한다. 정기 백업/서버 밖 사본·복원은 보존할 사용자 작업 저장 전에 준비하되 기존 구성 우선이다. 서버 부하는 개발자가 실측, 새 자원은 부족할 때만 요청한다. IssueDigest 실제 부담 비용은 운영 전, DNS/프록시는 두 사용자 앱 제공 시점에 확인한다. 지금 새 서버·유료 저장소·관리자 권한 요청은 없다.
- 근거·상세: [관리자 요청 상태](../../infra/administrator-request.md). 이번 변경은 문서/읽기 전용 확인이며 운영 DB·앱 코드·권한·백업·DNS·공유 서비스 변경이나 외부 메시지 발송 없음. 검색 기능·한국어 품질·운영 준비 완료로 표시하지 않는다.
- 게시: 기존 [Draft PR #13](https://github.com/DigestWorks/IssueDigest/pull/13)의 문서와 설명을 갱신했다. [Sites v30](https://lawdigest-rebuild-plan.ijaesinii.chatgpt.site/) native succeeded·공개 설정 유지. source `f6edd927796a800929162402c0000d2314213bdb`, saved version `appgprj_6ac612dd42708191a7a0c8377be64d48~appgver_ca6cf7d80f3c8191a36c6419298b8066`, deployment `appgdep_6acd9e30126c8191bacaae370b582ea6`. 사본 기준212bf18·이전v29 보존. 문서5개/상대 링크20개·HTML15개/로컬 링크·anchor202개·수치/공개 접속정보 제외·git diff --check 통과. 문서만 변경하여 코드 전체 테스트·브라우저 화면 검사는 반복하지 않았다. 마지막 게시 기록도 서버 사용자 전용 worktree로 fast-forward하고 깨끗함을 확인한다.

## 2026-10-13 · PDF 페이지 텍스트·정확 인용 준비

- 구현: `c778b80`, 문서 예제 형식 보완 `fce7a41`. pypdf6.20.1 고정, 원본 해시 확인 후 익명 복사본만 제한된 Linux 자식 프로세스에서 파싱한다. 페이지 텍스트·빈 페이지·code-point 구간을 기존 ParsedRepresentation/PdfQuoteSelector 계약에 연결했다. DB/API·생성 타입 변경 없음.
- 인용: 한 페이지 안의 정확하고 유일한 문자열만 선택한다. 반복·겹침·페이지 경계·파싱/한도 실패를 고정 오류로 거부한다. validate_citation의 anchor matched와 support not_evaluated를 구분한다. 표 구조·좌표·OCR·출처 진위·조사 대응·수치/주장 지지를 추정하지 않는다.
- 검증: 합성 assertion RED/GREEN과 ingestion243개(신규133개)를 구현했다. controller 첫 전체 검사는 늦게 편집된 README 코드 예제의 형식 오류로 중단됐다. 예제만 보완한 최종 코드에서 전용 합성 PostgreSQL18.6 포함 전체 Python1,021+JS134=1,155개, skip0·린트/format·mypy·TS·SPA·OpenAPI drift exit0. 독립 작업/전체 변경 리뷰는 승인·Critical/Important/Minor 지적0. 범위 밖인 원문/수치/표/OCR·전수 품질·첫 이슈/이용 권리·OS sandbox를 완료로 표시하지 않는다. PR/Sites/인계는 controller가 별도 검증한다.
- 실제 대조: 2026-10-13 UTC, 서버의 기존 후보225개를 parsed 상대 경로 순으로 정렬하고 서로 다른 PDF 해시의 첫6개를 선택했다. 추출 성공 여부/크기에 따른 재선택 없는 비무작위 소표본이며 전체225개 품질로 일반화하지 않는다. PDF당 wall15초로 제한, 6개 모두 성공·92페이지·빈 페이지0·텍스트94,535 code points. 개인 환경에서 기존 question_text35개를 정확 대조했고 전부 quote_ambiguous였다. 자동 확정 인용0개이며 실패를 성공으로 바꾸거나 fuzzy/공백 정규화를 사용하지 않았다.
- 별도 위치 확인: 추출한 각 PDF의 첫 비어 있지 않은 페이지에서 최대80 code points를 명시 페이지로 선택한 probe6개는 기존 인용 검증 matched/support not_evaluated를 통과했다. 임시 호출자 UUID만 사용했고 실제 저장된 문서 버전이나 기존35문항의 인용으로 표시하지 않는다.
- 출력: 실제 installed inspect-pdf도 집계만 반환했고 opt-in 추출 텍스트/메타데이터는 원문·Git 밖 개인 폴더의 새600 파일에 저장했다. 원문·질문·해시·경로·URL·UUID를 공개 기록/Sites에 넣지 않는다. 기존 원문·운영 DB·공유 서비스·DNS 변경이나 모델 호출 없음. 원격 직접 shell CLI 도움말은 venv PATH 미설정으로 exit127이었고 uv run으로 설치된 명령을 실행해 정상 확인했다.
- 남은 품질: 질문이 반복되는 문서에는 명시적 문항·페이지·표 대응이 필요하다. 원문 진위/조사 대응과 표·응답 수치 검증, 첫 제품 이슈·이용 조건·실제 평가셋은 후속이다. pypdf 업그레이드 시 암호화 사전 거부 hook과 회귀 테스트를 다시 확인해야 하며 resource 한도는 OS sandbox를 대체하지 않는다.
- 게시: [Draft PR #13](https://github.com/DigestWorks/IssueDigest/pull/13) 생성·앱 첨부 완료, 선행 #12 위·미병합. [def67c8의 CI](https://github.com/DigestWorks/IssueDigest/actions/runs/38338133072) 성공. Sites v29 게시와 현재 폴더/서버 사용자 전용 worktree의 f0c34d6 인계를 확인했다. 실제 제품 앱/운영 DB 배포는 수행하지 않았다.
- Sites: [v29 공개 게시](https://lawdigest-rebuild-plan.ijaesinii.chatgpt.site/#pdf-evidence) 성공. source `a84ffcec8ae42a2a76edb32fe8db368062f65d77`, saved version `appgprj_6ac612dd42708191a7a0c8377be64d48~appgver_578bd5a013808191b6383ac332013977`, deployment `appgdep_6acd9b12fe548191a4702a9a4e818322` native succeeded·URL 확인. 사본 기준f0c34d6·v28 보존·HTML14개/로컬 링크·anchor181개/manifest/공개 접속정보 제외 통과. 문서6개 상대 링크61개 검사 통과. 원문/개인 추출 상세는 미게시, 문서 변경의 브라우저 화면 검사는 수행하지 않았다. 사이트 탭 열기는 queued 접수다.
- 인계: 현재 폴더는 feat/pdf-text-evidence, 서버 사용자 전용 worktree는 같은 origin 브랜치를 추적하며 f0c34d6에서 Git 깨끗함·locked 설치·installed inspect-pdf 도움말을 확인했다. 게시 기록을 포함하는 마지막 문서 커밋도 fast-forward하고 최종 응답 전에 같은 HEAD·깨끗함을 확인한다. API/웹 프로세스를 재시작하거나 운영 DB·공유 서비스를 변경하지 않았다. 미병합 리뷰/RED·GREEN 증거는 격리 폴더에 보존한다.


## 2026-10-13 · 관리자 요청·읽기 전용 연결기 준비

- 사용자 요청에 따라 관리자가 해야 할 설치/계정/접근 작업만 전달 문서로 좁혔다. 개발자는 자료 연결기·검증과 후속 백업 자동화/배포 설정을 맡는다. 외부 저장소·DNS 공급자·청구 비용은 확인 전이다.
- 현재 계정의 비대화식 sudo/Docker 관리·DB superuser/CREATEROLE/CREATEDB 권한이 없고, DB 소유자이며 vector 패키지가 없음을 다시 확인했다. pg_dump/pg_restore 사용 가능, 서버 웹 포트는 기존 서비스가 사용 중이다. 접속 세부정보는 공개 기록에 넣지 않는다.
- 연결기는 parsed/pdf 파일만 명시 경로에서 읽는다. basename 대응은 후보로만 표시하고 누락·다중 후보·헤더 없는 PDF를 격리한다. 개별/전체 읽기 한도·symlink/경로 검증·집계와 개인 상세 결과를 분리한다. 첫 제품 이슈·기존 계약을 변경하지 않는다.
- 작업 절차: spec-driven-workflow 적용. OpenSpec root null로 해당 단계는 생략, 계획/요구사항을 변경 문서에 작성하고 SDD/TDD·독립 리뷰·실제 PG 포함 전체 검증으로 진행한다. native worktree 도구가 바깥 폴더를 Git 저장소로 인식하지 못해 기존 sibling 격리 방식으로 준비했다. 다른 작업의 리뷰 폴더·기록은 보존한다.
- baseline: locked Python3.13.12/uv0.11.4·SHA 확인한 Node24.21.0/npm11.19.0·전용 합성 PostgreSQL18.6, 전체 Python778+JS134=912·린트/타입/SPA/계약 drift 통과. 기본 시스템 도구 차이로 첫 npm 설치가 거절돼 고정 도구를 선택했다. 엔진 제약/lockfile 우회는 하지 않았다.
- 구현: `02d6cc5` 표준 라이브러리 전용 ingestion 패키지. 명시 경로·descriptor 기반 symlink/특수 파일 거부, JSON metadata·basename 다중 후보·PDF 헤더/해시·변경/크기/총 읽기 한도, 집계 전용 stdout·600 exclusive 개인 manifest. 원문/인용 증명·DB 이관을 만들지 않는다.
- 검증: 실제 assertion RED/GREEN 기록과 신규101개·전체Python879+JS134=1,013개, lint/format·mypy·TS·SPA·계약 drift를 controller가 최종 구현에서 exit0 확인했다. 새 외부 의존성·기존 생성 계약 변경 없음. 독립 작업 리뷰에서 명세/품질 모두 승인, 지적0. 전체 변경 리뷰의 비차단 URL 제어문자 처리 지적1개를 `1a6f71d`에서 Unicode Cc 거부·실제 assertion RED3/GREEN110개로 보완했다. 한 번의 수정 범위 재검토에서 해결·새 문제 없음 확인. 최종 controller 전체Python888+JS134=1,022개와 모든 검증 exit0, skip0. PR #12 생성·앱 첨부 완료, Sites는 대기 중이다.


- 실제 검사: 서버 사용자 전용 worktree `02d6cc5`에서 locked 설치 후 2026-10-13 10:37 한국 시간에 완료. 읽은 JSON840개 중 candidate225·quarantined384·unsupported231. 격리 사유: 등록번호 형식8·유효 출처 URL 없음315·다중 PDF 후보49·PDF 누락12. parsed 비JSON1개는 읽지 않았다.
- PDF:774개를 스트리밍 검사, 헤더 없는23개·정상 PDF의 동일 해시 그룹90개·유효 등록번호 중복 그룹226개. 전체 읽기942,478,095 bytes. 중복 그룹은 문서/조사 건수와 같지 않으며 자동 병합하지 않았다. 헤더/해시/basename 대응은 원문 동일성·인용 정확성의 증명이 아니다.
- 보완 영향 확인: 개인 manifest의 유효 metadata에 제어문자를 포함한 출처 URL이0개임을 집계로 확인했다. 이전 실제 검사 건수는 `02d6cc5` 관측 결과이며 전체943MB 재검사를 반복하지 않았다.
- 개인 상세 결과:840개 JSON의 manifest를 원문 경로와 Git 밖 개인 디렉터리의 새600 파일로 저장했다. 공개 stdout은 집계만, 원문·경로·등록번호·URL·해시는 기록하지 않았다. 소스 파일·운영 DB·공유 서비스·DNS 변경 없음. 전체 수집 상태/일관된 스냅샷을 보장하지 않는다.


- 게시: [Draft PR #12](https://github.com/DigestWorks/IssueDigest/pull/12) 생성·앱 첨부 완료, 선행 PR #11 위이며 미병합. [baf4b18의 CI](https://github.com/DigestWorks/IssueDigest/actions/runs/38333517845) 성공. 실제 제품 앱/운영 DB 배포는 수행하지 않았다.
- Sites: [v28 공개 게시](https://lawdigest-rebuild-plan.ijaesinii.chatgpt.site/) 성공. source `d1e95100359480f2e80d35d68bfd2ce8b824a859`, saved version `appgprj_6ac612dd42708191a7a0c8377be64d48~appgver_2792cfe7828c81918724c8ad7bc24447`, deployment `appgdep_6acd8d1834288191b467053c8bbcaf21` native succeeded·URL 확인. 사본 기준baf4b18·기존v27 보존·HTML13개/로컬 링크·anchor161개/manifest/공개 접속정보 제외 통과. 문서 변경의 브라우저 화면 검사는 수행하지 않았다. 앱 사이트 탭 열기는 queued 접수였다.
- 인계: 마지막 게시 기록까지 현재 폴더/서버 사용자 전용 worktree를 fast-forward하고 locked 새 ingestion 설치·Git 깨끗함·설치된 CLI를 확인한다. 최종 응답은 이 확인 결과를 기준으로 한다. 기존 웹/API·공유 서비스·운영 DB·수집 원문은 변경하지 않는다. 미병합 작업의 검증/리뷰 증거는 격리 폴더에 보존한다.

## 2026-10-12 · 전용 DB·기존 수집 자산 조사

- 관리자 안내를 실제 서버 조회로 확인했다. PostgreSQL18.6 전용 DB 접속·CREATE 권한·빈 public, vector가 설치/설치 가능 목록에 없음을 확인했다. 개인 설정 값은 출력·커밋하지 않았다. 기본 API는 계속 DB 미연결로 자료를 거부한다.
- 기존 MySQL SELECT 전용 helper로 허용 28테이블을 순차 COUNT했다. 법안41,004·여론조사305·후보25,235, 기간·AI 산출물·원문 URL/파일 참조와 누락을 기록했다. 전체 DB의 고정 시점 스냅샷은 아니다.
- 파일/상태/코드는 읽기 조사만 했다. 여론조사 PDF774개 중23개에 헤더 없음, 파싱 자료의 basename 누락/충돌을 확인했다. 폴더의 PDF 수를 검증된 고유 원문 수로 기록하지 않는다. 종료 이벤트·READY·수정 시각을 현재 수집 성공으로 간주하지 않는다.
- D012: 사용자 확정 서비스 도메인 issuedigest.projects.ai.kr. 조사 컴퓨터의 DNS 조회는 이름 해석 실패. DNS/TLS/프록시/콜백·공개 앱 배포는 수행하지 않았다. 계획 Sites 주소를 변경하지 않는다.
- 검증/공개: 문서 링크·기준 숫자·접속 세부정보 제외를 검사한다. 앱 코드·DB/수집 서비스·운영 데이터 변경 없음. 문서-only이므로 spec-driven 전체 구현 절차와 코드 테스트를 반복하지 않는다.
- 게시: [Draft PR #11](https://github.com/DigestWorks/IssueDigest/pull/11) 생성. 앱 첨부를 요청했으나 응답은 미확인이다. 변경 문서9개 상대 링크54개·공개 접속정보 제외·주요 집계값·git diff --check 통과. [사본 기준333f63e CI](https://github.com/DigestWorks/IssueDigest/actions/runs/38227033348) 성공. 기존 PR #10과 그 검토·테스트 증거를 보존한다.
- Sites: [v27 공개 게시](https://lawdigest-rebuild-plan.ijaesinii.chatgpt.site/) 성공. source `60fa91853bcb28c46ea36174de70774ccb3bb2a4`, saved version `appgprj_6ac612dd42708191a7a0c8377be64d48~appgver_5fcc117ac53881919ff4ca475789c41c`, deployment `appgdep_6acca1f9b3ac819199c9f83621765992` native succeeded·URL 확인. 사본 기준 `333f63e`; 이전 v26 보존. HTML12개·로컬 링크/anchor142개·manifest·공개 접속정보 제외 통과. 정적 문서 내용만 바꿨고 이번 변경의 브라우저 화면 검사는 수행하지 않았다.
- 인계: 현재 폴더와 서버 사용자 전용 worktree를 게시 기록91a41d8까지 동기화하고 깨끗한 상태를 확인했다. 기존 코드와 동일하므로 앱 프로세스·의존성·서비스 변경 없음. 이 인계 기록을 포함한 마지막 문서 커밋도 fast-forward하며 결과는 최종 응답 기준 확인한다. 사이트 탭 열기를 요청했으나 앱 응답은 미확인이다. 마지막 문서 커밋의 CI 결과는 PR에서 확인한다.

## 2026-10-12 · 서버 세션·회원 권한·첫 근거 조회 API

- 구현 `73f8684`, 보완 `ed44370`: 실제 PostgreSQL identity/membership/hash-only session 저장과 한 cookie-only 보호 GET. 신뢰된 내부 등록/발급·폐기/회원 권한 관리, secure cookie helper, 외부 연결 없는 기본 app factory를 구현했다. 절대8시간·idle30분은 초기 정책이며 공급자 검증/로그인·초대 승인 기능이 아니다.
- 데이터 경계: 같은 DB transaction에서 세션·활성 사용자·회원 권한을 먼저 확인하고 기존 근거 무결성 로더를 사용한다. 토큰 원문은 DB에 저장하지 않는다. 권한 없는 요청에 자료 내용을 반환하지 않고 모든 보호 응답에 no-store/새 request ID를 넣는다. 401/404/422/503 JSON과 기존200을 canonical OpenAPI/생성 TS로 연결한다.
- 검증: controller가 `ed44370`에서 실제 전용 PostgreSQL18.6 포함 전체 npm run check exit0 확인. Python778·JS134=912개, skip0; lint/format·mypy·TS·SPA·drift 통과. 기존 migration0001↔0002의 근거 보존·해시 저장·활동/만료·폐기·권한 회수·workspace 격리·동시 조회 검증. 초기 callable RED와 동시 요청/오류 모델 보완의 실제 assertion RED/GREEN 증거 보존.
- HTTP: 실제 확인용 Uvicorn 서버에서19회 요청. 두 회원의 동일 근거/인용 순서·같은 세션 동시200, 익명/형식 오류/Bearer/폐기/비활성/절대·idle 만료401, 미가입/다른 공간/없는 자료404, 미구성503. 보호 응답16회 모두 no-store/고유 서버 UUID, 실제 OpenAPI/export 동일. 내부 합성 세션만 쓰고 서버 스레드 종료.
- 리뷰: 독립 작업 리뷰에서 동시 같은 세션의 RR serialization503 및 오류 JSON 생성 계약 누락을 지적했다. 전체 transaction 40001 재시도(총3회)와 정상 오류 모델/생성 TS로 수정해 독립 수정 범위 재검토 통과. 재시도마다 권한/무결성을 새로 확인하며 소진/다른 DB 장애는 고정503이다. ignored 보고서의 denied-retry 테스트 설명 과장을 실제 테스트 내용으로 정정했다. 전체 변경 `04e2efa..193eed8` 독립 리뷰도 지적0으로 통과했다.
- 게시: [Draft PR #10](https://github.com/DigestWorks/IssueDigest/pull/10) 생성·앱 첨부 완료. [검토 기준193eed8의 CI](https://github.com/DigestWorks/IssueDigest/actions/runs/38223884082) 성공.
- 서버: 사용자 전용 ARM64 worktree를 `193eed8`로 fast-forward, locked 설치·웹134개/lint/TS/SPA/drift 통과. 원격 Python 전체나 운영 DB 검사를 수행한 것으로 표시하지 않는다. 기존 reload 부모가 새 storage 패키지 경로를 반영하지 못해 사용자 전용 API 창만 다시 시작했고, 직접/API 프록시10회에서 OpenAPI/export 동일·200상태·401/503 fail-closed/no-store/request ID 확인. 첫 인계는 로컬 로그 폴더가 없어 중단됐고 폴더 준비 후 재검증했다. 공유 서비스/관리자 설정 변경 없음.
- 현재 폴더: `feat/session-evidence-api`에 연결하고 locked npm/uv 설치, 기본 앱 import/OpenAPI/export 일치 확인. 기존 SSH 개발 연결을 통해 직접/API 프록시10회200/401/503·no-store/서버 UUID와 웹200 재확인. 서버와 현재 폴더의 마지막 문서 커밋도 동기화한다.
- Sites: v26 공개 배포 성공(`appgdep_6acc9c45c0d481918af07dd7ce9cc7c7`), saved version `appgprj_6ac612dd42708191a7a0c8377be64d48~appgver_ee3f5e57031c8191a67ea492b977c08f`, source `104c525440823de2757ea26edf39d0a453d46839`. 사본 기준 `80b56e0`; 그 이후 게시/인계 상태는 저장소 원본을 따른다. 이전v25 보존, HTML11개의 로컬 링크/anchor124개·manifest·공개 개인정보 제외 검사 통과. native succeeded URL 확인·사이트 탭 열기 요청 접수. 렌더러/제품 웹 UI를 변경하지 않았다.
- 운영: 실제 로그인·공급자 검증·초대·제품 화면·운영 DB·원문 bytes·AI·SSE·전체P1은 미완료. 공유 DB·운영 자료·서버관리자 설정을 바꾸지 않았다. 공개 요약·현재 폴더 연결을 완료했다. 최종 문서 커밋의 서버 동기화와 CI는 마지막 인계 확인에서 검증한다. 미병합 리뷰 증거는 격리 폴더에 보존한다.

## 2026-10-12 · 검증된 생성 화면 React 렌더러

- 구현 `a0f52b7` + 스타일 격리 보완 `068cb1f`: `@issuedigest/ui`의 CanvasView가 기존 생성 공개 타입/CanvasBundle을 소비한다. 근거·요약·주장 비교·날짜 구간·실제 방향 관계·정확 소수 수치 bar/표를 명세 순서·span으로 표시한다. 선택 근거·workspace·typed 참조·비교 조건·액션을 준비한 후 표시하며 깨진 화면은 부분 내용 없이 거부한다.
- 경계: null 빈 상태·근거 부족·추가 질문을 구분한다. 근거 열기·문서 선택·후속 질문·정렬은 등록 값의 콜백만 전달한다. 실제 API/AI·원문/액션 실행·로그인·SSE·취소·화면 저장·운영 DB는 미연결이다. 선택하지 않은 관계 endpoint는 표시하지 않는다. 문서 제목은 기존 계약에 없어 실제 source_id를 사용한다.
- 검증: controller가 `068cb1f`에서 전용 로컬 PostgreSQL18.6을 포함한 전체 `npm run check` exit0 확인. Python712개(저장39개 포함, skip 없음)·JS134개(UI74개), lint/format·타입·SPA 빌드·계약 drift 통과. 공유 합성 JSON을 기존 Python 계약과 생성 타입을 사용하는 React 테스트가 소비한다. 초기 실제 assertion RED63개, 스타일 containment RED3개 후 GREEN 증거 보존.
- 브라우저: 합성 자료의 내부 QA 화면에서1366/390 가로 넘침 없음·여섯 모듈·명세 구성 변화·빈/자료 부족·Enter 및 실제 Tab+Space의 정확 인용 ID·바깥/안쪽 스타일 격리·콘솔 오류/경고0 확인. 합성 결과를 제품 앱에 연결하거나 AI 생성 결과로 표시하지 않았다. 내부 QA 서버·브라우저와 전용 테스트 DB는 검사 후 종료했다.
- 리뷰: 독립 작업 리뷰의 CSS 범위 지적을 수정하고 재검토 통과. 전체 변경 리뷰의 fixture 주석·검증 기준 SHA 지적을 `cdaaec8`에서 정정하고 한 번의 수정 범위 재검토로 종료했다. 잔여 지적 없음. ignored 리뷰/검증 기록은 미병합 PR 검토가 끝날 때까지 격리 폴더에 보존한다.
- 게시: [Draft PR #9](https://github.com/DigestWorks/IssueDigest/pull/9) 생성·앱 첨부 완료. `83b7b7e`의 [GitHub CI](https://github.com/DigestWorks/IssueDigest/actions/runs/38218480943) 성공. 최종 게시 메타데이터는 문서만 변경한다.
- 서버/폴더: ARM64의 사용자 전용 worktree `cdaaec8`에서 locked 설치·웹 lint/타입·JS134·SPA·계약 drift 통과. 원격 Python/운영 DB 검사를 실행한 것으로 표시하지 않는다. 기존 tmux 웹/API 유지, 직접/프록시 및 로컬 연결 HTTP200·요청 ID 확인. 현재 사용자 폴더를 `feat/canvas-renderer`에 연결하고 locked 설치·UI export/CSS 경로를 확인했다. 마지막 문서 커밋도 개발 서버에 동기화한다.
- Sites: v25 공개 배포 성공(`appgdep_6acc8dfe53d08191a7267f919c17ff40`), 이전v24 보존. 사이트 source `078f41465efdbf919a737d2a8e69e2bd1dde2a27`, 저장소 문서 사본 기준 `83b7b7e`. 이후 게시 기록은 저장소 원본을 확인한다. 공개 요약의 로컬 링크·상태·건수·접속 세부정보 제외 검사 통과, 사이트 탭 열기 요청 접수.

## 2026-10-12 · 엔진 확정·첫 PostgreSQL 저장

- D011: 사용자 선택 PostgreSQL·pgvector·PydanticAI/DBOS 확정. A001~A003 추천/대안은 당시 비교 이력으로 대체 관계를 보존했다. [공식 근거·호환 범위·검증 기준](../research/engine-selection.md)에 선택과 실측을 구분했다.
- 구현: typed storage uv 패키지, SQLAlchemy2.1.4/Alembic1.20.0/psycopg3.3.6 고정. 문서·버전·표현·인용의 전역 불변 ID·공간/부모 FK, 스냅샷 인용 순서·내용 해시·동일 ID 재전송, 원자적 초기 outbox와 최초 마이그레이션.
- 실제 DB 검증: 새 전용 로컬 PostgreSQL18.6 합성 DB에서 저장39개, 전체Python711+JS60·lint/타입/SPA/계약 drift 통과. controller가 최종 `aaf810a`에서 동일 전체 명령을 직접 실행하고 exit0 확인. DB 미설정은 수동 로컬 통합 검사 skip이며 CI는 명시적 전용 서비스/URL·미설정 실패로 필수 실행한다.
- 리뷰: 독립 작업 리뷰의 AUTOCOMMIT 원자성·commit 응답 불확실 안내 수정, 전체 리뷰의 PDF signed-zero JSONB 정규화 수정. 각각 실제 DB RED/GREEN 및 범위 재검토 통과. 최종 잔여 지적 없음. 유실 commit 응답을 실제 장애로 주입하는 검증은 수행하지 않았으며 같은 ID 재확인 정책을 문서화했다.
- 운영 경계: PostgreSQL 연결 준비 항목 작성. 개발 서버 DB 설치·공유 서비스/기존 운영 데이터 변경·공급자 유료 호출 없음. 파일 원문 참조는 실제 파일 보존·해시 대조 완료가 아니다. workspace 필터는 로그인/멤버십 검증이 아니다. 검색·복구·월10만 원 실측과 전체P1은 미완료.
- 게시/인계: [Draft PR #8](https://github.com/DigestWorks/IssueDigest/pull/8)을 PR #7 브랜치 위에 게시·앱 첨부했다. `def2244`의 [GitHub CI](https://github.com/DigestWorks/IssueDigest/actions/runs/38195790846) 통과. 개발 서버의 개인 worktree를 같은 기준으로 동기화하고 ARM64 의존성·전체 검사 Python711+JS60·lint/타입/SPA/drift 통과. 서버에는 DB를 설치하지 않았으며 SSH 임시 역방향 연결로 로컬 전용 PostgreSQL18.6을 사용했다. 검증 후 임시 연결 종료, 기존 웹/API 직접·프록시 HTTP200·요청 ID 재확인. Sites v24 공개 배포 성공(`appgdep_6acc46d38e988191b16c6446fa9e5b26`), 이전v23 보존. 사이트 문서 사본은 `4b68ec7` 기준이며 이후 게시 기록은 저장소 원본을 확인한다. 사용자 폴더도 `feat/postgres-storage`로 연결하고 locked 설치·storage import를 확인했다. 리뷰 증거는 기존 격리 폴더에 보존한다.

## 2026-10-12 · 개발 서버 환경·실행 검증

- 담당/브랜치: controller · `docs/development-server-access`; 서버 `codex/jaesin-development`, 검증 기준 `806e22e`. 사용자 승인 범위에서 도구·worktree·의존성·웹/API를 준비했다. 제품 코드·공개 계약·고정 버전·lockfile 변경 없음.
- 사용자 전용 Node24.21.0/npm11.19.0/uv0.11.4/Python3.13.12 설치 및 PATH 선택 파일 구성. 공유 시스템 도구·기존 사용자 uv 보존. npm/uv lockfile 설치 성공, ARM64 전체 검사 Python672+JS60·lint·타입·SPA 빌드·계약 drift 통과.
- 서버 main은 깨끗한 초기 커밋으로 보존하고 중첩 worktree는 로컬 exclude로 제외했다. 지정 웹15173/API18090은 loopback에만 바인딩. SSH 터널 직접/프록시 HTTP200·JSON·UUID v4·실제 OpenAPI 일치 확인. 브라우저 실제 연결 성공·1366/390 가로 넘침 없음·콘솔 오류/경고0. tmux 종료 후 두 포트 해제·재시작 성공, 앱과 터널 실행 상태 유지.
- 저장소가 PUBLIC임을 GitHub에서 확인해 이전 비공개 표기를 정정했다. 공개 최신 문서에서 접속 주소·계정·키 경로를 제거하고 저장소 밖 개인 설정에 보관한다. 이전 커밋/PR에 접속 메타데이터는 남으며 키 본문·인증값은 커밋하지 않았다. 저장소 가시성·Git 이력은 변경하지 않았다.
- 미검증: 운영 배치·DB/수집/AI·앱 인증, 실제 데이터·서버 전용 자원·월 비용·서버 개인 push 권한. 관리자 설치·공유 서비스·운영 데이터 변경 없음. 개발 실행을 전체 P1이나 운영 배포 완료로 표시하지 않는다.
- 다음: 서버 자원·비용·기존 데이터 확인 및 DB·검색·실행기·배치·인증 판단. 새 유료 자원/API 키 설정은 아직 필요 없다. 기존 Draft PR #7을 현재 범위로 갱신·앱 첨부 완료, 기록 커밋 `e3c3f12`의 [GitHub CI](https://github.com/DigestWorks/IssueDigest/actions/runs/38192821177) 성공. Sites v23 배포 성공(`appgdep_6acc3b1ac77881918bd90ba41f0b47bf`), 이전 v22 보존. 공개 요약의 상태·로컬 링크·접속 메타데이터 제외 검사 통과. 사이트 사본은 `e3c3f12` 기준으로 이후 게시 메타데이터는 저장소 원본을 확인한다.

## 2026-10-12 · 개발 서버 접속·준비 상태 확인

- 담당/브랜치: controller · `docs/development-server-access`. 서버 안내와 SSH 읽기 확인을 [서버 확인 기록](https://github.com/DigestWorks/IssueDigest/blob/docs/development-server-access/infra/development-server.md)에 정리했다. 코드·공개 계약·의존성 변경 없음.
- 사용자 요청으로 키를 저장소 밖 SSH 전용 경로로 옮기고 권한 600을 적용했다. 키 내용·인증값은 기록/커밋하지 않았다. SSH 접속과 안내 파일·기초 자원·도구·Git 상태·포트 확인 완료.
- ARM64·4 CPU, 메모리 약 23.4GiB(가용 12.9GiB), 디스크 여유 약 39GiB. 순간 관측값이며 전용 할당·월 비용을 뜻하지 않는다. 개발 포트 15173/18090은 listener 없음, Docker 소켓 관리 권한 없음.
- 도구 버전이 고정 기준과 다르며 uv는 사용자 경로에 설치되어 있으나 비대화 SSH PATH에는 없다. 시스템 설치·환경 수정·Git fetch/checkout·의존성 설치·앱 기동·DB·운영 서비스 변경은 수행하지 않았다.
- 서버 main은 초기 README와 .gitignore만 있는 깨끗한 상태. GitHub 읽기에서 최신 `feat/execution-contracts` 확인; PR #1~#6 미병합으로 main에는 실행 코드가 아직 없다. GitHub push 권한은 미검증.
- 다음: 사용자 전용 도구·최신 코드 worktree·lockfile 설치와 원격 검증. 관리자 협의는 자원 배정·공존 서비스·비용·DB/백업 배치안을 구체화한 뒤 진행. 기존 수집 서버와의 관계·실제 데이터 현황은 미확인.
- 검증: 변경 문서의 상대 링크·고정 버전·지정 포트 명령안과 저장소 스크립트 일치, diff 공백·키 본문 제외 검사 통과. 문서 변경이므로 앱 테스트를 재실행하지 않았다. 원격 앱 실행 명령과 터널은 아직 명령안. [Draft PR #7](https://github.com/DigestWorks/IssueDigest/pull/7) 게시, 기록 커밋 `01cc3d3`의 [GitHub CI](https://github.com/DigestWorks/IssueDigest/actions/runs/38191551337) 통과. Sites v22 공개 요약 배포 성공(`appgdep_6acc367937b081919b14cc437c830f22`), 이전 v21 보존. 공개 요약에 SSH 주소·계정·키 경로는 포함하지 않는다. PR #7 앱 첨부 완료, 사이트 탭 열기 요청도 접수됨. 직접 URL로도 인계한다.

## 2026-10-12 · 실행 계약 검토·인계

- 구현 `b408ad6` + 배열 최소 개수 보완 `e2255d7`. 실제 API 스키마의 14개 필드 RED 후 보완 GREEN, Python/JSON의 개수·중복 검증 보존. 작업 리뷰·수정 범위 재검토·전체 변경 리뷰 통과, 최종 신규 지적 없음. controller의 reviewed-head 전체 검사 672 Python + 60 JS 및 lint/타입/빌드/drift 성공. 의존성·HTTP 경로·기존 도메인 정책·웹 UI 변경 없음.
- [Draft PR #6](https://github.com/DigestWorks/IssueDigest/pull/6)을 선행 PR #5 위에 게시했다. GitHub CI·Sites·사용자 폴더 연결은 이 기록 이후 완료 상태를 갱신한다. 자동 PR 첨부 요청은 응답하지 않아 직접 URL로 공유한다. 미병합 PR의 ignored SDD 검토/실행 증거는 이 작업의 격리 폴더에 보존한다.

## 2026-10-11 · 실행·이벤트·화면·사용량 부분 계약

- 역할별 `contract_values.py`, `canvas_modules.py`, `execution.py`, `canvas.py`, `usage.py`, `execution_bundle.py`에 순수 모델/함수를 구현했다. 새 계약의 strict 버전/정수/문자열·UTC 시각·tuple/frozen·추가 필드 거부를 적용하고 기존 원문/연구 정책·두 HTTP 경로·웹 UI를 보존한다.
- 입력 자료 순서와 원문 질문·실행 버전을 SHA-256에 고정하고 실제 입력 동등성으로 제출 reuse/conflict를 판정한다. 연속 seq 이력을 fold하여 취소/미확인/완료 경합·늦은 모듈을 거부하고 실패/취소의 base 화면과 비용 확인을 보존한다.
- Canvas는 허용 모듈/액션·선택 원문/인용 합집합·주장/관계/관측 존재·차트의 알려진 같은 조건·부모/expected ID를 검사한다. CallAttempt는 상태별 시각/결과와 prefix별 유료 적격성을 기록한다. 이 함수들은 실행·권한·서버 저장 인증이 아니다.
- Usage는 서울 완전한 달·월 전체 운영비 10만 원·다른 비용·정밀 정수 금액·unknown hold·각 retry 합계·실제 초과비용과 정산을 검사한다. 전체 bundle은 모듈 발표/성공 revision·attempt/reconciliation·가격/예약/entry를 연결한다. 제공된 다른 run의 정상 historical revision도 검사하며 최소 ancestor 목록을 선택하지 않는다.
- 검증: 순수 알고리즘 일곱 개 각각 callable scaffold에 대한 실제 assertion RED를 확인하고 focused GREEN과 실제 schema 등록/기존 component 동일·collision/입력 불변·생성 TS compile 소비자를 확인했다. 상세 명령/출력·self-review는 ignored `.superpowers/sdd/execution-contracts/task-1-report.md`와 evidence에 보존한다. 초기 `npm run check` 1회 통과: Python 656개·JS 60개, Ruff/format/mypy·ESLint·양쪽 TS 타입·SPA 생산 빌드·생성 계약 drift 통과. 유료 적격 cursor는 실제 dispatch 직전 권한 재확인·물리적 취소 경합 보장의 증거가 아니며 worker/DB 처리는 후속이다.
- 리뷰 보완 1차: 실제 OpenAPI의 ID 배열에 문자열 `minLength`가 생성되는 P2를 확인했다. 공통 tuple 길이 제약을 AfterValidator보다 먼저 적용하여 `minItems`를 생성하고 runtime cardinality/uniqueness를 보존했다. 실제 앱의 14개 배열 assertion RED 후 focused 286개·전체 `npm run check` 1회(Python 672개·JS 60개, lint/타입/SPA 빌드/계약 drift) 통과. OpenAPI/TS를 재생성했으며 TS 결과는 동일하다. 수정 부분 독립 재리뷰 대기다.
- 인계 대기: 독립 작업·전체 변경 리뷰, Draft PR, Sites v20 이후 공개 요약, 사용자 폴더 연결은 controller가 담당한다. 결합 완료 checkbox를 닫지 않았다. 신규 의존성·외부/유료 호출·비공개/운영 자료·실행기·저장소·SSE/제품 API·UI/AI 구현은 없다.

## 2026-10-11 · 개체·주장·관계·비교 조건 계약

- 동일 이름의 독립 개체와 미해결/미검토를 보존하고 외부 identity 3항 키 충돌을 거부한다. 근거 있는 원문 주장/관측/추론 입력과 inference에만 필요한 가공 기록을 구분한다. 검토는 UTC 시각·방법/버전·인용과 귀속/내용/관계 범위를 기록하며 실제 인증 행위·주장 진실을 보장하지 않는다.
- `issuedigest-relations-v1`의 6종 방향/양 끝 종류와 제공 객체 존재를 검사한다. 근거 없는/미등록 인과/자기 관계·다른 공간·없는 endpoint를 거부한다. mentions는 source 문서 버전의 인용만 허용한다. 자동 역관계·그래프 투영은 없다.
- 정확한 Python date/JSON YYYY-MM-DD 기간·strict 양의 표본 크기·최대128자 정밀 ASCII 소수 문자열과 원문/결측을 보존한다. 비교는 모든 조건과 value 결측을 순서대로 보고하고 different를 missing보다 우선한다. 같은 조건의 다른 값·순서만 다른 차원은 same_context이며 합산/분포는 not_evaluated다. 결과 ID·사유·status 모순도 거부한다.
- ResearchBundle의 전체 공간·문서/버전 일치·고유 인용/표현/검토 ID·typed 참조·검토 citation subset을 검증한다. 같은 문서/버전의 다른 파싱 표현은 허용한다. 검증 대상은 제공된 묶음이며 저장소 전체 unique enforcement는 아니다.
- 실제 OpenAPI components를 단일 등록 경로로 확장하고 생성 TS와 공개 aliases/compile 소비자를 갱신했다. 기존 HTTP 두 경로·상태/원문/인용·웹 UI를 보존했다. 종속성·외부/유료 호출·비공개/운영 자료 사용 없음.
- 초기 구현 검증: focused 새 계약+API 228개 통과, Ruff/mypy·공개 생성 타입 소비자 통과. 전체 `npm run check` 1회 통과: Python 380개·JS 60개, Ruff/format/mypy·ESLint·양쪽 타입 검사·SPA 생산 빌드·생성 계약 drift 검사 통과. RED/GREEN·수정 파일·self-review는 로컬 SDD `research-contracts/task-1-report.md`에 보존한다.
- 인계: 독립 작업 리뷰 통과. 전체 변경 리뷰의 P2 지적(같은 항목의 결측/다름 ID 겹침과 필수 항목의 결측 사유)을 `e902cb4`에서 보완했다. JSON 회귀 RED 8개 실패·정상 5개 통과 후 GREEN 107개, 수정 부분 재리뷰 지적 없음. 컨트롤러 최종 전체 검사도 393 Python + 60 JS 통과. 초기 비교 알고리즘만의 독립 RED 증거 범위는 제한적이며 이를 뒤늦게 충족했다고 주장하지 않는다. 현재 동작 테스트·코드 리뷰로 구현을 검증했다. 사용자 폴더 연결·실제 API 계약 및 웹 기동 확인 완료. Sites v20 공개 게시와 사용자 폴더 연결까지 확인하여 C1~C4 결합 완료를 체크했다. 나머지 P1·출처 시간 정밀도·재수집·내용 비교 fingerprint·Run/Event/Canvas/Usage·실제 자료/추출/저장/권한·AI·Neo4j는 미완료.

- 게시: [Draft PR #5](https://github.com/DigestWorks/IssueDigest/pull/5), base `feat/source-evidence-contracts`, 구현 `d82a8f1` + 보완 `e902cb4`. 보완 커밋의 [GitHub CI #38144301870](https://github.com/DigestWorks/IssueDigest/actions/runs/38144301870) 성공. Sites v20 공개 게시 성공. 사본 기준 `06dda30` 이후 상태는 저장소 원본에서 확인한다. 앱의 자동 PR 첨부·사이트 열기 요청이 응답하지 않아 직접 URL로 공유한다.

## 2026-10-11 · 첫 원문·파싱·인용 계약

- 원문 문서/버전과 파싱 표현을 분리하고 모든 내부/원문 객체 ID를 UUID4, 해시는 소문자 SHA-256, 수집 시각은 시간대 필수·UTC 직렬화로 검증한다. 원문 bytes를 받지 않으므로 raw hash는 형식만 검사한다.
- 중첩 frozen 모델·tuple, JSON 왕복·extra 거부, strict 오프셋/페이지/표본/유한 PDF 좌표를 구현했다. 원문/표현/인용 ID 연결, 페이지 범위·표/셀·인용 중복과 정확한 quote/context를 검증한다. 파서 버전별 표현·인용의 공존은 계약 테스트이며 DB 중복 제거 증거가 아니다.
- 빈 표·빈 셀·좌표 없는 PDF를 유지하고 통계 조건은 null을 채우거나 합산하지 않는다. `validate_citation` 결과는 anchor `matched`와 support `not_evaluated`를 구분한다. Python 검증 생략 construction/copy는 입력 경로로 사용하지 않도록 패키지 README에 기록했다.
- FastAPI OpenAPI components에 모델을 등록하고 기존 두 HTTP paths와 상태·요청 ID를 유지했다. 충돌 시 오류를 내며 `/openapi.json`과 export 스크립트가 같다. OpenAPI/TS 타입을 생성하고 웹 클라이언트에서 공개한다.
- `getCitationUtf16Range`는 Python code point→JS UTF-16 범위를 변환하며 quote/context 오류를 거부한다. 공통 합성 UTF-8 fixture로 한글·BMP 밖 이모지·결합 문자·NFC/NFD·선행/후행 공백을 검사한다. grapheme 분할·PDF 렌더링은 범위 밖이다.
- 검증: focused Python domain 140개, API 포함 150개 및 TS 인용 변환 40개 통과. 전체 `npm run check` 1회 통과: Python 150개·TS 60개, Ruff/mypy/ESLint·양쪽 타입·생산 SPA 빌드·생성 계약 drift 검사 통과. RED/GREEN 상세는 로컬 SDD `task-1-report.md`에 보존한다. 새 종속성·외부 호출·운영/비공개 자료 사용 없음.
- 후속: 출처 연/월/일 시간 정밀도·재수집 관측·내용 비교 fingerprint·실제 parser/원문 저장, 주장/관계·비교 조건, Run/Event/Canvas/Usage·저장·권한 검증. 전체 P1과 제품 기능은 미완료.
- 검토: `9271a0a`에서 독립 작업 명세/품질 리뷰와 전체 변경 리뷰 모두 지적 없음. 컨트롤러 전체 검사도 통과. 사용자 폴더 `/data/lawdigest/IssueDigest`에 브랜치를 연결하고 잠긴 설치·전체 검사 150 Python + 60 JS를 다시 통과했다. 별도 작업 공간의 검증 기록은 PR 병합 전까지 보존한다.
- 게시: [Draft PR #4](https://github.com/DigestWorks/IssueDigest/pull/4) 생성, 선행 PR #3 위에 쌓았으며 미병합. 구현 커밋 `9271a0a`의 [GitHub CI](https://github.com/DigestWorks/IssueDigest/actions/runs/38137640138) 성공. Sites v19 공개 배포 성공. 스냅샷 기준은 `63f88fe`이며 최신 상태는 이 저장소다. 앱의 브라우저 열기·PR 첨부 요청이 응답하지 않아 직접 URL로 공유한다.

## 2026-10-11 · 제품 계약 조사

- 기존 LawDigest·별도 파이프라인 원격 main SHA를 GitHub API로 확인했고 기존 조사 기준과 일치했다. IssueDigest 실행 기반은 `4e63421`, main은 PR 미병합 상태다.
- 원문 버전과 파싱 결과 분리, 정확한 인용 위치, 구조/원문 위치/주장 지지 검증 분리, 조건 있는 수치·관계, 저장 순번 이벤트, 불명확 유료 호출, 검증된 모듈과 불변 화면 버전·예약/정산의 설계 제안을 기록했다.
- 기존 발의자 결측에 따른 자료 제외·여론조사 불완전 분포 허용·요약 중심 검색·로컬 JSONL 기록의 재사용 경계를 정리했다. 기존 운영 데이터/공급자 호출·테스트 실행은 하지 않았다.
- Decisions public beta와 역할을 공식 문서로 확인했다. PydanticAI DBOS의 일반 모델 스트리밍 버퍼링과 live handler/중복 처리 경계를 확인해 실행기 비교 실험에 반영했다. 새 프로젝트 키·모델 품질·지연·비용은 미검증이다.
- 조사 완료는 계약 모델/API·저장·권한·AI/화면 구현 완료가 아니다. PostgreSQL·검색·DBOS/Temporal·json-render를 채택하지 않았다.
- 검증: 상대 문서 링크·고정 코드 근거·문서 상태 구분·변경 공백 확인. 런타임 코드를 바꾸지 않았으므로 로컬 전체 테스트를 반복하지 않는다.
- 사용자 입력: 지금 서버·키 추가 작업 불필요. 실제 평가 자료 단계 전에 첫 이슈·질문·원문 범위를 함께 선정한다.
- 게시: [Draft PR #3](https://github.com/DigestWorks/IssueDigest/pull/3) 작성·연결. base는 개발 기반 PR #2의 브랜치이며 병합하지 않았다. 문서 커밋 `8988f33`의 [GitHub CI](https://github.com/DigestWorks/IssueDigest/actions/runs/38134714271) 성공. Sites v18 공개 배포 성공, 네 영역으로 요약하고 설계 제안/제품 미구현 상태를 표시했다. 공개 사본 기준은 `8988f33`이며 최신 상태는 저장소 원본이다.

## 2026-10-11 · 웹·API 개발 실행 기반

- 작업: [Task 1](../changes/development-foundation.md). 기준 커밋 `862b2d94c20902ad3f64c5534956100bd5d8830b`, 브랜치 `feat/development-foundation`. P1 중 독립된 실행·계약·검증 기반만 구현했다.
- Node 24.21.0·npm 11.19.0·Python 3.13.12·uv 0.11.4를 사용했다. npm workspaces(웹·API 클라이언트)와 uv workspace(API·Python 도메인), 정확한 직접 의존성·잠금 파일, 루트 설치·개발·검증 명령을 구성했다.
- API의 `/health/live`, `/api/v1/status`는 지정한 JSON과 서버 UUID `X-Request-ID`를 반환한다. 오류에도 요청 ID를 부여한다. 상태는 API 프로세스의 응답 여부이며 DB·워커 준비 완료가 아니다.
- Python 모델/FastAPI OpenAPI에서 OpenAPI·TypeScript 타입을 생성·버전 관리한다. 재생성 비교와 런타임 응답 검증을 포함했다. 웹은 Framework SPA, 같은 출처 개발 프록시, 한국어 빈 자료 상태와 실제 연결 확인만 제공한다.
- TDD: API 7개 실패 후 7개 통과. 클라이언트·화면 20개 실패 후 20개 통과. 잘못된 응답·HTTP/네트워크 실패·본문까지 포함한 시간 초과·화면 확인 중·실패·재시도를 검증했다.
- 자동 검증: `npm run check` 통과. Python Ruff·mypy·pytest, TypeScript ESLint·타입·Vitest, 생산 SPA 빌드와 계약 변경 검사. 같은 절차의 [GitHub Actions 실행 #38133178226](https://github.com/DigestWorks/IssueDigest/actions/runs/38133178226)이 기반 코드 커밋 `d132583`에서 성공했다. 원격에서도 테스트 27개·lint·타입·생산 빌드·계약 검사를 통과했다.
- 실제 스모크: 컨트롤러 확인 완료. API 직접 연결과 웹 프록시의 두 엔드포인트에 정확한 JSON/UUID v4, 404에 UUID v4, 웹 HTTP 200을 확인했다. 데스크톱 1366×900·모바일 390×844에서 가로 넘침 없이 hydration을 확인했다. 실제 응답 지연 때 접수 안내·확인 중 비활성 버튼, API 중단 때 실패·재시도, 복구 후 재시도 성공을 확인했다. `npm run dev`로 두 서버 기동, Ctrl+C 후 두 포트 해제도 확인했다. favicon 404는 로컬 SVG로 수정했고 새 브라우저 콘솔 오류·경고는 각 0건이다. 생산 빌드의 `build/client`도 QA용 정적 미리보기에서 hydration·실제 동일 출처 상태 요청·콘솔 오류 없음으로 확인했다. 이는 빌드 검증이며 운영 배포는 아니다. 브라우저 산출물은 로컬 `output/issuedigest-foundation`에만 보관하고 커밋하지 않는다.
- 범위 밖: 기준 DB·검색·실행기·인증 결정, 워커·자료 수집·AI·권한·저장·운영 배포. 기존 P1 미완료 항목과 계획 Draft PR #1의 검토 이력을 유지한다.
- 검토 후속: 명세·코드 품질 검토와 전체 변경 리뷰를 통과했다. 본문 수신 시간 초과 때 이미 받은 서버 요청 ID를 보존하도록 `bae8e89`에서 수정했다. 기존 회귀 테스트에 ID 검증을 추가하여 1개 실패·19개 통과의 RED 후 전체 27개 테스트·검사를 통과했으며, 수정 범위 재검토에서 지적 해결과 새 문제 없음이 확인됐다. 통합 개발 실행기의 프로세스 종료 지원·검증 범위를 Linux로 문서화하고 Windows는 두 앱의 별도 터미널 실행·종료를 안내했다. 앱 코드는 변경하지 않았다.
- 다음 행동: [PR #2](https://github.com/DigestWorks/IssueDigest/pull/2) 검토와 자료·인용·실행 계약 정의. 운영 서버 설치·유료 외부 호출은 수행하지 않는다.
- Sites: v17 공개 게시 성공. 웹·API 개발 기반 완료와 전체 P1·제품 기능 미완료를 구분했다. 공개 문서 사본은 `dbbce9a` 시점이며 최신 원본은 저장소 문서다.

## 2026-10-11 · 모노레포 구현 준비

- 로컬 경로: `/data/lawdigest/IssueDigest`. 기존 클론을 원격 저장소와 같은 이름으로 변경하고 커밋 이력을 보존했다.
- `origin`: `https://github.com/DigestWorks/IssueDigest.git` · fetch/push 연결 확인.
- 브랜치: `docs/issuedigest-implementation-plan`. 기존 Draft PR #1에서 계획과 준비 내용을 함께 검토한다.
- 웹·API·워커·도메인·연결기·에이전트·UI·운영·평가 폴더와 책임 README를 추가했다. 의존성·실행 코드·배포 구성은 아직 없다.
- `AGENTS.md`와 문서 안내에 읽는 순서·결정·작업·검증·인계 방법을 정했다. Linear는 사용하지 않는다.
- 검증: 로컬 문서 링크·디렉터리 경로, Git 연결, 변경 공백, 비밀 설정·생성 파일 제외 규칙 확인. 실행 가능한 앱이 없어 런타임 테스트는 수행하지 않았다.
- 다음 행동: 공유 계약·언어별 개발 설정부터 구성하고 실제 실행·타입·테스트 결과를 기록한다.
- Sites: 이번 준비 내용의 요약 반영 대기. 결정·진행의 최신 원본은 이 저장소다.

## 2026-10-11 · 계획·배포 정리

- 조직·서비스·새 저장소 지정 반영: DigestWorks / IssueDigest.
- 첫 사용자: 우리 둘의 조사·근거 비교. 월 운영비 상한: 10만 원.
- 기존 백엔드·AI 파이프라인 서버 존재 확인. 상세 정보는 사용자 요청에 따라 추후 반영.
- 구현 계획·요구사항·결정·작업·와이어프레임 기록 작성.
- 와이어프레임 Vercel 프로젝트의 `paused=true`, 배포 삭제·자동 Git 연결 해제 검증. 실행 코드·개인 저장소는 유지.
- 계획 초안 PR과 IssueDigest 계획 사이트를 게시했다. Sites v15 배포 성공을 확인했다.

## 게시·검토

- 계획 PR: [#1 · 구현 계획과 결정·진행 기록](https://github.com/DigestWorks/IssueDigest/pull/1) · Draft, 병합 전.
- Sites: [IssueDigest 구현 계획](https://lawdigest-rebuild-plan.ijaesinii.chatgpt.site/). 초기 계약 단계에서 v20 공개 게시에 성공했다. 이후 게시 버전은 각 날짜의 기록과 현재 작업을 따른다. 원문·파싱·인용과 개체·주장·관계·비교 계약·검증·PR 요약을 반영했다. 계획·개발 기반 상태와 저장소 문서·PR 검토 경로를 반영했다.
- 구현 시작: 로컬 폴더·협업 문서와 웹·API·상태 계약·개발 검증 기반 완료. 실제 스모크 결과·코드 검토는 개발 기반 작업에 기록한다. PR #1~#5는 Draft이며 병합하지 않았다.

## 서버 정보를 기다리지 않고 진행 가능한 항목

- 기준 데이터·인용·실행 이벤트·화면 명세 계약 검토.
- 기존 수집/가공 규칙과 회귀 테스트의 재사용 범위 평가.
- 첫 이슈·대표 질문·원문 조건 선정과 실제 평가셋 준비.
- 검색·작업 복구·권한·비용의 결정 실험 설계.

유료 외부 호출이나 운영 서버 설치를 시작한 것으로 표시하지 않는다.

## 게시 검증 증거

- Sites v20 source: `d5ee646d64f65fa2dbc262d08a478dbc788e155a`, saved version `appgprj_6ac612dd42708191a7a0c8377be64d48~appgver_c69a26fc4d788191a2c2b21dc7ceafc9`, deployment `appgdep_6acb93b276408191ba940bc1a5681c61`, 상태 `succeeded` (2026-10-11 22:48:50 한국 시간). 기존 공개 설정 유지. 1366×900·390×844에서 가로 넘침 없음, 제품 계약 4행·최종 테스트 수·PR #5·이전 v19 보존 링크 정상, 현재/보존 문서 로컬 파일 링크·anchor 정상, 콘솔 오류/경고 0건. 사본 기준 `06dda300bb5171e5f41cf94e24338aa26f682d61`; 최신 기록은 저장소 원본이다.
- 최종 실행 코드 `e902cb4`: 구현자·컨트롤러 전체 검사 각각 통과(393 Python + 60 JS), 독립 작업·전체 변경·지적 보완 후 수정 부분 리뷰 통과. [코드 CI #38144301870](https://github.com/DigestWorks/IssueDigest/actions/runs/38144301870) 성공. 이후 변경은 문서·게시 기록만이다.
- 사용자 폴더 `/data/lawdigest/IssueDigest`의 `feat/research-contracts`: 실제 API `/openapi.json`과 생성 계약이 동일하고 ResearchBundle/ComparisonAssessment 등 새 모델과 기존 두 HTTP 경로만 존재, 웹 HTTP 200 확인. 개발 서버 5173/8000은 로컬 확인용이며 운영 배포가 아니다. 별도 작업 공간의 리뷰/RED·GREEN 기록은 PR 병합 전까지 보존한다.

- Sites v19 source: `36ece7df45854a5db46d1c9690641a3d5bfd09d9`, deployment `appgdep_6acb7b68bcb08191a9b187bc7327f92e`, 상태 `succeeded` (2026-10-11 12:05 UTC). 기존 공개 설정 유지. 로컬 1366×900·390×844에서 새 계약 요약·내부 anchor와 보존 파일 링크 정상, 가로 넘침 없음, 콘솔 오류/경고 0건. v18 이전 조사안을 별도 보존했다. 저장소 원본/공개 사본 기준을 구분했다.
- 원격 검증: 구현 `9271a0a` CI #38137640138, 검토/PR 문서 `63f88fe` CI #38137818441 성공. 제품 구현 코드는 독립 작업/전체 리뷰 이후 변경하지 않았다.
- 사용자 폴더의 실제 API `/openapi.json`에서 EvidenceBundle과 기존 상태 경로만 확인, 웹 HTTP200 확인. 개발 서버는 로컬 5173/8000에서 기동 중이며 운영 배포가 아니다.

- Sites v18 source: `02565938f167a9a6c0c5203b5bfdf6569640e8f6`, deployment `appgdep_6acb6fc608108191b1f9a302100aed7b`, 상태 `succeeded`. 기존 공개 설정 유지. 1366×900·390×844에서 가로 넘침 없음, 새 요약 4행·전체 내부 링크 정상, 콘솔 오류/경고 0건 확인.

- Sites v17 source: `721cf362a2d61a7aa2a7bb6013e18a04857ff700`, deployment `appgdep_6acb6a2969d08191b6f8999e42beb5a4`, 상태 `succeeded` (2026-10-11 10:51 UTC). 기존 공개 설정을 유지했다. 1366×900·390×844에서 가로 넘침 없음·내부 링크 정상·콘솔 오류/경고 0건을 확인했다. 아래 v15 증거는 이전 게시 기록이다.

- Sites v15 source: `a96fae750ac020212d239e3d69344718cd6c3f02`, deployment `appgdep_6acb5724c784819184713ada7b2a8a8a`, 상태 `succeeded`.
- Vercel: 배포 목록 0개, `paused=true`, Git 연결 없음. 대표 주소와 두 과거 배포 주소는 HTTP 404 `DEPLOYMENT_NOT_FOUND`.
- 화면: 1366×1000·390×844에서 문서 가로 넘침 없음, 내부 메뉴 이동 확인, 콘솔 오류 0건. 문서 링크·보존 원문·계획 사본 일치 확인.


## 2026-10-12 · 사용자 폴더 연결·게시 준비

- 사용자 폴더 `/data/lawdigest/IssueDigest`의 깨끗한 상태를 확인하고 `feat/execution-contracts`를 연결했다. 격리 구현 폴더는 같은 커밋에 detached로 보존했다. 기존에 이 작업이 실행한 API 프로세스만 중지하고 새 브랜치의 통합 개발 실행을 기동했다. 실제 `/openapi.json` HTTP 200과 생성 JSON의 정확한 일치, RunHistory/RunExecutionBundle/CanvasBundle/UsageBook/BudgetAssessment 및 차트 minItems2·기존 HTTP 두 경로를 확인했다. 웹 HTTP 200. 새로운 제품 화면/AI 실행 검증은 아니다.
- 검토된 구현 `e2255d7`의 [GitHub CI #38150424568](https://github.com/DigestWorks/IssueDigest/actions/runs/38150424568) 성공. Docs-only 인계 커밋 뒤의 최종 HEAD CI는 마지막에 다시 확인한다. Sites의 이전 v20 기록을 보존하고 새 공개 요약·docs 사본 게시를 준비 중이다. 결합 체크는 게시 성공 후 처리한다.


## 2026-10-12 · 실행 계약 결합 완료·Sites 게시

- C1~C5의 구현·독립 작업/수정 범위/전체 변경 리뷰·Draft PR #6·사용자 폴더/실제 API 확인·Sites 공개 게시를 마쳤다. 최종 code 검증은 `e2255d7`의 컨트롤러 전체 672 Python + 60 JS 및 lint/타입/SPA/drift. 공급자 호출·실제 과금·저장·SSE·인증·renderer/AI·전체 P1은 미완료다.
- [Sites v21](https://lawdigest-rebuild-plan.ijaesinii.chatgpt.site/) 공개 게시 성공. source `2d5d6afc7ab659985e71bd9439b972b73ab4f5a0`, saved version `appgprj_6ac612dd42708191a7a0c8377be64d48~appgver_2819fa8720c481918101b0b01fab19dc`, deployment `appgdep_6acba95b486c8191b665b1b05bd473f8`의 native succeeded를 확인했다. 이전 v20을 추가 보존하고 v14/v18/v19·데이터/와이어프레임 기록을 유지했다. docs 사본은 `cac6258` 기준이며 대기 표시는 그 시점의 상태다. 최신 상태는 이 원본/PR에서 확인한다. 데스크톱1366/모바일390·가로 넘침 없음·계약4행·672/60·PR6/이전 기록·console0·로컬 링크/anchor 검사 통과.
- 구현·Root 연결 문서 커밋 `cac6258`의 [CI #38150676791](https://github.com/DigestWorks/IssueDigest/actions/runs/38150676791) 성공. 마지막 게시 기록 커밋의 exact-HEAD check는 PR에서 확인한다. 앱 자동 PR 첨부/사이트 열기 요청이 응답하지 않아 직접 URL을 공유한다. PR을 병합하지 않았다. 격리 폴더와 이 작업의 검토/실행 증거를 보존한다.
