# 台中市房價趨勢追蹤

以內政部「不動產交易實價登錄」開放資料為主軸，追蹤台中市各行政區房價趨勢。

- **資料處理（Python）**：下載、清洗、正規化實價登錄資料，存入 SQLite，並彙整成前端可用的趨勢 JSON。
- **視覺化（Node.js）**：Express 伺服器 + Chart.js 儀表板，呈現全市與各行政區的房價趨勢。

## 資料來源

[內政部不動產交易實價查詢服務網](https://plvr.land.moi.gov.tw/DownloadOpenData) 提供的**季別批次開放資料**（依 101S1 ~ 最新季持續更新），只下載台中市（縣市代碼 `B`）的**不動產買賣（成屋）**資料（`b_lvr_land_a.csv`），排除純土地、純車位交易。

- 每坪單價計算方式：`(總價元 - 車位總價元) / 建物移轉總面積(坪)`，避免車位價格拉高房價統計。
- 只保留 `建物移轉總面積 > 0` 的交易（即含建物之買賣案件）。
- 過濾掉原始資料中偶爾出現的申報錯誤日期（例如年份誤植、超出季別合理範圍）。

## 專案結構

```
house_price/
├── python/                 # 資料下載、清洗、彙整
│   ├── config.py
│   ├── downloader.py       # 下載各季別 zip 並解壓 CSV
│   ├── etl.py               # 清洗正規化，寫入 SQLite
│   ├── aggregate.py         # 依行政區/月份彙整，輸出 trends.json
│   └── run_pipeline.py      # 一鍵執行：下載 -> 清洗 -> 彙整
├── data/
│   ├── raw/                 # 下載的原始 CSV（依季別分資料夾）
│   └── processed/
│       ├── house_price.db   # SQLite 資料庫
│       └── trends.json      # 給前端使用的彙整資料
└── dashboard/                # Node.js 視覺化儀表板
    ├── server.js
    └── public/
        ├── index.html
        ├── main.js
        └── style.css
```

## 使用方式

### 1. 執行資料管線（Python）

```bash
cd house_price
python3 -m venv .venv
./.venv/bin/pip install -r python/requirements.txt

cd python
../.venv/bin/python run_pipeline.py            # 首次執行：下載所有可用季別（101S1 ~ 最新季）
../.venv/bin/python run_pipeline.py --latest 4 # 例行更新：只抓最近 4 季
```

執行完成後會產生 `data/processed/house_price.db` 與 `data/processed/trends.json`。

### 2. 啟動儀表板（Node.js）

```bash
cd house_price/dashboard
npm install
npm start
```

開啟 http://localhost:3000 即可看到：

- 全市房價趨勢折線圖（每坪單價）
- 各行政區最新月份房價排行
- 可自由勾選行政區比較長期趨勢

## 資料更新

實價登錄開放資料每月 1、11、21 日更新當期（本季）資料，季別資料則於季末後定期發布最終版。建議定期執行 `run_pipeline.py --latest 2` 取得最新一兩季資料並重新產生 `trends.json`。
