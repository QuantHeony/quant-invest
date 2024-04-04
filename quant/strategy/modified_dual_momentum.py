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
        self.mDualMCumReturn = None
        self.target = None # 선택 ETF
        self.logger = logger
        if not endDate:
            today = datetime.now()
            self.endDate = today
        else:
            self.endDate = datetime.strptime(endDate, "%Y-%m-%d")
        self.startDate = (self.endDate - timedelta(days=365)).strftime("%Y-%m-%d")
        self.mDualMData:pd.DataFrame = pd.DataFrame()
        self.mDualAttack = ['VOO', "EFA"]
        self.mDualDefense = ["SHY", "IEF", "TLT", "TIP", "LQD", "HYG","BWX", "EMB"]
        self.mDualMCol = self.mDualAttack + self.mDualDefense

        self.loadDataSet()


    def loadDataSet(self):
        VOO = getCloseData("VOO", self.startDate, self.endDate) # VOO(미국주식)
        BIL = getCloseData("BIL", self.startDate, self.endDate) # BIL(미국 초단기 채권)
        EFA = getCloseData("EFA", self.startDate, self.endDate) # EFA(선진국 주식)
        AGG = getCloseData("AGG", self.startDate, self.endDate) # AGG(미국 총채권)

        self.mDualMData = pd.concat([VOO, BIL, EFA,  AGG], axis=1)
        self.mDualMData.columns = self.mDualMCol
        self.logger.info("=" * 25 + "[Dual Momentum] " + "=" * 25)
        self.logger.info(f"\n* (Dual Momentum) Completed to load Data set")

    # 12 개월 누적수익률
    def getCumReturn(self) -> pd.DataFrame:
        rebalDate = getRebalancingDate(self.mDualMData) # 리밸런싱 매월 말 날짜
        dualMDataOnRebalDate = self.mDualMData.loc[rebalDate] # 매월 말 가격 데이터

        dualMCumReturn = getCumulativeReturn(dualMDataOnRebalDate)
        return dualMCumReturn

    def pickTarget(self):
        self.mDualMCumReturn:pd.DataFrame = self.getCumReturn()
        lastDay = self.mDualMCumReturn.index[-1]
        self.printWeightAsTable(self.mDualMCumReturn.round(3), f"* (Dual Momentum) 12개월 누적 수익률")

        d = self.mDualMCumReturn.loc[lastDay]
        if d["VOO"] > d["BIL"]:
            self.target = [("VOO", 1.0)] if d["VOO"] >= d["EFA"] else [("EFA", 1.0)]
        else:
            self.target = [("AGG", 1.0)]

        self.logger.info(f'* (Dual Momentum) [{lastDay.strftime("%Y-%m-%d")} 기준] --->> "{self.target}" 선택\n')

    def printWeightAsTable(self, df, frontText=None):
        table = PrettyTable(field_names= ["투자 기준일"] + self.mDualMCol,
                            align='r',
                            )
        lastDay = df.index[-1]
        rowVal = [str(lastDay)] + df.loc[lastDay].tolist()

        table.add_row(rowVal)
        if frontText:
            self.logger.info(frontText + "\n" + table.get_string())
        else:
            self.logger.info("\n" + table.get_string())






