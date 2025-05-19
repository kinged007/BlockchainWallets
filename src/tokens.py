import csv
import os
from rich.table import Table
import inquirer
from rich import print as rprint
from web3 import Web3
from typing import Dict, List, Tuple
from .config import MULTICALL_ABI
from .bscscan import get_contract_abi



class TokenManager:
    def __init__(self, w3: Web3, tokens_file: str, console, abi, multicall_address: str, network='mainnet'):
        self.w3 = w3
        self.tokens_file = tokens_file
        self.console = console
        self.abi = abi
        self.network = network
        self.token_contracts: Dict[str, object] = {}  # Cache for token contracts
        self.token_abis: Dict[str, list] = {}  # Cache for token ABIs
        self.problem_tokens = set()  # Set to track tokens that cause timeouts or other issues

        # Initialize multicall contract
        self.multicall = self.w3.eth.contract(
            address=Web3.to_checksum_address(multicall_address),
            abi=MULTICALL_ABI
        )
        self.ensure_token_file()

    def ensure_token_file(self):
        """Ensure token file exists"""
        if not os.path.exists(self.tokens_file):
            with open(self.tokens_file, 'w', newline='') as file:
                writer = csv.writer(file)
                writer.writerow(['Address', 'Symbol', 'Decimals', 'Name'])

    def load_tokens(self):
        """Load tokens from CSV file"""
        tokens = []
        with open(self.tokens_file, 'r') as file:
            reader = csv.DictReader(file)
            tokens = list(reader)
        return tokens

    def get_token_contract(self, address: str, for_transfer=False):
        """Get or create token contract instance with appropriate ABI"""
        try:
            # Ensure address is in checksum format
            address = Web3.to_checksum_address(address)

            # If we need the contract for transfer and don't have the full ABI yet, fetch it
            if for_transfer and address not in self.token_abis:
                rprint(f"[cyan]Fetching full ABI for token contract {address}...[/cyan]")
                full_abi = get_contract_abi(address, self.network)
                if full_abi:
                    # Check if the ABI contains the transfer function
                    has_transfer = False
                    for item in full_abi:
                        if item.get('name') == 'transfer' and item.get('type') == 'function':
                            has_transfer = True
                            break

                    if has_transfer:
                        rprint(f"[green]Successfully fetched full ABI with transfer function[/green]")
                    else:
                        rprint(f"[yellow]Warning: ABI does not contain transfer function. This may not be a standard ERC20 token.[/yellow]")

                    self.token_abis[address] = full_abi
                    # If we already have a contract instance, update it with the full ABI
                    if address in self.token_contracts:
                        self.token_contracts[address] = self.w3.eth.contract(
                            address=address,
                            abi=full_abi
                        )
                else:
                    rprint(f"[yellow]Warning: Could not fetch full ABI for {address}. Using limited ABI.[/yellow]")
                    # Add a basic transfer function to the limited ABI if it's not already there
                    transfer_abi = {
                        "constant": False,
                        "inputs": [
                            {"name": "_to", "type": "address"},
                            {"name": "_value", "type": "uint256"}
                        ],
                        "name": "transfer",
                        "outputs": [{"name": "", "type": "bool"}],
                        "type": "function"
                    }

                    # Check if transfer is already in the ABI
                    has_transfer = False
                    for item in self.abi:
                        if item.get('name') == 'transfer':
                            has_transfer = True
                            break

                    # If not, add it
                    if not has_transfer:
                        extended_abi = self.abi.copy()
                        extended_abi.append(transfer_abi)
                        rprint(f"[yellow]Adding basic transfer function to limited ABI for {address}.[/yellow]")
                        self.token_abis[address] = extended_abi
                    else:
                        self.token_abis[address] = self.abi

            # Create contract instance if it doesn't exist
            if address not in self.token_contracts:
                # Use full ABI if available, otherwise use limited ABI
                contract_abi = self.token_abis.get(address, self.abi)

                # Log what we're doing
                rprint(f"[cyan]Creating contract instance for token at {address}...[/cyan]")

                # Create the contract instance
                try:
                    self.token_contracts[address] = self.w3.eth.contract(
                        address=address,
                        abi=contract_abi
                    )
                    rprint(f"[green]Successfully created contract instance for {address}[/green]")
                except Exception as contract_error:
                    rprint(f"[red]Error creating contract instance: {str(contract_error)}[/red]")
                    # Try with just the basic ERC20 ABI as a fallback
                    rprint(f"[yellow]Trying with basic ERC20 ABI as fallback...[/yellow]")
                    self.token_contracts[address] = self.w3.eth.contract(
                        address=address,
                        abi=self.abi
                    )

            return self.token_contracts[address]

        except Exception as e:
            rprint(f"[red]Error in get_token_contract for {address}: {str(e)}[/red]")
            # Create a minimal contract with just the basic ERC20 ABI
            try:
                rprint(f"[yellow]Creating minimal contract with basic ERC20 ABI...[/yellow]")
                minimal_contract = self.w3.eth.contract(
                    address=address,
                    abi=self.abi
                )
                # Cache it for future use
                self.token_contracts[address] = minimal_contract
                return minimal_contract
            except Exception as fallback_error:
                rprint(f"[red]Fatal error creating token contract: {str(fallback_error)}[/red]")
                # Return None - the calling code will need to handle this
                return None

    def get_token_balances(self, wallet_address: str, tokens: List[dict]) -> List[Tuple[str, float]]:
        """Get balances for multiple tokens using multicall with fallback to individual calls"""
        if not tokens:
            return []

        balances = []

        # First try using multicall for efficiency
        try:
            # Ensure wallet address is in checksum format
            try:
                checksum_wallet_address = Web3.to_checksum_address(wallet_address)
            except ValueError as checksum_error:
                # Handle checksum address error
                if "web3.py only accepts checksum addresses" in str(checksum_error):
                    # Convert to lowercase first, then to checksum address
                    checksum_wallet_address = Web3.to_checksum_address(wallet_address.lower())
                else:
                    raise checksum_error

            # Prepare calls for balanceOf
            calls = []
            valid_tokens = []

            tokens_skipped = 0
            for token in tokens:
                try:
                    # Check if this is a known problematic token
                    try:
                        checksum_address = Web3.to_checksum_address(token['Address'])
                        if checksum_address in self.problem_tokens:
                            tokens_skipped += 1
                            continue
                    except Exception:
                        # If we can't convert to checksum, just try anyway
                        pass

                    token_contract = self.get_token_contract(token['Address'])

                    # Check if the contract has the balanceOf function
                    if not hasattr(token_contract.functions, 'balanceOf'):
                        continue

                    balance_data = token_contract.encode_abi(
                        abi_element_identifier='balanceOf',
                        args=[checksum_wallet_address]
                    )
                    calls.append({
                        'target': Web3.to_checksum_address(token['Address']),
                        'callData': balance_data
                    })
                    valid_tokens.append(token)
                except Exception as e:
                    # Skip tokens that cause errors
                    rprint(f"[yellow]Skipping token {token.get('Symbol', 'unknown')} in multicall: {str(e)}[/yellow]")
                    continue

            if tokens_skipped > 0:
                rprint(f"[cyan]Skipped {tokens_skipped} known problematic tokens in multicall setup[/cyan]")

            # If we have no valid tokens, return empty list
            if not valid_tokens:
                return []

            # Make multicall
            try:
                _, return_data = self.multicall.functions.aggregate(calls).call(timeout=30)  # 30 second timeout
            except Exception as e:
                rprint(f"[yellow]Warning: Multicall failed: {str(e)}[/yellow]")
                rprint("[yellow]Falling back to individual token balance checks...[/yellow]")
                return self._get_individual_token_balances(wallet_address, tokens)

            # Process results
            for i, token in enumerate(valid_tokens):
                try:
                    balance = self.w3.codec.decode(['uint256'], return_data[i])[0]
                    decimals = int(token['Decimals'])
                    balance_float = float(balance) / (10 ** decimals)
                    balances.append((token['Symbol'], balance_float))
                except Exception:
                    # Skip tokens that cause errors in decoding
                    continue

            return balances

        except Exception as e:
            rprint(f"[yellow]Warning: Multicall setup failed: {str(e)}[/yellow]")
            rprint("[yellow]Falling back to individual token balance checks...[/yellow]")
            return self._get_individual_token_balances(wallet_address, tokens)

    def _get_individual_token_balances(self, wallet_address: str, tokens: List[dict]) -> List[Tuple[str, float]]:
        """Get balances for tokens individually as a fallback"""
        balances = []
        tokens_processed = 0
        tokens_skipped = 0

        for token in tokens:
            try:
                # Check if this is a known problematic token
                try:
                    checksum_address = Web3.to_checksum_address(token['Address'])
                    if checksum_address in self.problem_tokens:
                        tokens_skipped += 1
                        continue
                except Exception:
                    # If we can't convert to checksum, just try anyway
                    pass

                tokens_processed += 1
                if tokens_processed % 10 == 0:
                    rprint(f"[cyan]Processed {tokens_processed} tokens, skipped {tokens_skipped} problematic tokens[/cyan]")

                # Get the token balance
                raw_balance = self.get_token_balance(token['Address'], wallet_address)
                if raw_balance > 0:
                    decimals = int(token['Decimals'])
                    balance_float = float(raw_balance) / (10 ** decimals)
                    balances.append((token['Symbol'], balance_float))
                    rprint(f"[green]Found balance for {token['Symbol']}: {balance_float}[/green]")
            except Exception as e:
                # Skip tokens that cause errors
                rprint(f"[yellow]Error processing token {token.get('Symbol', 'unknown')}: {str(e)}[/yellow]")
                continue

        # Show summary
        rprint(f"[cyan]Token balance check complete: processed {tokens_processed}, skipped {tokens_skipped}, found {len(balances)} with balance[/cyan]")
        return balances

    def verify_token(self, address):
        """Verify token contract and get its details"""
        try:
            token_contract = self.get_token_contract(address)
            symbol = token_contract.functions.symbol().call()
            decimals = token_contract.functions.decimals().call()
            name = token_contract.functions.name().call()
            return {
                'address': address,
                'symbol': symbol,
                'decimals': decimals,
                'name': name
            }
        except Exception as e:
            rprint(f"[yellow]Error verifying token: {str(e)}[/yellow]")
            return None

    def save_token(self, token_data):
        """Save token to CSV file"""
        with open(self.tokens_file, 'a', newline='') as file:
            writer = csv.writer(file)
            writer.writerow([
                token_data['address'],
                token_data['symbol'],
                token_data['decimals'],
                token_data['name']
            ])

    def add_token_menu(self):
        """Menu for adding new tokens"""
        try:
            questions = [
                inquirer.Text('address',
                             message="Enter token contract address")
            ]
            answer = inquirer.prompt(questions)
            if not answer:
                return

            rprint("[yellow]Verifying token contract...[/yellow]")
            token_info = self.verify_token(answer['address'])
            if token_info:
                confirm = [
                    inquirer.Confirm('save',
                                   message=f"Save {token_info['name']} ({token_info['symbol']}) to token list?",
                                   default=True)
                ]
                if inquirer.prompt(confirm)['save']:
                    self.save_token(token_info)
                    rprint(f"[green]Token {token_info['symbol']} added successfully![/green]")
            else:
                rprint("[red]Invalid token contract![/red]")
        except KeyboardInterrupt:
            rprint("\n[yellow]Token addition cancelled by user[/yellow]")
            return
        except Exception as e:
            rprint(f"[red]Error adding token: {str(e)}[/red]")
            return

    def manage_tokens_menu(self, network_name):
        """Menu for token management"""
        try:
            questions = [
                inquirer.List('action',
                             message="Select token management action",
                             choices=['View Tokens', 'Add Token', 'Back to Main Menu'])
            ]
            answer = inquirer.prompt(questions)
            if not answer:
                return

            if answer['action'] == 'View Tokens':
                self.view_tokens(network_name)
            elif answer['action'] == 'Add Token':
                self.add_token_menu()
        except KeyboardInterrupt:
            rprint("\n[yellow]Token management cancelled by user[/yellow]")
            return
        except Exception as e:
            rprint(f"[red]Error in token management: {str(e)}[/red]")
            return

    def view_tokens(self, network_name):
        """Display all tokens in a table"""
        tokens = self.load_tokens()
        table = Table(title=f"Tokens on {network_name}")
        table.add_column("Symbol", style="cyan")
        table.add_column("Name", style="magenta")
        table.add_column("Address", style="green")
        table.add_column("Decimals", style="yellow")

        for token in tokens:
            table.add_row(
                token['Symbol'],
                token['Name'],
                token['Address'],
                str(token['Decimals'])
            )

        self.console.print(table)

    def get_token_by_symbol(self, symbol):
        """Get token details by symbol"""
        tokens = self.load_tokens()
        for token in tokens:
            if token['Symbol'] == symbol:
                return token
        return None

    def get_token_balance(self, token_address, wallet_address):
        """Get balance for a specific token"""
        try:
            # Ensure addresses are in checksum format
            try:
                checksum_token_address = Web3.to_checksum_address(token_address)
                checksum_wallet_address = Web3.to_checksum_address(wallet_address)
            except ValueError as checksum_error:
                # Handle checksum address error
                if "web3.py only accepts checksum addresses" in str(checksum_error):
                    # Convert to lowercase first, then to checksum address
                    if token_address.lower() in str(checksum_error):
                        checksum_token_address = Web3.to_checksum_address(token_address.lower())
                        checksum_wallet_address = Web3.to_checksum_address(wallet_address)
                    else:
                        checksum_token_address = Web3.to_checksum_address(token_address)
                        checksum_wallet_address = Web3.to_checksum_address(wallet_address.lower())
                else:
                    raise checksum_error

            # Check if this token is in our problem tokens list
            if hasattr(self, 'problem_tokens') and checksum_token_address in self.problem_tokens:
                rprint(f"[yellow]Skipping known problematic token {checksum_token_address}[/yellow]")
                return 0

            # Get the token contract
            token_contract = self.get_token_contract(checksum_token_address)

            # Check if the contract has the balanceOf function
            if not hasattr(token_contract.functions, 'balanceOf'):
                rprint(f"[yellow]Token at {token_address} does not have a balanceOf function[/yellow]")
                return 0

            # Try to call balanceOf with a timeout
            try:
                # Log the attempt
                rprint(f"[cyan]Calling balanceOf({checksum_wallet_address[:8]}...) on token contract {checksum_token_address[:8]}...[/cyan]")

                # Make the call with a very short timeout first to quickly identify problematic tokens
                # This helps avoid long waits for tokens that are known to cause issues
                try:
                    # Try with a very short timeout first (2 seconds)
                    balance = token_contract.functions.balanceOf(checksum_wallet_address).call(timeout=2)
                except Exception as timeout_error:
                    if "timeout" in str(timeout_error).lower():
                        # If it times out quickly, log it and return 0
                        rprint(f"[yellow]Quick timeout detected for token {checksum_token_address} - skipping to avoid delays[/yellow]")

                        # Add this token to a "problem tokens" list for future reference
                        if not hasattr(self, 'problem_tokens'):
                            self.problem_tokens = set()
                        self.problem_tokens.add(checksum_token_address)

                        return 0
                    else:
                        # If it's not a timeout error, try again with a longer timeout
                        rprint(f"[yellow]Retrying with longer timeout for token {checksum_token_address}...[/yellow]")
                        balance = token_contract.functions.balanceOf(checksum_wallet_address).call(timeout=10)

                # Log success
                if balance > 0:
                    rprint(f"[green]Successfully got balance: {balance} raw units[/green]")
                return balance

            except Exception as call_error:
                # Handle specific errors
                error_str = str(call_error)
                if "Could not decode contract function call" in error_str:
                    # This is likely not a standard ERC20 token or has issues
                    rprint(f"[yellow]Could not decode balanceOf response from {token_address}[/yellow]")
                    return 0
                elif "execution reverted" in error_str:
                    # Contract execution reverted
                    rprint(f"[yellow]Contract execution reverted for {token_address}[/yellow]")
                    return 0
                elif "timeout" in error_str.lower():
                    # Timeout error
                    rprint(f"[yellow]Timeout calling balanceOf on {token_address}[/yellow]")
                    return 0
                else:
                    # Log other errors
                    rprint(f"[yellow]Error calling balanceOf on {token_address}: {error_str}[/yellow]")
                    return 0

        except Exception as e:
            # Log all errors for better debugging
            error_msg = str(e)
            rprint(f"[yellow]Error getting token balance for {token_address}: {error_msg}[/yellow]")
            return 0

    def get_token_allowance(self, token_address, owner_address, spender_address):
        """Get allowance for a specific token"""
        try:
            # Ensure addresses are in checksum format
            try:
                checksum_token_address = Web3.to_checksum_address(token_address)
                checksum_owner_address = Web3.to_checksum_address(owner_address)
                checksum_spender_address = Web3.to_checksum_address(spender_address)
            except ValueError as checksum_error:
                # Handle checksum address error
                if "web3.py only accepts checksum addresses" in str(checksum_error):
                    rprint(f"[yellow]Warning: Converting non-checksum address to checksum format[/yellow]")
                    # Convert to lowercase first, then to checksum address
                    error_str = str(checksum_error).lower()

                    # Determine which address caused the error and fix it
                    checksum_token_address = Web3.to_checksum_address(token_address.lower() if token_address.lower() in error_str else token_address)
                    checksum_owner_address = Web3.to_checksum_address(owner_address.lower() if owner_address.lower() in error_str else owner_address)
                    checksum_spender_address = Web3.to_checksum_address(spender_address.lower() if spender_address.lower() in error_str else spender_address)
                else:
                    raise checksum_error

            token_contract = self.get_token_contract(checksum_token_address)
            allowance = token_contract.functions.allowance(checksum_owner_address, checksum_spender_address).call()
            return allowance
        except Exception as e:
            rprint(f"[yellow]Error getting token allowance: {str(e)}[/yellow]")
            return 0

    def transfer_token(self, token_address, from_address, to_address, amount, private_key, decimals):
        """Transfer tokens from one address to another"""
        try:
            # Ensure addresses are in checksum format
            try:
                checksum_token_address = Web3.to_checksum_address(token_address)
                checksum_from_address = Web3.to_checksum_address(from_address)
                checksum_to_address = Web3.to_checksum_address(to_address)
            except ValueError as checksum_error:
                # Handle checksum address error
                if "web3.py only accepts checksum addresses" in str(checksum_error):
                    rprint(f"[yellow]Warning: Converting non-checksum address to checksum format[/yellow]")
                    # Convert to lowercase first, then to checksum address
                    error_str = str(checksum_error).lower()

                    # Determine which address caused the error and fix it
                    checksum_token_address = Web3.to_checksum_address(token_address.lower() if token_address.lower() in error_str else token_address)
                    checksum_from_address = Web3.to_checksum_address(from_address.lower() if from_address.lower() in error_str else from_address)
                    checksum_to_address = Web3.to_checksum_address(to_address.lower() if to_address.lower() in error_str else to_address)
                else:
                    raise checksum_error

            # Get the token contract with full ABI for transfer
            token_contract = self.get_token_contract(checksum_token_address, for_transfer=True)

            # Convert amount to token units based on decimals
            amount_in_units = int(float(amount) * (10 ** int(decimals)))

            # Check BNB balance for gas
            bnb_balance = self.w3.eth.get_balance(checksum_from_address)
            gas_price = self.w3.eth.gas_price
            estimated_gas_cost = gas_price * 100000  # Estimated gas limit * gas price

            if bnb_balance < estimated_gas_cost:
                return False, f"Insufficient BNB for gas fees. You need at least {self.w3.from_wei(estimated_gas_cost, 'ether')} BNB for gas."

            # Get the current nonce
            nonce = self.w3.eth.get_transaction_count(checksum_from_address, 'pending')

            # Check if the contract has the transfer function
            if 'transfer' not in [func.fn_name for func in token_contract.all_functions()]:
                return False, "The token contract does not have a transfer function. It may not be a standard ERC20 token."

            # Build the transaction
            transfer_txn = token_contract.functions.transfer(
                checksum_to_address,
                amount_in_units
            ).build_transaction({
                'chainId': self.w3.eth.chain_id,
                'gas': 100000,  # Gas limit for token transfers
                'gasPrice': gas_price,
                'nonce': nonce,
            })

            # Sign the transaction
            if isinstance(private_key, str):
                if private_key.startswith('0x'):
                    private_key = private_key[2:]
                signed_txn = self.w3.eth.account.sign_transaction(transfer_txn, private_key=bytes.fromhex(private_key))
            else:
                signed_txn = self.w3.eth.account.sign_transaction(transfer_txn, private_key=private_key)

            # Send the transaction
            # Handle different attribute names in different Web3.py versions
            if hasattr(signed_txn, 'rawTransaction'):
                raw_tx = signed_txn.rawTransaction
            elif hasattr(signed_txn, 'raw_transaction'):
                raw_tx = signed_txn.raw_transaction
            else:
                return False, "Error: Could not find raw transaction data in signed transaction"

            tx_hash = self.w3.eth.send_raw_transaction(raw_tx)

            # Wait for the transaction receipt
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)

            if receipt['status'] == 1:
                return True, self.w3.to_hex(tx_hash)
            else:
                # Transaction failed - try to get more detailed information
                tx_hash_hex = self.w3.to_hex(tx_hash)
                rprint(f"[red]Token transfer failed with status 0. Transaction hash: {tx_hash_hex}[/red]")

                # Try to get transaction details
                try:
                    tx = self.w3.eth.get_transaction(tx_hash)
                    rprint(f"[yellow]Transaction details:[/yellow]")
                    rprint(f"  From: {tx['from']}")
                    rprint(f"  To: {tx['to']}")
                    rprint(f"  Gas: {tx['gas']}")
                    rprint(f"  Gas Price: {self.w3.from_wei(tx['gasPrice'], 'gwei')} Gwei")
                    rprint(f"  Nonce: {tx['nonce']}")

                    # Try to get transaction receipt for more details
                    gas_used = receipt.get('gasUsed', 'Unknown')
                    rprint(f"  Gas Used: {gas_used}")

                    # Check if transaction reverted
                    if gas_used == tx['gas'] or (isinstance(gas_used, int) and gas_used > 0.95 * tx['gas']):
                        rprint(f"[red]Transaction likely reverted - used almost all gas.[/red]")

                        # Try to get revert reason
                        try:
                            # Replay the transaction to get the revert reason
                            self.w3.eth.call(
                                {
                                    'from': tx['from'],
                                    'to': tx['to'],
                                    'data': tx['input'],
                                    'gas': tx['gas'],
                                    'gasPrice': tx['gasPrice'],
                                    'value': tx.get('value', 0)
                                },
                                receipt['blockNumber']
                            )
                        except Exception as call_error:
                            error_str = str(call_error)
                            if 'revert' in error_str.lower():
                                rprint(f"[red]Revert reason: {error_str}[/red]")
                                return False, f"Token transfer reverted: {error_str}"
                except Exception as tx_error:
                    rprint(f"[yellow]Could not get detailed transaction info: {str(tx_error)}[/yellow]")

                # Common reasons for token transfer failure
                rprint("[yellow]Common reasons for token transfer failure:[/yellow]")
                rprint("  1. Insufficient token balance")
                rprint("  2. Recipient is blacklisted or blocked")
                rprint("  3. Transfer exceeds allowed limits")
                rprint("  4. Token contract has transfer restrictions")

                return False, f"Token transfer failed. Hash: {tx_hash_hex}"

        except Exception as e:
            error_msg = str(e)
            rprint(f"[red]Token transfer error: {error_msg}[/red]")

            # Add more detailed error information for debugging
            if "insufficient funds" in error_msg.lower():
                if "gas" in error_msg.lower():
                    rprint("[yellow]The wallet doesn't have enough BNB to pay for gas.[/yellow]")
                    return False, "Insufficient BNB for gas fees"
                else:
                    rprint("[yellow]The wallet doesn't have enough tokens for this transfer.[/yellow]")
                    return False, "Insufficient token balance for transfer"
            elif "gas required exceeds allowance" in error_msg.lower():
                rprint("[yellow]The transaction requires more gas than provided. Try increasing the gas limit.[/yellow]")
                return False, "Gas required exceeds allowance. Try increasing the gas limit."
            elif "nonce too low" in error_msg.lower():
                rprint("[yellow]The transaction nonce is too low. Another transaction from this account may be pending.[/yellow]")
                return False, "Nonce too low. The transaction may have already been processed."
            elif "replacement transaction underpriced" in error_msg.lower():
                rprint("[yellow]A transaction with the same nonce is pending. Try again with a higher gas price.[/yellow]")
                return False, "Replacement transaction underpriced. Try again with a higher gas price."
            elif "execution reverted" in error_msg.lower():
                # Try to extract revert reason if available
                revert_reason = "Unknown reason"
                if ":" in error_msg:
                    revert_reason = error_msg.split(":", 1)[1].strip()
                rprint(f"[yellow]The token transfer reverted: {revert_reason}[/yellow]")
                return False, f"Token transfer reverted: {revert_reason}"

            return False, f"Error: {error_msg}"

    def get_contract_functions(self, token_address):
        """Get a list of all available functions in a token contract"""
        try:
            # Get the token contract with full ABI
            token_contract = self.get_token_contract(token_address, for_transfer=True)

            # Get all functions from the contract
            functions = []
            for func in token_contract.all_functions():
                # Get function name and inputs
                fn_name = func.fn_name
                inputs = []

                # Get function signature from ABI
                for item in token_contract.abi:
                    if item.get('type') == 'function' and item.get('name') == fn_name:
                        inputs = item.get('inputs', [])
                        outputs = item.get('outputs', [])
                        constant = item.get('constant', False) or item.get('stateMutability') in ['view', 'pure']
                        break

                functions.append({
                    'name': fn_name,
                    'inputs': inputs,
                    'outputs': outputs if 'outputs' in locals() else [],
                    'constant': constant if 'constant' in locals() else False
                })

            # Sort functions: read-only (constant) functions first, then alphabetically
            functions.sort(key=lambda x: (not x['constant'], x['name']))

            return functions
        except Exception as e:
            rprint(f"[red]Error getting contract functions: {str(e)}[/red]")
            return []

    def execute_contract_function(self, token_address, function_name, args, from_address=None, private_key=None, gas_limit=200000):
        """Execute a function on a token contract with customizable gas limit"""
        try:
            # Ensure addresses are in checksum format
            try:
                checksum_token_address = Web3.to_checksum_address(token_address)
                checksum_from_address = None
                if from_address:
                    checksum_from_address = Web3.to_checksum_address(from_address)
            except ValueError as checksum_error:
                # Handle checksum address error
                if "web3.py only accepts checksum addresses" in str(checksum_error):
                    rprint(f"[yellow]Warning: Converting non-checksum address to checksum format[/yellow]")
                    # Convert to lowercase first, then to checksum address
                    error_str = str(checksum_error).lower()

                    # Determine which address caused the error and fix it
                    checksum_token_address = Web3.to_checksum_address(token_address.lower() if token_address.lower() in error_str else token_address)
                    if from_address:
                        checksum_from_address = Web3.to_checksum_address(from_address.lower() if from_address and from_address.lower() in error_str else from_address)
                else:
                    raise checksum_error

            # Get the token contract with full ABI
            token_contract = self.get_token_contract(checksum_token_address, for_transfer=True)

            # Get the function
            contract_function = getattr(token_contract.functions, function_name)

            # Check if function exists
            if not contract_function:
                return False, f"Function {function_name} not found in contract"

            # Get function details from ABI
            function_abi = None
            for item in token_contract.abi:
                if item.get('type') == 'function' and item.get('name') == function_name:
                    function_abi = item
                    break

            if not function_abi:
                return False, f"Function {function_name} ABI not found"

            # Get token decimals
            token_info = None
            tokens = self.load_tokens()
            for token in tokens:
                if Web3.to_checksum_address(token['Address']) == Web3.to_checksum_address(token_address):
                    token_info = token
                    break

            token_decimals = int(token_info['Decimals']) if token_info else 18  # Default to 18 if not found

            # Process args based on function name and parameter types
            processed_args = []

            # Common token functions that deal with token amounts
            amount_functions = ['transfer', 'transferFrom', 'approve', 'burn', 'burnFrom', 'mint', 'increaseAllowance', 'decreaseAllowance']

            # Check if this is a function that deals with token amounts
            is_amount_function = function_name.lower() in [f.lower() for f in amount_functions]

            # Process each argument
            for i, arg in enumerate(args):
                # If this is a function that deals with token amounts and the parameter is likely an amount
                if is_amount_function and i < len(function_abi['inputs']) and function_abi['inputs'][i]['type'].startswith('uint'):
                    param_name = function_abi['inputs'][i].get('name', '')
                    # Check if parameter name suggests it's an amount
                    is_amount_param = any(term in param_name.lower() for term in ['amount', 'value', 'tokens', 'quantity', 'supply', 'balance', 'allowance'])

                    # Special case for burnFrom - the second parameter is always the amount
                    if function_name.lower() == 'burnfrom' and i == 1:
                        is_amount_param = True

                    if is_amount_param:
                        # Convert from human-readable to token units
                        rprint(f"[yellow]Converting {arg} tokens to raw units (× 10^{token_decimals})[/yellow]")
                        processed_arg = int(float(arg) * (10 ** token_decimals))
                        processed_args.append(processed_arg)
                        continue

                # For other arguments, pass them as is
                processed_args.append(arg)

            # Check if function is constant (read-only)
            is_constant = function_abi.get('constant', False) or function_abi.get('stateMutability') in ['view', 'pure']

            # For constant functions, just call and return the result
            if is_constant:
                result = contract_function(*processed_args).call()

                # Process result if it's likely a token amount
                if function_name.lower() in ['balanceof', 'totalsupply', 'allowance'] and isinstance(result, int):
                    human_readable = float(result) / (10 ** token_decimals)
                    return True, {"raw_units": result, "tokens": human_readable}

                return True, result

            # For non-constant functions, we need to send a transaction
            if not from_address or not private_key:
                return False, "From address and private key required for non-constant functions"

            # Get the current nonce
            nonce = self.w3.eth.get_transaction_count(checksum_from_address, 'pending')

            # Build the transaction
            function_txn = contract_function(*processed_args).build_transaction({
                'chainId': self.w3.eth.chain_id,
                'gas': gas_limit,  # Use the provided gas limit
                'gasPrice': self.w3.eth.gas_price,
                'nonce': nonce,
            })

            # Sign the transaction
            if isinstance(private_key, str):
                if private_key.startswith('0x'):
                    private_key = private_key[2:]
                signed_txn = self.w3.eth.account.sign_transaction(function_txn, private_key=bytes.fromhex(private_key))
            else:
                signed_txn = self.w3.eth.account.sign_transaction(function_txn, private_key=private_key)

            # Send the transaction
            # Handle different attribute names in different Web3.py versions
            if hasattr(signed_txn, 'rawTransaction'):
                raw_tx = signed_txn.rawTransaction
            elif hasattr(signed_txn, 'raw_transaction'):
                raw_tx = signed_txn.raw_transaction
            else:
                return False, "Error: Could not find raw transaction data in signed transaction"

            tx_hash = self.w3.eth.send_raw_transaction(raw_tx)

            # Wait for the transaction receipt
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)

            if receipt['status'] == 1:
                return True, self.w3.to_hex(tx_hash)
            else:
                # Transaction failed - try to get more detailed information
                tx_hash_hex = self.w3.to_hex(tx_hash)
                rprint(f"[red]Transaction failed with status 0. Transaction hash: {tx_hash_hex}[/red]")

                # Try to get transaction details
                try:
                    tx = self.w3.eth.get_transaction(tx_hash)
                    rprint(f"[yellow]Transaction details:[/yellow]")
                    rprint(f"  From: {tx['from']}")
                    rprint(f"  To: {tx['to']}")
                    rprint(f"  Gas: {tx['gas']}")
                    rprint(f"  Gas Price: {self.w3.from_wei(tx['gasPrice'], 'gwei')} Gwei")
                    rprint(f"  Nonce: {tx['nonce']}")

                    # Try to get transaction receipt for more details
                    gas_used = receipt.get('gasUsed', 'Unknown')
                    rprint(f"  Gas Used: {gas_used}")

                    # Check if transaction reverted
                    if gas_used == tx['gas'] or (isinstance(gas_used, int) and gas_used > 0.95 * tx['gas']):
                        rprint(f"[red]Transaction likely reverted - used almost all gas.[/red]")

                        # Try to get revert reason
                        try:
                            # Replay the transaction to get the revert reason
                            self.w3.eth.call(
                                {
                                    'from': tx['from'],
                                    'to': tx['to'],
                                    'data': tx['input'],
                                    'gas': tx['gas'],
                                    'gasPrice': tx['gasPrice'],
                                    'value': tx.get('value', 0)
                                },
                                receipt['blockNumber']
                            )
                        except Exception as call_error:
                            error_str = str(call_error)
                            if 'revert' in error_str.lower():
                                rprint(f"[red]Revert reason: {error_str}[/red]")
                                return False, f"Transaction reverted: {error_str}"
                except Exception as tx_error:
                    rprint(f"[yellow]Could not get detailed transaction info: {str(tx_error)}[/yellow]")

                # Common reasons for failure
                rprint("[yellow]Common reasons for transaction failure:[/yellow]")
                rprint("  1. Insufficient token balance or allowance")
                rprint("  2. Contract function reverted (failed internal checks)")
                rprint("  3. Gas limit too low for the operation")
                rprint("  4. Caller doesn't have required permissions")

                return False, f"Transaction failed. Hash: {tx_hash_hex}"

        except Exception as e:
            error_msg = str(e)
            rprint(f"[red]Error executing contract function: {error_msg}[/red]")

            # Provide more specific error messages based on common errors
            if "gas required exceeds allowance" in error_msg.lower():
                rprint("[yellow]The transaction requires more gas than provided. Try increasing the gas limit.[/yellow]")
                return False, f"Gas limit too low: {error_msg}"
            elif "insufficient funds" in error_msg.lower():
                rprint("[yellow]The wallet doesn't have enough BNB to pay for gas.[/yellow]")
                return False, f"Insufficient BNB for gas: {error_msg}"
            elif "nonce too low" in error_msg.lower():
                rprint("[yellow]The transaction nonce is too low. Another transaction from this account may be pending.[/yellow]")
                return False, f"Nonce too low: {error_msg}"
            elif "already known" in error_msg.lower():
                rprint("[yellow]This transaction was already submitted.[/yellow]")
                return False, f"Transaction already submitted: {error_msg}"
            elif "execution reverted" in error_msg.lower():
                # Try to extract revert reason if available
                revert_reason = "Unknown reason"
                if ":" in error_msg:
                    revert_reason = error_msg.split(":", 1)[1].strip()
                rprint(f"[yellow]The contract function reverted: {revert_reason}[/yellow]")
                return False, f"Function reverted: {revert_reason}"

            return False, f"Error: {error_msg}"
