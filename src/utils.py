"""
Utility functions for the Blockchain Wallet Manager application.
"""
import os
import logging
import json
from typing import Dict, Any, Optional, Union, Tuple
from web3 import Web3
from eth_account import Account
from dotenv import load_dotenv
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("blockchain_wallet.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("blockchain_wallet")

# Load environment variables
load_dotenv()

def to_checksum_address(address: str) -> str:
    """
    Convert an address to checksum format safely.
    
    Args:
        address (str): The address to convert
        
    Returns:
        str: The checksum address
    """
    try:
        # Handle empty or None addresses
        if not address:
            logger.warning("Empty address provided to checksum conversion")
            return ""
            
        # Remove '0x' prefix if present for normalization
        if address.startswith('0x'):
            clean_address = address[2:]
        else:
            clean_address = address
            
        # Ensure the address is valid hex
        if not all(c in '0123456789abcdefABCDEF' for c in clean_address):
            logger.warning(f"Invalid hex characters in address: {address}")
            return address
            
        # Ensure correct length (40 hex chars = 20 bytes)
        if len(clean_address) != 40:
            logger.warning(f"Address has incorrect length: {address}")
            return address
            
        # Convert to checksum address
        return Web3.to_checksum_address('0x' + clean_address)
    except Exception as e:
        logger.error(f"Error converting to checksum address: {str(e)}")
        return address

def mask_private_key(private_key: str) -> str:
    """
    Mask a private key for display or logging.
    
    Args:
        private_key (str): The private key to mask
        
    Returns:
        str: The masked private key
    """
    if not private_key:
        return ""
        
    # Remove '0x' prefix if present
    if private_key.startswith('0x'):
        key = private_key[2:]
    else:
        key = private_key
        
    # Show only first 4 and last 4 characters
    if len(key) > 8:
        return f"0x{key[:4]}...{key[-4:]}"
    else:
        return "0x****"

def mask_mnemonic(mnemonic: str) -> str:
    """
    Mask a mnemonic phrase for display or logging.
    
    Args:
        mnemonic (str): The mnemonic phrase to mask
        
    Returns:
        str: The masked mnemonic
    """
    if not mnemonic:
        return ""
        
    words = mnemonic.split()
    if len(words) <= 2:
        return "****"
        
    # Show only first and last word
    return f"{words[0]} ... {words[-1]}"

def get_encryption_key(password: Optional[str] = None) -> bytes:
    """
    Generate or retrieve an encryption key.
    
    Args:
        password (str, optional): Password to derive key from
        
    Returns:
        bytes: The encryption key
    """
    # Use environment variable if password not provided
    if not password:
        password = os.getenv('WALLET_ENCRYPTION_KEY', 'default_encryption_key')
    
    # Use PBKDF2 to derive a key from the password
    salt = b'blockchain_wallet_manager_salt'
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
    return key

def encrypt_data(data: str, password: Optional[str] = None) -> str:
    """
    Encrypt sensitive data.
    
    Args:
        data (str): Data to encrypt
        password (str, optional): Password to derive key from
        
    Returns:
        str: Encrypted data as a base64 string
    """
    try:
        key = get_encryption_key(password)
        f = Fernet(key)
        encrypted_data = f.encrypt(data.encode())
        return base64.urlsafe_b64encode(encrypted_data).decode()
    except Exception as e:
        logger.error(f"Encryption error: {str(e)}")
        # Return original data if encryption fails
        return data

def decrypt_data(encrypted_data: str, password: Optional[str] = None) -> str:
    """
    Decrypt sensitive data.
    
    Args:
        encrypted_data (str): Encrypted data as a base64 string
        password (str, optional): Password to derive key from
        
    Returns:
        str: Decrypted data
    """
    try:
        key = get_encryption_key(password)
        f = Fernet(key)
        decrypted_data = f.decrypt(base64.urlsafe_b64decode(encrypted_data))
        return decrypted_data.decode()
    except Exception as e:
        logger.error(f"Decryption error: {str(e)}")
        # Return original data if decryption fails
        return encrypted_data

def validate_address(address: str) -> bool:
    """
    Validate if an address is a valid Ethereum/BSC address.
    
    Args:
        address (str): The address to validate
        
    Returns:
        bool: True if valid, False otherwise
    """
    try:
        # Check if it's a valid address format
        return Web3.is_address(address)
    except Exception:
        return False

def validate_amount(amount: str, min_value: float = 0) -> Tuple[bool, float]:
    """
    Validate if an amount is a valid number.
    
    Args:
        amount (str): The amount to validate
        min_value (float): Minimum allowed value
        
    Returns:
        tuple: (is_valid, amount_as_float)
    """
    try:
        # Try to convert to float
        amount_float = float(amount)
        
        # Check if it's a positive number
        if amount_float < min_value:
            return False, 0
            
        return True, amount_float
    except ValueError:
        return False, 0
