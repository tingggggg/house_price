from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT_DIR / "data" / "raw"
PROCESSED_DIR = ROOT_DIR / "data" / "processed"
DB_PATH = PROCESSED_DIR / "house_price.db"
TRENDS_JSON_PATH = PROCESSED_DIR / "trends.json"

BASE_URL = "https://plvr.land.moi.gov.tw"
SEASON_LIST_URL = f"{BASE_URL}/DownloadSeason_ajax_list"
SEASON_DOWNLOAD_URL = f"{BASE_URL}/DownloadHistory"

# 內政部實價登錄開放資料中，台中市的縣市代碼為 "B"
COUNTY_CODE = "B"
COUNTY_NAME = "臺中市"

# 交易類別：a=不動產買賣, b=預售屋買賣, c=不動產租賃
# 房價趨勢以「不動產買賣（成屋）」為主軸
DEAL_TYPE = "a"

PING_PER_SQM = 3.305785

RAW_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
