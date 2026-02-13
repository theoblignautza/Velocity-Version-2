from __future__ import annotations

import ipaddress
import socket
from concurrent.futures import ThreadPoolExecutor


def validate_subnet(value: str) -> ipaddress.IPv4Network:
    try:
        network = ipaddress.ip_network(value, strict=False)
    except ValueError as exc:
        raise ValueError("Invalid subnet format") from exc
    if not isinstance(network, ipaddress.IPv4Network):
        raise ValueError("Only IPv4 subnets are supported")
    if network.num_addresses > 4096:
        raise ValueError("Subnet too large; max 4096 addresses")
    return network


def _is_open(host: str, port: int, timeout: float = 0.35) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(timeout)
        return sock.connect_ex((host, port)) == 0


def scan_network(subnet: str) -> list[dict[str, object]]:
    network = validate_subnet(subnet)
    hosts = [str(ip) for ip in network.hosts()]

    def scan_host(host: str) -> dict[str, object] | None:
        ssh_open = _is_open(host, 22)
        telnet_open = _is_open(host, 23)
        if not ssh_open and not telnet_open:
            return None
        return {
            "ip": host,
            "open_ports": [port for port, ok in ((22, ssh_open), (23, telnet_open)) if ok],
            "protocols": [name for name, ok in (("ssh", ssh_open), ("telnet", telnet_open)) if ok],
        }

    with ThreadPoolExecutor(max_workers=128) as executor:
        rows = list(executor.map(scan_host, hosts))
    return [row for row in rows if row is not None]
