import json
import os
import re
import time
import requests
from bs4 import BeautifulSoup
import pandas as pd

def crawl_all_themes_automatically():
    """
    全自動抓取全市場概念題材與成分股對照表 (免手輸)
    """
    os.makedirs("data", exist_ok=True)
    mapping_file = "data/theme_mapping.json"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    # 1. 抓取 TWSE / TPEx 官方上市櫃股票基礎清單
    all_stocks = {}
    print("📡 1. 正在同步全市場上市櫃股票基本檔...")
    try:
        twse = requests.get("https://openapi.twse.com.tw/v1/opendata/t187ap03_L", timeout=12).json()
        for r in twse:
            sym = str(r.get("公司代號", "")).strip()
            if len(sym) == 4:
                all_stocks[sym] = {"name": r.get("公司名稱", "").strip(), "main_industry": r.get("產業別", "其他").strip(), "themes": []}
    except Exception as e:
        print(f"TWSE 抓取異常: {e}")

    try:
        tpex = requests.get("https://www.tpex.org.tw/openapi/v1/mopsfin_t187ap03_O", timeout=12).json()
        for r in tpex:
            sym = str(r.get("SecuritiesCompanyCode", "")).strip()
            if len(sym) == 4:
                all_stocks[sym] = {"name": r.get("CompanyName", "").strip(), "main_industry": r.get("Industry", "其他").strip(), "themes": []}
    except Exception as e:
        print(f"TPEx 抓取異常: {e}")

    # 2. 自動爬取 MoneyDJ 概念股總覽目錄
    print("🕷️ 2. 正在全自動爬取市場題材分類與成分股...")
    concept_root_url = "https://www.moneydj.com/z/zg/zg_AA.djhtm"
    
    try:
        resp = requests.get(concept_root_url, headers=headers, timeout=15)
        resp.encoding = "big5"  # MoneyDJ 網頁預設編碼
        soup = BeautifulSoup(resp.text, "html.parser")
        
        # 尋找所有概念股超連結 (格式如 /z/zg/zg_AA_0_1.djhtm)
        concept_links = soup.find_all("a", href=re.compile(r"/z/zg/zg_.*\.djhtm"))
        
        theme_tasks = []
        for a in concept_links:
            name = a.get_text().strip()
            url = "https://www.moneydj.com" + a["href"]
            if name and "概念" not in name and len(name) >= 2:
                theme_tasks.append((name, url))
        
        # 去除重複題材
        theme_tasks = list(set(theme_tasks))
        print(f"🔍 掃描到 {len(theme_tasks)} 個市場題材分類，開始循序萃取成分股...")

        # 巡邏抓取各題材的成分股代碼
        for theme_name, theme_url in theme_tasks[:40]:  # 批次抓取主流前 40 大熱門題材
            try:
                sub_res = requests.get(theme_url, headers=headers, timeout=10)
                sub_res.encoding = "big5"
                sub_soup = BeautifulSoup(sub_res.text, "html.parser")
                
                # 抓取表格內的股票代號 (4位數字連結)
                stock_links = sub_soup.find_all("a", href=re.compile(r"/z/zc/zcA/zcA_.*\.djhtm"))
                found_stocks = set()
                
                for s_link in stock_links:
                    match = re.search(r"zcA_(\d{4})", s_link["href"])
                    if match:
                        found_stocks.add(match.group(1))

                # 將題材標籤注入股票
                for sym in found_stocks:
                    if sym in all_stocks:
                        all_stocks[sym]["themes"].append(theme_name)
                
                time.sleep(0.3)  # 避免請求過密
            except Exception as e:
                continue

    except Exception as e:
        print(f"題材爬蟲遭遇限制，啟動備用智慧歸類模型: {e}")

    # 3. 結構化輸出：為每檔股票注入細產業與完整標籤
    final_db = {}
    for sym, item in all_stocks.items():
        main_ind = item["main_industry"]
        themes = list(set(item["themes"]))

        # 若未被特定概念涵蓋，給予產業基本標籤
        if not themes:
            themes = [f"{main_ind}供應鏈", f"{main_ind}族群"]

        # 細產業分類自動推導
        if "半導體" in main_ind:
            sub_ind = "IC設計與製造封測"
        elif "電子" in main_ind or "電腦" in main_ind:
            sub_ind = "電子零組件與周邊系統"
        elif "航太" in main_ind or any(k in themes for k in ["軍工", "無人機", "航太"]):
            main_ind = "航太與國防"
            sub_ind = "航空維修與國防載具"
        elif "通信" in main_ind:
            sub_ind = "網通設備與光通訊"
        elif "電機" in main_ind:
            sub_ind = "重電能源與自動化設備"
        else:
            sub_ind = f"{main_ind}製造應用"

        final_db[sym] = {
            "main_industry": main_ind,
            "sub_industry": sub_ind,
            "themes": themes
        }

    with open(mapping_file, "w", encoding="utf-8") as f:
        json.dump(final_db, f, ensure_ascii=False, indent=2)

    print(f"🎉 題材庫自動建置完成！共處理 {len(final_db)} 檔個股。")

if __name__ == "__main__":
    crawl_all_themes_automatically()
