# Version: 1.1

from xrpl.wallet import Wallet
from xrpl.constants import CryptoAlgorithm
from xrpl.models import requests, Payment
from xrpl.clients import WebsocketClient
from xrpl.models.amounts import IssuedCurrencyAmount
from xrpl.transaction import autofill_and_sign, sign
from xrpl.utils.str_conversions import hex_to_str
from tabulate import tabulate
import time
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
            with open(input(f"{Color.CYAN}Seed List File:{Color.RESET} ").strip(), "r") as file:
                seed_list = [x for x in file.read().splitlines() if x.strip() and not x.strip().startswith("#")]
                file.close()
            
            if len(seed_list) < 1:
                print("Error: This seed list file is empty.")
                continue

            break
        except Exception:
            print("Error: Invalid seed list file.\n")
            continue

    client = WebsocketClient(url="wss://xrplcluster.com")
    client.open()

    trustlines = client.request(request=requests.AccountLines(account=Wallet.from_seed(seed=seed_list[0], algorithm=CryptoAlgorithm.SECP256K1).address)).result["lines"]
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

    try:
        trustline_name = hex_to_str(trustline["currency"]).replace("\x00", "")
    except Exception:
        trustline_name = trustline["currency"]

    while True:
        try:
            retain_value = float(input(f"{Color.CYAN}Retain Value:{Color.RESET} "))
            break
        except Exception:
            print("Error: Invalid retain value.\n")
            continue
    
    destination_address = input(f"{Color.CYAN}Destination Address:{Color.RESET} ").strip()
    
    while True:
        try:
            sleep_time = float(input(f"{Color.CYAN}Sleep Time:{Color.RESET} "))
            break
        except Exception:
            print("Error: Invalid sleep time.\n")
            continue

    print("")

    for seed in seed_list:
        try:
            sender_wallet = Wallet.from_seed(seed=seed, algorithm=CryptoAlgorithm.SECP256K1)
        except Exception:
            print(f"Error: Invalid seed {seed}")
            continue
        
        if sender_wallet.address == destination_address:
            print(f"Skip: {destination_address} cannot send to self.")
            continue

        sender_lines = client.request(request=requests.AccountLines(account=sender_wallet.address)).result["lines"]
        sender_balance = None
        for line in sender_lines:
            if line["account"] == trustline["account"] and line["currency"] == trustline["currency"]:
                sender_balance = float(line["balance"])
        
        if not sender_balance:
            print(f"Skip: {sender_wallet.address} does not have trustline set.")
            continue

        value = float(f"{(sender_balance - retain_value):.15f}")

        if value <= 0:
            print(f"Skip: {sender_wallet.address} insufficient trustline balance.")
            continue

        amount = IssuedCurrencyAmount(
            currency=trustline["currency"],
            issuer=trustline["account"],
            value=value
        )
        
        tx = Payment(
            account=sender_wallet.address,
            amount=amount,
            destination=destination_address
        )

        signed_tx = autofill_and_sign(transaction=tx, client=client, wallet=sender_wallet)

        result = client.request(request=requests.SubmitOnly(tx_blob=signed_tx.blob())).result
        engine_result = result["engine_result"]
        result_message = result["engine_result_message"]

        if engine_result == "tesSUCCESS":
            print(f"{Color.GREEN}Success: {sender_wallet.address} -> {destination_address}{Color.RESET} | {value} {trustline_name}")
            time.sleep(sleep_time)
        else:
            print(f"{Color.RED}Error: {sender_wallet.address} -> {destination_address} | {engine_result}: {result_message}{Color.RESET}")
        

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        exit()
