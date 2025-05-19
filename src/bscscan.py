"""
BSCScan API integration module for the Blockchain Wallet Manager.
"""
import os
import json
import logging
import time
import requests
from typing import Dict, List, Any, Optional, Union
from dotenv import load_dotenv

from .exceptions import BSCScanAPIError

# Configure logger
logger = logging.getLogger("blockchain_wallet.bscscan")

# Load environment variables from .env file
load_dotenv()

# Get BSCSCAN API key from environment variables
BSCSCAN_API_KEY = os.getenv('BSCSCAN_API_KEY')
if not BSCSCAN_API_KEY:
    logger.warning("BSCSCAN_API_KEY not found in environment variables. API functionality will be limited.")

# BSCScan API URLs
BSCSCAN_API_URLS = {
    'mainnet': os.getenv('BSC_MAINNET_API_URL', 'https://api.bscscan.com/api'),
    'testnet': os.getenv('BSC_TESTNET_API_URL', 'https://api-testnet.bscscan.com/api')
}

# Rate limiting settings
API_RATE_LIMIT = int(os.getenv('BSCSCAN_API_RATE_LIMIT', '5'))  # requests per second
LAST_API_CALL_TIME = 0

def _handle_rate_limit():
    """Handle API rate limiting to avoid exceeding BSCScan limits"""
    global LAST_API_CALL_TIME

    # Calculate time since last API call
    current_time = time.time()
    time_since_last_call = current_time - LAST_API_CALL_TIME

    # If we're making calls too quickly, sleep to respect rate limit
    if time_since_last_call < (1.0 / API_RATE_LIMIT):
        sleep_time = (1.0 / API_RATE_LIMIT) - time_since_last_call
        logger.debug(f"Rate limiting: sleeping for {sleep_time:.2f} seconds")
        time.sleep(sleep_time)

    # Update last call time
    LAST_API_CALL_TIME = time.time()

def _call_bscscan_api(endpoint: str, params: Dict[str, Any], network: str = 'mainnet') -> Dict[str, Any]:
    """
    Make a call to the BSCScan API with rate limiting and error handling

    Args:
        endpoint (str): API endpoint
        params (dict): API parameters
        network (str): 'mainnet' or 'testnet'

    Returns:
        dict: API response

    Raises:
        BSCScanAPIError: If the API call fails
    """
    # Handle rate limiting
    _handle_rate_limit()

    # Get API URL for the specified network
    api_url = BSCSCAN_API_URLS.get(network, BSCSCAN_API_URLS['mainnet'])

    # Add API key to parameters
    if BSCSCAN_API_KEY:
        params['apikey'] = BSCSCAN_API_KEY

    try:
        # Make the API call
        response = requests.get(api_url, params=params, timeout=10)

        # Check for HTTP errors
        response.raise_for_status()

        # Parse JSON response
        response_json = response.json()

        # Check API response status
        if response_json.get('status') == '1':
            return response_json
        elif response_json.get('message') == 'No transactions found' or response_json.get('message') == 'No records found':
            # Return empty result for no data
            return {'status': '1', 'result': []}
        else:
            # Log the error and raise exception
            error_message = response_json.get('message', 'Unknown API error')
            logger.error(f"BSCScan API error: {error_message}")
            raise BSCScanAPIError(f"BSCScan API error: {error_message}")

    except requests.exceptions.RequestException as e:
        # Handle network/request errors
        logger.error(f"Request error calling BSCScan API: {str(e)}")
        raise BSCScanAPIError(f"Request error: {str(e)}")
    except json.JSONDecodeError as e:
        # Handle JSON parsing errors
        logger.error(f"Invalid JSON response from BSCScan API: {str(e)}")
        raise BSCScanAPIError(f"Invalid API response: {str(e)}")
    except Exception as e:
        # Handle any other errors
        logger.error(f"Unexpected error calling BSCScan API: {str(e)}")
        raise BSCScanAPIError(f"Unexpected error: {str(e)}")

def get_transaction_history(address: str, network: str = 'mainnet', page: int = 1, offset: int = 10, sort: str = 'desc') -> List[Dict[str, Any]]:
    """
    Fetch transaction history for an address from BSCScan API

    Args:
        address (str): The wallet address to get transactions for
        network (str): 'mainnet' or 'testnet'
        page (int): Page number for pagination
        offset (int): Number of transactions to return
        sort (str): 'asc' or 'desc' for sorting by timestamp

    Returns:
        list: List of transactions or empty list if none found

    Raises:
        BSCScanAPIError: If the API call fails
    """
    logger.info(f"Fetching transaction history for {address} on {network}")

    # Prepare API parameters
    params = {
        'module': 'account',
        'action': 'txlist',
        'address': address,
        'startblock': 0,
        'endblock': 99999999,
        'page': page,
        'offset': offset,
        'sort': sort
    }

    try:
        # Call the API
        response = _call_bscscan_api(endpoint='', params=params, network=network)
        return response.get('result', [])
    except BSCScanAPIError as e:
        logger.error(f"Error fetching transaction history: {str(e)}")
        # Re-raise with more specific message
        raise BSCScanAPIError(f"Failed to fetch transaction history: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error in get_transaction_history: {str(e)}")
        raise BSCScanAPIError(f"Unexpected error fetching transactions: {str(e)}")

def get_contract_abi(contract_address: str, network: str = 'mainnet') -> List[Dict[str, Any]]:
    """
    Fetch the full ABI for a contract from BSCScan

    Args:
        contract_address (str): The contract address
        network (str): 'mainnet' or 'testnet'

    Returns:
        list: The contract ABI as a list of dictionaries

    Raises:
        BSCScanAPIError: If the API call fails
    """
    logger.info(f"Fetching ABI for contract {contract_address} on {network}")

    # Prepare API parameters
    params = {
        'module': 'contract',
        'action': 'getabi',
        'address': contract_address
    }

    try:
        # Call the API
        response = _call_bscscan_api(endpoint='', params=params, network=network)

        # Parse the ABI JSON string
        abi_json = response.get('result', '[]')
        if isinstance(abi_json, str):
            return json.loads(abi_json)
        return abi_json
    except json.JSONDecodeError as e:
        logger.error(f"Invalid ABI JSON: {str(e)}")
        raise BSCScanAPIError(f"Invalid ABI format: {str(e)}")
    except BSCScanAPIError as e:
        logger.error(f"Error fetching contract ABI: {str(e)}")
        raise BSCScanAPIError(f"Failed to fetch contract ABI: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error in get_contract_abi: {str(e)}")
        raise BSCScanAPIError(f"Unexpected error fetching contract ABI: {str(e)}")

def get_token_info(contract_address: str, network: str = 'mainnet') -> Dict[str, Any]:
    """
    Fetch token information for a contract from BSCScan

    Args:
        contract_address (str): The token contract address
        network (str): 'mainnet' or 'testnet'

    Returns:
        dict: Token information

    Raises:
        BSCScanAPIError: If the API call fails
    """
    logger.info(f"Fetching token info for contract {contract_address} on {network}")

    # Prepare API parameters
    params = {
        'module': 'token',
        'action': 'tokeninfo',
        'contractaddress': contract_address
    }

    try:
        # Call the API
        response = _call_bscscan_api(endpoint='', params=params, network=network)
        return response.get('result', {})
    except BSCScanAPIError as e:
        logger.error(f"Error fetching token info: {str(e)}")
        raise BSCScanAPIError(f"Failed to fetch token info: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error in get_token_info: {str(e)}")
        raise BSCScanAPIError(f"Unexpected error fetching token info: {str(e)}")

def get_token_balance(contract_address: str, wallet_address: str, network: str = 'mainnet') -> int:
    """
    Fetch token balance for a specific address

    Args:
        contract_address (str): The token contract address
        wallet_address (str): The wallet address to check balance for
        network (str): 'mainnet' or 'testnet'

    Returns:
        int: Token balance in raw units (not adjusted for decimals)

    Raises:
        BSCScanAPIError: If the API call fails
    """
    logger.info(f"Fetching token balance for {wallet_address} on contract {contract_address}")

    # Prepare API parameters
    params = {
        'module': 'account',
        'action': 'tokenbalance',
        'contractaddress': contract_address,
        'address': wallet_address,
        'tag': 'latest'
    }

    try:
        # Call the API
        response = _call_bscscan_api(endpoint='', params=params, network=network)

        # Parse the balance
        balance = response.get('result', '0')
        return int(balance)
    except ValueError as e:
        logger.error(f"Invalid balance value: {str(e)}")
        raise BSCScanAPIError(f"Invalid balance format: {str(e)}")
    except BSCScanAPIError as e:
        logger.error(f"Error fetching token balance: {str(e)}")
        raise BSCScanAPIError(f"Failed to fetch token balance: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error in get_token_balance: {str(e)}")
        raise BSCScanAPIError(f"Unexpected error fetching token balance: {str(e)}")
