#!/usr/bin/env python3

import os, sys, re, socket, threading, time
from datetime import datetime

# Auto-install missing modules
required = ["requests", "dnspython", "pyfiglet", "colorama", "rich", "whois"]
for lib in required:
    try:
        __import__(lib if lib != "whois" else "whois")
    except ImportError:
        os.system(f"pip install {lib}")

import requests, dns.resolver, pyfiglet, urllib3
from colorama import Fore, init
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
import whois

urllib3.disable_warnings()
init(autoreset=True)
console = Console()
report = []
lock = threading.Lock()

def clear(): os.system("clear" if os.name != "nt" else "cls")

def banner(text, color="bold green"):
    console.print(pyfiglet.figlet_format(text), style=color)

def intro():
    os.system("pkill php > /dev/null 2>&1")
    clear()
    banner("Pathan", "bold red")
    console.print(Panel("[bold cyan]>> By Arbab Khan | Pathan-HACKERS <<[/]"))
    console.print(Panel("ARBAB Recon Tool [v2] with Takeover + Rich UI", style="bold green"))

def log(text):
    with lock:
        print(text)
        report.append(text)

def is_ip(target):
    return re.match(r"^\d{1,3}(\.\d{1,3}){3}$", target)

def ip_lookup(target):
    log(Fore.YELLOW + "\n[+] IP Lookup")
    try:
        ip = target if is_ip(target) else socket.gethostbyname(target)
        res = requests.get(f"http://ip-api.com/json/{ip}").json()
        table = Table(title="IP Info")
        table.add_column("Field", style="cyan")
        table.add_column("Value", style="magenta")
        for k in ['query', 'isp', 'org', 'country', 'regionName', 'city', 'zip', 'timezone']:
            table.add_row(k, str(res.get(k, 'N/A')))
            report.append(f"{k}: {res.get(k, 'N/A')}")
        console.print(table)
        return ip
    except Exception as e:
        log(Fore.RED + f"[-] IP Lookup Failed: {e}")
        return target

def dns_lookup(domain):
    log(Fore.YELLOW + "\n[+] DNS Records")
    try:
        resolver = dns.resolver.Resolver()
        resolver.nameservers = ['8.8.8.8', '1.1.1.1']
        table = Table(title="DNS Records")
        table.add_column("Type", style="green")
        table.add_column("Value", style="white")
        for record in ['A', 'MX', 'NS', 'TXT']:
            try:
                answers = resolver.resolve(domain, record)
                for r in answers:
                    table.add_row(record, r.to_text())
                    report.append(f"{record}: {r.to_text()}")
            except:
                table.add_row(record, "❌ Not Found")
        console.print(table)
    except Exception as e:
        log(Fore.RED + f"[-] DNS Lookup Failed: {e}")

def subdomain_finder(domain):
    log(Fore.YELLOW + "\n[+] Subdomain Finder + Takeover Check")
    fingerprints = {
        "GitHub": "There isn't a GitHub Pages site here.",
        "Heroku": "No such app",
        "Netlify": "Page Not Found",
        "AWS/S3": "NoSuchBucket",
        "Bitbucket": "Repository not found",
        "Ghost": "The thing you were looking for is no longer here"
    }
    found_subdomains = set()
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        url = f"https://crt.sh/?q=%25.{domain}&output=json"
        res = requests.get(url, headers=headers, timeout=10)
        data = res.json() if res.status_code == 200 else []
        for entry in data:
            found_subdomains.update(entry['name_value'].split('\n'))
    except Exception as e:
        log(Fore.RED + f"[-] Subdomain Finder Failed: {e}")
        return

    table = Table(title="Subdomains & Takeover Status")
    table.add_column("Subdomain", style="cyan")
    table.add_column("Takeover", style="red")

    for sub in sorted(found_subdomains):
        sub = sub.strip()
        if not sub:
            continue
        status = "✅ Safe"
        try:
            r = requests.get(f"https://{sub}", headers=headers, timeout=5, verify=False)
        except:
            try:
                r = requests.get(f"http://{sub}", headers=headers, timeout=5)
            except:
                status = "❌ Unreachable"
                table.add_row(sub, status)
                report.append(f"{sub} - {status}")
                continue

        for service, fingerprint in fingerprints.items():
            if fingerprint.lower() in r.text.lower():
                status = f"⚠️ {service}"
                break

        table.add_row(sub, status)
        report.append(f"{sub} - {status}")
    console.print(table)

def port_scan(target):
    log(Fore.YELLOW + "\n[+] Port Scanner (Common Ports)")
    ports = [21,22,23,25,53,80,110,139,143,443,445,3306,3389,8080]
    open_ports = []

    def scan(port):
        try:
            with socket.socket() as s:
                s.settimeout(1)
                s.connect((target, port))
                open_ports.append(str(port))
                report.append(f"Port Open: {port}")
        except:
            pass

    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}")) as progress:
        task = progress.add_task("[cyan]Scanning ports...", total=None)
        threads = [threading.Thread(target=scan, args=(p,)) for p in ports]
        for t in threads: t.start()
        for t in threads: t.join()
        progress.update(task, completed=100)
        progress.stop()

    table = Table(title="Open Ports")
    table.add_column("Port", style="green")
    for port in open_ports:
        table.add_row(port)
    console.print(table)

def headers_grab(url):
    log(Fore.YELLOW + "\n[+] HTTP Headers")
    try:
        res = requests.get(url, timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
        table = Table(title="HTTP Headers")
        table.add_column("Header", style="yellow")
        table.add_column("Value", style="white")
        for k, v in res.headers.items():
            table.add_row(str(k), str(v))
            report.append(f"{k}: {v}")
        if "cloudflare" in res.headers.get("Server", "").lower():
            table.add_row("WAF", "⚠️ Cloudflare Detected")
        console.print(table)
    except Exception as e:
        log(Fore.RED + f"[-] Header Grab Failed: {e}")

def whois_lookup(target):
    log(Fore.YELLOW + "\n[+] Whois Lookup")
    try:
        w = whois.whois(target)
        table = Table(title="Whois Info")
        table.add_column("Field", style="magenta")
        table.add_column("Value", style="white")
        for k in ['domain_name', 'registrar', 'creation_date', 'expiration_date', 'emails']:
            table.add_row(k, str(w.get(k)))
            report.append(f"{k}: {w.get(k)}")
        console.print(table)
    except Exception as e:
        log(Fore.RED + f"[-] Whois Lookup Failed: {e}")

def save_report(target):
    try:
        now = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        fname = f"DHTRecon_{target.replace('.', '_')}_{now}.txt"
        with open(fname, "w", encoding="utf-8", errors="ignore") as f:
            for line in report:
                f.write(line + "\n")
        console.print(Fore.CYAN + f"\n[✔] Report saved as {fname}")
    except Exception as e:
        print(Fore.RED + f"[-] Failed to save report: {e}")

def main():
    intro()
    try:
        if len(sys.argv) > 1:
            target = sys.argv[1]
        else:
            target = input(Fore.CYAN + "[?] Enter domain or IP: ").strip()
        if not target:
            print(Fore.RED + "[-] No input.")
            sys.exit()
        ip = ip_lookup(target)
        if not is_ip(target):
            dns_lookup(target)
            subdomain_finder(target)
        port_scan(ip)
        headers_grab("http://" + target)
        whois_lookup(target)
        save_report(target)
        console.print(Panel("[bold green]✔ Recon Completed Successfully.[/bold green]"))
    except KeyboardInterrupt:
        console.print(Fore.RED + "\n[!] Interrupted by user.")
        os._exit(0)

if __name__ == "__main__":
    main()