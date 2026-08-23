import json
import os
import requests
import pandas as pd

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
        return "綜合產業"
    return raw_str if raw_str else "綜合產業"

def generate_theme_database():
    os.makedirs("data", exist_ok=True)
    mapping_file = "data/theme_mapping.json"

    # 真實公認核心題材庫（按真實業務定義，不硬湊數量）
    REAL_THEMES = {
        # 國防航太類
        "無人機概念": ["2645", "2634", "8033", "7402", "5371", "2630", "6829"],
        "GE航空供應鏈": ["2645", "2634", "8222", "4572", "3004", "6829", "4541"],
        "波音供應鏈": ["2645", "2634", "4572", "3004", "4536", "5284"],
        "國防軍工": ["2634", "2645", "8033", "6829", "8222", "2630", "4572"],

        # 半導體先進製程與封裝
        "CoWoS先進封裝": ["2330", "3131", "6187", "3583", "6640", "3680", "2467", "6139", "6515", "6223"],
        "矽光子(CPO)": ["2330", "3450", "6442", "4979", "6451", "3363", "3081", "4977", "3163", "4908"],
        "ASIC/IP矽智財": ["3661", "3443", "3035", "3529", "6643", "6531", "2454", "6533", "8227"],
        "先進製程設備材料": ["2330", "3680", "3131", "6187", "3583", "3551", "1560"],

        # AI 硬體與伺服器周邊
        "水冷散熱模組": ["3017", "3324", "8996", "3653", "2421", "3483", "3013"],
        "BBU備援電池": ["3211", "3323", "4931", "6781", "6558", "2308"],
        "AI伺服器ODM": ["2382", "2317", "6669", "3231", "2356", "2376"],
        "伺服器滑軌": ["3653", "8210", "2059"],

        # 電力與自動化
        "重電設備": ["1519", "1503", "1513", "1514", "1504", "1609", "1618"],
        "機器人與AI視覺": ["2359", "2365", "8374", "4562", "2049", "4576", "4573", "1597"],
        "低軌衛星": ["3491", "2313", "6285", "5388", "2314", "2485"],

        # 核心基礎產業族群
        "IC設計龍頭": ["2454", "2379", "3034", "3227", "6415", "4966", "4961"],
        "航運貨櫃散裝": ["2603", "2609", "2615", "2605", "2606", "2618", "2610"],
        "金控股權存股": ["2881", "2882", "2891", "2886", "2884", "2892", "5880", "2880"]
    }

    # 建立 反向對照表
    stock_to_themes = {}
    for theme_name, stocks in REAL_THEMES.items():
        for s in stocks:
            if s not in stock_to_themes:
                stock_to_themes[s] = []
            stock_to_themes[s].append(theme_name)

    print("📡 正在同步 TWSE / TPEx 上市櫃股票基本檔...")
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
        
        # 精準抓取對應題材
        matched_themes = stock_to_themes.get(sym, [])
        if not matched_themes:
            matched_themes = [f"{main_ind}族群"]

        # 細產業分類
        sub_ind = f"{main_ind}應用"
        if "半導體" in main_ind:
            sub_ind = "晶圓製造與IC封測"
        elif "電子零組件" in main_ind:
            sub_ind = "電子零組件與模組"
        elif "電腦" in main_ind:
            sub_ind = "電腦周邊與系統代工"
        elif "通信" in main_ind:
            sub_ind = "網通設備與通訊模組"
        elif "航太" in main_ind or any("航空" in t or "無人機" in t for t in matched_themes):
            main_ind = "航太與國防"
            sub_ind = "飛機維修與航太製造"
        elif "存託憑證" in main_ind:
            sub_ind = "海外第二上市/TDR"

        final_mapping[sym] = {
            "main_industry": main_ind,
            "sub_industry": sub_ind,
            "themes": list(set(matched_themes))
        }

    with open(mapping_file, "w", encoding="utf-8") as f:
        json.dump(final_mapping, f, ensure_ascii=False, indent=2)
        
    print(f"✅ 真實精準題材庫生成完成！共收錄 {len(final_mapping)} 檔個股。")

if __name__ == "__main__":
    generate_theme_database()
