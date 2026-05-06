import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime

# 한글명 부품 체크
try:
    from pykrx import stock
    PYKRX_AVAILABLE = True
except:
    PYKRX_AVAILABLE = False

st.set_page_config(page_title="트렌드 마스터 프로", layout="wide")
st.title("🚀 트렌드 마스터: 스마트 관리 시스템")

# 1. 데이터 저장소 초기화
if 'stocks' not in st.session_state:
    st.session_state.stocks = pd.DataFrame(columns=["코드", "수량", "매수단가", "손절가", "메모"])

# [보조 함수] 한글 이름 찾기
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
            else: st.warning("이미 있는 종목입니다.")

    # [핵심 수정] 종목별 개별 삭제 기능을 가장 강력하게 수정
    if not st.session_state.stocks.empty:
        st.divider()
        st.header("🗑️ 종목 삭제")
        # 현재 리스트에 있는 종목들을 이름과 함께 보여줌
        codes_for_delete = st.session_state.stocks['코드'].tolist()
        delete_target = st.selectbox(
            "삭제할 종목 선택", 
            codes_for_delete, 
            format_func=lambda x: f"{get_kr_name(x)} ({x})"
        )
        
        if st.button("❌ 선택 종목 삭제", use_container_width=True):
            # 메모리(Session State)에서 즉시 제거
            st.session_state.stocks = st.session_state.stocks[st.session_state.stocks['코드'] != delete_target].reset_index(drop=True)
            st.success(f"삭제되었습니다!")
            st.rerun() # 화면을 강제로 다시 그려서 즉시 반영

# 3. 분석 및 화면 표시
if not st.session_state.stocks.empty:
    full_results = []
    chart_data_dict = {}
    
    with st.spinner("데이터 분석 중..."):
        for idx, row in st.session_state.stocks.iterrows():
            code = str(row['코드']).zfill(6)
            kn = get_kr_name(code)
            
            try:
                # 데이터 수집 (Ticker 방식)
                tk_obj = yf.Ticker(code + ".KS")
                df = tk_obj.history(period="3mo")
                if df.empty:
                    tk_obj = yf.Ticker(code + ".KQ")
                    df = tk_obj.history(period="3mo")
                
                if not df.empty:
                    last_close = df['Close'].iloc[-1]
                    curr = int(last_close.iloc if hasattr(last_close, 'iloc') else last_close)
                    qty, buy, stop = int(row['수량']), int(row['매수단가']), int(row['손절가'])
                    if stop == 0 or stop > curr * 2: stop = int(df['High'].max() * 0.95)
                    profit = ((curr - buy) / buy * 100) if buy > 0 else 0
                    status = "🚨위험" if curr <= stop else "✅유지"
                    chart_data_dict[kn] = {"df": df, "stop": stop}
                else:
                    curr, profit, status, stop = 0, 0, "⚠️조회불가", row['손절가']
                
                full_results.append({
                    "종목명": kn, "수익률": f"{profit:.1f}%", "상태": status,
                    "수량": row['수량'], "매수단가": row['매수단가'], "손절가": stop,
                    "현재가": curr, "메모": row['메모'], "코드": code
                })
            except:
                full_results.append({
                    "종목명": kn, "수익률": "0.0%", "상태": "⚠️오류",
                    "수량": row['수량'], "매수단가": row['매수단가'], "손절가": row['손절가'],
                    "현재가": 0, "메모": row['메모'], "코드": code
                })

    if full_results:
        st.subheader("📋 내 포트폴리오 (수정 후 저장 버튼 필수!)")
        df_main = pd.DataFrame(full_results)
        
        # 편집 표
        edited_df = st.data_editor(
            df_main[["종목명", "수익률", "상태", "수량", "매수단가", "손절가", "현재가", "메모"]],
            use_container_width=True, hide_index=True, key="main_editor",
            disabled=["종목명", "수익률", "상태", "현재가"]
        )
        
        c1, c2 = st.columns(2)
        with c1:
            if st.button("💾 변경사항 저장", type="primary", use_container_width=True):
                # 편집된 표와 원래의 '코드'를 매칭하여 메모리 갱신
                new_data = edited_df.copy()
                new_data['코드'] = df_main['코드'].values
                st.session_state.stocks = new_data[["코드", "수량", "매수단가", "손절가", "메모"]]
                st.success("저장 완료!")
                st.rerun()
        with c2:
            csv = st.session_state.stocks.to_csv(index=False).encode('utf-8-sig')
            st.download_button("📥 백업(CSV) 다운로드", data=csv, file_name="my_stocks.csv", use_container_width=True)

        # 4. 차트 분석
        if chart_data_dict:
            st.divider()
            sel = st.selectbox("🎯 차트 분석 종목", list(chart_data_dict.keys()))
            target = chart_data_dict[sel]
            st.line_chart(pd.DataFrame({"주가": target['df']['Close'].values.flatten(), "손절선": target['stop']}, index=target['df'].index))
else:
    st.info("👈 왼쪽에서 종목을 추가하거나 파일을 불러오세요.")
