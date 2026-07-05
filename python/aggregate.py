"""彙整各行政區房價趨勢，輸出給前端儀表板使用的 trends.json。"""
import json
import sqlite3
from datetime import datetime, timezone

import pandas as pd

import config


def load_house_transactions(conn: sqlite3.Connection) -> pd.DataFrame:
    query = """
        SELECT district, transaction_date, total_price, unit_price_per_ping, building_area_m2
        FROM transactions
        WHERE is_house = 1 AND unit_price_per_ping > 0
    """
    return pd.read_sql_query(query, conn)


def build_trends(df: pd.DataFrame) -> dict:
    df["month"] = df["transaction_date"].str.slice(0, 7)

    grouped = df.groupby(["district", "month"]).agg(
        avg_unit_price_ping=("unit_price_per_ping", "mean"),
        median_unit_price_ping=("unit_price_per_ping", "median"),
        median_total_price=("total_price", "median"),
        transaction_count=("total_price", "count"),
    ).reset_index()

    districts: dict[str, list[dict]] = {}
    for district, group in grouped.groupby("district"):
        rows = group.sort_values("month")
        districts[district] = [
            {
                "month": r.month,
                "avg_unit_price_ping": round(r.avg_unit_price_ping),
                "median_unit_price_ping": round(r.median_unit_price_ping),
                "median_total_price": int(r.median_total_price),
                "transaction_count": int(r.transaction_count),
            }
            for r in rows.itertuples()
        ]

    city_overview = (
        df.groupby("month")
        .agg(
            avg_unit_price_ping=("unit_price_per_ping", "mean"),
            median_unit_price_ping=("unit_price_per_ping", "median"),
            transaction_count=("total_price", "count"),
        )
        .reset_index()
        .sort_values("month")
    )
    city_overview_records = [
        {
            "month": r.month,
            "avg_unit_price_ping": round(r.avg_unit_price_ping),
            "median_unit_price_ping": round(r.median_unit_price_ping),
            "transaction_count": int(r.transaction_count),
        }
        for r in city_overview.itertuples()
    ]

    latest_month = df["month"].max()

    # 排行以近 3 個月彙整並取中位數，避免單月交易筆數過少造成排名劇烈波動
    recent_months = sorted(df["month"].unique())[-3:]
    recent = df[df["month"].isin(recent_months)]
    latest = (
        recent.groupby("district")
        .agg(
            median_unit_price_ping=("unit_price_per_ping", "median"),
            transaction_count=("total_price", "count"),
        )
        .reset_index()
    )
    latest = latest[latest["transaction_count"] >= 5].sort_values(
        "median_unit_price_ping", ascending=False
    )
    latest_ranking = [
        {
            "district": r.district,
            "median_unit_price_ping": round(r.median_unit_price_ping),
            "transaction_count": int(r.transaction_count),
        }
        for r in latest.itertuples()
    ]

    return {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "county": config.COUNTY_NAME,
        "latest_month": latest_month,
        "ranking_period": f"{recent_months[0]} ~ {recent_months[-1]}",
        "city_overview": city_overview_records,
        "latest_ranking": latest_ranking,
        "districts": districts,
    }


def run_aggregate() -> dict:
    conn = sqlite3.connect(config.DB_PATH)
    try:
        df = load_house_transactions(conn)
        trends = build_trends(df)
    finally:
        conn.close()

    config.TRENDS_JSON_PATH.write_text(
        json.dumps(trends, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return trends


if __name__ == "__main__":
    trends = run_aggregate()
    print(f"已輸出 {config.TRENDS_JSON_PATH}，共 {len(trends['districts'])} 個行政區")
