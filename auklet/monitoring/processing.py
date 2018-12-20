import json
import msgpack

from datetime import datetime
from auklet.stats import SystemMetrics
from auklet.utils import (create_file, get_abs_path, open_auklet_url,
                          build_url, post_auklet_url, u)
from auklet.monitoring.utils import (load_limits, check_data_limits,
                                     build_send_data,
                                     build_log_data, build_event_data)

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
        load_limits(self)
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

    def _build_usage_json(self):
        return {"data": self.data_current, "offline": self.offline_current}

    def _update_usage_file(self):
        try:
            with open(self.usage_filename, 'w') as usage:
                usage.write(json.dumps(self._build_usage_json()))
        except IOError:
            return False

    def check_data_limit(self, data, current_use, offline=False):
        return check_data_limits(self, data, current_use, offline)

    def check_date(self):
        if datetime.today().day == self.data_day:
            if self.reset_data:
                self.data_current = 0
                self.reset_data = False
        else:
            self.reset_data = True

    def build_msgpack_event_data(self, type, tb, tree):
        return msgpack.packb(build_event_data(self, type, tb, tree),
                             use_bin_type=False)

    def build_msgpack_log_data(self, msg, data_type, level):
        return msgpack.packb(build_log_data(self, msg, data_type, level),
                             use_bin_type=False)

    def build_msgpack_send_data(self, msg, data_type):
        return msgpack.packb(build_send_data(self, msg, data_type),
                             use_bin_type=False)
