"""將台中市實價登錄買賣 CSV 清洗、正規化後寫入 SQLite。"""
import re
import sqlite3

import pandas as pd

import config

CN_DIGITS = {"零": 0, "一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS transactions (
    serial_no TEXT PRIMARY KEY,
    season TEXT,
    district TEXT,
    transaction_sign TEXT,
    address TEXT,
    transaction_date TEXT,
    building_type TEXT,
    main_use TEXT,
    floor_count INTEGER,
    building_area_m2 REAL,
    rooms INTEGER,
    halls INTEGER,
    baths INTEGER,
    total_price INTEGER,
    parking_price INTEGER,
    parking_area_m2 REAL,
    net_price INTEGER,
    unit_price_per_ping REAL,
    construction_date TEXT,
    is_house INTEGER
);
CREATE INDEX IF NOT EXISTS idx_transactions_district_date
    ON transactions(district, transaction_date);
"""


def cn_number_to_int(text) -> int | None:
    """將中文數字樓層（如「十二層」「二十一層」）轉為整數。"""
    if pd.isna(text):
        return None
    s = str(text).replace("層", "").strip()
    if not s:
        return None
    if s.isdigit():
        return int(s)

    total = 0
    section = 0
    unit_seen = False
    for ch in s:
        if ch in CN_DIGITS:
            section = CN_DIGITS[ch]
        elif ch == "十":
            section = (section or 1) * 10
            unit_seen = True
        elif ch == "百":
            section = (section or 1) * 100
            unit_seen = True
        else:
            continue
    total += section
    if not unit_seen and not total:
        return None
    return total if total else None


def roc_date_to_iso(value) -> str | None:
    """將民國年月日（例如 1150604）轉為 ISO 日期字串。原始資料偶有格式錯亂，一律視為無效值捨棄。"""
    if pd.isna(value):
        return None
    try:
        digits = str(int(float(value)))
    except (ValueError, TypeError):
        return None
    if len(digits) not in (6, 7) or digits == "0":
        return None
    year_len = len(digits) - 4
    roc_year, month, day = digits[:year_len], digits[year_len:year_len + 2], digits[year_len + 2:]
    try:
        year = int(roc_year) + 1911
        month_i, day_i = int(month), int(day)
        if not (1 <= month_i <= 12 and 1 <= day_i <= 31):
            return None
        return f"{year:04d}-{month_i:02d}-{day_i:02d}"
    except ValueError:
        return None


def roc_yearmonth_to_iso(value) -> str | None:
    """將民國年月（例如 1040803 為建築完成年月的日期格式）轉為 YYYY-MM。"""
    iso = roc_date_to_iso(value)
    return iso[:7] if iso else None


def load_season_dataframe(season: str) -> pd.DataFrame:
    from downloader import season_csv_path

    csv_path = season_csv_path(season)
    df = pd.read_csv(csv_path, encoding="utf-8-sig", skiprows=[1])
    # 歷年欄位名稱偶有括號差異（如「車位移轉總面積(平方公尺)」vs「車位移轉總面積平方公尺」），統一去除括號
    df.columns = [c.replace("(", "").replace(")", "") for c in df.columns]
    df = df[df["交易年月日"].notna()].copy()

    out = pd.DataFrame()
    out["serial_no"] = df["編號"]
    out["season"] = season
    out["district"] = df["鄉鎮市區"].str.strip()
    out["transaction_sign"] = df["交易標的"]
    out["address"] = df["土地位置建物門牌"]
    out["transaction_date"] = df["交易年月日"].apply(roc_date_to_iso)
    out["building_type"] = df["建物型態"]
    out["main_use"] = df["主要用途"]
    out["floor_count"] = df["總樓層數"].apply(cn_number_to_int)
    out["building_area_m2"] = pd.to_numeric(df["建物移轉總面積平方公尺"], errors="coerce").fillna(0.0)
    out["rooms"] = pd.to_numeric(df["建物現況格局-房"], errors="coerce")
    out["halls"] = pd.to_numeric(df["建物現況格局-廳"], errors="coerce")
    out["baths"] = pd.to_numeric(df["建物現況格局-衛"], errors="coerce")
    out["total_price"] = pd.to_numeric(df["總價元"], errors="coerce").fillna(0).astype(int)
    out["parking_price"] = pd.to_numeric(df["車位總價元"], errors="coerce").fillna(0).astype(int)
    out["parking_area_m2"] = pd.to_numeric(df["車位移轉總面積平方公尺"], errors="coerce").fillna(0.0)
    out["construction_date"] = df["建築完成年月"].apply(roc_yearmonth_to_iso)

    out["net_price"] = out["total_price"] - out["parking_price"]
    # 原始資料偶有建物面積誤植為極小值（如 0.02 平方公尺）造成單價異常放大，
    # 以 5 平方公尺（約 1.5 坪）作為合理房屋面積下限
    out["is_house"] = (out["building_area_m2"] >= 5).astype(int)

    unit_price_ping = out["net_price"] / out["building_area_m2"] * config.PING_PER_SQM
    out["unit_price_per_ping"] = unit_price_ping.where(out["building_area_m2"] > 0)

    out = out.dropna(subset=["serial_no", "transaction_date"])

    # 開放資料自民國 100 年 11 月（101S1 季）才開始收錄，原始資料偶有申報人填錯年份
    # 導致的異常日期（過去或未來），一律過濾以免污染趨勢圖
    today = pd.Timestamp.now().strftime("%Y-%m-%d")
    out = out[(out["transaction_date"] >= "2011-11-01") & (out["transaction_date"] <= today)]

    return out


def upsert_dataframe(conn: sqlite3.Connection, df: pd.DataFrame) -> int:
    conn.executescript(CREATE_TABLE_SQL)
    records = df.to_dict("records")
    columns = list(df.columns)
    placeholders = ", ".join(["?"] * len(columns))
    col_list = ", ".join(columns)
    sql = f"INSERT OR REPLACE INTO transactions ({col_list}) VALUES ({placeholders})"
    conn.executemany(sql, [[r[c] for c in columns] for r in records])
    conn.commit()
    return len(records)


def run_etl(season: str, conn: sqlite3.Connection | None = None) -> int:
    own_conn = conn is None
    if own_conn:
        conn = sqlite3.connect(config.DB_PATH)
    try:
        df = load_season_dataframe(season)
        return upsert_dataframe(conn, df)
    finally:
        if own_conn:
            conn.close()


if __name__ == "__main__":
    import sys

    season = sys.argv[1] if len(sys.argv) > 1 else "115S2"
    n = run_etl(season)
    print(f"季別 {season} 匯入 {n} 筆交易紀錄")
