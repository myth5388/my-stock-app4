import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime

# 한글명 라이브러리 체크
try:
    from pykrx import stock
    PYKRX_AVAILABLE = True
except:
    PYKRX_AVAILABLE = False

st.set_page_config(page_title="트렌드 마스터 프로", layout="wide")
st.title("🛡️ 트렌드 마스터: 지능형 거래량 지지선 시스템")

# 1. 데이터 저장소 초기화
if 'stocks' not in st.session_state:
    st.session_state.stocks = pd.DataFrame(columns=["코드", "수량", "매수단가", "손절가", "메모"])

# [보조 함수] 한글 이름 찾기
def get_kr_name(code):
    if PYKRX_AVAILABLE:
        try:
            name = stock.get_market_ticker_name(code)
            if name: return name
        except: pass
    return code

# [보조 함수] 의미 있는 거래량 지지선 계산 (핵심 로직)
def get_smart_support(df):
    try:
        if len(df) < 10: return int(df['Low'].min())
        # 평균 거래량의 150% 이상 터진 날 필터링
        avg_vol = df['Volume'].mean()
        high_vol_days = df[df['Volume'] > avg_vol * 1.5]
        
        if not high_vol_days.empty:
            # 거래량이 터졌던 날들의 최저가 중 현재가와 가장 가까운 하단 지점
            curr_price = df['Close'].iloc[-1]
            supports = high_vol_days[high_vol_days['Low'] < curr_price]['Low']
            if not supports.empty:
                return int(supports.max()) # 의미 있는 거래량 저점 중 가장 높은 곳
        return int(df['Low'].min()) # 데이터가 부족하면 기간 최저가
    except:
        return 0

# 2. 사이드바 구성
with st.sidebar:
    st.header("💾 데이터 관리")
    uploaded_file = st.file_uploader("백업 파일을 선택하세요", type=["csv"], key="uploader")
    if uploaded_file is not None:
        if st.button("📂 파일 데이터 불러오기"):
            try:
                load_df = pd.read_csv(uploaded_file)
                if '코드' in load_df.columns:
                    load_df['코드'] = load_df['코드'].astype(str).str.zfill(6)
                    st.session_state.stocks = pd.concat([st.session_state.stocks, load_df], ignore_index=True).drop_duplicates(subset=['코드'], keep='last')
                    st.success("데이터 로드 완료!")
                    st.rerun()
            except: st.error("파일 로드 실패")

    st.divider()
    st.header("➕ 종목 추가")
    new_code = st.text_input("종목 번호 (6자리)", key="manual_in")
    if st.button("📌 리스트에 추가"):
        if new_code:
            code = new_code.strip().zfill(6) if new_code.strip().isdigit() else new_code.strip()
            if code not in st.session_state.stocks['코드'].astype(str).values:
                new_row = pd.DataFrame([{"코드": code, "수량": 1, "매수단가": 0, "손절가": 0, "메모": ""}])
                st.session_state.stocks = pd.concat([st.session_state.stocks, new_row], ignore_index=True)
                st.rerun()

    if not st.session_state.stocks.empty:
        st.divider()
        st.header("🗑️ 종목 삭제")
        current_codes = st.session_state.stocks['코드'].tolist()
        del_target = st.selectbox("삭제할 종목 선택", current_codes, format_func=lambda x: f"{get_kr_name(x)} ({x})")
        if st.button("❌ 선택 종목 삭제", use_container_width=True):
            st.session_state.stocks = st.session_state.stocks[st.session_state.stocks['코드'] != del_target].reset_index(drop=True)
            st.rerun()

# 3. 분석 및 화면 표시
if not st.session_state.stocks.empty:
    full_results = []
    chart_dict = {}
    
    with st.spinner("지능형 지지선을 분석 중입니다..."):
        for idx, row in st.session_state.stocks.iterrows():
            code = str(row['코드']).zfill(6)
            name = get_kr_name(code) 
            try:
                tk = yf.Ticker(code + ".KS")
                df = tk.history(period="6mo")
                if df.empty:
                    tk = yf.Ticker(code + ".KQ")
                    df = tk.history(period="3mo")
                
                curr, profit, status, stop = 0, 0, "⚠️조회불가", row['손절가']
                
                if not df.empty:
                    last_c = df['Close'].iloc[-1]
                    curr = int(last_c.iloc if hasattr(last_c, 'iloc') else last_c)
                    
                    # [지능형 로직] 손절가가 0이거나 자동 갱신 필요 시 거래량 기반 전저점으로 설정
                    smart_support = get_smart_support(df)
                    if stop == 0: 
                        stop = smart_support
                    
                    buy_price = int(row['매수단가'])
                    profit = ((curr - buy_price) / buy_price * 100) if buy_price > 0 else 0
                    status = "🚨위험" if curr <= stop else "✅유지"
                    chart_dict[name] = {"df": df, "stop": stop}
                
                full_results.append({
                    "종목명": name, "수익률": f"{profit:.1f}%", "상태": status,
                    "수량": row['수량'], "매수단가": row['매수단가'], "손절가": stop,
                    "현재가": curr, "메모": row['메모'], "코드": code
                })
            except: continue

    if full_results:
        st.subheader("📋 내 포트폴리오 (거래량 기반 지지선 반영)")
        df_display = pd.DataFrame(full_results)
        edited_df = st.data_editor(
            df_display[["종목명", "수익률", "상태", "수량", "매수단가", "손절가", "현재가", "메모"]],
            use_container_width=True, hide_index=True, key="main_editor",
            disabled=["종목명", "수익률", "상태", "현재가"]
        )
        
        c1, c2 = st.columns(2)
        with c1:
            if st.button("💾 변경사항 저장", type="primary", use_container_width=True):
                new_data = edited_df.copy()
                new_data['코드'] = df_display['코드'].values
                st.session_state.stocks = new_data[["코드", "수량", "매수단가", "손절가", "메모"]]
                st.success("저장 완료!")
                st.rerun()
        with c2:
            csv = st.session_state.stocks.to_csv(index=False).encode('utf-8-sig')
            st.download_button("📥 백업(CSV) 다운로드", data=csv, file_name="my_stocks.csv", use_container_width=True)

        if chart_dict:
            st.divider()
            sel = st.selectbox("🎯 상세 차트 분석 (주황색: 거래량 지지선)", list(chart_dict.keys()))
            target = chart_dict[sel]
            # 차트 데이터 준비 (에러 방지 flatten)
            plot_df = pd.DataFrame(index=target['df'].index)
            plot_df['주가'] = target['df']['Close'].values.flatten()
            plot_df['거래량지지선'] = target['stop']
            st.line_chart(plot_df)
else:
    st.info("👈 왼쪽 사이드바에서 종목을 추가하세요.")
