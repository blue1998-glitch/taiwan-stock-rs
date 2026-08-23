import json
import os
import requests
import pandas as pd

def generate_theme_database():
    os.makedirs("data", exist_ok=True)
    mapping_file = "data/theme_mapping.json"
    
    # 1. 核心精準題材庫 (涵蓋台股關鍵族群與主流概念)
    expert_db = {
        # 航太、國防與無人機
        "2645": {"main_industry": "航太與國防", "sub_industry": "發動機製造/機體維修(MRO)", "themes": ["GE航空供應鏈", "無人機", "波音供應鏈", "軍工國防", "長榮集團"]},
        "2634": {"main_industry": "航太與國防", "sub_industry": "機體製造/發動機零件", "themes": ["GE航空供應鏈", "無人機", "國機國造", "軍工國防", "波音供應鏈"]},
        "8033": {"main_industry": "航太與國防", "sub_industry": "無人載具製造", "themes": ["無人機", "軍工國防"]},
        "4572": {"main_industry": "航太與國防", "sub_industry": "航太結構機加件", "themes": ["波音供應鏈", "航太零件", "軍工國防"]},
        "3004": {"main_industry": "航太與國防", "sub_industry": "發動機緊固件/扣件", "themes": ["GE航空供應鏈", "波音供應鏈", "航太零件"]},
        "8222": {"main_industry": "航太與國防", "sub_industry": "燃燒室燃管零件", "themes": ["GE航空供應鏈", "航太零件", "軍工國防"]},
        "6829": {"main_industry": "航太與國防", "sub_industry": "國防飛彈與半導體腔體", "themes": ["軍工國防", "半導體設備", "航太零件"]},
        
        # 半導體、先進封裝、矽光子(CPO)與IC設計
        "2330": {"main_industry": "半導體", "sub_industry": "先進製程晶圓代工", "themes": ["AI伺服器", "CoWoS先進封裝", "晶圓代工龍頭", "矽光子(CPO)"]},
        "2454": {"main_industry": "半導體", "sub_industry": "手機晶片/ASIC設計", "themes": ["AI手機", "ASIC客製化晶片", "WiFi 7", "聯發科集團"]},
        "3443": {"main_industry": "半導體", "sub_industry": "ASIC/IP矽智財", "themes": ["AI伺服器", "ASIC客製化晶片", "矽智財"]},
        "3661": {"main_industry": "半導體", "sub_industry": "ASIC/IP矽智財", "themes": ["AI伺服器", "ASIC客製化晶片", "先進製程"]},
        "3131": {"main_industry": "半導體", "sub_industry": "濕製程先進封裝設備", "themes": ["CoWoS先進封裝", "台積電供應鏈", "半導體設備"]},
        "6187": {"main_industry": "半導體", "sub_industry": "點膠與封裝設備", "themes": ["CoWoS先進封裝", "半導體設備"]},
        "3583": {"main_industry": "半導體", "sub_industry": "自動光學檢測(AOI)", "themes": ["CoWoS先進封裝", "半導體設備"]},
        "3363": {"main_industry": "通信網路", "sub_industry": "光收發模組/CPO", "themes": ["矽光子(CPO)", "AI伺服器", "光通訊"]},
        "6451": {"main_industry": "通信網路", "sub_industry": "光通訊模組封裝", "themes": ["矽光子(CPO)", "光通訊"]},
        "4977": {"main_industry": "通信網路", "sub_industry": "光通訊元件", "themes": ["矽光子(CPO)", "光通訊"]},

        # AI 伺服器、水冷散熱、機殼與電源
        "3017": {"main_industry": "電子零組件", "sub_industry": "水冷散熱模組/散熱板", "themes": ["AI伺服器", "水冷散熱", "GB200", "散熱模組"]},
        "3324": {"main_industry": "電子零組件", "sub_industry": "散熱管/水冷板", "themes": ["AI伺服器", "水冷散熱", "GB200", "散熱模組"]},
        "8996": {"main_industry": "電機機械", "sub_industry": "散熱沖壓件/冷卻系統", "themes": ["水冷散熱", "AI伺服器"]},
        "2382": {"main_industry": "電腦周邊", "sub_industry": "AI伺服器ODM代工", "themes": ["AI伺服器", "GB200", "車用電子", "廣達集團"]},
        "6669": {"main_industry": "電腦周邊", "sub_industry": "AI伺服器白牌主機", "themes": ["AI伺服器", "GB200", "雲端運算"]},
        "2317": {"main_industry": "其他電子", "sub_industry": "EMS電子代工龍頭", "themes": ["AI伺服器", "GB200", "電動車", "鴻海集團"]},
        "2308": {"main_industry": "電子零組件", "sub_industry": "電源供應器/儲能", "themes": ["AI伺服器", "伺服器電源", "電動車充電樁", "儲能綠能"]},
        "3653": {"main_industry": "電子零組件", "sub_industry": "伺服器高階滑軌", "themes": ["AI伺服器", "GB200", "伺服器滑軌"]},
        "8210": {"main_industry": "電子零組件", "sub_industry": "導軌/機構零組件", "themes": ["AI伺服器", "伺服器滑軌"]},

        # 重電、強韌電網與綠能儲能
        "1519": {"main_industry": "電機機械", "sub_industry": "超特高壓變壓器", "themes": ["重電設備", "台電強韌電網", "北美變壓器外銷", "綠能儲能"]},
        "1504": {"main_industry": "電機機械", "sub_industry": "重電設備/馬達", "themes": ["重電設備", "台電強韌電網", "電動車馬達"]},
        "1513": {"main_industry": "電機機械", "sub_industry": "氣體絕緣開關(GIS)", "themes": ["重電設備", "台電強韌電網"]},
        "1514": {"main_industry": "電機機械", "sub_industry": "變壓器/配電盤", "themes": ["重電設備", "台電強韌電網"]},
        "6806": {"main_industry": "電機機械", "sub_industry": "儲能系統/太陽能", "themes": ["綠能儲能", "太陽能/風電"]}
    }

    print("正在透過 TWSE / TPEx OpenAPI 獲取全市場清單並進行全覆蓋歸類...")
    all_stocks = {}

    # 1. 抓取上市清單
    try:
        twse_res = requests.get("https://openapi.twse.com.tw/v1/opendata/t187ap03_L", timeout=12).json()
        for row in twse_res:
            sym = str(row.get("公司代號", "")).strip()
            name = str(row.get("公司名稱", "")).strip()
            ind = str(row.get("產業別", "其他")).strip()
            if sym and len(sym) == 4:
                all_stocks[sym] = {"name": name, "main_industry": ind, "market": "上市"}
    except Exception as e:
        print(f"TWSE API 讀取通知: {e}")

    # 2. 抓取上櫃清單
    try:
        tpex_res = requests.get("https://www.tpex.org.tw/openapi/v1/mopsfin_t187ap03_O", timeout=12).json()
        for row in tpex_res:
            sym = str(row.get("SecuritiesCompanyCode", "")).strip()
            name = str(row.get("CompanyName", "")).strip()
            ind = str(row.get("Industry", "其他")).strip()
            if sym and len(sym) == 4:
                all_stocks[sym] = {"name": name, "main_industry": ind, "market": "上櫃"}
    except Exception as e:
        print(f"TPEx API 讀取通知: {e}")

    # 3. 結合專家庫與智能分類，補足全台股每一檔股票的細產業與多重題材
    final_mapping = {}
    for sym, base in all_stocks.items():
        if sym in expert_db:
            final_mapping[sym] = expert_db[sym]
        else:
            main_ind = base["main_industry"]
            name = base["name"]
            
            # 依產業與名稱關鍵字推導細產業與題材
            sub_ind = f"{main_ind}-一般零組件/製造"
            derived_themes = [main_ind]

            if "半導體" in main_ind:
                if any(k in name for k in ["科", "晶", "創", "智", "訊"]):
                    sub_ind = "IC設計與應用"
                    derived_themes += ["IC設計", "晶片概念"]
                else:
                    sub_ind = "半導體製造/封測/材料"
                    derived_themes += ["半導體供應鏈"]
            elif "電子" in main_ind or "電腦" in main_ind:
                sub_ind = "電子零組件/系統模組"
                derived_themes += ["電子代工與周邊", "AI生態系"]
            elif "通信" in main_ind:
                sub_ind = "網通設備與模組"
                derived_themes += ["5G/網通", "網通基礎建設"]
            elif "生技" in main_ind:
                sub_ind = "新藥/醫材/保健"
                derived_themes += ["生技醫療", "大健康概念"]
            elif "航運" in main_ind:
                sub_ind = "貨櫃/散裝/航空物流"
                derived_themes += ["航運物流", "全球貿易復甦"]
            elif "金融" in main_ind:
                sub_ind = "金控/銀行/保險"
                derived_themes += ["金融存股", "高股息概念"]
            elif "電機" in main_ind:
                sub_ind = "工具機/自動化設備"
                derived_themes += ["智慧製造", "工業自動化"]
            else:
                sub_ind = f"{main_ind}專業應用"
                derived_themes += [f"{main_ind}概念股"]

            final_mapping[sym] = {
                "main_industry": main_ind,
                "sub_industry": sub_ind,
                "themes": list(set(derived_themes))
            }

    with open(mapping_file, "w", encoding="utf-8") as f:
        json.dump(final_mapping, f, ensure_ascii=False, indent=2)
        
    print(f"✅ 全台股題材與細產業資料庫建置完成！共納入 {len(final_mapping)} 檔個股。")

if __name__ == "__main__":
    generate_theme_database()
