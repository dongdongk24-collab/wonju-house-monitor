# 원주시 부동산 모니터 - GitHub Pages 버전

GitHub Pages + GitHub Actions로 원주시 아파트/오피스텔 전세·반전세 매물을 주기적으로 확인해 보여주는 정적 웹사이트입니다.

## 조건

- 지역: 원주시
- 유형: 아파트, 오피스텔
- 전세: 1억 2천만 원 이하
- 반전세/월세: 보증금 1억 2천만 원 이하, 월세 20만 원 이하
- 갱신: GitHub Actions 스케줄 기준 30분마다

## GitHub Pages 켜는 방법

1. 저장소의 `Settings > Pages`로 이동합니다.
2. `Build and deployment`의 `Source`를 `GitHub Actions`로 선택합니다.
3. `Actions` 탭에서 `Update Naver Land Listings and Deploy Pages` 워크플로를 수동 실행하거나 30분 갱신을 기다립니다.

배포 후 주소는 아래 형태입니다.

```text
https://dongdongk24-collab.github.io/wonju-house-monitor/
```

## 파일 구조

```text
public/
  index.html
  styles.css
  app.js
  listings.json
scripts/
  fetch_naver_land.py
.github/workflows/
  update-listings.yml
```

## 주의

네이버 부동산은 공식 공개 API가 아니라 웹 화면에서 사용하는 내부 응답에 의존합니다. 네이버가 요청을 제한하거나 응답 형식을 바꾸면 `public/listings.json`에 오류 상태가 저장되고, 사이트 화면에 그 오류가 표시됩니다.
