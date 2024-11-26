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

## Security Note

- Wallet information is stored in `wallets.csv`
- Private keys and secret phrases are stored locally
- Never share private keys or secret phrases
- Use testnet for testing transactions

## Recent Changes

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
├── README.md           # Documentation
├── wallets.csv         # Wallet storage
├── mainnet_tokens.csv  # Mainnet token list
├── testnet_tokens.csv  # Testnet token list
└── src/               # Source code
    ├── __init__.py
    ├── config.py      # Configuration and constants
    ├── manager.py     # Main application manager
    ├── menus.py       # Menu interfaces
    ├── tokens.py      # Token management with multicall
    ├── transactions.py # Transaction handling
    └── wallets.py     # Wallet management
```

## Error Handling

The application includes comprehensive error handling for:
- Network connectivity issues
- Invalid transactions
- Insufficient funds
- Invalid token contracts
- User interruptions (Ctrl+C)

All operations can be safely cancelled using Ctrl+C, and the application will maintain data integrity.
