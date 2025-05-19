"""
Blockchain Wallet Manager - A Python-based CLI application for managing blockchain wallets.
"""
# Configuration
from .config import (
    NETWORKS, WALLET_FILE, ERC20_ABI, MULTICALL_ABI, MULTICALL_ADDRESSES,
    DEFAULT_GAS_LIMIT, DEFAULT_GAS_PRICE_MULTIPLIER, MAX_TRANSACTION_TIMEOUT,
    MAX_RETRIES, ENCRYPT_PRIVATE_KEYS, CONVERT_CHECKSUM_ADDRESS,
    get_network_config
)

# Core components
from .tokens import TokenManager
from .wallets import WalletManager
from .transactions import TransactionManager
from .token_contract import TokenContractManager
from .menus import MenuManager
from .manager import BlockchainWalletManager

# API integrations
from .bscscan import get_transaction_history, get_contract_abi, get_token_info

# Utilities
from .utils import (
    to_checksum_address, mask_private_key, mask_mnemonic,
    encrypt_data, decrypt_data, validate_address, validate_amount
)

# Exceptions
from .exceptions import (
    BlockchainWalletError, WalletError, TokenError, TransactionError,
    NetworkError, ValidationError, ConfigurationError, APIError
)

__all__ = [
    # Configuration
    'NETWORKS',
    'WALLET_FILE',
    'ERC20_ABI',
    'MULTICALL_ABI',
    'MULTICALL_ADDRESSES',
    'DEFAULT_GAS_LIMIT',
    'DEFAULT_GAS_PRICE_MULTIPLIER',
    'MAX_TRANSACTION_TIMEOUT',
    'MAX_RETRIES',
    'ENCRYPT_PRIVATE_KEYS',
    'CONVERT_CHECKSUM_ADDRESS',
    'get_network_config',

    # Core components
    'TokenManager',
    'WalletManager',
    'TransactionManager',
    'TokenContractManager',
    'MenuManager',
    'BlockchainWalletManager',

    # API integrations
    'get_transaction_history',
    'get_contract_abi',
    'get_token_info',

    # Utilities
    'to_checksum_address',
    'mask_private_key',
    'mask_mnemonic',
    'encrypt_data',
    'decrypt_data',
    'validate_address',
    'validate_amount',

    # Exceptions
    'BlockchainWalletError',
    'WalletError',
    'TokenError',
    'TransactionError',
    'NetworkError',
    'ValidationError',
    'ConfigurationError',
    'APIError'
]
