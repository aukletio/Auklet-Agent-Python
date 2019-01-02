import json
import traceback
from time import time
from uuid import uuid4

from auklet.stats import Event
from auklet.utils import get_agent_version, get_device_ip

MB_TO_B = 1e6
S_TO_MS = 1000


def load_limits(client):
    try:
        with open(client.limits_filename, "r") as limits:
            limits_str = limits.read()
            if limits_str:
                data = json.loads(limits_str)
                client.data_day = data['data']['normalized_cell_plan_date']
                client.data_limit = data['data']['cellular_data_limit']
                if client.data_limit is not None:
                    client.data_limit *= MB_TO_B

                client.offline_limit = data['storage']['storage_limit']
                if client.offline_limit is not None:
                    client.offline_limit *= MB_TO_B
    except IOError:
        return


def check_data_limits(client, data, current_use, offline=False):
    if client.offline_limit is None and offline:
        return True
    if client.data_limit is None and not offline:
        return True
    data_size = len(data)
    temp_current = current_use + data_size
    if temp_current >= client.data_limit:
        return False
    if offline:
        client.offline_current = temp_current
    else:
        client.data_current = temp_current
        client._update_usage_file()
    return True


def update_data_limits(client):
    config = client._get_config()
    if config is None:
        return 60000
    with open(client.limits_filename, 'w+') as limits:
        limits.truncate()
        limits.write(json.dumps(config))
    client.data_limit = config['data']['cellular_data_limit']
    if client.data_limit is not None:
        client.data_limit *= MB_TO_B

    client.offline_limit = config['storage']['storage_limit']
    if client.offline_limit is not None:
        client.offline_limit *= MB_TO_B

    if client.data_day != config['data']['normalized_cell_plan_date']:
        client.data_day = config['data']['normalized_cell_plan_date']
        client.data_current = 0
    # return emission period in ms
    return config['emission_period'] * S_TO_MS


def build_event_data(client, type, tb, tree):
    event = Event(type, tb, tree, client.abs_path)
    event_dict = dict(event)
    event_dict['application'] = client.app_id
    event_dict['publicIP'] = get_device_ip()
    event_dict['id'] = str(uuid4())
    event_dict['timestamp'] = int(round(time() * 1000))
    event_dict['systemMetrics'] = dict(client.system_metrics)
    event_dict['macAddressHash'] = client.mac_hash
    event_dict['release'] = client.commit_hash
    event_dict['agentVersion'] = get_agent_version()
    event_dict['device'] = client.broker_username
    event_dict['absPath'] = client.abs_path
    event_dict['version'] = client.version
    return event_dict


def build_log_data(client, msg, data_type, level):
    log_dict = {
        "message": msg,
        "type": data_type,
        "level": level,
        "application": client.app_id,
        "publicIP": get_device_ip(),
        "id": str(uuid4()),
        "timestamp": int(round(time() * 1000)),
        "systemMetrics": dict(client.system_metrics),
        "macAddressHash": client.mac_hash,
        "release": client.commit_hash,
        "agentVersion": get_agent_version(),
        "device": client.broker_username,
        "version": client.version
    }
    return log_dict


def build_send_data(client, msg, data_type):
    send_dict = {
        "payload": msg,
        "application": client.app_id,
        "publicIP": get_device_ip(),
        "id": str(uuid4()),
        "timestamp": int(round(time() * 1000)),
        "macAddressHash": client.mac_hash,
        "release": client.commit_hash,
        "agentVersion": get_agent_version(),
        "device": client.broker_username,
        "version": client.version,
        "type": data_type
    }
    return send_dict

