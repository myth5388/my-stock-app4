import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime

# 1. 앱 설정 (속도와 안정성 최우선)
st.set_page_config(page_title="트렌드 마스터 프로", layout="wide")
st.title("🚀 트렌드 마스터: 고속 통합 관리 시스템")

# 2. 데이터 저장소 초기화
if 'stocks' not in st.session_state:
    st.session_state.stocks = pd.DataFrame(columns=["코드", "수량", "매수단가", "손절가", "메모"])

# 3. 사이드바 구성
with st.sidebar:
    st.header("💾 데이터 복구 (CSV)")
    # 파일 업로더
    uploaded_file = st.file_uploader("백업 파일을 선택하세요", type=["csv"], key="backup_loader")
    
    if uploaded_file is not None:
        if st.button("📂 데이터 합치기", key="merge_btn"):
            try:
                load_df = pd.read_csv(uploaded_file)
                if '코드' in load_df.columns:
                    load_df['코드'] = load_df['코드'].astype(str).str.zfill(6)
                    # 기존 목록 + 파일 내용 합치기 (중복은 제거)
                    combined = pd.concat([st.session_state.stocks, load_df], ignore_index=True)
                    st.session_state.stocks = combined.drop_duplicates(subset=['코드'], keep='last')
                    st.success("데이터를 성공적으로 합쳤습니다!")
                    st.rerun()
                else:
                    st.error("파일에 '코드' 컬럼이 없습니다.")
            except:
                st.error("파일 읽기 실패")

    st.divider()
    st.header("➕ 종목 추가")
    # [안정화] 텍스트 입력 후 버튼 클릭 방식으로 고정
    new_code = st.text_input("종목 번호 (예: 005930)", key="manual_in")
    
    if st.button("📌 리스트에 추가", key="add_btn"):
        if new_code:
            code = new_code.strip().zfill(6) if new_code.strip().isdigit() else new_code.strip()
            if code not in st.session_state.stocks['코드'].astype(str).values:
                new_row = pd.DataFrame([{"코드": code, "수량": 1, "매수단가": 0, "손절가": 0, "메모": ""}])
                st.session_state.stocks = pd.concat([st.session_state.stocks, new_row], ignore_index=True)
                st.success(f"{code} 추가 완료!")
                st.rerun()
            else:
                st.warning("이미 목록에 있는 종목입니다.")

    if st.button("🗑️ 전체 비우기"):
        st.session_state.stocks = pd.DataFrame(columns=["코드", "수량", "매수단가", "손절가", "메모"])
        st.rerun()

# 4. 분석 및 메인 화면 표시
if not st.session_state.stocks.empty:
    with st.spinner("최신 주가 동기화 중..."):
        full_results = []
        chart_data_dict = {}
        
        # [고속화] 모든 종목 티커 한꺼번에 생성
        codes = st.session_state.stocks['코드'].tolist()
        tickers = [c + ".KS" if c.isdigit() else c for c in codes]
        
        # 데이터를 한 번에 통째로 다운로드 (속도 획기적 개선)
        raw_data = yf.download(tickers, period="3mo", group_by='ticker', progress=False)

        for idx, row in st.session_state.stocks.iterrows():
            code = str(row['코드'])
            tk = code + ".KS" if code.isdigit() else code
            try:
                # 단일 종목과 여러 종목 데이터 추출 방식 구분
                df = raw_data[tk].dropna() if len(tickers) > 1 else raw_data.dropna()
                
                if not df.empty:
                    curr = int(df['Close'].iloc[-1])
                    qty, buy, stop = int(row['수량']), int(row['매수단가']), int(row['손절가'])
                    
                    # 지능형 자동 손절가
                    if stop == 0: stop = int(df['High'].max() * 0.95)
                    
                    p_rate = ((curr - buy) / buy * 100) if buy > 0 else 0
                    full_results.append({
                        "코드": code, "종목": tk, "수익률": f"{p_rate:.1f}%",
                        "상태": "🚨위험" if curr <= stop else "✅유지",
                        "수량": qty, "매수단가": buy, "손절가": stop, "현재가": curr, "메모": row['메모']
                    })
                    chart_data_dict[tk] = {"df": df, "stop": stop}
            except: continue

    if full_results:
        st.subheader("📋 내 포트폴리오 현황")
        df_main = pd.DataFrame(full_results)
        
        # 편집 가능한 표
        edited_df = st.data_editor(
            df_main[["코드", "종목", "수익률", "상태", "수량", "매수단가", "손절가", "현재가", "메모"]],
            use_container_width=True, hide_index=True, key="main_editor",
            disabled=["코드", "종목", "수익률", "상태", "현재가"]
        )
        
        # 저장 및 백업
        c1, c2 = st.columns(2)
        with c1:
            if st.button("💾 변경사항 저장 및 분석", type="primary"):
                st.session_state.stocks = edited_df[["코드", "수량", "매수단가", "손절가", "메모"]]
                st.success("반영되었습니다!")
                st.rerun()
        with c2:
            csv = st.session_state.stocks.to_csv(index=False).encode('utf-8-sig')
            st.download_button("📥 내 컴퓨터에 백업(CSV)", data=csv, file_name="my_stocks.csv")

        # 5. 차트 상세 분석
        st.divider()
        sel = st.selectbox("🎯 분석할 종목 선택", list(chart_data_dict.keys()))
        if sel in chart_data_dict:
            target = chart_data_dict[sel]
            # 차트 에러 방지용 flatten 적용
            plot_df = pd.DataFrame({
                "주가": target['df']['Close'].values.flatten(), 
                "손절선": target['stop']
            }, index=target['df'].index)
            st.line_chart(plot_df)
else:
    st.info("👈 왼쪽에서 파일을 불러오거나 종목 번호를 입력하세요.")
