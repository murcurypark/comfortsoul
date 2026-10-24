"""wedding_data DB에서 시세 참고용 집계값만 뽑아 index.html에 넣는다.

사용법: python3 tools/build_market.py path/to/wedding_data_clean.db

index.html 의 <script id="market-data" type="application/json"> ... </script> 내용을 교체한다.
업체 연락처, 후기 작성자 등 원본 행 데이터는 넣지 않는다.
"""
import json
import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HTML = ROOT / "index.html"

# unit_price / sdeme_price 의 area 이름 → 페이지에서 쓰는 지역 키
AREA_KEYS = {
    "전국": "nation",
    "서울": "seoul",
    "경인": "gyeongin",
    "4대 광역시·통합특별시": "metro",
    "이외 지역": "other",
}
AREA_LABELS = {
    "nation": "전국 평균",
    "seoul": "서울",
    "gyeongin": "경기·인천",
    "metro": "광역시 (부산·대구·광주·대전·울산)",
    "other": "그 외 지역",
}
# optional 테이블 컬럼 → 지역 키
OPT_COLS = {"nationwide": "nation", "seoul": "seoul", "gyeongin": "gyeongin", "metro": "metro", "other": "other"}
# NH농협은행 지역별 평균 축의금(만원). 광역시는 부산·광주 평균, 그 외는 전국 평균 사용
GIFT_METRICS = {"seoul": "서울 평균 축의금", "gyeongin": "인천 평균 축의금"}


def rows(c, q, *a):
    cur = c.execute(q, a)
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


def survey(c, org, metric):
    r = c.execute("select value from survey where org=? and metric=?", (org, metric)).fetchone()
    return r[0] if r else None


def build(db):
    c = sqlite3.connect(f"file:{db}?mode=ro", uri=True)

    areas = {}
    for u in rows(c, "select * from unit_price"):
        k = AREA_KEYS[u["area"]]
        areas[k] = {"label": AREA_LABELS[k], "hall": u["hall_med"], "guarantee": u["guarantee_guests"], "perGuest": u["per_guest"]}
    for s in rows(c, "select * from sdeme_price"):
        k = AREA_KEYS[s["area"]]
        areas[k].update({"sdeme": s["sdeme_med"], "dress": s["dress_med"], "studio": s["studio_med"]})

    nation_gift = survey(c, "NH농협은행", "평균 축의금")
    gifts = {k: survey(c, "NH농협은행", m) for k, m in GIFT_METRICS.items()}
    busan, gwangju = survey(c, "NH농협은행", "부산 평균 축의금"), survey(c, "NH농협은행", "광주 평균 축의금")
    gifts["metro"] = round((busan + gwangju) / 2, 1)
    gifts["other"] = gifts["nation"] = nation_gift
    for k in areas:
        areas[k]["gift"] = gifts[k]

    optional = {}
    for o in rows(c, "select * from optional"):
        optional[o["item"]] = {OPT_COLS[col]: o[col] for col in OPT_COLS}

    monthly = [{"m": r["month"], "hall": r["hall_median"], "n": r["hall_n"], "sdeme": r["sdeme_median"]}
               for r in rows(c, "select * from monthly order by month")]

    def s(org, metric):
        return survey(c, org, metric)

    surveys = {
        "duo": {"label": "듀오 2026 (신혼부부 1,000명)", "hall": s("듀오", "예식홀"), "sdeme": s("듀오", "웨딩패키지(스튜디오+드레스+메이크업)"),
                "gifts": s("듀오", "예물"), "yedan": s("듀오", "예단"), "ibaji": s("듀오", "이바지"), "honsu": s("듀오", "혼수"),
                "honeymoon": s("듀오", "신혼여행"), "total": s("듀오", "주택자금 제외 결혼비용"), "small": s("듀오", "작은 결혼식 예상 비용")},
        "gayeon": {"label": "가연 2024 (기혼 1,000명)", "hall": s("가연", "예식장"), "sdeme": s("가연", "스드메"),
                   "gifts": s("가연", "예물"), "yedan": s("가연", "예단"), "honsu": s("가연", "혼수"),
                   "total": s("가연", "결혼 준비비용(신혼집 제외)")},
    }
    meal = {"코스": s("한국소비자원", "코스식 1인 식대 평균"), "뷔페": s("한국소비자원", "뷔페식 1인 식대 평균"),
            "한상차림": s("한국소비자원", "한상차림 1인 식대 평균")}
    season = {"peak": s("한국소비자원", "성수기 총 계약금액 중간값"), "off": s("한국소비자원", "비수기 총 계약금액 중간값")}

    cost = {r["item"]: {"lo": r["min_val"], "hi": r["max_val"], "basis": r["basis"]}
            for r in rows(c, "select item,min_val,max_val,basis from cost_items")}

    extra = [{"cat": r["category"], "contract": r["contract_price"], "final": r["final_price"], "diff": r["diff_amount"],
              "pct": r["diff_pct"], "note": r["note"], "src": r["src_name"], "url": r["src_url"]}
             for r in rows(c, "select v.*, r.src_url from v_extra_fee v join reviews r using (review_id)")]

    support = [{"org": r["org"], "metric": r["metric"], "value": r["value"], "note": r["note"]}
               for r in rows(c, "select org,metric,value,note from survey where org in ('서울시','구미시')")]

    scen = [{"name": r["name"], "guests": r["guests"], "total": r["total_est"], "notes": r["notes"]}
            for r in rows(c, "select * from scenarios where total_est is not null order by scen_id")]

    src_ids = (1, 3, 4, 7, 8, 9, 23, 26)
    sources = [{"name": r["name"], "url": r["url"]}
               for r in rows(c, f"select name,url from sources where src_id in ({','.join(map(str, src_ids))}) order by src_id")]
    collected = c.execute("select max(collected_on) from sources").fetchone()[0]

    return {"areas": areas, "optional": optional, "monthly": monthly, "surveys": surveys, "meal": meal, "season": season,
            "cost": cost, "extra": extra, "support": support, "scenarios": scen, "sources": sources, "collected": collected}


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    data = json.dumps(build(sys.argv[1]), ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    html = HTML.read_text(encoding="utf-8")
    pat = re.compile(r'(<script id="market-data" type="application/json">)(.*?)(</script>)', re.S)
    if not pat.search(html):
        sys.exit("index.html 에 market-data 스크립트 태그가 없습니다.")
    HTML.write_text(pat.sub(lambda m: m.group(1) + data + m.group(3), html, count=1), encoding="utf-8")
    print(f"market-data 갱신: {len(data):,} bytes")


if __name__ == "__main__":
    main()
