
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