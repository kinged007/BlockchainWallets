import json

# Multicall ABI for batch requests
MULTICALL_ABI = json.loads('''
[{"inputs":[{"components":[{"internalType":"address","name":"target","type":"address"},{"internalType":"bytes","name":"callData","type":"bytes"}],"internalType":"struct Multicall.Call[]","name":"calls","type":"tuple[]"}],"name":"aggregate","outputs":[{"internalType":"uint256","name":"blockNumber","type":"uint256"},{"internalType":"bytes[]","name":"returnData","type":"bytes[]"}],"stateMutability":"view","type":"function"}]
''')

# BSC Testnet and Mainnet Multicall addresses
MULTICALL_ADDRESSES = {
    'testnet': '0x6e5BB1a5Ad6F68A8D7D6A5e47750eC15773d6042',  # BSC Testnet
    'mainnet': '0x41263cBA59EB80dC200F3E2544eda4ed6A90E76C'   # BSC Mainnet
}

# Network configurations
NETWORKS = {
    'mainnet': {
        'name': 'BSC Mainnet',
        'rpc': 'https://bsc-dataseed.binance.org/',
        'chain_id': 56,
        'tokens_file': 'mainnet_tokens.csv'
    },
    'testnet': {
        'name': 'BSC Testnet',
        'rpc': 'https://data-seed-prebsc-1-s1.binance.org:8545/',
        'chain_id': 97,
        'tokens_file': 'testnet_tokens.csv'
    }
}

# CSV file for storing wallet information
WALLET_FILE = 'wallets.csv'

# Common ERC20 ABI for token balance checks
ERC20_ABI = [
    {
        "constant": True,
        "inputs": [{"name": "_owner", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "balance", "type": "uint256"}],
        "type": "function"
    },
    {
        "constant": True,
        "inputs": [],
        "name": "decimals",
        "outputs": [{"name": "", "type": "uint8"}],
        "type": "function"
    },
    {
        "constant": True,
        "inputs": [],
        "name": "symbol",
        "outputs": [{"name": "", "type": "string"}],
        "type": "function"
    },
    {
        "constant": True,
        "inputs": [],
        "name": "name",
        "outputs": [{"name": "", "type": "string"}],
        "type": "function"
    }
]
