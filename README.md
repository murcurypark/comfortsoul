# comfortsoul

지수와 성수의 결혼준비 대시보드 (`index.html`, 브라우저에서 바로 열기)

## 시세 데이터 갱신

예산 옆의 참고 시세와 "시세 참고" 카드는 `wedding_data` SQLite DB에서 뽑은 집계값입니다.
DB가 바뀌면 아래 명령으로 `index.html` 안의 데이터를 다시 넣습니다.

```
python3 tools/build_market.py path/to/wedding_data_clean.db
```

DB 원본(업체 연락처, 후기 작성자 등)은 레포에 올리지 않고 집계값과 출처만 페이지에 들어갑니다.
