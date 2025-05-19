import csv
import os
import re
import json
import datetime
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
import inquirer
from rich import print as rprint
from web3 import Web3
from eth_account import Account
from dotenv import load_dotenv

class WalletManager:
    def __init__(self, w3: Web3, wallet_file: str, console, network='mainnet'):
        self.w3 = w3
        self.wallet_file = wallet_file
        self.console = console
        self.network = network  # Store the network (mainnet or testnet)
        self.ensure_wallet_file()

    def ensure_wallet_file(self):
        """Create wallet file if it doesn't exist or validate and fix its structure"""
        # Define the expected columns
        expected_columns = ['Address', 'Private Key', 'Secret Phrase', 'bnb_balance', 'btc_balance', 'eth_balance', 'other_tokens', 'last_transaction_date']

        if not os.path.exists(self.wallet_file):
            # Create new file with all expected columns
            rprint("[yellow]Wallet file not found. Creating a new one...[/yellow]")
            with open(self.wallet_file, 'w', newline='') as file:
                writer = csv.writer(file)
                writer.writerow(expected_columns)
            return

        # File exists, validate its structure
        try:
            # First, check if the file is valid CSV
            wallets_data = []
            header = []
            try:
                with open(self.wallet_file, 'r', newline='') as file:
                    reader = csv.reader(file)
                    header = next(reader, [])
                    wallets_data = list(reader)
            except Exception as e:
                rprint(f"[red]Error reading wallet file: {str(e)}[/red]")
                rprint("[yellow]Attempting to repair the file...[/yellow]")

                # Try to read the file line by line to salvage data
                wallets_data = []
                with open(self.wallet_file, 'r') as file:
                    lines = file.readlines()
                    if lines:
                        # Try to determine the delimiter
                        first_line = lines[0].strip()
                        if ',' in first_line:
                            delimiter = ','
                        elif ';' in first_line:
                            delimiter = ';'
                        elif '\t' in first_line:
                            delimiter = '\t'
                        else:
                            delimiter = ','  # Default to comma

                        # Parse header
                        header = first_line.split(delimiter)

                        # Parse data rows
                        for line in lines[1:]:
                            if line.strip():  # Skip empty lines
                                wallets_data.append(line.strip().split(delimiter))

            # Check if we have a valid header
            if not header:
                rprint("[red]Wallet file has no header![/red]")
                # Create a new file with the expected structure
                self._create_new_wallet_file(expected_columns, [])
                return

            # Check if the header matches expected columns
            missing_columns = [col for col in expected_columns if col not in header]
            extra_columns = [col for col in header if col not in expected_columns]

            # If there are missing or extra columns, we need to fix the structure
            if missing_columns or extra_columns:
                rprint(f"[yellow]Wallet file structure needs updating.[/yellow]")
                if missing_columns:
                    rprint(f"[yellow]Missing columns: {', '.join(missing_columns)}[/yellow]")
                if extra_columns:
                    rprint(f"[yellow]Extra columns: {', '.join(extra_columns)}[/yellow]")

                # Create a mapping from current columns to expected columns
                column_mapping = {}
                for i, col in enumerate(header):
                    if col in expected_columns:
                        column_mapping[i] = expected_columns.index(col)

                # Convert the data to the expected structure
                fixed_wallets = []
                for row in wallets_data:
                    if not row:  # Skip empty rows
                        continue

                    # Create a new row with all expected columns (initially empty)
                    new_row = [''] * len(expected_columns)

                    # Copy data from the original row to the new row based on the mapping
                    for i, val in enumerate(row):
                        if i < len(header) and i in column_mapping:
                            new_row[column_mapping[i]] = val

                    # Ensure the Address column is not empty (it's the primary key)
                    if new_row[0]:  # Address is the first column
                        fixed_wallets.append(new_row)
                    else:
                        rprint(f"[yellow]Skipping row with empty Address: {row}[/yellow]")

                # Write the fixed data back to the file
                self._create_new_wallet_file(expected_columns, fixed_wallets)
                rprint(f"[green]Successfully fixed wallet file structure. Saved {len(fixed_wallets)} wallets.[/green]")
            else:
                # Check for duplicate addresses
                addresses = {}
                duplicates = []

                for i, row in enumerate(wallets_data):
                    if not row:  # Skip empty rows
                        continue

                    if len(row) > 0 and row[0]:  # Check if Address column exists and is not empty
                        address = row[0]
                        if address in addresses:
                            duplicates.append((address, i, addresses[address]))
                        else:
                            addresses[address] = i

                if duplicates:
                    rprint(f"[yellow]Found {len(duplicates)} duplicate addresses in wallet file.[/yellow]")

                    # Merge duplicate entries
                    merged_wallets = []
                    skip_indices = set()

                    for i, row in enumerate(wallets_data):
                        if i in skip_indices or not row:
                            continue

                        if len(row) > 0 and row[0]:  # Check if Address column exists and is not empty
                            address = row[0]

                            # Find all duplicates of this address
                            dups = [(idx, orig_idx) for addr, idx, orig_idx in duplicates if addr == address and idx != i]

                            if dups:
                                # Merge the data from all duplicates
                                merged_row = row.copy()
                                for dup_idx, _ in dups:
                                    if dup_idx < len(wallets_data):
                                        dup_row = wallets_data[dup_idx]
                                        # For each column, take the non-empty value
                                        for j in range(min(len(merged_row), len(dup_row))):
                                            if not merged_row[j] and dup_row[j]:
                                                merged_row[j] = dup_row[j]

                                        # Mark this duplicate to be skipped
                                        skip_indices.add(dup_idx)

                                merged_wallets.append(merged_row)
                            else:
                                merged_wallets.append(row)

                    # Write the merged data back to the file
                    self._create_new_wallet_file(header, merged_wallets)
                    rprint(f"[green]Successfully merged duplicate addresses. Saved {len(merged_wallets)} wallets.[/green]")

                # Check for rows with wrong number of columns
                malformed_rows = [i for i, row in enumerate(wallets_data) if len(row) != len(header)]

                if malformed_rows:
                    rprint(f"[yellow]Found {len(malformed_rows)} rows with incorrect number of columns.[/yellow]")

                    # Fix rows with wrong number of columns
                    fixed_wallets = []
                    for i, row in enumerate(wallets_data):
                        if not row:  # Skip empty rows
                            continue

                        if len(row) != len(header):
                            # Pad or truncate the row to match the header length
                            if len(row) < len(header):
                                # Pad with empty strings
                                fixed_row = row + [''] * (len(header) - len(row))
                            else:
                                # Truncate
                                fixed_row = row[:len(header)]

                            fixed_wallets.append(fixed_row)
                        else:
                            fixed_wallets.append(row)

                    # Write the fixed data back to the file
                    self._create_new_wallet_file(header, fixed_wallets)
                    rprint(f"[green]Successfully fixed rows with incorrect number of columns. Saved {len(fixed_wallets)} wallets.[/green]")

        except Exception as e:
            rprint(f"[red]Error validating wallet file: {str(e)}[/red]")
            rprint("[yellow]Creating a backup of the original file and creating a new one...[/yellow]")

            # Create a backup of the original file
            import shutil
            backup_file = f"{self.wallet_file}.bak"
            shutil.copy2(self.wallet_file, backup_file)
            rprint(f"[green]Created backup at {backup_file}[/green]")

            # Create a new file with the expected structure
            self._create_new_wallet_file(expected_columns, [])

    def _create_new_wallet_file(self, columns, data):
        """Helper method to create a new wallet file with the given columns and data"""
        with open(self.wallet_file, 'w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(columns)
            writer.writerows(data)
        rprint(f"[green]Created new wallet file with {len(columns)} columns and {len(data)} rows.[/green]")

    def get_wallet_list_basic(self):
        """Get basic list of stored wallets without additional processing"""
        wallets = []
        if os.path.exists(self.wallet_file):
            try:
                with open(self.wallet_file, 'r', newline='') as file:
                    reader = csv.DictReader(file)
                    wallets = list(reader)

                    # Validate that each wallet has an Address field
                    for i, wallet in enumerate(wallets):
                        if 'Address' not in wallet or not wallet['Address']:
                            rprint(f"[yellow]Warning: Wallet at index {i} has no Address field. Skipping.[/yellow]")
                            wallets[i] = None  # Mark for removal

                    # Remove invalid wallets
                    wallets = [w for w in wallets if w is not None]

                    # Ensure all wallets have the expected fields
                    expected_fields = ['Address', 'Private Key', 'Secret Phrase', 'bnb_balance', 'btc_balance', 'eth_balance', 'other_tokens', 'last_transaction_date']
                    for wallet in wallets:
                        for field in expected_fields:
                            if field not in wallet:
                                wallet[field] = ''  # Add missing field with empty value
            except Exception as e:
                rprint(f"[red]Error reading wallet file: {str(e)}[/red]")
                rprint("[yellow]Running wallet file validation and repair...[/yellow]")
                # Run the validation and repair process
                self.ensure_wallet_file()

                # Try reading again after repair
                try:
                    with open(self.wallet_file, 'r', newline='') as file:
                        reader = csv.DictReader(file)
                        wallets = list(reader)
                except Exception as e2:
                    rprint(f"[red]Still unable to read wallet file after repair: {str(e2)}[/red]")
                    wallets = []  # Return empty list as fallback

        return wallets

    def get_wallet_list(self):
        """Get list of stored wallets"""
        wallets = []
        if os.path.exists(self.wallet_file):
            with open(self.wallet_file, 'r') as file:
                reader = csv.DictReader(file)
                wallets = list(reader)

            # Check if we should convert checksum addresses
            load_dotenv()  # Make sure we have the latest env variables
            convert_checksum = os.getenv('CONVERT_CHECKSUM_ADDRESS', 'false').lower() == 'true'
            if convert_checksum:
                self.convert_private_keys_format(wallets)

        return wallets

    def convert_private_keys_format(self, wallets):
        """Convert private keys to the correct format and update wallets.csv file"""
        try:
            # Check if any wallets need conversion
            wallets_to_update = []
            for wallet in wallets:
                private_key = wallet.get('Private Key', '')
                if private_key and not private_key.startswith('0x'):
                    # Try to create a standardized private key
                    try:
                        # Remove any non-hex characters
                        clean_key = re.sub(r'[^0-9a-fA-F]', '', private_key)
                        # Ensure it's the right length (64 hex chars)
                        if len(clean_key) < 64:
                            clean_key = clean_key.rjust(64, '0')
                        elif len(clean_key) > 64:
                            clean_key = clean_key[-64:]  # Take the last 64 chars

                        # Verify the key works by deriving the address
                        account = Account.from_key('0x' + clean_key)
                        # If we get here, the key is valid

                        # Check if the derived address matches the stored address
                        if self.w3.to_checksum_address(wallet['Address']) == account.address:
                            wallet['Private Key'] = '0x' + clean_key
                            wallets_to_update.append(wallet)
                    except Exception as e:
                        rprint(f"[yellow]Could not convert private key for address {wallet['Address']}: {str(e)}[/yellow]")

            # If we have wallets to update, rewrite the CSV file
            if wallets_to_update:
                # First read all wallets to preserve those we're not updating
                all_wallets = []
                with open(self.wallet_file, 'r') as file:
                    reader = csv.DictReader(file)
                    all_wallets = list(reader)

                # Update the wallets that need conversion
                for update_wallet in wallets_to_update:
                    for i, wallet in enumerate(all_wallets):
                        if wallet['Address'] == update_wallet['Address']:
                            all_wallets[i]['Private Key'] = update_wallet['Private Key']
                            rprint(f"[green]Updated private key format for wallet {wallet['Address']}[/green]")

                # Write back all wallets
                with open(self.wallet_file, 'w', newline='') as file:
                    writer = csv.DictWriter(file, fieldnames=['Address', 'Private Key', 'Secret Phrase'])
                    writer.writeheader()
                    writer.writerows(all_wallets)

                rprint(f"[green]Successfully updated {len(wallets_to_update)} wallet(s) with standardized private key format[/green]")
        except Exception as e:
            rprint(f"[red]Error converting private keys: {str(e)}[/red]")

    def save_wallet(self, wallet_data):
        """Save wallet information to CSV with all required fields"""
        # Ensure the wallet file exists and has the correct structure
        self.ensure_wallet_file()

        # Get the expected columns from an existing wallet or create them
        expected_columns = ['Address', 'Private Key', 'Secret Phrase', 'bnb_balance', 'btc_balance', 'eth_balance', 'other_tokens', 'last_transaction_date']

        # Create a new wallet row with all expected fields
        wallet_row = {
            'Address': wallet_data.get('address', ''),
            'Private Key': wallet_data.get('private_key', ''),
            'Secret Phrase': wallet_data.get('secret_phrase', ''),
            'bnb_balance': wallet_data.get('bnb_balance', '0'),
            'btc_balance': wallet_data.get('btc_balance', '0'),
            'eth_balance': wallet_data.get('eth_balance', '0'),
            'other_tokens': wallet_data.get('other_tokens', ''),
            'last_transaction_date': wallet_data.get('last_transaction_date', '')
        }

        # Check if the wallet already exists
        existing_wallets = self.get_wallet_list_basic()
        for wallet in existing_wallets:
            if wallet.get('Address', '').lower() == wallet_row['Address'].lower():
                rprint(f"[yellow]Wallet with address {wallet_row['Address']} already exists. Updating...[/yellow]")

                # Update the existing wallet file
                self._update_existing_wallet(wallet_row)
                return

        # If the wallet doesn't exist, append it to the file
        try:
            with open(self.wallet_file, 'a', newline='') as file:
                writer = csv.DictWriter(file, fieldnames=expected_columns)
                writer.writerow(wallet_row)
            rprint(f"[green]Successfully saved wallet with address {wallet_row['Address']}[/green]")
        except Exception as e:
            rprint(f"[red]Error saving wallet: {str(e)}[/red]")

    def _update_existing_wallet(self, new_wallet):
        """Update an existing wallet in the CSV file"""
        wallets = self.get_wallet_list_basic()
        updated = False

        # Find and update the wallet
        for i, wallet in enumerate(wallets):
            if wallet.get('Address', '').lower() == new_wallet['Address'].lower():
                # Merge the wallet data, keeping existing values if not provided in the new wallet
                for key in wallet:
                    if key not in new_wallet or not new_wallet[key]:
                        new_wallet[key] = wallet[key]

                wallets[i] = new_wallet
                updated = True
                break

        if updated:
            # Write all wallets back to the file
            expected_columns = ['Address', 'Private Key', 'Secret Phrase', 'bnb_balance', 'btc_balance', 'eth_balance', 'other_tokens', 'last_transaction_date']
            try:
                with open(self.wallet_file, 'w', newline='') as file:
                    writer = csv.DictWriter(file, fieldnames=expected_columns)
                    writer.writeheader()
                    writer.writerows(wallets)
                rprint(f"[green]Successfully updated wallet with address {new_wallet['Address']}[/green]")
            except Exception as e:
                rprint(f"[red]Error updating wallet: {str(e)}[/red]")

    def create_wallet(self):
        """Create a single wallet"""
        Account.enable_unaudited_hdwallet_features()
        account, mnemonic = Account.create_with_mnemonic()
        return {
            'address': account.address,
            'private_key': account.key.hex(),
            'secret_phrase': mnemonic
        }

    def create_bulk_wallets(self, count):
        """Create multiple wallets"""
        wallets = []
        successful = 0

        # Ensure the wallet file exists with the correct structure
        self.ensure_wallet_file()

        for i in range(count):
            try:
                wallet = self.create_wallet()
                self.save_wallet(wallet)
                wallets.append(wallet)
                successful += 1

                # Show progress for large batches
                if count > 10 and (i+1) % 5 == 0:
                    rprint(f"[cyan]Created {i+1}/{count} wallets...[/cyan]")
            except Exception as e:
                rprint(f"[red]Error creating wallet {i+1}/{count}: {str(e)}[/red]")

        rprint(f"[green]Successfully created {successful}/{count} wallets[/green]")
        return wallets

    def import_wallet_from_private_key(self):
        """Import a wallet using private key"""
        try:

            # Use rich.prompt instead of inquirer for private key input
            private_key = Prompt.ask("Enter private key (with or without 0x prefix)")
            if not private_key:
                return None

            private_key = private_key.strip()
            rprint(f"[yellow]Attempting to import key with length: {len(private_key)} chars[/yellow]")

            # Ask for expected address for verification
            expected_address = Prompt.ask("Enter the expected wallet address (for verification, optional)", default="")
            if expected_address:
                rprint(f"[yellow]Will verify against expected address: {expected_address}[/yellow]")

            # Remove 0x prefix if present
            if private_key.startswith('0x'):
                key_hex = private_key[2:]
            else:
                key_hex = private_key

            # Try multiple methods to derive the correct address
            methods_tried = 0

            # Method 1: Direct import with 0x prefix
            methods_tried += 1
            try:
                account = Account.from_key('0x' + key_hex)
                if expected_address and account.address.lower() == expected_address.lower():
                    rprint(f"[green]Success with Method 1! Address matches: {account.address}[/green]")
                    return {
                        'address': account.address,
                        'private_key': '0x' + key_hex,
                        'secret_phrase': 'Imported via private key'
                    }
                else:
                    rprint(f"[yellow]Method {methods_tried}: Got {account.address}, expected {expected_address}[/yellow]")
            except Exception as e:
                rprint(f"[yellow]Method {methods_tried} failed: {str(e)}[/yellow]")

            # Method 2: Try with zero padding using zfill
            methods_tried += 1
            try:
                padded_key = key_hex.zfill(64)
                account = Account.from_key('0x' + padded_key)
                if expected_address and account.address.lower() == expected_address.lower():
                    rprint(f"[green]Success with Method 2! Address matches: {account.address}[/green]")
                    return {
                        'address': account.address,
                        'private_key': '0x' + padded_key,
                        'secret_phrase': 'Imported via private key (padded with zfill)'
                    }
                else:
                    rprint(f"[yellow]Method {methods_tried}: Got {account.address}, expected {expected_address}[/yellow]")
            except Exception as e:
                rprint(f"[yellow]Method {methods_tried} failed: {str(e)}[/yellow]")

            # Method 3: Try with zero padding using rjust
            methods_tried += 1
            try:
                padded_key = key_hex.rjust(64, "0")
                account = Account.from_key('0x' + padded_key)
                if expected_address and account.address.lower() == expected_address.lower():
                    rprint(f"[green]Success with Method 3! Address matches: {account.address}[/green]")
                    return {
                        'address': account.address,
                        'private_key': '0x' + padded_key,
                        'secret_phrase': 'Imported via private key (padded with rjust)'
                    }
                else:
                    rprint(f"[yellow]Method {methods_tried}: Got {account.address}, expected {expected_address}[/yellow]")
            except Exception as e:
                rprint(f"[yellow]Method {methods_tried} failed: {str(e)}[/yellow]")

            # Method 4: Try with base64 decoding (some wallets export in base64)
            methods_tried += 1
            try:
                import base64
                try:
                    # Try to decode as base64
                    decoded = base64.b64decode(key_hex)
                    hex_key = decoded.hex()
                    account = Account.from_key('0x' + hex_key)
                    if expected_address and account.address.lower() == expected_address.lower():
                        rprint(f"[green]Success with Method 4! Address matches: {account.address}[/green]")
                        return {
                            'address': account.address,
                            'private_key': '0x' + hex_key,
                            'secret_phrase': 'Imported via private key (base64 decoded)'
                        }
                    else:
                        rprint(f"[yellow]Method {methods_tried}: Got {account.address}, expected {expected_address}[/yellow]")
                except Exception:
                    rprint(f"[yellow]Method {methods_tried} failed: Not valid base64[/yellow]")
            except Exception as e:
                rprint(f"[yellow]Method {methods_tried} failed: {str(e)}[/yellow]")

            # Method 5: Try with different endianness
            methods_tried += 1
            try:
                # Convert to int and then to bytes with different endianness
                int_key = int(key_hex, 16)
                for endianness in ['big', 'little']:
                    try:
                        bytes_key = int_key.to_bytes(32, byteorder=endianness)
                        account = Account.from_key(bytes_key)
                        if expected_address and account.address.lower() == expected_address.lower():
                            rprint(f"[green]Success with Method 5 ({endianness} endian)! Address matches: {account.address}[/green]")
                            return {
                                'address': account.address,
                                'private_key': '0x' + bytes_key.hex(),
                                'secret_phrase': f'Imported via private key ({endianness} endian)'
                            }
                        else:
                            rprint(f"[yellow]Method {methods_tried} ({endianness}): Got {account.address}, expected {expected_address}[/yellow]")
                    except Exception as inner_e:
                        rprint(f"[yellow]Method {methods_tried} ({endianness}) failed: {str(inner_e)}[/yellow]")
            except Exception as e:
                rprint(f"[yellow]Method {methods_tried} failed: {str(e)}[/yellow]")

            # Method 6: Try with different byte lengths
            methods_tried += 1
            try:
                int_key = int(key_hex, 16)
                for byte_length in range(20, 33):  # Try different byte lengths
                    try:
                        bytes_key = int_key.to_bytes(byte_length, byteorder='big')
                        account = Account.from_key(bytes_key)
                        if expected_address and account.address.lower() == expected_address.lower():
                            rprint(f"[green]Success with Method 6 ({byte_length} bytes)! Address matches: {account.address}[/green]")
                            return {
                                'address': account.address,
                                'private_key': '0x' + bytes_key.hex(),
                                'secret_phrase': f'Imported via private key ({byte_length} bytes)'
                            }
                        else:
                            rprint(f"[yellow]Method {methods_tried} ({byte_length} bytes): Got {account.address}, expected {expected_address}[/yellow]")
                    except Exception:
                        pass  # Skip errors for this method as we're trying many variations
            except Exception as e:
                rprint(f"[yellow]Method {methods_tried} failed: {str(e)}[/yellow]")

            # Method 7: Try with rjust but without 0x prefix
            methods_tried += 1
            try:
                padded_key = key_hex.rjust(64, "0")
                account = Account.from_key(padded_key)  # No 0x prefix
                if expected_address and account.address.lower() == expected_address.lower():
                    rprint(f"[green]Success with Method 7! Address matches: {account.address}[/green]")
                    return {
                        'address': account.address,
                        'private_key': padded_key,  # Store without 0x prefix
                        'secret_phrase': 'Imported via private key (padded with rjust, no prefix)'
                    }
                else:
                    rprint(f"[yellow]Method {methods_tried}: Got {account.address}, expected {expected_address}[/yellow]")
            except Exception as e:
                rprint(f"[yellow]Method {methods_tried} failed: {str(e)}[/yellow]")

            # If we've tried all methods and none worked
            rprint("[red]All import methods failed to match the expected address.[/red]")

            # Ask if they want to use one of the addresses we found
            if expected_address:
                continue_answer = Confirm.ask("Would you like to import one of the addresses we found instead?", default=False)
                if continue_answer:
                    # Try the simplest method again
                    try:
                        if len(key_hex) < 64:
                            padded_key = key_hex.rjust(64, "0")  # Use rjust as requested
                            account = Account.from_key('0x' + padded_key)
                            return {
                                'address': account.address,
                                'private_key': '0x' + padded_key,
                                'secret_phrase': 'Imported via private key (padded with rjust)'
                            }
                        else:
                            account = Account.from_key('0x' + key_hex)
                            return {
                                'address': account.address,
                                'private_key': '0x' + key_hex,
                                'secret_phrase': 'Imported via private key'
                            }
                    except Exception as e:
                        rprint(f"[red]Final import attempt failed: {str(e)}[/red]")
                        return None

            return None

        except KeyboardInterrupt:
            rprint("\n[yellow]Import cancelled by user[/yellow]")
            return None
        except Exception as e:
            rprint(f"[red]Unexpected error: {str(e)}[/red]")
            return None

    def import_wallet_from_mnemonic(self):
        """Import a wallet using mnemonic phrase"""
        try:
            Account.enable_unaudited_hdwallet_features()
            questions = [
                inquirer.Text('mnemonic',
                             message="Enter mnemonic phrase (12 or 24 words)")
            ]
            answers = inquirer.prompt(questions)
            if not answers:
                return None

            account = Account.from_mnemonic(answers['mnemonic'])
            return {
                'address': account.address,
                'private_key': account.key.hex(),
                'secret_phrase': answers['mnemonic']
            }
        except KeyboardInterrupt:
            rprint("\n[yellow]Import cancelled by user[/yellow]")
            return None
        except Exception:
            rprint("[red]Invalid mnemonic phrase![/red]")
            return None

    def get_bnb_balance(self, address):
        """Get BNB balance for a wallet"""
        try:
            # Check if we should convert to checksum address
            load_dotenv()  # Make sure we have the latest env variables
            convert_checksum = os.getenv('CONVERT_CHECKSUM_ADDRESS', 'false').lower() == 'true'

            # Always convert to checksum address if the setting is enabled
            # This prevents errors later in the process
            if convert_checksum:
                try:
                    checksum_address = Web3.to_checksum_address(address.lower())
                    if checksum_address != address:
                        rprint(f"[yellow]Converting to checksum address for BNB balance: {address} -> {checksum_address}[/yellow]")
                    address = checksum_address  # Use the checksum address from now on
                except Exception as convert_error:
                    rprint(f"[yellow]Error converting to checksum address: {str(convert_error)}[/yellow]")
                    # Continue with original address, but it might fail later

            # Get BNB balance
            try:
                balance_wei = self.w3.eth.get_balance(address)
                return float(self.w3.from_wei(balance_wei, 'ether'))
            except ValueError as checksum_error:
                if "web3.py only accepts checksum addresses" in str(checksum_error):
                    if convert_checksum:
                        # We already tried to convert above, so this is a different issue
                        rprint(f"[yellow]Address still not accepted after checksum conversion: {address}[/yellow]")
                    else:
                        rprint(f"[yellow]Checksum address error and conversion not enabled: {str(checksum_error)}[/yellow]")
                    return 0.0
                else:
                    # Some other ValueError
                    rprint(f"[yellow]Error getting BNB balance: {str(checksum_error)}[/yellow]")
                    return 0.0
            except Exception as e:
                rprint(f"[yellow]Error getting BNB balance: {str(e)}[/yellow]")
                return 0.0
        except Exception as e:
            rprint(f"[yellow]Error getting BNB balance: {str(e)}[/yellow]")
            return 0.0

    def get_token_balance(self, token_address, wallet_address, token_manager):
        """Get balance for a specific token"""
        try:
            # Validate inputs
            if not token_address or not wallet_address:
                rprint(f"[yellow]Invalid address: token={token_address}, wallet={wallet_address}[/yellow]")
                return 0

            # Check if we should convert to checksum address
            load_dotenv()  # Make sure we have the latest env variables
            convert_checksum = os.getenv('CONVERT_CHECKSUM_ADDRESS', 'false').lower() == 'true'

            # Always convert addresses to checksum format if the setting is enabled
            if convert_checksum:
                try:
                    # Convert wallet address
                    checksum_wallet_address = Web3.to_checksum_address(wallet_address.lower())
                    if checksum_wallet_address != wallet_address:
                        rprint(f"[yellow]Converting wallet to checksum address: {wallet_address} -> {checksum_wallet_address}[/yellow]")
                    wallet_address = checksum_wallet_address

                    # Convert token address
                    checksum_token_address = Web3.to_checksum_address(token_address.lower())
                    if checksum_token_address != token_address:
                        rprint(f"[yellow]Converting token to checksum address: {token_address} -> {checksum_token_address}[/yellow]")
                    token_address = checksum_token_address
                except Exception as convert_error:
                    rprint(f"[yellow]Error converting to checksum address: {str(convert_error)}[/yellow]")
                    # Continue with original addresses, but it might fail later

            # Try to get token balance
            try:
                # Get the token balance from the token manager
                rprint(f"[cyan]Getting balance for token {token_address} and wallet {wallet_address}...[/cyan]")
                raw_balance = token_manager.get_token_balance(token_address, wallet_address)

                # Check if we got a valid balance
                if raw_balance is None:
                    rprint(f"[yellow]Token balance returned None for {token_address}[/yellow]")
                    return 0

                # Return the raw balance
                return raw_balance

            except ValueError as checksum_error:
                if "web3.py only accepts checksum addresses" in str(checksum_error):
                    if convert_checksum:
                        # We already tried to convert above, so this is a different issue
                        rprint(f"[yellow]Addresses still not accepted after checksum conversion: {token_address}, {wallet_address}[/yellow]")
                    else:
                        rprint(f"[yellow]Checksum address error and conversion not enabled: {str(checksum_error)}[/yellow]")
                    return 0
                else:
                    # Some other ValueError
                    rprint(f"[yellow]Error getting token balance: {str(checksum_error)}[/yellow]")
                    return 0
            except Exception as e:
                # Handle other exceptions
                error_msg = str(e)
                if "Could not decode contract function call" in error_msg:
                    rprint(f"[yellow]Warning: Token at {token_address} may not be a valid ERC20 token or has issues with the balanceOf function.[/yellow]")
                elif "NoneType" in error_msg:
                    rprint(f"[yellow]Warning: Token contract could not be created for {token_address}[/yellow]")
                else:
                    rprint(f"[yellow]Warning: Error getting balance for token at {token_address}: {error_msg}[/yellow]")
                return 0
        except Exception as e:
            # Log the error but don't stop the process
            error_msg = str(e)
            rprint(f"[yellow]Warning: Unexpected error getting token balance: {error_msg}[/yellow]")
            return 0

    def get_last_transaction_date(self, address):
        """Get the date of the last transaction for a wallet using BSCScan API"""
        try:
            # Check if we should convert to checksum address
            load_dotenv()  # Make sure we have the latest env variables
            convert_checksum = os.getenv('CONVERT_CHECKSUM_ADDRESS', 'false').lower() == 'true'

            # Always convert to checksum address if the setting is enabled
            if convert_checksum:
                try:
                    checksum_address = Web3.to_checksum_address(address.lower())
                    if checksum_address != address:
                        rprint(f"[yellow]Converting to checksum address: {address} -> {checksum_address}[/yellow]")
                    address = checksum_address  # Use the checksum address from now on
                except Exception as convert_error:
                    rprint(f"[yellow]Error converting to checksum address: {str(convert_error)}[/yellow]")
                    # Continue with original address, but it might fail later

            # Use BSCScan API to get transaction history
            from src.bscscan import get_transaction_history

            # Determine which network we're on (mainnet or testnet)
            network = 'mainnet'  # Default to mainnet
            if hasattr(self, 'network'):
                network = self.network
            elif hasattr(self.w3, 'chain_id'):
                chain_id = self.w3.eth.chain_id
                if chain_id == 97:
                    network = 'testnet'

            # Get the most recent transaction (just 1 is enough)
            rprint(f"[cyan]Fetching transaction history from BSCScan for {address}...[/cyan]")
            transactions = get_transaction_history(address, network=network, offset=1)

            if not transactions:
                rprint(f"[yellow]No transactions found for {address} on BSCScan[/yellow]")
                return ""

            # Get the most recent transaction (should be the first one since we sort by desc)
            latest_tx = transactions[0]

            # Convert timestamp to datetime
            import datetime
            timestamp = int(latest_tx.get('timeStamp', 0))
            if timestamp > 0:
                tx_date = datetime.datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
                rprint(f"[green]Found transaction from {tx_date} (Block: {latest_tx.get('blockNumber', 'unknown')})[/green]")
                return tx_date
            else:
                rprint(f"[yellow]Transaction found but no valid timestamp for {address}[/yellow]")
                return ""

        except Exception as e:
            rprint(f"[yellow]Error getting last transaction date from BSCScan: {str(e)}[/yellow]")

            # Fallback: Try to get transaction count from the blockchain
            try:
                tx_count = self.w3.eth.get_transaction_count(address)
                if tx_count > 0:
                    rprint(f"[yellow]Address has {tx_count} transactions but couldn't get date from BSCScan[/yellow]")
                    # Return a placeholder indicating there are transactions but date is unknown
                    return "Has transactions (date unknown)"
                else:
                    return ""  # No transactions
            except Exception:
                return ""  # Return empty string if all methods fail

    def update_wallet_balances(self, token_manager):
        """Update wallet balances in the CSV file"""
        try:
            wallets = self.get_wallet_list_basic()
            if not wallets:
                rprint("[yellow]No wallets found to update.[/yellow]")
                return False

            # Load mainnet tokens
            mainnet_tokens = token_manager.load_tokens()
            if not mainnet_tokens:
                rprint("[yellow]No tokens found in mainnet_tokens.csv. Please add tokens first.[/yellow]")
                return False

            rprint(f"[cyan]Found {len(wallets)} wallets and {len(mainnet_tokens)} tokens to process.[/cyan]")

            # Find BTC and ETH tokens
            btc_token = next((t for t in mainnet_tokens if t['Symbol'] == 'BTCB'), None)
            eth_token = next((t for t in mainnet_tokens if t['Symbol'] == 'ETH'), None)

            if not btc_token:
                rprint("[yellow]Warning: BTCB token not found in mainnet_tokens.csv[/yellow]")
            if not eth_token:
                rprint("[yellow]Warning: ETH token not found in mainnet_tokens.csv[/yellow]")

            # Define CSV field names
            fieldnames = ['Address', 'Private Key', 'Secret Phrase', 'bnb_balance', 'btc_balance', 'eth_balance', 'other_tokens', 'last_transaction_date']

            # Create a temporary file to store updated wallets
            import tempfile
            import shutil
            temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, newline='')

            # Write header to temp file
            writer = csv.DictWriter(temp_file, fieldnames=fieldnames)
            writer.writeheader()

            # Track progress
            total_wallets = len(wallets)
            current_wallet = 0
            updated_wallets = []

            for wallet in wallets:
                current_wallet += 1
                address = wallet['Address']

                rprint(f"[cyan]Processing wallet {current_wallet}/{total_wallets}: {address}[/cyan]")

                # Get BNB balance
                try:
                    bnb_balance = self.get_bnb_balance(address)
                    bnb_balance_str = f"{bnb_balance:.8f}" if bnb_balance > 0 else "0"
                except Exception as e:
                    rprint(f"[yellow]Warning: Error getting BNB balance for {address}: {str(e)}[/yellow]")
                    bnb_balance_str = "0"

                # Get BTC balance if token exists
                btc_balance = "0"
                if btc_token:
                    try:
                        raw_balance = self.get_token_balance(btc_token['Address'], address, token_manager)
                        if raw_balance > 0:
                            decimals = int(btc_token['Decimals'])
                            btc_balance_float = float(raw_balance) / (10 ** decimals)
                            btc_balance = f"{btc_balance_float:.8f}"
                    except Exception as e:
                        rprint(f"[yellow]Warning: Error getting BTCB balance for {address}: {str(e)}[/yellow]")

                # Get ETH balance if token exists
                eth_balance = "0"
                if eth_token:
                    try:
                        raw_balance = self.get_token_balance(eth_token['Address'], address, token_manager)
                        if raw_balance > 0:
                            decimals = int(eth_token['Decimals'])
                            eth_balance_float = float(raw_balance) / (10 ** decimals)
                            eth_balance = f"{eth_balance_float:.8f}"
                    except Exception as e:
                        rprint(f"[yellow]Warning: Error getting ETH balance for {address}: {str(e)}[/yellow]")

                # Get other token balances
                other_tokens = {}
                tokens_processed = 0
                tokens_with_balance = 0

                for token in mainnet_tokens:
                    # Skip BTC and ETH as they're handled separately
                    if token['Symbol'] in ['BTCB', 'ETH']:
                        continue

                    tokens_processed += 1
                    if tokens_processed % 10 == 0:
                        rprint(f"[cyan]  Processed {tokens_processed}/{len(mainnet_tokens) - 2} tokens for wallet {address}[/cyan]")

                    try:
                        # Make sure we have valid addresses
                        if not token['Address'] or not address:
                            continue

                        # Get token balance with detailed logging
                        rprint(f"[cyan]  Checking balance for {token['Symbol']} ({token['Address'][:8]}...)[/cyan]")
                        raw_balance = self.get_token_balance(token['Address'], address, token_manager)

                        # Process non-zero balances
                        if raw_balance > 0:
                            decimals = int(token['Decimals'])
                            token_balance = float(raw_balance) / (10 ** decimals)
                            formatted_balance = f"{token_balance:.8f}"
                            other_tokens[token['Symbol']] = formatted_balance
                            tokens_with_balance += 1
                            rprint(f"[green]  Found {token['Symbol']} balance: {formatted_balance}[/green]")
                    except Exception as e:
                        rprint(f"[yellow]  Error getting {token['Symbol']} balance: {str(e)}[/yellow]")
                        # Continue with next token

                # Convert other_tokens to semicolon-separated string format: "TOKEN:VALUE;TOKEN:VALUE"
                other_tokens_str = ";".join([f"{k}:{v}" for k, v in other_tokens.items()]) if other_tokens else ""

                # Get last transaction date using BSCScan API
                try:
                    rprint(f"[cyan]  Getting last transaction date for {address} using BSCScan API...[/cyan]")
                    last_tx_date = self.get_last_transaction_date(address)
                    if last_tx_date:
                        if "unknown" in last_tx_date.lower():
                            rprint(f"[yellow]  {last_tx_date}[/yellow]")
                        else:
                            rprint(f"[green]  Found last transaction date: {last_tx_date}[/green]")
                    else:
                        rprint(f"[yellow]  No transactions found for {address}[/yellow]")
                except Exception as e:
                    rprint(f"[yellow]Warning: Error getting last transaction date for {address}: {str(e)}[/yellow]")
                    last_tx_date = ""

                # Create updated wallet record
                updated_wallet = {
                    'Address': address,
                    'Private Key': wallet.get('Private Key', ''),
                    'Secret Phrase': wallet.get('Secret Phrase', ''),
                    'bnb_balance': bnb_balance_str,
                    'btc_balance': btc_balance,
                    'eth_balance': eth_balance,
                    'other_tokens': other_tokens_str,
                    'last_transaction_date': last_tx_date
                }

                # Write this wallet to the temp file immediately
                writer.writerow(updated_wallet)
                updated_wallets.append(updated_wallet)

                # Show summary for this wallet
                token_summary = f"BNB={bnb_balance_str}, BTC={btc_balance}, ETH={eth_balance}"
                if tokens_with_balance > 0:
                    token_list = ", ".join(other_tokens.keys())
                    token_summary += f", Other tokens ({tokens_with_balance}): {token_list}"
                last_tx_info = f", Last TX: {last_tx_date}" if last_tx_date else ""
                rprint(f"[green]Updated balances for wallet {address}: {token_summary}{last_tx_info}[/green]")

                # Flush the file to ensure data is written
                temp_file.flush()

            # Close the temp file
            temp_file.close()

            # Replace the original file with the temp file
            shutil.move(temp_file.name, self.wallet_file)

            rprint(f"[green]Successfully updated balances for {len(updated_wallets)} wallets[/green]")
            return True
        except Exception as e:
            rprint(f"[red]Error updating wallet balances: {str(e)}[/red]")
            # If we have a temp file, try to close and remove it
            if 'temp_file' in locals():
                try:
                    temp_file.close()
                    import os
                    if os.path.exists(temp_file.name):
                        os.unlink(temp_file.name)
                except:
                    pass
            return False

    def display_wallet_balances(self, address, token_balances):
        """Display all balances for a wallet"""
        rprint(f"\n[bold cyan]Wallet Balances for {address}[/bold cyan]")

        if not token_balances:
            rprint("[yellow]No balances found for this wallet[/yellow]")
            return

        table = Table()
        table.add_column("Token", style="cyan")
        table.add_column("Balance", style="green")
        table.add_column("Value", style="yellow")

        # Sort balances with BNB first, then alphabetically
        sorted_balances = sorted(token_balances, key=lambda x: (0 if x[0] == 'BNB' else 1, x[0]))

        for token, balance in sorted_balances:
            # Format balance based on size
            if balance == 0:  # Zero balance
                formatted_balance = "0"
            elif balance < 0.00000001:  # Very small balance
                formatted_balance = f"{balance:.12f}"
            elif balance < 0.0001:  # Small balance
                formatted_balance = f"{balance:.10f}"
            elif balance < 1:  # Medium balance
                formatted_balance = f"{balance:.8f}"
            else:  # Large balance
                formatted_balance = f"{balance:.6f}"

            # For now, leave value column empty (could be filled with price data in future)
            table.add_row(token, formatted_balance, "")

        self.console.print(table)

    def view_wallets(self):
        """Display all wallets in a table"""
        if not os.path.exists(self.wallet_file):
            rprint("[red]No wallets found![/red]")
            return

        table = Table(title="Stored Wallets")
        table.add_column("Address", style="cyan")
        table.add_column("Private Key", style="magenta")
        table.add_column("Secret Phrase", style="green")
        table.add_column("BNB", style="yellow")
        table.add_column("BTC", style="yellow")
        table.add_column("ETH", style="yellow")
        table.add_column("Other Tokens", style="yellow")
        table.add_column("Last Transaction", style="blue")

        with open(self.wallet_file, 'r') as file:
            reader = csv.DictReader(file)
            for row in reader:
                # Get other tokens string (already in "TOKEN:VALUE;TOKEN:VALUE" format)
                other_tokens_str = row.get('other_tokens', "")
                # Replace semicolons with commas for better readability in the table
                if other_tokens_str:
                    other_tokens_str = other_tokens_str.replace(";", ", ")

                # Truncate private key and secret phrase for display
                table.add_row(
                    row['Address'],
                    row.get('Private Key', '')[:10] + "..." if row.get('Private Key') else "",
                    row.get('Secret Phrase', '')[:15] + "..." if row.get('Secret Phrase') else "",
                    row.get('bnb_balance', '0'),
                    row.get('btc_balance', '0'),
                    row.get('eth_balance', '0'),
                    other_tokens_str[:30] + "..." if len(other_tokens_str) > 30 else other_tokens_str,
                    row.get('last_transaction_date', '')
                )

        self.console.print(table)

    def select_wallet(self, wallets, message="Select a wallet", token_info=None, token_manager=None, is_sender=False, require_private_key=False):
        """Present wallet selection menu with optional token balance display"""
        try:
            # Filter wallets if private key is required (for sender wallets)
            filtered_wallets = wallets
            if require_private_key and is_sender:
                filtered_wallets = [w for w in wallets if w.get('Private Key', '').strip() != '']
                if not filtered_wallets:
                    rprint("[red]No wallets with private keys found! Transactions require a wallet with a private key.[/red]")
                    return None

            # If token_info is provided, show token balances
            if token_info and token_manager:
                choices = []
                wallets_with_token_balance = []

                for w in filtered_wallets:
                    address = w['Address']
                    # Get token balance
                    raw_balance = token_manager.get_token_balance(token_info['Address'], address)
                    # Convert to human-readable format
                    decimals = int(token_info['Decimals'])
                    token_balance = float(raw_balance) / (10 ** decimals)

                    # For senders, filter out wallets with zero token balance
                    if is_sender and token_balance <= 0:
                        continue

                    # Store wallet with its balance for display
                    wallets_with_token_balance.append((w, token_balance))

                # Check if we have any wallets with token balance
                if is_sender and not wallets_with_token_balance:
                    rprint(f"[red]No wallets found with {token_info['Symbol']} balance! You need to have some {token_info['Symbol']} to send.[/red]")
                    return None

                # Create choices for display
                for w, token_balance in wallets_with_token_balance:
                    address = w['Address']
                    # For senders, also show BNB balance (needed for gas)
                    if is_sender:
                        bnb_balance = self.get_bnb_balance(address)
                        choices.append(f"{address} (Token: {token_balance:.8f} {token_info['Symbol']}, BNB: {bnb_balance:.8f})")
                    else:
                        # For recipients, show token balance and secret phrase
                        secret_phrase = w.get('Secret Phrase', '')
                        # Truncate secret phrase to first 15 chars + ellipsis
                        if secret_phrase:
                            truncated_phrase = secret_phrase[:15] + "..." if len(secret_phrase) > 15 else secret_phrase
                            choices.append(f"{address} ({truncated_phrase}) (Balance: {token_balance:.8f} {token_info['Symbol']})")
                        else:
                            choices.append(f"{address} (Balance: {token_balance:.8f} {token_info['Symbol']})")
            else:
                # Default to BNB balance
                # For senders, filter out wallets with zero BNB balance (needed for gas)
                if is_sender:
                    wallets_with_bnb = []
                    for w in filtered_wallets:
                        address = w['Address']
                        bnb_balance = self.get_bnb_balance(address)
                        if bnb_balance > 0:
                            wallets_with_bnb.append((w, bnb_balance))

                    if not wallets_with_bnb:
                        rprint("[red]No wallets found with BNB balance! You need BNB for gas fees.[/red]")
                        return None

                    choices = [f"{w['Address']} (Balance: {balance} BNB)" for w, balance in wallets_with_bnb]
                else:
                    # For recipients, include secret phrase in display
                    choices = []
                    for w in filtered_wallets:
                        address = w['Address']
                        bnb_balance = self.get_bnb_balance(address)
                        secret_phrase = w.get('Secret Phrase', '')

                        # Truncate secret phrase to first 15 chars + ellipsis
                        if secret_phrase:
                            truncated_phrase = secret_phrase[:15] + "..." if len(secret_phrase) > 15 else secret_phrase
                            choices.append(f"{address} ({truncated_phrase}) (Balance: {bnb_balance} BNB)")
                        else:
                            choices.append(f"{address} (Balance: {bnb_balance} BNB)")

            choices.append("Other (Enter address manually)")

            questions = [
                inquirer.List('wallet',
                             message=message,
                             choices=choices)
            ]
            answer = inquirer.prompt(questions)
            if not answer:
                return None

            if answer['wallet'].startswith("Other"):
                address_q = [
                    inquirer.Text('address', message="Enter wallet address"),
                    inquirer.Text('private_key', message="Enter private key (optional)")
                ]
                wallet_info = inquirer.prompt(address_q)
                if not wallet_info:
                    return None

                # Ask if they want to save this wallet
                save_q = [
                    inquirer.Confirm('save',
                                   message="Would you like to save this wallet for future use?",
                                   default=False)
                ]
                save_answer = inquirer.prompt(save_q)
                if not save_answer:
                    return wallet_info

                if save_answer['save'] and wallet_info['private_key']:
                    new_wallet = {
                        'address': wallet_info['address'],
                        'private_key': wallet_info['private_key'],
                        'secret_phrase': 'Imported wallet'
                    }
                    self.save_wallet(new_wallet)
                    rprint("[green]Wallet saved successfully![/green]")

                return wallet_info
            else:
                selected_address = answer['wallet'].split(" ")[0]
                # If we have token_info and filtered wallets with token balance, use those
                if token_info and token_manager and wallets_with_token_balance:
                    for w, _ in wallets_with_token_balance:
                        if w['Address'] == selected_address:
                            return w
                    return None
                # If we're selecting a sender wallet for BNB transaction, use wallets with BNB
                elif is_sender and 'wallets_with_bnb' in locals() and wallets_with_bnb:
                    for w, _ in wallets_with_bnb:
                        if w['Address'] == selected_address:
                            return w
                    return None
                else:
                    return next((w for w in filtered_wallets if w['Address'] == selected_address), None)
        except KeyboardInterrupt:
            return None
        except Exception as e:
            rprint(f"[red]Error selecting wallet: {str(e)}[/red]")
            return None

    def select_multiple_wallets(self, wallets, message="Select wallets", token_info=None, token_manager=None, is_sender=False, require_private_key=False):
        """Present multi-select wallet menu with optional token balance display"""
        try:
            # Filter wallets if private key is required (for sender wallets)
            filtered_wallets = wallets
            if require_private_key and is_sender:
                filtered_wallets = [w for w in wallets if w.get('Private Key', '').strip() != '']
                if not filtered_wallets:
                    rprint("[red]No wallets with private keys found! Transactions require a wallet with a private key.[/red]")
                    return None

            # If token_info is provided, show token balances
            if token_info and token_manager:
                choices = []
                wallets_with_token_balance = []
                wallet_address_map = {}  # Map to store address -> wallet for lookup later

                for w in filtered_wallets:
                    address = w['Address']
                    # Get token balance
                    raw_balance = token_manager.get_token_balance(token_info['Address'], address)
                    # Convert to human-readable format
                    decimals = int(token_info['Decimals'])
                    token_balance = float(raw_balance) / (10 ** decimals)

                    # For senders, filter out wallets with zero token balance
                    if is_sender and token_balance <= 0:
                        continue

                    # Store wallet with its balance for display
                    wallets_with_token_balance.append((w, token_balance))
                    wallet_address_map[address] = w

                # Check if we have any wallets with token balance
                if is_sender and not wallets_with_token_balance:
                    rprint(f"[red]No wallets found with {token_info['Symbol']} balance! You need to have some {token_info['Symbol']} to send.[/red]")
                    return None

                # Create choices for display
                for w, token_balance in wallets_with_token_balance:
                    address = w['Address']
                    # For senders, also show BNB balance (needed for gas)
                    if is_sender:
                        bnb_balance = self.get_bnb_balance(address)
                        choices.append(f"{address} (Token: {token_balance:.8f} {token_info['Symbol']}, BNB: {bnb_balance:.8f})")
                    else:
                        # For recipients, show token balance and secret phrase
                        secret_phrase = w.get('Secret Phrase', '')
                        # Truncate secret phrase to first 15 chars + ellipsis
                        if secret_phrase:
                            truncated_phrase = secret_phrase[:15] + "..." if len(secret_phrase) > 15 else secret_phrase
                            choices.append(f"{address} ({truncated_phrase}) (Balance: {token_balance:.8f} {token_info['Symbol']})")
                        else:
                            choices.append(f"{address} (Balance: {token_balance:.8f} {token_info['Symbol']})")
            else:
                # Default to BNB balance
                # For senders, filter out wallets with zero BNB balance (needed for gas)
                if is_sender:
                    wallets_with_bnb = []
                    wallet_address_map = {}  # Map to store address -> wallet for lookup later

                    for w in filtered_wallets:
                        address = w['Address']
                        bnb_balance = self.get_bnb_balance(address)
                        if bnb_balance > 0:
                            wallets_with_bnb.append((w, bnb_balance))
                            wallet_address_map[address] = w

                    if not wallets_with_bnb:
                        rprint("[red]No wallets found with BNB balance! You need BNB for gas fees.[/red]")
                        return None

                    choices = [f"{w['Address']} (Balance: {balance} BNB)" for w, balance in wallets_with_bnb]
                else:
                    # For recipients, include secret phrase in display
                    choices = []
                    for w in filtered_wallets:
                        address = w['Address']
                        bnb_balance = self.get_bnb_balance(address)
                        secret_phrase = w.get('Secret Phrase', '')

                        # Truncate secret phrase to first 15 chars + ellipsis
                        if secret_phrase:
                            truncated_phrase = secret_phrase[:15] + "..." if len(secret_phrase) > 15 else secret_phrase
                            choices.append(f"{address} ({truncated_phrase}) (Balance: {bnb_balance} BNB)")
                        else:
                            choices.append(f"{address} (Balance: {bnb_balance} BNB)")

            choices.insert(0, "All Wallets")

            questions = [
                inquirer.Checkbox('wallets',
                                message=message,
                                choices=choices)
            ]
            answer = inquirer.prompt(questions)
            if not answer:
                return None

            selected_wallets = []
            if "All Wallets" in answer['wallets']:
                # If token_info is provided and is_sender is True, only return wallets with token balance
                if token_info and token_manager and is_sender:
                    return [w for w, _ in wallets_with_token_balance]
                # If is_sender is True but no token_info, return wallets with BNB balance
                elif is_sender and wallets_with_bnb:
                    return [w for w, _ in wallets_with_bnb]
                else:
                    return filtered_wallets

            for selection in answer['wallets']:
                address = selection.split(" ")[0]
                # Use the wallet_address_map if available, otherwise fall back to the old method
                if token_info and token_manager:
                    wallet = wallet_address_map.get(address)
                elif is_sender and 'wallet_address_map' in locals() and wallet_address_map:
                    wallet = wallet_address_map.get(address)
                else:
                    wallet = next((w for w in filtered_wallets if w['Address'] == address), None)

                if wallet:
                    selected_wallets.append(wallet)

            return selected_wallets
        except KeyboardInterrupt:
            return None
        except Exception as e:
            rprint(f"[red]Error selecting wallets: {str(e)}[/red]")
            return None
