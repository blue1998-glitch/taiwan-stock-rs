import streamlit as st
import pandas as pd
import json
import os

st.set_page_config(page_title="台股動能 RS 產業與題材雙核心系統", layout="wide")

# ----------------- 1. 手機極簡緊湊膠囊 CSS -----------------
st.markdown("""
<style>
div.stButton > button {
    width: 100% !important;
    min-height: 34px !important;
    height: 35px !important;
    border-radius: 6px !important;
    border: 1px solid #3b4252 !important;
    background: #1e222b !important;
    color: #e5e9f0 !important;
    font-size: 12px !important;
    font-weight: 500 !important;
    white-space: nowrap !important;
    overflow: hidden !important;
    text-overflow: ellipsis !important;
    padding: 1px 6px !important;
    margin-bottom: 2px !important;
    transition: all 0.1s ease-in-out !important;
}

div.stButton > button:hover {
    border-color: #88c0d0 !important;
    background: #2e3440 !important;
    color: #eceff4 !important;
}

.block-container {
    padding-top: 0.8rem !important;
    padding-bottom: 1.5rem !important;
}
</style>
""", unsafe_allow_html=True)

# ----------------- 2. 載入資料庫 -----------------
@st.cache_data(ttl=60)
def load_market_rankings():
    if os.path.exists("market_rankings.json"):
        with open("market_rankings.json", "r", encoding="utf-8") as f:
            return pd.DataFrame(json.load(f))
    # 預備範例
    return pd.DataFrame([
        {"symbol": "2645", "name": "長榮航太", "market": "上市", "close_price": 108.5, "r_5d": 3.2, "r_20d": 12.5, "r_60d": 25.0, "score": 14.39, "rs_rating": 92, "main_industry": "航太與國防", "sub_industry": "航太維修與發動機製造", "macro_themes": ["航太國防與無人機"], "micro_themes": ["GE航太發動機", "軍用無人機", "波音機體維修(MRO)"]},
        {"symbol": "2634", "name": "漢翔", "market": "上市", "close_price": 53.2, "r_5d": 2.1, "r_20d": 8.5, "r_60d": 18.0, "score": 10.07, "rs_rating": 85, "main_industry": "航太與國防", "sub_industry": "機體製造與引擎零件", "macro_themes": ["航太國防與無人機"], "micro_themes": ["國機國造", "GE引擎零組件", "軍用無人機"]},
        {"symbol": "8033", "name": "雷虎", "market": "上市", "close_price": 62.0, "r_5d": 6.8, "r_20d": 16.0, "r_60d": 30.0, "score": 18.36, "rs_rating": 94, "main_industry": "航太與國防", "sub_industry": "無人載具製造", "macro_themes": ["航太國防與無人機"], "micro_themes": ["軍用商規無人機", "國防標案"]},
        {"symbol": "2330", "name": "台積電", "market": "上市", "close_price": 980.0, "r_5d": 4.5, "r_20d": 15.0, "r_60d": 32.0, "score": 18.00, "rs_rating": 98, "main_industry": "半導體業", "sub_industry": "晶圓代工龍頭", "macro_themes": ["先進封裝與光通訊(CoWoS/CPO)", "AI伺服器與液冷/BBU"], "micro_themes": ["CoWoS先進封裝", "CPO矽光子", "2nm先進製程"]},
        {"symbol": "3017", "name": "奇鋐", "market": "上市", "close_price": 650.0, "r_5d": 5.1, "r_20d": 18.2, "r_60d": 28.0, "score": 18.52, "rs_rating": 96, "main_industry": "電子零組件業", "sub_industry": "水冷散熱模組", "macro_themes": ["AI伺服器與液冷/BBU"], "micro_themes": ["水冷散熱板/模組", "散熱風扇", "GB200供應鏈"]},
        {"symbol": "1519", "name": "華城", "market": "上市", "close_price": 520.0, "r_5d": 2.1, "r_20d": 8.0, "r_60d": 15.0, "score": 11.20, "rs_rating": 88, "main_industry": "電機機械", "sub_industry": "特高壓變壓器", "macro_themes": ["重電能源與強韌電網"], "micro_themes": ["超特高壓變壓器", "北美電網外銷", "台電強韌電網"]}
    ])

df_market = load_market_rankings()

# ----------------- 3. 聚合大題材計算與強弱排序 -----------------
all_macro_themes = sorted(list(set(t for sublist in df_market["macro_themes"] for t in sublist if t)))
theme_stats = []
theme_rs_map = {}

for th in all_macro_themes:
    sub_df = df_market[df_market["macro_themes"].apply(lambda tags: th in tags)]
    if not sub_df.empty:
        avg_rs = sub_df["rs_rating"].mean()
        theme_rs_map[th] = avg_rs
        theme_stats.append({
            "theme": th,
            "avg_rs": avg_rs,
            "t1_count": len(sub_df[sub_df["rs_rating"] >= 90]),
            "total_count": len(sub_df)
        })

df_theme_ranked = pd.DataFrame(theme_stats).sort_values(by="avg_rs", ascending=False)

# 2) 縱向法定產業統計 (33 大類)
all_industries = sorted(df_market["main_industry"].unique().tolist())
industry_stats = []
ind_rs_map = {}

for ind in all_industries:
    sub_df = df_market[df_market["main_industry"] == ind]
    if not sub_df.empty:
        avg_rs = sub_df["rs_rating"].mean()
        ind_rs_map[ind] = avg_rs
        industry_stats.append({
            "industry": ind,
            "avg_rs": avg_rs,
            "t1_count": len(sub_df[sub_df["rs_rating"] >= 90]),
            "total_count": len(sub_df)
        })

df_industry_ranked = pd.DataFrame(industry_stats).sort_values(by="avg_rs", ascending=False)

# 3) 雙重共振標記 (強大題材 + 強產業 + 個股 RS>=90)
def check_resonance(row):
    sym_ind = row["main_industry"]
    ind_ok = ind_rs_map.get(sym_ind, 0) >= 75
    theme_ok = any(theme_rs_map.get(t, 0) >= 80 for t in row["macro_themes"])
    stock_ok = row["rs_rating"] >= 90
    return "⚡ 雙強共振" if (ind_ok and theme_ok and stock_ok) else ("🥇 Tier 1 (90+)" if row["rs_rating"] >= 90 else ("🥈 Tier 2 (80-89)" if row["rs_rating"] >= 80 else "🥉 Tier 3 (75-79)"))

df_market["梯隊與共振"] = df_market.apply(check_resonance, axis=1)

# 初始化狀態
if "selected_theme" not in st.session_state:
    st.session_state.selected_theme = df_theme_ranked["theme"].iloc[0] if not df_theme_ranked.empty else "航太國防與無人機"
if "selected_industry" not in st.session_state:
    st.session_state.selected_industry = df_industry_ranked["industry"].iloc[0] if not df_industry_ranked.empty else "航太與國防"

# ----------------- 4. 頂部萬用搜尋 -----------------
st.title("🎯 台股 RS 動能：產業與題材雙核心系統")

search_txt = st.text_input("🔍 萬用個股搜尋 (輸入代碼如 2645 或名稱如 長榮航太):", "").strip()
if search_txt:
    matched = df_market[df_market["symbol"].str.contains(search_txt) | df_market["name"].str.contains(search_txt)]
    if not matched.empty:
        stk = matched.iloc[0]
        ind_avg = ind_rs_map.get(stk['main_industry'], 0)
        macro_str = "、".join(stk["macro_themes"]) if stk["macro_themes"] else "一般產業標的"
        micro_str = " | ".join([f"🎯 {m}" for m in stk["micro_themes"]]) if stk["micro_themes"] else "標準業務"

        with st.container():
            st.success(
                f"### 📍 【{stk['name']} ({stk['symbol']})】\n"
                f"* **動能地位**：`{stk['梯隊與共振']}` | **RS 強勢評分**：`{stk['rs_rating']}` | **綜合得分**：`{stk.get('score', 0):.2f}`\n"
                f"* **縱向產業**：`{stk['main_industry']} (產業均分: {ind_avg:.1f})` ➔ `{stk['sub_industry']}`\n"
                f"* **所屬大板塊**：`{macro_str}`\n"
                f"* **詳細題材特徵**：`{micro_str}`\n"
                f"* **動能拆解**：近5日 `{stk.get('r_5d', 0):+.2f}%` | 近1月 `{stk.get('r_20d', 0):+.2f}%` | 近1季 `{stk.get('r_60d', 0):+.2f}%`"
            )
            
            if stk['macro_themes']:
                st.write("👉 **點擊大題材板塊快速置頂穿透：**")
                b_cols = st.columns(len(stk['macro_themes']) + 1)
                with b_cols[0]:
                    if st.button(f"🏭 {stk['main_industry']}", key=f"s_btn_ind_{stk['symbol']}"):
                        st.session_state.selected_industry = stk['main_industry']
                        st.rerun()
                for idx, tag in enumerate(stk['macro_themes']):
                    with b_cols[idx + 1]:
                        if st.button(f"🔥 {tag}", key=f"s_btn_t_{stk['symbol']}_{tag}"):
                            st.session_state.selected_theme = tag
                            st.rerun()

st.markdown("---")

# ----------------- 5. 主導航分頁 -----------------
tab1, tab2, tab3, tab4 = st.tabs([
    "🔥 題材板塊 (修剪大題材 ➔ 置頂成分股細分)",
    "🏭 產業視角 (看法定類股輪動)",
    "⚡ 雙重共振專區 (強題材+強產業)",
    "🏆 全市場 RS 總榜"
])

# =========================================================
# TAB 1: 修剪後的聚合大題材板塊 ➔ 置頂成分股與詳細微題材
# =========================================================
with tab1:
    cur_t = st.session_state.selected_theme
    t_constituents = df_market[df_market["macro_themes"].apply(lambda tags: cur_t in tags)].sort_values(by=["rs_rating", "score"], ascending=[False, False]).copy()

    # --- 1. 【資料置頂區】：所選大題材成分股清單直接呈現在最頂部 ---
    st.markdown(f"### 📋 【{cur_t}】 題材成分股真實動能明細 (依 RS 評分排序)")

    # 橫跨產業統計
    covered_inds = t_constituents["main_industry"].value_counts().to_dict()
    covered_str = " | ".join([f"{k} ({v}檔)" for k, v in covered_inds.items()])

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("當前大板塊", cur_t)
    k1.caption(f"橫跨產業: {covered_str}")
    k2.metric("真實成分股", f"{len(t_constituents)} 檔")
    k3.metric("題材平均 RS", f"{t_constituents['rs_rating'].mean():.1f}" if not t_constituents.empty else "0")
    k4.metric("RS ≥ 90 領袖股", f"{len(t_constituents[t_constituents['rs_rating'] >= 90])} 檔")

    # 將詳細微題材特徵格式化為直觀標籤
    t_constituents["詳細微題材特徵 / 業務切入點"] = t_constituents["micro_themes"].apply(
        lambda tags: " | ".join([f"🎯 {t}" for t in tags]) if tags else "—"
    )

    st.dataframe(
        t_constituents[
            ["symbol", "name", "rs_rating", "梯隊與共振", "close_price", "r_5d", "r_20d", "r_60d", "score", "main_industry", "詳細微題材特徵 / 業務切入點"]
        ].rename(
            columns={
                "symbol": "代號", "name": "名稱", "rs_rating": "RS 評分",
                "close_price": "收盤價", "r_5d": "5日(%)", "r_20d": "1月(%)",
                "r_60d": "1季(%)", "score": "綜合動能", "main_industry": "所屬主產業"
            }
        ),
        use_container_width=True,
        hide_index=True,
        column_config={"RS 評分": st.column_config.ProgressColumn("RS 強勢度", format="%d", min_value=1, max_value=99)}
    )

    st.markdown("---")

    # --- 2. 【修剪後的修長大題材板塊】：只有 7~8 顆，橫向緊湊排列 ---
    st.subheader("⚡ 核心大題材板塊切換 (每日依平均 RS 動能排序)")
    st.caption("點選下方任一板塊，上方成分股與詳細微題材將即時刷新：")

    cols_per_row = 3
    for row_idx in range(0, len(df_theme_ranked), cols_per_row):
        cols = st.columns(cols_per_row)
        for col_idx in range(cols_per_row):
            idx = row_idx + col_idx
            if idx < len(df_theme_ranked):
                item = df_theme_ranked.iloc[idx]
                t_name = item["theme"]
                t_avg = item["avg_rs"]
                t_cnt = item["total_count"]
                icon = "🔥" if t_avg >= 85 else ("⚡" if t_avg >= 75 else "📦")
                is_active = "▶ " if t_name == cur_t else ""
                btn_label = f"{is_active}{icon} {t_name} | {t_avg:.1f} ({t_cnt}檔)"
                with cols[col_idx]:
                    if st.button(btn_label, key=f"tab1_p_{t_name}"):
                        st.session_state.selected_theme = t_name
                        st.rerun()

# =========================================================
# TAB 2: 產業視角 (縱向產業 ➔ 內部成分股與具備之題材)
# =========================================================
with tab2:
    cur_ind = st.session_state.selected_industry
    ind_constituents = df_market[df_market["main_industry"] == cur_ind].sort_values(by=["rs_rating", "score"], ascending=[False, False]).copy()

    st.markdown(f"### 📋 【{cur_ind}】 產業成分股明細")

    i1, i2, i3, i4 = st.columns(4)
    i1.metric("鎖定產業", cur_ind)
    i2.metric("產業成分股", f"{len(ind_constituents)} 檔")
    i3.metric("產業平均 RS", f"{ind_constituents['rs_rating'].mean():.1f}" if not ind_constituents.empty else "0")
    i4.metric("RS ≥ 90 領袖股", f"{len(ind_constituents[ind_constituents['rs_rating'] >= 90])} 檔")

    ind_constituents["所屬大題材與微題材"] = ind_constituents.apply(
        lambda r: " | ".join(r["macro_themes"] + [f"({m})" for m in r["micro_themes"]]) if r["macro_themes"] else "標準業務/無特定熱點",
        axis=1
    )

    st.dataframe(
        ind_constituents[
            ["symbol", "name", "rs_rating", "梯隊與共振", "close_price", "r_5d", "r_20d", "r_60d", "score", "sub_industry", "所屬大題材與微題材"]
        ].rename(
            columns={
                "symbol": "代號", "name": "名稱", "rs_rating": "RS 評分",
                "close_price": "收盤價", "r_5d": "5日(%)", "r_20d": "1月(%)",
                "r_60d": "1季(%)", "score": "綜合動能", "sub_industry": "細產業分類"
            }
        ),
        use_container_width=True,
        hide_index=True,
        column_config={"RS 評分": st.column_config.ProgressColumn("RS 強勢度", format="%d", min_value=1, max_value=99)}
    )

    st.markdown("---")
    st.subheader("🏭 快速切換法定產業 (依產業輪動強弱排序)")
    for row_idx in range(0, len(df_industry_ranked), cols_per_row):
        cols = st.columns(cols_per_row)
        for col_idx in range(cols_per_row):
            idx = row_idx + col_idx
            if idx < len(df_industry_ranked):
                item = df_industry_ranked.iloc[idx]
                i_name = item["industry"]
                i_avg = item["avg_rs"]
                i_cnt = item["total_count"]
                icon = "🔥" if i_avg >= 80 else ("⚡" if i_avg >= 60 else "📦")
                is_active = "▶ " if i_name == cur_ind else ""
                btn_label = f"{is_active}{icon} {i_name} | {i_avg:.1f} ({i_cnt}檔)"
                with cols[col_idx]:
                    if st.button(btn_label, key=f"tab2_p_{i_name}"):
                        st.session_state.selected_industry = i_name
                        st.rerun()

# =========================================================
# TAB 3: 雙重共振領袖股 (強題材 × 強產業)
# =========================================================
with tab3:
    st.subheader("⚡ 全市場「雙重共振」超級領袖股")
    st.caption("條件：所屬大題材平均 RS ≥ 80 ＋ 所屬產業平均 RS ≥ 75 ＋ 個股 RS ≥ 90（處於強勢產業且站在核心風口）")

    resonance_df = df_market[df_market["梯隊與共振"] == "⚡ 雙強共振"].sort_values(by=["rs_rating", "score"], ascending=[False, False]).copy()

    r1, r2, r3 = st.columns(3)
    r1.metric("雙重共振標的", f"{len(resonance_df)} 檔")
    r1.caption("全市場最強動能交集")
    r2.metric("共振股平均 RS", f"{resonance_df['rs_rating'].mean():.1f}" if not resonance_df.empty else "0")
    r3.metric("平均動能得分", f"{resonance_df['score'].mean():.2f}" if not resonance_df.empty else "0")

    resonance_df["詳細題材特徵"] = resonance_df["micro_themes"].apply(lambda tags: " | ".join([f"🎯 {t}" for t in tags]))

    st.dataframe(
        resonance_df[
            ["symbol", "name", "rs_rating", "close_price", "r_5d", "r_20d", "r_60d", "score", "main_industry", "詳細題材特徵"]
        ].rename(
            columns={
                "symbol": "代號", "name": "名稱", "rs_rating": "RS 評分",
                "close_price": "收盤價", "r_5d": "5日(%)", "r_20d": "1月(%)",
                "r_60d": "1季(%)", "score": "綜合動能",
                "main_industry": "主產業"
            }
        ),
        use_container_width=True,
        hide_index=True,
        column_config={"RS 評分": st.column_config.ProgressColumn("動能 PR", format="%d", min_value=1, max_value=99)}
    )

# =========================================================
# TAB 4: 全市場真實 RS 排行榜
# =========================================================
with tab4:
    st.subheader("🏆 全市場真實 RS 動能綜合排行榜")
    
    with st.expander("⚙️ 篩選條件 (RS 門檻、市場、產業)", expanded=True):
        fc1, fc2, fc3 = st.columns(3)
        with fc1:
            rs_min_val = st.slider("最低 RS Rating 門檻", 1, 99, 80, key="all_rs_slider")
        with fc2:
            market_types = st.multiselect("上市 / 上櫃", ["上市", "上櫃"], default=["上市", "上櫃"], key="all_market_types")
        with fc3:
            main_ind_filter = st.selectbox("主產業篩選", ["全部"] + all_industries, key="all_main_filter")

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

    all_filtered["所屬題材與特徵"] = all_filtered.apply(
        lambda r: " | ".join(r["macro_themes"] + [f"({m})" for m in r["micro_themes"]]) if r["macro_themes"] else "—",
        axis=1
    )
    
    view_all_df = all_filtered.sort_values(by=["rs_rating", "score"], ascending=[False, False])[
        ["symbol", "name", "rs_rating", "梯隊與共振", "close_price", "r_5d", "r_20d", "r_60d", "score", "main_industry", "sub_industry", "所屬題材與特徵"]
    ].rename(
        columns={
            "symbol": "代號", "name": "名稱", "rs_rating": "RS 評分",
            "close_price": "最新現價", "r_5d": "近5日(%)", "r_20d": "近1月(%)",
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
