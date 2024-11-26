import csv
import os
from rich.table import Table
from rich.panel import Panel
import inquirer
from rich import print as rprint
from web3 import Web3
from eth_account import Account

class WalletManager:
    def __init__(self, w3: Web3, wallet_file: str, console):
        self.w3 = w3
        self.wallet_file = wallet_file
        self.console = console
        self.ensure_wallet_file()

    def ensure_wallet_file(self):
        """Create wallet file if it doesn't exist"""
        if not os.path.exists(self.wallet_file):
            with open(self.wallet_file, 'w', newline='') as file:
                writer = csv.writer(file)
                writer.writerow(['Address', 'Private Key', 'Secret Phrase'])

    def get_wallet_list(self):
        """Get list of stored wallets"""
        wallets = []
        if os.path.exists(self.wallet_file):
            with open(self.wallet_file, 'r') as file:
                reader = csv.DictReader(file)
                wallets = list(reader)
        return wallets

    def save_wallet(self, wallet_data):
        """Save wallet information to CSV"""
        with open(self.wallet_file, 'a', newline='') as file:
            writer = csv.writer(file)
            writer.writerow([
                wallet_data['address'],
                wallet_data['private_key'],
                wallet_data['secret_phrase']
            ])

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
        for _ in range(count):
            wallet = self.create_wallet()
            self.save_wallet(wallet)
            wallets.append(wallet)
        return wallets

    def import_wallet_from_private_key(self):
        """Import a wallet using private key"""
        try:
            questions = [
                inquirer.Text('private_key',
                             message="Enter private key")
            ]
            answers = inquirer.prompt(questions)
            if not answers:
                return None
            
            account = Account.from_key(answers['private_key'])
            return {
                'address': account.address,
                'private_key': answers['private_key'],
                'secret_phrase': 'Imported via private key'
            }
        except KeyboardInterrupt:
            rprint("\n[yellow]Import cancelled by user[/yellow]")
            return None
        except Exception as e:
            rprint("[red]Invalid private key![/red]")
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
        except Exception as e:
            rprint("[red]Invalid mnemonic phrase![/red]")
            return None

    def get_bnb_balance(self, address):
        """Get BNB balance for a wallet"""
        try:
            balance_wei = self.w3.eth.get_balance(address)
            return float(self.w3.from_wei(balance_wei, 'ether'))
        except Exception as e:
            return 0.0

    def display_wallet_balances(self, address, token_balances):
        """Display all balances for a wallet"""
        table = Table(title=f"Wallet Balances for {address}")
        table.add_column("Token", style="cyan")
        table.add_column("Balance", style="green")
        
        for token, balance in token_balances:
            table.add_row(token, f"{balance:.8f}")
        
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

        with open(self.wallet_file, 'r') as file:
            reader = csv.reader(file)
            next(reader)  # Skip header
            for row in reader:
                # Truncate private key and secret phrase for display
                table.add_row(
                    row[0],
                    row[1][:10] + "...",
                    row[2][:20] + "..."
                )
        
        self.console.print(table)

    def select_wallet(self, wallets, message="Select a wallet"):
        """Present wallet selection menu"""
        try:
            choices = [f"{w['Address']} (Balance: {self.get_bnb_balance(w['Address'])} BNB)" for w in wallets]
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
                return next((w for w in wallets if w['Address'] == selected_address), None)
        except KeyboardInterrupt:
            return None
        except Exception as e:
            rprint(f"[red]Error selecting wallet: {str(e)}[/red]")
            return None

    def select_multiple_wallets(self, wallets, message="Select wallets"):
        """Present multi-select wallet menu"""
        try:
            choices = [f"{w['Address']} (Balance: {self.get_bnb_balance(w['Address'])} BNB)" for w in wallets]
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
                return wallets
            
            for selection in answer['wallets']:
                address = selection.split(" ")[0]
                wallet = next((w for w in wallets if w['Address'] == address), None)
                if wallet:
                    selected_wallets.append(wallet)
            
            return selected_wallets
        except KeyboardInterrupt:
            return None
        except Exception as e:
            rprint(f"[red]Error selecting wallets: {str(e)}[/red]")
            return None
