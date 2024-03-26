from prettytable import PrettyTable
from pykis import *
from features import *

with open("../hts-isa.txt", "r") as f:
    for line in f:
        key, value = line.strip().split(':')

        if key == 'APPKEY':
            APP_KEY = value
        elif key == 'APPSECRET':
            APP_SECRET = value
        elif key == 'ACCOUNTNO':
            ACCOUNT_NO = value


# 11 To 4
KoreanAllWeather11To4 = {
    '360750' : {
        "name" : "TIGER 미국S&P500",
        "ratio" : 0.2
    },
    '294400' : {
        "name" : "KOSEF 200TR",
        "ratio" : 0.2
    },
    '132030' : {
        "name" : "KODEX 골드선물(H)",
        "ratio" : 0.15
    },
    '148070' :  {
        "name" : "KOSEF 국고채10년",
        "ratio" : 0.225
    },
    '305080' : {
        "name" : "TIGER 미국채10년선물",
        "ratio" : 0.225
    }
}

if __name__ == "__main__":
    kis = PyKis(
        appkey=APP_KEY,
        appsecret=APP_SECRET,
        virtual_account=False, # 가상 계좌 여부
        realtime=True # 실시간 조회 비활성화
    )
    # 계좌 스코프를 생성한다.
    account = kis.account(ACCOUNT_NO)
    # 계좌 잔고를 조회한다.
    balance = account.balance_all()
    table = PrettyTable(field_names=[
        '상품번호',
        '상품명',
        '보유수량',
        '매입금액',
        '현재가',
        '평가손익율',
        '평가손익',
    ],
        align='r',
    )

    print(f"\n [현재 잔고 조회]")

    print(f'예수금: {balance.dnca_tot_amt:,}원 평가금: {balance.tot_evlu_amt:,} 손익: {balance.evlu_pfls_smtl_amt:,}원')

    for stock in balance.stocks:
        table.add_row([
            stock.pdno,
            stock.prdt_name,
            f'{stock.hldg_qty:,}주',
            f'{stock.pchs_amt:,}원',
            f'{stock.prpr:,}원',
            f'{stock.evlu_pfls_rt:.2f}%',
            f'{stock.evlu_pfls_amt:,}원',
        ])

    print(table)

    # 리밸런싱 수량 확인
    orderList = adjustRebalancing(kis, balance, KoreanAllWeather11To4)

    # TODO. 주문시 체크!
    ORDER_FLAG = False
    # 먼저 팔고, 구매 한다.
    orderBuyList =[]
    if ORDER_FLAG:
        # 주문 or 매수
        for doc in orderList:
            ticker = doc["ticker"]
            cnt = doc["order"]
            price = doc["price"]

            if cnt > 0:
                orderBuyList.append([ticker, cnt, price])
            else:
                sellStock(account,ticker, cnt, price)

        for ticker, cnt, price in orderBuyList:
            orderStock(account,ticker, cnt, price)



    # FM 대로 사용 다한 임시 토큰은 삭제함.
    if kis.client.token:
        kis.client.token.discard()
