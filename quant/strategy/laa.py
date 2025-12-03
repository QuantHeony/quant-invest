from quant.quant_functions import *
from quant.custom_logger import *
from prettytable import PrettyTable
from fredapi import Fred           # 미국 경제 지표 (실업률, S&P500)
import pandas as pd
import datetime as dt
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import time

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
        # 실업률 정보 파싱 시작일 (12개월 이동평균 계산을 위해 충분한 과거 데이터 필요)
        observation_start = (self.endDate - relativedelta(months=25)).strftime('%Y-%m-01')

        # 데이터 가져오고 정리하기
        data = self.fred.get_series('unrate', observation_start=observation_start)
        data = pd.DataFrame(data)
        data.index.names = ['Date']
        data.columns = ['Unrate']

        # 12개월 이동평균 만들기
        data['12SMA'] = data['Unrate'].rolling(window=12).mean()

        # 디버깅: 조회된 데이터 확인
        self.logger.info(f"* (LAA) FRED API 조회 성공: {len(data)}개 데이터 조회됨 (시작일: {observation_start})")
        self.logger.info(f"* (LAA) 조회된 데이터 날짜 범위: {data.index.min()} ~ {data.index.max()}")
        self.logger.info(f"* (LAA) 최근 5개 데이터:\n{data.tail()}")

        # 가장 최근 실업률 데이터 찾기 (ROBUST)
        # 1달 전부터 시작해서 데이터가 있는 가장 최근 날짜 찾기
        tgt_date = None
        for months_back in range(1, 14):  # 최대 13개월 전까지 검색
            candidate_date = pd.Timestamp((self.endDate - relativedelta(months=months_back)).strftime('%Y-%m-01'))
            if candidate_date in data.index and pd.notna(data.loc[candidate_date, '12SMA']):
                tgt_date = candidate_date
                if months_back > 1:
                    self.logger.warning("*" * 60)
                    self.logger.warning(f"*** 최근 고용지표 조회: {tgt_date.strftime('%Y-%m-%d')} 기준으로 조회 ({months_back}개월 전)")
                    self.logger.warning("*" * 60)
                break

        if tgt_date is None:
            raise RuntimeError("unrateIsBad: 유효한 고용지표 데이터를 찾을 수 없습니다.")

        self.logger.info(f"* (LAA) 미국 실업율({round(data.loc[tgt_date,'Unrate'],3)}%) vs 12개월 실업율 이동평균({round(data.loc[tgt_date,'12SMA'],3)}%)")

        return data.loc[tgt_date,'Unrate'] >= data.loc[tgt_date,'12SMA']


    def sp500IsBad(self):
        # FRED API로 S&P 500 데이터 조회 (더 안정적)
        # 200일 이동평균 계산을 위해 충분한 과거 데이터 필요
        # 영업일 기준 200일 ≈ 10개월, 안전하게 2년 전부터 조회
        observation_start = (self.endDate - relativedelta(years=2)).strftime('%Y-%m-%d')

        try:
            # FRED에서 S&P 500 인덱스 조회
            self.logger.info(f"sp500IsBad: FRED API로 S&P500 데이터 조회 시작 (시작일: {observation_start})")
            data = self.fred.get_series('SP500', observation_start=observation_start)

            self.logger.info(f"sp500IsBad: 원본 데이터 타입: {type(data)}")
            self.logger.info(f"sp500IsBad: 원본 데이터 길이: {len(data)}")

            data = pd.DataFrame(data)
            data.index.names = ['Date']
            data.columns = ['Close']

            self.logger.info(f"sp500IsBad: FRED API 조회 성공 ({len(data)}개 데이터)")
            if len(data) > 0:
                self.logger.info(f"sp500IsBad: 날짜 범위: {data.index.min()} ~ {data.index.max()}")
                self.logger.info(f"sp500IsBad: 최근 5개 데이터:\n{data.tail()}")
            else:
                self.logger.error("sp500IsBad: 조회된 데이터가 0개입니다.")

        except Exception as e:
            self.logger.error(f"sp500IsBad: FRED API 조회 실패: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            raise RuntimeError(f"sp500IsBad: S&P500 데이터 조회 실패 - {e}")

        if data.empty:
            raise RuntimeError("sp500IsBad: S&P500 데이터가 비어있습니다.")

        # NaN 값 처리: 이전 값으로 채우기 (forward fill)
        data['Close'] = data['Close'].ffill()

        # NaN을 제거한 유효한 데이터 개수 확인
        valid_count = data['Close'].notna().sum()
        self.logger.info(f"sp500IsBad: NaN 제거 후 유효 데이터 개수: {valid_count}")

        if valid_count < 200:
            raise RuntimeError(f"sp500IsBad: 유효한 데이터가 부족합니다 ({valid_count}개, 최소 200개 필요)")

        # 200일 이동평균 만들기
        data['200SMA'] = data['Close'].rolling(window=200, min_periods=200).mean()

        self.logger.info(f"sp500IsBad: 200일 이동평균 계산 완료")
        self.logger.info(f"sp500IsBad: 전체 데이터 개수: {len(data)}")
        self.logger.info(f"sp500IsBad: NaN이 아닌 200SMA 개수: {data['200SMA'].notna().sum()}")

        # 200일 이동평균이 유효한 데이터만 필터링
        valid_data = data[pd.notna(data['200SMA'])]

        if valid_data.empty:
            self.logger.error("sp500IsBad: 200일 이동평균이 계산된 데이터가 없습니다.")
            self.logger.error(f"sp500IsBad: 전체 데이터:\n{data}")
            raise RuntimeError("sp500IsBad: 200일 이동평균을 계산할 수 없습니다. 데이터가 부족합니다. (최소 200개 일별 데이터 필요)")

        # 가장 최근 유효한 데이터 사용 (지난 달 말일 근처)
        latest_date = valid_data.index.max()
        first_day_of_month = dt.datetime(self.endDate.year, self.endDate.month, day=1).date()
        last_day_of_prev_month = (first_day_of_month - relativedelta(days=1))

        self.logger.info(f"sp500IsBad: 가장 최근 유효 데이터: {latest_date}")
        self.logger.info(f"sp500IsBad: 목표 날짜(지난달 말일): {last_day_of_prev_month}")

        # 지난 달 말일 이전의 가장 최근 데이터 사용
        target_data = valid_data[valid_data.index <= pd.Timestamp(last_day_of_prev_month)]

        if target_data.empty:
            # 지난달 말일 데이터가 없으면 그냥 가장 최근 데이터 사용
            self.logger.warning(f"sp500IsBad: 지난달 말일 이전 데이터 없음, 최신 데이터 사용: {latest_date}")
            target_date = latest_date
        else:
            target_date = target_data.index.max()
            days_diff = (last_day_of_prev_month - target_date.date()).days
            if days_diff > 0:
                self.logger.warning(f"sp500IsBad: 최근 데이터 조회 - {target_date.strftime('%Y-%m-%d')} 기준 ({days_diff}일 전)")

        self.logger.info(f"sp500IsBad: 선택된 날짜: {target_date}")

        close_price = data.loc[target_date, 'Close']
        sma_200 = data.loc[target_date, '200SMA']

        self.logger.info(f"* (LAA) S&P 200일 이동 평균({round(sma_200, 2)}) vs 종가({round(close_price, 2)})")

        return sma_200 >= close_price



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
