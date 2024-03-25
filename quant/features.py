import pykis
from pykis import *
from typing import Dict
from collections import defaultdict
from prettytable import PrettyTable
import copy
import numpy as np


def adjustRebalancing(kis:PyKis, balance:KisAccountBalance, weightDict:Dict[str, Dict], bullet=None):
    # rebalancing ratio가 1인지 체크
    totalRatio = 0
    n = 0
    for ticker in weightDict:
        totalRatio += weightDict[ticker]["ratio"]
        if weightDict[ticker]["name"] != kis.stock(str(ticker)).name:
            raise Exception(f"[ERROR] 이름 오류 {weightDict[ticker]['name']} != {kis.stock(str(ticker)).name}")
        n+=1
    if totalRatio != 1 :
        raise Exception(f"[ERROR] 비율의 합 1 != {totalRatio}")

    priceInfo = np.zeros(n) # 가격 리스트
    ratioList = np.zeros(n) # 비율 계산 리스트
    countList = np.zeros(n) # 구매 개수 리스트
    totalPriceList = np.zeros(n) # 소모 금액
    diffRatioList = np.zeros(n) # 개수를 정수화 하면서 잃은 비율
    tickerList = sorted(list(weightDict.keys())) # ticker 리스트
    tickerIndexDict = defaultdict(str) # key : ticker -> val: tickerList index
    for idx, ticker in enumerate(tickerList):
        tickerIndexDict[ticker] = idx

    # 정해진 구매액이 없다면 예수금을 전부 다 사용
    if not bullet:
        deposit = balance.tot_evlu_amt # 평가금
    else :
        deposit = bullet

    totalResidual = 0
    for i,ticker in enumerate(tickerList):
        stock = kis.stock(str(ticker))
        price = stock.price().stck_prpr
        count = int(deposit * weightDict[ticker]["ratio"] / price)
        # diffCountList[i] = (deposit * weightDict[ticker]["ratio"] / price) - count
        priceInfo[i] = price

        countList[i] = count
        ratioList[i] = (count * price) / deposit
        diffRatioList[i] = abs(weightDict[ticker]["ratio"] - ratioList[i])
        totalPriceList[i] = count * price
        totalResidual += abs(ratioList[i] - weightDict[ticker]["ratio"])

    bestCountList = copy.deepcopy(countList)
    bestRatioList = copy.deepcopy(ratioList)
    bestTotalPriceList = copy.deepcopy(totalPriceList)
    bestDiff = deposit - sum(totalPriceList)
    bestTotalResidual = totalResidual
    bestDiffRatioList = diffRatioList

    while True:
        toUpTickerIdx = np.argmax(bestDiffRatioList)
        tempDiff = priceInfo[toUpTickerIdx]
        if bestDiff > tempDiff :
            tempCountList = copy.deepcopy(bestCountList)
            tempCountList[toUpTickerIdx] += 1
            tempTotalPriceList = copy.deepcopy(totalPriceList)
            tempTotalPriceList[toUpTickerIdx] += priceInfo[toUpTickerIdx]
            tempSumPrice = sum(tempTotalPriceList)
            tempRatioList = np.zeros(n)
            tempDiffRatioList = np.zeros(n)
            tempTotalResidual = 0
            for idx, ticker in enumerate(tickerList):
                tempRatioList[idx] = tempTotalPriceList[idx]/tempSumPrice
                tempTotalResidual += abs(tempRatioList[idx] - weightDict[ticker]["ratio"])
                tempDiffRatioList[idx] = abs(weightDict[ticker]["ratio"] - tempRatioList[idx])
            if bestTotalResidual > tempTotalResidual:
                bestCountList = copy.deepcopy(tempCountList)
                bestRatioList = tempRatioList
                bestDiff = bestDiff - tempDiff
                bestTotalResidual = tempTotalResidual
                bestTotalPriceList = tempTotalPriceList
                bestDiffRatioList = tempDiffRatioList
            else:
                break
        else:
            break
    print("\n" + "=" * 30 + " Rebalancing Result " + "=" * 30 + "\n")

    table = PrettyTable(field_names=[
        '상품번호',
        '상품명',
        '리밸런싱 수량',
        '매입금액',
        '현재가',
        '목표 비율',
        '리밸런싱 비율',
        "비율 차이"
    ],
        align='r',
    )

    for idx, ticker in enumerate(tickerList):
        table.add_row([
            ticker,
            weightDict[ticker]["name"],
            f'{int(bestCountList[idx]):,}주',
            f'{int(bestTotalPriceList[idx]):,}원',
            f'{int(priceInfo[idx]):,}원',
            f'{weightDict[ticker]["ratio"] * 100:.2f}%',
            f'{bestRatioList[idx] * 100:.2f}%',
            f'{(bestRatioList[idx] - weightDict[ticker]["ratio"]) * 100:.2f}%'
        ])
    print(table)


    orderList = []
    taken = []
    for stock in balance.stocks:
        ticker = stock.pdno
        idx = tickerIndexDict[ticker]

        doc = {
            "ticker" : ticker,
            "order" : int(bestCountList[idx] - stock.hldg_qty),
            "price" : int(priceInfo[idx])
        }
        taken.append(ticker)
        orderList.append(doc)

        if doc['order'] > 0:
            print(f"* 추가 매수 필요 수량: [{ticker} | {weightDict[ticker]['name']}] \t (+{doc['order']}개) 금액: {int(priceInfo[idx] * doc['order']):,}원")
        else :
            print(f"* 매도 필요 수량: [{ticker} | {weightDict[ticker]['name']}] \t ({doc['order']}개) 금액: -{int(priceInfo[idx] * doc['order']):,}원")

    for ticker in tickerList:
        if ticker not in taken:
            idx = tickerIndexDict[ticker]
            doc = {
                "ticker" : ticker,
                "order" : int(bestCountList[idx]),
                "price" : int(priceInfo[idx])
            }
            orderList.append(doc)
            taken.append(ticker)
            if doc['order'] > 0:
                print(f"* 추가 매수 필요 수량: [{ticker} | {weightDict[ticker]['name']}] \t (+{doc['order']}개) 금액: {int(priceInfo[idx] * doc['order']):,}원")
    print("")
    print(f"* 구매시 예수금 변화 : {balance.dnca_tot_amt:,}원 -> {int(bestDiff):,}원 ")
    return orderList


'''
매수 
'''
def orderStock(account:pykis.KisAccountScope, ticker, count, orderPrice=0):
    print(f"*매수 {ticker}, qty={count}, orderPrice={orderPrice} (0일경우 시장가)")
    if orderPrice == 0: # 시장가
        return account.buy(ticker, qty=count, unpr=0, dvsn='시장가')
    else :
        return account.buy(ticker, qty=count, unpr=orderPrice)
'''
매도
'''
def sellStock(account:pykis.KisAccountScope, ticker, count, sellPrice=0):
    print(f"*매도 {ticker}, qty={count}, sellPrice={sellPrice} (0일경우 시장가)")
    if sellPrice == 0: # 시장가
        return account.sell(ticker, qty=count, unpr=0, dvsn='시장가')
    else :
        return account.sell(ticker, qty=count, unpr=sellPrice)
