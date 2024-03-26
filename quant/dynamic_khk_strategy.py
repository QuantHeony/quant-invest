import time
from datetime import datetime, timedelta
from custom_logger import CustomLogger
from strategy.vaa import Vaa
from strategy.dual_momentum import DualMomentum
from strategy.laa import Laa


'''
khk strategy

1. VAA 공격형 - 33.4%
2. LAA - 33.3%
3. 오리지날 듀얼 모멘텀 - 33.3%
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
    'DUAL' : {
        "target" : None,
        "ratio" : 0.333
    }
}

FRED_API_KEY = '3f3d80667b222b9928b43d97abc7642c'
if __name__ == "__main__":
    testTimeLabel:str = time.strftime("%m%d_%H%M%S", time.localtime())
    logger = CustomLogger(testTimeLabel)

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

    # Dual Momentum
    dualM = DualMomentum(logger, todayStr)
    khkStrategy["DUAL"]["name"] = dualM.target




