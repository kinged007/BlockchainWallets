from web3 import Web3
from rich.table import Table
import inquirer
from rich import print as rprint
from eth_account import Account
from eth_account.signers.local import LocalAccount
import time

class TransactionManager:
    def __init__(self, w3: Web3, chain_id: int, console):
        self.w3 = w3
        self.chain_id = chain_id
        self.console = console

    def get_current_nonce(self, address):
        """Get the current nonce for an address"""
        return self.w3.eth.get_transaction_count(address, 'pending')

    def get_pending_transaction(self, address, nonce):
        """Get a pending transaction with the specified nonce if it exists"""
        try:
            # Get the pending transactions for this address
            # We need to check the mempool for transactions with this nonce
            pending_tx = None

            # Try to find a pending transaction with this nonce
            # This is a simplified approach - in a real implementation, you'd query the mempool
            # For now, we'll just try to estimate what might be happening
            block = self.w3.eth.get_block('pending', full_transactions=True)

            for tx in block.transactions:
                if tx.get('from', '').lower() == address.lower() and tx.get('nonce') == nonce:
                    pending_tx = tx
                    break

            return pending_tx
        except Exception as e:
            rprint(f"[yellow]Error checking pending transactions: {str(e)}[/yellow]")
            return None

    def check_transaction_status(self, tx_hash):
        """Check the status of a transaction"""
        try:
            # First check if the transaction exists
            tx = self.w3.eth.get_transaction(tx_hash)
            if tx is None:
                return "Transaction not found"

            # Check if it's been mined
            if tx.get('blockNumber') is None:
                return "Pending - Not yet mined"

            # Get the receipt to check status
            receipt = self.w3.eth.get_transaction_receipt(tx_hash)
            if receipt is None:
                return "Mined but no receipt available"

            if receipt.get('status') == 1:
                return f"Success - Mined in block {receipt.get('blockNumber')}"
            else:
                return f"Failed - Mined in block {receipt.get('blockNumber')}"

        except Exception as e:
            return f"Error checking status: {str(e)}"

    def check_network_status(self):
        """Check if the network is responsive and return current gas price"""
        try:
            # Check if we can connect to the network
            block_number = self.w3.eth.block_number
            gas_price = self.w3.eth.gas_price

            rprint(f"[green]Network is responsive. Current block: {block_number}, Gas price: {self.w3.from_wei(gas_price, 'gwei')} Gwei[/green]")
            return True, gas_price
        except Exception as e:
            rprint(f"[red]Network connection issue: {str(e)}[/red]")
            return False, 0

    def calculate_replacement_gas_price(self, from_address, nonce, base_gas_price):
        """Calculate a gas price high enough to replace a pending transaction"""
        try:
            # Try to find the pending transaction
            pending_tx = self.get_pending_transaction(from_address, nonce)

            if pending_tx and 'gasPrice' in pending_tx:
                # Get the gas price of the pending transaction
                pending_gas_price = pending_tx['gasPrice']

                # Calculate a new gas price that's at least 10% higher than the pending one
                # This is the minimum required by most networks to replace a transaction
                new_gas_price = int(pending_gas_price * 1.2)  # 20% higher

                rprint(f"[yellow]Found pending transaction with nonce {nonce}.[/yellow]")
                rprint(f"[yellow]Pending transaction gas price: {self.w3.from_wei(pending_gas_price, 'gwei')} Gwei[/yellow]")
                rprint(f"[yellow]New gas price needed: {self.w3.from_wei(new_gas_price, 'gwei')} Gwei (20% higher)[/yellow]")

                return new_gas_price
            else:
                # If we can't find the pending transaction, use a very high gas price
                # This is a fallback mechanism
                new_gas_price = int(base_gas_price * 3)  # 3x the current gas price
                rprint(f"[yellow]No pending transaction found with nonce {nonce}. Using 3x current gas price: {self.w3.from_wei(new_gas_price, 'gwei')} Gwei[/yellow]")
                return new_gas_price

        except Exception as e:
            rprint(f"[yellow]Error calculating replacement gas price: {str(e)}. Using 3x current gas price.[/yellow]")
            return int(base_gas_price * 3)  # 3x the current gas price as fallback

    def cancel_transaction(self, from_address, private_key, nonce):
        """Cancel a pending transaction by sending a 0 value transaction to yourself with the same nonce"""
        try:
            # Check if there's a pending transaction with this nonce
            pending_tx = self.get_pending_transaction(from_address, nonce)

            if not pending_tx:
                rprint(f"[yellow]No pending transaction found with nonce {nonce}.[/yellow]")
                return False, "No pending transaction found with this nonce"

            # Calculate a gas price high enough to replace the pending transaction
            base_gas_price = self.w3.eth.gas_price
            new_gas_price = self.calculate_replacement_gas_price(from_address, nonce, base_gas_price)

            # Build a cancellation transaction (send 0 value to yourself)
            transaction = {
                'nonce': nonce,
                'gasPrice': new_gas_price,
                'gas': 21000,  # Standard gas limit for ETH transfer
                'to': from_address,  # Send to yourself
                'value': 0,  # 0 value
                'data': b'',
                'chainId': self.chain_id
            }

            # Create account from private key
            if isinstance(private_key, str):
                if private_key.startswith('0x'):
                    private_key = private_key[2:]
                account = Account.from_key(bytes.fromhex(private_key))
            else:
                account = Account.from_key(private_key)

            # Sign transaction
            signed = account.sign_transaction(transaction)

            # Send raw transaction
            rprint(f"[yellow]Attempting to cancel transaction with nonce {nonce} using gas price {self.w3.from_wei(new_gas_price, 'gwei')} Gwei...[/yellow]")

            try:
                tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
                rprint(f"[green]Cancellation transaction submitted: {self.w3.to_hex(tx_hash)}[/green]")

                # Wait for the cancellation transaction to be mined
                receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)

                if receipt['status'] == 1:
                    rprint(f"[green]Transaction with nonce {nonce} successfully cancelled![/green]")
                    return True, self.w3.to_hex(tx_hash)
                else:
                    rprint(f"[red]Cancellation transaction failed with status 0.[/red]")
                    return False, "Cancellation transaction failed"

            except Exception as e:
                error_msg = str(e)
                rprint(f"[red]Error sending cancellation transaction: {error_msg}[/red]")
                return False, f"Error: {error_msg}"

        except Exception as e:
            rprint(f"[red]Error cancelling transaction: {str(e)}[/red]")
            return False, f"Error: {str(e)}"

    def estimate_gas(self, from_address, to_address, amount_wei):
        """Estimate gas for a transaction"""
        try:
            # Create a transaction object for estimation
            tx = {
                'from': self.w3.to_checksum_address(from_address),
                'to': self.w3.to_checksum_address(to_address),
                'value': amount_wei,
                'chainId': self.chain_id
            }

            # Estimate gas
            estimated_gas = self.w3.eth.estimate_gas(tx)

            # Add a 20% buffer to be safe
            return int(estimated_gas * 1.2)
        except Exception as e:
            # If estimation fails, return a default value
            rprint(f"[yellow]Gas estimation failed: {str(e)}. Using default gas limit.[/yellow]")
            return 21000  # Default gas limit for simple ETH transfers

    def perform_transaction(self, from_address, to_address, amount, private_key, nonce=None, gas_price_multiplier=1.1, max_retries=3):
        """Perform a transaction with retry logic for common errors"""
        try:
            # Ensure addresses are checksummed
            from_address = self.w3.to_checksum_address(from_address)
            to_address = self.w3.to_checksum_address(to_address)

            # Convert amount to Wei
            amount_wei = self.w3.to_wei(amount, 'ether')

            # Get the nonce (transaction count) if not provided
            if nonce is None:
                nonce = self.get_current_nonce(from_address)

            retry_count = 0
            while retry_count < max_retries:
                try:
                    # Get current gas price with an increasing multiplier for each retry
                    current_multiplier = gas_price_multiplier * (1 + (retry_count * 0.3))  # Increase by 30% each retry

                    # Get the current gas price from the network
                    base_gas_price = self.w3.eth.gas_price

                    # Calculate gas price with multiplier
                    gas_price = int(base_gas_price * current_multiplier)

                    # Ensure gas price is at least 10% higher than base to help with confirmation
                    min_gas_price = int(base_gas_price * 1.5)
                    gas_price = max(gas_price, min_gas_price)

                    # Estimate gas for this transaction
                    estimated_gas = self.estimate_gas(from_address, to_address, amount_wei)

                    # Build transaction
                    transaction = {
                        'nonce': nonce,
                        'gasPrice': gas_price,
                        'gas': estimated_gas,  # Use estimated gas instead of fixed value
                        'to': to_address,
                        'value': amount_wei,
                        'data': b'',
                        'chainId': self.chain_id
                    }

                    # Log the transaction details for debugging
                    rprint(f"[cyan]Transaction details: Nonce={nonce}, Gas={estimated_gas}, Gas Price={self.w3.from_wei(gas_price, 'gwei')} Gwei[/cyan]")

                    # Create account from private key
                    if isinstance(private_key, str):
                        if private_key.startswith('0x'):
                            private_key = private_key[2:]
                        account: LocalAccount = Account.from_key(bytes.fromhex(private_key))
                    else:
                        account: LocalAccount = Account.from_key(private_key)

                    # Sign transaction
                    signed = account.sign_transaction(transaction)

                    # Send raw transaction and get transaction hash
                    try:
                        tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
                        break  # Exit the retry loop if successful
                    except ValueError as e:
                        error_msg = str(e)

                        # Print the full error for debugging
                        rprint(f"[red]RPC Error: {error_msg}[/red]")

                        # Handle "already known" error - this means the transaction is already in the mempool
                        if "already known" in error_msg:
                            rprint(f"[yellow]Transaction with nonce {nonce} is already in the mempool. This is not an error.[/yellow]")
                            # Extract the transaction hash from the raw transaction
                            tx_hash = self.w3.keccak(signed.raw_transaction)
                            break  # Exit the retry loop

                        # Handle "replacement transaction underpriced" error
                        elif "replacement transaction underpriced" in error_msg:
                            if retry_count < max_retries - 1:
                                retry_count += 1

                                # Get a gas price high enough to replace the pending transaction
                                new_gas_price = self.calculate_replacement_gas_price(
                                    from_address,
                                    nonce,
                                    self.w3.eth.gas_price
                                )

                                # Override the gas price for the next attempt
                                gas_price = new_gas_price

                                rprint(f"[yellow]Replacement transaction underpriced. Retrying with calculated gas price (attempt {retry_count}/{max_retries})...[/yellow]")
                                continue  # Try again with higher gas price
                            else:
                                # If we've tried multiple times and still can't replace the transaction,
                                # suggest to the user to wait for the pending transaction to complete
                                # or to use a tool to cancel the transaction
                                rprint(f"[red]Unable to replace transaction with nonce {nonce} after {max_retries} attempts.[/red]")
                                rprint(f"[yellow]Options:[/yellow]")
                                rprint(f"[yellow]1. Wait for the pending transaction to complete or fail[/yellow]")
                                rprint(f"[yellow]2. Use a transaction cancellation tool to send a 0 value transaction to yourself with the same nonce and higher gas price[/yellow]")
                                raise  # Max retries reached, re-raise the error
                        # Handle nonce errors
                        elif "nonce too low" in error_msg:
                            if retry_count < max_retries - 1:
                                retry_count += 1
                                # Get a fresh nonce
                                nonce = self.get_current_nonce(from_address)
                                rprint(f"[yellow]Nonce too low. Retrying with new nonce {nonce} (attempt {retry_count}/{max_retries})...[/yellow]")
                                continue
                            else:
                                raise
                        # Handle other RPC errors
                        else:
                            if retry_count < max_retries - 1:
                                retry_count += 1
                                rprint(f"[yellow]RPC error occurred. Retrying (attempt {retry_count}/{max_retries})...[/yellow]")
                                time.sleep(2)  # Wait before retrying
                                continue
                            else:
                                raise  # Max retries reached, re-raise the error

                except Exception as e:
                    error_msg = str(e)
                    if retry_count < max_retries - 1:
                        retry_count += 1
                        # Print the full error message for debugging
                        rprint(f"[red]Detailed error: {error_msg}[/red]")
                        rprint(f"[yellow]Transaction failed. Retrying (attempt {retry_count}/{max_retries})...[/yellow]")
                        time.sleep(2)  # Wait longer before retrying
                        continue
                    else:
                        # Print the full error message before giving up
                        rprint(f"[red]Final attempt failed with error: {error_msg}[/red]")
                        raise  # Max retries reached, re-raise the error

            # Convert tx_hash to hex string for display
            tx_hex = self.w3.to_hex(tx_hash)

            # First check if the transaction was successfully submitted
            rprint(f"[cyan]Transaction submitted: {tx_hex}[/cyan]")

            # Try to wait for the transaction with a shorter timeout first
            try:
                # Try with a shorter timeout first (30 seconds)
                receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=30)

                if receipt['status'] == 1:
                    rprint(f"[green]Transaction confirmed quickly! Block: {receipt['blockNumber']}[/green]")
                    return tx_hex
                else:
                    return f"Error: Transaction failed with status 0 in block {receipt['blockNumber']}"

            except Exception as initial_error:
                # If the short timeout fails, check the status
                status = self.check_transaction_status(tx_hash)
                rprint(f"[yellow]Current status: {status}[/yellow]")

                if "Pending" in status:
                    # Try with a longer timeout
                    try:
                        # Try again with a longer timeout (180 seconds)
                        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)

                        if receipt['status'] == 1:
                            return tx_hex
                        else:
                            return f"Error: Transaction failed with status 0 in block {receipt['blockNumber']}"

                    except Exception as e:
                        error_msg = str(e)
                        # If timeout occurred, provide a more helpful message
                        if "is not in the chain after" in error_msg:
                            rprint(f"[yellow]Transaction {tx_hex} submitted but not confirmed within timeout.[/yellow]")
                            rprint(f"[yellow]You can check the transaction status later using a blockchain explorer.[/yellow]")
                            # Return the transaction hash anyway so the user can track it
                            return f"Pending: {tx_hex}"
                        else:
                            rprint(f"[red]Error waiting for transaction: {error_msg}[/red]")
                            return f"Error: {error_msg}"
                else:
                    # If it's not pending, return the current status
                    if "Success" in status:
                        return tx_hex
                    else:
                        return f"Error: {status}"

        except ValueError as e:
            error_msg = str(e)
            if "insufficient funds" in error_msg:
                return "Error: Insufficient funds for transaction"
            elif "replacement transaction underpriced" in error_msg:
                return "Error: Replacement transaction underpriced. Try again with a higher gas price."
            elif "nonce too low" in error_msg:
                return "Error: Nonce too low. The transaction may have already been processed."
            return f"Error: {error_msg}"
        except Exception as e:
            return f"Error: {str(e)}"

    def handle_single_transaction(self, sender, recipient, amount, token_info=None, token_manager=None):
        """Handle a single transaction (BNB or token)"""
        try:
            # Check network status before proceeding
            network_ok, _ = self.check_network_status()
            if not network_ok:
                rprint("[red]Cannot proceed with transaction due to network issues.[/red]")
                return

            # Get sender's private key if not available
            private_key = sender.get('private_key', sender.get('Private Key', None))
            if not private_key:
                key_q = [
                    inquirer.Text('private_key',
                                 message="Enter sender's private key")
                ]
                key_answer = inquirer.prompt(key_q)
                if not key_answer:
                    return
                private_key = key_answer['private_key']

            # Perform transaction
            from_address = sender.get('address', sender.get('Address'))
            to_address = recipient.get('address', recipient.get('Address'))

            # If token_info is provided, perform a token transfer
            if token_info and token_manager:
                token_symbol = token_info['Symbol']
                token_address = token_info['Address']
                token_decimals = token_info['Decimals']

                rprint(f"[yellow]Sending {amount} {token_symbol} from {from_address} to {to_address}...[/yellow]")

                # Check token balance
                raw_balance = token_manager.get_token_balance(token_address, from_address)
                decimals = int(token_decimals)
                balance = float(raw_balance) / (10 ** decimals)

                if balance < float(amount):
                    rprint(f"[red]Insufficient token balance! You have {balance} {token_symbol} but trying to send {amount} {token_symbol}[/red]")
                    return

                # Perform token transfer
                success, result = token_manager.transfer_token(
                    token_address,
                    from_address,
                    to_address,
                    float(amount),
                    private_key,
                    decimals
                )

                if success:
                    rprint(f"[green]Token transfer successful![/green]")
                    rprint(f"[cyan]Transaction hash: {result}[/cyan]")
                else:
                    rprint(f"[red]Token transfer failed: {result}[/red]")

            else:
                # Regular BNB transfer
                rprint(f"[yellow]Sending {amount} BNB from {from_address} to {to_address}...[/yellow]")

                # Check sender balance
                balance = self.w3.eth.get_balance(from_address)
                amount_wei = self.w3.to_wei(float(amount), 'ether')
                if balance < amount_wei:
                    rprint(f"[red]Insufficient balance! You have {self.w3.from_wei(balance, 'ether')} BNB but trying to send {amount} BNB[/red]")
                    return

                # Get the current nonce
                current_nonce = self.get_current_nonce(from_address)

                # Start with a higher gas price multiplier for single transactions
                tx_hash = self.perform_transaction(
                    from_address,
                    to_address,
                    float(amount),
                    private_key,
                    nonce=current_nonce,
                    gas_price_multiplier=1.5,  # Much higher initial gas price for better confirmation chances
                    max_retries=3
                )

                if tx_hash.startswith('Error:'):
                    rprint(f"[red]{tx_hash}[/red]")
                elif tx_hash.startswith('Pending:'):
                    tx_hex = tx_hash.replace('Pending: ', '')
                    rprint(f"[yellow]Transaction submitted but not confirmed within timeout.[/yellow]")
                    rprint(f"[cyan]Transaction hash: {tx_hex}[/cyan]")
                    rprint(f"[yellow]You can check the status later using a blockchain explorer.[/yellow]")
                else:
                    rprint(f"[green]Transaction successful![/green]")
                    rprint(f"[cyan]Transaction hash: {tx_hash}[/cyan]")

        except Exception as e:
            rprint(f"[red]Transaction failed: {str(e)}[/red]")

    def handle_bulk_transaction(self, sender, recipients, amount, token_info=None, token_manager=None):
        """Handle bulk transactions (BNB or token)"""
        try:
            # Check network status before proceeding
            network_ok, _ = self.check_network_status()
            if not network_ok:
                rprint("[red]Cannot proceed with bulk transactions due to network issues.[/red]")
                return

            results = []
            private_key = sender.get('private_key', sender.get('Private Key', None))
            if not private_key:
                key_q = [
                    inquirer.Text('private_key',
                                 message="Enter sender's private key")
                ]
                key_answer = inquirer.prompt(key_q)
                if not key_answer:
                    return
                private_key = key_answer['private_key']

            from_address = sender.get('address', sender.get('Address'))

            # If token_info is provided, perform token transfers
            if token_info and token_manager:
                token_symbol = token_info['Symbol']
                token_address = token_info['Address']
                token_decimals = int(token_info['Decimals'])

                # Check total token amount needed
                raw_balance = token_manager.get_token_balance(token_address, from_address)
                balance = float(raw_balance) / (10 ** token_decimals)
                total_amount = float(amount) * len(recipients)

                if balance < total_amount:
                    rprint(f"[red]Insufficient token balance for bulk transaction![/red]")
                    rprint(f"[red]You have {balance} {token_symbol} but need {total_amount} {token_symbol} for {len(recipients)} transactions[/red]")
                    return

                # Ask for confirmation before proceeding with bulk transaction
                rprint(f"[yellow]You are about to send {amount} {token_symbol} to {len(recipients)} recipients.[/yellow]")
                rprint(f"[yellow]Total amount: {total_amount} {token_symbol}[/yellow]")

                confirm_q = [
                    inquirer.Confirm('confirm',
                                   message="Do you want to proceed?",
                                   default=True)
                ]
                confirm = inquirer.prompt(confirm_q)
                if not confirm or not confirm['confirm']:
                    rprint("[yellow]Bulk transaction cancelled by user.[/yellow]")
                    return
            else:
                # Regular BNB transfers
                # Check total amount needed
                total_amount_wei = self.w3.to_wei(float(amount) * len(recipients), 'ether')
                balance = self.w3.eth.get_balance(from_address)

                if balance < total_amount_wei:
                    rprint(f"[red]Insufficient balance for bulk transaction![/red]")
                    rprint(f"[red]You have {self.w3.from_wei(balance, 'ether')} BNB but need {self.w3.from_wei(total_amount_wei, 'ether')} BNB for {len(recipients)} transactions[/red]")
                    return

                # Ask for confirmation before proceeding with bulk transaction
                rprint(f"[yellow]You are about to send {amount} BNB to {len(recipients)} recipients.[/yellow]")
                rprint(f"[yellow]Total amount: {self.w3.from_wei(total_amount_wei, 'ether')} BNB[/yellow]")

                confirm_q = [
                    inquirer.Confirm('confirm',
                                   message="Do you want to proceed?",
                                   default=True)
                ]
                confirm = inquirer.prompt(confirm_q)
                if not confirm or not confirm['confirm']:
                    rprint("[yellow]Bulk transaction cancelled by user.[/yellow]")
                    return

            for i, recipient in enumerate(recipients):
                to_address = recipient.get('address', recipient.get('Address'))

                # If token_info is provided, perform token transfers
                if token_info and token_manager:
                    token_symbol = token_info['Symbol']
                    token_address = token_info['Address']
                    token_decimals = int(token_info['Decimals'])

                    rprint(f"[yellow]Sending {amount} {token_symbol} to {to_address} (Transaction {i+1}/{len(recipients)})...[/yellow]")

                    # Perform token transfer
                    success, result = token_manager.transfer_token(
                        token_address,
                        from_address,
                        to_address,
                        float(amount),
                        private_key,
                        token_decimals
                    )

                    if success:
                        tx_hash = result
                    else:
                        tx_hash = f"Error: {result}"
                else:
                    # Regular BNB transfer
                    rprint(f"[yellow]Sending {amount} BNB to {to_address} (Transaction {i+1}/{len(recipients)})...[/yellow]")

                    # Get the current nonce for each transaction
                    current_nonce = self.get_current_nonce(from_address)

                    # Use increasing gas price multiplier for each transaction in the bulk
                    # This helps ensure later transactions don't get stuck
                    gas_multiplier = 1.5 + (i * 0.1)  # Start at 1.5x and increase by 10% for each transaction

                    tx_hash = self.perform_transaction(
                        from_address,
                        to_address,
                        amount,
                        private_key,
                        nonce=current_nonce,  # Use the current nonce from the blockchain
                        gas_price_multiplier=gas_multiplier,  # Increasing gas price
                        max_retries=3
                    )

                results.append({
                    'recipient': to_address,
                    'tx_hash': tx_hash
                })

                # Small delay between transactions to ensure proper nonce handling
                time.sleep(2)  # Increased delay to 2 seconds

            self.display_transaction_results(results)

        except Exception as e:
            rprint(f"[red]Bulk transaction failed: {str(e)}[/red]")

    def display_transaction_results(self, results):
        """Display transaction results in a table"""
        table = Table(title="Transaction Results")
        table.add_column("Recipient", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Transaction Hash", style="yellow")

        for result in results:
            tx_hash = result['tx_hash']

            if tx_hash.startswith('Error:'):
                status = "Failed"
                style = "red"
                display_hash = tx_hash.replace('Error: ', '')
            elif tx_hash.startswith('Pending:'):
                status = "Pending"
                style = "yellow"
                display_hash = tx_hash.replace('Pending: ', '')
            else:
                status = "Success"
                style = "green"
                display_hash = tx_hash

            table.add_row(
                result['recipient'],
                f"[{style}]{status}[/{style}]",
                display_hash
            )

        self.console.print(table)

    def handle_cancel_transaction(self, sender):
        """Handle cancellation of a stuck transaction"""
        try:
            # Check network status before proceeding
            network_ok, _ = self.check_network_status()
            if not network_ok:
                rprint("[red]Cannot proceed with transaction cancellation due to network issues.[/red]")
                return

            # Get sender's private key if not available
            private_key = sender.get('private_key', sender.get('Private Key', None))
            if not private_key:
                key_q = [
                    inquirer.Text('private_key',
                                 message="Enter sender's private key")
                ]
                key_answer = inquirer.prompt(key_q)
                if not key_answer:
                    return
                private_key = key_answer['private_key']

            from_address = sender.get('address', sender.get('Address'))

            # Ask for the nonce of the transaction to cancel
            nonce_q = [
                inquirer.Text('nonce',
                             message="Enter the nonce of the transaction to cancel",
                             validate=lambda _, x: x.isdigit())
            ]
            nonce_answer = inquirer.prompt(nonce_q)
            if not nonce_answer:
                return

            nonce = int(nonce_answer['nonce'])

            # Confirm cancellation
            rprint(f"[yellow]You are about to cancel transaction with nonce {nonce} from address {from_address}.[/yellow]")
            rprint(f"[yellow]This will send a 0 value transaction to yourself with the same nonce and a higher gas price.[/yellow]")

            confirm_q = [
                inquirer.Confirm('confirm',
                               message="Do you want to proceed with cancellation?",
                               default=True)
            ]
            confirm = inquirer.prompt(confirm_q)
            if not confirm or not confirm['confirm']:
                rprint("[yellow]Transaction cancellation cancelled by user.[/yellow]")
                return

            # Attempt to cancel the transaction
            success, result = self.cancel_transaction(from_address, private_key, nonce)

            if success:
                rprint(f"[green]Transaction with nonce {nonce} successfully cancelled![/green]")
                rprint(f"[green]Cancellation transaction hash: {result}[/green]")
            else:
                rprint(f"[red]Failed to cancel transaction: {result}[/red]")

        except Exception as e:
            rprint(f"[red]Error during transaction cancellation: {str(e)}[/red]")
