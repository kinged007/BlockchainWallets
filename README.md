# Blockchain Wallet Manager

A Python-based CLI application for creating and managing blockchain wallets on the BSC network. This application allows you to create single or bulk wallets, manage existing wallets, handle tokens, and perform transactions.

## Features

- Create single or multiple BSC wallets
- Import existing wallets using private key or mnemonic phrase
- Manage existing wallets
- Perform transactions (single/bulk)
- Fast token balance checking using multicall
- Support for both BSC Mainnet and Testnet
- Interactive CLI interface using Rich and Inquirer

## Performance Features

- **Fast Token Balance Checking**: Uses multicall contract to batch multiple token balance requests into a single call
- **Contract Caching**: Reuses token contract instances for better performance
- **Network-Specific Configuration**: Separate multicall contracts for mainnet and testnet
- **Efficient Error Handling**: Graceful handling of failed token checks without blocking other operations

## Setup

1. Clone the repository
2. Create and activate virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # On Unix/macOS
# or
.\venv\Scripts\activate  # On Windows
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

Run the application:
```bash
python main.py
```

### Network Selection
- Choose between BSC Mainnet or Testnet
- Network-specific configurations are automatically loaded

### Main Menu Options:

1. Create Wallet
   - Single wallet creation
   - Bulk wallet creation
   - Import existing wallet (private key/mnemonic)

2. Manage Wallets
   - View existing wallets
   - Fast balance checking (BNB and tokens)
   - Export wallet information

3. Manage Tokens
   - View token list
   - Add new tokens by contract address
   - Automatic token verification
   - Separate token lists for mainnet/testnet

4. Perform Transaction
   - Single transaction
   - Bulk transactions with multiple recipients
   - Support for "Send to All" option

### Token Management

The application maintains two separate token lists:
- `mainnet_tokens.csv` - BSC Mainnet tokens
- `testnet_tokens.csv` - BSC Testnet tokens

Each token list includes:
- Contract Address
- Symbol
- Decimals
- Name

To add a new token:
1. Select "Manage Tokens" from main menu
2. Choose "Add Token"
3. Enter token contract address
4. Token details will be automatically verified and saved

## Security Features

- **Encryption**: Optional encryption for private keys and mnemonics
- **Masking**: Sensitive data is masked in logs and console output
- **Input Validation**: Addresses and amounts are validated before use
- **Environment Variables**: Sensitive configuration stored in environment variables
- **Checksum Addresses**: Option to automatically convert addresses to checksum format
- **Rate Limiting**: API calls are rate-limited to prevent blocking

## Security Note

- Wallet information is stored in `wallets.csv`
- Private keys and secret phrases are stored locally
- Enable encryption by setting `ENCRYPT_PRIVATE_KEYS=true` in your `.env` file
- Never share private keys or secret phrases
- Use testnet for testing transactions

## Recent Changes

### Version 1.4.0 (Current)
- Enhanced security with encryption capabilities for private keys and mnemonics
- Improved error handling with a proper exception hierarchy
- Added utility module for common functions
- Moved hardcoded values to environment variables
- Created dedicated token contract interaction module
- Added proper logging throughout the application
- Improved API error handling and rate limiting
- Added support for executing arbitrary functions on token contracts
- Updated dependencies and improved project structure
- Added ABI files for tokens and multicall contracts
- Enhanced input validation for addresses and amounts

### Version 1.3.0
- Consolidated configuration files into a single file in src/config.py
- Removed duplicate config.py from root directory
- Improved project structure

### Version 1.2.0
- Added multicall support for fast token balance checking
- Implemented contract instance caching
- Added network-specific configurations
- Improved error handling and user feedback

### Version 1.1.0
- Added support for both BSC Mainnet and Testnet
- Implemented token management system
- Added bulk transaction capabilities

### Version 1.0.0
- Initial release with basic wallet management
- Transaction support
- CSV storage for wallets

## File Structure

```
BlockchainWallets/
├── main.py              # Application entry point
├── requirements.txt     # Python dependencies
├── README.md            # Documentation
├── .env                 # Environment variables (not tracked by git)
├── sample.env           # Sample environment variables template
├── run.sh               # Convenience script to run the application
├── wallets.csv          # Wallet storage
├── mainnet_tokens.csv   # Mainnet token list
├── testnet_tokens.csv   # Testnet token list
├── abis/                # Contract ABIs
│   ├── erc20.json       # ERC20 token ABI
│   └── multicall.json   # Multicall contract ABI
└── src/                 # Source code
    ├── __init__.py
    ├── config.py        # Configuration and constants
    ├── utils.py         # Utility functions
    ├── exceptions.py    # Custom exception hierarchy
    ├── bscscan.py       # BSCScan API integration
    ├── manager.py       # Main application manager
    ├── menus.py         # Menu interfaces
    ├── tokens.py        # Token management with multicall
    ├── token_contract.py # Token contract interaction
    ├── transactions.py  # Transaction handling
    └── wallets.py       # Wallet management
```

## Error Handling

The application includes a comprehensive exception hierarchy for robust error handling:

- **BlockchainWalletError**: Base exception for all application errors
  - **WalletError**: Base for wallet-related errors
    - **WalletFileError**: Errors related to wallet file operations
    - **WalletImportError**: Errors during wallet import
    - **WalletCreationError**: Errors during wallet creation
  - **TokenError**: Base for token-related errors
    - **TokenFileError**: Errors related to token file operations
    - **TokenVerificationError**: Errors during token verification
    - **TokenBalanceError**: Errors during token balance operations
  - **TransactionError**: Base for transaction-related errors
    - **InsufficientBalanceError**: Insufficient balance for a transaction
    - **TransactionFailedError**: Transaction failed
    - **TransactionTimeoutError**: Transaction timed out
  - **NetworkError**: Network-related errors
    - **RPCError**: RPC-related errors
  - **ValidationError**: Validation errors
    - **AddressValidationError**: Address validation errors
    - **AmountValidationError**: Amount validation errors
  - **ConfigurationError**: Configuration errors
  - **APIError**: API-related errors
    - **BSCScanAPIError**: BSCScan API errors

The application handles:
- Network connectivity issues
- Invalid transactions
- Insufficient funds
- Invalid token contracts
- User interruptions (Ctrl+C)
- API rate limiting
- Input validation

All operations can be safely cancelled using Ctrl+C, and the application will maintain data integrity.
