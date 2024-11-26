import csv
import os
from rich.table import Table
import inquirer
from rich import print as rprint
from web3 import Web3
from typing import Dict, List, Tuple
from .config import MULTICALL_ABI



class TokenManager:
    def __init__(self, w3: Web3, tokens_file: str, console, abi, multicall_address: str):
        self.w3 = w3
        self.tokens_file = tokens_file
        self.console = console
        self.abi = abi
        self.token_contracts: Dict[str, object] = {}  # Cache for token contracts
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

    def get_token_contract(self, address: str):
        """Get or create token contract instance"""
        if address not in self.token_contracts:
            self.token_contracts[address] = self.w3.eth.contract(
                address=Web3.to_checksum_address(address),
                abi=self.abi
            )
        return self.token_contracts[address]

    def get_token_balances(self, wallet_address: str, tokens: List[dict]) -> List[Tuple[str, float]]:
        """Get balances for multiple tokens using multicall"""
        try:
            if not tokens:
                return []

            # Prepare calls for balanceOf
            calls = []
            for token in tokens:
                token_contract = self.get_token_contract(token['Address'])
                balance_data = token_contract.encode_abi(
                    abi_element_identifier='balanceOf',
                    args=[wallet_address]
                )
                calls.append({
                    'target': Web3.to_checksum_address(token['Address']),
                    'callData': balance_data
                })

            # Make multicall
            _, return_data = self.multicall.functions.aggregate(calls).call()

            # Process results
            balances = []
            for i, token in enumerate(tokens):
                try:
                    balance = self.w3.codec.decode(['uint256'], return_data[i])[0]
                    if balance > 0:
                        decimals = int(token['Decimals'])
                        balance_float = float(balance) / (10 ** decimals)
                        balances.append((token['Symbol'], balance_float))
                except Exception as e:
                    rprint(f"[yellow]Warning: Error processing {token['Symbol']}: {str(e)}[/yellow]")
                    continue

            return balances
        except Exception as e:
            rprint(f"[yellow]Warning: Error getting token balances: {str(e)}[/yellow]")
            return []

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
