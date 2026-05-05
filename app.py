import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

# [안전 장치] 수급 데이터 부품 체크
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
    st.text_input("종목 번호(Enter)", key="new_code", on_change=add_ticker)
    
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
            tk = code + ".KS" if code.isdigit() else code
            try:
                # [안전 장치] 데이터를 가져올 때 에러가 나면 해당 종목은 건너뜀
                df = yf.download(tk, period="6mo", progress=False)
                if df.empty and code.isdigit():
                    tk = code + ".KQ"
                    df = yf.download(tk, period="6mo", progress=False)
                
                if df.empty:
                    st.warning(f"⚠️ {code} 종목 데이터를 찾을 수 없어 제외합니다.")
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
            except Exception as e:
                continue

    if full_results:
        df_main = pd.DataFrame(full_results)
        st.subheader("📝 내 포트폴리오")
        edited_df = st.data_editor(df_main[["종목", "수익률", "상태", "수량", "매수단가", "손절가", "현재가", "메모"]], use_container_width=True, hide_index=True)
        
        if st.button("💾 저장"):
            # 화면에 남은 종목들만 저장 (잘못된 종목은 자동 제거됨)
            st.session_state.stocks = edited_df[["코드", "수량", "매수단가", "손절가", "메모"]]
            st.rerun()

        # 4. 차트 및 수급 분석 (선택 박스)
        st.divider()
        sel = st.selectbox("🎯 분석 종목", df_main['종목'].tolist())
        if sel in analysis_data:
            target = analysis_data[sel]
            t1, t2 = st.tabs(["📉 차트", "👥 수급"])
            with t1:
                p_df = pd.DataFrame({"주가": target['df']['Close'].values.flatten(), "손절선": target['stop']}, index=target['df'].index)
                st.line_chart(p_df)
            with t2:
                if PYKRX_AVAILABLE and str(target['code']).isdigit():
                    try:
                        end_d = datetime.now().strftime("%Y%m%d"); start_d = (datetime.now() - timedelta(days=30)).strftime("%Y%m%d")
                        inv = stock.get_market_net_purchases_of_equities_by_ticker(start_d, end_d, target['code'])
                        st.line_chart(inv[['외국인', '기관합계']].cumsum())
                    except: st.write("수급 데이터 대기 중...")
else:
    st.info("👈 왼쪽에서 올바른 종목 번호를 입력하세요.")
