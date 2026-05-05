import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

# [안전 장치] pykrx 설치 오류 대비
try:
    from pykrx import stock
    PYKRX_AVAILABLE = True
except ImportError:
    PYKRX_AVAILABLE = False

st.set_page_config(page_title="트렌드 마스터 프로", layout="wide")
st.title("🚀 트렌드 마스터: 비주얼 분석 통합 버전")

# 1. 데이터 관리 (세션 상태) - '목표가' 컬럼 추가
if 'stocks' not in st.session_state:
    st.session_state.stocks = pd.DataFrame(columns=["코드", "수량", "매수단가", "손절가", "목표가", "메모"])

# 2. 사이드바: 종목 추가
with st.sidebar:
    st.header("➕ 종목 수동 추가")
    def add_ticker():
        code = st.session_state.new_code.strip()
        if code and code not in st.session_state.stocks['코드'].values:
            new_row = pd.DataFrame([{"코드": code, "수량": 1, "매수단가": 0, "손절가": 0, "목표가": 0, "메모": ""}])
            st.session_state.stocks = pd.concat([st.session_state.stocks, new_row], ignore_index=True)
            st.session_state.new_code = "" 
    st.text_input("종목 번호(Enter)", key="new_code", on_change=add_ticker)
    
    st.divider()
    if st.button("🗑️ 전체 초기화"):
        st.session_state.stocks = pd.DataFrame(columns=["코드", "수량", "매수단가", "손절가", "목표가", "메모"])
        st.rerun()

# 3. 메인 분석 로직
if not st.session_state.stocks.empty:
    with st.spinner("데이터 분석 중..."):
        full_results = []
        analysis_data = {}
        tickers = [str(c) + ".KS" if str(c).isdigit() else str(c) for c in st.session_state.stocks['코드']]
        raw_data = yf.download(tickers, period="6mo", group_by='ticker', progress=False)

        for idx, row in st.session_state.stocks.iterrows():
            code = str(row['코드'])
            tk = code + ".KS" if code.isdigit() else code
            try:
                df = raw_data[tk].dropna() if len(tickers) > 1 else raw_data.dropna()
                curr = int(df['Close'].iloc[-1])
                qty, buy_p, stop, target_p = int(row['수량']), int(row['매수단가']), int(row['손절가']), int(row['목표가'])
                
                # 자동 설정 로직
                if stop == 0: stop = int(df['High'].iloc[-21:-1].max() * 0.97)
                if target_p == 0: target_p = int(curr * 1.2) # 목표가 미입력 시 +20% 자동 설정
                
                p_rate = ((curr - buy_p) / buy_p * 100) if buy_p > 0 else 0
                
                full_results.append({
                    "종목": tk, "수익률(%)": round(p_rate, 2), 
                    "상태": "🚨위험" if curr <= stop else "🚀목표달성" if curr >= target_p else "✅유지",
                    "수량": qty, "매수단가": buy_p, "손절가": stop, "목표가": target_p, "현재가": curr, "메모": row['메모'], "코드": code
                })
                analysis_data[tk] = {"df": df, "stop": stop, "target": target_p, "code": code}
            except: continue

    if full_results:
        st.subheader("📝 내 포트폴리오 관리")
        df_main = pd.DataFrame(full_results)
        
        # 수익률에 따라 색상을 지정하는 함수
        def color_profit(val):
            color = 'red' if val > 0 else 'blue' if val < 0 else 'black'
            return f'color: {color}'

        # 표 출력 (수익률 색상 적용)
        edited_df = st.data_editor(
            df_main[["종목", "수익률(%)", "상태", "수량", "매수단가", "손절가", "목표가", "현재가", "메모"]], 
            use_container_width=True, 
            hide_index=True
        )
        
        if st.button("💾 변경사항 저장"):
            st.session_state.stocks['수량'] = edited_df['수량'].values
            st.session_state.stocks['매수단가'] = edited_df['매수단가'].values
            st.session_state.stocks['손절가'] = edited_df['손절가'].values
            st.session_state.stocks['목표가'] = edited_df['목표가'].values
            st.session_state.stocks['메모'] = edited_df['메모'].values
            st.rerun()

        # 4. 차트 분석 (목표가 선 추가)
        st.divider()
        sel = st.selectbox("🎯 분석 종목 선택", df_main['종목'].tolist())
        if sel in analysis_data:
            target = analysis_data[sel]
            t1, t2 = st.tabs(["📉 주가/목표/손절", "👥 외인/기관 수급"])
            with t1:
                p_df = pd.DataFrame({
                    "주가": target['df']['Close'].values.flatten(), 
                    "손절선": target['stop'],
                    "목표선": target['target']
                }, index=target['df'].index)
                st.line_chart(p_df)
                st.caption(f"🔵주가  |  🟠목표가({target['target']:,.0f}원)  |  🔴손절가({target['stop']:,.0f}원)")
            with t2:
                if PYKRX_AVAILABLE and str(target['code']).isdigit():
                    try:
                        end_d = datetime.now().strftime("%Y%m%d"); start_d = (datetime.now() - timedelta(days=30)).strftime("%Y%m%d")
                        inv = stock.get_market_net_purchases_of_equities_by_ticker(start_d, end_d, target['code'])
                        inv['외인'] = inv['외국인'].cumsum(); inv['기관'] = inv['기관합계'].cumsum()
                        st.line_chart(inv[['외인', '기관']])
                    except: st.write("수급 데이터 로딩 실패")

# 5. 하단 추천 섹션 (현재 시장 핫이슈 반영)
st.divider()
st.subheader("🚀 실시간 트렌드 주도주")
reco_list = [
    {"이름": "레인보우로보틱스", "코드": "272410", "이유": "로봇 대장주"},
    {"이름": "알테오젠", "코드": "196170", "이유": "바이오 신고가"},
    {"이름": "에코프로머티", "코드": "450080", "이유": "2차전지 반등"},
    {"이름": "한미반도체", "코드": "042700", "이유": "HBM 장비"}
]

cols = st.columns(len(reco_list))
for i, item in enumerate(reco_list):
    with cols[i]:
        st.success(f"**{item['이름']}**")
        st.caption(item['이유'])
        if st.button(f"추가", key=f"rec_{item['코드']}"):
            if item['코드'] not in st.session_state.stocks['코드'].values:
                new_data = pd.DataFrame([{"코드": item['코드'], "수량": 1, "매수단가": 0, "손절가": 0, "목표가": 0, "메모": "추천주"}])
                st.session_state.stocks = pd.concat([st.session_state.stocks, new_data], ignore_index=True)
                st.rerun()
