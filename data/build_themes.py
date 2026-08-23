import json
import os
import requests

def generate_theme_database():
    os.makedirs("data", exist_ok=True)
    mapping_file = "data/theme_mapping.json"
    
    expert_themes = {
        # 航太、國防與無人機族群
        "2645": {"main_industry": "航太與國防", "sub_industry": "飛機維修/發動機製造", "themes": ["GE航空供應鏈", "無人機", "波音供應鏈", "軍工概念", "長榮集團"]},
        "2634": {"main_industry": "航太與國防", "sub_industry": "機體製造/發動機零件", "themes": ["GE航空供應鏈", "無人機", "國機國造", "軍工概念", "波音供應鏈"]},
        "8033": {"main_industry": "航太與國防", "sub_industry": "無人載具製造", "themes": ["無人機", "軍工概念"]},
        "4572": {"main_industry": "航太與國防", "sub_industry": "結構機構件加工", "themes": ["波音供應鏈", "航太零件"]},
        "3004": {"main_industry": "航太與國防", "sub_industry": "航太緊固件", "themes": ["GE航空供應鏈", "波音供應鏈", "航太零件"]},
        "8222": {"main_industry": "航太與國防", "sub_industry": "發動機燃燒室零組件", "themes": ["GE航空供應鏈", "航太零件"]},
        "6829": {"main_industry": "航太與國防", "sub_industry": "國防飛彈與半導體設備", "themes": ["軍工概念", "半導體設備"]},
        
        # 半導體、先進封裝與矽光子
        "2330": {"main_industry": "半導體", "sub_industry": "晶圓代工", "themes": ["AI伺服器", "CoWoS", "先進製程", "矽光子(CPO)"]},
        "2454": {"main_industry": "半導體", "sub_industry": "IC設計", "themes": ["AI手機", "ASIC", "WiFi 7", "聯發科集團"]},
        "3443": {"main_industry": "半導體", "sub_industry": "ASIC/IP設計", "themes": ["AI伺服器", "ASIC", "矽智財"]},
        "3661": {"main_industry": "半導體", "sub_industry": "ASIC/IP設計", "themes": ["AI伺服器", "ASIC", "先進封裝"]},
        "3131": {"main_industry": "半導體", "sub_industry": "半導體濕製程設備", "themes": ["CoWoS", "先進封裝設備", "台積電供應鏈"]},
        "6187": {"main_industry": "半導體", "sub_industry": "點膠與封裝設備", "themes": ["CoWoS", "半導體設備"]},
        "3363": {"main_industry": "通信網路", "sub_industry": "光收發模組", "themes": ["矽光子(CPO)", "AI伺服器", "光通訊"]},
        "6451": {"main_industry": "通信網路", "sub_industry": "光通訊模組", "themes": ["矽光子(CPO)", "光通訊"]},

        # AI 伺服器、散熱與機殼
        "3017": {"main_industry": "電子零組件", "sub_industry": "散熱模組/水冷板", "themes": ["AI伺服器", "水冷散熱", "GB200", "散熱模組"]},
        "3324": {"main_industry": "電子零組件", "sub_industry": "散熱模組/水冷板", "themes": ["AI伺服器", "水冷散熱", "GB200", "散熱模組"]},
        "8996": {"main_industry": "電機機械", "sub_industry": "散熱零組件/沖壓件", "themes": ["水冷散熱", "AI伺服器"]},
        "2382": {"main_industry": "電腦周邊", "sub_industry": "伺服器ODM代工", "themes": ["AI伺服器", "GB200", "車用電子", "廣達集團"]},
        "6669": {"main_industry": "電腦周邊", "sub_industry": "AI伺服器白牌代工", "themes": ["AI伺服器", "GB200", "高價股"]},
        "3653": {"main_industry": "電子零組件", "sub_industry": "伺服器滑軌", "themes": ["AI伺服器", "GB200", "伺服器滑軌"]},

        # 重電、綠能與儲能
        "1519": {"main_industry": "電機機械", "sub_industry": "變壓器/重電設備", "themes": ["重電綠能", "台電強韌電網", "北美電網外銷"]},
        "1504": {"main_industry": "電機機械", "sub_industry": "變壓器/重電設備", "themes": ["重電綠能", "台電強韌電網"]},
        "1513": {"main_industry": "電機機械", "sub_industry": "開關設備/GIS", "themes": ["重電綠能", "台電強韌電網"]},
        "1514": {"main_industry": "電機機械", "sub_industry": "變壓器/重電設備", "themes": ["重電綠能", "台電強韌電網"]}
    }

    try:
        twse_url = "https://openapi.twse.com.tw/v1/opendata/t187ap03_L"
        res = requests.get(twse_url, timeout=10).json()
        for row in res:
            sym = row.get("公司代號", "")
            ind = row.get("產業別", "其他")
            if sym and sym not in expert_themes:
                expert_themes[sym] = {
                    "main_industry": ind,
                    "sub_industry": f"{ind}-一般",
                    "themes": [ind]
                }
    except Exception as e:
        print(f"TWSE OpenAPI 略過: {e}")

    with open(mapping_file, "w", encoding="utf-8") as f:
        json.dump(expert_themes, f, ensure_ascii=False, indent=2)
    print(f"✅ 題材資料庫建立完成！共收錄 {len(expert_themes)} 檔個股標籤。")

if __name__ == "__main__":
    generate_theme_database()
  
