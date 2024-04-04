from datetime import datetime, timedelta
from quant.quant_functions import *
from quant.custom_logger import *
from prettytable import PrettyTable

''' 
VOO(미국 주식), BIL(미국 초단기 채권), 선진국 주식(EFA)
* 안전자산: SHY(미국 단기국채), IEF(미국 중기국채), 미국 장기국채(TLT), 미국 물가연동채(TIP), 미국 회사채(LQD), 미국 하이일드(HYG), 국제 채권(BWX), 개도국 채권(EMB) 

12개월 수익률 확인 
* VOO > BIL
    * VOO와 EFA중 더 큰것 선택
* VOO < BIL
    * 8개 채권 중 6개월간 수익이 높았던 3개 ETF 확인
    * 수익이 0이하는 -> 현금전환
    * 따라서 현금 비중은 0, 33, 66, 100% 
    
'''

class ModifiedDualMomentum:
    def __init__(self, logger:CustomLogger, endDate=None):
        self.mDualMDefenseCumReturn = None
        self.mDualMAttackCumReturn = None
        self.target = None # 선택 ETF
        self.logger = logger
        if not endDate:
            today = datetime.now()
            self.endDate = today
        else:
            self.endDate = datetime.strptime(endDate, "%Y-%m-%d")
        self.aYearAgo = (self.endDate - timedelta(days=365)).strftime("%Y-%m-%d")
        self.sixMonthAgo = (self.endDate - timedelta(days=180)).strftime("%Y-%m-%d")
        self.mDualMDataAttack:pd.DataFrame = pd.DataFrame()
        self.mDualMDataDefense:pd.DataFrame = pd.DataFrame()
        self.mDualAttackCol = ['VOO', "EFA"]
        self.mDualDefenseCol = ["SHY", "IEF", "TLT", "TIP", "LQD", "HYG", "BWX", "EMB"]
        self.mDualMCol = self.mDualAttackCol + self.mDualDefenseCol

        self.loadDataSet()

    def loadDataSet(self):
        # Attack
        VOO = getCloseData("VOO", self.aYearAgo, self.endDate) # VOO(미국주식)
        BIL = getCloseData("BIL", self.aYearAgo, self.endDate) # BIL(미국 초단기 채권)
        EFA = getCloseData("EFA", self.aYearAgo, self.endDate) # EFA(선진국 주식)
        # Defense
        SHY = getCloseData("SHY", self.sixMonthAgo, self.endDate) # SHY(미국 단기국채)
        IEF = getCloseData("IEF", self.sixMonthAgo, self.endDate) # IEF(미국 중기국채)
        TLT = getCloseData("TLT", self.sixMonthAgo, self.endDate) # TLT(미국 장기국채)
        TIP = getCloseData("TIP", self.sixMonthAgo, self.endDate) # TIP(미국 물가연동채)
        LQD = getCloseData("LQD", self.sixMonthAgo, self.endDate) # LQD(미국 회사채)
        HYG = getCloseData("HYG", self.sixMonthAgo, self.endDate) # HYG(미국 하이일드)
        BWX = getCloseData("BWX", self.sixMonthAgo, self.endDate) # BWX(국제 채권)
        EMB = getCloseData("EMB", self.sixMonthAgo, self.endDate) # EMB(개도국 채권)


        self.mDualMDataAttack = pd.concat([VOO, EFA, BIL], axis=1)
        self.mDualMDataDefense = pd.concat([SHY, IEF, TLT, TIP, LQD, HYG, BWX, EMB], axis=1)
        self.mDualMDataAttack.columns = self.mDualAttackCol + ["BIL"]
        self.mDualMDataDefense.columns = self.mDualDefenseCol
        self.logger.info("=" * 25 + "[Dual Momentum] " + "=" * 25)
        self.logger.info(f"\n* (Modified Dual Momentum) Completed to load Data set")

    # 12 개월 누적수익률
    def getAttackCumReturn(self) -> pd.DataFrame:
        rebalDate = getRebalancingDate(self.mDualMDataAttack) # 리밸런싱 매월 말 날짜
        dualMDataOnRebalDate = self.mDualMDataAttack.loc[rebalDate] # 매월 말 가격 데이터

        dualMCumReturn = getCumulativeReturn(dualMDataOnRebalDate)
        return dualMCumReturn

    def getDefenseCumReturn(self) -> pd.DataFrame:
        rebalDate = getRebalancingDate(self.mDualMDataDefense) # 리밸런싱 매월 말 날짜
        dualMDataOnRebalDate = self.mDualMDataDefense.loc[rebalDate] # 매월 말 가격 데이터

        dualMCumReturn = getCumulativeReturn(dualMDataOnRebalDate)
        return dualMCumReturn

    def pickTarget(self):
        self.mDualMAttackCumReturn:pd.DataFrame = self.getAttackCumReturn()
        lastDay = self.mDualMAttackCumReturn.index[-1]
        self.printWeightAsTable(self.mDualMAttackCumReturn.round(3), self.mDualMAttackCumReturn.columns.tolist(),f"* (Modified Dual Momentum) Attack 자산 12개월 누적 수익률")

        attackData = self.mDualMAttackCumReturn.loc[lastDay]
        if attackData["VOO"] > attackData["BIL"]:
            self.target = [("VOO", 1.0)] if attackData["VOO"] >= attackData["EFA"] else [("EFA", 1.0)]
        else:
            self.mDualMDefenseCumReturn:pd.DataFrame = self.getDefenseCumReturn()
            lastDay = self.mDualMDefenseCumReturn.index[-1]
            self.printWeightAsTable(self.mDualMDefenseCumReturn.round(3), self.mDualMDefenseCumReturn.columns.tolist(), f"* (Modified Dual Momentum) Attack 자산 12개월 누적 수익률")
            defenseData = self.mDualMDefenseCumReturn.loc[lastDay]
            top3Indices = defenseData.nlargest(3).index.tolist()

            cash = 0
            target = []
            self.target = []
            for ticker in top3Indices:
                if defenseData.loc[ticker] > 1 :
                    ratio = 0.333
                else :
                    ratio = 0.0
                    cash += 1
                target.append([ticker,ratio])
            target.append(["cash", cash * 0.333])
            if cash > 0 :
                target[-1][1] += 0.001
            else :
                target[0][1] += 0.001
            for ele in target:
                self.target.append(tuple(ele))

        self.logger.info(f'* (Modified Dual Momentum) [{lastDay.strftime("%Y-%m-%d")} 기준] --->> "{self.target}" 선택\n')

    def printWeightAsTable(self, df, col, frontText=None):
        table = PrettyTable(field_names= ["투자 기준일"] + col,
                            align='r',
                            )
        lastDay = df.index[-1]
        rowVal = [str(lastDay)] + df.loc[lastDay].tolist()

        table.add_row(rowVal)
        if frontText:
            self.logger.info(frontText + "\n" + table.get_string())
        else:
            self.logger.info("\n" + table.get_string())






