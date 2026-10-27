# 분석→최종 브리핑→SQL 재열람 실제 인수

2026-10-27. [직전 모델 비교](../research/question-model-comparison.md)의 standalone 분석 성공 뒤, [모델 지원 확장](question-astra-runtime.md)을 먼저 검증한 뒤 native 내구 실행 전체 경로를 소유 격리 DB에서 검증한다. OpenSpec root=null이며 private 검증 도구 TDD·독립 검토를 적용한다.

## 범위·불변 조건

원래 한 원문/질문·사전 기준을 유지하고 새 계획·새 실제 실행을 만든다. 이전 standalone 영수증을 DBOS journal/유료 호출로 주입하거나 기존 실패를 성공으로 바꾸지 않는다. 원래SDKv5/최종v1·지침/tool/schema/core와 공유 queue·버전/권한/원문 검증·예산 예약/재접수 계약은 변경하지 않는다.

모델gpt-6-astra·각 단계 예약1달러/합계2달러, 분석/최종 각각 POST 최대1·합계2, 각 출력4,000/timeout60초·전체supervisor600초를 유지한다. 실패/불명확 송신 후 재호출하지 않는다. 기존 전체 요청 한도·공백256·retry0·strict·추론low·service default·storefalse/backgroundfalse는 그대로다. 각 요청의 보수 비용 상한0.70달러는 직전 공식 단가 가정과 분리 기록한다.

PG18.6/기존 고정 이미지의 소유 QA DB·새 DBOS schema·합성 신원만 사용한다. 공동DB/개발 서버/세션·현재 모델 설정·main/운영·Actions는 바꾸지 않는다. DB migration0015는 이 QA DB에만 적용한다.

## 사전 gate

직전 검토한 interpreter/실제 의존성/제품 import 위치 동결·타입을 보존하는 JSON 비교·최적화 모드 거부·fork supervisor/모든 종료의 process group kill/reap·원응답8MiB tee·비밀값 비출력 장치를 재사용한다. 모델/endpoint·순서/호출 수·필수 설정을 전송 전에 검사한다. 분석 request는 직전 Astra body와 일치해야 한다. 최종은 고정 지침/tool/schema/control을 유지하고 현재 완료 분석으로 구성한 input·SQL prompt hash가 일치해야 한다.

실제 Docker ID/image/label/loopback port와 DB명/계정·PG/version/schema·빈 앱 테이블을 controller가 확인한다. DB 지정 env는 소유 QA만 허용한다. fake/real마다 격리 DB는 새로 비우며 fake dump/TOC를 먼저 보존한다. 최종 fake는 native 두 단계 ANSWER→SQL 저장/reader 동등→재접수 추가0과 cleanup을 확인하고 요청/영수증/원응답·닫힘·SQL 증거에 묶인 완료 attestation을 만든다. 독립 frozen-artifact 검토/정확 freeze 승인 전 실제 키를 읽지 않는다.

## 결과 기준

새 실제 분석→최종 ANSWER 영수증·SQL hash·현재 권한/원문에 따른 reader의 전체 JSON 동등·같은 요청 재접수 추가 호출0을 확인한다. SQL/usage/예약·journal·원응답/닫힘·실제/모의 dump를 보존하고 소유 QA/volume만 정리한다.

구조 수용과 내용 검토를 분리한다. 분석 필수3단위/나머지9·최종 사용자 문장에 나타난 대상/조건/각 상한/불확실성·인용 연결을 별도 평가한다. backing canonical에 보존됐다는 이유만으로 최종 자유 문장 의미를 통과시키지 않는다. 필수 조건 누락/왜곡은 그대로 기록하고 재작성/자동수리하지 않는다. curated 한 질문의 AI 개발판정이며 사람/맹검·일반 품질/신뢰도 인증은 아니다. 실제 앱/로그인/UI 인수는 별도다.

## 작업

- [ ] 최신 사전 gate와 기존 native SQL 경로를 재사용한 private 도구·TDD/독립 검토.
- [ ] 소유 QA attestation/0015·동결/전체 모의·덤프/리셋·독립 사전 승인.
- [ ] 제한 새 실제 분석1/최종1 이하·무재시도·SQL 저장/재열람/재접수 확인.
- [ ] 별도 결과/내용 검토·기록/PR/Sites·과거/제품 보존·소유 QA 정리.

## 적용 경계

전체 인수가 성공하더라도 자동 공개/현재 앱 전환은 하지 않는다. 현재 앱 적용에는 공동DB 백업/복원·migration·가격/예산 설정·실제 사용자 화면 확인이 필요하다. 실패하면 관측 단계·미관측 비용/usage를 보존하고 그 이후 성공을 주장하지 않는다.
