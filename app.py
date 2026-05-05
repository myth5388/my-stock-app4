import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

# [안전 장치] pykrx 라이브러리 체크
try:
    from pykrx import stock
    PYKRX_AVAILABLE = True
except ImportError:
    PYKRX_AVAILABLE = False

st.set_page_config(page_title="트렌드 마스터 프로", layout="wide")
st.title("🛡️ 트렌드 마스터: 통합 관리 & 추천 시스템")

# 1. 데이터 관리 (세션 상태 초기화)
if 'stocks' not in st.session_state:
    st.session_state.stocks = pd.DataFrame(columns=["코드", "수량", "매수단가", "손절가", "메모"])
if 'reco_list' not in st.session_state:
    st.session_state.reco_list = [] # 추천 목록 저장용

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
    
    st.divider()
    if st.button("🗑️ 전체 초기화"):
        st.session_state.stocks = pd.DataFrame(columns=["코드", "수량", "매수단가", "손절가", "메모"])
        st.session_state.reco_list = []
        st.rerun()

# 3. 추천 종목 분석 함수
def fetch_recommendations():
    targets = ["005930", "000660", "003230", "267260", "196170", "000270", "035420", "068270", "105560", "005380"]
    tickers = [t + ".KS" for t in targets]
    data = yf.download(tickers, period="3mo", group_by='ticker', progress=False)
    
    results = []
    for t in targets:
        tk = t + ".KS"
        try:
            df = data[tk].dropna()
            curr = float(df['Close'].iloc[-1])
            h20 = float(df['High'].iloc[-21:-1].max())
            if curr >= h20: # 20일 신고가 돌파
                name = yf.Ticker(tk).info.get('shortName', t)
                results.append({"이름": name, "코드": t, "현재가": int(curr), "전고점": int(h20)})
        except: continue
    return results

# 4. 메인 분석 화면 (상단)
if not st.session_state.stocks.empty:
    with st.spinner("내 포트폴리오 분석 중..."):
        full_results = []
        analysis_data = {}
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
                    "종목": tk, "수익률": f"{p_rate:.1f}%", "상태": "🚨위험" if curr <= stop else "✅유지",
                    "수량": qty, "매수단가": buy_p, "손절가": stop, "현재가": curr, "메모": row['메모'], "코드": code
                })
                analysis_data[tk] = {"df": df, "stop": stop, "code": code}
            except: continue

    if full_results:
        st.subheader("📝 내 포트폴리오 현황")
        df_main = pd.DataFrame(full_results)
        edited_df = st.data_editor(df_main[["종목", "수익률", "상태", "수량", "매수단가", "손절가", "현재가", "메모"]], use_container_width=True, hide_index=True)
        
        if st.button("💾 변경사항 저장"):
            st.session_state.stocks['수량'] = edited_df['수량'].values
            st.session_state.stocks['매수단가'] = edited_df['매수단가'].values
            st.session_state.stocks['손절가'] = edited_df['손절가'].values
            st.session_state.stocks['메모'] = edited_df['메모'].values
            st.rerun()

# 5. 오늘의 추천주 섹션 (하단 - 로직 개선)
st.divider()
st.subheader("🚀 오늘의 추천주 (신고가 돌파)")

# 스캔 시작 버튼
if st.button("🔍 추천 종목 스캔 시작"):
    with st.spinner("시장 분석 중..."):
        st.session_state.reco_list = fetch_recommendations()

# 저장된 추천 목록이 있으면 화면에 표시
if st.session_state.reco_list:
    cols = st.columns(len(st.session_state.reco_list))
    for i, item in enumerate(st.session_state.reco_list):
        with cols[i]:
            st.info(f"**{item['이름']}**")
            st.write(f"{item['현재가']:,.0f}원")
            
            # [핵심] 추가 버튼 클릭 시 세션 상태에 즉시 반영
            if st.button(f"추가", key=f"rec_btn_{item['코드']}"):
                existing_codes = st.session_state.stocks['코드'].astype(str).values
                if str(item['코드']) not in existing_codes:
                    new_entry = pd.DataFrame([{
                        "코드": str(item['코드']), "수량": 1, 
                        "매수단가": item['현재가'], "손절가": item['전고점'], "메모": "추천주 추가"
                    }])
                    st.session_state.stocks = pd.concat([st.session_state.stocks, new_entry], ignore_index=True)
                    st.rerun() # 추가 후 즉시 새로고침하여 상단 표에 표시
                else:
                    st.warning("이미 목록에 있습니다.")
else:
    st.write("버튼을 누르면 현재 시장에서 가장 힘이 좋은 종목을 분석합니다.")
