import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

# [안전 장치]
try:
    from pykrx import stock
    PYKRX_AVAILABLE = True
except:
    PYKRX_AVAILABLE = False

st.set_page_config(page_title="트렌드 마스터 프로", layout="wide")
st.title("🚀 트렌드 마스터: 최종 안정화 버전")

# 1. 데이터 관리 (세션 상태 초기화)
if 'stocks' not in st.session_state:
    st.session_state.stocks = pd.DataFrame(columns=["코드", "수량", "매수단가", "손절가", "메모"])

# 2. 사이드바: 입력
with st.sidebar:
    st.header("➕ 종목 추가")
    def add_ticker():
        code = st.session_state.new_code.strip()
        if code and code not in st.session_state.stocks['코드'].values:
            new_row = pd.DataFrame([{"코드": code, "수량": 1, "매수단가": 0, "손절가": 0, "메모": ""}])
            st.session_state.stocks = pd.concat([st.session_state.stocks, new_row], ignore_index=True)
            st.session_state.new_code = "" 
    st.text_input("종목 번호 입력 후 Enter", key="new_code", on_change=add_ticker)
    
    st.divider()
    if st.button("🗑️ 리스트 비우기"):
        st.session_state.stocks = pd.DataFrame(columns=["코드", "수량", "매수단가", "손절가", "메모"])
        st.rerun()

# 3. 메인 분석 화면
if not st.session_state.stocks.empty:
    with st.spinner("데이터 분석 중..."):
        full_results = []
        analysis_data = {}
        
        for idx, row in st.session_state.stocks.iterrows():
            code = str(row['코드'])
            # [수정] Ticker 객체를 사용해 더 안정적으로 데이터 수집
            tk = code + ".KS" if (code.isdigit() and len(code)==6) else code
            try:
                stock_obj = yf.Ticker(tk)
                df = stock_obj.history(period="6mo")
                
                # 코스피에서 실패하면 코스닥(.KQ)으로 한 번 더 시도
                if df.empty and ".KS" in tk:
                    tk = code + ".KQ"
                    stock_obj = yf.Ticker(tk)
                    df = stock_obj.history(period="6mo")
                
                if df.empty:
                    st.warning(f"⚠️ {code} 종목 데이터를 가져올 수 없습니다. 번호를 확인하세요.")
                    continue

                curr = int(df['Close'].iloc[-1])
                qty, buy_p, stop = int(row['수량']), int(row['매수단가']), int(row['손절가'])
                if stop == 0: stop = int(df['High'].iloc[-21:-1].max() * 0.97)
                
                p_rate = ((curr - buy_p) / buy_p * 100) if buy_p > 0 else 0
                full_results.append({
                    "종목": tk, "수익률": f"{p_rate:.1f}%", "상태": "🚨위험" if curr <= stop else "✅유지",
                    "수량": qty, "매수단가": buy_p, "손절가": stop, "현재가": curr, "메모": row['메모'], "코드": code
                })
                analysis_data[tk] = {"df": df, "stop": stop, "code": code}
            except:
                continue

    if full_results:
        df_main = pd.DataFrame(full_results)
        st.subheader("📝 내 포트폴리오")
        edited_df = st.data_editor(df_main[["종목", "수익률", "상태", "수량", "매수단가", "손절가", "현재가", "메모"]], use_container_width=True, hide_index=True)
        
        if st.button("💾 저장"):
            st.session_state.stocks = edited_df[["코드", "수량", "매수단가", "손절가", "메모"]]
            st.rerun()

        # 차트 분석
        st.divider()
        sel = st.selectbox("🎯 상세 분석 선택", df_main['종목'].tolist())
        if sel in analysis_data:
            target = analysis_data[sel]
            p_df = pd.DataFrame({"주가": target['df']['Close'].values.flatten(), "손절선": target['stop']}, index=target['df'].index)
            st.line_chart(p_df)
else:
    st.info("👈 왼쪽 사이드바에 종목 번호(예: 005930)를 입력하고 Enter를 누르세요.")
