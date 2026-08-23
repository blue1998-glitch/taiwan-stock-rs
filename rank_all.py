import yfinance as yf
import pandas as pd
import json
import time
import requests
import sys
import os

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
    "36": "數位雲端", "37": "運動休閒", "38": "居家生活",
    "80": "管理股票", "91": "存託憑證(TDR)"
}

def clean_industry_name(raw_ind, sym="", name=""):
    raw_str = str(raw_ind).strip()
    if sym.startswith("91") or "-DR" in name or "DR" in name or raw_str == "91":
        return "存託憑證(TDR)"
    if raw_str in TWSE_INDUSTRY_MAP:
        return TWSE_INDUSTRY_MAP[raw_str]
    if raw_str.isdigit():
        return "其他"
    return raw_str if raw_str else "其他"

def get_tw_market_tickers():
    """抓取全台股代號、中文簡稱與上市櫃類別 (整合官方 OpenAPI)"""
    target_list = []
    headers = {"User-Agent": "Mozilla/5.0"}
    
    # 1. 上市 (TWSE)
    try:
        url_twse = "https://openapi.twse.com.tw/v1/opendata/t187ap03_L"
        res = requests.get(url_twse, headers=headers, timeout=12)
        if res.status_code == 200:
            for row in res.json():
                c = str(row.get('公司代號', '')).strip()
                n = str(row.get('公司簡稱', row.get('公司名稱', c))).strip()
                raw_ind = row.get('產業別', '')
                if len(c) == 4 and c.isdigit():
                    target_list.append({
                        "symbol": c,
                        "name": n,
                        "market": "上市",
                        "ticker": f"{c}.TW",
                        "industry": clean_industry_name(raw_ind, c, n)
                    })
    except Exception as e:
        print(f"TWSE API 連線異常: {e}")

    # 2. 上櫃 (TPEx)
    try:
        url_tpex = "https://www.tpex.org.tw/openapi/v1/mopsfin_t187ap03_O"
        res = requests.get(url_tpex, headers=headers, timeout=12)
        if res.status_code == 200:
            for row in res.json():
                c = str(row.get('SecuritiesCompanyCode', row.get('公司代號', ''))).strip()
                n = str(row.get('CompanyAbbreviation', row.get('SecuritiesCompanyName', row.get('公司簡稱', c)))).strip()
                raw_ind = row.get('Industry', '')
                if len(c) == 4 and c.isdigit():
                    target_list.append({
                        "symbol": c,
                        "name": n,
                        "market": "上櫃",
                        "ticker": f"{c}.TWO",
                        "industry": clean_industry_name(raw_ind, c, n)
                    })
    except Exception as e:
        print(f"TPEx API 連線異常: {e}")

    unique_map = {}
    for item in target_list:
        if item["symbol"] not in unique_map:
            unique_map[item["symbol"]] = item

    return list(unique_map.values())

def main():
    # 確保題材對照檔存在
    if not os.path.exists("data/theme_mapping.json"):
        import sys
        sys.path.append(".")
        from data.build_themes import generate_theme_database
        generate_theme_database()

    with open("data/theme_mapping.json", "r", encoding="utf-8") as f:
        theme_map = json.load(f)

    stock_info_list = get_tw_market_tickers()
    print(f"成功取得台股全市場 {len(stock_info_list)} 檔標的資料，開始批次下載動能...")

    if len(stock_info_list) < 500:
        print("❌ 取得代號數量不足，取消覆蓋檔案。")
        sys.exit(1)

    all_tickers = [item["ticker"] for item in stock_info_list]
    ticker_to_info = {item["ticker"]: item for item in stock_info_list}

    chunk_size = 60
    market_data = []

    for i in range(0, len(all_tickers), chunk_size):
        chunk = all_tickers[i:i + chunk_size]
        try:
            df = yf.download(
                tickers=chunk,
                period="6mo",
                interval="1d",
                auto_adjust=False,
                progress=False,
                threads=True,
                timeout=20
            )

            if df is not None and not df.empty and 'Close' in df:
                closes_df = df['Close']

                for ticker in chunk:
                    try:
                        if isinstance(closes_df, pd.DataFrame):
                            if ticker in closes_df.columns:
                                series = closes_df[ticker].dropna()
                            else:
                                continue
                        elif isinstance(closes_df, pd.Series):
                            series = closes_df.dropna()
                        else:
                            continue

                        if len(series) < 6:
                            continue

                        p_now = float(series.iloc[-1])
                        p_5d = float(series.iloc[-6]) if len(series) >= 6 else float(series.iloc[0])
                        p_1m = float(series.iloc[-21]) if len(series) >= 21 else float(series.iloc[0])
                        p_1q = float(series.iloc[-61]) if len(series) >= 61 else float(series.iloc[0])

                        r_5d = round(((p_now - p_5d) / p_5d) * 100, 2)
                        r_1m = round(((p_now - p_1m) / p_1m) * 100, 2)
                        r_1q = round(((p_now - p_1q) / p_1q) * 100, 2)

                        # 完全採用您的加權公式
                        score = round((r_5d * 0.2) + (r_1m * 0.5) + (r_1q * 0.3), 2)
                        info = ticker_to_info[ticker]
                        sym = info["symbol"]

                        tag_info = theme_map.get(sym, {
                            "main_industry": info["industry"],
                            "sub_industry": f"{info['industry']}應用",
                            "macro_themes": [],
                            "micro_themes": []
                        })
                        
                        market_data.append({
                            "symbol": sym,
                            "name": info["name"],
                            "market": info["market"],
                            "close_price": round(p_now, 2),
                            "r_5d": r_5d,
                            "r_20d": r_1m,
                            "r_60d": r_1q,
                            "score": score,
                            "main_industry": tag_info["main_industry"],
                            "sub_industry": tag_info["sub_industry"],
                            "macro_themes": tag_info["macro_themes"],
                            "micro_themes": tag_info["micro_themes"]
                        })
                    except Exception:
                        continue
        except Exception:
            pass

        time.sleep(0.3)

    # 排序並計算全市場 PR 百分位 (1 ~ 99)
    market_data.sort(key=lambda x: x['score'], reverse=True)
    total_count = len(market_data)
    print(f"成功收錄 {total_count} 檔有效股票，開始計算全市場 PR 百分位...")

    if total_count < 1000:
        print(f"❌ 警告：成功計算筆數 ({total_count}) 低於 1000，取消覆蓋檔案。")
        sys.exit(1)

    for idx, item in enumerate(market_data):
        pr = max(1, min(99, int(((total_count - idx) / total_count) * 100)))
        item['rs_rating'] = pr

    with open("market_rankings.json", "w", encoding="utf-8") as f:
        json.dump(market_data, f, ensure_ascii=False, indent=2)

    print(f"✅ 全市場排名大功告成！共計收錄 {total_count} 檔股票。")

if __name__ == "__main__":
    main()
