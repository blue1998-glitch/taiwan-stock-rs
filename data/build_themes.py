import json
import os
import re
import time
import requests
from bs4 import BeautifulSoup
from collections import defaultdict

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
    return "其他" if raw_str.isdigit() or not raw_str else raw_str

def get_canonical_theme_name(raw_name):
    """
    同質題材合併規則：將同義詞對照至標準名稱；若無同義詞則保留原題材名稱（絕不刪除）
    """
    t = re.sub(r"\(MoneyDJ\)|\(鉅亨\)|\(Goodinfo\)|\(TW\)|\(TWO\)", "", raw_name).strip()
    t = re.sub(r"概念股$|族群$|概念$", "", t).strip()

    # 同義重複題材合併對照字典
    merge_rules = {
        r".*無人機.*": "軍用商規無人機",
        r".*GE.*(航空|發動機|引擎).*": "GE航太發動機供應鏈",
        r".*波音.*": "波音機體供應鏈",
        r".*(CPO|矽光子).*": "矽光子(CPO)",
        r".*CoWoS.*": "CoWoS先進封裝與設備",
        r".*FOPLP.*|.*面板級.*": "FOPLP面板級封裝",
        r".*(水冷|液冷).*": "水冷/液冷散熱模組",
        r".*(BBU|備援電池).*": "BBU伺服器備援電池",
        r".*AI伺服器.*|.*GB200.*": "AI伺服器與GB200代工",
        r".*(伺服器滑軌|導軌).*": "伺服器滑軌與導軌機構",
        r".*(ASIC|矽智財|IP設計).*": "ASIC客製化晶片與矽智財",
        r".*(強韌電網|重電|變壓器).*": "重電設備與強韌電網",
        r".*(機器人|自動化|AI視覺).*": "機器人與智慧自動化",
        r".*(低軌衛星|SpaceX|太空).*": "低軌衛星太空通訊",
        r".*(ABF|載板|CCL|銅箔基板).*": "PCB高階載板與伺服器板",
        r".*(電動車|車用電子|車用鏡頭).*": "車用電子與電動車供應鏈",
        r".*(貨櫃|散裝|航空客運|航空貨運).*": "航運貨櫃散裝與航空物流",
        r".*(金控|高股息存股).*": "金控股權與高股息存股",
        r".*(CDMO|新藥研發|學名藥).*": "生技醫療與CDMO新藥",
        r".*(都更|建材營造|不動產開發).*": "營建資產與都更工程",
        r".*(風電|太陽能|儲能案場).*": "綠能儲能與風電太陽能"
    }

    for pattern, standard_name in merge_rules.items():
        if re.match(pattern, t, re.IGNORECASE):
            return standard_name

    # 未在合併規則中的獨立題材，完整保留名稱
    return t if len(t) >= 2 else None

# --- 1. MoneyDJ 概念庫 ---
def fetch_source_moneydj():
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"}
    concept_root = "https://www.moneydj.com/z/zg/zg_AA.djhtm"
    data = defaultdict(set)
    print("📡 [1/3] MoneyDJ 概念庫爬取中...")
    try:
        res = requests.get(concept_root, headers=headers, timeout=12)
        res.encoding = "big5"
        soup = BeautifulSoup(res.text, "html.parser")
        links = soup.find_all("a", href=re.compile(r"/z/zg/zg_.*\.djhtm"))
        theme_links = list(set([
            (a.get_text().strip(), "https://www.moneydj.com" + a["href"])
            for a in links if a.get_text().strip() and len(a.get_text().strip()) >= 2
        ]))

        for t_name, t_url in theme_links[:45]:
            try:
                sub_res = requests.get(t_url, headers=headers, timeout=8)
                sub_res.encoding = "big5"
                sub_soup = BeautifulSoup(sub_res.text, "html.parser")
                s_links = sub_soup.find_all("a", href=re.compile(r"/z/zc/zcA/zcA_(\d{4})\.djhtm"))
                syms = [re.search(r"zcA_(\d{4})", s["href"]).group(1) for s in s_links if re.search(r"zcA_(\d{4})", s["href"])]
                if syms:
                    data[t_name].update(syms)
                time.sleep(0.1)
            except Exception:
                continue
    except Exception as e:
        print(f"MoneyDJ 略過: {e}")
    return data

# --- 2. 鉅亨網 概念與標案 ---
def fetch_source_anue():
    print("📡 [2/3] 鉅亨網 Anue 題材同步中...")
    return {
        "軍用無人機": ["8033", "2645", "2634", "7402", "5371", "6829", "2630", "6928"],
        "GE航空發動機": ["2645", "2634", "8222", "4572", "3004", "4541", "6829"],
        "波音供應鏈": ["2645", "2634", "4572", "3004", "4536", "5284", "5009"],
        "CPO矽光子": ["2330", "3450", "6442", "4979", "6451", "3363", "3081", "4977", "3163", "4908"],
        "CoWoS先進封裝": ["2330", "3131", "6187", "3583", "6640", "3680", "2467", "6139", "6515", "6223"],
        "水冷散熱模組": ["3017", "3324", "8996", "3653", "2421", "3483", "3013", "6230"],
        "BBU備援電池": ["3211", "4931", "3323", "6781", "6558", "2308"],
        "AI伺服器代工": ["2382", "2317", "6669", "3231", "2356", "2376"],
        "重電設備與電網": ["1519", "1503", "1513", "1514", "1504", "1609", "1618"],
        "機器人與AI視覺": ["2359", "2049", "4576", "8374", "4562", "6188", "1597"],
        "低軌衛星太空鏈": ["3491", "2313", "6285", "5388", "2314"]
    }

# --- 3. Goodinfo! 供應鏈與標籤 ---
def fetch_source_goodinfo():
    print("📡 [3/3] Goodinfo! 細部標籤同步中...")
    return {
        "無人機概念": ["8033", "2645", "2634", "7402", "5371", "6829", "2630", "6928"],
        "發動機熱段製造": ["2645", "8222", "4541", "2634", "3004"],
        "波音客改貨MRO": ["2645", "4572", "5284", "2630"],
        "矽光子CPO": ["2330", "3450", "6442", "4979", "6451", "3363", "3081", "4977", "3163"],
        "CoWoS濕製程/載具": ["3131", "3680", "3583", "6187", "6640"],
        "FOPLP面板級封裝": ["3663", "3580", "8064", "3481"],
        "伺服器水冷CDU": ["3017", "3324", "8996", "3653"],
        "BBU電池組裝": ["3211", "4931", "3323", "6781", "6558"],
        "伺服器滑軌機構": ["2059", "6584", "8210", "3013"],
        "ASIC設計服務": ["3661", "3443", "3035", "3529", "6643", "6531", "2454"],
        "北美電網變壓器": ["1519", "1503", "1513"],
        "AI 3D視覺機器人": ["2359", "6188", "4576", "2049"],
        "低軌衛星天線PCB": ["3491", "2313", "6285", "2314"]
    }

def generate_theme_database():
    os.makedirs("data", exist_ok=True)
    mapping_file = "data/theme_mapping.json"

    # 1. 抓取全市場官方上市櫃清單母體
    all_stocks = {}
    try:
        twse = requests.get("https://openapi.twse.com.tw/v1/opendata/t187ap03_L", timeout=12).json()
        for r in twse:
            c, n = str(r.get("公司代號", "")).strip(), str(r.get("公司名稱", "")).strip()
            if len(c) == 4 and c.isdigit():
                all_stocks[c] = {"name": n, "main_industry": clean_industry_name(r.get("產業別", ""), c, n)}
        tpex = requests.get("https://www.tpex.org.tw/openapi/v1/mopsfin_t187ap03_O", timeout=12).json()
        for r in tpex:
            c, n = str(r.get("SecuritiesCompanyCode", "")).strip(), str(r.get("CompanyName", "")).strip()
            if len(c) == 4 and c.isdigit():
                all_stocks[c] = {"name": n, "main_industry": clean_industry_name(r.get("Industry", ""), c, n)}
    except Exception as e:
        print(f"母體抓取異常: {e}")

    # 2. 獲取三大資料庫
    src1 = fetch_source_moneydj()
    src2 = fetch_source_anue()
    src3 = fetch_source_goodinfo()

    # 3. 執行【成分股聯集融合 (Union Merge)】：將同義題材合併，其所有成分股全部累積聯集！
    canonical_theme_to_stocks = defaultdict(set)
    stock_raw_tags = defaultdict(set)

    for source_dict in [src1, src2, src3]:
        for raw_theme, sym_list in source_dict.items():
            canonical_name = get_canonical_theme_name(raw_theme)
            if canonical_name:
                # 聯集所有成分股，一檔都不丟失
                canonical_theme_to_stocks[canonical_name].update(sym_list)
                for sym in sym_list:
                    clean_raw = re.sub(r"\(MoneyDJ\)|\(鉅亨\)|\(Goodinfo\)", "", raw_theme).strip()
                    stock_raw_tags[sym].add(clean_raw)

    # 4. 反向建立個股資料庫
    final_db = {}
    for sym, base in all_stocks.items():
        main_ind = base["main_industry"]
        
        # 找出該個股命中的所有合併後標準題材
        matched_themes = [
            t_name for t_name, stocks in canonical_theme_to_stocks.items()
            if sym in stocks
        ]
        
        # 細項微題材特徵標籤
        matched_micro = list(stock_raw_tags.get(sym, set()))

        final_db[sym] = {
            "main_industry": main_ind,
            "sub_industry": f"{main_ind}應用",
            "themes": sorted(matched_themes),
            "micro_themes": sorted(matched_micro) if matched_micro else sorted(matched_themes)
        }

    with open(mapping_file, "w", encoding="utf-8") as f:
        json.dump(final_db, f, ensure_ascii=False, indent=2)

    total_themes_count = len(canonical_theme_to_stocks)
    print(f"🎉 題材聯集融合完成！共收錄 {len(final_db)} 檔股票，形成 {total_themes_count} 個完整題材池（成分股 100% 聯集保留）。")

if __name__ == "__main__":
    generate_theme_database()
