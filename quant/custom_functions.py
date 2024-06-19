import mojito
from pykis import *
from typing import Dict
from collections import defaultdict
from prettytable import PrettyTable
import copy
import numpy as np
import mojito
import pprint

def adjustRebalancing(kis:PyKis, balance:KisAccountBalance, weightDict:Dict[str, Dict], bullet=None):
    # rebalancing ratio가 1인지 체크
    totalRatio = 0
    n = 0
    for ticker in weightDict:
        totalRatio += weightDict[ticker]["ratio"]
        if weightDict[ticker]["name"] == "현금":
            pass
        elif weightDict[ticker]["name"] != kis.stock(str(ticker)).name:
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
        if ticker == "cash":
            stock = "cash"
            price = 1
        else :
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
        try :
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
                print(f"* 매도 필요 수량: [{ticker} | {weightDict[ticker]['name']}] \t ({doc['order']}개) 금액: {int(priceInfo[idx] * doc['order']):,}원")
        except:
            pass

    cash = 0
    for ticker in tickerList:
        if ticker not in taken:
            idx = tickerIndexDict[ticker]
            doc = {
                "ticker" : ticker,
                "order" : int(bestCountList[idx]),
                "price" : int(priceInfo[idx])
            }
            if ticker == "cash":
                cash = priceInfo[idx] * int(bestCountList[idx])
            orderList.append(doc)
            taken.append(ticker)
            if doc['order'] > 0:
                print(f"* 추가 매수 필요 수량: [{ticker} | {weightDict[ticker]['name']}] \t (+{doc['order']}개) 금액: {int(priceInfo[idx] * doc['order']):,}원")
    print("")
    if cash > 0:
        print(f"* 구매시 예수금 변화 : {balance.dnca_tot_amt:,}원 -> {int(bestDiff) + cash:,}원 ")
    else :
        print(f"* 구매시 예수금 변화 : {balance.dnca_tot_amt:,}원 -> {int(bestDiff):,}원 ")
    return orderList


def adjustRebalancingUS(blanceDict:dict, weightDict:Dict[str, Dict], bullet=None):
    # rebalancing ratio가 1인지 체크
    totalRatio = 0
    n = 0
    maxTicker = None
    maxRatio = 0.0
    for ticker in weightDict:
        totalRatio += weightDict[ticker]["ratio"]
        if weightDict[ticker]["ratio"] >= maxRatio:
            maxTicker = ticker
            maxRatio = weightDict[ticker]["ratio"]
        n+=1
    if totalRatio != 1 :
        if (1 - totalRatio) < 0.01 :
            weightDict[maxTicker]["ratio"] += (1 - totalRatio)
        else :
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
        deposit = blanceDict["summary"]['evaluateTotalPrice'] # 평가금
    else :
        deposit = bullet

    totalResidual = 0
    for i,ticker in enumerate(tickerList):
        if "price" not in weightDict[ticker]:
            raise Exception(f"[ERROR] (해외) 현재가 정보가 없음. {ticker}")
        price = weightDict[ticker]["price"]
        if ticker == "cash":
            price = 1.0
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
            f'{int(bestTotalPriceList[idx]):,}달러',
            f'{int(priceInfo[idx]):,}달러',
            f'{weightDict[ticker]["ratio"] * 100:.2f}%',
            f'{bestRatioList[idx] * 100:.2f}%',
            f'{(bestRatioList[idx] - weightDict[ticker]["ratio"]) * 100:.2f}%'
        ])
    print(table)


    orderList = []
    taken = []
    for ticker in blanceDict["stock"]:
        idx = tickerIndexDict[ticker]

        doc = {
            "ticker" : ticker,
            "order" : int(bestCountList[idx] - blanceDict["stock"][ticker]["cnt"]),
            "price" : int(priceInfo[idx])
        }
        taken.append(ticker)
        orderList.append(doc)

        if doc['order'] > 0:
            print(f"* 추가 매수 필요 수량: [{ticker} | {weightDict[ticker]['name']}] \t (+{doc['order']}개) 금액: {int(priceInfo[idx] * doc['order']):,} 달러")
        else :
            print(f"* 매도 필요 수량: [{ticker} | {weightDict[ticker]['name']}] \t ({doc['order']}개) 금액: {int(priceInfo[idx] * doc['order']):,} 달러")

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
    print(f"* 구매시 예수금 변화 : {blanceDict['summary']['available']:,}달러 -> {int(bestDiff):,}달러 ")
    return orderList

'''
매수 
'''
def orderStock(account, ticker, count, orderPrice=0):
    print(f"*매수 {ticker}, qty={count}, orderPrice={orderPrice} (0일경우 시장가)")
    if orderPrice == 0: # 시장가
        return account.buy(ticker, qty=count, unpr=0, dvsn='시장가')
    else :
        return account.buy(ticker, qty=count, unpr=orderPrice)
'''
매도
'''
def sellStock(account, ticker, count, sellPrice=0):
    print(f"*매도 {ticker}, qty={count}, sellPrice={sellPrice} (0일경우 시장가)")
    if sellPrice == 0: # 시장가
        return account.sell(ticker, qty=count, unpr=0, dvsn='시장가')
    else :
        return account.sell(ticker, qty=count, unpr=sellPrice)



'''
해외 매수 
'''
def orderStockUS(account:mojito.KoreaInvestment, ticker, count, orderPrice=0):
    print(f"*매수 {ticker}, qty={count}, orderPrice={orderPrice} (0일경우 시장가)")
    if orderPrice == 0: # 시장가
        fetchPrice = account.fetch_price(ticker)
        if 'last' in fetchPrice['output'] and fetchPrice['output']['last'] != "" :
            currentPrice = int(round(float(fetchPrice['output']['last'])))
            print(f"조회시점 현재 가격 : {currentPrice}")
            return pprint.pprint(account.create_limit_buy_order(symbol=ticker, price=currentPrice, quantity=count))
        else :
            return -1
    else :
        return pprint.pprint(account.create_limit_buy_order(symbol=ticker, price=orderPrice, quantity=count))
'''
매도
'''
def sellStockUS(account:mojito.KoreaInvestment, ticker, count, sellPrice=0):
    print(f"*매도 {ticker}, qty={count}, sellPrice={sellPrice} (0일경우 시장가)")
    if sellPrice == 0: # 시장가
        fetchPrice = account.fetch_price(ticker)
        if 'last' in fetchPrice['output'] and fetchPrice['output']['last'] != "":
            currentPrice = int(round(float(fetchPrice['output']['last'])))
            print(f"조회시점 현재 가격 : {currentPrice}")
            return pprint.pprint(account.create_limit_sell_order(symbol=ticker, price=currentPrice, quantity=count))
        else :
            return -1
    else :
        return pprint.pprint(account.create_limit_sell_order(symbol=ticker, price=sellPrice, quantity=count))