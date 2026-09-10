import socket
import threading
from dnslib import DNSRecord, RR, A, AAAA, QTYPE
from dnslib.server import DNSServer, BaseResolver

LISTEN_PORT = 53
FORWARD_DNS = "9.9.9.9"
FORWARD_PORT = 53

ROBLOX_CDN_DOMAINS = [
    "tr.rbxcdn.com",
    "rbxcdn.com",
    "clientsettingscdn.roblox.com",
    "thumbnails.roblox.com",
    "images.rbxcdn.com",
]

ROBLOX_CDN_IP = "18.65.39.105"


def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def forward_query(qname, qtype):
    try:
        query = DNSRecord.question(qname, qtype)
        data = query.send(FORWARD_DNS, FORWARD_PORT, timeout=3)
        return DNSRecord.parse(data)
    except Exception:
        return None


class RobloxResolver(BaseResolver):
    def resolve(self, request, handler):
        reply = request.reply()
        qname = str(request.q.qname).rstrip(".")
        qtype = QTYPE[request.q.qtype]

        if any(qname.endswith(d) for d in ROBLOX_CDN_DOMAINS):
            if qtype == "A":
                reply.add_answer(
                    RR(request.q.qname, rdata=A(ROBLOX_CDN_IP), ttl=60)
                )
            return reply

        upstream = forward_query(qname, qtype)
        if upstream:
            for rr in upstream.rr:
                reply.add_answer(rr)
            for rr in upstream.auth:
                reply.add_auth(rr)

        return reply


server = None
server_thread = None


# ===== Инструкции под каждую ОС =====
def show_windows(primary, secondary):
    print()
    print("  ── WINDOWS ──")
    print("  Параметры -> Сеть и Интернет -> Ethernet/Wi-Fi")
    print("  -> Изменить параметры адаптера")
    print("  -> ПКМ по адаптеру -> Свойства -> IPv4 -> Свойства")
    print("  -> 'Использовать следующие адреса DNS-серверов'")
    print(f"     Предпочитаемый DNS : {primary}")
    print(f"     Альтернативный DNS : {secondary}")
    print("  -> ОК. Затем в CMD (от админа):")
    print("     ipconfig /flushdns")


def show_linux(primary, secondary):
    print()
    print("  ── LINUX ──")
    print("  Через nmcli (NetworkManager):")
    print(f"     sudo nmcli con mod '<имя>' ipv4.dns \"{primary} {secondary}\"")
    print("     sudo nmcli con up '<имя>'")
    print()
    print("  Или вручную /etc/resolv.conf:")
    print(f"     nameserver {primary}")
    print(f"     nameserver {secondary}")
    print()
    print("  Сбросить кэш:")
    print("     sudo systemd-resolve --flush-caches   (или resolvectl flush-caches)")


def show_macos(primary, secondary):
    print()
    print("  ── MACOS ──")
    print("  Системные настройки -> Сеть -> Wi-Fi/Ethernet")
    print("  -> Подробнее -> DNS -> '+'")
    print(f"     DNS-сервер 1 : {primary}")
    print(f"     DNS-сервер 2 : {secondary}")
    print("  -> ОК")
    print()
    print("  Сбросить кэш в Терминале:")
    print("     sudo dscacheutil -flushcache; sudo killall -HUP mDNSResponder")


OS_CHOICES = {
    "1": ("Windows", show_windows),
    "2": ("Linux",   show_linux),
    "3": ("macOS",   show_macos),
}


def pick_os():
    print()
    print("  Выбери свою ОС:")
    print("    1 - Windows")
    print("    2 - Linux")
    print("    3 - macOS")
    choice = input("  ОС: ").strip()
    return OS_CHOICES.get(choice)


def start_dns():
    global server, server_thread
    if server_thread and server_thread.is_alive():
        print("[!] DNS уже включён")
        return

    os_pick = pick_os()
    if not os_pick:
        print("[!] Нет такой ОС")
        return
    os_name, os_func = os_pick

    try:
        server = DNSServer(
            RobloxResolver(), port=LISTEN_PORT, address="0.0.0.0"
        )
    except PermissionError:
        print("[!] Нет прав на порт 53. Запусти от админа/root.")
        return
    except OSError as e:
        print(f"[!] Порт 53 занят: {e}")
        print("    Windows: net stop dnscache")
        print("    Linux:   sudo systemctl stop systemd-resolved")
        return

    server_thread = threading.Thread(target=server.start, daemon=True)
    server_thread.start()

    local_ip = get_local_ip()
    primary = local_ip
    secondary = FORWARD_DNS

    print()
    print("=" * 55)
    print("  DNS ДЛЯ КАРТИНОК ROBLOX ВКЛЮЧЁН ✅")
    print("=" * 55)
    print(f"  ОС             : {os_name}")
    print(f"  IP DNS-сервера : {primary}")
    print(f"  Порт           : {LISTEN_PORT}")
    print(f"  Форвард        : {secondary}")

    os_func(primary, secondary)

    print()
    print("  После настройки перезапусти Roblox 🖼️")
    print("=" * 55)


def stop_dns():
    global server
    if server:
        try:
            server.stop()
        except Exception:
            pass
        server = None
        print("[+] DNS выключен")


def menu():
    print("=" * 55)
    print("     ФИКС ЛАГОВ / СЕРЫХ КАРТИНОК В ROBLOX")
    print("=" * 55)
    while True:
        print("\n1 - Выход")
        print("2 - Включить DNS")
        choice = input("Выбор: ").strip()
        if choice == "1":
            stop_dns()
            print("Пока, братан 👋")
            break
        elif choice == "2":
            start_dns()
        else:
            print("[!] Нет такого пункта")


if __name__ == "__main__":
    menu()