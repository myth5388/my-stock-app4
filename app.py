import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime

# 한글명을 위한 pykrx 체크
try:
    from pykrx import stock
    PYKRX_AVAILABLE = True
except:
    PYKRX_AVAILABLE = False

st.set_page_config(page_title="트렌드 마스터 프로", layout="wide")
st.title("🚀 트렌드 마스터: 최종 안정화 버전")

# 1. 데이터 저장소 초기화
if 'stocks' not in st.session_state:
    st.session_state.stocks = pd.DataFrame(columns=["코드", "수량", "매수단가", "손절가", "메모"])

# [보조 함수] 한글 이름 찾기 (강력하게 보강)
def get_kr_name(code):
    # 1순위: pykrx 사용
    if PYKRX_AVAILABLE:
        try:
            name = stock.get_market_ticker_name(code)
            if name: return name
        except: pass
    
    # 2순위: yfinance info 사용 (백업)
    try:
        tk = code + ".KS" if len(code) == 6 else code
        info = yf.Ticker(tk).info
        name = info.get('shortName') or info.get('longName')
        if name: return name
    except: pass
    
    return code

# 2. 사이드바 구성
with st.sidebar:
    st.header("💾 데이터 관리")
    
    # [수정] 파일 업로드 시 즉시 반영되지 않고 '버튼'을 눌러야만 합쳐지도록 변경 (삭제 버그 해결 핵심)
    uploaded_file = st.file_uploader("백업 파일을 선택하세요", type=["csv"], key="uploader")
    if uploaded_file is not None:
        if st.button("📂 파일 데이터 불러오기/합치기"):
            try:
                try: load_df = pd.read_csv(uploaded_file, encoding='utf-8-sig')
                except: load_df = pd.read_csv(uploaded_file, encoding='cp949')
                
                if '코드' in load_df.columns:
                    load_df['코드'] = load_df['코드'].astype(str).str.zfill(6)
                    # 기존 데이터와 합치기
                    st.session_state.stocks = pd.concat([st.session_state.stocks, load_df], ignore_index=True).drop_duplicates(subset=['코드'], keep='last')
                    st.success("데이터를 불러왔습니다!")
                    st.rerun()
                else: st.error("'코드' 열이 없습니다.")
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

    # 3. [개별 삭제] - 파일 업로드 상태와 상관없이 무조건 작동함
    if not st.session_state.stocks.empty:
        st.divider()
        st.header("🗑️ 종목 삭제")
        current_codes = st.session_state.stocks['코드'].tolist()
        del_target = st.selectbox("삭제할 종목 선택", current_codes, format_func=lambda x: f"{get_kr_name(x)} ({x})")
        
        if st.button("❌ 선택 종목 삭제", type="secondary", use_container_width=True):
            st.session_state.stocks = st.session_state.stocks[st.session_state.stocks['코드'] != del_target].reset_index(drop=True)
            st.success(f"{del_target} 삭제 완료!")
            st.rerun()

    # 전체 비우기 버튼 추가
    if st.button("🚨 전체 리스트 비우기"):
        st.session_state.stocks = pd.DataFrame(columns=["코드", "수량", "매수단가", "손절가", "메모"])
        st.rerun()

# 4. 분석 및 메인 화면 표시
if not st.session_state.stocks.empty:
    full_results = []
    chart_dict = {}
    
    with st.spinner("데이터 동기화 중..."):
        for idx, row in st.session_state.stocks.iterrows():
            code = str(row['코드']).zfill(6)
            name = get_kr_name(code) 
            try:
                # 데이터 수집 최적화
                tk = yf.Ticker(code + ".KS")
                df = tk.history(period="3mo")
                if df.empty:
                    tk = yf.Ticker(code + ".KQ")
                    df = tk.history(period="3mo")
                
                curr, profit, status, stop = 0, 0, "⚠️조회불가", row['손절가']
                
                if not df.empty:
                    last_c = df['Close'].iloc[-1]
                    curr = int(last_c.iloc if hasattr(last_c, 'iloc') else last_c)
                    if stop == 0 or stop > curr * 2: 
                        high_m = df['High'].max()
                        stop = int((high_m.iloc if hasattr(high_m, 'iloc') else high_m) * 0.95)
                    
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
        st.subheader("📋 내 포트폴리오 (수정 후 저장 필수!)")
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
            sel = st.selectbox("🎯 상세 차트 분석", list(chart_dict.keys()))
            target = chart_dict[sel]
            st.line_chart(pd.DataFrame({"주가": target['df']['Close'].values.flatten(), "손절선": target['stop']}, index=target['df'].index))
else:
    st.info("👈 왼쪽 사이드바에서 종목을 추가하거나 파일을 불러오세요.")
