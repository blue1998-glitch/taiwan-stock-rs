import os
import json
import time
import requests
import pandas as pd
import numpy as np
import yfinance as yf

# 官方產業代碼對照中文表
TWSE_INDUSTRY_MAP = {
    "01": "水泥工業", "1": "水泥工業", "02": "食品工業", "2": "食品工業",
    "03": "塑膠工業", "3": "塑膠工業", "04": "紡織纖維", "4": "紡織纖維",
    "05": "電機機械", "5": "電機機械", "06": "電器電纜", "6": "電器電纜",
    "07": "化學工業", "7": "化學工業", "08": "玻璃陶瓷", "8": "玻璃陶瓷",
    "09": "造紙工業", "9": "造紙工業", "10": "鋼鐵工業", "11": "橡膠工業",
    "12": "汽車工業", "13": "電子工業", "14": "建材營造", "15": "航運業",
    "16": "觀光餐旅", "17": "金融保險", "18": "貿易百貨", "19": "綜合",
    "20": "其他", "21": "化學工業", "22": "生技醫療業", "23": "油電燃氣業",
    "24": "半導體業", "25": "電腦及週邊設備業", "26": "光電業", "27": "通信網路業",
    "28": "電子零組件業", "29": "電子通路業", "30": "資訊服務業", "31": "其他電子業",
    "32": "文化創意業", "33": "農業科技業", "34": "電子商務業", "35": "綠能環保",
    "36": "數位雲端", "37": "運動休閒", "38": "居家生活"
}

def clean_industry_name(raw_ind):
    raw_str = str(raw_ind).strip()
    return TWSE_INDUSTRY_MAP.get(raw_str, raw_str if raw_str else "綜合產業")

def get_stock_list():
    """抓取全市場上市與上櫃股票清單"""
    stocks = []
    try:
        r_twse = requests.get("https://openapi.twse.com.tw/v1/opendata/t187ap03_L", timeout=12).json()
        for item in r_twse:
            sym = str(item.get("公司代號", "")).strip()
            if len(sym) == 4 and sym.isdigit():
                stocks.append({
                    "symbol": sym,
                    "name": str(item.get("公司名稱", "")).strip(),
                    "market": "上市",
                    "ticker": f"{sym}.TW",
                    "industry": clean_industry_name(item.get("產業別", ""))
                })
    except Exception as e:
        print(f"TWSE API 讀取: {e}")

    try:
        r_tpex = requests.get("https://www.tpex.org.tw/openapi/v1/mopsfin_t187ap03_O", timeout=12).json()
        for item in r_tpex:
            sym = str(item.get("SecuritiesCompanyCode", "")).strip()
            if len(sym) == 4 and sym.isdigit():
                stocks.append({
                    "symbol": sym,
                    "name": str(item.get("CompanyName", "")).strip(),
                    "market": "上櫃",
                    "ticker": f"{sym}.TWO",
                    "industry": clean_industry_name(item.get("Industry", ""))
                })
    except Exception as e:
        print(f"TPEx API 讀取: {e}")

    return pd.DataFrame(stocks)

def calculate_real_market_rs():
    print("🚀 開始執行全市場真實 RS Rating 動能評分計算...")

    # 確保題材對照檔存在
    if not os.path.exists("data/theme_mapping.json"):
        import sys
        sys.path.append(".")
        from data.build_themes import generate_theme_database
        generate_theme_database()

    with open("data/theme_mapping.json", "r", encoding="utf-8") as f:
        theme_map = json.load(f)

    stock_df = get_stock_list()
    if stock_df.empty:
        print("❌ 無法取得股票清單！")
        return

    print(f"📋 共取得全市場 {len(stock_df)} 檔上市櫃個股，開始批次下載真實歷史股價...")

    # 批次透過 yfinance 下載（每批 120 檔，避免超時與被擋）
    tickers = stock_df["ticker"].tolist()
    chunk_size = 120
    all_close_data = pd.DataFrame()

    for i in range(0, len(tickers), chunk_size):
        chunk = tickers[i:i + chunk_size]
        try:
            # 下載近 6 個月日 K 線
            df_chunk = yf.download(chunk, period="6mo", interval="1d", progress=False, auto_adjust=True)
            if isinstance(df_chunk.columns, pd.MultiIndex):
                if "Close" in df_chunk.columns.levels[0]:
                    close_chunk = df_chunk["Close"]
                else:
                    close_chunk = df_chunk.xs("Close", level=0, axis=1)
            else:
                close_chunk = df_chunk["Close"] if "Close" in df_chunk else df_chunk
            
            all_close_data = pd.concat([all_close_data, close_chunk], axis=1)
        except Exception as e:
            print(f"批次下載異常 ({i}~{i+chunk_size}): {e}")
        time.sleep(0.5)

    print("📊 股價下載完畢，開始計算動能評分 (5日 20%、20日 50%、60日 30%)...")

    valid_results = []
    for _, row in stock_df.iterrows():
        sym = row["symbol"]
        name = row["name"]
        mkt = row["market"]
        ticker = row["ticker"]
        ind = row["industry"]

        # 讀取題材標籤
        tag_info = theme_map.get(sym, {
            "main_industry": ind,
            "sub_industry": f"{ind}-一般應用",
            "themes": [f"{ind}族群", f"{ind}供應鏈"]
        })

        if ticker not in all_close_data.columns:
            continue

        prices = all_close_data[ticker].dropna()
        n = len(prices)

        # 至少需要 5 個交易日才有基本動能
        if n < 5:
            continue

        cur_p = float(prices.iloc[-1])
        if cur_p <= 0 or np.isnan(cur_p):
            continue

        # 計算 5 日報酬率
        r_5 = float((cur_p - prices.iloc[-5]) / prices.iloc[-5] * 100)

        # 計算 20 日 (近1個月) 報酬率
        if n >= 20:
            r_20 = float((cur_p - prices.iloc[-20]) / prices.iloc[-20] * 100)
        else:
            r_20 = r_5

        # 計算 60 日 (近1季) 報酬率
        if n >= 60:
            r_60 = float((cur_p - prices.iloc[-60]) / prices.iloc[-60] * 100)
        else:
            r_60 = r_20

        # 動能加權綜合得分
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
        print("❌ 無有效計算結果！")
        return

    # 全市場精確百分位 PR 排名 (1~99，99 為市場最強前 1%)
    df_rank["rs_rating"] = pd.qcut(
        df_rank["score"].rank(method="first"),
        q=99,
        labels=range(1, 100)
    ).astype(int)

    # 依照 RS 評分與綜合動能由大到小排序
    df_rank = df_rank.sort_values(by=["rs_rating", "score"], ascending=[False, False])

    output_data = df_rank.to_dict(orient="records")
    with open("market_rankings.json", "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    print(f"🎉 全市場真實 RS 計算完畢！共評比 {len(output_data)} 檔個股，榜首 RS 99 股票範例：")
    for top in output_data[:5]:
        print(f"  [{top['symbol']} {top['name']}] RS: {top['rs_rating']} (5日:{top['r_5d']}%, 20日:{top['r_20d']}%, 60日:{top['r_60d']}%, 得分:{top['score']})")

if __name__ == "__main__":
    calculate_real_market_rs()
