import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime

# 1. 앱 설정
st.set_page_config(page_title="트렌드 마스터 프로", layout="wide")
st.title("🚀 트렌드 마스터: 최종 통합 시스템")

# 2. 데이터 저장소 초기화 (없으면 생성)
if 'stocks' not in st.session_state:
    st.session_state.stocks = pd.DataFrame(columns=["코드", "수량", "매수단가", "손절가", "메모"])

# 3. 사이드바 구성
with st.sidebar:
    st.header("💾 데이터 복구")
    uploaded_file = st.file_uploader("CSV 파일을 선택하세요", type=["csv"], key="file_loader")
    
    if uploaded_file is not None:
        # 파일을 이미 적용했는지 체크하는 장치
        if st.button("📂 파일 데이터 적용하기"):
            try:
                load_df = pd.read_csv(uploaded_file)
                if '코드' in load_df.columns:
                    load_df['코드'] = load_df['코드'].astype(str).str.zfill(6)
                    # 기존 목록에 파일 내용을 합침 (중복 제거)
                    combined = pd.concat([st.session_state.stocks, load_df]).drop_duplicates(subset=['코드'], keep='last')
                    st.session_state.stocks = combined
                    st.success("파일 데이터를 불러왔습니다!")
                    st.rerun()
                else:
                    st.error("파일에 '코드' 열이 없습니다.")
            except:
                st.error("파일 형식이 올바르지 않습니다.")

    st.divider()
    st.header("➕ 종목 추가")
    # 수동 입력창
    new_code_input = st.text_input("종목 번호 입력 (예: 005930)", key="manual_stock_in")
    
    if st.button("📌 포트폴리오에 추가"):
        if new_code_input:
            code = new_code_input.strip()
            if code.isdigit():
                code = code.zfill(6)
            
            # 중복 체크 후 추가
            if code not in st.session_state.stocks['코드'].astype(str).values:
                new_row = pd.DataFrame([{"코드": code, "수량": 1, "매수단가": 0, "손절가": 0, "메모": ""}])
                st.session_state.stocks = pd.concat([st.session_state.stocks, new_row], ignore_index=True)
                st.success(f"{code} 추가되었습니다!")
                st.rerun()
            else:
                st.warning("이미 목록에 있는 종목입니다.")
        else:
            st.error("번호를 입력하세요.")

    if st.button("🗑️ 리스트 전체 비우기"):
        st.session_state.stocks = pd.DataFrame(columns=["코드", "수량", "매수단가", "손절가", "메모"])
        st.rerun()

# 4. 분석 및 화면 표시
if not st.session_state.stocks.empty:
    results = []
    charts = {}
    with st.spinner("최신 시장 데이터 분석 중..."):
        for _, row in st.session_state.stocks.iterrows():
            code = str(row['코드']).zfill(6)
            tk = code + ".KS" if code.isdigit() else code
            try:
                # 야후 파이낸스 접속
                df = yf.download(tk, period="3mo", progress=False, timeout=10)
                if df.empty and ".KS" in tk:
                    tk = code + ".KQ"
                    df = yf.download(tk, period="3mo", progress=False, timeout=10)
                
                if not df.empty:
                    # 데이터 정리
                    curr = int(df['Close'].iloc[-1].iloc if hasattr(df['Close'].iloc[-1], 'iloc') else df['Close'].iloc[-1])
                    high_max = df['High'].max()
                    high_val = high_max.iloc if hasattr(high_max, 'iloc') else high_max
                    
                    qty, buy, stop = int(row['수량']), int(row['매수단가']), int(row['손절가'])
                    if stop == 0: stop = int(high_val * 0.95)
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
        
        # 편집 가능한 표
        edited_df = st.data_editor(
            df_main[["코드", "종목", "수익률", "상태", "수량", "매수단가", "손절가", "현재가", "메모"]],
            use_container_width=True, hide_index=True, key="main_editor_final",
            disabled=["코드", "종목", "수익률", "상태", "현재가"]
        )
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("💾 변경사항 저장", type="primary"):
                st.session_state.stocks = edited_df[["코드", "수량", "매수단가", "손절가", "메모"]]
                st.success("수정 사항이 저장되었습니다!")
                st.rerun()
        with col2:
            # 백업용 다운로드 버튼
            csv_data = st.session_state.stocks.to_csv(index=False).encode('utf-8-sig')
            st.download_button("📥 내 컴퓨터에 백업(CSV)", data=csv_data, file_name="my_stocks.csv")

        # 5. 차트 분석
        st.divider()
        sel = st.selectbox("🎯 분석할 종목 선택", list(charts.keys()))
        if sel in charts:
            target = charts[sel]
            st.line_chart(pd.DataFrame({"주가": target['df']['Close'].values.flatten(), "손절선": target['stop']}, index=target['df'].index))
else:
    st.info("👈 왼쪽에서 파일을 불러오거나 종목 번호를 입력하여 추가하세요.")
