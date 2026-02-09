from __future__ import annotations

from netmiko import ConnectHandler


def fetch_running_config(
    *, device_ip: str, username: str, password: str, device_type: str
) -> str:
    try:
        connection = ConnectHandler(
            device_type=device_type,
            host=device_ip,
            username=username,
            password=password,
        )
    except Exception as exc:  # Netmiko raises multiple custom exceptions
        raise RuntimeError("Unable to connect to device") from exc

    try:
        output = connection.send_command("show running-config")
    except Exception as exc:
        raise RuntimeError("Unable to fetch running config") from exc
    finally:
        connection.disconnect()

    return output
