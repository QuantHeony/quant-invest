import time
from datetime import datetime, timedelta
from custom_logger import CustomLogger
from strategy.vaa import Vaa
from strategy.modified_dual_momentum import ModifiedDualMomentum
from strategy.laa import Laa
from prettytable import PrettyTable
import pykis
from custom_functions import *


with open("../hts.txt", "r") as f:
    for line in f:
        key, value = line.strip().split(':')

        if key == 'APPKEY':
            APP_KEY = value
        elif key == 'APPSECRET':
            APP_SECRET = value
        elif key == 'ACCOUNTNO':
            ACCOUNT_NO = value

'''
khk strategy -> 변경 

1. VAA 공격형 - 33.4%
2. LAA - 33.3%
3. 변형 듀얼 모멘텀 - 33.3%
'''

khkStrategy = {
    'VAA' : {
        "target" : None,
        "ratio" : 0.334
    },
    'LAA' : {
        "target" : None,
        "ratio" : 0.333
    },
    'MODIFIED_DUAL' : {
        "target" : None,
        "ratio" : 0.333
    }
}

FRED_API_KEY = '3f3d80667b222b9928b43d97abc7642c'
if __name__ == "__main__":
    testTimeLabel:str = time.strftime("%m%d_%H%M%S", time.localtime())
    logger = CustomLogger(testTimeLabel, f"log/{testTimeLabel}.txt")

    today = datetime.now()
    startDate = today - timedelta(days=365)
    todayStr = today.strftime("%Y-%m-%d")
    startDateStr = startDate.strftime("%Y-%m-%d")

    # VOO
    vaa = Vaa(logger, startDateStr, todayStr)
    vaa.getVAAWeight()
    khkStrategy["VAA"]["target"] = vaa.target

    # LAA
    laa = Laa(logger, FRED_API_KEY, todayStr)
    laa.pickTargets()
    khkStrategy["LAA"]["target"] = laa.target

    # Modified Dual Momentum
    modifiedDualM = ModifiedDualMomentum(logger, todayStr)
    modifiedDualM.pickTarget()
    khkStrategy["MODIFIED_DUAL"]["target"] = modifiedDualM.target


    # TODO. 주문시 체크!
    ORDER_FLAG = False

    PORTFOLIO_DICT = {}

    cnt = 0
    ratioValid = 0
    for strategy in khkStrategy:
        ratio = khkStrategy[strategy]["ratio"]
        targetList = khkStrategy[strategy]["target"]
        targetRatioValid = 0
        for ticker, r in targetList:
            if ticker not in PORTFOLIO_DICT:
                PORTFOLIO_DICT[ticker] = {
                    "name" : None,
                    "ratio" : None,
                    "cumRatio" : r
                }
            else:
                PORTFOLIO_DICT[ticker]["cumRatio"] += r
            targetRatioValid += r
        if targetRatioValid != 1:
            logger.info(f"[ERROR] 전략 비율 확인 필요 (전략명:{strategy}|비율 합:{targetRatioValid}")
            raise Exception(f"[ERROR] 전략 비율 확인 필요 (전략명:{strategy}|비율 합:{targetRatioValid}")
        ratioValid += ratio
        cnt += 1
    if ratioValid != 1:
        logger.info(f"[ERROR] 포트폴리오 비율 확인 필요 (비율 합:{ratioValid})")


    logger.info("* 포트폴리오 티커별 목표 보유 비율")
    for ticker in PORTFOLIO_DICT:
        PORTFOLIO_DICT[ticker]["ratio"] = round(PORTFOLIO_DICT[ticker]["cumRatio"] / cnt, 3)
        logger.info(f"* {ticker} \t" + "-" * 20 + f"{round(PORTFOLIO_DICT[ticker]['ratio'] * 100,1)} %")

    #
    # kis = PyKis(
    #     appkey=APP_KEY,
    #     appsecret=APP_SECRET,
    #     virtual_account=False, # 가상 계좌 여부
    #     realtime=True # 실시간 조회 비활성화
    # )
    #
    # KEY_INFO = {
    #     "appkey" : APP_KEY,
    #     "appsecret" : APP_SECRET
    # }
    #
    # ACCOUNT_INFO = {
    #     "account_code": ACCOUNT_NO.split("-")[0],
    #     "product_code": ACCOUNT_NO.split("-")[1]
    # }
    # # API 객체 생성
    #
    # api = pykis.Api(key_info=KEY_INFO, account_info=ACCOUNT_INFO)
    # # DataFrame 형태로 해외 주식 잔고 반환
    # stocks_os = api.get_os_stock_balance()


    # 계좌 스코프를 생성한다.
    # account = kis.account(ACCOUNT_NO)
    # # 계좌 잔고를 조회한다.
    # balance = account.balance_all()
    # table = PrettyTable(field_names=[
    #     '상품번호',
    #     '상품명',
    #     '보유수량',
    #     '매입금액',
    #     '현재가',
    #     '평가손익율',
    #     '평가손익',
    # ],
    #     align='r',
    # )
    #
    # print(f"\n [현재 잔고 조회]")
    # print(f'예수금: {balance.dnca_tot_amt:,}원 평가금: {balance.tot_evlu_amt:,} 손익: {balance.evlu_pfls_smtl_amt:,}원')
    #
    # for stock in balance.stocks:
    #     table.add_row([
    #         stock.pdno,
    #         stock.prdt_name,
    #         f'{stock.hldg_qty:,}주',
    #         f'{stock.pchs_amt:,}원',
    #         f'{stock.prpr:,}원',
    #         f'{stock.evlu_pfls_rt:.2f}%',
    #         f'{stock.evlu_pfls_amt:,}원',
    #     ])
    #
    # print(table)
    #
    # # 리밸런싱 수량 확인
    # orderList = adjustRebalancing(kis, balance, PORTFOLIO_DICT)





