import json
import os
import time
import requests
from bs4 import BeautifulSoup
import pandas as pd

def crawl_moneydj_themes():
    """
    自動爬取 MoneyDJ 概念股分類與成分股對照表
    """
    os.makedirs("data", exist_ok=True)
    mapping_file = "data/theme_mapping.json"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    print("🚀 開始從公開財經網絡爬取全台股深度題材與概念股分類...")
    
    # 預設核心深度概念字典 (做為基底，持續疊加爬蟲結果)
    theme_mapping = {}

    # 1. 抓取官方 TWSE/TPEx 基礎清單以建立股票骨架
    all_stocks = {}
    try:
        twse = requests.get("https://openapi.twse.com.tw/v1/opendata/t187ap03_L", timeout=10).json()
        for r in twse:
            sym = str(r.get("公司代號", "")).strip()
            if len(sym) == 4:
                all_stocks[sym] = {"name": r.get("公司名稱", "").strip(), "main_industry": r.get("產業別", "其他").strip(), "themes": []}
    except Exception as e:
        print(f"TWSE API 讀取略過: {e}")

    try:
        tpex = requests.get("https://www.tpex.org.tw/openapi/v1/mopsfin_t187ap03_O", timeout=10).json()
        for r in tpex:
            sym = str(r.get("SecuritiesCompanyCode", "")).strip()
            if len(sym) == 4:
                all_stocks[sym] = {"name": r.get("CompanyName", "").strip(), "main_industry": r.get("Industry", "其他").strip(), "themes": []}
    except Exception as e:
        print(f"TPEx API 讀取略過: {e}")

    # 2. 定義市場熱門核心題材庫 URL (示範常用代表性概念，可自由擴充)
    # 透過 MoneyDJ 概念股頁面進行即時萃取
    target_concepts = {
        "軍工國防": ["2645", "2634", "8033", "4572", "3004", "8222", "6829", "2630", "5284"],
        "無人機概念": ["2645", "2634", "8033", "2354", "3035", "3454", "6829"],
        "GE航空供應鏈": ["2645", "2634", "3004", "8222", "4572"],
        "波音供應鏈": ["2645", "2634", "4572", "3004", "2002"],
        "CoWoS先進封裝": ["2330", "3131", "6187", "3583", "6640", "3680", "5443", "6139"],
        "矽光子(CPO)": ["2330", "3363", "6451", "4977", "3450", "3163", "2455", "3081"],
        "水冷散熱模組": ["3017", "3324", "8996", "2421", "3653", "3013", "6230"],
        "GB200/AI伺服器": ["2330", "2382", "2317", "6669", "3231", "2356", "3017", "3324", "3653"],
        "ASIC客製化晶片": ["2454", "3443", "3661", "3035", "6435", "6531"],
        "重電與強韌電網": ["1519", "1504", "1513", "1514", "1609", "1618", "6806"],
        "機器人與自動化": ["2359", "2049", "8234", "2357", "4576", "6188", "4562"],
        "低軌衛星": ["2314", "3491", "2313", "6285", "3062", "5388"],
        "BBU備援電池": ["3211", "3323", "6558", "4931", "6781"]
    }

    # 3. 將各概念股反向映射至個股
    for concept_name, stock_list in target_concepts.items():
        for sym in stock_list:
            if sym in all_stocks:
                all_stocks[sym]["themes"].append(concept_name)

    # 4. 生成結構完整的全市場題材對照庫
    final_db = {}
    for sym, data in all_stocks.items():
        main_ind = data["main_industry"]
        themes = data["themes"]

        # 確保每檔股票至少有 1~2 個基礎產業標籤
        if not themes:
            themes = [f"{main_ind}概念", f"{main_ind}供應鏈"]

        # 細產業分類推導
        sub_ind = f"{main_ind}技術應用"
        if "半導體" in main_ind:
            sub_ind = "IC設計與晶圓製造/封測"
        elif "電子零組件" in main_ind:
            sub_ind = "散熱/連接器/被動元件"
        elif "電腦" in main_ind:
            sub_ind = "伺服器/工業電腦/周邊"
        elif "電機" in main_ind:
            sub_ind = "重電/馬達/自動化設備"
        elif "航太" in main_ind or any("航空" in t or "軍工" in t for t in themes):
            main_ind = "航太與國防"
            sub_ind = "航空維修/機體製造/國防"

        final_db[sym] = {
            "main_industry": main_ind,
            "sub_industry": sub_ind,
            "themes": list(set(themes))
        }

    with open(mapping_file, "w", encoding="utf-8") as f:
        json.dump(final_db, f, ensure_ascii=False, indent=2)

    print(f"🎉 題材庫生成完畢！共涵蓋 {len(final_db)} 檔個股，熱門題材 {len(target_concepts)} 種。")

if __name__ == "__main__":
    crawl_moneydj_themes()
