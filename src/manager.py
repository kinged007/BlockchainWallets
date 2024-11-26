from rich.console import Console
from rich.panel import Panel
import inquirer
from web3 import Web3

from .config import NETWORKS, WALLET_FILE, ERC20_ABI, MULTICALL_ADDRESSES
from .tokens import TokenManager
from .wallets import WalletManager
from .transactions import TransactionManager
from .menus import MenuManager

class BlockchainWalletManager:
    def __init__(self):
        self.console = Console()
        try:
            self.network = self.select_network()
            if not self.network:  # Handle cancellation during network selection
                raise KeyboardInterrupt
                
            self.w3 = Web3(Web3.HTTPProvider(NETWORKS[self.network]['rpc']))
            self.chain_id = NETWORKS[self.network]['chain_id']
            
            # Initialize managers
            self.token_manager = TokenManager(
                self.w3,
                NETWORKS[self.network]['tokens_file'],
                self.console,
                ERC20_ABI,
                MULTICALL_ADDRESSES[self.network]  # Pass network-specific multicall address
            )
            
            self.wallet_manager = WalletManager(
                self.w3,
                WALLET_FILE,
                self.console
            )
            
            self.transaction_manager = TransactionManager(
                self.w3,
                self.chain_id,
                self.console
            )
            
            self.menu_manager = MenuManager(
                self.wallet_manager,
                self.token_manager,
                self.transaction_manager
            )
        except (KeyboardInterrupt, EOFError):
            raise
        except Exception as e:
            self.console.print(f"[red]Initialization error: {str(e)}[/red]")
            raise

    def select_network(self):
        """Select network to connect to"""
        try:
            questions = [
                inquirer.List('network',
                             message="Select network to connect to",
                             choices=['mainnet', 'testnet'])
            ]
            answer = inquirer.prompt(questions)
            if not answer:
                return None
            return answer['network']
        except (KeyboardInterrupt, EOFError):
            return None
        except Exception as e:
            self.console.print(f"[red]Network selection error: {str(e)}[/red]")
            return None

    def run(self):
        """Run the application"""
        try:
            self.console.print(Panel.fit("Blockchain Wallet Manager", style="bold magenta"))
            self.menu_manager.main_menu()
        except (KeyboardInterrupt, EOFError):
            raise
        except Exception as e:
            self.console.print(f"[red]Runtime error: {str(e)}[/red]")
            raise
