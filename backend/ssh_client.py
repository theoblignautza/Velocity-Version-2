from __future__ import annotations

from netmiko import ConnectHandler


def _effective_device_type(device_type: str, protocol: str) -> str:
    if protocol == "telnet" and not device_type.endswith("_telnet"):
        return f"{device_type}_telnet"
    return device_type


def fetch_running_config(
    *, device_ip: str, username: str, password: str, device_type: str, protocol: str = "ssh"
) -> str:
    try:
        connection = ConnectHandler(
            device_type=_effective_device_type(device_type, protocol),
            host=device_ip,
            username=username,
            password=password,
        )
    except Exception as exc:
        raise RuntimeError("Unable to connect to device") from exc

    try:
        output = connection.send_command("show running-config")
    except Exception as exc:
        raise RuntimeError("Unable to fetch running config") from exc
    finally:
        connection.disconnect()

    return output


def restore_running_config(
    *,
    device_ip: str,
    username: str,
    password: str,
    device_type: str,
    config_text: str,
    protocol: str = "ssh",
) -> None:
    try:
        connection = ConnectHandler(
            device_type=_effective_device_type(device_type, protocol),
            host=device_ip,
            username=username,
            password=password,
        )
    except Exception as exc:
        raise RuntimeError("Unable to connect to device") from exc

    try:
        lines = [line for line in config_text.splitlines() if line.strip() and not line.strip().startswith("!")]
        if not lines:
            raise RuntimeError("Backup file has no configuration lines to restore")
        connection.send_config_set(lines)
        connection.save_config()
    except Exception as exc:
        if isinstance(exc, RuntimeError):
            raise
        raise RuntimeError("Unable to restore running config") from exc
    finally:
        connection.disconnect()
