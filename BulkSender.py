from xrpl.wallet import Wallet
from xrpl.constants import CryptoAlgorithm
from xrpl.models import requests, Payment
from xrpl.clients import WebsocketClient
from xrpl.models.amounts import IssuedCurrencyAmount
from xrpl.transaction import autofill_and_sign, sign
from xrpl.utils.str_conversions import hex_to_str
from tabulate import tabulate
import sys
import os

class Color:
    RED = "\u001b[31;1m"
    GREEN = "\u001b[32;1m"
    YELLOW = "\u001b[33;1m"
    BLUE = "\u001b[34;1m"
    PURPLE = "\u001b[35;1m"
    CYAN = "\u001b[36;1m"
    RESET = "\u001b[0;0m"

def clear_console():
    if sys.platform == "win32":
        os.system("cls")
    elif sys.platform in ["linux", "linux2"]:
        os.system("clear")

def main():
    clear_console()

    while True:
        try:
            sender_seed = input(f"{Color.CYAN}Sender Seed:{Color.RESET} ").strip()
            sender_account = Wallet.from_seed(seed=sender_seed, algorithm=CryptoAlgorithm.SECP256K1)
            break
        except Exception:
            print("Error: Invalid account seed.\n")
            continue

    client = WebsocketClient(url="wss://xrplcluster.com")
    client.open()

    trustlines = client.request(request=requests.AccountLines(account=sender_account.address)).result["lines"]
    print("\nSelect a trustline: ")
    trustline_tabulate = []
    for i, trustline in enumerate(trustlines, start=1):
        try:
            currency_name = hex_to_str(trustline["currency"]).replace("\x00", "")
        except Exception:
            currency_name = trustline["currency"]
        
        trustline_tabulate.append([i, currency_name, trustline["balance"]])
    
    print(tabulate(trustline_tabulate, headers=["#", "Name", "Balance"]), "\n")

    while True:
        try:
            select_trustline = int(input(f"{Color.CYAN}Trustline #:{Color.RESET} "))
            trustline = trustlines[select_trustline - 1]
            break
        except Exception:
            print("Error: Invalid trustline number.\n")
            continue

    while True:
        try:
            value = float(input(f"{Color.CYAN}Value:{Color.RESET} "))
            break
        except Exception:
            print("Error: Invalid value.\n")
            continue
    
    while True:
        try:
            with open(input(f"{Color.CYAN}Destination List File:{Color.RESET} "), "r") as file:
                destination_list = [x.strip() for x in file.read().splitlines() if x.strip() and not x.strip().startswith("#") and not x.strip() == sender_account.address]
                file.close()
            break
        except Exception:
            print("Error: Invalid destination list file.\n")
            continue
    
    print("")

    amount = IssuedCurrencyAmount(
        currency=trustline["currency"],
        issuer=trustline["account"],
        value=value
    )

    for destination in destination_list:
        tx = Payment(
            account=sender_account.address,
            amount=amount,
            destination=destination
        )

        signed_tx = autofill_and_sign(transaction=tx, client=client, wallet=sender_account)

        result = client.request(request=requests.SubmitOnly(tx_blob=signed_tx.blob())).result
        engine_result = result["engine_result"]
        result_message = result["engine_result_message"]

        if engine_result == "tesSUCCESS":
            destination_account_lines = client.request(request=requests.AccountLines(account=destination)).result["lines"]
            destination_balance = None
            for destination_trustline in destination_account_lines:
                if destination_trustline["account"] == trustline["account"] and destination_trustline["currency"] == trustline["currency"]:
                    destination_balance = destination_trustline["balance"]

            print(f"{Color.GREEN}Success: {sender_account.address} -> {destination} | New Balance: {destination_balance or 'Unable to get balance'}{Color.RESET}")
        else:
            print(f"{Color.RED}Error: {sender_account.address} -> {destination} | {engine_result}: {result_message}{Color.RESET}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        exit()
