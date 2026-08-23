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
    # 🎯 20 大精確市場題材與微題材對照庫 (精準反映技術、供應鏈與業務)
    # =========================================================================
    EXPERT_STOCK_PROFILES = {
        # 【1. 軍工無人機與國防標案】
        "8033": {"macro_themes": ["軍工無人機與國防標案"], "micro_themes": ["軍用商規無人機", "國防標案量產"], "sub_ind": "無人載具製造"},
        "2645": {"macro_themes": ["軍工無人機與國防標案", "航太發動機與民航機體(GE/波音)"], "micro_themes": ["軍用無人機原型", "GE航太發動機", "波音客改貨(P2F)"], "sub_ind": "航太維修與發動機製造"},
        "2634": {"macro_themes": ["軍工無人機與國防標案", "航太發動機與民航機體(GE/波音)"], "micro_themes": ["國機國造(勇鷹號)", "軍用無人機量產", "GE發動機機匣"], "sub_ind": "機體製造與引擎零件"},
        "6829": {"macro_themes": ["軍工無人機與國防標案", "CoWoS先進封裝與設備"], "micro_themes": ["國防飛彈腔體", "半導體設備腔體"], "sub_ind": "國防與半導體腔體加工"},
        "7402": {"macro_themes": ["軍工無人機與國防標案"], "micro_themes": ["無人機航電系統", "軍用導航通訊"], "sub_ind": "軍工航電系統"},
        "5371": {"macro_themes": ["軍工無人機與國防標案"], "micro_themes": ["無人機地面控制站", "軍用強固顯示器"], "sub_ind": "強固顯示系統"},
        "2630": {"macro_themes": ["軍工無人機與國防標案", "航太發動機與民航機體(GE/波音)"], "micro_themes": ["軍機翻修", "空軍後勤保修標案"], "sub_ind": "軍機維修"},
        "5009": {"macro_themes": ["軍工無人機與國防標案"], "micro_themes": ["防彈鋼板", "裝甲車輛結構鋼"], "sub_ind": "特殊合金鋼"},

        # 【2. 航太發動機與民航機體(GE/波音)】
        "3004": {"macro_themes": ["航太發動機與民航機體(GE/波音)"], "micro_themes": ["GE航空發動機扣件", "航太高溫緊固件"], "sub_ind": "航太緊固件"},
        "8222": {"macro_themes": ["航太發動機與民航機體(GE/波音)"], "micro_themes": ["GE/LEAP燃燒室零件", "發動機熱段擴壓管"], "sub_ind": "發動機熱段零件"},
        "4572": {"macro_themes": ["航太發動機與民航機體(GE/波音)"], "micro_themes": ["波音機體結構件", "起落架機構件代工"], "sub_ind": "航太結構零件"},
        "4541": {"macro_themes": ["航太發動機與民航機體(GE/波音)"], "micro_themes": ["GE發動機機匣加工", "航太渦輪扇零件"], "sub_ind": "航太發動機零件"},
        "5284": {"macro_themes": ["航太發動機與民航機體(GE/波音)"], "micro_themes": ["波音/空巴駕駛艙件", "航太機電機構"], "sub_ind": "航太機電機構件"},
        "4536": {"macro_themes": ["航太發動機與民航機體(GE/波音)"], "micro_themes": ["波音起落架零組件", "航太鍛壓件"], "sub_ind": "精密金屬鍛件"},

        # 【3. 矽光子(CPO)與光通訊】
        "2330": {"macro_themes": ["矽光子(CPO)與光通訊", "CoWoS先進封裝與設備", "AI伺服器ODM與整機代工"], "micro_themes": ["TSMC-COUPE矽光子平台", "CoWoS先進封裝", "2nm先進製程"], "sub_ind": "晶圓代工龍頭"},
        "3450": {"macro_themes": ["矽光子(CPO)與光通訊"], "micro_themes": ["CPO雷射封測", "高階光收發模組"], "sub_ind": "光通訊雷射封測"},
        "6442": {"macro_themes": ["矽光子(CPO)與光通訊"], "micro_themes": ["CPO高階光纖跳線", "主被動光通訊元件"], "sub_ind": "光纖跳線與模組"},
        "4979": {"macro_themes": ["矽光子(CPO)與光通訊"], "micro_themes": ["CPO光收發晶片", "800G/1.6T光模組"], "sub_ind": "光收發主動元件"},
        "6451": {"macro_themes": ["矽光子(CPO)與光通訊"], "micro_themes": ["CPO光學模組封裝", "鴻海集團半導體"], "sub_ind": "系統級封裝(SiP)"},
        "3363": {"macro_themes": ["矽光子(CPO)與光通訊"], "micro_themes": ["光纖陣列連接器", "台積電CPO合作夥伴"], "sub_ind": "光纖連接模組"},
        "3081": {"macro_themes": ["矽光子(CPO)與光通訊"], "micro_themes": ["矽光子磊晶片", "CW大功率雷射源"], "sub_ind": "化合物半導體磊晶"},
        "4977": {"macro_themes": ["矽光子(CPO)與光通訊"], "micro_themes": ["高階光收發模組", "微型光學元件"], "sub_ind": "光通訊模組"},
        "3163": {"macro_themes": ["矽光子(CPO)與光通訊"], "micro_themes": ["光纖隔離器", "DWDM波分復用器"], "sub_ind": "光通訊被動元件"},

        # 【4. CoWoS先進封裝與設備】
        "3131": {"macro_themes": ["CoWoS先進封裝與設備"], "micro_themes": ["CoWoS濕製程設備", "台積電主要供應鏈", "晶圓清洗機"], "sub_ind": "半導體濕製程設備"},
        "6187": {"macro_themes": ["CoWoS先進封裝與設備"], "micro_themes": ["點膠機/貼片機", "先進封裝設備"], "sub_ind": "半導體封裝設備"},
        "3583": {"macro_themes": ["CoWoS先進封裝與設備"], "micro_themes": ["濕製程設備", "再生晶圓製造"], "sub_ind": "半導體設備與再生晶圓"},
        "6640": {"macro_themes": ["CoWoS先進封裝與設備"], "micro_themes": ["高精度挑晶機", "晶粒黏著機(Die Bonder)"], "sub_ind": "半導體後段設備"},
        "3680": {"macro_themes": ["CoWoS先進封裝與設備"], "micro_themes": ["EUV極紫外光光罩盒", "先進封裝載具"], "sub_ind": "半導體載具與光罩盒"},
        "6515": {"macro_themes": ["CoWoS先進封裝與設備"], "micro_themes": ["垂直探針卡(VPC)", "CoWoS封裝測試座"], "sub_ind": "半導體測試介面"},
        "6223": {"macro_themes": ["CoWoS先進封裝與設備"], "micro_themes": ["探針卡組裝", "先進測試設備"], "sub_ind": "半導體測試探針卡"},
        "6139": {"macro_themes": ["CoWoS先進封裝與設備"], "micro_themes": ["台積電無塵室工程", "高科技廠務系統"], "sub_ind": "無塵室工程"},
        "2467": {"macro_themes": ["CoWoS先進封裝與設備"], "micro_themes": ["晶圓壓膜機", "高階PCB設備"], "sub_ind": "半導體壓膜設備"},

        # 【5. FOPLP面板級封裝】
        "3663": {"macro_themes": ["FOPLP面板級封裝"], "micro_themes": ["FOPLP面板級載板", "高階靶材加工"], "sub_ind": "面板級封裝與靶材"},
        "3580": {"macro_themes": ["FOPLP面板級封裝"], "micro_themes": ["面板級雷射剝離", "晶圓雷射切割"], "sub_ind": "雷射加工設備"},
        "8064": {"macro_themes": ["FOPLP面板級封裝"], "micro_themes": ["面板級封裝電鍍設備", "半導體濕製程"], "sub_ind": "電鍍與清洗設備"},
        "3481": {"macro_themes": ["FOPLP面板級封裝"], "micro_themes": ["3.5代舊廠轉FOPLP封裝", "群創先進封裝"], "sub_ind": "面板製造與封裝"},

        # 【6. 水冷/液冷散熱模組】
        "3017": {"macro_themes": ["水冷/液冷散熱模組"], "micro_themes": ["水冷板(Cold Plate)", "GB200冷卻模組", "散熱風扇"], "sub_ind": "水冷散熱模組"},
        "3324": {"macro_themes": ["水冷/液冷散熱模組"], "micro_themes": ["水冷散熱板", "CDU冷卻液分配器", "散熱導管"], "sub_ind": "散熱導管與水冷系統"},
        "8996": {"macro_themes": ["水冷/液冷散熱模組"], "micro_themes": ["板式熱交換器", "水冷CDU關鍵沖壓件"], "sub_ind": "熱交換器與冷卻系統"},
        "3653": {"macro_themes": ["水冷/液冷散熱模組", "伺服器滑軌與導軌機構"], "micro_themes": ["均熱片(ILid)", "伺服器散熱底座", "高階滑軌"], "sub_ind": "均熱片與機構件"},
        "2421": {"macro_themes": ["水冷/液冷散熱模組"], "micro_themes": ["高風壓伺服器風扇", "水冷輔助散熱系統"], "sub_ind": "高階散熱風扇"},
        "3483": {"macro_themes": ["水冷/液冷散熱模組"], "micro_themes": ["伺服器散熱模組", "均溫板加工"], "sub_ind": "散熱模組製造"},
        "3013": {"macro_themes": ["水冷/液冷散熱模組", "伺服器滑軌與導軌機構"], "micro_themes": ["CPU Socket散熱插座", "液冷快接頭機構"], "sub_ind": "精密連接器與機構"},

        # 【7. BBU伺服器備援電池】
        "3211": {"macro_themes": ["BBU伺服器備援電池"], "micro_themes": ["伺服器BBU模組", "AI資料中心備援電力"], "sub_ind": "BBU備援電池模組"},
        "4931": {"macro_themes": ["BBU伺服器備援電池"], "micro_themes": ["高功率鋰電池BBU", "伺服器專用電池模組"], "sub_ind": "高功率鋰電池"},
        "3323": {"macro_themes": ["BBU伺服器備援電池"], "micro_themes": ["BBU電池PACK組裝", "電源管理系統"], "sub_ind": "鋰電池組裝"},
        "6781": {"macro_themes": ["BBU伺服器備援電池"], "micro_themes": ["高階伺服器BBU", "輕型載具電池"], "sub_ind": "高階電池模組"},
        "6558": {"macro_themes": ["BBU伺服器備援電池"], "micro_themes": ["微型鋰電池封裝", "BBU備援電芯"], "sub_ind": "鋰電池封裝製造"},
        "2308": {"macro_themes": ["BBU伺服器備援電池", "AI伺服器ODM與整機代工"], "micro_themes": ["伺服器電源供應器", "BBU儲能系統", "電動車充電樁"], "sub_ind": "電源供應器與儲能"},

        # 【8. AI伺服器ODM與整機代工】
        "2382": {"macro_themes": ["AI伺服器ODM與整機代工"], "micro_themes": ["GB200整機櫃代工", "AI伺服器主機板", "廣達集團"], "sub_ind": "AI伺服器ODM代工"},
        "2317": {"macro_themes": ["AI伺服器ODM與整機代工"], "micro_themes": ["GB200 NVL72整機組裝", "AI伺服器伺服算力中心"], "sub_ind": "EMS電子代工龍頭"},
        "6669": {"macro_themes": ["AI伺服器ODM與整機代工"], "micro_themes": ["白牌AI伺服器主機", "CSP雲端專案"], "sub_ind": "雲端伺服器主機"},
        "3231": {"macro_themes": ["AI伺服器ODM與整機代工"], "micro_themes": ["AI伺服器代工", "GPU運算基板"], "sub_ind": "伺服器製造代工"},
        "2356": {"macro_themes": ["AI伺服器ODM與整機代工"], "micro_themes": ["伺服器整機製造", "英業達伺服器"], "sub_ind": "電子代工製造"},
        "2376": {"macro_themes": ["AI伺服器ODM與整機代工"], "micro_themes": ["技鋼AI伺服器", "伺服器主機板"], "sub_ind": "伺服器主機板製造"},

        # 【9. 伺服器滑軌與導軌機構】
        "2059": {"macro_themes": ["伺服器滑軌與導軌機構"], "micro_themes": ["川湖伺服器滑軌龍頭", "GB200專用導軌"], "sub_ind": "伺服器滑軌龍頭"},
        "6584": {"macro_themes": ["伺服器滑軌與導軌機構"], "micro_themes": ["伺服器機構導軌", "雲端機櫃滑軌"], "sub_ind": "精密滑軌製造"},
        "8210": {"macro_themes": ["伺服器滑軌與導軌機構"], "micro_themes": ["伺服器導軌機構", "電子精密組件"], "sub_ind": "導軌機構件"},

        # 【10. ASIC客製化晶片與矽智財】
        "3661": {"macro_themes": ["ASIC客製化晶片與矽智財"], "micro_themes": ["7nm/3nm先進ASIC設計", "北美CSP大廠專用晶片"], "sub_ind": "ASIC設計服務"},
        "3443": {"macro_themes": ["ASIC客製化晶片與矽智財"], "micro_themes": ["台積電主要ASIC夥伴", "HBM/CoWoS介面IP"], "sub_ind": "ASIC與矽智財"},
        "3035": {"macro_themes": ["ASIC客製化晶片與矽智財"], "micro_themes": ["ASIC客製化設計服務", "聯電集團矽智財"], "sub_ind": "ASIC設計服務"},
        "3529": {"macro_themes": ["ASIC客製化晶片與矽智財"], "micro_themes": ["嵌入式非揮發記憶體IP", "安全晶片矽智財"], "sub_ind": "嵌入式記憶體IP"},
        "6643": {"macro_themes": ["ASIC客製化晶片與矽智財"], "micro_themes": ["高速傳輸介面IP", "PCIe Gen5/6 IP"], "sub_ind": "高速傳輸IP"},
        "2454": {"macro_themes": ["ASIC客製化晶片與矽智財"], "micro_themes": ["旗艦天璣手機晶片", "客製化ASIC晶片", "WiFi 7"], "sub_ind": "手機與通訊IC設計"},
        "6531": {"macro_themes": ["ASIC客製化晶片與矽智財"], "micro_themes": ["客製化ASIC設計", "邊緣運算晶片"], "sub_ind": "ASIC設計服務"},

        # 【11. 重電設備與強韌電網】
        "1519": {"macro_themes": ["重電設備與強韌電網"], "micro_themes": ["超特高壓500kV變壓器", "北美變壓器外銷", "台電強韌電網"], "sub_ind": "特高壓變壓器"},
        "1503": {"macro_themes": ["重電設備與強韌電網"], "micro_themes": ["重電變壓器/配電盤", "外銷北美變壓器標案"], "sub_ind": "重電設備製造"},
        "1513": {"macro_themes": ["重電設備與強韌電網"], "micro_themes": ["GIS氣體絕緣開關", "台電統包統購標案"], "sub_ind": "高壓開關設備"},
        "1514": {"macro_themes": ["重電設備與強韌電網"], "micro_themes": ["配電盤與變壓器", "半導體廠電力工程"], "sub_ind": "配電盤與變壓器"},
        "1504": {"macro_themes": ["重電設備與強韌電網"], "micro_themes": ["重電馬達/開關設備", "儲能電力工程"], "sub_ind": "重電馬達製造"},
        "1609": {"macro_themes": ["重電設備與強韌電網"], "micro_themes": ["特高壓電力電纜", "強韌電網地下化標案"], "sub_ind": "特高壓電纜"},
        "1618": {"macro_themes": ["重電設備與強韌電網"], "micro_themes": ["超高壓電力電纜", "綠能電廠饋線"], "sub_ind": "電力電纜"},

        # 【12. 機器人與智慧自動化】
        "2359": {"macro_themes": ["機器人與智慧自動化"], "micro_themes": ["AI 3D視覺感測", "機器人視覺導航", "輝達生態系"], "sub_ind": "AI機器人視覺"},
        "2049": {"macro_themes": ["機器人與智慧自動化"], "micro_themes": ["滾珠螺桿/線性滑軌", "機器人關節軸承"], "sub_ind": "線性傳動元件"},
        "4576": {"macro_themes": ["機器人與智慧自動化"], "micro_themes": ["直驅馬達/定位平台", "機器人旋轉關節控制"], "sub_ind": "直驅馬達與定位平台"},
        "8374": {"macro_themes": ["機器人與智慧自動化"], "micro_themes": ["機器人視覺系統整合", "自動化機電傳動"], "sub_ind": "自動化機電系統"},
        "4562": {"macro_themes": ["機器人與智慧自動化"], "micro_themes": ["全電式智慧彎管機", "協作型自動化機械"], "sub_ind": "工具機與智慧機械"},
        "6188": {"macro_themes": ["機器人與智慧自動化"], "micro_themes": ["達明協作機器人(TM Robot)", "AI視覺手臂整合"], "sub_ind": "協作型機器人"},

        # 【13. 低軌衛星太空通訊】
        "3491": {"macro_themes": ["低軌衛星太空通訊"], "micro_themes": ["高頻微波元件", "SpaceX/Kuiper地面天線"], "sub_ind": "高頻微波元件"},
        "2313": {"macro_themes": ["低軌衛星太空通訊"], "micro_themes": ["低軌衛星高階HDI板", "SpaceX地面接收主板"], "sub_ind": "高階HDI印刷電路板"},
        "6285": {"macro_themes": ["低軌衛星太空通訊"], "micro_themes": ["地面接收站天線/路由器", "車載衛星通訊"], "sub_ind": "網通與天線模組"},
        "5388": {"macro_themes": ["低軌衛星太空通訊"], "micro_themes": ["衛星通訊接收器", "寬頻光纖設備"], "sub_ind": "寬頻網通設備"},
        "2314": {"macro_themes": ["低軌衛星太空通訊"], "micro_themes": ["衛星收發射頻元件", "地面站天線模組"], "sub_ind": "衛星通訊設備"},

        # 【14. PCB高階載板與伺服器板】
        "3037": {"macro_themes": ["PCB高階載板與伺服器板"], "micro_themes": ["ABF高階載板龍頭", "AI晶片封裝載板"], "sub_ind": "ABF載板製造"},
        "8046": {"macro_themes": ["PCB高階載板與伺服器板"], "micro_themes": ["高階ABF/BT載板", "車用電子載板"], "sub_ind": "IC載板製造"},
        "2368": {"macro_themes": ["PCB高階載板與伺服器板"], "micro_themes": ["AI伺服器高層板", "超高層高頻厚銅板"], "sub_ind": "高層PCB板製造"},
        "2383": {"macro_themes": ["PCB高階載板與伺服器板"], "micro_themes": ["銅箔基板(CCL)龍頭", "高頻高速M8材料"], "sub_ind": "銅箔基板製造"},

        # 【15. 車用電子與電動車供應鏈】
        "6235": {"macro_themes": ["車用電子與電動車供應鏈"], "micro_themes": ["車用連接器", "高壓車用線束"], "sub_ind": "車用連接器"},
        "1536": {"macro_themes": ["車用電子與電動車供應鏈"], "micro_themes": ["電動車減速齒輪箱", "Tesla主要齒輪供應商"], "sub_ind": "汽車傳動齒輪"},
        "2497": {"macro_themes": ["車用電子與電動車供應鏈"], "micro_themes": ["車用環景鏡頭", "ADAS先進駕駛輔助"], "sub_ind": "車用光學鏡頭"},
        "3552": {"macro_themes": ["車用電子與電動車供應鏈"], "micro_themes": ["車用抬頭顯示器(HUD)", "智慧座艙儀表"], "sub_ind": "車用光電顯示"},

        # 【16. 航運貨櫃散裝與航空物流】
        "2603": {"macro_themes": ["航運貨櫃散裝與航空物流"], "micro_themes": ["長榮海運貨櫃龍頭", "歐美遠洋航線"], "sub_ind": "貨櫃海運"},
        "2609": {"macro_themes": ["航運貨櫃散裝與航空物流"], "micro_themes": ["陽明海運貨櫃", "全球航運聯盟"], "sub_ind": "貨櫃海運"},
        "2615": {"macro_themes": ["航運貨櫃散裝與航空物流"], "micro_themes": ["萬海近洋航線龍頭", "亞洲區間航線"], "sub_ind": "近洋貨櫃海運"},
        "2618": {"macro_themes": ["航運貨櫃散裝與航空物流"], "micro_themes": ["長榮航空客運復甦", "航空貨運航線"], "sub_ind": "航空客貨運"},
        "2610": {"macro_themes": ["航運貨櫃散裝與航空物流"], "micro_themes": ["中華航空客貨運", "波音/空巴新機隊"], "sub_ind": "航空客貨運"},
        "2605": {"macro_themes": ["航運貨櫃散裝與航空物流"], "micro_themes": ["新興散裝海運", "海岬型/巴拿馬型散裝"], "sub_ind": "散裝海運"},

        # 【17. 金控股權與高股息存股】
        "2881": {"macro_themes": ["金控股權與高股息存股"], "micro_themes": ["富邦金控獲利王", "壽險與證券金控龍頭"], "sub_ind": "綜合金融金控"},
        "2882": {"macro_themes": ["金控股權與高股息存股"], "micro_themes": ["國泰金控龍頭", "國泰人壽資產配置"], "sub_ind": "綜合金融金控"},
        "2891": {"macro_themes": ["金控股權與高股息存股"], "micro_themes": ["中信金控銀行獲利", "消金與信用卡龍頭"], "sub_ind": "綜合金融金控"},
        "2886": {"macro_themes": ["金控股權與高股息存股"], "micro_themes": ["兆豐金控官股龍頭", "外匯業務與穩健配息"], "sub_ind": "官股金融金控"},
        "2884": {"macro_themes": ["金控股權與高股息存股"], "micro_themes": ["玉山金控財富管理", "綠色金融與科技銀行"], "sub_ind": "綜合金融金控"},

        # 【18. 生技醫療與CDMO新藥】
        "6446": {"macro_themes": ["生技醫療與CDMO新藥"], "micro_themes": ["藥華藥罕病新藥", "美國FDA藥證上市"], "sub_ind": "生技新藥研發"},
        "6472": {"macro_themes": ["生技醫療與CDMO新藥"], "micro_themes": ["保瑞CDMO製藥龍頭", "全球代工外銷"], "sub_ind": "CDMO委託藥品代工"},
        "1795": {"macro_themes": ["生技醫療與CDMO新藥"], "micro_themes": ["美時學名藥龍頭", "抗癌重磅藥物"], "sub_ind": "特殊學名藥"},

        # 【19. 營建資產與都更工程】
        "2520": {"macro_themes": ["營建資產與都更工程"], "micro_themes": ["冠德捷運聯開案", "北部精華區都更建案"], "sub_ind": "營建建材工程"},
        "2501": {"macro_themes": ["營建資產與都更工程"], "micro_themes": ["國建住宅推案", "國泰集團房地產"], "sub_ind": "營建建材工程"},
        "5534": {"macro_themes": ["營建資產與都更工程"], "micro_themes": ["長虹商辦廠辦開發", "內科與北士科商辦"], "sub_ind": "商用不動產開發"},

        # 【20. 綠能儲能與風電太陽能】
        "6806": {"macro_themes": ["綠能儲能與風電太陽能"], "micro_themes": ["森崴能源離岸風電", "光電與儲能案場統包"], "sub_ind": "再生能源統包工程"},
        "9958": {"macro_themes": ["綠能儲能與風電太陽能"], "micro_themes": ["世紀鋼離岸風電水下基礎", "套筒式水下基樁"], "sub_ind": "風電鋼構工程"},
        "6443": {"macro_themes": ["綠能儲能與風電太陽能"], "micro_themes": ["元晶太陽能模組", "大型地面型太陽能案場"], "sub_ind": "太陽能模組製造"}
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
        
    print(f"✅ 精確題材庫重構完成！共收錄 {len(final_mapping)} 檔個股，20 大真實板塊已就緒。")

if __name__ == "__main__":
    generate_theme_database()
