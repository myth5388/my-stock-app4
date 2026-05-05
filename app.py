import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime

# 1. 앱 설정
st.set_page_config(page_title="트렌드 마스터 프로", layout="wide")
st.title("🚀 트렌드 마스터: 통합 분석 시스템")

# 2. 데이터 관리 (세션 상태 초기화)
if 'stocks' not in st.session_state:
    st.session_state.stocks = pd.DataFrame(columns=["코드", "수량", "매수단가", "손절가", "메모"])

# 3. 사이드바 구성
with st.sidebar:
    st.header("💾 데이터 복구")
    uploaded_file = st.file_uploader("CSV 파일을 선택하세요", type=["csv"])
    
    # [수정] 파일이 올라왔을 때 자동으로 실행되지 않고 버튼을 눌러야 실행됨
    if uploaded_file is not None:
        if st.button("📂 파일 데이터 적용하기"):
            try:
                load_df = pd.read_csv(uploaded_file)
                # 엑셀에서 잘린 앞자리 0 보정
                if '코드' in load_df.columns:
                    load_df['코드'] = load_df['코드'].astype(str).str.zfill(6)
                    st.session_state.stocks = load_df
                    st.success("데이터를 성공적으로 가져왔습니다!")
                    st.rerun()
                else:
                    st.error("파일에 '코드' 열이 없습니다.")
            except:
                st.error("파일 형식이 잘못되었습니다.")

    st.divider()
    st.header("➕ 종목 추가")
    new_code_input = st.text_input("종목 번호 입력 (예: 005930)", key="stock_in")
    
    if st.button("📌 포트폴리오에 추가"):
        if new_code_input:
            code = new_code_input.strip()
            if code.isdigit():
                code = code.zfill(6)
            
            # 중복 체크 후 추가
            if code not in st.session_state.stocks['코드'].astype(str).values:
                new_row = pd.DataFrame([{"코드": code, "수량": 1, "매수단가": 0, "손절가": 0, "메모": ""}])
                st.session_state.stocks = pd.concat([st.session_state.stocks, new_row], ignore_index=True)
                st.success(f"{code} 추가 완료!")
                st.rerun()
            else:
                st.warning("이미 목록에 있는 종목입니다.")
        else:
            st.error("번호를 입력해주세요.")

    if st.button("🗑️ 리스트 전체 비우기"):
        st.session_state.stocks = pd.DataFrame(columns=["코드", "수량", "매수단가", "손절가", "메모"])
        st.rerun()

# 4. 분석 및 화면 표시
if not st.session_state.stocks.empty:
    results = []
    charts = {}
    with st.spinner("최신 데이터를 분석 중입니다..."):
        for _, row in st.session_state.stocks.iterrows():
            code = str(row['코드']).zfill(6)
            tk = code + ".KS" if code.isdigit() else code
            try:
                df = yf.download(tk, period="3mo", progress=False, timeout=10)
                if df.empty and ".KS" in tk:
                    tk = code + ".KQ"
                    df = yf.download(tk, period="3mo", progress=False, timeout=10)
                
                if not df.empty:
                    curr = int(df['Close'].iloc[-1].iloc if hasattr(df['Close'].iloc[-1], 'iloc') else df['Close'].iloc[-1])
                    high_max = df['High'].max()
                    high_max = high_max.iloc if hasattr(high_max, 'iloc') else high_max
                    
                    qty, buy, stop = int(row['수량']), int(row['매수단가']), int(row['손절가'])
                    if stop == 0: stop = int(high_max * 0.95)
                    profit = ((curr - buy) / buy * 100) if buy > 0 else 0
                    
                    results.append({
                        "코드": code, "종목": tk, "수익률": f"{profit:.1f}%", 
                        "상태": "🚨위험" if curr <= stop else "✅유지",
                        "수량": qty, "매수단가": buy, "손절가": stop, "현재가": curr, "메모": row['메모']
                    })
                    charts[tk] = {"df": df, "stop": stop}
            except: continue

    if results:
        st.subheader("📝 내 포트폴리오 현황")
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
            st.download_button("📥 내 컴퓨터에 백업(CSV)", data=csv, file_name="my_stocks.csv")

        st.divider()
        sel = st.selectbox("🎯 분석할 종목 선택", list(charts.keys()))
        if sel in charts:
            target = charts[sel]
            chart_data = pd.DataFrame({
                "주가": target['df']['Close'].values.flatten(), 
                "손절선": target['stop']
            }, index=target['df'].index)
            st.line_chart(chart_data)
else:
    st.info("👈 왼쪽에서 종목을 추가하거나 파일을 불러오세요.")
