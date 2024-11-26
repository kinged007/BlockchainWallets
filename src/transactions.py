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

    def perform_transaction(self, from_address, to_address, amount, private_key, nonce=None):
        """Perform a transaction"""
        try:
            # Ensure addresses are checksummed
            from_address = self.w3.to_checksum_address(from_address)
            to_address = self.w3.to_checksum_address(to_address)
            
            # Convert amount to Wei
            amount_wei = self.w3.to_wei(amount, 'ether')
            
            # Get the nonce (transaction count) if not provided
            if nonce is None:
                nonce = self.w3.eth.get_transaction_count(from_address)
            
            # Get current gas price with a small increase for faster confirmation
            gas_price = int(self.w3.eth.gas_price * 1.1)
            
            # Build transaction
            transaction = {
                'nonce': nonce,
                'gasPrice': gas_price,
                'gas': 21000,  # Standard gas limit for ETH transfer
                'to': to_address,
                'value': amount_wei,
                'data': b'',
                'chainId': self.chain_id
            }
            
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
            tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
            
            # Wait for transaction receipt
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
            
            if receipt['status'] == 1:
                return self.w3.to_hex(receipt['transactionHash'])
            else:
                return "Error: Transaction failed"
            
        except ValueError as e:
            if "insufficient funds" in str(e):
                return "Error: Insufficient funds for transaction"
            return f"Error: {str(e)}"
        except Exception as e:
            return f"Error: {str(e)}"

    def handle_single_transaction(self, sender, recipient, amount):
        """Handle a single transaction"""
        try:
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
            
            rprint(f"[yellow]Sending {amount} BNB from {from_address} to {to_address}...[/yellow]")
            
            tx_hash = self.perform_transaction(
                from_address,
                to_address,
                float(amount),
                private_key
            )
            
            if tx_hash.startswith('Error:'):
                rprint(f"[red]{tx_hash}[/red]")
            else:
                rprint(f"[green]Transaction successful![/green]")
                rprint(f"[cyan]Transaction hash: {tx_hash}[/cyan]")
                
        except Exception as e:
            rprint(f"[red]Transaction failed: {str(e)}[/red]")

    def handle_bulk_transaction(self, sender, recipients, amount):
        """Handle bulk transactions"""
        try:
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
            
            # Get initial nonce
            nonce = self.w3.eth.get_transaction_count(from_address)
            
            for i, recipient in enumerate(recipients):
                to_address = recipient.get('address', recipient.get('Address'))
                rprint(f"[yellow]Sending {amount} BNB to {to_address} (Transaction {i+1}/{len(recipients)})...[/yellow]")
                
                tx_hash = self.perform_transaction(
                    from_address,
                    to_address,
                    amount,
                    private_key,
                    nonce=nonce + i  # Increment nonce for each transaction
                )
                
                results.append({
                    'recipient': to_address,
                    'tx_hash': tx_hash
                })
                
                # Small delay between transactions to ensure proper nonce handling
                time.sleep(1)
            
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
            status = "Success" if not result['tx_hash'].startswith('Error:') else "Failed"
            style = "green" if status == "Success" else "red"
            
            table.add_row(
                result['recipient'],
                f"[{style}]{status}[/{style}]",
                result['tx_hash']
            )
        
        self.console.print(table)
