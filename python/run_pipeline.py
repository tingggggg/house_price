"""完整流程：下載 -> 清洗匯入 -> 彙整輸出。

用法：
    python run_pipeline.py               # 抓取所有可用季別（首次執行建議用此，會較久）
    python run_pipeline.py --latest 4    # 只抓最近 4 季（例行更新用）
    python run_pipeline.py --seasons 115S1 115S2   # 指定季別
"""
import argparse
import sqlite3

import config
import downloader
import etl
from aggregate import run_aggregate


def parse_args():
    parser = argparse.ArgumentParser(description="台中市實價登錄房價趨勢資料管線")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--latest", type=int, metavar="N", help="只處理最近 N 季")
    group.add_argument("--seasons", nargs="+", metavar="SEASON", help="指定要處理的季別，如 115S1 115S2")
    parser.add_argument("--force", action="store_true", help="即使本地已有資料也重新下載")
    return parser.parse_args()


def main():
    args = parse_args()

    all_seasons = downloader.get_available_seasons()
    if args.seasons:
        seasons = args.seasons
    elif args.latest:
        seasons = all_seasons[-args.latest:]
    else:
        seasons = all_seasons

    print(f"準備處理 {len(seasons)} 季：{seasons[0]} ~ {seasons[-1]}")

    conn = sqlite3.connect(config.DB_PATH)
    total = 0
    try:
        for i, season in enumerate(seasons, 1):
            print(f"[{i}/{len(seasons)}] 下載 {season} ...")
            csv_path = downloader.download_season(season, force=args.force)
            if csv_path is None:
                print("  -> 該季尚無台中市資料，略過")
                continue
            n = etl.run_etl(season, conn=conn)
            total += n
            print(f"  -> 匯入 {n} 筆")
    finally:
        conn.close()

    print(f"共匯入 {total} 筆交易紀錄，開始彙整趨勢資料 ...")
    trends = run_aggregate()
    print(f"完成！已輸出 {config.TRENDS_JSON_PATH}，涵蓋 {len(trends['districts'])} 個行政區，"
          f"最新月份 {trends['latest_month']}")


if __name__ == "__main__":
    main()
