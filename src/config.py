"""
Configuration settings for the Blockchain Wallet Manager application.
"""
import json
import os
import logging
from typing import Dict, Any
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure logger
logger = logging.getLogger("blockchain_wallet.config")

# Multicall ABI for batch requests - load from file if available
MULTICALL_ABI_FILE = os.path.join(os.path.dirname(__file__), '../abis/multicall.json')
try:
    if os.path.exists(MULTICALL_ABI_FILE):
        with open(MULTICALL_ABI_FILE, 'r') as f:
            MULTICALL_ABI = json.load(f)
    else:
        # Fallback to hardcoded ABI
        MULTICALL_ABI = json.loads('''
        [{"inputs":[{"components":[{"internalType":"address","name":"target","type":"address"},{"internalType":"bytes","name":"callData","type":"bytes"}],"internalType":"struct Multicall.Call[]","name":"calls","type":"tuple[]"}],"name":"aggregate","outputs":[{"internalType":"uint256","name":"blockNumber","type":"uint256"},{"internalType":"bytes[]","name":"returnData","type":"bytes[]"}],"stateMutability":"view","type":"function"}]
        ''')
        logger.warning("Multicall ABI file not found, using hardcoded ABI")
except Exception as e:
    logger.error(f"Error loading Multicall ABI: {str(e)}")
    # Fallback to hardcoded ABI
    MULTICALL_ABI = json.loads('''
    [{"inputs":[{"components":[{"internalType":"address","name":"target","type":"address"},{"internalType":"bytes","name":"callData","type":"bytes"}],"internalType":"struct Multicall.Call[]","name":"calls","type":"tuple[]"}],"name":"aggregate","outputs":[{"internalType":"uint256","name":"blockNumber","type":"uint256"},{"internalType":"bytes[]","name":"returnData","type":"bytes[]"}],"stateMutability":"view","type":"function"}]
    ''')

# BSC Testnet and Mainnet Multicall addresses - use environment variables if available
MULTICALL_ADDRESSES = {
    'testnet': os.getenv('BSC_TESTNET_MULTICALL_ADDRESS', '0x6e5BB1a5Ad6F68A8D7D6A5e47750eC15773d6042'),
    'mainnet': os.getenv('BSC_MAINNET_MULTICALL_ADDRESS', '0x41263cBA59EB80dC200F3E2544eda4ed6A90E76C')
}

# Network configurations - use environment variables if available
NETWORKS = {
    'mainnet': {
        'name': 'BSC Mainnet',
        'rpc': os.getenv('BSC_MAINNET_RPC', 'https://bsc-dataseed.binance.org/'),
        'chain_id': int(os.getenv('BSC_MAINNET_CHAIN_ID', '56')),
        'tokens_file': os.getenv('BSC_MAINNET_TOKENS_FILE', 'mainnet_tokens.csv'),
        'explorer_url': os.getenv('BSC_MAINNET_EXPLORER_URL', 'https://bscscan.com')
    },
    'testnet': {
        'name': 'BSC Testnet',
        'rpc': os.getenv('BSC_TESTNET_RPC', 'https://data-seed-prebsc-1-s1.binance.org:8545/'),
        'chain_id': int(os.getenv('BSC_TESTNET_CHAIN_ID', '97')),
        'tokens_file': os.getenv('BSC_TESTNET_TOKENS_FILE', 'testnet_tokens.csv'),
        'explorer_url': os.getenv('BSC_TESTNET_EXPLORER_URL', 'https://testnet.bscscan.com')
    }
}

# CSV file for storing wallet information
WALLET_FILE = os.getenv('WALLET_FILE', 'wallets.csv')

# Transaction settings
DEFAULT_GAS_LIMIT = int(os.getenv('DEFAULT_GAS_LIMIT', '100000'))
DEFAULT_GAS_PRICE_MULTIPLIER = float(os.getenv('DEFAULT_GAS_PRICE_MULTIPLIER', '1.1'))
MAX_TRANSACTION_TIMEOUT = int(os.getenv('MAX_TRANSACTION_TIMEOUT', '180'))  # seconds
MAX_RETRIES = int(os.getenv('MAX_RETRIES', '3'))

# Security settings
ENCRYPT_PRIVATE_KEYS = os.getenv('ENCRYPT_PRIVATE_KEYS', 'false').lower() == 'true'
CONVERT_CHECKSUM_ADDRESS = os.getenv('CONVERT_CHECKSUM_ADDRESS', 'false').lower() == 'true'

# Common ERC20 ABI for token balance checks - load from file if available
ERC20_ABI_FILE = os.path.join(os.path.dirname(__file__), '../abis/erc20.json')
try:
    if os.path.exists(ERC20_ABI_FILE):
        with open(ERC20_ABI_FILE, 'r') as f:
            ERC20_ABI = json.load(f)
    else:
        # Fallback to hardcoded ABI
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
            },
            {
                "constant": False,
                "inputs": [
                    {"name": "_to", "type": "address"},
                    {"name": "_value", "type": "uint256"}
                ],
                "name": "transfer",
                "outputs": [{"name": "", "type": "bool"}],
                "type": "function"
            }
        ]
        logger.warning("ERC20 ABI file not found, using hardcoded ABI")
except Exception as e:
    logger.error(f"Error loading ERC20 ABI: {str(e)}")
    # Fallback to hardcoded ABI
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
        },
        {
            "constant": False,
            "inputs": [
                {"name": "_to", "type": "address"},
                {"name": "_value", "type": "uint256"}
            ],
            "name": "transfer",
            "outputs": [{"name": "", "type": "bool"}],
            "type": "function"
        }
    ]

def get_network_config(network: str) -> Dict[str, Any]:
    """
    Get configuration for a specific network.

    Args:
        network (str): Network name ('mainnet' or 'testnet')

    Returns:
        dict: Network configuration
    """
    return NETWORKS.get(network, NETWORKS['mainnet'])
