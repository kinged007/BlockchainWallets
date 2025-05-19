"""
Token contract interaction module for the Blockchain Wallet Manager.
"""
import time
import inquirer
from rich import print as rprint
from rich.table import Table
from web3 import Web3

from .exceptions import TokenError, TransactionError, ValidationError
from .utils import validate_address, validate_amount, to_checksum_address

class TokenContractManager:
    """Manager for token contract interactions."""

    def __init__(self, wallet_manager, token_manager, transaction_manager):
        """
        Initialize the TokenContractManager.

        Args:
            wallet_manager: The wallet manager instance
            token_manager: The token manager instance
            transaction_manager: The transaction manager instance
        """
        self.wallet_manager = wallet_manager
        self.token_manager = token_manager
        self.transaction_manager = transaction_manager

    def execute_contract_function_menu(self):
        """Menu for executing token contract functions"""
        try:
            # First, select the token
            tokens = self.token_manager.load_tokens()
            if not tokens:
                rprint("[red]No tokens found! Please add tokens first using 'Manage Tokens'.[/red]")
                return

            token_choices = [f"{t['Symbol']} ({t['Name']}) - {t['Address']}" for t in tokens]
            token_q = [
                inquirer.List('token',
                             message="Select token contract",
                             choices=token_choices)
            ]
            token_answer = inquirer.prompt(token_q)
            if not token_answer:
                return

            # Extract token address from the selection
            selected_token_address = token_answer['token'].split(" - ")[1]
            selected_token_symbol = token_answer['token'].split(" ")[0]

            # Get token info
            token_info = None
            for token in tokens:
                if token['Address'] == selected_token_address:
                    token_info = token
                    break

            if not token_info:
                rprint(f"[red]Token with address {selected_token_address} not found![/red]")
                return

            # Get contract functions
            rprint(f"[yellow]Fetching functions for {selected_token_symbol} contract...[/yellow]")
            functions = self.token_manager.get_contract_functions(selected_token_address)

            if not functions:
                rprint(f"[red]No functions found for {selected_token_symbol} contract![/red]")
                return

            # Display functions
            rprint(f"[green]Found {len(functions)} functions in {selected_token_symbol} contract:[/green]")

            # Create a table of functions
            table = Table(title=f"{selected_token_symbol} Contract Functions")
            table.add_column("Function", style="cyan")
            table.add_column("Type", style="green")
            table.add_column("Inputs", style="yellow")

            for func in functions:
                func_name = func['name']
                func_type = "Read-Only" if func['constant'] else "Write"

                # Format inputs
                inputs_str = ""
                for i, inp in enumerate(func['inputs']):
                    inputs_str += f"{inp.get('name', f'param{i}')} ({inp.get('type', 'unknown')})"
                    if i < len(func['inputs']) - 1:
                        inputs_str += ", "

                table.add_row(func_name, func_type, inputs_str)

            self.token_manager.console.print(table)

            # Select function to execute
            function_choices = [f"{func['name']} ({'Read' if func['constant'] else 'Write'})" for func in functions]
            function_choices.append("Back to Main Menu")

            function_q = [
                inquirer.List('function',
                             message="Select function to execute",
                             choices=function_choices)
            ]
            function_answer = inquirer.prompt(function_q)
            if not function_answer or function_answer['function'] == "Back to Main Menu":
                return

            selected_function = function_answer['function'].split(" ")[0]

            # Find the function details
            function_info = None
            for func in functions:
                if func['name'] == selected_function:
                    function_info = func
                    break

            if not function_info:
                rprint(f"[red]Function {selected_function} not found![/red]")
                return

            # Handle the selected function
            self._handle_contract_function(
                selected_token_address,
                selected_token_symbol,
                function_info,
                token_info,
                tokens
            )

        except KeyboardInterrupt:
            rprint("\n[yellow]Operation cancelled by user[/yellow]")
            return
        except Exception as e:
            rprint(f"\n[red]Error executing contract function: {str(e)}[/red]")
            return

    def _handle_contract_function(
            self,
            selected_token_address,
            selected_token_symbol,
            function_info,
            token_info,
            tokens
        ):
        """
        Handle the execution of a specific contract function.

        Args:
            selected_token_address: The address of the selected token contract
            selected_token_symbol: The symbol of the selected token
            function_info: Information about the selected function
            token_info: Information about the selected token
            tokens: List of all available tokens
        """
        try:
            # Special handling for burnFrom, transferFrom, and similar functions that require approval
            requires_approval = function_info['name'].lower() in ['burnfrom', 'transferfrom', 'spendallowance']
            if requires_approval:
                self._handle_approval_process(selected_token_address, selected_token_symbol, token_info)

            # Get function arguments
            args = self._get_function_arguments(function_info, selected_token_symbol)
            if args is None:  # User cancelled
                return

            # For write functions, we need a wallet with private key
            if not function_info['constant']:
                self._execute_write_function(
                    selected_token_address,
                    selected_token_symbol,
                    function_info['name'],
                    args
                )
            else:
                # For read-only functions, no wallet needed
                self._execute_read_function(
                    selected_token_address,
                    selected_token_symbol,
                    function_info['name'],
                    args,
                    tokens
                )

        except KeyboardInterrupt:
            rprint("\n[yellow]Operation cancelled by user[/yellow]")
        except Exception as e:
            rprint(f"\n[red]Error handling contract function: {str(e)}[/red]")

    def _handle_approval_process(self, token_address, token_symbol, token_info):
        """
        Handle the approval process for functions that require it.

        Args:
            token_address: The address of the token contract
            token_symbol: The symbol of the token
            token_info: Information about the token
        """
        try:
            rprint("[yellow]This function requires token approval first![/yellow]")
            rprint("[cyan]The token owner must approve the spender before this function can be called.[/cyan]")

            approval_q = [
                inquirer.Confirm('handle_approval',
                               message="Would you like to handle the approval process first?",
                               default=True)
            ]
            handle_approval = inquirer.prompt(approval_q)

            # Flag to track if we need to handle approval
            need_approval = handle_approval and handle_approval['handle_approval']

            if need_approval:
                # Get the token owner (who needs to approve)
                rprint("[cyan]Select the token owner wallet (who will approve the tokens):[/cyan]")
                wallets = self.wallet_manager.get_wallet_list()
                if not wallets:
                    rprint("[red]No wallets found! Please create a wallet first.[/red]")
                    return

                owner = self.wallet_manager.select_wallet(
                    wallets,
                    "Select token owner wallet",
                    require_private_key=True  # Only show wallets with private keys
                )
                if not owner:
                    return

                # Get the spender (who will be allowed to burn/transfer the tokens)
                rprint("[cyan]Select the spender wallet (who will be allowed to burn/transfer the tokens):[/cyan]")
                spender = self.wallet_manager.select_wallet(wallets, "Select spender wallet")
                if not spender:
                    return

                # Get the amount to approve
                amount_q = [
                    inquirer.Text('amount',
                                 message=f"Enter amount of {token_symbol} to approve",
                                 validate=lambda _, x: float(x) > 0)
                ]
                amount_answer = inquirer.prompt(amount_q)
                if not amount_answer:
                    return

                amount = float(amount_answer['amount'])

                # Get owner's private key
                owner_private_key = owner.get('private_key', owner.get('Private Key', None))
                if not owner_private_key:
                    key_q = [
                        inquirer.Text('private_key',
                                     message="Enter owner's private key")
                    ]
                    key_answer = inquirer.prompt(key_q)
                    if not key_answer:
                        return
                    owner_private_key = key_answer['private_key']

                owner_address = owner.get('address', owner.get('Address'))
                spender_address = spender.get('address', spender.get('Address'))

                # Check current allowance
                token_decimals = int(token_info['Decimals'])
                current_allowance_raw = self.token_manager.get_token_allowance(
                    token_address,
                    owner_address,
                    spender_address
                )
                current_allowance = float(current_allowance_raw) / (10 ** token_decimals)

                rprint(f"[cyan]Current allowance: {current_allowance} {token_symbol}[/cyan]")

                # Check if we already have sufficient allowance
                if current_allowance >= amount:
                    rprint(f"[green]The current allowance ({current_allowance} {token_symbol}) is already sufficient for this operation.[/green]")
                    proceed_q = [
                        inquirer.Confirm('proceed',
                                       message="Would you like to proceed with the original function?",
                                       default=True)
                    ]
                    proceed = inquirer.prompt(proceed_q)
                    if proceed and proceed['proceed']:
                        rprint("[yellow]Proceeding with the original function...[/yellow]")
                        # Skip the approval process
                        return
                    else:
                        rprint("[yellow]Setting a new allowance anyway...[/yellow]")

                # Execute the approve function
                rprint(f"[yellow]Approving {amount} {token_symbol} for {spender_address}...[/yellow]")

                # Ask for gas limit for approval
                gas_limit = 100000  # Default gas limit for approval
                custom_gas_q = [
                    inquirer.Confirm('custom_gas',
                                   message="Would you like to set a custom gas limit for approval? (Default: 100,000)",
                                   default=False)
                ]
                custom_gas = inquirer.prompt(custom_gas_q)

                if custom_gas and custom_gas['custom_gas']:
                    gas_limit_q = [
                        inquirer.Text('gas_limit',
                                     message="Enter gas limit (50,000 - 1,000,000)",
                                     validate=lambda _, x: x.isdigit() and 50000 <= int(x) <= 1000000)
                    ]
                    gas_limit_answer = inquirer.prompt(gas_limit_q)
                    if gas_limit_answer:
                        gas_limit = int(gas_limit_answer['gas_limit'])

                # Call the approve function
                success, result = self.token_manager.execute_contract_function(
                    token_address,
                    'approve',
                    [spender_address, amount],  # Args for approve function
                    owner_address,
                    owner_private_key,
                    gas_limit
                )

                if not success:
                    rprint(f"[red]Approval failed: {result}[/red]")
                    rprint("[yellow]Cannot proceed with the original function without approval.[/yellow]")
                    raise TokenError("Approval failed")

                rprint(f"[green]Approval successful! Transaction hash: {result}[/green]")
                rprint("[yellow]Now proceeding with the original function...[/yellow]")

                # Wait a bit for the approval transaction to be confirmed
                rprint("[yellow]Waiting for approval transaction to be confirmed...[/yellow]")
                time.sleep(5)  # Wait 5 seconds

        except KeyboardInterrupt:
            rprint("\n[yellow]Operation cancelled by user[/yellow]")
            raise
        except Exception as e:
            rprint(f"\n[red]Error in approval process: {str(e)}[/red]")
            raise

    def _get_function_arguments(self, function_info, token_symbol):
        """
        Get arguments for a contract function from user input.

        Args:
            function_info: Information about the function
            token_symbol: The symbol of the token

        Returns:
            list: List of function arguments or None if cancelled
        """
        try:
            args = []
            for i, inp in enumerate(function_info['inputs']):  # i is the parameter index (0-based)
                param_name = inp.get('name', f'param{i}')
                param_type = inp.get('type', 'unknown')

                # Special handling for address type
                if param_type == 'address' and param_name.lower() in ['to', 'recipient', 'dst', 'destination']:
                    # This might be an address parameter, offer wallet selection
                    wallets = self.wallet_manager.get_wallet_list()
                    if wallets:
                        use_wallet_q = [
                            inquirer.Confirm('use_wallet',
                                           message=f"Would you like to select a wallet for {param_name}?",
                                           default=True)
                        ]
                        use_wallet = inquirer.prompt(use_wallet_q)

                        if use_wallet and use_wallet['use_wallet']:
                            wallet = self.wallet_manager.select_wallet(wallets, f"Select wallet for {param_name}")
                            if wallet:
                                address = wallet.get('address', wallet.get('Address'))
                                args.append(address)
                                continue

                # For other parameters, ask for input
                param_q = [
                    inquirer.Text('value',
                                 message=f"Enter value for {param_name} ({param_type})")
                ]
                param_answer = inquirer.prompt(param_q)
                if not param_answer:
                    return None

                # Convert input to appropriate type
                value = param_answer['value']

                # Special handling for uint types that might represent token amounts
                if param_type.startswith('uint') or param_type.startswith('int'):
                    # For token amount parameters, we'll pass the human-readable value
                    # The execute_contract_function method will handle the conversion
                    if function_info['name'].lower() in ['transfer', 'transferfrom', 'approve', 'burn', 'burnfrom', 'mint', 'increaseallowance', 'decreaseallowance']:
                        param_name = inp.get('name', '').lower()
                        # Check if parameter name suggests it's an amount
                        is_amount_param = any(term in param_name for term in ['amount', 'value', 'tokens', 'quantity', 'supply', 'balance', 'allowance'])

                        # Special case for burnFrom - the second parameter is always the amount
                        if function_info['name'].lower() == 'burnfrom' and i == 1:
                            is_amount_param = True

                        if is_amount_param:
                            # This is likely a token amount, keep it as a float
                            value = float(value)
                            rprint(f"[yellow]Treating {param_name} as a token amount. You entered {value} tokens.[/yellow]")
                        else:
                            # Regular integer parameter
                            value = int(value)
                    else:
                        # Regular integer parameter
                        value = int(value)
                elif param_type == 'bool':
                    value = value.lower() in ['true', 'yes', 'y', '1']
                elif param_type == 'address':
                    value = to_checksum_address(value)

                args.append(value)

            return args

        except KeyboardInterrupt:
            rprint("\n[yellow]Operation cancelled by user[/yellow]")
            return None
        except Exception as e:
            rprint(f"\n[red]Error getting function arguments: {str(e)}[/red]")
            return None

    def _execute_write_function(self, token_address, token_symbol, function_name, args):
        """
        Execute a write function on a token contract.

        Args:
            token_address: The address of the token contract
            token_symbol: The symbol of the token
            function_name: The name of the function to execute
            args: The arguments for the function
        """
        try:
            rprint("[yellow]This is a write function that will modify the blockchain state.[/yellow]")
            rprint("[yellow]You need to select a wallet with a private key to sign the transaction.[/yellow]")

            wallets = self.wallet_manager.get_wallet_list()
            if not wallets:
                rprint("[red]No wallets found! Please create a wallet first.[/red]")
                return

            sender = self.wallet_manager.select_wallet(
                wallets,
                "Select wallet to sign transaction",
                require_private_key=True  # Only show wallets with private keys
            )
            if not sender:
                return

            # Get private key if not available
            private_key = sender.get('private_key', sender.get('Private Key', None))
            if not private_key:
                key_q = [
                    inquirer.Text('private_key',
                                 message="Enter wallet's private key")
                ]
                key_answer = inquirer.prompt(key_q)
                if not key_answer:
                    return
                private_key = key_answer['private_key']

            from_address = sender.get('address', sender.get('Address'))

            # Ask for gas limit
            gas_limit = 200000  # Default gas limit
            custom_gas_q = [
                inquirer.Confirm('custom_gas',
                               message="Would you like to set a custom gas limit? (Default: 200,000)",
                               default=False)
            ]
            custom_gas = inquirer.prompt(custom_gas_q)

            if custom_gas and custom_gas['custom_gas']:
                gas_limit_q = [
                    inquirer.Text('gas_limit',
                                 message="Enter gas limit (100,000 - 5,000,000)",
                                 validate=lambda _, x: x.isdigit() and 100000 <= int(x) <= 5000000)
                ]
                gas_limit_answer = inquirer.prompt(gas_limit_q)
                if gas_limit_answer:
                    gas_limit = int(gas_limit_answer['gas_limit'])

            # Execute the function
            rprint(f"[yellow]Executing {function_name} on {token_symbol} contract with gas limit {gas_limit}...[/yellow]")
            success, result = self.token_manager.execute_contract_function(
                token_address,
                function_name,
                args,
                from_address,
                private_key,
                gas_limit
            )

            self._display_function_result(success, result, token_symbol)

        except KeyboardInterrupt:
            rprint("\n[yellow]Operation cancelled by user[/yellow]")
        except Exception as e:
            rprint(f"\n[red]Error executing write function: {str(e)}[/red]")

    def _execute_read_function(self, token_address, token_symbol, function_name, args, tokens):
        """
        Execute a read-only function on a token contract.

        Args:
            token_address: The address of the token contract
            token_symbol: The symbol of the token
            function_name: The name of the function to execute
            args: The arguments for the function
            tokens: List of all available tokens
        """
        try:
            # For read-only functions, no wallet needed
            rprint(f"[yellow]Executing {function_name} on {token_symbol} contract...[/yellow]")
            success, result = self.token_manager.execute_contract_function(
                token_address,
                function_name,
                args
            )

            self._display_function_result(success, result, token_symbol, token_address, tokens)

        except KeyboardInterrupt:
            rprint("\n[yellow]Operation cancelled by user[/yellow]")
        except Exception as e:
            rprint(f"\n[red]Error executing read function: {str(e)}[/red]")

    def _display_function_result(self, success, result, token_symbol, token_address=None, tokens=None):
        """
        Display the result of a function execution.

        Args:
            success: Whether the function execution was successful
            result: The result of the function execution
            token_symbol: The symbol of the token
            token_address: The address of the token contract (optional)
            tokens: List of all available tokens (optional)
        """
        if success:
            rprint(f"[green]Function executed successfully![/green]")

            # Format result for display
            if isinstance(result, (list, tuple)):
                rprint("[cyan]Result:[/cyan]")
                for i, item in enumerate(result):
                    rprint(f"  [yellow]{i}:[/yellow] {item}")
            elif isinstance(result, dict):
                rprint("[cyan]Result:[/cyan]")
                # Special handling for token amount results
                if "tokens" in result and "raw_units" in result:
                    rprint(f"  [yellow]Tokens:[/yellow] {result['tokens']}")
                    rprint(f"  [yellow]Raw Units:[/yellow] {result['raw_units']}")
                else:
                    for key, value in result.items():
                        rprint(f"  [yellow]{key}:[/yellow] {value}")
            else:
                # Check if this might be a token amount result (large integer)
                if isinstance(result, int) and result > 1000000000000000000 and tokens and token_address:
                    # This is likely a token amount in raw units
                    token_info = None
                    for token in tokens:
                        if to_checksum_address(token['Address']) == to_checksum_address(token_address):
                            token_info = token
                            break

                    if token_info:
                        token_decimals = int(token_info['Decimals'])
                        human_readable = float(result) / (10 ** token_decimals)
                        rprint(f"[cyan]Result (raw units):[/cyan] {result}")
                        rprint(f"[cyan]Result (tokens):[/cyan] {human_readable}")
                    else:
                        rprint(f"[cyan]Result:[/cyan] {result}")
                else:
                    rprint(f"[cyan]Result:[/cyan] {result}")
        else:
            rprint(f"[red]Function execution failed: {result}[/red]")

            # Add blockchain explorer link for transaction hashes
            if isinstance(result, str) and result.startswith("Transaction failed. Hash: 0x"):
                tx_hash = result.split("Hash: ")[1]
                network = "testnet" if "testnet" in self.token_manager.tokens_file.lower() else "mainnet"
                explorer_url = f"https://{'testnet.' if network == 'testnet' else ''}bscscan.com/tx/{tx_hash}"
                rprint(f"[cyan]View transaction on BSCScan: {explorer_url}[/cyan]")

            # Suggest possible solutions
            rprint("[yellow]Possible solutions:[/yellow]")
            rprint("  1. Check if you have sufficient token balance and BNB for gas")
            rprint("  2. Try increasing the gas limit (for complex operations)")
            rprint("  3. Verify you have the necessary permissions for this operation")
            rprint("  4. Check if the contract has any transfer restrictions")