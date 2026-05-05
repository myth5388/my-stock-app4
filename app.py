
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
st.title("🚀 트렌드 마스터: 에러 해결 완료")

# 1. 데이터 관리 (세션 상태 초기화)
if 'stocks' not in st.session_state:
    st.session_state.stocks = pd.DataFrame(columns=["코드", "수량", "매수단가", "손절가", "메모"])

# 2. 사이드바: 종목 추가
with st.sidebar:
    st.header("➕ 종목 추가")
    def add_ticker():
        code = st.session_state.new_code.strip()
        if code and code not in st.session_state.stocks['코드'].values:
            new_row = pd.DataFrame([{"코드": code, "수량": 1, "매수단가": 0, "손절가": 0, "메모": ""}])
            st.session_state.stocks = pd.concat([st.session_state.stocks, new_row], ignore_index=True)
            st.session_state.new_code = "" 
    st.text_input("종목 번호(예: 005930) 입력 후 Enter", key="new_code", on_change=add_ticker)
    
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
            tk = code + ".KS" if (code.isdigit() and len(code)==6) else code
            try:
                stock_obj = yf.Ticker(tk)
                df = stock_obj.history(period="6mo")
                if df.empty and ".KS" in tk:
                    tk = code + ".KQ"
                    df = yf.Ticker(tk).history(period="6mo")
                
                if df.empty: continue

                curr = int(df['Close'].iloc[-1])
                qty, buy_p, stop = int(row['수량']), int(row['매수단가']), int(row['손절가'])
                if stop == 0: stop = int(df['High'].iloc[-21:-1].max() * 0.97)
                
                p_rate = ((curr - buy_p) / buy_p * 100) if buy_p > 0 else 0
                full_results.append({
                    "코드": code, "종목": tk, "수익률": f"{p_rate:.1f}%", 
                    "상태": "🚨위험" if curr <= stop else "✅유지",
                    "수량": qty, "매수단가": buy_p, "손절가": stop, "현재가": curr, "메모": row['메모']
                })
                analysis_data[tk] = {"df": df, "stop": stop}
            except: continue

    if full_results:
        df_main = pd.DataFrame(full_results)
        st.subheader("📝 내 포트폴리오")
        
        # [에러 해결 포인트] '코드' 열을 포함해서 그리고, 사용자에게는 안 보이게 설정함
        edited_df = st.data_editor(
            df_main, 
            use_container_width=True, 
            hide_index=True,
            column_config={
                "코드": None, # 화면에서 코드를 숨깁니다 (하지만 데이터에는 남아있음)
                "종목": st.column_config.TextColumn("종목", disabled=True),
                "수익률": st.column_config.TextColumn("수익률", disabled=True),
                "상태": st.column_config.TextColumn("상태", disabled=True),
                "현재가": st.column_config.NumberColumn("현재가", disabled=True),
            }
        )
        
        if st.button("💾 변경사항 저장"):
            # 이제 edited_df에 '코드'가 살아있으므로 에러가 나지 않습니다.
            st.session_state.stocks = edited_df[["코드", "수량", "매수단가", "손절가", "메모"]]
            st.success("성공적으로 저장되었습니다!")
            st.rerun()

        # 차트 분석
        st.divider()
        sel = st.selectbox("🎯 상세 차트 분석", df_main['종목'].tolist())
        if sel in analysis_data:
            target = analysis_data[sel]
            p_df = pd.DataFrame({"주가": target['df']['Close'].values.flatten(), "손절선": target['stop']}, index=target['df'].index)
            st.line_chart(p_df)
else:
    st.info("👈 왼쪽 사이드바에 종목 번호를 입력하세요.")

