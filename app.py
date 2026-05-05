import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime

# 1. 앱 설정
st.set_page_config(page_title="트렌드 마스터 프로", layout="wide")
st.title("🚀 트렌드 마스터: 무한 로딩 방지 시스템")

# 2. 데이터 관리 (세션 상태 초기화)
if 'stocks' not in st.session_state:
    st.session_state.stocks = pd.DataFrame(columns=["코드", "수량", "매수단가", "손절가", "메모"])

# 3. 사이드바: 파일 복구 및 종목 추가
with st.sidebar:
    st.header("💾 데이터 복구")
    uploaded_file = st.file_uploader("CSV 파일을 올려주세요", type=["csv"])
    if uploaded_file is not None:
        try:
            load_df = pd.read_csv(uploaded_file)
            # [보정] 엑셀이 지운 앞자리 '0'을 다시 채워줌 (핵심!)
            load_df['코드'] = load_df['코드'].astype(str).str.zfill(6)
            st.session_state.stocks = load_df
            st.success("데이터 복구 완료!")
            st.rerun()
        except:
            st.error("파일 형식이 잘못되었습니다.")

    st.divider()
    st.header("➕ 종목 추가")
    def add_stock():
        code = st.session_state.new_in.strip()
        if code:
            # 입력 시에도 자동으로 6자리 채움
            code = code.zfill(6) if code.isdigit() else code
            if code not in st.session_state.stocks['코드'].values:
                new_row = pd.DataFrame([{"코드": code, "수량": 1, "매수단가": 0, "손절가": 0, "메모": ""}])
                st.session_state.stocks = pd.concat([st.session_state.stocks, new_row], ignore_index=True)
                st.session_state.new_in = ""
    st.text_input("종목 번호(Enter)", key="new_in", on_change=add_stock)

# 4. 분석 로직 (무한 로딩 방지용 try-except 강화)
if not st.session_state.stocks.empty:
    results = []
    charts = {}
    with st.spinner("시장 데이터 동기화 중..."):
        for _, row in st.session_state.stocks.iterrows():
            code = str(row['코드']).zfill(6) if str(row['코드']).isdigit() else str(row['코드'])
            tk = code + ".KS" if code.isdigit() else code
            try:
                # 데이터를 1개월치만 빠르게 가져옴 (속도 최적화)
                df = yf.download(tk, period="3mo", progress=False, timeout=5)
                if df.empty and ".KS" in tk:
                    tk = code + ".KQ"
                    df = yf.download(tk, period="3mo", progress=False, timeout=5)
                
                if not df.empty:
                    curr = int(df['Close'].iloc[-1])
                    qty, buy, stop = int(row['수량']), int(row['매수단가']), int(row['손절가'])
                    if stop == 0: stop = int(df['High'].max() * 0.95)
                    profit = ((curr - buy) / buy * 100) if buy > 0 else 0
                    
                    results.append({
                        "코드": code, "종목": tk, "수익률": f"{profit:.1f}%", 
                        "상태": "🚨위험" if curr <= stop else "✅유지",
                        "수량": qty, "매수단가": buy, "손절가": stop, "현재가": curr, "메모": row['메모']
                    })
                    charts[tk] = {"df": df, "stop": stop}
            except: continue

    if results:
        st.subheader("📝 내 포트폴리오 관리")
        df_main = pd.DataFrame(results)
        edited_df = st.data_editor(
            df_main[["코드", "종목", "수익률", "상태", "수량", "매수단가", "손절가", "현재가", "메모"]],
            use_container_width=True, hide_index=True, key="main_editor",
            disabled=["코드", "종목", "수익률", "상태", "현재가"]
        )
        
        c1, c2 = st.columns(2)
        with c1:
            if st.button("💾 변경사항 저장", type="primary"):
                st.session_state.stocks = edited_df[["코드", "수량", "매수단가", "손절가", "메모"]]
                st.success("저장되었습니다!")
                st.rerun()
        with c2:
            csv = st.session_state.stocks.to_csv(index=False).encode('utf-8-sig')
            st.download_button("📥 내 컴퓨터에 백업", data=csv, file_name="my_portfolio.csv")

        st.divider()
        sel = st.selectbox("🎯 차트 분석", list(charts.keys()))
        if sel in charts:
            target = charts[sel]
            st.line_chart(pd.DataFrame({"주가": target['df']['Close'].values.flatten(), "손절선": target['stop']}, index=target['df'].index))
else:
    st.info("👈 왼쪽에서 종목을 추가하거나 파일을 불러오세요.")
