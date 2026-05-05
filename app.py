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
st.title("🚀 트렌드 마스터: 스마트 추천 통합 버전")

# 1. 데이터 관리 (세션 상태)
if 'stocks' not in st.session_state:
    st.session_state.stocks = pd.DataFrame(columns=["코드", "수량", "매수단가", "손절가", "메모"])

# 2. 사이드바: 수동 종목 추가
with st.sidebar:
    st.header("➕ 종목 수동 추가")
    def add_ticker():
        code = st.session_state.new_code.strip()
        if code and code not in st.session_state.stocks['코드'].values:
            new_row = pd.DataFrame([{"코드": code, "수량": 1, "매수단가": 0, "손절가": 0, "메모": ""}])
            st.session_state.stocks = pd.concat([st.session_state.stocks, new_row], ignore_index=True)
            st.session_state.new_code = "" 
    st.text_input("종목 번호(Enter)", key="new_code", on_change=add_ticker)
    
    st.divider()
    if st.button("🗑️ 전체 초기화"):
        st.session_state.stocks = pd.DataFrame(columns=["코드", "수량", "매수단가", "손절가", "메모"])
        st.rerun()

# 3. 메인 분석 화면
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
        st.subheader("📝 내 포트폴리오 관리")
        df_main = pd.DataFrame(full_results)
        edited_df = st.data_editor(df_main[["종목", "수익률", "상태", "수량", "매수단가", "손절가", "현재가", "메모"]], use_container_width=True, hide_index=True)
        if st.button("💾 변경사항 저장"):
            st.session_state.stocks['수량'] = edited_df['수량'].values
            st.session_state.stocks['매수단가'] = edited_df['매수단가'].values
            st.session_state.stocks['손절가'] = edited_df['손절가'].values
            st.session_state.stocks['메모'] = edited_df['메모'].values
            st.rerun()

        # 상세 차트 연동
        st.divider()
        sel = st.selectbox("🎯 분석 종목 선택", df_main['종목'].tolist())
        if sel in analysis_data:
            target = analysis_data[sel]
            t1, t2 = st.tabs(["📉 주가 차트", "👥 외인/기관 수급"])
            with t1:
                p_df = pd.DataFrame({"주가": target['df']['Close'].values.flatten(), "손절선": target['stop']}, index=target['df'].index)
                st.line_chart(p_df)
            with t2:
                if PYKRX_AVAILABLE and str(target['code']).isdigit():
                    try:
                        end_d = datetime.now().strftime("%Y%m%d"); start_d = (datetime.now() - timedelta(days=30)).strftime("%Y%m%d")
                        inv = stock.get_market_net_purchases_of_equities_by_ticker(start_d, end_d, target['code'])
                        inv['외인'] = inv['외국인'].cumsum(); inv['기관'] = inv['기관합계'].cumsum()
                        st.line_chart(inv[['외인', '기관']])
                    except: st.write("수급 데이터를 가져올 수 없습니다.")
                else: st.warning("수급 분석 미지원 환경")

# 4. [NEW] 오늘의 추천주 섹션
st.divider()
st.subheader("🚀 오늘의 추세추종 추천주")
st.write("시장의 주도주 중 강력한 돌파 신호가 있는 종목입니다. 클릭 시 내 목록에 추가됩니다.")

# 추천 종목 리스트 (이름, 코드)
reco_list = [
    {"이름": "SK하이닉스", "코드": "000660"},
    {"이름": "삼양식품", "코드": "003230"},
    {"이름": "HD현대일렉트릭", "코드": "267260"},
    {"이름": "아모레퍼시픽", "코드": "090430"}
]

cols = st.columns(len(reco_list))
for i, item in enumerate(reco_list):
    with cols[i]:
        st.info(f"**{item['이름']}**")
        if st.button(f"➕ {item['이름']} 추가", key=f"btn_{item['코드']}"):
            # 중복 체크 후 추가
            if item['코드'] not in st.session_state.stocks['코드'].values:
                new_data = pd.DataFrame([{"코드": item['코드'], "수량": 1, "매수단가": 0, "손절가": 0, "메모": "추천주 추가"}])
                st.session_state.stocks = pd.concat([st.session_state.stocks, new_data], ignore_index=True)
                st.rerun()
            else:
                st.toast(f"{item['이름']}은 이미 목록에 있습니다.")
