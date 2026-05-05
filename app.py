import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import io

# [안전 장치]
try:
    from pykrx import stock
    PYKRX_AVAILABLE = True
except ImportError:
    PYKRX_AVAILABLE = False

st.set_page_config(page_title="트렌드 마스터 프로", layout="wide")
st.title("🛡️ 트렌드 마스터: 통합 관리 & 데이터 보존")

# 1. 데이터 관리 (세션 상태 초기화)
if 'stocks' not in st.session_state:
    st.session_state.stocks = pd.DataFrame(columns=["코드", "수량", "매수단가", "손절가", "메모"])
if 'reco_list' not in st.session_state:
    st.session_state.reco_list = []

# --- [새 기능] 데이터 백업 및 복구 로직 ---
with st.sidebar:
    st.header("💾 데이터 백업 및 복구")
    
    # 1. 파일로 내보내기 (Download)
    if not st.session_state.stocks.empty:
        csv = st.session_state.stocks.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="📥 현재 목록 PC에 저장 (CSV)",
            data=csv,
            file_name=f"my_portfolio_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
        )
    
    # 2. 파일에서 불러오기 (Upload)
    uploaded_file = st.file_uploader("📂 저장된 파일 불러오기", type=["csv"])
    if uploaded_file is not None:
        load_df = pd.read_csv(uploaded_file)
        # 컬럼명 일치 확인 후 불러오기
        st.session_state.stocks = load_df
        st.success("데이터를 성공적으로 불러왔습니다!")
        st.rerun()

    st.divider()

# 2. 사이드바: 종목 수동 추가
with st.sidebar:
    st.header("➕ 종목 수동 추가")
    def add_ticker():
        code = str(st.session_state.new_code_input).strip()
        if code and code not in st.session_state.stocks['코드'].astype(str).values:
            new_row = pd.DataFrame([{"코드": code, "수량": 1, "매수단가": 0, "손절가": 0, "메모": ""}])
            st.session_state.stocks = pd.concat([st.session_state.stocks, new_row], ignore_index=True)
            st.session_state.new_code_input = "" 
    st.text_input("종목 번호(Enter)", key="new_code_input", on_change=add_ticker)
    
    if st.button("🗑️ 리스트 전체 비우기"):
        st.session_state.stocks = pd.DataFrame(columns=["코드", "수량", "매수단가", "손절가", "메모"])
        st.session_state.reco_list = []
        st.rerun()

# --- 이하 기존 분석 및 추천 로직 (동일) ---
def fetch_recommendations():
    targets = ["005930", "000660", "003230", "267260", "196170", "000270", "035420", "068270"]
    tickers = [t + ".KS" for t in targets]
    data = yf.download(tickers, period="3mo", group_by='ticker', progress=False)
    results = []
    for t in targets:
        tk = t + ".KS"
        try:
            df = data[tk].dropna()
            curr = float(df['Close'].iloc[-1])
            h20 = float(df['High'].iloc[-21:-1].max())
            if curr >= h20:
                name = yf.Ticker(tk).info.get('shortName', t)
                results.append({"이름": name, "코드": t, "현재가": int(curr), "전고점": int(h20)})
        except: continue
    return results

if not st.session_state.stocks.empty:
    with st.spinner("데이터 분석 중..."):
        full_results = []
        ticker_list = [str(c) + ".KS" if str(c).isdigit() else str(c) for c in st.session_state.stocks['코드']]
        raw_data = yf.download(ticker_list, period="6mo", group_by='ticker', progress=False)

        for idx, row in st.session_state.stocks.iterrows():
            code = str(row['코드'])
            tk = code + ".KS" if code.isdigit() else code
            try:
                df = raw_data[tk].dropna() if len(ticker_list) > 1 else raw_data.dropna()
                curr = int(df['Close'].iloc[-1])
                qty, buy_p, stop = int(row['수량']), int(row['매수단가']), int(row['손절가'])
                if stop == 0: stop = int(df['High'].iloc[-21:-1].max() * 0.97)
                p_rate = ((curr - buy_p) / buy_p * 100) if buy_p > 0 else 0
                full_results.append({
                    "코드": code, "종목": tk, "수익률": f"{p_rate:.1f}%", "상태": "🚨위험" if curr <= stop else "✅유지",
                    "수량": qty, "매수단가": buy_p, "손절가": stop, "현재가": curr, "메모": row['메모']
                })
            except: continue

    if full_results:
        st.subheader("📝 내 포트폴리오 현황")
        df_main = pd.DataFrame(full_results)
        edited_df = st.data_editor(
            df_main[["코드", "종목", "수익률", "상태", "수량", "매수단가", "손절가", "현재가", "메모"]], 
            use_container_width=True, hide_index=True,
            disabled=["종목", "수익률", "상태", "현재가"]
        )
        if st.button("💾 변경사항 저장"):
            st.session_state.stocks = edited_df[["코드", "수량", "매수단가", "손절가", "메모"]]
            st.success("데이터가 안전하게 저장되었습니다!")
            st.rerun()

st.divider()
st.subheader("🚀 오늘의 추천주")
if st.button("🔍 추천 종목 스캔"):
    st.session_state.reco_list = fetch_recommendations()

if st.session_state.reco_list:
    cols = st.columns(len(st.session_state.reco_list))
    for i, item in enumerate(st.session_state.reco_list):
        with cols[i]:
            st.info(f"**{item['이름']}**")
            if st.button(f"추가", key=f"rec_{item['코드']}"):
                existing_codes = st.session_state.stocks['코드'].astype(str).values
                if str(item['코드']) not in existing_codes:
                    new_entry = pd.DataFrame([{"코드": str(item['코드']), "수량": 1, "매수단가": item['현재가'], "손절가": item['전고점'], "메모": "추천주 추가"}])
                    st.session_state.stocks = pd.concat([st.session_state.stocks, new_entry], ignore_index=True)
                    st.rerun()
