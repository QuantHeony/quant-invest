from quant.quant_functions import *
from quant.custom_logger import *
from prettytable import PrettyTable
from fredapi import Fred           # 미국 실업률 지표
import yfinance as yf              # S&P500 지표
import pandas as pd
import datetime as dt
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

'''
1) 고정자산 75%(각 25%)
IWD(미국 대형가치주), 금(GLD), 미국 중기국채(IEF)

2) 타이밍 자산 25%   
SHY(미국 단기국채) : 미국 S&P 지수 가격이 200일 이동평균선보다 낮고 미국실업률이 12개월 이동평균보다 높은 경우
QQQ(나스닥): 이외 경우  
'''

class Laa():
    def __init__(self, logger:CustomLogger, FRED_API_KEY, endDate=None):
        self.fred = Fred(api_key=FRED_API_KEY)
        self.logger = logger
        self.target = None
        if not endDate:
            today = datetime.now()
            self.endDate = today
        else:
            self.endDate = datetime.strptime(endDate, "%Y-%m-%d")

    def unrateIsBad(self):
        # 실업률 정보 파싱 시작일
        observation_start = (self.endDate - relativedelta(months=13)).strftime('%Y-%m-01')

        # 데이터 가져오고 정리하기
        data = self.fred.get_series('unrate', observation_start=observation_start)
        data = pd.DataFrame(data)
        data.index.names = ['Date']
        data.columns = ['Unrate']

        # 12개월 이동평균 만들기
        data['12SMA'] = data['Unrate'].rolling(window=12).mean()

        # 지난달 실업률을 검색할 기준일
        tgt_date = (self.endDate - relativedelta(months=1)).strftime('%Y-%m-01')
        if tgt_date not in data.index:
            tgt_date = (self.endDate - relativedelta(months=2)).strftime('%Y-%m-01')
            self.logger.warning("*" * 60)
            self.logger.warning(f"*** 지난달 1일 고용지표 조회 실패, {tgt_date} 기준으로 조회")
            self.logger.warning("*" * 60)

        self.logger.info(f"* (LAA) 미국 실업율({round(data.loc[tgt_date,'Unrate'],3)}%) vs 12개월 실업율 이동평균({round(data.loc[tgt_date,'12SMA'],3)}%)")

        return data.loc[tgt_date,'Unrate'] >= data.loc[tgt_date,'12SMA']

    def sp500IsBad(self):
        # S&P500 정보 파싱 시작일
        start = (self.endDate - relativedelta(months=13)).strftime('%Y-%m-%d')

        # S&P500 지수 자료에 엑세스하고 시작일부터 현재까지의 자료를 가져옵니다.
        sp500 = yf.Ticker('^GSPC')
        data = sp500.history(start=start, auto_adjust = False)
        data = pd.DataFrame(data)

        # 200일 이동평균 만들기
        data['200SMA'] = data['Close'].rolling(window=200).mean()

        # 빈 날짜를 새로 만들고 데이터 채우기
        data = data.asfreq(freq='D', method='ffill')

        # 지난 달 말일
        first_day = dt.datetime(self.endDate.year, self.endDate.month, day=1).date()
        last_day = (first_day - relativedelta(days=1)).strftime('%Y-%m-%d')

        self.logger.info(f"* (LAA) S&P 200일 이동 평균({round(data.loc[last_day,'200SMA'],2)}) vs 종가({round(data.loc[last_day,'Close'],2)})")

        return data.loc[last_day,'200SMA'] >= data.loc[last_day,'Close']

    def pickTargets(self):
        self.logger.info("=" * 25 + "[LAA] " + "=" * 25)
        # 지속적으로 투자하는 종목들 리스트
        self.target = [('IWD', 0.25), ('GLD', 0.25), ('IEF', 0.25)]

        # 투자 자산 선정
        if self.unrateIsBad() and self.sp500IsBad():
            self.target.append(('SHY', 0.25))

        else :
            self.target.append(('QQQ', 0.25))

        self.logger.info(f'* (LAA) [{self.endDate.strftime("%Y-%m-%d")} 기준] --->> "{self.target}" 선택\n')
        return self.target
