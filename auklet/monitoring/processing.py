import json
import msgpack
import traceback

from time import time
from uuid import uuid4
from datetime import datetime
from auklet.stats import Event, SystemMetrics
from auklet.utils import create_file, \
    get_abs_path, get_device_ip, open_auklet_url, build_url, \
    get_agent_version, post_auklet_url, u

try:
    # For Python 3.0 and later
    from urllib.error import HTTPError, URLError
    from urllib.request import Request, urlopen
except ImportError:
    # Fall back to Python 2's urllib2
    from urllib2 import urlopen, Request, HTTPError, URLError


MB_TO_B = 1e6
S_TO_MS = 1000


class Client(object):
    producer_types = None
    brokers = None
    commit_hash = None
    mac_hash = None
    offline_filename = "{}/local.txt"
    limits_filename = "{}/limits"
    usage_filename = "{}/usage"
    com_config_filename = "{}/communication"
    identification_filename = "{}/identification"
    abs_path = None

    org_id = None
    client_id = None
    broker_username = None
    broker_password = None

    reset_data = False
    data_day = 1
    data_limit = None
    data_current = 0
    offline_limit = None
    offline_current = 0

    system_metrics = None

    def __init__(self, api_key=None, app_id=None, release=None,
                 base_url="https://api.auklet.io/", mac_hash=None,
                 version="", auklet_dir=""):
        self.apikey = api_key
        self.app_id = app_id
        self.base_url = base_url
        self.send_enabled = True
        self.producer = None
        self.mac_hash = mac_hash
        self.version = version
        self.auklet_dir = auklet_dir
        self._set_filenames()
        self._load_limits()
        create_file(self.offline_filename)
        create_file(self.limits_filename)
        create_file(self.usage_filename)
        create_file(self.com_config_filename)
        create_file(self.identification_filename)
        self.commit_hash = release
        self.abs_path = get_abs_path(".auklet/version")
        self.system_metrics = SystemMetrics()
        self._register_device()

    def _set_filenames(self):
        self.offline_filename = self.offline_filename.format(self.auklet_dir)
        self.limits_filename = self.limits_filename.format(self.auklet_dir)
        self.usage_filename = self.usage_filename.format(self.auklet_dir)
        self.com_config_filename = self.com_config_filename.format(
            self.auklet_dir)
        self.identification_filename = self.identification_filename.format(
            self.auklet_dir)

    def _register_device(self):
        try:
            read_id = json.loads(
                open(self.identification_filename, "r").read())
            if not read_id:
                raise IOError
            res, created = self.check_device(read_id['id'])
            if created:
                read_id = res
        except (IOError, ValueError):
            read_id = self.create_device()
        self.broker_password = read_id['client_password']
        self.broker_username = read_id['id']
        self.client_id = read_id['client_id']
        self.org_id = read_id['organization']
        self._write_identification({"id": self.broker_username,
                                    "client_password": self.broker_password,
                                    "organization": self.org_id,
                                    "client_id": self.client_id})
        return True

    def check_device(self, device_id):
        try:
            opened = open_auklet_url(
                build_url(
                    self.base_url,
                    "private/devices/{}/".format(device_id)
                ),
                self.apikey
            )
            res = json.loads(u(opened.read()))
            created = False
        except HTTPError:
            res = self.create_device()
            created = True
        return res, created

    def create_device(self):
        return post_auklet_url(
            build_url(
                self.base_url,
                "private/devices/"
            ),
            self.apikey,
            {"mac_address_hash": self.mac_hash, "application": self.app_id}
        )

    def _write_identification(self, data):
        with open(self.identification_filename, "w") as id_file:
            id_file.write(json.dumps(data))

    def _get_config(self):
        res = open_auklet_url(
            build_url(
                self.base_url,
                "private/devices/{}/app_config/".format(self.app_id)),
            self.apikey)
        if res is not None:
            return json.loads(u(res.read()))['config']

    def _load_limits(self):
        try:
            with open(self.limits_filename, "r") as limits:
                limits_str = limits.read()
                if limits_str:
                    data = json.loads(limits_str)
                    self.data_day = data['data']['normalized_cell_plan_date']
                    temp_limit = data['data']['cellular_data_limit']
                    if temp_limit is not None:
                        self.data_limit = data['data'][
                                              'cellular_data_limit'] * MB_TO_B
                    else:
                        self.data_limit = temp_limit
                    temp_offline = data['storage']['storage_limit']
                    if temp_offline is not None:
                        self.offline_limit = data['storage'][
                                                 'storage_limit'] * MB_TO_B
                    else:
                        self.offline_limit = data['storage']['storage_limit']
        except IOError:
            return

    def _build_usage_json(self):
        return {"data": self.data_current, "offline": self.offline_current}

    def _update_usage_file(self):
        try:
            with open(self.usage_filename, 'w') as usage:
                usage.write(json.dumps(self._build_usage_json()))
        except IOError:
            return False

    def check_data_limit(self, data, current_use, offline=False):
        if self.offline_limit is None and offline:
            return True
        if self.data_limit is None and not offline:
            return True
        data_size = len(data)
        temp_current = current_use + data_size
        if temp_current >= self.data_limit:
            return False
        if offline:
            self.offline_current = temp_current
        else:
            self.data_current = temp_current
        self._update_usage_file()
        return True

    def check_date(self):
        if datetime.today().day == self.data_day:
            if self.reset_data:
                self.data_current = 0
                self.reset_data = False
        else:
            self.reset_data = True

    def update_limits(self):
        config = self._get_config()
        if config is None:
            return 60000
        with open(self.limits_filename, 'w+') as limits:
            limits.truncate()
            limits.write(json.dumps(config))
        new_day = config['data']['normalized_cell_plan_date']
        temp_limit = config['data']['cellular_data_limit']
        if temp_limit is not None:
            new_data = config['data']['cellular_data_limit'] * MB_TO_B
        else:
            new_data = temp_limit
        temp_offline = config['storage']['storage_limit']
        if temp_offline is not None:
            new_offline = config['storage']['storage_limit'] * MB_TO_B
        else:
            new_offline = config['storage']['storage_limit']
        if self.data_day != new_day:
            self.data_day = new_day
            self.data_current = 0
        if self.data_limit != new_data:
            self.data_limit = new_data
        if self.offline_limit != new_offline:
            self.offline_limit = new_offline
        # return emission period in ms
        return config['emission_period'] * S_TO_MS

    def build_event_data(self, type, tb, tree):
        event = Event(type, tb, tree, self.abs_path)
        event_dict = dict(event)
        event_dict['application'] = self.app_id
        event_dict['publicIP'] = get_device_ip()
        event_dict['id'] = str(uuid4())
        event_dict['timestamp'] = int(round(time() * 1000))
        event_dict['systemMetrics'] = dict(self.system_metrics)
        event_dict['macAddressHash'] = self.mac_hash
        event_dict['release'] = self.commit_hash
        event_dict['agentVersion'] = get_agent_version()
        event_dict['device'] = self.broker_username
        event_dict['absPath'] = self.abs_path
        event_dict['version'] = self.version
        return event_dict

    def build_log_data(self, msg, data_type, level):
        log_dict = {
            "message": msg,
            "type": data_type,
            "level": level,
            "application": self.app_id,
            "publicIP": get_device_ip(),
            "id": str(uuid4()),
            "timestamp": int(round(time() * 1000)),
            "systemMetrics": dict(self.system_metrics),
            "macAddressHash": self.mac_hash,
            "release": self.commit_hash,
            "agentVersion": get_agent_version(),
            "device": self.broker_username,
            "version": self.version
        }
        return log_dict

    def build_send_data(self, msg, data_type):
        send_dict = {
            "payload": msg,
            "application": self.app_id,
            "publicIP": get_device_ip(),
            "id": str(uuid4()),
            "timestamp": int(round(time() * 1000)),
            "macAddressHash": self.mac_hash,
            "release": self.commit_hash,
            "agentVersion": get_agent_version(),
            "device": self.broker_username,
            "version": self.version,
            "type": data_type
        }
        return send_dict

    def build_msgpack_event_data(self, type, tb, tree):
        event_data = self.build_event_data(type, tb, tree)
        return msgpack.packb(event_data, use_bin_type=False)

    def build_msgpack_log_data(self, msg, data_type, level):
        log_data = self.build_log_data(msg, data_type, level)
        return msgpack.packb(log_data, use_bin_type=False)

    def build_msgpack_send_data(self, msg, data_type):
        send_data = self.build_send_data(msg, data_type)
        return msgpack.packb(send_data, use_bin_type=False)
