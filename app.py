import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime
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

# --- 사이드바: 백업 및 종목 추가 ---
with st.sidebar:
    st.header("💾 데이터 백업 및 복구")
    if not st.session_state.stocks.empty:
        csv = st.session_state.stocks.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="📥 현재 목록 PC에 저장 (CSV)",
            data=csv,
            file_name=f"my_portfolio_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
        )
    
    uploaded_file = st.file_uploader("📂 저장된 파일 불러오기", type=["csv"])
    if uploaded_file is not None:
        st.session_state.stocks = pd.read_csv(uploaded_file)
        st.success("데이터 복구 완료!")
        st.rerun()

    st.divider()
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
        st.rerun()

# 2. 메인 분석 로직
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
        
        # [수정] key를 추가하여 데이터 편집 상태를 명확히 관리
        edited_df = st.data_editor(
            df_main[["코드", "종목", "수익률", "상태", "수량", "매수단가", "손절가", "현재가", "메모"]], 
            use_container_width=True, hide_index=True, key="portfolio_editor"
        )
        
        # [중요] 저장 버튼 클릭 시 로직 강화
        if st.button("💾 변경사항 저장 및 분석 반영"):
            # 편집된 내용을 원본 데이터 구조에 맞게 추출
            updated_stocks = edited_df[["코드", "수량", "매수단가", "손절가", "메모"]].copy()
            # 세션 상태 업데이트
            st.session_state.stocks = updated_stocks
            st.success("✅ 저장이 완료되었습니다! 화면을 갱신합니다.")
            st.rerun() # 강제로 화면을 새로고침하여 분석 결과 반영

# 3. 추천 종목 (이전과 동일)
st.divider()
# ... (생략된 추천 로직)
