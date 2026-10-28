# 개발 앱의 검증한 질문 파이프라인 연결

2026-10-28 KST. [직전 실제 인수](../research/question-native-final-validation.md) 뒤 새 개발 요청이 Astra/v5 분석과 최종 생성으로 이어지도록 명시 설정을 연결한다. OpenSpec root=null이며 기존 승인된 개발 범위의 후속이다. main/운영·기존 실행/결과·공개 게시·로그인/세션·수집기는 유지한다.

## 계약

QuestionServiceConfig에 서버 전용 model 설정을 추가한다. 기본 Sol/근거v2와 각각0.50달러 예약을 유지한다. 명시 Astra는 근거v5만 허용하며 분석/최종 각각1달러를 예약한다. 임의 모델·Astra/legacy profile 조합은 시작 전에 거부한다. 비용을 브라우저가 정하거나 임의 예약을 낮추는 설정을 추가하지 않는다. 현재 모델이 바뀐 과거 동일 요청은 원래 identity/충돌 규칙을 따르고 재라벨/새 유료 재생을 하지 않는다.

Provider는 공식 endpoint·timeout60·retry0·명시 project/organization 없음·환경 proxy 미사용으로 구성해 직전 검증 전송 경계를 유지한다. 별도 opt-in factory·DBOS 큐/버전/잠금·해제 순서·API/DTO·웹 입력/로그인/권한/공개 경계는 유지한다.

개발 적용은 사전 read-only 실측→서버 밖 백업/별도 복원→활성 작업0→소유자 migration/최소 앱 권한·DBOS schema→고정 소스/환경/웹빌드 준비→개인 개발 전환·외부 HTTPS/질문/상태/재열람/인용 검증→사후 백업/복원 순서다. 실제 공유 DB reset·downgrade·자동 게시·실사용자 세션 위조는 금지한다. 기존 source/설정/static을 롤백용으로 보존하며 준비가 안 되면 현재 서비스 유지와 부족한 조건을 구체적으로 기록한다. 검증용 로그인은 격리 합성 환경에서만 생성한다.

## 작업

- [x] T1: 서비스 model/profile/예약·명시 전송 설정 TDD·기존 Sol 및 Astra HTTP 흐름 검증.
- [ ] T1 독립 검토·필요 범위 전체 검사/타입/빌드/OpenAPI.
- [ ] T2: 실제 서버 source/process/DB revision·권한·백업/복원 실측과 적용 계획 확정.
- [ ] T3: 준비 조건 충족 시 개인 개발 앱 연결·외부 검증·기록/PR/Sites. 미충족이면 기존 서비스 보존·부족 조건과 준비 산출물 기록.
