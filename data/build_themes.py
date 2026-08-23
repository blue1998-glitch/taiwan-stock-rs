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
        return "其他"
    return raw_str if raw_str else "其他"

def generate_theme_database():
    os.makedirs("data", exist_ok=True)
    mapping_file = "data/theme_mapping.json"

    # =========================================================================
    # 🎯 修剪樹枝：定義 7 大聚合核心題材，每檔個股綁定專屬的「微題材詳細特徵」
    # =========================================================================
    EXPERT_STOCK_PROFILES = {
        # 【1. 航太國防與無人機】
        "2645": {"macro_themes": ["航太國防與無人機"], "micro_themes": ["GE航太發動機", "軍用無人機", "波音機體維修(MRO)"], "sub_ind": "航太維修與發動機製造"},
        "2634": {"macro_themes": ["航太國防與無人機"], "micro_themes": ["國機國造", "GE引擎零組件", "軍用無人機", "波音代工"], "sub_ind": "機體製造與引擎零件"},
        "8033": {"macro_themes": ["航太國防與無人機"], "micro_themes": ["軍用商規無人機", "國防標案"], "sub_ind": "無人載具製造"},
        "4572": {"macro_themes": ["航太國防與無人機"], "micro_themes": ["波音機體結構件", "航太精密機加"], "sub_ind": "航太結構零件"},
        "3004": {"macro_themes": ["航太國防與無人機"], "micro_themes": ["GE發動機扣件", "航太引擎緊固件"], "sub_ind": "航太緊固件"},
        "8222": {"macro_themes": ["航太國防與無人機"], "micro_themes": ["GE/LEAP燃燒室零件", "發動機熱段"], "sub_ind": "發動機熱段零件"},
        "6829": {"macro_themes": ["航太國防與無人機", "先進封裝與光通訊(CoWoS/CPO)"], "micro_themes": ["國防飛彈腔體", "半導體設備腔體"], "sub_ind": "國防與半導體腔體加工"},
        "2630": {"macro_themes": ["航太國防與無人機"], "micro_themes": ["軍機翻修", "國防後勤標案"], "sub_ind": "軍機維修"},
        "5284": {"macro_themes": ["航太國防與無人機"], "micro_themes": ["波音/空巴駕駛艙件", "航太機電機構"], "sub_ind": "航太機電機構件"},
        "4541": {"macro_themes": ["航太國防與無人機"], "micro_themes": ["GE發動機機匣", "起落架結構件"], "sub_ind": "航太發動機零件"},
        "7402": {"macro_themes": ["航太國防與無人機"], "micro_themes": ["無人機航電系統", "軍用導航通訊"], "sub_ind": "軍工航電系統"},

        # 【2. 先進封裝與光通訊 (CoWoS/CPO)】
        "2330": {"macro_themes": ["先進封裝與光通訊(CoWoS/CPO)", "AI伺服器與液冷/BBU"], "micro_themes": ["CoWoS先進封裝", "CPO矽光子", "2nm先進製程"], "sub_ind": "晶圓代工龍頭"},
        "3131": {"macro_themes": ["先進封裝與光通訊(CoWoS/CPO)"], "micro_themes": ["CoWoS濕製程設備", "台積電供應鏈", "單晶圓清洗"], "sub_ind": "半導體濕製程設備"},
        "6187": {"macro_themes": ["先進封裝與光通訊(CoWoS/CPO)"], "micro_themes": ["點膠機/貼片機", "CoWoS封裝設備"], "sub_ind": "半導體封裝設備"},
        "3583": {"macro_themes": ["先進封裝與光通訊(CoWoS/CPO)"], "micro_themes": ["濕製程設備", "再生晶圓製造"], "sub_ind": "半導體設備與再生晶圓"},
        "6640": {"macro_themes": ["先進封裝與光通訊(CoWoS/CPO)"], "micro_themes": ["高精度挑晶機", "晶粒黏著機(Die Bonder)"], "sub_ind": "半導體後段設備"},
        "3680": {"macro_themes": ["先進封裝與光通訊(CoWoS/CPO)"], "micro_themes": ["EUV極紫外光光罩盒", "先進封裝載具"], "sub_ind": "半導體載具與光罩盒"},
        "3450": {"macro_themes": ["先進封裝與光通訊(CoWoS/CPO)"], "micro_themes": ["CPO雷射封測", "高階光收發模組"], "sub_ind": "光通訊雷射封測"},
        "6442": {"macro_themes": ["先進封裝與光通訊(CoWoS/CPO)"], "micro_themes": ["CPO高階光纖跳線", "主被動光通訊元件"], "sub_ind": "光纖跳線與模組"},
        "4979": {"macro_themes": ["先進封裝與光通訊(CoWoS/CPO)"], "micro_themes": ["CPO光收發晶片", "800G光模組"], "sub_ind": "光收發主動元件"},
        "6451": {"macro_themes": ["先進封裝與光通訊(CoWoS/CPO)"], "micro_themes": ["CPO光學模組封裝", "鴻海集團半導體"], "sub_ind": "系統級封裝(SiP)"},
        "3363": {"macro_themes": ["先進封裝與光通訊(CoWoS/CPO)"], "micro_themes": ["光纖陣列連接器", "台積電CPO合作夥伴"], "sub_ind": "光纖連接模組"},
        "3081": {"macro_themes": ["先進封裝與光通訊(CoWoS/CPO)"], "micro_themes": ["矽光子磊晶片", "CW大功率雷射源"], "sub_ind": "化合物半導體磊晶"},
        "3663": {"macro_themes": ["先進封裝與光通訊(CoWoS/CPO)"], "micro_themes": ["FOPLP面板級封裝載板", "靶材加工"], "sub_ind": "面板級封裝與靶材"},

        # 【3. AI伺服器與液冷/BBU】
        "3017": {"macro_themes": ["AI伺服器與液冷/BBU"], "micro_themes": ["水冷散熱板/模組", "散熱風扇", "GB200供應鏈"], "sub_ind": "水冷散熱模組"},
        "3324": {"macro_themes": ["AI伺服器與液冷/BBU"], "micro_themes": ["水冷板(Cold Plate)", "CDU冷卻液分配器"], "sub_ind": "散熱導管與水冷系統"},
        "8996": {"macro_themes": ["AI伺服器與液冷/BBU"], "micro_themes": ["板式熱交換器", "CDU水冷核心零件"], "sub_ind": "熱交換器與冷卻系統"},
        "3653": {"macro_themes": ["AI伺服器與液冷/BBU"], "micro_themes": ["均熱片(ILid)", "伺服器散熱底板"], "sub_ind": "均熱片與散熱機構件"},
        "3211": {"macro_themes": ["AI伺服器與液冷/BBU"], "micro_themes": ["伺服器BBU電池模組", "AI備援電力"], "sub_ind": "BBU備援電池模組"},
        "4931": {"macro_themes": ["AI伺服器與液冷/BBU"], "micro_themes": ["高功率BBU模組", "儲能鋰電池"], "sub_ind": "高功率鋰電池"},
        "3323": {"macro_themes": ["AI伺服器與液冷/BBU"], "micro_themes": ["BBU鋰電池組裝", "伺服器電源"], "sub_ind": "鋰電池組裝"},
        "6781": {"macro_themes": ["AI伺服器與液冷/BBU"], "micro_themes": ["高階伺服器BBU", "輕型電動車電池"], "sub_ind": "高階電池模組"},
        "2382": {"macro_themes": ["AI伺服器與液冷/BBU"], "micro_themes": ["AI伺服器ODM", "GB200整機櫃", "廣達集團"], "sub_ind": "AI伺服器ODM代工"},
        "2317": {"macro_themes": ["AI伺服器與液冷/BBU"], "micro_themes": ["GB200 NVL72代工", "AI伺服器主機板", "鴻海集團"], "sub_ind": "EMS電子代工龍頭"},
        "6669": {"macro_themes": ["AI伺服器與液冷/BBU"], "micro_themes": ["AI伺服器白牌主機", "ASIC專用伺服器"], "sub_ind": "雲端伺服器主機"},
        "2059": {"macro_themes": ["AI伺服器與液冷/BBU"], "micro_themes": ["高階伺服器滑軌", "GB200機櫃專用導軌"], "sub_ind": "伺服器滑軌龍頭"},
        "8210": {"macro_themes": ["AI伺服器與液冷/BBU"], "micro_themes": ["伺服器滑軌", "精密機構件"], "sub_ind": "機構導軌零組件"},

        # 【4. ASIC與矽智財(IP)】
        "3661": {"macro_themes": ["ASIC與矽智財(IP)"], "micro_themes": ["7nm/3nm先進ASIC設計", "北美雲端CSP晶片"], "sub_ind": "ASIC設計服務"},
        "3443": {"macro_themes": ["ASIC與矽智財(IP)"], "micro_themes": ["台積電主要ASIC夥伴", "HBM/CoWoS介面IP"], "sub_ind": "ASIC與矽智財"},
        "3035": {"macro_themes": ["ASIC與矽智財(IP)"], "micro_themes": ["ASIC客製化設計", "聯電集團"], "sub_ind": "ASIC設計服務"},
        "3529": {"macro_themes": ["ASIC與矽智財(IP)"], "micro_themes": ["嵌入式非揮發記憶體IP", "安全晶片IP"], "sub_ind": "嵌入式記憶體IP"},
        "6643": {"macro_themes": ["ASIC與矽智財(IP)"], "micro_themes": ["高速傳輸介面IP", "基礎元件IP"], "sub_ind": "高速傳輸IP"},
        "2454": {"macro_themes": ["ASIC與矽智財(IP)"], "micro_themes": ["旗艦天璣手機晶片", "客製化ASIC", "WiFi 7"], "sub_ind": "手機與通訊IC設計"},

        # 【5. 重電能源與強韌電網】
        "1519": {"macro_themes": ["重電能源與強韌電網"], "micro_themes": ["超特高壓變壓器", "北美電網外銷", "台電強韌電網"], "sub_ind": "特高壓變壓器"},
        "1503": {"macro_themes": ["重電能源與強韌電網"], "micro_themes": ["重電變壓器", "北美外銷", "台電標案"], "sub_ind": "重電設備製造"},
        "1513": {"macro_themes": ["重電能源與強韌電網"], "micro_themes": ["GIS氣體絕緣開關", "台電統包標案", "氫能"], "sub_ind": "高壓開關設備"},
        "1514": {"macro_themes": ["重電能源與強韌電網"], "micro_themes": ["配電盤/變壓器", "台積電擴廠重電設備"], "sub_ind": "配電盤與變壓器"},
        "1609": {"macro_themes": ["重電能源與強韌電網"], "micro_themes": ["特高壓電力電纜", "綠能儲能案場"], "sub_ind": "特高壓電纜"},
        "1618": {"macro_themes": ["重電能源與強韌電網"], "micro_themes": ["超高壓電力電纜", "台電強韌電網標案"], "sub_ind": "電力電纜"},

        # 【6. 機器人與智慧自動化】
        "2359": {"macro_themes": ["機器人與智慧自動化"], "micro_themes": ["AI 3D視覺感測", "機器人手臂整合", "輝達生態系"], "sub_ind": "AI機器人視覺"},
        "2049": {"macro_themes": ["機器人與智慧自動化"], "micro_themes": ["滾珠螺桿/線性滑軌", "機器人關節零組件"], "sub_ind": "線性傳動元件"},
        "4576": {"macro_themes": ["機器人與智慧自動化"], "micro_themes": ["直驅馬達/高階定位平台", "半導體機器人控制"], "sub_ind": "直驅馬達與定位平台"},
        "8374": {"macro_themes": ["機器人與智慧自動化"], "micro_themes": ["機器人視覺系統整合", "自動化傳動零件"], "sub_ind": "自動化機電系統"},
        "4562": {"macro_themes": ["機器人與智慧自動化"], "micro_themes": ["全電式智慧彎管機", "協作型機器人"], "sub_ind": "工具機與智慧機械"},
        "6188": {"macro_themes": ["機器人與智慧自動化"], "micro_themes": ["達明協作機器人(TM Robot)", "AI視覺辨識手臂"], "sub_ind": "協作型機器人"},

        # 【7. 低軌衛星太空通訊】
        "3491": {"macro_themes": ["低軌衛星太空通訊"], "micro_themes": ["衛星天線/微波元件", "SpaceX/Kuiper供應鏈"], "sub_ind": "高頻微波元件"},
        "2313": {"macro_themes": ["低軌衛星太空通訊"], "micro_themes": ["低軌衛星高階HDI板", "SpaceX主要板廠"], "sub_ind": "高階HDI印刷電路板"},
        "6285": {"macro_themes": ["低軌衛星太空通訊"], "micro_themes": ["地面接收站天線/路由器", "低軌衛星設備"], "sub_ind": "網通與天線模組"},
        "5388": {"macro_themes": ["低軌衛星太空通訊"], "micro_themes": ["衛星通訊終端", "光纖寬頻設備"], "sub_ind": "寬頻網通設備"},
        "2314": {"macro_themes": ["低軌衛星太空通訊"], "micro_themes": ["衛星收發天線", "地面站射頻元件"], "sub_ind": "衛星通訊設備"}
    }

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

        if sym in EXPERT_STOCK_PROFILES:
            profile = EXPERT_STOCK_PROFILES[sym]
            final_mapping[sym] = {
                "main_industry": main_ind,
                "sub_industry": profile["sub_ind"],
                "macro_themes": profile["macro_themes"],
                "micro_themes": profile["micro_themes"]
            }
        else:
            final_mapping[sym] = {
                "main_industry": main_ind,
                "sub_industry": f"{main_ind}應用",
                "macro_themes": [],
                "micro_themes": []
            }

    with open(mapping_file, "w", encoding="utf-8") as f:
        json.dump(final_mapping, f, ensure_ascii=False, indent=2)
        
    print(f"✅ 修剪版題材資料庫建立完成！共收錄 {len(final_mapping)} 檔個股。")

if __name__ == "__main__":
    generate_theme_database()
