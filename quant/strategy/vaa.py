from quant.quant_functions import *
from quant.custom_logger import *
from prettytable import PrettyTable

'''
1. 공격자산, 수비자산 설정.

공격자산 : VOO(미국주식), VEA(선진국 주식), EEM(이머징 주식), AGG(미국 총채권)

수비자산 : LQD(미국 회사채), SHY(미국 단기국채), IEF(미국 중기국채)

2. 모멘텀 스코어를 구한다.

`모멘텀 = (현재 주가 / n개월 전 주가) - 1`

(최근 1개월 수익률x12) + (최근 3개월 수익률x4) + (최근 6개월 수익률x2) + (최근 12개월 수익률x1)

3. 공격자산 4개 모멘텀 스코어가 전부 0 이상일 경우 가장 모멘텀스코어가 높은 공격자산에 올인

4. 공격자산 중 하나라도 모멘텀스코어가 0 이하일 경우 가장 모멘텀스코어가 높은 수비자산에 올인

'''
class Vaa:
    def __init__(self, logger:CustomLogger, startDate, endDate=None, addCash=True):
        self.logger = logger
        self.startDate = startDate# 수집 시작 날짜
        self.endDate = endDate
        self.vaaData:pd.DataFrame = pd.DataFrame()
        self.vaaDataWithCash = None
        self.target = None # 선택 ETF

        self.vaaCol = ['VOO', "VEA", "EEM", "AGG", "LQD", "SHY", "IEF"]
        self.vaaAttack = ['VOO', "VEA", "EEM", "AGG"]
        self.vaaDefense = ["LQD", "SHY", "IEF"]

        self.loadDataSet()


        if addCash:
            self.vaaCol.append("cash")
            self.vaaDefense.append("cash")
            self.vaaData.loc[:,"cash"] = 1
    
    def loadDataSet(self):
        # 공격형 자산
        VOO = getCloseData("VOO", self.startDate, self.endDate) # VOO(미국주식)
        VEA = getCloseData("VEA", self.startDate, self.endDate) # VEA(선진국 주식)
        EEM = getCloseData("EEM", self.startDate, self.endDate) # EEM(신흥국 주식)
        AGG = getCloseData("AGG", self.startDate, self.endDate) #AGG(미국 총채권)
        
        #수비자산
        LQD = getCloseData("LQD", self.startDate, self.endDate) #LQD(미국 회사채)
        SHY = getCloseData("SHY", self.startDate, self.endDate) #SHY(미국 단기국채)
        IEF = getCloseData("IEF", self.startDate, self.endDate) #IEF(미국 중기국채)

        self.vaaData = pd.concat([VOO, VEA, EEM, AGG, LQD, SHY, IEF], axis=1)
        self.vaaData.columns = self.vaaCol
        self.logger.info("=" * 25 + "[VAA] " + "=" * 25)
        self.logger.info(f"* (VAA) Completed to load Data set")

    def getVAAWeight(self):
        # 모멘텀 스코어를 구하기
        # (최근 1개월 수익률x12) + (최근 3개월 수익률x4) + (최근 6개월 수익률x2) + (최근 12개월 수익률x1)
        rebalDate = getRebalancingDate(self.vaaData)
        vaaDataOnRebalDate = self.vaaData.loc[rebalDate]

        momentum1 = vaaDataOnRebalDate / vaaDataOnRebalDate.shift(1) - 1
        momentum3 = vaaDataOnRebalDate / vaaDataOnRebalDate.shift(3) - 1
        momentum6 = vaaDataOnRebalDate / vaaDataOnRebalDate.shift(6) - 1
        momentum12 = vaaDataOnRebalDate / vaaDataOnRebalDate.shift(12) - 1

        momentumScore = 12*momentum1 + 4*momentum3 + 2*momentum6 + momentum12
        momentumScore.dropna(inplace=True)
        self.printWeightAsTable(momentumScore.round(2), f"* (VAA) 모멘텀 스코어")

        # 공격자산 4개 모멘텀 스코어가 전부 0 초과일 경우 가장 모멘텀스코어가 높은 공격자산에 몰빵
        # 공격자산 중 하나라도 모멘텀스코어가 0 이하일 경우 가장 모멘텀스코어가 높은 수비자산에 몰빵
        isAttack = (momentumScore[self.vaaAttack] > 0).all(axis=1)
        try:
            if isAttack[-1]:
                self.logger.info(f"* (VAA) 공격 자산 선택.")
            else:
                self.logger.info("* (VAA) 수비 자산 선택.")
        except:
            pass
        vaaWeight = momentumScore.apply(self.applyGetVAAWegiht, axis=1, args=(isAttack,))

        self.target = [(vaaWeight.iloc[-1].idxmax(), 1.0)]
        self.logger.info(f'* (VAA) [{vaaWeight.index[-1].strftime("%Y-%m-%d")} 기준] --->> "{self.target}" 선택\n')
        return vaaWeight

    def applyGetVAAWegiht(self, row, isAttack):
        vaaAttack = ['VOO', "VEA", "EEM", "AGG"]
        vaaDefense = ["LQD", "SHY", "IEF", "cash"]

        if isAttack[row.name]:
            # 공격자산 중 가장 모멘텀 스코어가 높은 종목에 몰빵
            return pd.Series(row.index == row[vaaAttack].idxmax(), index=row.index, name=row.name).astype(int)

        # 수비자산 중 가장 모멘텀스코어가 높은 종목에 몰빵
        return pd.Series(row.index == row[vaaDefense].idxmax(), index=row.index, name=row.name).astype(int)

    def printWeightAsTable(self, df, frontText=None):
        table = PrettyTable(field_names= ["투자 기준일"] + self.vaaCol,
            align='r',
        )
        lastDay = df.index[-1]
        rowVal = [str(lastDay)] + df.loc[lastDay].tolist()

        table.add_row(rowVal)
        if frontText:
            self.logger.info(frontText + "\n" + table.get_string())
        else:
            self.logger.info("\n" + table.get_string())


