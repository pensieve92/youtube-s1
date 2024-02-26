import streamlit as st
from datetime import datetime, timedelta

from bokeh.layouts import gridplot, row
from bokeh.models import HoverTool, ColumnDataSource, FactorRange, Range1d
import FinanceDataReader as fdr
import talib
import math

st.set_page_config(layout="wide", page_title="My favorite stocks", page_icon="📈")

if not "initialized" in st.session_state:
    # 전체 종목 리스트 - all_stocks
    st.session_state.all_stocks = []
    # 사용자의 종목 리스트 - items_user_stocks
    st.session_state.user_stocks = ['TQQQ', 'GOOG', 'TSLA', 'BA', 'CVE', 'AAPL']
    # 사용자가 선택한 종목 리스트 - 최대 갯수가 6개
    st.session_state.user_stock6 = ['TQQQ', 'GOOG', 'TSLA', 'BA', 'CVE', 'AAPL']
    # TODO 필요한가?
    st.session_state.chart = None
    # 변수 초기화
    st.session_state.initialized = True


# ===================================================================
# ===================================================================
# 사이드 메뉴 - method
# selectbox에서 선택 이벤트
# deprecated
# def change_sel_stock():
#     print(st.session_state.sel_stock)

# 추가 클릭 이벤트
def add_to_user_stock():
    st.session_state.user_stocks.append(st.session_state.stock_value)
    # print(st.session_state.stock_value)


# user_stock 변경 이벤트
def change_user_stocks():
    st.session_state.user_stock6 = st.session_state.user_stock6_value
    # print(st.session_state.user_stock6_value)


# ===================================================================
# ===================================================================
# 사이드 메뉴 - template
with st.sidebar:
    # ==============================================================
    # 사이드 메뉴 - Row1
    col1, col2 = st.columns([3, 1])
    with col1:
        # selectbox를 변경할 때마다 다시 그리는데 값은 초기화 되지 않음
        st.selectbox(
            'Stocks',
            ['TQQQ', 'AAPL', 'FB', 'GOOG'],  # all_stocks
            key='stock_value',  # value
            # on_change=change_sel_stock # 사실상 필요 없는듯
        )
        # print('here')
    with col2:
        # 버튼 클릭할 때마다 다시 그리는데 값은 초기화 되지 않음
        add_btn = st.button('추가', on_click=add_to_user_stock)
        # print('here2')
    # ==============================================================
    # 사이드 메뉴 - Row2
    st.multiselect(
        'What are your favorite stock6',
        st.session_state.user_stocks,  # 리스트
        st.session_state.user_stock6,  # 선택된 리스트6
        on_change=change_user_stocks,
        key='user_stock6_value',
        max_selections=6
    )
    # ==============================================================
    # 사이드 메뉴 - Row3
    st.selectbox(
        'Stocks',
        ['일', '주', '월'],  # bong
        key='bong_value',  # value
    )

# ===================================================================
# ===================================================================
# 메인 화면 - method
import pandas as pd

from bokeh.plotting import figure, column


# 주식 데이터 조회 - 3년치 데이터
def load_stock_data(ticker):
    start = (datetime.today() - timedelta(365 * 3)).strftime("%Y-%m-%d")
    df = fdr.DataReader(symbol=ticker, start=start).reset_index()
    df['Date'] = pd.to_datetime(df["Date"])

    # 메인차트 - 이동 평균선
    df['MA5'] = talib.MA(df['Close'], 5)
    df['MA15'] = talib.MA(df['Close'], 15)
    df['MA60'] = talib.MA(df['Close'], 60)
    df['MA120'] = talib.MA(df['Close'], 120)

    # 메인차트 - 볼린저 밴드
    df['BBANDS_UPPER'], df['BBANDS_MIDDLE'], df['BBANDS_LOWER'] = talib.BBANDS(df["Close"], 20, 2)

    # 서브차트 - RSI
    df["RSI"] = talib.RSI(df.Close, timeperiod=14)

    # 서브차트 - macd
    df["MACD"], df["MACD_SIGNAL"], df["MACD_HIST"] = talib.MACD(df["Close"], fastperiod=12, slowperiod=26,
                                                                signalperiod=9)

    # TODO 주봉
    # df = fdr.DataReader(symbol='TQQQ', start=start)
    # week = df.resample('W').first().reset_index()
    # week['Date'] = pd.to_datetime(week["Date"])
    return df


def get_chart(df, ticker):
    TOOLS = ['pan', 'box_zoom', 'wheel_zoom', 'save', 'reset']

    p = figure(tools=TOOLS, width=600, height=300,
               active_drag="pan",
               active_scroll="wheel_zoom",
               title=f"{ticker} Candlestick without missing dates",
               background_fill_color="#efefef",
               )

    p.xaxis.major_label_orientation = 0.8  # radians
    p.x_range.range_padding = 0.05
    # map dataframe indices to date strings and use as label overrides
    p.xaxis.major_label_overrides = {i: date.strftime('%b %d') for i, date in zip(df.index, df["Date"])}
    # p.xaxis.major_label_overrides = {i: date.strftime('%Y-%m') if date.strftime('%d') == '02' else '' for i, date in zip(df.index, df["Date"])}
    # one tick per week (5 weekdays) - 주말 제거
    # p.xaxis.ticker = list(range(df.index[0], df.index[-1], 5))

    # 범위 지정
    range_start = len(df.index) - 110
    max_y_range = max(max(df['High'][range_start:]), max(df['Low'][range_start:])) * 1.1
    min_y_range = min(min(df['High'][range_start:]), min(df['Low'][range_start:])) * 0.9
    p.y_range = Range1d(min_y_range, max_y_range)
    p.x_range = Range1d(range_start, len(df.index) + 3)

    # 그래프별 source
    inc = df['Close'] > df['Open']
    dec = df['Open'] > df['Close']
    high_low_source = ColumnDataSource(data=dict(x=df.index, low=df['Low'], high=df['High']))
    plus_bong_source = ColumnDataSource(data=dict(x=df.index[inc], rsi=df['RSI'][inc], top=df['Close'][inc], bottom=df['Open'][inc], low=df['Low'][inc],high=df['High'][inc], date=df['Date'][inc], volume=df['Volume'][inc]))
    minus_bong_source = ColumnDataSource(data=dict(x=df.index[dec], rsi=df['RSI'][dec], top=df['Open'][dec], bottom=df['Close'][dec], low=df['Low'][dec],high=df['High'][dec], date=df['Date'][dec], volume=df['Volume'][dec]))

    # 캔들 - 고가/저가 그래프
    p.segment(x0='x', x1='x', y0='high', y1='low', color="black", source=high_low_source)

    # 캔들 - 음봉/양봉 그래프
    plus_bong = p.vbar(x='x', width=0.6, top='top', bottom='bottom', color='red', source=plus_bong_source)
    minus_bong = p.vbar(x='x', width=0.6, top='top', bottom='bottom', color="blue", source=minus_bong_source)

    # 이동 평균선 (5일, 15일, 60일, 120일)
    p.line(df.index, df['MA5'], color="green")
    p.line(df.index, df['MA15'], color="red")
    p.line(df.index, df['MA60'], color="purple")
    p.line(df.index, df['MA120'], color="orange")

    # 볼린저 밴드
    p.varea(x=df.index, y1=df['BBANDS_UPPER'], y2=df['BBANDS_LOWER'], color='lightblue', alpha=0.5)

    # 툴팁 추가
    p.add_tools(HoverTool(renderers=[minus_bong, plus_bong],
                          tooltips=[('Date', "@date{%F}"), ('시가', "@top"), ('고가', "@high"), ('저가', "@low"),
                                    ("종가", "@bottom"), ("거래량", "@volume{0.00a}"), ("RSI", "@rsi")],
                          formatters={"@date": "datetime"},
                          mode='vline'))

    # TODO 나중에 커스텀 툴팁 만들어야지
    # TOOLTIPS = """
    #     <div>
    #         <div>
    #             <span style="font-size: 17px; font-weight: bold;">$date</span>
    #             <span style="font-size: 15px; color: #966;">[$index]</span>
    #         </div>
    #         <div>
    #             <span style="font-size: 15px;">Location</span>
    #             <span style="font-size: 10px; color: #696;">($x, $y)</span>
    #         </div>
    #     </div>
    # """

    return p


def add_chart(df, main_chart):
    xaxis_overrides = {i: date.strftime('%b %d') for i, date in zip(df.index, df["Date"])}

    # ===================================================================
    # volume
    inc = df['Close'] > df['Open']
    dec = df['Open'] > df['Close']

    volume = figure(width=600, height=50, background_fill_color="#efefef", x_range=main_chart.x_range)

    plus_volume_source = ColumnDataSource(data=dict(x=df.index[inc], volume=df['Volume'][inc]))
    minus_volume_source = ColumnDataSource(data=dict(x=df.index[dec], volume=df['Volume'][dec]))

    volume.vbar(x='x', width=0.6, top='volume', bottom=0, color="red", source=plus_volume_source)
    volume.vbar(x='x', width=0.6, top='volume', bottom=0, color="blue", source=minus_volume_source)
    volume.xaxis.major_label_overrides = xaxis_overrides

    # ===================================================================
    # rsi
    rsi = figure(width=600, height=50, background_fill_color="#efefef", x_range=main_chart.x_range)
    rsi.line(df.index, df["RSI"], color="orange")
    rsi.xaxis.major_label_overrides = xaxis_overrides

    # ===================================================================
    # macd
    macd = figure(width=600, height=50, background_fill_color="#efefef", x_range=main_chart.x_range)
    macd.line(df.index, df["MACD"], color="orange")
    macd.line(df.index, df["MACD_SIGNAL"], color="blue")
    macd.line(df.index, df["MACD_HIST"], color="green")
    macd.xaxis.major_label_overrides = xaxis_overrides

    return gridplot([[column(children=[main_chart, volume, rsi, macd], sizing_mode="scale_width")]], toolbar_location=None)

def make_chart(ticker):
    print(ticker)
    df = load_stock_data(ticker)
    p = get_chart(df, ticker)
    return add_chart(df, p)

@st.cache_data
def main(user_stock6):
    len_stock6 = len(user_stock6)
    col_cut = math.ceil(len_stock6/2)

    if col_cut == 0:
        st.write("no item!")
    else:
        cols = st.columns(col_cut)
        for i in range(col_cut):
            col = cols[i]
            with col:
                st.write(user_stock6[i * 2])
                st.bokeh_chart(make_chart(user_stock6[i * 2]), use_container_width=True)
                if len_stock6 >= i * 2 + 2:
                    st.write(user_stock6[i * 2 + 1])
                    st.bokeh_chart(make_chart(user_stock6[i * 2 + 1]), use_container_width=True)

# ===================================================================
# ===================================================================
# 메인 화면 - template
if __name__ == '__main__':
    print('__main__')
    main(st.session_state.user_stock6)

# ===================================================================
# ===================================================================
# 스타일 스크립트
style = """
<style>

/* 사이드 메뉴 */
div[data-testid="stVerticalBlock"] div[data-testid="stHorizontalBlock"] div[data-testid="column"] { 
    display: flex;
    align-items: flex-end;
}
</style>
"""
st.markdown(style, unsafe_allow_html=True)
