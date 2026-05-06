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
st.title("🚀 트렌드 마스터: 한글 종목 분석 시스템")

# 1. 데이터 저장소 초기화
if 'stocks' not in st.session_state:
    st.session_state.stocks = pd.DataFrame(columns=["코드", "수량", "매수단가", "손절가", "메모"])

# [보조 함수] 한글 이름 찾기 (더 튼튼하게 보강)
def get_kr_name(code):
    if not PYKRX_AVAILABLE: return code
    try:
        name = stock.get_market_ticker_name(code)
        return name if name else code
    except:
        return code

# 2. 사이드바 구성
with st.sidebar:
    st.header("💾 데이터 복구 (CSV)")
    uploaded_file = st.file_uploader("백업 파일을 선택하세요", type=["csv"])
    if uploaded_file is not None:
        if st.button("📂 데이터 합치기"):
            try:
                load_df = pd.read_csv(uploaded_file)
                if '코드' in load_df.columns:
                    load_df['코드'] = load_df['코드'].astype(str).str.zfill(6)
                    combined = pd.concat([st.session_state.stocks, load_df], ignore_index=True)
                    st.session_state.stocks = combined.drop_duplicates(subset=['코드'], keep='last')
                    st.success("불러오기 성공!")
                    st.rerun()
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
            else:
                st.warning("이미 목록에 있는 종목입니다.")

    if st.button("🗑️ 전체 비우기"):
        st.session_state.stocks = pd.DataFrame(columns=["코드", "수량", "매수단가", "손절가", "메모"])
        st.rerun()

# 3. 분석 및 화면 표시
if not st.session_state.stocks.empty:
    full_results = []
    chart_data_dict = {}
    
    with st.spinner("데이터 분석 중..."):
        # 모든 종목을 한꺼번에 분석 시도
        for idx, row in st.session_state.stocks.iterrows():
            code = str(row['코드']).zfill(6)
            tk = code + ".KS"
            kn = get_kr_name(code)
            
            try:
                # 데이터를 못 가져오더라도 줄은 생기게 기본값 설정
                curr, profit, status = 0, 0, "⚠️조회불가"
                df = yf.download(tk, period="3mo", progress=False)
                if df.empty:
                    tk = code + ".KQ"
                    df = yf.download(tk, period="3mo", progress=False)
                
                if not df.empty:
                    curr = int(df['Close'].iloc[-1])
                    qty, buy, stop = int(row['수량']), int(row['매수단가']), int(row['손절가'])
                    if stop == 0: stop = int(df['High'].max() * 0.95)
                    profit = ((curr - buy) / buy * 100) if buy > 0 else 0
                    status = "🚨위험" if curr <= stop else "✅유지"
                    chart_data_dict[kn] = {"df": df, "stop": stop}
                
                full_results.append({
                    "종목명": kn, "수익률": f"{profit:.1f}%", "상태": status,
                    "수량": row['수량'], "매수단가": row['매수단가'], "손절가": row['손절가'],
                    "현재가": curr, "메모": row['메모'], "코드": code
                })
            except:
                continue

    if full_results:
        st.subheader("📋 내 포트폴리오 현황")
        df_main = pd.DataFrame(full_results)
        
        # 표 출력
        edited_df = st.data_editor(
            df_main[["종목명", "수익률", "상태", "수량", "매수단가", "손절가", "현재가", "메모"]],
            use_container_width=True, hide_index=True, key="main_editor",
            disabled=["종목명", "수익률", "상태", "현재가"]
        )
        
        # 저장 버튼
        if st.button("💾 변경사항 저장", type="primary"):
            # 편집된 표와 원래 코드를 안전하게 매칭
            new_stocks = edited_df.copy()
            new_stocks['코드'] = df_main['코드'].values
            st.session_state.stocks = new_stocks[["코드", "수량", "매수단가", "손절가", "메모"]]
            st.success("저장 완료!")
            st.rerun()

        # 4. 차트 상세 분석
        st.divider()
        if chart_data_dict:
            sel = st.selectbox("🎯 차트 분석 종목", list(chart_data_dict.keys()))
            target = chart_data_dict[sel]
            plot_df = pd.DataFrame({
                "주가": target['df']['Close'].values.flatten(), 
                "손절선": target['stop']
            }, index=target['df'].index)
            st.line_chart(plot_df)
else:
    st.info("👈 왼쪽에서 종목 번호를 입력하거나 백업 파일을 불러오세요.")
