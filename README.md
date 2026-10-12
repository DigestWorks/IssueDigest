# IssueDigest

IssueDigest는 여러 출처의 데이터를 연결해 이슈의 맥락과 근거를 제공하는 독립 프로젝트다.

- 저장소: https://github.com/DigestWorks/IssueDigest
- 현재 구현: 채팅과 3D 지도·온톨로지 시각화 프론트엔드 프로토타입
- 서버 자원과 비용: 프로젝트 전용으로 추가 확보

## 개발 실행

루트 `package.json`에 지정된 pnpm 버전을 사용한다.

```sh
pnpm install --frozen-lockfile
pnpm dev
```

`/`에서 채팅·시각화 프로토타입, `/map`에서 지도, `/style`에서 스타일 가이드를 확인한다. 프로토타입은 샘플 시나리오 이벤트를 재생한다. 실제 서버·DB·에이전트 연결은 후속 작업이다.

```sh
pnpm typecheck
pnpm test
pnpm build
```

## 작업 자료

- [제품 기획](docs/planning/2026-10-11-issuedigest-plan.md)
- [서버·데이터 연결 계획](docs/planning/2026-10-12-server-data-plan.md)
- [PoC 기술 검토](docs/research/2026-10-11-poc-feasibility.md)
- [스타일 가이드](docs/design/style-guide.md)
- [3D 지도 컨셉](docs/design/3d-map-concept.md)
- [프로토타입 스크린샷](docs/screenshots/)

기존 기획과 프로토타입의 커밋 이력을 가져왔으며, 초기 설계·계획 기록은 `.intent/`에 있다. 새 Git 워크트리는 루트 `worktree/` 아래에 만든다.
