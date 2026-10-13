# IssueDigest

DigestWorks의 이슈 조사·근거 비교 서비스 풀스택 모노레포입니다. 현재는 개발 폴더와 협업 문서를 준비한 단계입니다. 실행 가능한 앱과 개발 명령은 아직 없습니다.

첫 사용자는 우리 둘이며, 실제 원자료에서 근거·관계·변화를 찾아 질문에 맞는 화면으로 탐색합니다. 프론트는 React Router, 백엔드는 Python/FastAPI, 그래프는 Neo4j를 사용합니다. 나머지 도구와 운영 배치는 검토 중입니다.

- [문서 안내·협업 방법](docs/README.md)
- [에이전트 지침](AGENTS.md)
- [구현 계획](docs/planning/implementation-plan.md)
- [요구사항·설계](docs/planning/requirements-design.md)
- [결정 기록](docs/planning/decisions.md)
- [작업 목록](docs/planning/tasks.md)
- [진행 기록](docs/planning/progress.md)
- [이전 기록·재사용 자산](docs/planning/archive.md)
- [공유 계획 사이트](https://lawdigest-rebuild-plan.ijaesinii.chatgpt.site/)

이전 와이어프레임은 별도 비공개 저장소의 코드로 보존하며 배포를 종료했습니다. 계획 문서는 서비스 기능의 구현 완료를 뜻하지 않습니다.

## 저장소 구조

```text
apps/
  web/                    React Router · React · TypeScript
  api/                    Python · FastAPI
  worker/                 수집·가공·투영·에이전트 작업
packages/
  domain/                 공통 도메인·계약
  connectors/             데이터 수집 연결기
  agents/                 에이전트·도구·결과 검증
  ui/                     생성 화면 명세·허용 컴포넌트
infra/                    배포·백업·운영 설정
tests/evaluation/         실제 근거와 평가 질문
docs/                     계획·결정·작업·진행 기록
AGENTS.md                 사람과 에이전트의 작업 기준
```

각 개발 폴더에는 책임과 현재 상태를 적은 README가 있습니다. Python·TypeScript 워크스페이스 설정과 의존성 고정은 기반 구현에서 추가합니다.

## 협업 기준

Linear 대신 이 저장소의 문서와 PR로 논의합니다. 결정·작업 상태의 원본은 `docs/`이며, Sites에는 이를 요약해 공유합니다. 작업을 시작할 때 [문서 안내](docs/README.md)를 읽고 관련 요구사항·결정·작업을 확인하세요.
