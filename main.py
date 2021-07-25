import threading

from web3 import Web3
import json
from configparser import ConfigParser
from amm import AMMDex
from data_type import Token
from utils import *

#####################datetype##################

######################enum####################


#################Global variables##############
json_abi = '[]'
AMMData = {}
TokenData = []
mnemonic = ''
passphrase = ''
web3 = 0
my_account = 0
AMMSolutionMap = {}
SoundAlarm = True
MessageNotification = True
ScanDelay = 30000
ProgramExit = False

############################################################


def LoadAMM():
    global AMMSolutionMap
    global AMMData

    for amm, info in AMMData.items():
        AMMSolutionMap[amm] = AMMDex(info.Factory, info.Router, web3, my_account, json_abi)


def LoadConfig(config_file):
    config = ConfigParser()
    config.read(config_file)

    global SoundAlarm
    global MessageNotification
    global ScanDelay
    global AMMData
    global mnemonic
    global passphrase
    global AMMSolutionMap

    general = config['general']

    SoundAlarm = general['SoundAlarm'] == 'True'
    MessageNotification = general['MessageNotification'] == 'True'
    ScanDelay = int(general['ScanDelay'])
    AMMsRaw = general['AMM'][1:-1].split(',')
    AMMs = [AMM.strip() for AMM in AMMsRaw]

    wallet = config['wallet']

    mnemonic = wallet['Mnemonic']
    passphrase = wallet['Passphrase']

    for AMM in AMMs:
        config_info = config[AMM]
        router = web3.toChecksumAddress(config_info['Router'])
        factory = web3.toChecksumAddress(config_info['Factory'])

        AMMData[AMM] = AMMInfo(router, factory)


def LoadData(data_file):
    data = ConfigParser()
    data.read('data.ini')

    global TokenData

    for index, section in enumerate(data.sections()):
        AMMsRaw = data.get(section, 'AMM')[1:-1].split(',')
        AMMs = [AMM.strip() for AMM in AMMsRaw]

        token_route_map = {}
        for AMM in AMMs:
            route = data.get(section, AMM)[1:-1].split(',')
            token_route_map[AMM] = [Token(web3.toChecksumAddress(token.strip()), web3, json_abi) for token in route]

        swap_on_diff = float(data.get(section, "SwapOnPriceDiff"))
        amount_to_buy = float(data.get(section, "AmountToBuy"))
        slippage = float(data.get(section, "SlippageTolerance"))
        gas_price = int(data.get(section, "GasPrice"))
        gas = int(data.get(section, "Gas"))
        time_limit = int(data.get(section, "TimeLimit"))

        trans_data = TransactionData(slippage, amount_to_buy, gas_price, gas, time_limit)

        data = TokenDataInfo(token_route_map, swap_on_diff, trans_data)

        TokenData.append(data)


def LoadABI(json_file):
    global json_abi
    abi_json_file = open(json_file, 'r')
    json_abi = json.load(abi_json_file)


def ConnectBSC():
    bsc = "https://bsc-dataseed.binance.org/"
    global web3
    global my_account
    try:
        web3 = Web3(Web3.HTTPProvider(bsc))
        web3.eth.account.enable_unaudited_hdwallet_features()
        my_account = web3.eth.account.from_mnemonic(mnemonic, passphrase)
    except:
        logging.error("Connect to BSC and Pancake failed")
        return False

    if web3.isConnected():
        logging.info("Connected to BSC")
        # logging.info("Wallet Address: %s", my_account.address)
    else:
        logging.error("Failed to connect to BSC")
        return False

    return True


def CheckPriceDiff(token: TokenDataInfo):
    while not ProgramExit:
        price = []
        for amm, route in token.Route.items():
            price.append(AMMSolutionMap[amm].CalculatePrice())

        price_max = max(price)
        price_min = min(price)
        max_idx = price.index(price_max)
        min_idx = price.index(price_min)
        diff = (price_max - price_max) / price_min
        if diff > token.SwapOnPriceDiff:
            amm_list = list(token.Route)
            amm_sell = amm_list[min_idx]
            amm_buy = amm_list[max_idx]

            logging.info("Price diff between %s and %s: %d%%", amm_sell, amm_buy, diff * 100)

            # buy_result, sel_result = BridgeSwap(AMMSolutionMap[amm_buy], AMMSolutionMap[amm_sell], token.Route[amm_sell], token.Route[amm_buy], price_max, price_min, token.TransData)


def BridgeSwap(amm_sell: AMMDex, amm_buy: AMMDex, sell_route, buy_route, price_sell, price_buy, trans_data):
    buy_txn_hash = amm_buy.Buy(buy_route, trans_data, price_buy)
    hash_data = web3.eth.wait_for_transaction_receipt(buy_txn_hash)

    if hash_data['status'] != 1:
        return False, False

    sell_txn_hash = amm_sell.Sell(sell_route, trans_data, price_sell)
    hash_data = web3.eth.wait_for_transaction_receipt(sell_txn_hash)

    if hash_data['status'] != 1:
        return True, True
    else:
        return True, False


def RunCheck(pos):
    global ProgramExit
    while not ProgramExit:
        CheckPriceDiff(Token[pos])


def main():
    LoadABI('abi.json')

    ConnectBSC()

    LoadConfig('config.ini')
    LoadData('data.ini')
    LoadAMM()

    TokenCheckingThread = []
    for pos, token_check in enumerate(TokenData):
        th = threading.Thread(target=RunCheck(), args=pos)
        TokenCheckingThread.append(th)
        th.start()

    for th in TokenCheckingThread:
        th.join()


if __name__ == "__main__":
    main()
