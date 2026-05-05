import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime

# 1. 앱 설정
st.set_page_config(page_title="트렌드 마스터 프로", layout="wide")
st.title("🚀 트렌드 마스터: 실시간 분석 시스템")

# 2. 데이터 관리 (세션 상태 초기화)
if 'stocks' not in st.session_state:
    st.session_state.stocks = pd.DataFrame(columns=["코드", "수량", "매수단가", "손절가", "메모"])

# 3. 사이드바: 종목 추가
with st.sidebar:
    st.header("➕ 종목 추가")
    def add_ticker():
        code = st.session_state.new_code.strip()
        if code and code not in st.session_state.stocks['코드'].values:
            # 기본값 1, 0, 0으로 추가
            new_row = pd.DataFrame([{"코드": code, "수량": 1, "매수단가": 0, "손절가": 0, "메모": ""}])
            st.session_state.stocks = pd.concat([st.session_state.stocks, new_row], ignore_index=True)
            st.session_state.new_code = "" 
    st.text_input("종목 번호 입력 후 Enter", key="new_code", on_change=add_ticker)
    
    st.divider()
    if st.button("🗑️ 리스트 비우기"):
        st.session_state.stocks = pd.DataFrame(columns=["코드", "수량", "매수단가", "손절가", "메모"])
        st.rerun()

# 4. 분석 로직 (저장된 데이터를 바탕으로 현재가 계산)
if not st.session_state.stocks.empty:
    with st.spinner("최신 시장 데이터 분석 중..."):
        full_results = []
        analysis_data = {}
        
        # 현재 저장된 모든 종목 분석
        for idx, row in st.session_state.stocks.iterrows():
            code = str(row['코드'])
            tk = code + ".KS" if (code.isdigit() and len(code)==6) else code
            try:
                # 야후 파이낸스 데이터 호출
                df = yf.download(tk, period="6mo", progress=False)
                if df.empty and ".KS" in tk:
                    tk = code + ".KQ"
                    df = yf.download(tk, period="6mo", progress=False)
                
                if not df.empty:
                    curr = int(df['Close'].iloc[-1])
                    qty = int(row['수량'])
                    buy_p = int(row['매수단가'])
                    stop = int(row['손절가'])
                    
                    # 손절가 자동 제안 (미입력 시)
                    if stop == 0: stop = int(df['High'].iloc[-21:-1].max() * 0.97)
                    
                    p_rate = ((curr - buy_p) / buy_p * 100) if buy_p > 0 else 0
                    
                    full_results.append({
                        "코드": code, "종목": tk, "수익률": f"{p_rate:.1f}%", 
                        "상태": "🚨위험" if curr <= stop else "✅유지",
                        "수량": qty, "매수단가": buy_p, "손절가": stop, "현재가": curr, "메모": row['메모']
                    })
                    analysis_data[tk] = {"df": df, "stop": stop}
            except: continue

    if full_results:
        st.subheader("📝 내 포트폴리오 관리")
        # 편집 가능한 표 생성
        df_main = pd.DataFrame(full_results)
        
        # [핵심] 표에서 수정한 값을 edited_df로 받음
        edited_df = st.data_editor(
            df_main, 
            use_container_width=True, 
            hide_index=True,
            column_config={
                "코드": None, # 코드 숨김
                "종목": st.column_config.TextColumn("종목", disabled=True),
                "수익률": st.column_config.TextColumn("수익률", disabled=True),
                "상태": st.column_config.TextColumn("상태", disabled=True),
                "현재가": st.column_config.NumberColumn("현재가", disabled=True),
            },
            key="editor"
        )
        
        # [해결책] 저장 버튼을 누르면 수정한 값을 원본 데이터에 덮어쓰고 새로고침
        if st.button("💾 변경사항 저장 및 분석 반영", type="primary"):
            st.session_state.stocks = edited_df[["코드", "수량", "매수단가", "손절가", "메모"]]
            st.success("데이터가 성공적으로 저장되었습니다!")
            st.rerun()

        # 5. 차트 분석
        st.divider()
        sel = st.selectbox("🎯 상세 차트 분석", df_main['종목'].tolist())
        if sel in analysis_data:
            target = analysis_data[sel]
            p_df = pd.DataFrame({
                "주가": target['df']['Close'].values.flatten(), 
                "손절선": target['stop']
            }, index=target['df'].index)
            st.line_chart(p_df)
else:
    st.info("👈 왼쪽 사이드바에 종목 번호를 입력하고 Enter를 누르세요.")
