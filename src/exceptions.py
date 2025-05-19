"""
Custom exceptions for the Blockchain Wallet Manager application.
"""

class BlockchainWalletError(Exception):
    """Base exception for all application errors."""
    pass

class WalletError(BlockchainWalletError):
    """Base exception for wallet-related errors."""
    pass

class WalletFileError(WalletError):
    """Exception raised for errors related to wallet file operations."""
    pass

class WalletImportError(WalletError):
    """Exception raised for errors during wallet import."""
    pass

class WalletCreationError(WalletError):
    """Exception raised for errors during wallet creation."""
    pass

class TokenError(BlockchainWalletError):
    """Base exception for token-related errors."""
    pass

class TokenFileError(TokenError):
    """Exception raised for errors related to token file operations."""
    pass

class TokenVerificationError(TokenError):
    """Exception raised for errors during token verification."""
    pass

class TokenBalanceError(TokenError):
    """Exception raised for errors during token balance operations."""
    pass

class TransactionError(BlockchainWalletError):
    """Base exception for transaction-related errors."""
    pass

class InsufficientBalanceError(TransactionError):
    """Exception raised when there is insufficient balance for a transaction."""
    pass

class TransactionFailedError(TransactionError):
    """Exception raised when a transaction fails."""
    pass

class TransactionTimeoutError(TransactionError):
    """Exception raised when a transaction times out."""
    pass

class NetworkError(BlockchainWalletError):
    """Exception raised for network-related errors."""
    pass

class RPCError(NetworkError):
    """Exception raised for RPC-related errors."""
    pass

class ValidationError(BlockchainWalletError):
    """Exception raised for validation errors."""
    pass

class AddressValidationError(ValidationError):
    """Exception raised for address validation errors."""
    pass

class AmountValidationError(ValidationError):
    """Exception raised for amount validation errors."""
    pass

class ConfigurationError(BlockchainWalletError):
    """Exception raised for configuration errors."""
    pass

class APIError(BlockchainWalletError):
    """Exception raised for API-related errors."""
    pass

class BSCScanAPIError(APIError):
    """Exception raised for BSCScan API errors."""
    pass
