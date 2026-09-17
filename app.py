import os, json, re
from datetime import datetime, timezone, timedelta
import numpy as np
import pandas as pd
import requests
import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from streamlit_gsheets import GSheetsConnection
from google import genai

# ============================================================
# 台股 Trend OS — 交易作業系統
# 核心：資料 → 市場環境 → 個股狀態 → 風控 → 行動 → 紀錄
# ============================================================
st.set_page_config(page_title="台股 Trend OS", page_icon="🧭", layout="wide",
                   initial_sidebar_state="collapsed")
TZ = timezone(timedelta(hours=8))
NOW = lambda fmt="%Y-%m-%d %H:%M:%S": datetime.now(TZ).strftime(fmt)
DATA_FILE = "portfolio.json"
WATCHLIST_COLS = ["symbol","name","theme","created_date","stage","prev_stage",
                  "substate","base_count","pivot_price","strategy_tranches",
                  "transition_date","is_active"]

STAGES = {
    "醞釀期 (VCP)": {"risk":"觀察/試單","tranches":"2 批","rule":"收縮量試單；突破樞紐再確認","stop":"整理區最新 Swing Low"},
    "初升段 (Breakout)": {"risk":"進攻","tranches":"2 批","rule":"帶量突破；回測守穩再補","stop":"突破長紅低點或 20MA"},
    "主升段 (Trend)": {"risk":"持有/順勢","tranches":"1 批","rule":"沿 10/20MA 趨勢持有","stop":"20MA 或前波低點"},
    "末升段 (Climax)": {"risk":"收割","tranches":"0 批","rule":"不追買；收緊移動停利","stop":"5/10MA"},
    "出貨期 (Distribution)": {"risk":"防守","tranches":"0 批","rule":"停止加碼；檢查退出條件","stop":"結構破壞即退出"},
    "打底期 (Basing)": {"risk":"等待","tranches":"0 批","rule":"等待趨勢重新建立","stop":"—"},
}

def clean_sym(x):
    s = str(x or "").strip()
    return s[:-2] if s.endswith(".0") else s

@st.cache_data(ttl=3600)
def stock_names():
    try:
        with open("stock_names.json", encoding="utf-8") as f: return json.load(f)
    except Exception: return {}

NAMES = stock_names()

def clean_name(name, symbol):
    s = clean_sym(symbol).upper()
    if s in NAMES: return NAMES[s]
    raw = str(name or "").strip()
    if not raw: return s
    for suffix in ["股份有限公司台灣分公司","股份有限公司","有限股份公司","有限公司","(股)公司","（股）公司"]:
        raw = raw.replace(suffix, "")
    return raw.strip() or s

def gs():
    try: return st.connection("gsheets", type=GSheetsConnection)
    except Exception: return None

def load_portfolio():
    c = gs()
    if c:
        try:
            df = c.read(ttl=0)
            if df is not None and not df.empty:
                out=[]
                for _,r in df.iterrows():
                    x=r.dropna().to_dict(); sym=clean_sym(x.get("symbol"))
                    if sym:
                        hist=x.get("history",[])
                        try: hist=json.loads(hist) if isinstance(hist,str) else hist
                        except Exception: hist=[]
                        out.append({"symbol":sym,"name":clean_name(x.get("name"),sym),
                                    "market":str(x.get("market","TW")).upper(),
                                    "entry_date":str(x.get("entry_date",NOW("%Y-%m-%d"))),
                                    "avg_cost":float(x.get("avg_cost",0) or 0),
                                    "shares":int(float(x.get("shares",0) or 0)),
                                    "record_high":float(x.get("record_high",x.get("avg_cost",0)) or 0),
                                    "realized_pnl":float(x.get("realized_pnl",0) or 0),
                                    "history":hist})
                if out:return out
        except Exception: pass
    try:
        with open(DATA_FILE,encoding="utf-8") as f:return json.load(f)
    except Exception:return []

def save_portfolio(data):
    try:
        with open(DATA_FILE,"w",encoding="utf-8") as f: json.dump(data,f,ensure_ascii=False,indent=2)
    except Exception: pass
    c=gs()
    if c:
        try:
            cols=["symbol","name","market","entry_date","avg_cost","shares","record_high","realized_pnl","history"]
            rows=[{k:x.get(k,"") for k in cols} for x in data]
            for r in rows:r["history"]=json.dumps(r["history"],ensure_ascii=False)
            c.update(data=pd.DataFrame(rows,columns=cols))
        except Exception: pass

def log(action,price,delta,left,pnl="",note=""):
    return {"時間":NOW("%Y-%m-%d %H:%M"),"動作":action,"成交價":price,
            "異動股數":delta,"剩餘股數":left,"單筆損益":pnl,"備註":note}

@st.cache_data(ttl=900)
def market_db():
    data=[]; status="無資料"
    try:
        if os.path.exists("market_rankings.json"):
            with open("market_rankings.json",encoding="utf-8") as f:data=json.load(f)
            if data: status="本機資料庫"
    except Exception: pass
    if not data:
        try:
            u="https://raw.githubusercontent.com/blue1998-glitch/-/main/market_rankings.json"
            r=requests.get(u,timeout=8)
            if r.ok:data=r.json();status="線上同步"
        except Exception: pass
    for x in data:
        x["symbol"]=clean_sym(x.get("symbol"));x["name"]=clean_name(x.get("name"),x["symbol"])
    return data,status

def ticker(sym,mkt):
    return f"{clean_sym(sym)}.{ 'TWO' if 'TWO' in str(mkt).upper() or '上櫃' in str(mkt) else 'TW'}"

@st.cache_data(ttl=900)
def history(sym,mkt,period="14mo"):
    t=ticker(sym,mkt)
    try:
        d=yf.Ticker(t).history(period=period,auto_adjust=False)
        if d.empty:
            alt=f"{clean_sym(sym)}.{ 'TW' if '.TWO' in t else 'TWO'}"
            d=yf.Ticker(alt).history(period=period,auto_adjust=False)
        return d
    except Exception:return pd.DataFrame()

def indicators(d):
    if d is None or len(d)<20:return {}
    c,v,h,l=d["Close"],d["Volume"],d["High"],d["Low"]
    ma={n:c.rolling(n,min_periods=max(3,min(len(c),n//4))).mean() for n in [5,20,60,130,260]}
    tr=pd.concat([h-l,(h-c.shift()).abs(),(l-c.shift()).abs()],axis=1).max(axis=1)
    atr10=tr.rolling(10,min_periods=3).mean().iloc[-1]
    atr60=tr.rolling(60,min_periods=10).mean().iloc[-1] if len(d)>=10 else atr10
    vm20=v.rolling(20,min_periods=5).mean().iloc[-1]
    vm60=v.rolling(60,min_periods=10).mean().iloc[-1]
    cur=float(c.iloc[-1]); high60=float(h.tail(60).max()); high260=float(h.tail(min(260,len(d))).max())
    low260=float(l.tail(min(260,len(d))).min())
    ret=lambda n: float((c.iloc[-1]/c.iloc[-n-1]-1)*100) if len(c)>n else 0
    return dict(c=c,v=v,h=h,l=l,ma=ma,cur=cur,high60=high60,high260=high260,low260=low260,
                r5=ret(5),r20=ret(20),r60=ret(60),bias20=(cur/ma[20].iloc[-1]-1)*100,
                relvol20=float(v.iloc[-1]/vm20) if vm20 else 1,
                relvol60=float(v.iloc[-1]/vm60) if vm60 else 1,
                vdu=float(v.tail(5).min()/vm60) if vm60 else 1,
                atr_ratio=float(atr10/atr60) if atr60 else 1,
                slope20=float(ma[20].pct_change(5).iloc[-1]) if len(d)>6 else 0,
                slope60=float(ma[60].pct_change(10).iloc[-1]) if len(d)>11 else 0)

def dow(d):
    if len(d)<20:return "收斂"
    h,l=d["High"].tail(20),d["Low"].tail(20)
    if h.iloc[-1]>=h.max()*.98 and l.iloc[-1]>l.min():return "HH + HL"
    if l.iloc[-1]<=l.min()*1.02 and h.iloc[-1]<h.max():return "LH + LL"
    return "收斂"

def stage(feat,structure):
    if not feat:return "打底期 (Basing)","資料不足"
    c,m=feat["cur"],feat["ma"]
    if structure=="LH + LL" or (c<m[130].iloc[-1] and c<m[260].iloc[-1] and feat["slope60"]<0):
        return "打底期 (Basing)","結構走弱"
    if feat["bias20"]>25 or c/m[60].iloc[-1]>1.25:return "末升段 (Climax)","過熱"
    if c>m[20].iloc[-1]>m[60].iloc[-1]>m[130].iloc[-1]>m[260].iloc[-1] and feat["slope20"]>0 and feat["slope60"]>0 and structure=="HH + HL":
        return "主升段 (Trend)","趨勢完整"
    body=(c/float(feat["c"].iloc[-1-1])-1) if len(feat["c"])>1 else 0
    if c>=feat["high60"]*.99 and feat["relvol20"]>=1.5 and c>m[5].iloc[-1]>m[20].iloc[-1]>m[60].iloc[-1]:
        return "初升段 (Breakout)","突破確認"
    if c>m[60].iloc[-1] and abs(m[20].iloc[-1]-m[60].iloc[-1])/m[60].iloc[-1]<.03 and feat["vdu"]<=.5 and feat["atr_ratio"]<.65:
        return "醞釀期 (VCP)","波動/量能收縮"
    return "打底期 (Basing)","等待表態"

def benchmark(mkt):
    sym="^TWOII" if "TWO" in str(mkt).upper() else "^TWII"
    try:
        d=yf.Ticker(sym).history(period="1y")
        if d.empty:d=yf.Ticker("0050.TW").history(period="1y")
        c=d["Close"]
        return d,float((c.iloc[-1]/c.iloc[-6]-1)*100),float((c.iloc[-1]/c.iloc[-21]-1)*100),float((c.iloc[-1]/c.iloc[-61]-1)*100)
    except Exception:return pd.DataFrame(),0,0,0

def rs(d,mkt):
    b,_,_,_=benchmark(mkt)
    if d.empty or b.empty:return 100,100
    a=pd.DataFrame({"a":d["Close"],"b":b["Close"]}).dropna()
    raw=a.a/a.b*100
    ma60=raw.rolling(60,min_periods=15).mean()
    ratio=(raw/ma60*100).dropna()
    ma20=ratio.rolling(20,min_periods=5).mean()
    mom=(ratio/ma20*100).dropna()
    return round(float(ratio.iloc[-1]),2) if len(ratio) else 100,round(float(mom.iloc[-1]),2) if len(mom) else 100

def pnl(shares,cost,price,discount=.6):
    fee=.001425*discount
    buy=shares*cost*(1+fee);sell=shares*price*(1-fee-.003)
    p=round(sell-buy);return p,round(p/buy*100,2) if buy else 0

@st.cache_data(ttl=900)
def breadth(db,mkt):
    syms=[ticker(x["symbol"],x.get("market","TW")) for x in db if clean_sym(x.get("symbol")) and
          (mkt=="ALL" or ("TWO" in str(x.get("market","")).upper() if mkt=="TWO" else "TWO" not in str(x.get("market","")).upper()))]
    if not syms:return pd.DataFrame()
    try:
        raw=yf.download(syms,period="1y",group_by="column",auto_adjust=True,progress=False,threads=True)
        c=raw["Close"] if isinstance(raw.columns,pd.MultiIndex) else raw[["Close"]]
        h=raw["High"] if isinstance(raw.columns,pd.MultiIndex) else raw[["High"]]
        l=raw["Low"] if isinstance(raw.columns,pd.MultiIndex) else raw[["Low"]]
        c,h,l=c.ffill(),h.ffill(),l.ffill()
        total=c.notna().sum(axis=1).replace(0,np.nan)
        ma20,ma60,ma240=c.rolling(20).mean(),c.rolling(60).mean(),c.rolling(240).mean()
        nh=h.rolling(60,min_periods=20).max();nl=l.rolling(60,min_periods=20).min()
        out=pd.DataFrame(index=c.index)
        out["MAB20"]=(c>ma20).sum(axis=1)/total*100
        out["MAB60"]=(c>ma60).sum(axis=1)/total*100
        out["MAB240"]=(c>ma240).sum(axis=1)/total*100
        out["NNH60"]=(h>=nh).sum(axis=1)-(l<=nl).sum(axis=1)
        out["dist60"]=((c.mean(axis=1)-c.mean(axis=1).rolling(60).mean())/c.mean(axis=1).rolling(60).mean()*100)
        return out.dropna(subset=["MAB20"])
    except Exception:return pd.DataFrame()

def ai_client():
    key=st.secrets.get("GEMINI_API_KEY",os.getenv("GEMINI_API_KEY"))
    return genai.Client(api_key=key) if key else None

# -------------------- Header / command center --------------------
db,db_status=market_db()
portfolio=load_portfolio()
st.title("🧭 台股 Trend OS")
st.caption("把「看盤、選股、持倉、風控、觀察、AI」收斂成同一套決策流程。")

if db:
    st.success(f"市場資料：{len(db):,} 檔｜{db_status}｜資料更新 {NOW()}")
else: st.warning("市場排名資料尚未載入。")

tab1,tab2,tab3,tab4,tab5=st.tabs(["🎛️ 決策中樞","📈 持倉作戰室","🔎 全市場雷達","🎯 題材/觀察","🤖 AI 研究員"])

# -------------------- 1. Decision Center --------------------
with tab1:
    st.subheader("今日先回答三件事：市場能不能打？我的部位有沒有風險？哪裡正在發動？")
    mkt=st.selectbox("市場",["上市 (TWSE)","上櫃 (TPEX)"],key="center_mkt")
    b=breadth(db,"TWO" if "上櫃" in mkt else "TW")
    if b.empty:
        st.info("大盤廣度暫時無法取得。")
    else:
        last,prev=b.iloc[-1],b.iloc[-2] if len(b)>1 else b.iloc[-1]
        green=last.MAB20>=60 and last.MAB60>=50 and last.NNH60>30
        red=last.MAB20<40 or last.MAB60<35 or last.NNH60<-30
        regime="🟢 擴張" if green else ("🔴 收縮" if red else "🟡 震盪")
        c1,c2,c3,c4=st.columns(4)
        c1.metric("市場狀態",regime)
        c2.metric("MAB20",f"{last.MAB20:.1f}%",f"{last.MAB20-prev.MAB20:+.1f}%")
        c3.metric("MAB60",f"{last.MAB60:.1f}%",f"{last.MAB60-prev.MAB60:+.1f}%")
        c4.metric("NNH60",f"{last.NNH60:+.0f}",f"{last.NNH60-prev.NNH60:+.0f}")
        fig=go.Figure()
        for col,name in [("MAB20","20MA 廣度"),("MAB60","60MA 廣度"),("MAB240","240MA 廣度")]:
            fig.add_trace(go.Scatter(x=b.index,y=b[col],mode="lines",name=name))
        fig.add_hline(y=50,line_dash="dash")
        fig.update_layout(height=360,margin=dict(l=20,r=20,t=35,b=20),hovermode="x unified")
        st.plotly_chart(fig,use_container_width=True)
        st.info("這裡只負責「市場環境」，不替你把環境直接翻成買賣指令；個股與部位要回到各自模組確認。")

# -------------------- 2. Portfolio War Room --------------------
with tab2:
    left,right=st.columns([3,1])
    with right:
        with st.expander("⚙️ 風控參數",expanded=False):
            stop=st.number_input("初始停損 %",1.,50.,7.,.5)
            be_trigger=st.number_input("保本啟動 %",1.,50.,8.,.5)
            trail=st.number_input("高點回撤停利 %",1.,50.,10.,.5)
            hot=st.number_input("20MA 過熱 %",5.,100.,30.,1.)
            fee_discount=st.number_input("手續費折數",.01,1.,.6,.05)
    with left:
        st.subheader("📈 持倉作戰室")
        with st.expander("➕ 建立持倉",False):
            with st.form("new_position"):
                a,b=st.columns(2)
                s=a.text_input("代號"); n=a.text_input("名稱")
                market=a.selectbox("市場",["TW","TWO"]); date=b.date_input("進場日")
                price=b.number_input("成本",.1,step=.1); shares=b.number_input("股數",1,step=1000)
                if st.form_submit_button("建立持倉",use_container_width=True) and s:
                    s=clean_sym(s);portfolio.append({"symbol":s,"name":clean_name(n,s),"market":market,
                    "entry_date":str(date),"avg_cost":float(price),"shares":int(shares),"record_high":float(price),
                    "realized_pnl":0,"history":[log("🌱 建倉",price,f"+{shares}",shares,"","初始持倉")]})
                    save_portfolio(portfolio);st.rerun()
        if not portfolio:
            st.info("尚無持倉。")
        for i,x in enumerate(portfolio):
            d=history(x["symbol"],x["market"],"1y"); f=indicators(d)
            if not f: continue
            rsm,rsmom=rs(d,x["market"]); cur=f["cur"]; high=max(float(x.get("record_high",x["avg_cost"])),float(f["high260"]))
            x["record_high"]=high;p,roi=pnl(x["shares"],x["avg_cost"],cur,fee_discount)
            be=(high/x["avg_cost"]-1)*100>=be_trigger
            init=x["avg_cost"]*(1-stop/100); be_line=x["avg_cost"]*(1+fee_discount*.001425*2+.003)
            effective=max(init,be_line) if be else init
            pull=high*(1-trail/100)
            status="⚪ 正常持有"
            if cur<=effective:status="🔴 風控線觸發"
            elif cur<=pull and cur>x["avg_cost"]:status="🟣 高點回撤"
            elif f["bias20"]>=hot:status="🟠 乖離過熱"
            title=f"{x['name']} ({x['symbol']})｜{status}｜RS {rsm:.1f}"
            with st.expander(title,expanded=True):
                c=st.columns(6)
                for col,label,val in zip(c,["現價","報酬率","未實現損益","RS Ratio","RS 動能","20MA乖離"],
                                         [f"${cur:.2f}",f"{roi:+.2f}%",f"{p:+,}",f"{rsm:.1f}",f"{rsmom:.1f}",f"{f['bias20']:+.1f}%"]):
                    col.metric(label,val)
                st.caption(f"高點 ${high:.2f}｜初始防線 ${init:.2f}｜有效防線 ${effective:.2f}｜回撤線 ${pull:.2f}")
                a,b,c=st.columns(3)
                add_p=a.number_input("加碼價",.1,value=float(cur),key=f"ap{i}")
                add_s=a.number_input("加碼股數",1,step=100,value=1000,key=f"as{i}")
                red_p=b.number_input("減碼價",.1,value=float(cur),key=f"rp{i}")
                red_s=b.number_input("減碼股數",1,max_value=int(x["shares"]),step=100,value=min(1000,int(x["shares"])),key=f"rs{i}")
                if a.button("🔼 加碼",key=f"add{i}",use_container_width=True):
                    ns=x["shares"]+int(add_s); x["avg_cost"]=round((x["shares"]*x["avg_cost"]+int(add_s)*add_p)/ns,2);x["shares"]=ns
                    x.setdefault("history",[]).append(log("🔼 加碼",add_p,f"+{add_s}",ns,"","人工執行"))
                    save_portfolio(portfolio);st.rerun()
                if b.button("🔽 減碼",key=f"red{i}",use_container_width=True):
                    rp,rr=pnl(int(red_s),x["avg_cost"],red_p,fee_discount);ns=x["shares"]-int(red_s)
                    x["realized_pnl"]=x.get("realized_pnl",0)+rp;x.setdefault("history",[]).append(log("🔽 減碼",red_p,f"-{red_s}",ns,f"{rp:+,}","人工執行"))
                    if ns:x["shares"]=ns
                    else:portfolio.pop(i)
                    save_portfolio(portfolio);st.rerun()
                if c.button("🗑️ 結清",key=f"del{i}",use_container_width=True):
                    portfolio.pop(i);save_portfolio(portfolio);st.rerun()
                if x.get("history"):
                    st.dataframe(pd.DataFrame(x["history"]),use_container_width=True,hide_index=True)

# -------------------- 3. Market Radar --------------------
with tab3:
    st.subheader("🔎 全市場雷達")
    if db:
        df=pd.DataFrame(db)
        for col,default in [("rs_rating",50),("rs_ratio",100),("rs_momentum",100),("market","")]:
            if col not in df:df[col]=default
        c1,c2=st.columns(2);minrs=c1.slider("最低 RS",1,99,85);markets=c2.multiselect("市場",sorted(df.market.dropna().unique()),default=sorted(df.market.dropna().unique()))
        view=df[(df.rs_rating>=minrs)&df.market.isin(markets)].copy().sort_values("rs_rating",ascending=False)
        view["股票名稱"]=view.apply(lambda r:clean_name(r.get("name"),r.get("symbol")),axis=1)
        show=view[["symbol","股票名稱","market","rs_rating","rs_ratio","rs_momentum"]].rename(columns={"symbol":"代號","market":"市場","rs_rating":"RS Rating","rs_ratio":"RS Ratio","rs_momentum":"RS 動能"})
        st.dataframe(show,use_container_width=True,hide_index=True,height=520)
        q=st.text_input("🔍 深入查詢代號/名稱")
        if q:
            hit=view[view.symbol.astype(str).str.contains(q,case=False,na=False)|view["股票名稱"].str.contains(q,case=False,na=False)]
            st.dataframe(hit,use_container_width=True,hide_index=True)

# -------------------- 4. Theme / Watchlist --------------------
with tab4:
    st.subheader("🎯 題材 → 候選池 → 量化診斷 → 觀察")
    theme=st.text_input("輸入題材，例如：AI 伺服器、矽光子、機器人、低軌衛星")
    if st.button("🤖 建立候選池",type="primary") and theme:
        client=ai_client()
        if not client:st.error("請設定 GEMINI_API_KEY。")
        else:
            prompt=f'請針對「{theme}」列出最多10檔台灣上市櫃代表股票，只回傳JSON陣列，每筆含 symbol,name,market,relevance,business_role。'
            try:
                res=client.models.generate_content(model=st.secrets.get("GEMINI_MODEL","gemini-2.5-flash"),
                    contents=prompt,config={"response_mime_type":"application/json"})
                st.session_state.theme_candidates=json.loads(res.text);st.session_state.theme=theme
            except Exception as e:st.error(f"AI 題材映射失敗：{e}")
    if st.session_state.get("theme_candidates"):
        cand=pd.DataFrame(st.session_state.theme_candidates)
        cand.insert(0,"分析",True)
        edit=st.data_editor(cand,use_container_width=True,hide_index=True,key="theme_editor")
        if st.button("⚡ 執行量化診斷",use_container_width=True):
            results=[]
            for _,s in edit[edit["分析"]==True].iterrows():
                d=history(s.symbol,s.market);f=indicators(d);stg,sub=stage(f,dow(d)) if f else ("打底期 (Basing)","資料不足")
                results.append({"stock":s.to_dict(),"feat":f,"stage":stg,"sub":sub})
            st.session_state.theme_results=results
    for r in st.session_state.get("theme_results",[]):
        s,f=r["stock"],r["feat"]
        if not f:continue
        with st.expander(f"📌 {s.get('name')} ({s.get('symbol')})｜{r['stage']}｜{r['sub']}",True):
            c=st.columns(5)
            for col,label,val in zip(c,["現價","20MA乖離","量能","ATR收縮","60日高點距離"],
                                     [f"${f['cur']:.2f}",f"{f['bias20']:+.1f}%",f"{f['relvol20']:.2f}x",f"{f['atr_ratio']:.2f}",f"{(f['cur']/f['high60']-1)*100:+.1f}%"]):
                col.metric(label,val)
            st.write(STAGES.get(r["stage"],STAGES["打底期 (Basing)"]))
            if st.button("📥 加入觀察",key=f"watch{s.get('symbol')}"):
                c=gs()
                if c:
                    rec={"symbol":clean_sym(s.symbol),"name":clean_name(s.get("name"),s.symbol),"theme":st.session_state.get("theme",""),
                         "created_date":NOW("%Y-%m-%d"),"stage":r["stage"],"prev_stage":"","substate":r["sub"],
                         "base_count":1,"pivot_price":round(f["high60"],2),"strategy_tranches":json.dumps(STAGES[r["stage"]],ensure_ascii=False),
                         "transition_date":NOW("%Y-%m-%d"),"is_active":True}
                    try:
                        oldw=c.read(worksheet="watchlist",ttl=0);oldw=pd.DataFrame(columns=WATCHLIST_COLS) if oldw is None else oldw
                        c.update(worksheet="watchlist",data=pd.concat([oldw,pd.DataFrame([rec])],ignore_index=True));st.success("已加入 Watchlist")
                    except Exception as e:st.error(e)

# -------------------- 5. AI Researcher --------------------
with tab5:
    st.subheader("🤖 AI 研究員")
    st.caption("AI 只讀取目前畫面形成的結構化資料；它是研究與檢查層，不是自動下單層。")
    leaders=sorted(db,key=lambda x:x.get("rs_rating",0),reverse=True)[:15] if db else []
    context={"portfolio":[{"symbol":x["symbol"],"shares":x["shares"],"cost":x["avg_cost"]} for x in portfolio],
             "leaders":[{k:x.get(k) for k in ["symbol","name","rs_rating","rs_ratio","rs_momentum"]} for x in leaders]}
    for m in st.session_state.get("chat",[]):st.chat_message(m["role"]).markdown(m["text"])
    q=st.chat_input("問我：目前持倉有哪些風控事件？哪些股票值得深入研究？")
    if q:
        st.session_state.setdefault("chat",[]).append({"role":"user","text":q});st.chat_message("user").markdown(q)
        client=ai_client()
        if not client:reply="請先設定 GEMINI_API_KEY。"
        else:
            try:
                reply=client.models.generate_content(model=st.secrets.get("GEMINI_MODEL","gemini-2.5-flash"),
                    contents=q,config={"system_instruction":"你是台股量化研究助理。只根據提供資料分析，清楚區分事實、推論與不確定性，不替使用者做最終投資決策。\n資料："+json.dumps(context,ensure_ascii=False)}).text
            except Exception as e:reply=f"AI 呼叫失敗：{e}"
        st.session_state["chat"].append({"role":"assistant","text":reply});st.chat_message("assistant").markdown(reply)

# 持久化當前高點（避免每次重新計算遺失）
save_portfolio(portfolio)
