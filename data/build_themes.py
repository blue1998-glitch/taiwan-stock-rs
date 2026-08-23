import json
import os
import requests
import pandas as pd

# 官方 33 大法定產業標準中文字典 (縱向產業)
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

def generate_theme_database():
    os.makedirs("data", exist_ok=True)
    mapping_file = "data/theme_mapping.json"

    # =========================================================================
    # 🎯 核心市場題材字典 (純橫向風口、特定供應鏈與技術應用，絕不與產業混淆)
    # =========================================================================
    MARKET_THEMES = {
        # 【先進半導體製程與光通訊】
        "矽光子(CPO)": ["2330", "3450", "6442", "4979", "6451", "3363", "3081", "4977", "3163", "4908", "6530", "6548"],
        "CoWoS先進封裝": ["2330", "3131", "6187", "3583", "6640", "3680", "2467", "6139", "6515", "6223", "3413", "8027", "2404"],
        "FOPLP面板級封裝": ["3663", "3580", "8064", "3535", "3481", "3131"],
        "ASIC/IP矽智財": ["3661", "3443", "3035", "3529", "6643", "6531", "2454", "6533", "8227", "6462"],
        
        # 【AI 硬體運算與伺服器架構】
        "水冷/液冷散熱模組": ["3017", "3324", "8996", "3653", "2421", "3483", "3013", "6230", "6275"],
        "BBU伺服器備援電池": ["3211", "4931", "3323", "6781", "6558", "3625", "5309", "2308"],
        "AI伺服器ODM/代工": ["2382", "2317", "6669", "3231", "2356", "2376", "4938", "3515"],
        "高階伺服器滑軌": ["2059", "6584", "3013"],
        
        # 【國防航太與低軌衛星】
        "軍用商規無人機": ["2645", "2634", "8033", "7402", "5371", "6928", "6829", "2630"],
        "GE航太發動機供應鏈": ["2645", "2634", "8222", "4572", "3004", "6829", "4541"],
        "波音/空巴機體供應鏈": ["2645", "2634", "4572", "3004", "4536", "5284", "5009"],
        "國防軍工標案": ["2634", "2645", "8033", "6829", "8222", "2630", "4572", "5009"],
        "低軌衛星太空通訊": ["3491", "2313", "6285", "5388", "2314", "2485", "2367", "4916"],
        
        # 【能源轉型與自動化】
        "台電強韌電網/重電": ["1519", "1503", "1513", "1514", "1504", "1609", "1618", "1605", "1616", "2371"],
        "北美變壓器外銷": ["1519", "1503", "1513"],
        "機器人/AI視覺自動化": ["2359", "6215", "8374", "4562", "2049", "4576", "1597", "4583", "2464", "6188", "2395", "6166"]
    }

    # 反向建立 股票代號 -> 題材列表
    stock_themes_map = {}
    for theme_name, stock_list in MARKET_THEMES.items():
        for sym in stock_list:
            if sym not in stock_themes_map:
                stock_themes_map[sym] = []
            stock_themes_map[sym].append(theme_name)

    print("📡 正在同步上市櫃股票法定產業別...")
    all_stocks = {}

    try:
        twse_res = requests.get("https://openapi.twse.com.tw/v1/opendata/t187ap03_L", timeout=12).json()
        for row in twse_res:
            sym = str(row.get("公司代號", "")).strip()
            name = str(row.get("公司名稱", "")).strip()
            ind_name = clean_industry_name(row.get("產業別", ""), sym, name)
            if sym and len(sym) == 4 and sym.isdigit():
                all_stocks[sym] = {"name": name, "main_industry": ind_name, "market": "上市"}
    except Exception as e:
        print(f"TWSE API: {e}")

    try:
        tpex_res = requests.get("https://www.tpex.org.tw/openapi/v1/mopsfin_t187ap03_O", timeout=12).json()
        for row in tpex_res:
            sym = str(row.get("SecuritiesCompanyCode", "")).strip()
            name = str(row.get("CompanyName", "")).strip()
            ind_name = clean_industry_name(row.get("Industry", ""), sym, name)
            if sym and len(sym) == 4 and sym.isdigit():
                all_stocks[sym] = {"name": name, "main_industry": ind_name, "market": "上櫃"}
    except Exception as e:
        print(f"TPEx API: {e}")

    final_mapping = {}
    for sym, base in all_stocks.items():
        main_ind = base["main_industry"]
        name = base["name"]

        # 純淨題材列表：只保留真實命中的市場題材，若無則為空清單 []，絕不產生「XX族群」
        assigned_themes = stock_themes_map.get(sym, [])

        # 細產業分類 (縱向業務細分)
        sub_ind = f"{main_ind}應用"
        if sym in ["2645", "2634"]:
            sub_ind = "飛機維修(MRO)與機體製造"
        elif sym in ["3017", "3324", "8996", "3653"]:
            sub_ind = "散熱模組與熱傳導零組件"
        elif sym in ["2330"]:
            sub_ind = "晶圓代工製造"
        elif sym in ["3131", "6187", "3583"]:
            sub_ind = "半導體先進製程設備"
        elif sym in ["1519", "1503", "1513", "1514"]:
            sub_ind = "重電與特高壓變壓器"
        elif "半導體" in main_ind:
            sub_ind = "IC設計與製造封裝"
        elif "電子零組件" in main_ind:
            sub_ind = "電子零組件與機構件"
        elif "電腦" in main_ind:
            sub_ind = "伺服器與電腦系統"
        elif "通信" in main_ind:
            sub_ind = "光通訊與網通設備"
        elif "電機" in main_ind:
            sub_ind = "重電馬達與自動化工具機"
        elif "航運" in main_ind:
            sub_ind = "貨櫃散裝與物流運輸"

        final_mapping[sym] = {
            "main_industry": main_ind,
            "sub_industry": sub_ind,
            "themes": assigned_themes
        }

    with open(mapping_file, "w", encoding="utf-8") as f:
        json.dump(final_mapping, f, ensure_ascii=False, indent=2)
        
    print(f"✅ 精準題材庫重構完成！共收錄 {len(final_mapping)} 檔個股，純淨題材數：{len(MARKET_THEMES)} 個。")

if __name__ == "__main__":
    generate_theme_database()
