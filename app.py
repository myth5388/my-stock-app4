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
st.title("🚀 트렌드 마스터: 최종 안정화 시스템")

# 1. 데이터 저장소 초기화
if 'stocks' not in st.session_state:
    st.session_state.stocks = pd.DataFrame(columns=["코드", "수량", "매수단가", "손절가", "메모"])

# [보조 함수] 한글 이름 찾기 (성능 보강)
def get_kr_name(code):
    if not PYKRX_AVAILABLE: return code
    try:
        name = stock.get_market_ticker_name(code)
        return name if name else code
    except:
        return code

# 2. 사이드바 구성
with st.sidebar:
    st.header("💾 데이터 관리")
    uploaded_file = st.file_uploader("백업 파일을 선택하세요", type=["csv"], key="uploader")
    if uploaded_file is not None:
        try:
            try: load_df = pd.read_csv(uploaded_file, encoding='utf-8-sig')
            except: load_df = pd.read_csv(uploaded_file, encoding='cp949')
            if '코드' in load_df.columns:
                load_df['코드'] = load_df['코드'].astype(str).str.zfill(6)
                st.session_state.stocks = pd.concat([st.session_state.stocks, load_df], ignore_index=True).drop_duplicates(subset=['코드'], keep='last')
                st.success("불러오기 완료!")
        except: st.error("파일 읽기 실패")

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

    # [핵심] 삭제 기능을 독립적인 로직으로 분리하여 우선순위 상향
    if not st.session_state.stocks.empty:
        st.divider()
        st.header("🗑️ 종목 삭제")
        # 현재 리스트의 코드를 한글명과 함께 표시
        current_codes = st.session_state.stocks['코드'].tolist()
        del_target = st.selectbox("삭제할 종목 선택", current_codes, format_func=lambda x: f"{get_kr_name(x)} ({x})")
        
        if st.button("❌ 선택 종목 삭제", type="secondary", use_container_width=True):
            # 세션 상태에서 즉시 제거
            st.session_state.stocks = st.session_state.stocks[st.session_state.stocks['코드'] != del_target].reset_index(drop=True)
            st.success("삭제 완료!")
            st.rerun() # 즉시 화면 갱신

# 3. 분석 및 메인 화면 표시
if not st.session_state.stocks.empty:
    full_results = []
    chart_dict = {}
    
    with st.spinner("데이터 분석 중..."):
        for idx, row in st.session_state.stocks.iterrows():
            code = str(row['코드']).zfill(6)
            name = get_kr_name(code) # 한글명 가져오기
            try:
                tk = yf.Ticker(code + ".KS")
                df = tk.history(period="3mo")
                if df.empty:
                    tk = yf.Ticker(code + ".KQ")
                    df = tk.history(period="3mo")
                
                curr, profit, status = 0, 0, "⚠️조회불가"
                stop = row['손절가']
                
                if not df.empty:
                    last_c = df['Close'].iloc[-1]
                    curr = int(last_c.iloc if hasattr(last_c, 'iloc') else last_c)
                    if stop == 0 or stop > curr * 2: 
                        high_m = df['High'].max()
                        stop = int((high_m.iloc if hasattr(high_m, 'iloc') else high_m) * 0.95)
                    profit = ((curr - int(row['매수단가'])) / int(row['매수단가']) * 100) if int(row['매수단가']) > 0 else 0
                    status = "🚨위험" if curr <= stop else "✅유지"
                    chart_dict[name] = {"df": df, "stop": stop}
                
                full_results.append({
                    "종목명": name, "수익률": f"{profit:.1f}%", "상태": status,
                    "수량": row['수량'], "매수단가": row['매수단가'], "손절가": stop,
                    "현재가": curr, "메모": row['메모'], "코드": code
                })
            except: continue

    if full_results:
        st.subheader("📋 내 포트폴리오 (수정 후 저장 필수!)")
        df_display = pd.DataFrame(full_results)
        
        # 편집 표
        edited_df = st.data_editor(
            df_display[["종목명", "수익률", "상태", "수량", "매수단가", "손절가", "현재가", "메모"]],
            use_container_width=True, hide_index=True, key="main_editor",
            disabled=["종목명", "수익률", "상태", "현재가"]
        )
        
        c1, c2 = st.columns(2)
        with c1:
            if st.button("💾 변경사항 저장", type="primary", use_container_width=True):
                # 편집된 데이터와 원본 코드 합체
                new_data = edited_df.copy()
                new_data['코드'] = df_display['코드'].values
                st.session_state.stocks = new_data[["코드", "수량", "매수단가", "손절가", "메모"]]
                st.success("저장되었습니다!")
                st.rerun()
        with c2:
            csv = st.session_state.stocks.to_csv(index=False).encode('utf-8-sig')
            st.download_button("📥 백업(CSV) 다운로드", data=csv, file_name="my_stocks.csv", use_container_width=True)

        # 4. 차트 분석
        if chart_dict:
            st.divider()
            sel = st.selectbox("🎯 차트 분석 종목", list(chart_dict.keys()))
            target = chart_dict[sel]
            st.line_chart(pd.DataFrame({"주가": target['df']['Close'].values.flatten(), "손절선": target['stop']}, index=target['df'].index))
else:
    st.info("👈 왼쪽에서 종목을 추가하거나 파일을 불러오세요.")
