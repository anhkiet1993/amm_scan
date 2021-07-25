from data_type import *
from utils import *
from collections import namedtuple
import time

TransactionData = namedtuple('TransactionData',
                             ['slippage_tolerance', 'amount_input', 'gas_price', 'gas', 'time_limit'])


class AMMDex:
    __factory = ''
    __router = ''
    __web3 = ''
    __json_abi = ''
    __account = ''

    __token_pair_map = {}

    def __init__(self, factory, router, web3, account, json_abi):
        self.__factory = web3.eth.contract(address=factory, abi=json_abi)
        self.__router = web3.eth.contract(address=router, abi=json_abi)
        self.__web3 = web3
        self.__json_abi = json_abi
        self.__account = account

    def CalculatePairPrice(self, token0, token1):
        # pair_addr = self.__factory.functions.getPair(token0, token1).call()
        pair_addr = self.__get_pair(token0.address, token1.address)

        pair_contract = self.__web3.eth.contract(pair_addr, self.__json_abi)

        r0, r1, ts = pair_contract.functions.getReserves().call()

        if token0.address.lower() == pair_contract.functions.token0().call().lower():
            return (r1 / r0) * pow(10, token0.decimal - token1.decimal)
        else:
            return (r0 / r1) * pow(10, token1.decimal - token0.decimal)

    def CalculatePrice(self, tokens):
        price = 1
        for i in range(0, len(tokens) - 1):
            price = price * self.CalculatePairPrice(tokens[i], tokens[i + 1])

        return price

    def __swap(self, tokens_route, trans_data, price):
        logging.info("Token list: {}".format(', '.join([token.address for token in tokens_route])))
        logging.info("Price: %lf", price)

        wallet_address = self.__account.address

        amount_in = int(trans_data.amount_input * pow(10, tokens_route[0].decimal)) if trans_data.amount_input != 0 \
            else self.__web3.eth.contract(address=tokens_route[0].address, abi=self.__json_abi).functions.balanceOf(
            wallet_address).call()
        amount_out_min = int(amount_in * price * (1 - trans_data.slippage_tolerance / 100) * pow(10, tokens_route[
            -1].decimal - tokens_route[0].decimal)) \
            if (trans_data.slippage_tolerance >= 0) else 0

        logging.info("In: %d. Min out:%d", amount_in, amount_out_min)
        route = [token.address for token in tokens_route]

        if amount_in != 0:
            if tokens_route[0].address.lower() == '0xbb4cdb9cbd36b01bd1cbaebf2de08d9173bc095c':
                txn = self.__router.functions.swapExactETHForTokens(
                    amount_out_min,
                    route,
                    wallet_address,
                    (int(time.time()) + trans_data.time_limit),
                ).buildTransaction({
                    'from': wallet_address,
                    'gas': trans_data.gas,
                    'gasPrice': trans_data.gas_price,
                    'nonce': self.__web3.eth.get_transaction_count(wallet_address),
                })
            elif tokens_route[-1].address.lower() == '0xbb4cdb9cbd36b01bd1cbaebf2de08d9173bc095c':
                txn = self.__router.functions.swapExactTokensForETH(
                    amount_in,
                    amount_out_min,
                    route,
                    wallet_address,
                    (int(time.time()) + trans_data.time_limit),
                ).buildTransaction({
                    'from': wallet_address,
                    'gas': trans_data.gas,
                    'gasPrice': trans_data.gas_price,
                    'nonce': self.__web3.eth.get_transaction_count(wallet_address),
                })
            else:
                txn = self.__router.functions.swapExactTokensForTokens(
                    amount_in,
                    amount_out_min,
                    route,
                    wallet_address,
                    (int(time.time()) + trans_data.time_limit)
                ).buildTransaction({
                    'from': wallet_address,
                    'gas': trans_data.gas,
                    'gasPrice': trans_data.gas_price,
                    'nonce': self.__web3.eth.get_transaction_count(wallet_address),
                })

            signed_txn = self.__account.sign_transaction(txn)
            tx_token = self.__web3.eth.send_raw_transaction(signed_txn.rawTransaction)
            # WriteConsoleLog("Swap done: https://bscscan.com/tx/" + tx_token.hex())
            logging.info("Swap done: https://bscscan.com/tx/%s", str(tx_token.hex()))
            # AddMessage("Swap done: https://bscscan.com/tx/" + tx_token.hex())
            return tx_token
        else:
            logging.info("AmountIn = 0")

    def Buy(self, token_list, trans_data, price):
        reverse_list = token_list[::-1]
        return self.__swap(reverse_list, trans_data, 1 / price)

    def Sell(self, token_list, trans_data, price, decimal):
        return self.__swap(token_list, trans_data, price)

    def __get_pair(self, token0_addr, token1_addr):
        key = token0_addr + token1_addr if token0_addr < token1_addr else token1_addr + token0_addr
        if key in self.__token_pair_map:
            return self.__token_pair_map[key]
        else:
            pair_contract = self.__factory.functions.getPair(token0_addr, token1_addr).call()
            self.__token_pair_map[key] = pair_contract
            logging.info("Add pair contract to map:%s %s", token0_addr, token1_addr)
            return pair_contract
