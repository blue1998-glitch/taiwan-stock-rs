import json
import os
import requests
import pandas as pd

# 官方產業代碼轉正體中文標準字典
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
    "38": "居家生活"
}

def clean_industry_name(raw_ind):
    raw_str = str(raw_ind).strip()
    return TWSE_INDUSTRY_MAP.get(raw_str, raw_str if raw_str else "綜合產業")

def generate_theme_database():
    os.makedirs("data", exist_ok=True)
    mapping_file = "data/theme_mapping.json"
    
    # 1. 深度專家題材庫 (含精確次產業與市場主流概念標籤)
    expert_db = {
        # 航太、國防與無人機族群
        "2645": {"main_industry": "航太與國防", "sub_industry": "飛機維修/發動機零件製造", "themes": ["GE航空供應鏈", "無人機", "波音供應鏈", "軍工國防", "長榮集團"]},
        "2634": {"main_industry": "航太與國防", "sub_industry": "機體製造/發動機零件", "themes": ["GE航空供應鏈", "無人機", "國機國造", "軍工國防", "波音供應鏈"]},
        "8033": {"main_industry": "航太與國防", "sub_industry": "無人載具製造", "themes": ["無人機", "軍工國防"]},
        "4572": {"main_industry": "航太與國防", "sub_industry": "航太結構機加件", "themes": ["波音供應鏈", "航太零件", "軍工國防"]},
        "3004": {"main_industry": "航太與國防", "sub_industry": "發動機緊固件/扣件", "themes": ["GE航空供應鏈", "波音供應鏈", "航太零件"]},
        "8222": {"main_industry": "航太與國防", "sub_industry": "發動機燃燒室零件", "themes": ["GE航空供應鏈", "航太零件", "軍工國防"]},
        "6829": {"main_industry": "航太與國防", "sub_industry": "國防飛彈與半導體設備", "themes": ["軍工國防", "半導體設備", "航太零件"]},
        
        # 半導體、先進封裝、矽光子(CPO)與IC設計
        "2330": {"main_industry": "半導體業", "sub_industry": "先進製程晶圓代工", "themes": ["AI伺服器", "CoWoS先進封裝", "先進製程", "矽光子(CPO)"]},
        "2454": {"main_industry": "半導體業", "sub_industry": "手機晶片/ASIC設計", "themes": ["AI手機", "ASIC客製化晶片", "WiFi 7", "聯發科集團"]},
        "3443": {"main_industry": "半導體業", "sub_industry": "ASIC/IP矽智財", "themes": ["AI伺服器", "ASIC客製化晶片", "矽智財"]},
        "3661": {"main_industry": "半導體業", "sub_industry": "ASIC/IP矽智財", "themes": ["AI伺服器", "ASIC客製化晶片", "先進製程"]},
        "3035": {"main_industry": "半導體業", "sub_industry": "ASIC設計服務", "themes": ["ASIC客製化晶片", "矽智財"]},
        "3131": {"main_industry": "半導體業", "sub_industry": "濕製程先進封裝設備", "themes": ["CoWoS先進封裝", "台積電供應鏈", "半導體設備"]},
        "6187": {"main_industry": "半導體業", "sub_industry": "點膠與封裝設備", "themes": ["CoWoS先進封裝", "半導體設備"]},
        "3583": {"main_industry": "半導體業", "sub_industry": "自動光學檢測(AOI)", "themes": ["CoWoS先進封裝", "半導體設備"]},
        "3363": {"main_industry": "通信網路業", "sub_industry": "光收發模組/CPO", "themes": ["矽光子(CPO)", "AI伺服器", "光通訊"]},
        "6451": {"main_industry": "通信網路業", "sub_industry": "光通訊模組封裝", "themes": ["矽光子(CPO)", "光通訊"]},
        "4977": {"main_industry": "通信網路業", "sub_industry": "光通訊元件", "themes": ["矽光子(CPO)", "光通訊"]},

        # AI 伺服器、水冷散熱、機殼與電源
        "3017": {"main_industry": "電子零組件業", "sub_industry": "水冷散熱模組/水冷板", "themes": ["AI伺服器", "水冷散熱", "GB200", "散熱模組"]},
        "3324": {"main_industry": "電子零組件業", "sub_industry": "散熱管/水冷板", "themes": ["AI伺服器", "水冷散熱", "GB200", "散熱模組"]},
        "8996": {"main_industry": "電機機械", "sub_industry": "散熱沖壓件/冷卻系統", "themes": ["水冷散熱", "AI伺服器"]},
        "2382": {"main_industry": "電腦及週邊設備業", "sub_industry": "AI伺服器ODM代工", "themes": ["AI伺服器", "GB200", "車用電子", "廣達集團"]},
        "6669": {"main_industry": "電腦及週邊設備業", "sub_industry": "AI伺服器白牌主機", "themes": ["AI伺服器", "GB200", "雲端運算"]},
        "2317": {"main_industry": "其他電子業", "sub_industry": "EMS電子代工龍頭", "themes": ["AI伺服器", "GB200", "電動車", "鴻海集團"]},
        "2308": {"main_industry": "電子零組件業", "sub_industry": "伺服器電源/儲能", "themes": ["AI伺服器", "伺服器電源", "電動車充電樁", "儲能綠能"]},
        "3653": {"main_industry": "電子零組件業", "sub_industry": "伺服器高階滑軌", "themes": ["AI伺服器", "GB200", "伺服器滑軌"]},
        "8210": {"main_industry": "電子零組件業", "sub_industry": "導軌/機構零組件", "themes": ["AI伺服器", "伺服器滑軌"]},

        # BBU 備援電池、重電與強韌電網
        "3211": {"main_industry": "電子零組件業", "sub_industry": "伺服器BBU電池模組", "themes": ["BBU備援電池", "AI伺服器", "鋰電池模組"]},
        "3323": {"main_industry": "電子零組件業", "sub_industry": "伺服器BBU電池模組", "themes": ["BBU備援電池", "AI伺服器", "鋰電池模組"]},
        "6558": {"main_industry": "電子零組件業", "sub_industry": "鋰電池組裝/BBU", "themes": ["BBU備援電池", "儲能綠能"]},
        "1519": {"main_industry": "電機機械", "sub_industry": "超特高壓變壓器", "themes": ["重電設備", "台電強韌電網", "北美變壓器外銷", "綠能儲能"]},
        "1504": {"main_industry": "電機機械", "sub_industry": "重電設備/馬達", "themes": ["重電設備", "台電強韌電網", "電動車馬達"]},
        "1513": {"main_industry": "電機機械", "sub_industry": "氣體絕緣開關(GIS)", "themes": ["重電設備", "台電強韌電網"]},
        "1514": {"main_industry": "電機機械", "sub_industry": "變壓器/配電盤", "themes": ["重電設備", "台電強韌電網"]}
    }

    print("📡 正在抓取 TWSE / TPEx 全市場清單並轉換標準中文產業別...")
    all_stocks = {}

    try:
        twse_res = requests.get("https://openapi.twse.com.tw/v1/opendata/t187ap03_L", timeout=12).json()
        for row in twse_res:
            sym = str(row.get("公司代號", "")).strip()
            name = str(row.get("公司名稱", "")).strip()
            raw_ind = row.get("產業別", "")
            ind_name = clean_industry_name(raw_ind)
            if sym and len(sym) == 4:
                all_stocks[sym] = {"name": name, "main_industry": ind_name, "market": "上市"}
    except Exception as e:
        print(f"TWSE OpenAPI 讀取: {e}")

    try:
        tpex_res = requests.get("https://www.tpex.org.tw/openapi/v1/mopsfin_t187ap03_O", timeout=12).json()
        for row in tpex_res:
            sym = str(row.get("SecuritiesCompanyCode", "")).strip()
            name = str(row.get("CompanyName", "")).strip()
            raw_ind = row.get("Industry", "")
            ind_name = clean_industry_name(raw_ind)
            if sym and len(sym) == 4:
                all_stocks[sym] = {"name": name, "main_industry": ind_name, "market": "上櫃"}
    except Exception as e:
        print(f"TPEx OpenAPI 讀取: {e}")

    # 2. 自動推導全市場個股的細產業與語意標籤（不含任何數字代碼）
    final_mapping = {}
    for sym, base in all_stocks.items():
        if sym in expert_db:
            final_mapping[sym] = expert_db[sym]
        else:
            main_ind = base["main_industry"]
            name = base["name"]
            
            # 依據產業大類與名稱進行語意歸類
            sub_ind = f"{main_ind}-一般應用"
            derived_themes = []

            if "半導體" in main_ind:
                sub_ind = "IC設計與半導體製造"
                derived_themes = ["半導體供應鏈", "晶片概念"]
            elif "電子零組件" in main_ind:
                sub_ind = "電子元件與模組機構"
                derived_themes = ["電子零組件族群", "硬體供應鏈"]
            elif "電腦" in main_ind:
                sub_ind = "電腦系統與周邊設備"
                derived_themes = ["PC/伺服器周邊", "資訊硬體"]
            elif "通信" in main_ind:
                sub_ind = "通訊設備與光通訊"
                derived_themes = ["網通供應鏈", "5G/通訊概念"]
            elif "生技" in main_ind:
                sub_ind = "製藥醫材與生物科技"
                derived_themes = ["生技醫療族群", "大健康概念"]
            elif "航運" in main_ind:
                sub_ind = "海運航空與物流運輸"
                derived_themes = ["航運物流概念", "全球貿易概念"]
            elif "金融" in main_ind:
                sub_ind = "銀行金控與證券保險"
                derived_themes = ["金融族群", "高股息存股"]
            elif "電機" in main_ind:
                sub_ind = "重電電機與自動化機台"
                derived_themes = ["電機設備族群", "智慧製造概念"]
            elif "鋼鐵" in main_ind:
                sub_ind = "鋼鐵冶煉與金屬加工"
                derived_themes = ["鋼鐵金屬族群", "基礎建設概念"]
            elif "建材" in main_ind or "營造" in main_ind:
                sub_ind = "營建營造與建材工程"
                derived_themes = ["營建資產概念", "房產建設"]
            else:
                sub_ind = f"{main_ind}製造與應用"
                derived_themes = [f"{main_ind}供應鏈", f"{main_ind}族群"]

            final_mapping[sym] = {
                "main_industry": main_ind,
                "sub_industry": sub_ind,
                "themes": list(set(derived_themes))
            }

    with open(mapping_file, "w", encoding="utf-8") as f:
        json.dump(final_mapping, f, ensure_ascii=False, indent=2)
        
    print(f"✅ 題材與細產業資料庫重構完成！共納入 {len(final_mapping)} 檔個股，全部採用標準正體中文。")

if __name__ == "__main__":
    generate_theme_database()
