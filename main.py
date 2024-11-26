from src.manager import BlockchainWalletManager
from rich import print as rprint

def main():
    """Main application entry point"""
    try:
        manager = BlockchainWalletManager()
        manager.run()
    except (KeyboardInterrupt, EOFError):
        pass
    except Exception as e:
        rprint(f"\n[red]Error: {str(e)}[/red]")
    finally:
        rprint("\n[green]Goodbye![/green]")

if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        rprint("\n[yellow]Application terminated by user[/yellow]")
        rprint("\n[green]Goodbye![/green]")
    except Exception as e:
        rprint(f"\n[red]Fatal error: {str(e)}[/red]")
        rprint("\n[green]Goodbye![/green]")
