from __future__ import annotations

import asyncio
from pathlib import Path

from backend import main
from backend.discovery import validate_subnet
from backend.log_stream import LogStream


def test_validate_subnet() -> None:
    network = validate_subnet('192.168.1.0/24')
    assert str(network.network_address) == '192.168.1.0'


def test_health_reports_external_binding() -> None:
    data = asyncio.run(main.health())
    assert data['host'] == '0.0.0.0'


def test_log_stream_publish_subscribe() -> None:
    stream = LogStream()

    async def runner() -> dict[str, str]:
        agen = stream.subscribe()
        task = asyncio.create_task(agen.__anext__())
        await asyncio.sleep(0)
        await stream.publish('Discovery started')
        item = await task
        await agen.aclose()
        return item

    payload = asyncio.run(runner())
    assert payload['message'] == 'Discovery started'


def test_backup_restore_and_file_access(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv('BACKUP_ROOT', str(tmp_path))

    monkeypatch.setattr(main, 'fetch_running_config', lambda **kwargs: 'hostname SW1\ninterface Gi0/1')
    captured: dict[str, str] = {}

    def fake_restore_running_config(**kwargs):
        captured['device_ip'] = kwargs['device_ip']
        captured['config_text'] = kwargs['config_text']

    monkeypatch.setattr(main, 'restore_running_config', fake_restore_running_config)

    backup_payload = main.BackupRequest(
        device_ip='10.1.1.1',
        username='admin',
        password='secret',
        device_type='cisco_ios',
        protocol='ssh',
    )
    backup_response = asyncio.run(main.backup_config(backup_payload))
    assert backup_response.device == '10.1.1.1'

    files = asyncio.run(main.backups_list())['files']
    assert files
    saved_path = files[0]['path']

    content = asyncio.run(main.backup_content(path=saved_path))
    assert 'hostname SW1' in content['content']

    restore_payload = main.RestoreRequest(
        device_ip='10.1.1.1',
        username='admin',
        password='secret',
        device_type='cisco_ios',
        protocol='ssh',
        backup_file=saved_path,
    )
    restore_response = asyncio.run(main.restore_config(restore_payload))
    assert restore_response['status'] == 'success'
    assert captured['device_ip'] == '10.1.1.1'


def test_discovery_endpoint(monkeypatch) -> None:
    monkeypatch.setattr(main, 'scan_network', lambda subnet: [{'ip': '192.168.1.8', 'open_ports': [22], 'protocols': ['ssh']}])
    response = asyncio.run(main.discover_switches(main.DiscoverRequest(subnet='192.168.1.0/24')))
    assert response['devices'][0]['ip'] == '192.168.1.8'
