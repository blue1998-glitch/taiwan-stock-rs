import os
import json
import time
import requests
import pandas as pd
import numpy as np
import yfinance as yf
from concurrent.futures import ThreadPoolExecutor, as_completed

TWSE_INDUSTRY_MAP = {
    "01": "水泥工業", "1": "水泥工業",
    "02": "食品工業", "2": "食品工業",
    "03": "塑膠工業", "3": "塑膠工業",
    "04": "紡織纖維", "4": "紡織纖維",
    "05": "電機機械", "5": "電機機械",
    "06": "電器電纜", "6": "電器電纜",
    "07": "化學工業", "7": "化學工業",
    "08": "玻璃陶瓷", "8": "玻璃陶瓷",
    "09": "造紙工業", "9": "造紙工業",
    "10": "鋼鐵工業",
    "11": "橡膠工業",
    "12": "汽車工業",
    "13": "電子工業",
    "14": "建材營造",
    "15": "航運業",
    "16": "觀光餐旅",
    "17": "金融保險",
    "18": "貿易百貨",
    "19": "綜合",
    "20": "其他",
    "21": "化學工業",
    "22": "生技醫療業",
    "23": "油電燃氣業",
    "24": "半導體業",
    "25": "電腦及週邊設備業",
    "26": "光電業",
    "27": "通信網路業",
    "28": "電子零組件業",
    "29": "電子通路業",
    "30": "資訊服務業",
    "31": "其他電子業",
    "32": "文化創意業",
    "33": "農業科技業",
    "34": "電子商務業",
    "35": "綠能環保",
    "36": "數位雲端",
    "37": "運動休閒",
    "38": "居家生活",
    "80": "管理股票",
    "91": "存託憑證(TDR)"
}

def clean_industry_name(raw_ind, sym="", name=""):
    raw_str = str(raw_ind).strip()
    if sym.startswith("91") or "-DR" in name or "DR" in name or raw_str == "91":
        return "存託憑證(TDR)"
    if raw_str in TWSE_INDUSTRY_MAP:
        return TWSE_INDUSTRY_MAP[raw_str]
    if raw_str.isdigit():
        return "綜合產業"
    return raw_str if raw_str else "綜合產業"

def get_stock_list():
    stocks = []
    try:
        r_twse = requests.get("https://openapi.twse.com.tw/v1/opendata/t187ap03_L", timeout=10).json()
        for item in r_twse:
            sym = str(item.get("公司代號", "")).strip()
            name = str(item.get("公司名稱", "")).strip()
            if len(sym) == 4 and sym.isdigit():
                stocks.append({
                    "symbol": sym,
                    "name": name,
                    "market": "上市",
                    "ticker": f"{sym}.TW",
                    "industry": clean_industry_name(item.get("產業別", ""), sym, name)
                })
    except Exception as e:
        print(f"TWSE API 讀取: {e}")

    try:
        r_tpex = requests.get("https://www.tpex.org.tw/openapi/v1/mopsfin_t187ap03_O", timeout=10).json()
        for item in r_tpex:
            sym = str(item.get("SecuritiesCompanyCode", "")).strip()
            name = str(item.get("CompanyName", "")).strip()
            if len(sym) == 4 and sym.isdigit():
                stocks.append({
                    "symbol": sym,
                    "name": name,
                    "market": "上櫃",
                    "ticker": f"{sym}.TWO",
                    "industry": clean_industry_name(item.get("Industry", ""), sym, name)
                })
    except Exception as e:
        print(f"TPEx API 讀取: {e}")

    return pd.DataFrame(stocks)

def download_batch_prices(chunk):
    try:
        data = yf.download(
            chunk,
            period="3mo",
            interval="1d",
            progress=False,
            auto_adjust=True,
            threads=True,
            timeout=8
        )
        if isinstance(data.columns, pd.MultiIndex):
            if "Close" in data.columns.levels[0]:
                return data["Close"]
            else:
                return data.xs("Close", level=0, axis=1)
        elif "Close" in data:
            return data["Close"]
        return data
    except Exception as e:
        return pd.DataFrame()

def calculate_real_market_rs():
    print("⚡ 啟動全市場高速計算引擎...")

    if not os.path.exists("data/theme_mapping.json"):
        import sys
        sys.path.append(".")
        from data.build_themes import generate_theme_database
        generate_theme_database()

    with open("data/theme_mapping.json", "r", encoding="utf-8") as f:
        theme_map = json.load(f)

    stock_df = get_stock_list()
    if stock_df.empty:
        print("❌ 無法取得股票清單")
        return

    print(f"📋 共取得全市場 {len(stock_df)} 檔上市櫃個股，啟動多線程下載...")

    tickers = stock_df["ticker"].tolist()
    chunk_size = 60
    chunks = [tickers[i:i + chunk_size] for i in range(0, len(tickers), chunk_size)]

    all_close_data = pd.DataFrame()

    with ThreadPoolExecutor(max_workers=6) as executor:
        future_to_chunk = {executor.submit(download_batch_prices, chunk): i for i, chunk in enumerate(chunks)}
        for future in as_completed(future_to_chunk):
            idx = future_to_chunk[future]
            try:
                chunk_res = future.result()
                if not chunk_res.empty:
                    all_close_data = pd.concat([all_close_data, chunk_res], axis=1)
                print(f"  ✔ 批次 {idx+1}/{len(chunks)} 下載完成")
            except Exception as exc:
                print(f"  ⚠ 批次 {idx+1} 略過: {exc}")

    print("📊 股價數據彙整完畢，計算動能評分...")

    valid_results = []
    for _, row in stock_df.iterrows():
        sym = row["symbol"]
        name = row["name"]
        mkt = row["market"]
        ticker = row["ticker"]
        ind = row["industry"]

        tag_info = theme_map.get(sym, {
            "main_industry": ind,
            "sub_industry": f"{ind}-一般應用",
            "themes": [f"{ind}族群", f"{ind}供應鏈"]
        })

        if ticker not in all_close_data.columns:
            continue

        prices = all_close_data[ticker].dropna()
        n = len(prices)

        if n < 5:
            continue

        cur_p = float(prices.iloc[-1])
        if cur_p <= 0 or np.isnan(cur_p):
            continue

        r_5 = float((cur_p - prices.iloc[-5]) / prices.iloc[-5] * 100)
        r_20 = float((cur_p - prices.iloc[-20]) / prices.iloc[-20] * 100) if n >= 20 else r_5
        r_60 = float((cur_p - prices.iloc[-60]) / prices.iloc[-60] * 100) if n >= 60 else r_20

        composite_score = (r_5 * 0.20) + (r_20 * 0.50) + (r_60 * 0.30)

        valid_results.append({
            "symbol": sym,
            "name": name,
            "market": mkt,
            "close_price": round(cur_p, 2),
            "r_5d": round(r_5, 2),
            "r_20d": round(r_20, 2),
            "r_60d": round(r_60, 2),
            "score": round(composite_score, 2),
            "main_industry": tag_info["main_industry"],
            "sub_industry": tag_info["sub_industry"],
            "themes": tag_info["themes"]
        })

    df_rank = pd.DataFrame(valid_results)
    if df_rank.empty:
        print("❌ 計算結果為空")
        return

    df_rank["rs_rating"] = pd.qcut(
        df_rank["score"].rank(method="first"),
        q=99,
        labels=range(1, 100)
    ).astype(int)

    df_rank = df_rank.sort_values(by=["rs_rating", "score"], ascending=[False, False])

    output_data = df_rank.to_dict(orient="records")
    with open("market_rankings.json", "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    print(f"🎉 全市場 RS 評分計算完成！共評比 {len(output_data)} 檔標的。")

if __name__ == "__main__":
    calculate_real_market_rs()
