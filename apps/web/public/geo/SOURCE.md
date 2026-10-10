# 지도 경계 데이터 출처

## seoul-gu.json

- 내용: 서울특별시 자치구 25개 경계(단순화), GeoJSON FeatureCollection
- 원본 파일: https://github.com/southkorea/seoul-maps — `kostat/2013/json/seoul_municipalities_geo_simple.json`
- 받은 날짜: 2026-10-11, 57,732 bytes, 내용 수정 없이 파일 이름만 바꿈
- 저장소 라이선스: README 표기 Apache License 2.0 (저작자 Lucy Park)
- 원자료: 통계청 센서스용 행정구역경계(2013)
- 속성: `code`(통계청 행정구역 코드), `name`, `name_eng`, `base_year`

원자료(통계청) 자체의 이용 조건은 확인하지 않았다. 샘플 데이터 프로토타입에서만 쓰고,
실제 서비스에 쓰기 전에 원자료 이용 조건과 최신 경계를 확인한다.
