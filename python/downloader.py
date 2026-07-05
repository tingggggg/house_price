"""下載內政部不動產交易實價登錄開放資料（台中市，依季別）。"""
import re
import zipfile
from pathlib import Path

import requests

import config

SEASON_RE = re.compile(r'value="(\d{3}S[1-4])"')


def get_available_seasons() -> list[str]:
    """回傳網站上目前可下載的季別代碼，由舊到新排序，例如 ['101S1', ..., '115S2']。"""
    resp = requests.post(config.SEASON_LIST_URL, timeout=30)
    resp.raise_for_status()
    seasons = sorted(set(SEASON_RE.findall(resp.text)))
    if not seasons:
        raise RuntimeError("無法從實價登錄網站取得季別清單，頁面格式可能已變更")
    return seasons


def season_csv_path(season: str) -> Path:
    return config.RAW_DIR / season / f"{config.COUNTY_CODE.lower()}_lvr_land_{config.DEAL_TYPE}.csv"


def download_season(season: str, force: bool = False) -> Path | None:
    """下載並解壓指定季別的台中市買賣資料，回傳解壓後 CSV 路徑。

    若已存在則直接略過；若該季尚無台中市資料（開放資料系統上線初期部分季別無資料），回傳 None。
    """
    csv_path = season_csv_path(season)
    if csv_path.exists() and not force:
        return csv_path

    season_dir = config.RAW_DIR / season
    season_dir.mkdir(parents=True, exist_ok=True)
    zip_path = season_dir / "lvr_landcsv.zip"

    resp = requests.get(
        config.SEASON_DOWNLOAD_URL,
        params={"type": "season", "fileName": season},
        timeout=120,
    )
    resp.raise_for_status()
    if resp.content[:2] != b"PK":
        raise RuntimeError(f"季別 {season} 下載失敗，伺服器未回傳 zip 檔（可能季別不存在）")
    zip_path.write_bytes(resp.content)

    member = f"{config.COUNTY_CODE.lower()}_lvr_land_{config.DEAL_TYPE}.csv"
    with zipfile.ZipFile(zip_path) as zf:
        if member not in zf.namelist():
            zip_path.unlink()
            return None
        zf.extract(member, path=season_dir)
    zip_path.unlink()

    return csv_path


if __name__ == "__main__":
    seasons = get_available_seasons()
    print(f"可下載季別共 {len(seasons)} 季，範圍 {seasons[0]} ~ {seasons[-1]}")
