# 질문·브리핑 개발 전환 사전 검증

2026-10-26. [작업 범위](../changes/question-web-development.md).

개인 개발 서버는 기존 schema0009·이전 API/worker/웹으로 유지했다. 현재 활성 research와 DBOS workflow는0이었다. 기존 앱 역할은 DB/public CREATE가 없고 개발자에게는 기존 소유 역할을 사용할 권한이 있다. 새 역할/관리자 권한을 요청하지 않았다.

## 확인한 범위

- 제품9170e06을 별도 서버 worktree에 고정하고 Node24.21.0/npm11.19.0·locked Python 환경·정적 빌드를 확인했다. 기존 실행 프로세스와 수집기/cron은 건드리지 않았다.
- 서버 밖 full/app archive를 보관하고 별도 PostgreSQL18.6에 app archive를 복원했다. 기존23테이블 row hash/count는 기존 감사 규칙의 auth_sessions.last_activity_at 제외 기준으로 일치했다. vector를 제외한 app 복원이며 역할/vector 전체 재해복구 검증은 아니다.
- 복원한 전용 DB에서 기존0010~0012와 별도 DBOS schema만 준비했다. 기존23테이블의 같은 정규화 비교와 이전 DBOS 전체 테이블의 행 해시를 유지했다. 신규3앱 테이블·새 workflow는 모두0이다.
- 합성 앱 역할의 새3테이블 SELECT/INSERT/UPDATE를 확인했다. DB CREATE·public/dedicated schema CREATE·새 public 테이블 DELETE는 거부됐고 네 실제 금지 시도의 SQLSTATE는42501이었다. DBOS 권한은 SDK의 새 schema 내부 table/sequence/function/default grants이며 기존 public CREATE/DDL은 부여하지 않았다. 실제 서버의 기존 앱 권한을 합성 역할 권한으로 대체하지 않는다.
- 실제 configured API lifespan과 소유 worker를 시작하고 정상 종료했다. 합성 OAuth/API 키와 외부 socket 차단을 사용했고 외부 요청0, 생성/세션/작업 제출0이다.
- 독립 검토에서 상속된 DBOS schema 설정으로 다른 schema가 시작될 수 있는 리허설 하네스 문제를 보완했다. 잘못된 상속값을 주입하고 고정 schema 덮어쓰기·파싱 결과·무관 schema 미생성·재실행 보존을 확인했다. 보존 주장은 활동 시각 제외를 명시했다. 재검토 C0I0M0다.

## 남은 실제 전환 조건

같은 사용자 OpenAI 키의 모델 조회가 api.model.read 부족403을 반환했다. 인증 없는 동일 API의401도 확인해 일반 연결 실패와 구분했다. 서버 키는 사용자가 제공한 키와 동일하다. 모델 부재·Responses 쓰기 거부로 단정하지 않으며 모델 조회 권한 갱신이 필요하다. 생성은 호출하지 않았다.

권한 갱신 뒤 실제 모델 사용 가능 여부와 최종 복귀/전환 절차를 확인하고, 서버 DB migration·단일 executor 전환·HTTPS/자산/세션/공개 경계를 검증해야 한다. 준비된 소스나 local rehearsal 성공을 개발 사이트 적용·실제 로그인·유료 모델 의미 품질 완료로 표시하지 않는다.

이번 변경은 운영 준비 문서뿐이다. 이전 전체10,327개로 검증한 제품537파일은 byte-identical이며 전체 제품 검사를 반복했다고 주장하지 않는다. 검증용 복원 컨테이너/익명volume과 포트는 정리하고 백업·검증 기록만 비공개로 보존했다. 계획판 게시 여부는 진행 기록을 따른다.
