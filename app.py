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
st.title("🛡️ 트렌드 마스터: 통합 관리 & 추천 시스템")

# 1. 데이터 관리 (세션 상태)
if 'stocks' not in st.session_state:
    st.session_state.stocks = pd.DataFrame(columns=["코드", "수량", "매수단가", "손절가", "메모"])

# 2. 사이드바: 종목 수동 추가
with st.sidebar:
    st.header("➕ 종목 수동 추가")
    def add_ticker():
        code = st.session_state.new_code_input.strip()
        if code and code not in st.session_state.stocks['코드'].values:
            new_row = pd.DataFrame([{"코드": code, "수량": 1, "매수단가": 0, "손절가": 0, "메모": ""}])
            st.session_state.stocks = pd.concat([st.session_state.stocks, new_row], ignore_index=True)
            st.session_state.new_code_input = "" 
    st.text_input("종목 번호(Enter)", key="new_code_input", on_change=add_ticker)
    
    st.divider()
    if st.button("🗑️ 전체 초기화"):
        st.session_state.stocks = pd.DataFrame(columns=["코드", "수량", "매수단가", "손절가", "메모"])
        st.rerun()

# 3. 추천 종목 분석 함수 (캐싱으로 속도 향상)
@st.cache_data(ttl=3600)
def get_daily_recos():
    # 시장 주도주 10종목 후보군 (반도체, 전력, 식품, 바이오 등)
    targets = ["005930", "000660", "003230", "267260", "196170", "000270", "035420", "068270", "005380", "122630"]
    tickers = [t + ".KS" for t in targets]
    data = yf.download(tickers, period="3mo", group_by='ticker', progress=False)
    
    recos = []
    for t in targets:
        tk = t + ".KS"
        try:
            df = data[tk].dropna()
            curr = float(df['Close'].iloc[-1])
            h20 = float(df['High'].iloc[-21:-1].max())
            v_avg = float(df['Volume'].iloc[-21:-1].mean())
            v_curr = float(df['Volume'].iloc[-1])
            
            # 조건: 20일 신고가 돌파 & 거래량 1.3배 이상
            if curr >= h20 and v_curr > v_avg * 1.3:
                name = yf.Ticker(tk).info.get('shortName', t)
                recos.append({"이름": name, "코드": t, "현재가": int(curr), "전고점": int(h20)})
        except: continue
    return recos

# 4. 메인 분석 화면
if not st.session_state.stocks.empty:
    with st.spinner("내 포트폴리오 분석 중..."):
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
        st.subheader("📝 내 포트폴리오 현황")
        df_main = pd.DataFrame(full_results)
        edited_df = st.data_editor(df_main[["종목", "수익률", "상태", "수량", "매수단가", "손절가", "현재가", "메모"]], use_container_width=True, hide_index=True)
        if st.button("💾 모든 변경사항 저장"):
            st.session_state.stocks['수량'] = edited_df['수량'].values
            st.session_state.stocks['매수단가'] = edited_df['매수단가'].values
            st.session_state.stocks['손절가'] = edited_df['손절가'].values
            st.session_state.stocks['메모'] = edited_df['메모'].values
            st.rerun()

        # 차트 분석
        st.divider()
        sel = st.selectbox("🎯 상세 분석 선택", df_main['종목'].tolist())
        if sel in analysis_data:
            target = analysis_data[sel]
            tab1, tab2 = st.tabs(["📉 주가 차트", "👥 수급 데이터"])
            with tab1:
                p_df = pd.DataFrame({"주가": target['df']['Close'].values.flatten(), "손절선": target['stop']}, index=target['df'].index)
                st.line_chart(p_df)
            with tab2:
                if PYKRX_AVAILABLE and str(target['code']).isdigit():
                    try:
                        end = datetime.now().strftime("%Y%m%d"); start = (datetime.now() - timedelta(days=30)).strftime("%Y%m%d")
                        inv = stock.get_market_net_purchases_of_equities_by_ticker(start, end, target['code'])
                        st.line_chart(inv[['외국인', '기관합계']].cumsum())
                    except: st.write("수급 데이터 대기 중...")
                else: st.warning("수급 분석 미지원 (Python 버전)")

# 5. [NEW] 오늘의 추천주 섹션
st.divider()
st.subheader("🚀 오늘의 추세추종 추천주 (신고가 돌파)")
st.write("시장의 주도주 중 강력한 **돌파 신호**가 포착된 종목입니다.")

if st.button("🔍 추천 종목 스캔 시작"):
    with st.spinner("시장 주도주 데이터를 분석 중입니다..."):
        recos = get_daily_recos()
        if recos:
            cols = st.columns(len(recos))
            for i, item in enumerate(recos):
                with cols[i]:
                    st.success(f"**{item['이름']}**")
                    st.write(f"추천가: {item['현재가']:,.0f}원")
                    if st.button(f"포트폴리오 추가", key=f"rec_{item['코드']}"):
                        if item['코드'] not in st.session_state.stocks['코드'].values:
                            new_data = pd.DataFrame([{"코드": item['코드'], "수량": 1, "매수단가": item['현재가'], "손절가": item['전고점'], "메모": "추천주 자동추가"}])
                            st.session_state.stocks = pd.concat([st.session_state.stocks, new_data], ignore_index=True)
                            st.rerun()
                        else:
                            st.toast(f"{item['이름']}은(는) 이미 리스트에 있습니다!")
        else:
            st.info("현재 돌파 조건을 만족하는 강력한 주도주가 없습니다. 관망을 추천합니다.")
else:
    st.write("버튼을 누르면 현재 시장에서 가장 힘이 좋은 종목을 분석합니다.")
