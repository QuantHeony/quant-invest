from datetime import datetime, timedelta
from quant.quant_functions import *
from quant.custom_logger import *
from prettytable import PrettyTable

''' 
VOO(미국 주식), BIL(미국 초단기 채권), 선진국 주식(EFA), 미국 채권(AGG)

12개월 수익률 확인 
* VOO > BIL
    * VOO와 EFA중 더 큰것 선택
* VOO < BIL
    * AGG 투자
'''
# Dual Momentum
# dualM = DualMomentum(logger, todayStr)
# dualM.pickTarget()
# khkStrategy["DUAL"]["target"] = dualM.target

class DualMomentum:
    def __init__(self, logger:CustomLogger, endDate=None):
        self.dualMCumReturn = None
        self.target = None # 선택 ETF
        self.logger = logger
        if not endDate:
            today = datetime.now()
            self.endDate = today
        else:
            self.endDate = datetime.strptime(endDate, "%Y-%m-%d")
        self.startDate = (self.endDate - timedelta(days=365)).strftime("%Y-%m-%d")
        self.dualMData:pd.DataFrame = pd.DataFrame()
        self.dualMCol = ['VOO', "BIL", "EFA", "AGG"]

        self.loadDataSet()


    def loadDataSet(self):
        VOO = getCloseData("VOO", self.startDate, self.endDate) # VOO(미국주식)
        BIL = getCloseData("BIL", self.startDate, self.endDate) # BIL(미국 초단기 채권)
        EFA = getCloseData("EFA", self.startDate, self.endDate) # EFA(선진국 주식)
        AGG = getCloseData("AGG", self.startDate, self.endDate) # AGG(미국 총채권)

        self.dualMData = pd.concat([VOO, BIL, EFA,  AGG], axis=1)
        self.dualMData.columns = self.dualMCol
        self.logger.info("=" * 25 + "[Dual Momentum] " + "=" * 25)
        self.logger.info(f"\n* (Dual Momentum) Completed to load Data set")

    # 12 개월 누적수익률
    def getCumReturn(self) -> pd.DataFrame:
        rebalDate = getRebalancingDate(self.dualMData) # 리밸런싱 매월 말 날짜
        dualMDataOnRebalDate = self.dualMData.loc[rebalDate] # 매월 말 가격 데이터

        dualMCumReturn = getCumulativeReturn(dualMDataOnRebalDate)
        return dualMCumReturn

    def pickTarget(self):
        self.dualMCumReturn:pd.DataFrame = self.getCumReturn()
        lastDay = self.dualMCumReturn.index[-1]
        self.printWeightAsTable(self.dualMCumReturn.round(3), f"* (Dual Momentum) 12개월 누적 수익률")

        d = self.dualMCumReturn.loc[lastDay]
        if d["VOO"] > d["BIL"]:
            self.target = [("VOO", 1.0)] if d["VOO"] >= d["EFA"] else [("EFA", 1.0)]
        else:
            self.target = [("AGG", 1.0)]

        self.logger.info(f'* (Dual Momentum) [{lastDay.strftime("%Y-%m-%d")} 기준] --->> "{self.target}" 선택\n')

    def printWeightAsTable(self, df, frontText=None):
        table = PrettyTable(field_names= ["투자 기준일"] + self.dualMCol,
                            align='r',
                            )
        lastDay = df.index[-1]
        rowVal = [str(lastDay)] + df.loc[lastDay].tolist()

        table.add_row(rowVal)
        if frontText:
            self.logger.info(frontText + "\n" + table.get_string())
        else:
            self.logger.info("\n" + table.get_string())






