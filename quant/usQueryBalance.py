import mojito

def getBalance(PORTFOLIO_DICT = None) -> dict:
    with open("../hts.txt", "r") as f:
        for line in f:
            key, value = line.strip().split(':')

            if key == 'APPKEY':
                APP_KEY = value
            elif key == 'APPSECRET':
                APP_SECRET = value
            elif key == 'ACCOUNTNO':
                ACCOUNT_NO = value

    BALANCE = {"stock": {},
               "dollar": {}}

    for exchange in ["나스닥", "아멕스"]:
        account = mojito.KoreaInvestment(
            api_key=APP_KEY,
            api_secret=APP_SECRET,
            acc_no=ACCOUNT_NO,
            exchange=exchange
        )
        balance = account.fetch_present_balance()
        ## PORTFOLIO_DICT을 업데이트 함
        if PORTFOLIO_DICT:
            for ticker in PORTFOLIO_DICT:
                if PORTFOLIO_DICT[ticker]["price"] == None:
                    priceRes = account.fetch_price(ticker)
                    if priceRes["msg_cd"] == 'MCA00000' and priceRes["output"]['last'] != "":
                        price = float(priceRes["output"]['last'])
                        PORTFOLIO_DICT[ticker]["price"] = price
                        PORTFOLIO_DICT[ticker]["exchange"] = exchange
        #########################################

        for i, bKey in enumerate(balance.keys()):
            # if i == 0 and 'msg1' in balance:
            #     print(f"\n, {'=' * 15} {balance['msg1']} {'=' * 15}")
            if bKey == 'output1':
                # print(f"\n# {'>' * 5} [보유 주식정보] {'<' * 5}\n")
                for idx, docData in enumerate(balance[bKey]):
                    ticker = docData['pdno']
                    if ticker in BALANCE["stock"]:
                        raise Exception(f"동일한 Ticker 값이 들어옴 {ticker}")
                    BALANCE["stock"][ticker] = {
                        "name" : docData['prdt_name'],
                        "cnt": float(docData['cblc_qty13']),
                        "currentUnitPrice": float(docData['ovrs_now_pric1']),
                        "boughtTotalPrice": float(docData['frcr_pchs_amt']),
                        "evaluateTotalPrice": float(docData['frcr_evlu_amt2']),
                        "exchange": exchange,
                        "profit" : float(docData['evlu_pfls_amt2'])
                    }

                    # print(f"# [{idx}] ({docData['pdno']}) {docData['prdt_name']}\n")
                    # print(f"\t* 보유 수량 : {docData['cblc_qty13']}")
                    # print(f"\t* 체결 기준 보유 수량 : {docData['ccld_qty_smtl1']}")
                    # print(f"\t* 주문 가능 수량 : {docData['ord_psbl_qty1']}\n")
                    #
                    # print(f"\t* 외화 매입 금액 : {docData['frcr_pchs_amt']}")
                    # print(f"\t* 외화 평가 금액 : {docData['frcr_evlu_amt2']}")
                    # print(f"\t* 외화 손익 금액 : {docData['evlu_pfls_amt2']}")
                    # print(f"\t* 손익율 : {docData['evlu_pfls_rt1']}")
                    # print(f"\t* 현재가: {docData['ovrs_now_pric1']}")
                    # print(f"\t* 매수 평균 단가: {docData['avg_unpr3']}\n")

            elif bKey == "output2":
                for idx, docData in enumerate(balance[bKey]):
                    if BALANCE["dollar"] == {}:
                        BALANCE["dollar"] = {
                            "available" : float(docData['frcr_dncl_amt_2']),
                            "exchangeRate" : float(docData['frst_bltn_exrt'])
                        }

                        # print(f"\n# {'>' * 5}  [보유 달러] {'<' * 5}\n")
                        # print(f"\t* 외화 보유액 : {docData['frcr_dncl_amt_2']}")
                        # print(f"\t* 최초 고시 환율(원) : {docData['frst_bltn_exrt']}")
                        # print(f"\t* 출금 가능 금액(원) : {docData['frcr_evlu_amt2']}")
                        # print(f"\t* 출금 가능 금액(달러) : {docData['frcr_drwg_psbl_amt_1']}")

            elif bKey == 'output3':
                # print(f"\n# {'>' * 5}  [총 평가 정보] {'<' * 5}\n")
                bData = balance[bKey]
                if "availableWon" not in BALANCE["dollar"]:
                    BALANCE["dollar"]["availableWon"] = float(bData['tot_dncl_amt'])
                # print(f"\t* 총 매입 금액 합계(원): {bData['pchs_amt_smtl_amt']}")
                # print(f"\t* 총 평가금 합계(원): {bData['evlu_amt_smtl_amt']}")
                # print(f"\t* 총 평가 손익 금액(달러): {bData['tot_evlu_pfls_amt']}")
                # print(f"\t* 총 예수금(원): {bData['tot_dncl_amt']}")
                # print(f"\t* 총 평가금(원): {bData['frcr_evlu_tota']}")
                # print(f"\t* 총 수익율: {bData['evlu_erng_rt1']}")
                # print(f"\t* 총 외화 잔고 합계: {bData['tot_frcr_cblc_smtl']}")
                # print(f"\t* 총 자산 금액: {bData['tot_asst_amt']}")
                # print(f"\t* 총 인출 가능 금액(원): {bData['tot_dncl_amt']}")
                # print(f"* : {}")
                # print(f"* : {}")
                # print(f"* : {}")
                # print(bData)

    totalEvaluateTotalPrice = 0
    availableBullet = 0
    totalProfit = 0
    print(f"\n, {'=' * 15} {'[해외 주식 잔고 조회]'} {'=' * 15}")
    for idx, ticker in enumerate(BALANCE["stock"]):
        d = BALANCE["stock"][ticker]
        print(f"\n# [{idx}] ({ticker}) {d['name']} {'<' * 5}")
        for key in BALANCE["stock"][ticker].keys():
            print(f"\t* {key}: {d[key]}")
            if key == "evaluateTotalPrice":
                totalEvaluateTotalPrice += d[key]
            elif key == "profit":
                totalProfit += d[key]

    print(f"\n, {'=' * 15} {'[잔고 보유 금액]'} {'=' * 15}")
    for key in BALANCE["dollar"].keys():
        d = BALANCE["dollar"]
        if key == "available":
            totalEvaluateTotalPrice += d[key]
        print(f"\t* {key}: {d[key]}")

    if BALANCE["dollar"]["availableWon"] > 0:
        availableBullet += int(round(BALANCE["dollar"]["availableWon"] / BALANCE["dollar"]["exchangeRate"],0))

    BALANCE["summary"] = {
        "available" : BALANCE["dollar"]["available"],
        "evaluateTotalPrice" : totalEvaluateTotalPrice,
        "availableBullet" : availableBullet,
        "currentProfit" : totalProfit
    }

    print(f"\n, {'=' * 15} [가용 총알(달러)] {'=' * 15}")
    for key in BALANCE["summary"].keys():
        print(f"\t* {key}: {BALANCE['summary'][key]}")

    return BALANCE