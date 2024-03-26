import time
from datetime import datetime, timedelta
from custom_logger import CustomLogger
from strategy.vaa import Vaa

'''
khk strategy

1. VAA 공격형 - 33.4%
2. LAA - 33.3%
3. 오리지날 듀얼 모멘텀 - 33.3%
'''


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

