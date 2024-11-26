import inquirer
from rich import print as rprint
from rich.panel import Panel

class MenuManager:
    def __init__(self, wallet_manager, token_manager, transaction_manager):
        self.wallet_manager = wallet_manager
        self.token_manager = token_manager
        self.transaction_manager = transaction_manager

    def create_wallet_menu(self):
        """Menu for wallet creation"""
        try:
            questions = [
                inquirer.List('type',
                             message="Select creation type",
                             choices=['Single Wallet', 'Bulk Wallets', 'Import Wallet', 'Back to Main Menu'])
            ]
            answer = inquirer.prompt(questions)
            if not answer:
                return
            
            if answer['type'] == 'Single Wallet':
                wallet = self.wallet_manager.create_wallet()
                self.wallet_manager.save_wallet(wallet)
                rprint(Panel.fit(
                    f"[green]Wallet created successfully![/green]\n"
                    f"Address: {wallet['address']}\n"
                    f"Private Key: {wallet['private_key']}\n"
                    f"Secret Phrase: {wallet['secret_phrase']}"
                ))
            elif answer['type'] == 'Bulk Wallets':
                count_q = [
                    inquirer.Text('count',
                                 message="How many wallets to create?",
                                 validate=lambda _, x: x.isdigit() and int(x) > 0)
                ]
                count_answer = inquirer.prompt(count_q)
                if count_answer:
                    wallets = self.wallet_manager.create_bulk_wallets(int(count_answer['count']))
                    rprint(f"[green]Successfully created {len(wallets)} wallets![/green]")
                    self.wallet_manager.view_wallets()
            elif answer['type'] == 'Import Wallet':
                import_q = [
                    inquirer.List('method',
                                 message="Select import method",
                                 choices=['Private Key', 'Secret Phrase'])
                ]
                import_answer = inquirer.prompt(import_q)
                if not import_answer:
                    return
                
                wallet = None
                if import_answer['method'] == 'Private Key':
                    wallet = self.wallet_manager.import_wallet_from_private_key()
                else:
                    wallet = self.wallet_manager.import_wallet_from_mnemonic()
                    
                if wallet:
                    self.wallet_manager.save_wallet(wallet)
                    rprint(Panel.fit(
                        f"[green]Wallet imported successfully![/green]\n"
                        f"Address: {wallet['address']}\n"
                        f"Private Key: {wallet['private_key'][:10]}...\n"
                        f"Secret Phrase: {wallet['secret_phrase'][:20]}..."
                    ))
        except KeyboardInterrupt:
            rprint("\n[yellow]Operation cancelled by user[/yellow]")
            return
        except Exception as e:
            rprint(f"\n[red]Error: {str(e)}[/red]")
            return

    def check_wallet_balance(self, wallets):
        """Check wallet balance with error handling"""
        try:
            wallet_info = self.wallet_manager.select_wallet(wallets, "Select wallet to check balance")
            if not wallet_info:
                return
                
            address = wallet_info['address'] if 'address' in wallet_info else wallet_info['Address']
            
            # Get BNB balance
            bnb_balance = self.wallet_manager.get_bnb_balance(address)
            balances = [('BNB', bnb_balance)]
            
            # Get token balances in batch
            rprint("[yellow]Checking token balances...[/yellow]")
            tokens = self.token_manager.load_tokens()
            if tokens:
                token_balances = self.token_manager.get_token_balances(address, tokens)
                balances.extend(token_balances)
            
            self.wallet_manager.display_wallet_balances(address, balances)
        except KeyboardInterrupt:
            rprint("\n[yellow]Balance check cancelled by user[/yellow]")
            return
        except Exception as e:
            rprint(f"\n[red]Error checking balance: {str(e)}[/red]")
            return

    def manage_wallets_menu(self):
        """Menu for wallet management"""
        try:
            questions = [
                inquirer.List('action',
                             message="Select management action",
                             choices=['View Wallets', 'Check Balance', 'Back to Main Menu'])
            ]
            answer = inquirer.prompt(questions)
            if not answer:
                return
            
            if answer['action'] == 'View Wallets':
                self.wallet_manager.view_wallets()
            elif answer['action'] == 'Check Balance':
                wallets = self.wallet_manager.get_wallet_list()
                if not wallets:
                    rprint("[red]No wallets found! Please create a wallet first.[/red]")
                    return
                
                self.check_wallet_balance(wallets)
        except KeyboardInterrupt:
            rprint("\n[yellow]Operation cancelled by user[/yellow]")
            return
        except Exception as e:
            rprint(f"\n[red]Error: {str(e)}[/red]")
            return

    def transaction_menu(self):
        """Menu for performing transactions"""
        try:
            questions = [
                inquirer.List('type',
                             message="Select transaction type",
                             choices=['Single Transaction', 'Bulk Transaction', 'Back to Main Menu'])
            ]
            answer = inquirer.prompt(questions)
            if not answer:
                return
            
            if answer['type'] in ['Single Transaction', 'Bulk Transaction']:
                wallets = self.wallet_manager.get_wallet_list()
                if not wallets:
                    rprint("[red]No wallets found! Please create a wallet first.[/red]")
                    return
                    
                # Select sender wallet
                rprint("\n[cyan]Select sender wallet:[/cyan]")
                sender = self.wallet_manager.select_wallet(wallets, "Select sender wallet")
                if not sender:
                    return
                
                if answer['type'] == 'Single Transaction':
                    # Select recipient wallet
                    rprint("\n[cyan]Select recipient wallet:[/cyan]")
                    recipient = self.wallet_manager.select_wallet(wallets, "Select recipient wallet")
                    if not recipient:
                        return
                    
                    # Get amount
                    amount_q = [
                        inquirer.Text('amount',
                                     message="Enter amount in BNB",
                                     validate=lambda _, x: float(x) > 0)
                    ]
                    amount_answer = inquirer.prompt(amount_q)
                    if not amount_answer:
                        return
                    
                    self.transaction_manager.handle_single_transaction(
                        sender,
                        recipient,
                        float(amount_answer['amount'])
                    )
                
                else:  # Bulk Transaction
                    # Select recipient wallets
                    rprint("\n[cyan]Select recipient wallets:[/cyan]")
                    recipients = self.wallet_manager.select_multiple_wallets(
                        wallets,
                        "Select recipient wallets (space to select, enter to confirm)"
                    )
                    if not recipients:
                        return
                    
                    # Get amount per recipient
                    amount_q = [
                        inquirer.Text('amount',
                                     message="Enter amount per recipient in BNB",
                                     validate=lambda _, x: float(x) > 0)
                    ]
                    amount_answer = inquirer.prompt(amount_q)
                    if not amount_answer:
                        return
                    
                    self.transaction_manager.handle_bulk_transaction(
                        sender,
                        recipients,
                        float(amount_answer['amount'])
                    )
        except KeyboardInterrupt:
            rprint("\n[yellow]Transaction cancelled by user[/yellow]")
            return
        except Exception as e:
            rprint(f"\n[red]Transaction error: {str(e)}[/red]")
            return

    def main_menu(self):
        """Main application menu"""
        while True:
            try:
                questions = [
                    inquirer.List('action',
                                 message="Select an action",
                                 choices=['Create Wallet', 'Manage Wallets', 
                                        'Manage Tokens', 'Perform Transaction', 'Exit'])
                ]
                answer = inquirer.prompt(questions)
                if not answer:
                    break
                
                if answer['action'] == 'Create Wallet':
                    self.create_wallet_menu()
                elif answer['action'] == 'Manage Wallets':
                    self.manage_wallets_menu()
                elif answer['action'] == 'Manage Tokens':
                    self.token_manager.manage_tokens_menu("BSC Testnet")
                elif answer['action'] == 'Perform Transaction':
                    self.transaction_menu()
                elif answer['action'] == 'Exit':
                    break
            except KeyboardInterrupt:
                rprint("\n[yellow]Operation cancelled by user[/yellow]")
                continue
            except Exception as e:
                rprint(f"\n[red]Error: {str(e)}[/red]")
                continue
