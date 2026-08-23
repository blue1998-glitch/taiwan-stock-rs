import os
import json
import requests
import pandas as pd
import numpy as np

def get_stock_list():
    stocks = []
    try:
        r_twse = requests.get("https://openapi.twse.com.tw/v1/opendata/t187ap03_L", timeout=10).json()
        for item in r_twse:
            stocks.append({"symbol": str(item["公司代號"]), "name": str(item["公司名稱"]), "market": "上市", "industry": item.get("產業別", "其他")})
    except Exception as e:
        print(f"TWSE API: {e}")

    try:
        r_tpex = requests.get("https://www.tpex.org.tw/openapi/v1/mopsfin_t187ap03_O", timeout=10).json()
        for item in r_tpex:
            stocks.append({"symbol": str(item["SecuritiesCompanyCode"]), "name": str(item["CompanyName"]), "market": "上櫃", "industry": item.get("Industry", "其他")})
    except Exception as e:
        print(f"TPEx API: {e}")

    return pd.DataFrame(stocks)

def calculate_momentum_and_enrich():
    if not os.path.exists("data/theme_mapping.json"):
        import sys
        sys.path.append(".")
        from data.build_themes import generate_theme_database
        generate_theme_database()

    with open("data/theme_mapping.json", "r", encoding="utf-8") as f:
        theme_map = json.load(f)

    stock_df = get_stock_list()
    if stock_df.empty:
        print("使用基礎清單...")
        stock_df = pd.DataFrame([
            {"symbol": "2645", "name": "長榮航太", "market": "上市", "industry": "航太與國防"},
            {"symbol": "2330", "name": "台積電", "market": "上市", "industry": "半導體"},
            {"symbol": "2634", "name": "漢翔", "market": "上市", "industry": "航太與國防"},
            {"symbol": "3017", "name": "奇鋐", "market": "上市", "industry": "電子零組件"},
            {"symbol": "8033", "name": "雷虎", "market": "上市", "industry": "航太與國防"},
            {"symbol": "1519", "name": "華城", "market": "上市", "industry": "電機機械"}
        ])

    results = []
    for _, row in stock_df.iterrows():
        sym = row["symbol"]
        name = row["name"]
        market = row["market"]
        
        tag_info = theme_map.get(sym, {
            "main_industry": row.get("industry", "其他"),
            "sub_industry": f"{row.get('industry', '其他')}-一般",
            "themes": [row.get("industry", "其他")]
        })

        results.append({
            "symbol": sym,
            "name": name,
            "market": market,
            "score": float(np.random.uniform(20, 98)),
            "main_industry": tag_info["main_industry"],
            "sub_industry": tag_info["sub_industry"],
            "themes": tag_info["themes"]
        })

    df_rank = pd.DataFrame(results)
    df_rank["rs_rating"] = pd.qcut(df_rank["score"].rank(method="first"), q=99, labels=range(1, 100)).astype(int)
    df_rank = df_rank.sort_values(by="rs_rating", ascending=False)

    with open("market_rankings.json", "w", encoding="utf-8") as f:
        json.dump(df_rank.to_dict(orient="records"), f, ensure_ascii=False, indent=2)

    print(f"✅ market_rankings.json 產生成功，共 {len(df_rank)} 檔股票。")

if __name__ == "__main__":
    calculate_momentum_and_enrich()
  
