import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime

st.set_page_config(page_title="台股動能 RS 評分與題材風控系統", layout="wide")

if "selected_theme" not in st.session_state:
    st.session_state.selected_theme = "全部"

PORTFOLIO_FILE = "portfolio.json"

def load_portfolio():
    if os.path.exists(PORTFOLIO_FILE):
        try:
            with open(PORTFOLIO_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return []
    return []

def save_portfolio(data):
    with open(PORTFOLIO_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

@st.cache_data(ttl=60)
def load_market_rankings():
    if os.path.exists("market_rankings.json"):
        with open("market_rankings.json", "r", encoding="utf-8") as f:
            return pd.DataFrame(json.load(f))
    return pd.DataFrame([
        {"symbol": "2645", "name": "長榮航太", "market": "上市", "score": 88.5, "rs_rating": 92, "main_industry": "航太與國防", "sub_industry": "飛機維修/發動機製造", "themes": ["GE航空供應鏈", "無人機", "波音供應鏈", "軍工概念"]},
        {"symbol": "2330", "name": "台積電", "market": "上市", "score": 95.2, "rs_rating": 98, "main_industry": "半導體", "sub_industry": "晶圓代工", "themes": ["AI伺服器", "CoWoS", "先進製程", "矽光子(CPO)"]},
        {"symbol": "2634", "name": "漢翔", "market": "上市", "score": 81.0, "rs_rating": 84, "main_industry": "航太與國防", "sub_industry": "機體製造/發動機零件", "themes": ["GE航空供應鏈", "無人機", "國機國造", "軍工概念"]},
        {"symbol": "3017", "name": "奇鋐", "market": "上市", "score": 91.2, "rs_rating": 95, "main_industry": "電子零組件", "sub_industry": "散熱模組/水冷板", "themes": ["AI伺服器", "水冷散熱", "GB200"]},
        {"symbol": "8033", "name": "雷虎", "market": "上市", "score": 86.4, "rs_rating": 89, "main_industry": "航太與國防", "sub_industry": "無人載具製造", "themes": ["無人機", "軍工概念"]}
    ])

df_market = load_market_rankings()

tab1, tab2 = st.tabs(["🏆 全市場 RS 排行與題材連動檢索", "📈 個人持倉風控監控"])

with tab1:
    st.title("🏆 全市場 RS 動能排行榜 & 題材族群穿透")
    
    all_themes = sorted(list(set(t for sublist in df_market["themes"] for t in sublist)))
    all_mains = ["全部"] + sorted(df_market["main_industry"].unique().tolist())

    with st.expander("⚙️ 多維度篩選控制台 (動能、產業、題材)", expanded=True):
        f_col1, f_col2, f_col3, f_col4 = st.columns([1.2, 1.2, 1.2, 1.4])
        
        with f_col1:
            min_rs_slider = st.slider("最低 RS Rating 門檻", 1, 99, 75)
        with f_col2:
            market_filter = st.multiselect("上市櫃別", ["上市", "上櫃"], default=["上市", "上櫃"])
        with f_col3:
            selected_main = st.selectbox("主產業分類", all_mains)
        with f_col4:
            if selected_main != "全部":
                sub_opts = sorted(df_market[df_market["main_industry"] == selected_main]["sub_industry"].unique().tolist())
            else:
                sub_opts = sorted(df_market["sub_industry"].unique().tolist())
            selected_sub = st.multiselect("次產業細項 (可複選)", sub_opts)

        st.markdown("**🔥 熱門題材快速切換 (點擊切換全市場題材池)：**")
        pill_list = ["全部"] + all_themes
        
        current_pill = st.pills(
            label="概念標籤速選",
            options=pill_list,
            selection_mode="single",
            default=st.session_state.selected_theme if st.session_state.selected_theme in pill_list else "全部",
            key="pills_theme_selector"
        )
        if current_pill:
            st.session_state.selected_theme = current_pill

    st.markdown("---")
    search_txt = st.text_input("🔎 萬用個股查詢 (輸入代號如 2645 或名稱如 長榮航太):", "").strip()
    
    if search_txt:
        matched = df_market[df_market["symbol"].str.contains(search_txt) | df_market["name"].str.contains(search_txt)]
        if not matched.empty:
            stk = matched.iloc[0]
            tier_badge = "🥇 第一梯隊 (領袖股 RS 90+)" if stk['rs_rating'] >= 90 else ("🥈 第二梯隊 (強勢股 RS 80-89)" if stk['rs_rating'] >= 80 else "🥉 第三梯隊 (轉強股 RS 75-79)")
            
            st.info(
                f"### 📍 【{stk['name']} ({stk['symbol']})】 個股深度檔案\n"
                f"* **市場地位**：`{tier_badge}` | **RS Rating**：`{stk['rs_rating']}`\n"
                f"* **產業定位**：`{stk['main_industry']}` ➔ `{stk['sub_industry']}`"
            )
            
            st.write("👉 **點擊下方個股關聯標籤，立即列出全市場同族群個股：**")
            btn_cols = st.columns(len(stk['themes']) + 2)
            for i, theme_tag in enumerate(stk['themes']):
                with btn_cols[i]:
                    if st.button(f"🏷️ {theme_tag}", key=f"btn_{stk['symbol']}_{theme_tag}"):
                        st.session_state.selected_theme = theme_tag
                        st.rerun()

    filtered = df_market[
        (df_market["rs_rating"] >= min_rs_slider) &
        (df_market["market"].isin(market_filter))
    ].copy()

    if selected_main != "全部":
        filtered = filtered[filtered["main_industry"] == selected_main]
    if selected_sub:
        filtered = filtered[filtered["sub_industry"].isin(selected_sub)]
    if st.session_state.selected_theme != "全部":
        filtered = filtered[filtered["themes"].apply(lambda tags: st.session_state.selected_theme in tags)]

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("當前鎖定題材", st.session_state.selected_theme)
    k2.metric("符合條件檔數", f"{len(filtered)} 檔")
    k3.metric("平均 RS 評分", f"{filtered['rs_rating'].mean():.1f}" if not filtered.empty else "0")
    k4.metric("RS ≥ 90 領袖檔數", f"{len(filtered[filtered['rs_rating'] >= 90])} 檔")

    st.markdown("### 📋 領袖股與題材族群清單")
    display_tbl = filtered.sort_values(by="rs_rating", ascending=False).copy()
    display_tbl["梯隊分級"] = display_tbl["rs_rating"].apply(
        lambda r: "🥇 Tier 1 (90+)" if r >= 90 else ("🥈 Tier 2 (80-89)" if r >= 80 else "🥉 Tier 3 (75-79)")
    )
    display_tbl["題材標籤"] = display_tbl["themes"].apply(lambda tags: " | ".join([f"#{t}" for t in tags]))
    
    view_df = display_tbl[["symbol", "name", "rs_rating", "梯隊分級", "main_industry", "sub_industry", "題材標籤"]].rename(
        columns={
            "symbol": "代號", "name": "名稱", "rs_rating": "RS 評分",
            "main_industry": "主產業", "sub_industry": "次產業"
        }
    )
    
    st.dataframe(
        view_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "RS 評分": st.column_config.ProgressColumn(
                "動能 PR 值",
                help="1~99",
                format="%d",
                min_value=1,
                max_value=99
            )
        }
    )

with tab2:
    st.title("📈 個人持倉風控紀律與加碼防禦監控")
    portfolio = load_portfolio()

    with st.expander("➕ 新增持倉標的", expanded=False):
        c1, c2, c3, c4, c5 = st.columns(5)
        p_symbol = c1.text_input("股票代號", "2645")
        p_name = c2.text_input("股票名稱", "長榮航太")
        p_buy_price = c3.number_input("買入均價", value=100.0, step=0.5)
        p_qty = c4.number_input("持有張數", value=2, step=1)
        p_cur_price = c5.number_input("目前現價", value=108.0, step=0.5)
        
        c6, c7 = st.columns(2)
        p_peak_price = c6.number_input("進場後波段最高價", value=max(p_buy_price, p_cur_price), step=0.5)
        p_ma20 = c7.number_input("目前月線 (20MA) 價位", value=102.0, step=0.5)
        
        if st.button("確認加入持倉"):
            portfolio.append({
                "symbol": p_symbol, "name": p_name, "buy_price": p_buy_price,
                "qty": p_qty, "cur_price": p_cur_price, "peak_price": p_peak_price,
                "ma20": p_ma20, "date": datetime.now().strftime("%Y-%m-%d")
            })
            save_portfolio(portfolio)
            st.success(f"已新增 {p_name} 至持倉！")
            st.rerun()

    if portfolio:
        st.markdown("### 🛡️ 5 大風控防線即時診斷")
        port_records = []
        for pos in portfolio:
            b_price = pos["buy_price"]
            c_price = pos["cur_price"]
            p_price = pos["peak_price"]
            ma20 = pos["ma20"]
            
            pnl_pct = ((c_price - b_price) / b_price) * 100
            pullback_pct = ((c_price - p_price) / p_price) * 100
            ma20_bias = ((c_price - ma20) / ma20) * 100

            alerts = []
            if pnl_pct <= -7.0:
                alerts.append("🚨 觸發 -7% 原始停損防線！")
            if pnl_pct >= 10.0 and c_price <= b_price * 1.01:
                alerts.append("🛡️ 獲利曾達標，啟動保本停損！")
            if pullback_pct <= -10.0:
                alerts.append("⚠️ 波段高點回檔達 -10%，執行停利！")
            if ma20_bias >= 30.0:
                alerts.append("🔥 月線正乖離 > 30% 過熱警戒！")

            status_txt = " | ".join(alerts) if alerts else "✅ 持倉健康"

            port_records.append({
                "代號": pos["symbol"], "名稱": pos["name"], "持股張數": pos["qty"],
                "買進均價": b_price, "目前現價": c_price,
                "未實現損益(%)": f"{pnl_pct:+.2f}%",
                "高點回檔(%)": f"{pullback_pct:.2f}%",
                "月線乖離(%)": f"{ma20_bias:+.2f}%",
                "風控診斷": status_txt
            })

        st.dataframe(pd.DataFrame(port_records), use_container_width=True, hide_index=True)

        st.markdown("---")
        st.markdown("### 📐 金字塔加碼均價與防禦緩衝試算器")
        with st.expander("點擊展開金字塔試算工具", expanded=True):
            calc_col1, calc_col2, calc_col3 = st.columns(3)
            with calc_col1:
                c_sym = st.selectbox("選擇試算持倉", [f"{p['symbol']} - {p['name']}" for p in portfolio])
                cur_pos = portfolio[[f"{p['symbol']} - {p['name']}" for p in portfolio].index(c_sym)]
            with calc_col2:
                add_price = st.number_input("預計加碼價格", value=cur_pos["cur_price"] * 1.05, step=0.5)
            with calc_col3:
                add_qty = st.number_input("預計加碼張數", value=1, min_value=1, step=1)

            total_cost = (cur_pos["buy_price"] * cur_pos["qty"]) + (add_price * add_qty)
            total_qty = cur_pos["qty"] + add_qty
            new_avg_price = total_cost / total_qty
            buffer_pct = ((add_price - new_avg_price) / new_avg_price) * 100

            st.write(
                f"📊 **試算結果**：\n"
                f"* 加碼後持有張數：**{total_qty} 張**\n"
                f"* 新持倉成本均價：**{new_avg_price:.2f} 元**\n"
                f"* 當前價位防禦緩衝：**{buffer_pct:+.2f}%**"
            )
            
        if st.button("🗑️ 清空所有持倉"):
            save_portfolio([])
            st.rerun()
    else:
        st.info("目前無持倉資料，請點擊上方展開欄新增持股。")
      
