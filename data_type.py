class Token:
    address = ''
    decimal = 0
    symbol = ''

    def __init(self, token, web3, json_abi):
        self.address = token

        token_contract = web3.eth.contract(contract=token, abi=json_abi)
        self.decimal = token_contract.functions.decimal().call()
        self.symbol = token_contract.functions.symbol().call()
