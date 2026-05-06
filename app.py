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
    # 파일 업로더
    uploaded_file = st.file_uploader("백업 파일을 선택하세요", type=["csv"], key="uploader")
    if uploaded_file is not None:
        try:
            try: load_df = pd.read_csv(uploaded_file, encoding='utf-8-sig')
            except: load_df = pd.read_csv(uploaded_file, encoding='cp949')
            
            load_df.columns = load_df.columns.str.strip()
            if '코드' in load_df.columns:
                load_df['코드'] = load_df['코드'].astype(str).str.zfill(6)
                st.session_state.stocks = pd.concat([st.session_state.stocks, load_df], ignore_index=True).drop_duplicates(subset=['코드'], keep='last')
                st.success("데이터를 불러왔습니다!")
            else: st.error("'코드' 열을 찾을 수 없습니다.")
        except Exception as e: st.error(f"오류: {e}")

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

    # 3. [새 기능] 종목별 개별 삭제 섹션
    if not st.session_state.stocks.empty:
        st.divider()
        st.header("🗑️ 종목 삭제")
        # 현재 리스트에 있는 종목들을 "이름(코드)" 형태로 보여줌
        stock_list = st.session_state.stocks['코드'].tolist()
        delete_target = st.selectbox("삭제할 종목 선택", stock_list, format_func=lambda x: f"{get_kr_name(x)} ({x})")
        
        if st.button("❌ 선택 종목 삭제", type="secondary"):
            st.session_state.stocks = st.session_state.stocks[st.session_state.stocks['코드'] != delete_target]
            st.success(f"삭제 완료!")
            st.rerun()

# 4. 분석 및 화면 표시
if not st.session_state.stocks.empty:
    full_results = []
    chart_data_dict = {}
    
    with st.spinner("데이터 동기화 중..."):
        for idx, row in st.session_state.stocks.iterrows():
            code = str(row['코드']).zfill(6)
            tk = code + ".KS"
            kn = get_kr_name(code)
            
            try:
                curr, profit, status = 0, 0, "⚠️조회불가"
                df = yf.download(tk, period="3mo", progress=False)
                if df.empty:
                    tk = code + ".KQ"; df = yf.download(tk, period="3mo", progress=False)
                
                if not df.empty:
                    last_close = df['Close'].iloc[-1]
                    curr = int(last_close.iloc if hasattr(last_close, 'iloc') else last_close)
                    qty, buy, stop = int(row['수량']), int(row['매수단가']), int(row['손절가'])
                    
                    if stop == 0:
                        high_val = df['High'].max()
                        stop = int((high_val.iloc if hasattr(high_val, 'iloc') else high_val) * 0.95)
                    
                    profit = ((curr - buy) / buy * 100) if buy > 0 else 0
                    status = "🚨위험" if curr <= stop else "✅유지"
                    chart_data_dict[kn] = {"df": df, "stop": stop}
                
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
        st.subheader("📋 내 포트폴리오 (수정 후 저장 버튼을 누르세요)")
        df_main = pd.DataFrame(full_results)
        
        # [수정] num_rows="dynamic"을 추가하여 사용자가 표에서 직접 줄을 지울 수도 있게 함
        edited_df = st.data_editor(
            df_main[["종목명", "수익률", "상태", "수량", "매수단가", "손절가", "현재가", "메모"]],
            use_container_width=True, hide_index=True, key="main_editor",
            disabled=["종목명", "수익률", "상태", "현재가"],
            num_rows="dynamic" # 줄 추가/삭제 기능 활성화
        )
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("💾 변경사항 저장", type="primary"):
                # 표의 데이터와 원래 코드를 다시 맞춤 (줄 삭제 대응)
                new_stocks = edited_df.copy()
                # 사용자가 표에서 직접 지운 경우를 대비해 인덱스 기준으로 코드 매칭
                st.session_state.stocks = pd.DataFrame({
                    "코드": df_main.iloc[edited_df.index]['코드'].values,
                    "수량": edited_df['수량'].values,
                    "매수단가": edited_df['매수단가'].values,
                    "손절가": edited_df['손절가'].values,
                    "메모": edited_df['메모'].values
                })
                st.success("저장 완료!")
                st.rerun()
        with col2:
            csv = st.session_state.stocks.to_csv(index=False).encode('utf-8-sig')
            st.download_button("📥 백업(CSV) 다운로드", data=csv, file_name="my_stocks.csv")

        # 5. 차트 분석
        if chart_data_dict:
            st.divider()
            sel = st.selectbox("🎯 차트 분석 종목", list(chart_data_dict.keys()))
            target = chart_data_dict[sel]
            st.line_chart(pd.DataFrame({"주가": target['df']['Close'].values.flatten(), "손절선": target['stop']}, index=target['df'].index))
else:
    st.info("👈 왼쪽 사이드바에서 종목을 추가하거나 파일을 불러오세요.")
