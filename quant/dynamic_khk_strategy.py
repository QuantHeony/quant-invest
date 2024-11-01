import time
from datetime import datetime, timedelta
from custom_logger import CustomLogger
from strategy.vaa import Vaa
from strategy.modified_dual_momentum import ModifiedDualMomentum
from strategy.laa import Laa
import yfinance as yf
from custom_functions import *
from usQueryBalance import getBalance

#####
# TODO. 주문시 체크!
ORDER_FLAG = False
####


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
    startDate = today - timedelta(days=370)
    todayStr = today.strftime("%Y-%m-%d")
    startDateStr = startDate.strftime("%Y-%m-%d")

    # VAA
    vaa = Vaa(logger, startDateStr, todayStr)
    vaa.getVAAWeight()
    khkStrategy["VAA"]["target"] = vaa.target

    # LAA
    laa = Laa(logger, FRED_API_KEY, todayStr)
    laa.pickTargets()
    khkStrategy["LAA"]["target"] = laa.target

    # Dual Momentum
    # dualM = DualMomentum(logger, todayStr)
    # dualM.pickTarget()
    # khkStrategy["DUAL"]["target"] = dualM.target

    # Modified Dual Momentum
    modifiedDualM = ModifiedDualMomentum(logger, todayStr)
    modifiedDualM.pickTarget()
    khkStrategy["MODIFIED_DUAL"]["target"] = modifiedDualM.target

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
                    "exchange" : None, # 거래소 정보 getBalance 함수 필요
                    "price" : None,  # 현재가 getBalance 함수 필요
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
        etf = yf.Ticker(ticker)
        PORTFOLIO_DICT[ticker]["ratio"] = round(PORTFOLIO_DICT[ticker]["cumRatio"] / cnt, 3)
        PORTFOLIO_DICT[ticker]["name"] = etf.info["longName"]
        logger.info(f"* ({ticker}) {PORTFOLIO_DICT[ticker]['name']} \t" + "-" * 20 + f"{round(PORTFOLIO_DICT[ticker]['ratio'] * 100,2)} %")

    # 잔고 조회 및 PORTFOLIO_DICT 현재가 업데이트
    BALANCE = getBalance(PORTFOLIO_DICT)
    # 리밸런스 수량
    orderList = adjustRebalancingUS(BALANCE, PORTFOLIO_DICT)

    for exchange in ["나스닥", "아멕스"]:
        account = mojito.KoreaInvestment(
            api_key=APP_KEY,
            api_secret=APP_SECRET,
            acc_no=ACCOUNT_NO,
            exchange=exchange
        )
        balance = account.fetch_present_balance()

    # 먼저 팔고, 구매 한다.
    orderBuyList =[]
    ACCOUNT_DICT = {}
    if ORDER_FLAG:
        # 주문 or 매수
        for doc in orderList:
            ticker = doc["ticker"]
            cnt = doc["order"]
            price = doc["price"]
            if cnt == 0:
                pass
            elif cnt > 0:
                if ticker == "cash": pass
                orderBuyList.append([ticker, cnt, price])
            else:
                exchange = PORTFOLIO_DICT[ticker]["exchange"]
                if not exchange :
                    for exchange in ["나스닥", "아멕스"] :
                        account = mojito.KoreaInvestment(
                            api_key=APP_KEY,
                            api_secret=APP_SECRET,
                            acc_no=ACCOUNT_NO,
                            exchange=exchange
                        )
                        ACCOUNT_DICT[exchange] = account
                        if sellStockUS(account, ticker, -cnt, 0) != -1 : break;
                else :
                    if exchange not in ACCOUNT_DICT:
                        account = mojito.KoreaInvestment(
                            api_key=APP_KEY,
                            api_secret=APP_SECRET,
                            acc_no=ACCOUNT_NO,
                            exchange=exchange
                        )
                        ACCOUNT_DICT[exchange] = account
                    else :
                        account = ACCOUNT_DICT[exchange]
                    sellStockUS(account,ticker, -cnt, 0)

        for ticker, cnt, price in orderBuyList:
            exchange = PORTFOLIO_DICT[ticker]["exchange"]
            if not exchange:
                for exchange in ["나스닥", "아멕스"] :
                    account = mojito.KoreaInvestment(
                        api_key=APP_KEY,
                        api_secret=APP_SECRET,
                        acc_no=ACCOUNT_NO,
                        exchange=exchange
                    )
                    ACCOUNT_DICT[exchange] = account
                    if orderStockUS(account,ticker, cnt, 0) != -1 : break;
            else :
                if exchange not in ACCOUNT_DICT:
                    account = mojito.KoreaInvestment(
                        api_key=APP_KEY,
                        api_secret=APP_SECRET,
                        acc_no=ACCOUNT_NO,
                        exchange=exchange
                    )
                    ACCOUNT_DICT[exchange] = account
                else :
                    account = ACCOUNT_DICT[exchange]
                orderStockUS(account,ticker, cnt, 0)
