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
    st.header("💾 데이터 복구 (CSV)")
    # 업로드 즉시 실행되도록 로직 변경
    uploaded_file = st.file_uploader("백업 파일을 선택하세요", type=["csv"], key="uploader")
    
    if uploaded_file is not None:
        try:
            # 다양한 인코딩 시도 (UTF-8-SIG, CP949 순서)
            try:
                load_df = pd.read_csv(uploaded_file, encoding='utf-8-sig')
            except:
                uploaded_file.seek(0)
                load_df = pd.read_csv(uploaded_file, encoding='cp949')
            
            # 열 이름 표준화 (공백 제거 등)
            load_df.columns = load_df.columns.str.strip()
            
            if '코드' in load_df.columns:
                # 0 채우기 및 데이터 정리
                load_df['코드'] = load_df['코드'].astype(str).str.zfill(6)
                # 기존 데이터와 병합 (중복 제거)
                st.session_state.stocks = pd.concat([st.session_state.stocks, load_df], ignore_index=True).drop_duplicates(subset=['코드'], keep='last')
                st.success("데이터를 성공적으로 불러왔습니다!")
                # 업로드 후 파일 초기화를 위해 rerun 사용하지 않고 상태 유지
            else:
                st.error("'코드'라는 이름의 열을 찾을 수 없습니다.")
        except Exception as e:
            st.error(f"파일을 읽는 중 오류가 발생했습니다: {e}")

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
        for idx, row in st.session_state.stocks.iterrows():
            code = str(row['코드']).zfill(6)
            tk = code + ".KS"
            kn = get_kr_name(code)
            
            try:
                curr, profit, status = 0, 0, "⚠️조회불가"
                df = yf.download(tk, period="3mo", progress=False)
                if df.empty:
                    tk = code + ".KQ"
                    df = yf.download(tk, period="3mo", progress=False)
                
                if not df.empty:
                    # 데이터가 있을 때만 계산
                    last_close = df['Close'].iloc[-1]
                    # yfinance 업데이트 대응 (단일값 추출)
                    curr = int(last_close.iloc[0] if hasattr(last_close, 'iloc') else last_close)
                    
                    qty = int(row['수량'])
                    buy = int(row['매수단가'])
                    stop = int(row['손절가'])
                    
                    if stop == 0:
                        high_val = df['High'].max()
                        high_val = high_val.iloc[0] if hasattr(high_val, 'iloc') else high_val
                        stop = int(high_val * 0.95)
                    
                    profit = ((curr - buy) / buy * 100) if buy > 0 else 0
                    status = "🚨위험" if curr <= stop else "✅유지"
                    chart_data_dict[kn] = {"df": df, "stop": stop}
                
                full_results.append({
                    "종목명": kn, "수익률": f"{profit:.1f}%", "상태": status,
                    "수량": row['수량'], "매수단가": row['매수단가'], "손절가": stop,
                    "현재가": curr, "메모": row['메모'], "코드": code
                })
            except:
                # 에러 발생 시에도 빈 줄은 추가
                full_results.append({
                    "종목명": kn, "수익률": "0.0%", "상태": "⚠️오류",
                    "수량": row['수량'], "매수단가": row['매수단가'], "손절가": row['손절가'],
                    "현재가": 0, "메모": row['메모'], "코드": code
                })

    if full_results:
        st.subheader("📋 내 포트폴리오 현황")
        df_main = pd.DataFrame(full_results)
        
        edited_df = st.data_editor(
            df_main[["종목명", "수익률", "상태", "수량", "매수단가", "손절가", "현재가", "메모"]],
            use_container_width=True, hide_index=True, key="main_editor",
            disabled=["종목명", "수익률", "상태", "현재가"]
        )
        
        if st.button("💾 변경사항 저장", type="primary"):
            new_stocks = edited_df.copy()
            new_stocks['코드'] = df_main['코드'].values
            st.session_state.stocks = new_stocks[["코드", "수량", "매수단가", "손절가", "메모"]]
            st.success("저장 완료!")
            st.rerun()

        # 4. 차트 분석
        if chart_data_dict:
            st.divider()
            sel = st.selectbox("🎯 차트 분석 종목", list(chart_data_dict.keys()))
            target = chart_data_dict[sel]
            # 차트 데이터 준비
            c_df = pd.DataFrame(index=target['df'].index)
            c_df['주가'] = target['df']['Close'].values.flatten()
            c_df['손절선'] = target['stop']
            st.line_chart(c_df)
else:
    st.info("👈 왼쪽에서 파일을 불러오거나 종목을 추가하세요.")
