import logging
import datetime
from collections import namedtuple

logging.basicConfig(filename="./log/" + datetime.now().strftime("%d-%m-%Y-%Hh%M") + ".log",
                    filemode='a',
                    format='[%(asctime)s,%(msecs)d][%(levelname)s][%(filename)s:%(lineno)d] %(message)s',
                    datefmt='%H:%M:%S',
                    level=logging.INFO)

TransactionData = namedtuple('TransactionData',
                             ['slippage_tolerance', 'amount_input', 'gas_price', 'gas', 'time_limit'])

AMMInfo = namedtuple('AMMInfo', ['Factory', 'Router'])

TokenDataInfo = namedtuple('TokenDataInfo', ['Route', 'SwapOnPriceDiff', 'TransData'])