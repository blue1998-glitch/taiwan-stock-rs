import streamlit as st
import pandas as pd
import json
import os

st.set_page_config(page_title="台股真實 RS 動能評分與題材細產業穿透庫", layout="wide")

if "selected_theme" not in st.session_state:
    st.session_state.selected_theme = "無人機"
if "selected_sub_ind" not in st.session_state:
    st.session_state.selected_sub_ind = "飛機維修/發動機零件製造"

@st.cache_data(ttl=60)
def load_market_rankings():
    if os.path.exists("market_rankings.json"):
        with open("market_rankings.json", "r", encoding="utf-8") as f:
            return pd.DataFrame(json.load(f))
    # 預設備援資料
    return pd.DataFrame([
        {"symbol": "2645", "name": "長榮航太", "market": "上市", "close_price": 108.5, "r_5d": 3.2, "r_20d": 12.5, "r_60d": 25.0, "score": 14.39, "rs_rating": 92, "main_industry": "航太與國防", "sub_industry": "飛機維修/發動機零件製造", "themes": ["GE航空供應鏈", "無人機", "波音供應鏈", "軍工國防", "長榮集團"]},
        {"symbol": "2330", "name": "台積電", "market": "上市", "close_price": 980.0, "r_5d": 4.5, "r_20d": 15.0, "r_60d": 32.0, "score": 18.0, "rs_rating": 98, "main_industry": "半導體業", "sub_industry": "先進製程晶圓代工", "themes": ["AI伺服器", "CoWoS先進封裝", "先進製程", "矽光子(CPO)"]},
        {"symbol": "3017", "name": "奇鋐", "market": "上市", "close_price": 650.0, "r_5d": 5.1, "r_20d": 18.2, "r_60d": 28.0, "score": 18.52, "rs_rating": 96, "main_industry": "電子零組件業", "sub_industry": "水冷散熱模組/水冷板", "themes": ["AI伺服器", "水冷散熱", "GB200", "散熱模組"]}
    ])

df_market = load_market_rankings()

all_themes = sorted(list(set(t for sublist in df_market["themes"] for t in sublist)))
all_sub_industries = sorted(df_market["sub_industry"].unique().tolist())
all_main_industries = sorted(df_market["main_industry"].unique().tolist())

# ----------------- 頂部萬用個股搜尋 -----------------
st.title("🎯 台股真實動能 RS 評分與細產業 / 題材全穿透系統")

search_txt = st.text_input("🔍 萬用個股搜尋 (輸入代碼如 2645 或名稱如 長榮航太):", "").strip()

if search_txt:
    matched = df_market[df_market["symbol"].str.contains(search_txt) | df_market["name"].str.contains(search_txt)]
    if not matched.empty:
        stk = matched.iloc[0]
        tier = "🥇 第一梯隊 (RS 90+ 領袖股)" if stk['rs_rating'] >= 90 else ("🥈 第二梯隊 (RS 80-89 強勢股)" if stk['rs_rating'] >= 80 else "🥉 第三梯隊 (RS 75-79 轉強股)")
        
        with st.container():
            st.success(
                f"### 📍 【{stk['name']} ({stk['symbol']})】 個股動能全方位透視\n"
                f"* **市場梯隊**：`{tier}` | **RS 強勢度評分**：`{stk['rs_rating']}` (全市場 PR 值)\n"
                f"* **最新收盤價**：`{stk.get('close_price', 'N/A')} 元` | **綜合動能得分**：`{stk.get('score', 0):.2f}`\n"
                f"* **動能拆解**：近 5 日 `{stk.get('r_5d', 0):+.2f}%` | 近 1 個月 `{stk.get('r_20d', 0):+.2f}%` | 近 1 季 `{stk.get('r_60d', 0):+.2f}%`\n"
                f"* **產業鏈定位**：`{stk['main_industry']}` ➔ `{stk['sub_industry']}`"
            )
            
            st.write("👉 **點擊下方標籤，立即列出全市場同族群個股：**")
            badge_cols = st.columns(len(stk['themes']) + 1)
            
            with badge_cols[0]:
                if st.button(f"🏭 細產業：{stk['sub_industry']}", key=f"btn_sub_{stk['symbol']}"):
                    st.session_state.selected_sub_ind = stk['sub_industry']
                    st.rerun()

            for idx, tag in enumerate(stk['themes']):
                with badge_cols[idx + 1]:
                    if st.button(f"🏷️ 題材：{tag}", key=f"btn_tag_{stk['symbol']}_{tag}"):
                        st.session_state.selected_theme = tag
                        st.rerun()
    else:
        st.warning("查無符合個股，請確認代號或名稱是否正確。")

st.markdown("---")

# ----------------- 三大穿透分頁 -----------------
nav_tab1, nav_tab2, nav_tab3 = st.tabs([
    "🌐 題材概念庫 (點擊看成分股)",
    "🏭 細產業分類庫 (點擊看成分股)",
    "🏆 全市場真實 RS 排行榜"
])

# =========================================================
# TAB 1: 題材概念庫 ➔ 穿透成分股
# =========================================================
with nav_tab1:
    st.subheader("🌐 全市場熱門題材概念 ➔ 成分股穿透")
    
    theme_choice = st.pills(
        label="題材標籤速選",
        options=all_themes,
        selection_mode="single",
        default=st.session_state.selected_theme if st.session_state.selected_theme in all_themes else all_themes[0],
        key="theme_pill_widget"
    )
    if theme_choice:
        st.session_state.selected_theme = theme_choice

    cur_theme = st.session_state.selected_theme
    theme_constituents = df_market[df_market["themes"].apply(lambda tags: cur_theme in tags)].sort_values(by=["rs_rating", "score"], ascending=[False, False]).copy()

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("當前鎖定題材", cur_theme)
    m2.metric("涵蓋成分股", f"{len(theme_constituents)} 檔")
    m3.metric("題材平均 RS", f"{theme_constituents['rs_rating'].mean():.1f}" if not theme_constituents.empty else "0")
    m4.metric("RS ≥ 90 領袖股", f"{len(theme_constituents[theme_constituents['rs_rating'] >= 90])} 檔")

    st.markdown(f"#### 📋 【{cur_theme}】 概念成分股真實動能明細 (依 RS 評分排序)")
    
    theme_constituents["梯隊分級"] = theme_constituents["rs_rating"].apply(
        lambda r: "🥇 Tier 1 (90+)" if r >= 90 else ("🥈 Tier 2 (80-89)" if r >= 80 else "🥉 Tier 3 (75-79)")
    )
    theme_constituents["關聯標籤"] = theme_constituents["themes"].apply(lambda tags: " | ".join([f"#{t}" for t in tags]))
    
    render_theme_df = theme_constituents[
        ["symbol", "name", "rs_rating", "梯隊分級", "close_price", "r_5d", "r_20d", "r_60d", "score", "main_industry", "sub_industry", "關聯標籤"]
    ].rename(
        columns={
            "symbol": "股票代號", "name": "股票名稱", "rs_rating": "RS 評分",
            "close_price": "收盤現價", "r_5d": "近5日(%)", "r_20d": "近1月(%)",
            "r_60d": "近1季(%)", "score": "綜合動能得分",
            "main_industry": "主產業", "sub_industry": "細產業分類"
        }
    )

    st.dataframe(
        render_theme_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "RS 評分": st.column_config.ProgressColumn(
                "RS 強勢度 (PR)",
                help="1~99，全市場真實排名",
                format="%d",
                min_value=1,
                max_value=99
            )
        }
    )

# =========================================================
# TAB 2: 細產業分類庫 ➔ 穿透成分股
# =========================================================
with nav_tab2:
    st.subheader("🏭 全市場細產業價值鏈 ➔ 成分股穿透")
    
    col_ind1, col_ind2 = st.columns([1, 2])
    with col_ind1:
        sel_main = st.selectbox("1. 選擇主產業大類", all_main_industries)
    with col_ind2:
        available_subs = sorted(df_market[df_market["main_industry"] == sel_main]["sub_industry"].unique().tolist())
        sel_sub = st.selectbox("2. 選擇細產業分類", available_subs)
        if sel_sub:
            st.session_state.selected_sub_ind = sel_sub

    cur_sub = st.session_state.selected_sub_ind
    sub_constituents = df_market[df_market["sub_industry"] == cur_sub].sort_values(by=["rs_rating", "score"], ascending=[False, False]).copy()

    s1, s2, s3, s4 = st.columns(4)
    s1.metric("所屬主產業", sel_main)
    s2.metric("所選細產業", cur_sub)
    s3.metric("細產業成分股", f"{len(sub_constituents)} 檔")
    s4.metric("細產業平均 RS", f"{sub_constituents['rs_rating'].mean():.1f}" if not sub_constituents.empty else "0")

    st.markdown(f"#### 📋 【{cur_sub}】 細產業成分股清單")

    sub_constituents["梯隊分級"] = sub_constituents["rs_rating"].apply(
        lambda r: "🥇 Tier 1 (90+)" if r >= 90 else ("🥈 Tier 2 (80-89)" if r >= 80 else "🥉 Tier 3 (75-79)")
    )
    sub_constituents["涵蓋題材"] = sub_constituents["themes"].apply(lambda tags: " | ".join([f"#{t}" for t in tags]))
    
    render_sub_df = sub_constituents[
        ["symbol", "name", "rs_rating", "梯隊分級", "close_price", "r_5d", "r_20d", "r_60d", "score", "main_industry", "涵蓋題材"]
    ].rename(
        columns={
            "symbol": "股票代號", "name": "股票名稱", "rs_rating": "RS 評分",
            "close_price": "收盤現價", "r_5d": "近5日(%)", "r_20d": "近1月(%)",
            "r_60d": "近1季(%)", "score": "綜合動能得分", "main_industry": "主產業"
        }
    )

    st.dataframe(
        render_sub_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "RS 評分": st.column_config.ProgressColumn("RS 強勢度 (PR)", format="%d", min_value=1, max_value=99)
        }
    )

# =========================================================
# TAB 3: 全市場真實 RS 排行榜
# =========================================================
with nav_tab3:
    st.subheader("🏆 全市場真實 RS 動能綜合排行榜")
    
    with st.expander("⚙️ 篩選條件 (RS 門檻、市場、產業)", expanded=True):
        fc1, fc2, fc3 = st.columns(3)
        with fc1:
            rs_min_val = st.slider("最低 RS Rating 門檻", 1, 99, 80, key="all_rs_slider")
        with fc2:
            market_types = st.multiselect("上市 / 上櫃", ["上市", "上櫃"], default=["上市", "上櫃"], key="all_market_types")
        with fc3:
            main_ind_filter = st.selectbox("主產業篩選", ["全部"] + all_main_industries, key="all_main_filter")

    all_filtered = df_market[
        (df_market["rs_rating"] >= rs_min_val) &
        (df_market["market"].isin(market_types))
    ].copy()

    if main_ind_filter != "全部":
        all_filtered = all_filtered[all_filtered["main_industry"] == main_ind_filter]

    k1, k2, k3 = st.columns(3)
    k1.metric("符合條件檔數", f"{len(all_filtered)} 檔")
    k2.metric("平均 RS 評分", f"{all_filtered['rs_rating'].mean():.1f}" if not all_filtered.empty else "0")
    k3.metric("RS ≥ 90 領袖股檔數", f"{len(all_filtered[all_filtered['rs_rating'] >= 90])} 檔")

    all_filtered["梯隊分級"] = all_filtered["rs_rating"].apply(
        lambda r: "🥇 Tier 1 (90+)" if r >= 90 else ("🥈 Tier 2 (80-89)" if r >= 80 else "🥉 Tier 3 (75-79)")
    )
    all_filtered["題材標籤"] = all_filtered["themes"].apply(lambda tags: " | ".join([f"#{t}" for t in tags]))
    
    view_all_df = all_filtered.sort_values(by=["rs_rating", "score"], ascending=[False, False])[
        ["symbol", "name", "rs_rating", "梯隊分級", "close_price", "r_5d", "r_20d", "r_60d", "score", "main_industry", "sub_industry", "題材標籤"]
    ].rename(
        columns={
            "symbol": "代號", "name": "名稱", "rs_rating": "RS 評分",
            "close_price": "收盤現價", "r_5d": "近5日(%)", "r_20d": "近1月(%)",
            "r_60d": "近1季(%)", "score": "綜合動能得分",
            "main_industry": "主產業", "sub_industry": "細產業"
        }
    )

    st.dataframe(
        view_all_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "RS 評分": st.column_config.ProgressColumn("動能 PR", format="%d", min_value=1, max_value=99)
        }
    )
