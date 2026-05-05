import streamlit as st
import yfinance as yf
import pandas as pd
from pykrx import stock
from datetime import datetime, timedelta

# 1. 앱 설정
st.set_page_config(page_title="트렌드 마스터 프로", layout="wide")
st.title("🛡️ 트렌드 마스터: 고속 분석 & 중복 방지 시스템")

# 2. 데이터 관리 (세션 상태)
if 'stocks' not in st.session_state:
    st.session_state.stocks = pd.DataFrame(columns=["코드", "수량", "매수단가", "손절가", "매매메모"])

# 3. 사이드바: 종목 수동 추가
with st.sidebar:
    st.header("➕ 종목 수동 추가")
    def add_ticker():
        code = st.session_state.new_code_input.strip()
        if code:
            if code not in st.session_state.stocks['코드'].values:
                new_row = pd.DataFrame([{"코드": code, "수량": 10, "매수단가": 0, "손절가": 0, "매매메모": ""}])
                st.session_state.stocks = pd.concat([st.session_state.stocks, new_row], ignore_index=True)
            st.session_state.new_code_input = "" 
    st.text_input("번호 입력 후 Enter", key="new_code_input", on_change=add_ticker)
    
    st.divider()
    if st.button("🗑️ 전체 초기화"):
        st.session_state.stocks = pd.DataFrame(columns=["코드", "수량", "매수단가", "손절가", "매매메모"])
        st.rerun()

# [보조 함수] 매수 추천 스캔 (속도 개선: 배치 다운로드 적용)
@st.cache_data(ttl=3600)
def get_recommendations():
    target_codes = ["005930", "000660", "005380", "068270", "035420", "122630", "003230", "196170"]
    # 한 번에 모든 종목 데이터 다운로드 (네트워크 효율화)
    tickers = [t + ".KS" for t in target_codes]
    data = yf.download(tickers, period="3mo", group_by='ticker', progress=False)
    
    recos = []
    for t in target_codes:
        tk = t + ".KS"
        try:
            df = data[tk].dropna()
            if len(df) < 20: continue
            
            curr = float(df['Close'].iloc[-1])
            h20 = float(df['High'].iloc[-21:-1].max())
            vol_avg = float(df['Volume'].iloc[-21:-1].mean())
            curr_vol = float(df['Volume'].iloc[-1])
            
            # 조건: 20일 신고가 돌파 & 거래량 1.3배 이상
            if curr > h20 and curr_vol > vol_avg * 1.3:
                name = yf.Ticker(tk).info.get('shortName', t)
                recos.append({"이름": name, "코드": t, "현재가": int(curr), "전고점": int(h20)})
        except:
            continue
    return recos

# 4. 분석 및 메인 화면
if not st.session_state.stocks.empty:
    with st.spinner("데이터 동기화 중..."):
        full_results = []
        analysis_data = {} 
        total_asset = 0
        total_pl = 0

        for idx, row in st.session_state.stocks.iterrows():
            code = str(row['코드'])
            tk = code + ".KS" if (code.isdigit() and len(code) == 6) else code
            t_obj = yf.Ticker(tk)
            df = t_obj.history(period="6mo")
            if df.empty and ".KS" in tk:
                tk = code + ".KQ"; t_obj = yf.Ticker(tk); df = t_obj.history(period="6mo")
            
            if not df.empty:
                try: name = t_obj.info.get('shortName', code)
                except: name = code
                curr = int(df['Close'].iloc[-1])
                qty, buy_p, stop = int(row['수량']), int(row['매수단가']), int(row['손절가'])
                memo = str(row['매매메모'])
                
                if stop == 0:
                    avg_v = df['Volume'].mean()
                    v_days = df[(df['High'] < curr) & (df['Volume'] > avg_v * 1.5)]
                    stop = int(v_days['High'].max()) if not v_days.empty else int(curr * 0.95)
                
                p_rate = ((curr - buy_p) / buy_p * 100) if buy_p > 0 else 0
                eval_val = curr * qty
                total_asset += eval_val
                total_pl += (curr - buy_p) * qty if buy_p > 0 else 0
                
                full_results.append({
                    "코드": code, "종목명": name, "수익률": f"{p_rate:.2f}%",
                    "수량": qty, "매수단가": buy_p, "손절가": stop, "상태": "🚨위험" if curr <= stop else "✅유지", "매매메모": memo
                })
                analysis_data[name] = {"df": df, "stop": stop, "code": code, "memo": memo, "curr": curr}

    m1, m2 = st.columns(2)
    m1.metric("💰 총 자산 가치", f"{total_asset:,.0f}원")
    m2.metric("📈 총 손익", f"{total_pl:,.0f}원", delta=f"{total_pl:,.0f}원")

    st.subheader("📝 내 포트폴리오 관리")
    df_main = pd.DataFrame(full_results)
    edited_df = st.data_editor(df_main[["코드", "종목명", "수익률", "수량", "매수단가", "손절가", "상태", "매매메모"]], 
                               use_container_width=True, hide_index=True, key="main_editor_v3",
                               disabled=["코드", "종목명", "수익률", "상태"])
    
    if st.button("💾 데이터 및 메모 저장"):
        st.session_state.stocks = edited_df[["코드", "수량", "매수단가", "손절가", "매매메모"]]
        st.rerun()

    # 5. 상세 분석
    st.divider()
    sel_name = st.selectbox("🎯 분석할 종목 선택", list(analysis_data.keys()))
    if sel_name in analysis_data:
        target = analysis_data[sel_name]
        c1, c2 = st.columns(2)
        with c1:
            st.info(f"### {sel_name}")
            st.write(f"현재가: **{target['curr']:,.0f}원** / 손절가: **{target['stop']:,.0f}원**")
            st.write(f"나의 메모: {target['memo']}")
        with c2:
            tab1, tab2 = st.tabs(["📉 차트", "👥 수급"])
            with tab1:
                p_df = pd.DataFrame(index=target['df'].index)
                p_df['주가'] = target['df']['Close'].values
                p_df['손절선'] = target['stop']
                st.line_chart(p_df)
            with tab2:
                if target['code'].isdigit():
                    try:
                        end = datetime.now().strftime("%Y%m%d"); start = (datetime.now() - timedelta(days=30)).strftime("%Y%m%d")
                        inv = stock.get_market_net_purchases_of_equities_by_ticker(start, end, target['code'])
                        inv['외인누적'] = inv['외국인'].cumsum(); inv['기관누적'] = inv['기관합계'].cumsum()
                        st.line_chart(inv[['외인누적', '기관누적']])
                    except: st.write("수급 데이터 없음")

# 6. 오늘의 추천주 (에러 처리 및 로딩 최적화)
st.divider()
st.subheader("🚀 오늘의 추천주 (신고가 돌파)")
try:
    with st.spinner("최신 시장 데이터 스캔 중..."):
        recos = get_recommendations()
        if recos:
            cols = st.columns(len(recos))
            for i, r in enumerate(recos):
                with cols[i]:
                    st.success(f"**{r['이름']}**")
                    is_added = r['코드'] in st.session_state.stocks['코드'].values
                    if is_added:
                        st.button("이미 추가됨", key=f"rec_{r['코드']}", disabled=True)
                    else:
                        if st.button("추가", key=f"rec_{r['코드']}"):
                            new_reco = pd.DataFrame([{"코드": r['코드'], "수량": 10, "매수단가": r['현재가'], "손절가": r['전고점'], "매매메모": "추천주 추가"}])
                            st.session_state.stocks = pd.concat([st.session_state.stocks, new_reco], ignore_index=True)
                            st.rerun()
        else:
            st.info("현재 돌파 조건을 만족하는 주도주가 없습니다.")
except Exception as e:
    st.warning(f"추천주 스캔 중 일시적인 오류가 발생했습니다. 잠시 후 다시 시도해 주세요. (사유: {e})")
