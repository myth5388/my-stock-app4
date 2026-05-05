import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime

# [안전 장치] 부품 설치 에러 방지
try:
    from pykrx import stock
    PYKRX_AVAILABLE = True
except:
    PYKRX_AVAILABLE = False

st.set_page_config(page_title="트렌드 마스터", layout="wide")
st.title("🛡️ 트렌드 마스터: 최종 안정화 관리 시스템")

# 1. 데이터 관리 (세션 상태 초기화)
if 'stocks' not in st.session_state:
    st.session_state.stocks = pd.DataFrame(columns=["코드", "수량", "매수단가", "손절가", "메모"])

# 2. 사이드바: 데이터 복구 및 종목 추가
with st.sidebar:
    st.header("💾 데이터 복구 (CSV)")
    uploaded_file = st.file_uploader("저장했던 CSV 파일을 올려주세요", type=["csv"])
    if uploaded_file is not None:
        st.session_state.stocks = pd.read_csv(uploaded_file)
        st.success("데이터 복구 성공!")
        st.rerun()

    st.divider()
    st.header("➕ 종목 추가")
    def add_stock():
        code = st.session_state.new_code_in.strip()
        if code and code not in st.session_state.stocks['코드'].values:
            new_row = pd.DataFrame([{"코드": code, "수량": 1, "매수단가": 0, "손절가": 0, "메모": ""}])
            st.session_state.stocks = pd.concat([st.session_state.stocks, new_row], ignore_index=True)
            st.session_state.new_code_in = "" 
    st.text_input("종목 번호(Enter)", key="new_code_in", on_change=add_stock)
    
    if st.button("🗑️ 리스트 전체 비우기"):
        st.session_state.stocks = pd.DataFrame(columns=["코드", "수량", "매수단가", "손절가", "메모"])
        st.rerun()

# 3. 메인 분석 로직
if not st.session_state.stocks.empty:
    with st.spinner("최신 주가 분석 중..."):
        full_results = []
        analysis_data = {}
        
        # 현재 리스트의 모든 종목 분석
        for idx, row in st.session_state.stocks.iterrows():
            code = str(row['코드'])
            tk = code + ".KS" if (code.isdigit() and len(code)==6) else code
            try:
                df = yf.download(tk, period="6mo", progress=False)
                if df.empty and ".KS" in tk:
                    tk = code + ".KQ"
                    df = yf.download(tk, period="6mo", progress=False)
                
                if not df.empty:
                    # 데이터가 2차원(Series)일 경우를 대비해 확실히 값만 추출
                    curr = int(df['Close'].iloc[-1].iloc[0] if hasattr(df['Close'].iloc[-1], 'iloc') else df['Close'].iloc[-1])
                    high_20 = df['High'].iloc[-21:-1].max()
                    high_20_val = high_20.iloc[0] if hasattr(high_20, 'iloc') else high_20
                    
                    qty, buy_p, stop = int(row['수량']), int(row['매수단가']), int(row['손절가'])
                    if stop == 0: stop = int(high_20_val * 0.97)
                    
                    profit = ((curr - buy_p) / buy_p * 100) if buy_p > 0 else 0
                    
                    full_results.append({
                        "코드": code, "종목": tk, "수익률": f"{profit:.1f}%", 
                        "상태": "🚨위험" if curr <= stop else "✅유지",
                        "수량": qty, "매수단가": buy_p, "손절가": stop, "현재가": curr, "메모": row['메모']
                    })
                    analysis_data[tk] = {"df": df, "stop": stop, "code": code}
            except: continue

    if full_results:
        st.subheader("📝 내 포트폴리오 관리")
        df_main = pd.DataFrame(full_results)
        
        # [저장 문제 해결] 데이터 에디터
        edited_df = st.data_editor(
            df_main[["코드", "종목", "수익률", "상태", "수량", "매수단가", "손절가", "현재가", "메모"]], 
            use_container_width=True, hide_index=True,
            disabled=["종목", "수익률", "상태", "현재가"],
            key="data_editor"
        )
        
        c1, c2 = st.columns(2)
        with c1:
            if st.button("💾 변경사항 저장 및 분석 반영", type="primary"):
                # 수정된 내용을 세션에 즉시 저장
                st.session_state.stocks = edited_df[["코드", "수량", "매수단가", "손절가", "메모"]]
                st.success("데이터가 반영되었습니다!")
                st.rerun()
        with c2:
            # 영구 저장을 위한 파일 다운로드 버튼
            csv = st.session_state.stocks.to_csv(index=False).encode('utf-8-sig')
            st.download_button("📥 내 컴퓨터에 백업(CSV 저장)", data=csv, file_name="my_stocks.csv", mime="text/csv")

        # 4. 차트 분석
        st.divider()
        sel = st.selectbox("🎯 상세 차트 분석", df_main['종목'].tolist())
        if sel in analysis_data:
            target = analysis_data[sel]
            p_df = pd.DataFrame(index=target['df'].index)
            # 차트 에러 방지용 flatten 처리
            p_df['주가'] = target['df']['Close'].values.reshape(-1)
            p_df['손절선'] = target['stop']
            st.line_chart(p_df)
else:
    st.info("👈 왼쪽 사이드바에서 종목 번호를 입력하고 Enter를 누르세요.")

# 5. 추천주 섹션
st.divider()
st.subheader("🚀 오늘의 주도주 추천")
recos = [{"이름": "SK하이닉스", "코드": "000660"}, {"이름": "삼양식품", "코드": "003230"}, {"이름": "알테오젠", "코드": "196170"}]
cols = st.columns(len(recos))
for i, r in enumerate(recos):
    with cols[i]:
        if st.button(f"➕ {r['이름']} 추가"):
            if r['코드'] not in st.session_state.stocks['코드'].values:
                new_data = pd.DataFrame([{"코드": r['코드'], "수량": 1, "매수단가": 0, "손절가": 0, "메모": "추천주"}])
                st.session_state.stocks = pd.concat([st.session_state.stocks, new_data], ignore_index=True)
                st.rerun()
