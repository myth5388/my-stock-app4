import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# [부품 체크] pykrx가 없어도 앱이 멈추지 않게 방어
try:
    from pykrx import stock
    PYKRX_AVAILABLE = True
except:
    PYKRX_AVAILABLE = False

st.set_page_config(page_title="트렌드 마스터", layout="wide")
st.title("🛡️ 트렌드 마스터: 에러 해결 최종판")

# 1. 데이터 관리
if 'my_portfolio' not in st.session_state:
    st.session_state.my_portfolio = []

# 2. 사이드바: 종목 추가
with st.sidebar:
    st.header("➕ 종목 추가")
    new_code = st.text_input("종목 번호(6자리)", key="add_input")
    if st.button("포트폴리오 추가") and new_code:
        if not any(s['코드'] == new_code for s in st.session_state.my_portfolio):
            st.session_state.my_portfolio.append({
                "코드": new_code, "수량": 1, "매수단가": 0, "손절가": 0, "메모": ""
            })
            st.rerun()
    
    if st.button("🗑️ 전체 초기화"):
        st.session_state.my_portfolio = []
        st.rerun()

# 3. 데이터 분석 및 화면 표시
if st.session_state.my_portfolio:
    full_results = []
    analysis_data = {}

    with st.spinner("데이터 동기화 중..."):
        for item in st.session_state.my_portfolio:
            code = item['코드']
            tk = code + ".KS" if code.isdigit() else code
            df = yf.download(tk, period="6mo", progress=False)
            
            if df.empty and code.isdigit():
                tk = code + ".KQ"
                df = yf.download(tk, period="6mo", progress=False)

            if not df.empty:
                try:
                    # [에러 해결 핵심] 데이터가 표 형태(Series)여도 첫 번째 값을 확실히 추출
                    last_price_val = df['Close'].iloc[-1]
                    if isinstance(last_price_val, (pd.Series, np.ndarray)):
                        last_price_val = last_price_val[0]
                    
                    curr = int(float(last_price_val))
                    
                    # 20일 고점 계산 (손절가 자동 제안용)
                    high_20 = df['High'].iloc[-21:-1].max()
                    if isinstance(high_20, (pd.Series, np.ndarray)):
                        high_20 = high_20[0]
                        
                    qty = item['수량']
                    buy_p = item['매수단가']
                    stop = item['손절가'] if item['손절가'] > 0 else int(float(high_20) * 0.95)
                    
                    profit = ((curr - buy_p) / buy_p * 100) if buy_p > 0 else 0
                    
                    full_results.append({
                        "코드": code, "종목": tk, "현재가": curr, "수익률(%)": f"{profit:.2f}%",
                        "수량": qty, "매수단가": buy_p, "손절가": stop, "메모": item['메모']
                    })
                    analysis_data[tk] = {"df": df, "stop": stop, "code": code}
                except Exception as e:
                    continue

    if full_results:
        st.subheader("📝 내 포트폴리오 현황")
        df_display = pd.DataFrame(full_results)
        edited_df = st.data_editor(df_display, use_container_width=True, hide_index=True)

        if st.button("💾 변경사항 저장"):
            new_portfolio = []
            for _, row in edited_df.iterrows():
                new_portfolio.append({
                    "코드": str(row['코드']), 
                    "수량": int(row['수량']), 
                    "매수단가": int(row['매수단가']), 
                    "손절가": int(row['손절가']), 
                    "메모": str(row['메모'])
                })
            st.session_state.my_portfolio = new_portfolio
            st.success("저장되었습니다!")
            st.rerun()

        # 4. 차트 분석
        st.divider()
        sel = st.selectbox("🎯 상세 분석 종목", df_display['종목'].tolist())
        if sel in analysis_data:
            target = analysis_data[sel]
            t1, t2 = st.tabs(["📉 주가 차트", "👥 수급 분석"])
            with t1:
                chart_df = pd.DataFrame(index=target['df'].index)
                # 데이터 1차원 변환으로 에러 방지
                chart_df['주가'] = target['df']['Close'].values.flatten()
                chart_df['손절선'] = target['stop']
                st.line_chart(chart_df)
            with t2:
                if PYKRX_AVAILABLE and str(target['code']).isdigit():
                    try:
                        end = datetime.now().strftime("%Y%m%d"); start = (datetime.now() - timedelta(days=30)).strftime("%Y%m%d")
                        inv = stock.get_market_net_purchases_of_equities_by_ticker(start, end, target['code'])
                        st.line_chart(inv[['외국인', '기관합계']].cumsum())
                    except: st.write("수급 데이터 로딩 중...")
else:
    st.info("👈 왼쪽에서 종목 번호를 입력하고 추가 버튼을 누르세요.")
