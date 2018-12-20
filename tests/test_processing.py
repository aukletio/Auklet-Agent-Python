import os
import ast
import json
import unittest

from mock import patch
from datetime import datetime

from tests import data_factory

from auklet.utils import b
from auklet.stats import MonitoringTree
from auklet.monitoring.processing import Client
from auklet.monitoring.utils import update_data_limits, load_limits

try:
    # For Python 3.0 and later
    from urllib.error import HTTPError, URLError
    from urllib.request import Request, urlopen
except ImportError:
    # Fall back to Python 2's urllib2
    from urllib2 import urlopen, Request, HTTPError, URLError


class TestClient(unittest.TestCase):
    data = ast.literal_eval(str(data_factory.MonitoringDataFactory()))

    def setUp(self):
        with patch("auklet.monitoring.processing.Client._register_device",
                   new=self.__register_device):
            self.broker_username = "test-username"
            self.broker_password = "test-password"
            self.client = Client(
                api_key="", app_id="",
                base_url="https://api-staging.auklet.io/",
                auklet_dir=".auklet"
            )
            self.monitoring_tree = MonitoringTree()

    def test_get_config(self):
        class MockRequest:
            def __init__(self, *args, **kwargs):
                pass

            def get_type(self):
                pass

        class res:
            def read(self):
                return str(json.dumps({"config": ""})).encode()

        with patch('auklet.utils.urlopen') as _urlopen:
            with patch('auklet.utils.Request') as _Request:
                    _Request.side_effect = MockRequest
                    _urlopen.return_value = res()
                    self.assertIsNotNone(self.client._get_config())

    def test_register_device(self):
        with patch("json.loads", return_value=False):
            with patch("auklet.monitoring.processing.Client."
                       "create_device") as create_mock:
                create_mock.return_value = {
                    "client_password": "test-pass",
                    "client_id": "12345",
                    "id": "12345",
                    "organization": "12345"
                }
                self.assertTrue(self.client._register_device())

        with patch("json.loads") as loads_mock:
                with patch("auklet.monitoring.processing.Client."
                           "check_device") as check_mock:
                    loads_mock.return_value = {"id": "12345"}
                    check_mock.return_value = ({
                        "client_password": "test-pass",
                        "client_id": "12345",
                        "id": "12345",
                        "organization": "12345"
                    }, True)
                    self.assertTrue(self.client._register_device())

    def test_check_device(self):
        with patch("auklet.monitoring.processing.open_auklet_url",
                   return_value=self.MockResult()):
            res = self.client.check_device("123")
            self.assertFalse(res[1])
        with patch("auklet.monitoring.processing.open_auklet_url",
                   side_effect=HTTPError("url", 404, "failed post",
                                         {"test": "header"}, None)):
            res = self.client.check_device("123")
            self.assertTrue(res[1])

    def test_create_device(self):
        with patch("auklet.monitoring.processing.post_auklet_url",
                   return_value=self.MockResult()):
            res = self.client.create_device()
            self.assertEqual(res.read(), b(json.dumps({"test": "object"})))

    def test_load_limits(self):
        default_data = data_factory.LimitsGenerator()
        self.write_load_limits_test(default_data)
        self.build_load_limits_test(1, self.client.data_day)

        self.assertEqual(None, self.client.data_limit)
        self.assertEqual(None, self.client.offline_limit)

        data = data_factory.LimitsGenerator(cellular_data_limit=10)
        self.write_load_limits_test(data)
        load_limits(self.client)
        self.build_load_limits_test(10000000.0, self.client.data_limit)

        data = data_factory.LimitsGenerator(
            cellular_data_limit="null", storage_limit=10)
        self.write_load_limits_test(data)
        load_limits(self.client)
        self.build_load_limits_test(10000000.0, self.client.offline_limit)

        with open(self.client.limits_filename, "w") as limits:
            limits.write(str(default_data))

        self.base_patch_side_effect_with_none(
            'auklet.monitoring.processing.open',
            IOError, (load_limits, self.client))

    def test_build_usage_json(self):
        data = self.client._build_usage_json()
        for value in data.values():
            self.assertNotEqual(value, None)

    def test_update_usage_file(self):
        os.system("rm -R .auklet")
        self.assertFalse(self.client._update_usage_file())
        os.system("mkdir .auklet")
        os.system("touch %s" % self.client.offline_filename)
        os.system("touch .auklet/version")

    def test_check_data_limit(self):
        self.client.offline_limit = None
        self.assertTrue(
            self.client.check_data_limit(
                data=self.data, current_use=0, offline=True))

        self.client.data_limit = None
        self.assertTrue(
            self.client.check_data_limit(data=self.data, current_use=0))

        self.client.offline_limit = self.client.data_limit = 1
        self.assertFalse(
            self.client.check_data_limit(data=self.data, current_use=0))

        self.client.data_limit = 1000
        self.client.check_data_limit(
            data=self.data, current_use=0, offline=True)
        self.assertNotEqual(self.client.offline_current, 0)

        self.client.check_data_limit(
            data=self.data, current_use=0)
        self.assertNotEqual(self.client.data_current, 0)

        self.assertTrue(
            self.client.check_data_limit(data=self.data, current_use=0))

    def test_check_date(self):
        self.client.data_day = datetime.today().day
        self.client.data_current = 1000
        self.client.reset_data = True
        self.client.check_date()
        self.assertEqual(self.client.data_current, 0)
        self.assertEqual(self.client.reset_data, False)
        self.client.data_day = datetime.today().day+1
        self.client.check_date()
        self.assertTrue(self.client.reset_data)

    def test_update_limits(self):
        with patch(
                'auklet.monitoring.processing.Client._get_config',
                new=self._get_config):
            self.assertEqual(update_data_limits(self.client), 60000)
            self.none = False

            self.cellular_data_limit = 1000
            update_data_limits(self.client)
            self.assertEqual(self.client.data_limit, 1000000000.0)
            self.cellular_data_limit = None

            self.storage_limit = 1000
            update_data_limits(self.client)
            self.assertEqual(self.client.offline_limit, 1000000000.0)
            self.storage_limit = None

            self.cell_plan_date = 10
            update_data_limits(self.client)
            self.assertEqual(self.client.data_day, 10)
            self.cell_plan_date = 1

            self.assertEqual(update_data_limits(self.client), 60000)

    def test_build_msgpack_event_data(self):
        with patch("auklet.monitoring.utils.traceback.format_exc",
                   new=self.mock_format_exc):
            self.assertBuildEventData(self.client.build_msgpack_event_data)

    def test_build_msgpack_send_data(self):
        self.assertIsNotNone(
            self.client.build_msgpack_send_data(
                {"latitude": 0.0, "longitude": 0.0},
                data_type="location")
        )

    def test_build_msgpack_log_data(self):
        self.assertBuildLogData(
            self.client.build_msgpack_log_data(
                msg='msg', data_type='data_type', level='level'))

    def mock_format_exc(self):
        return ""

    @staticmethod
    def get_mock_event(exc_type=None, tb=None, tree=None, abs_path=None):
        return {"stackTrace":
                [{"functionName": "",
                  "filePath": "",
                  "lineNumber": 0,
                  "locals":
                    {"key": "value"}}]}

    def base_patch_side_effect_with_none(self, location, side_effect,
                                         func_info):
        func, arg = func_info
        with patch(location) as _base:
            _base.side_effect = side_effect
            if arg is not None:
                self.assertIsNone(func(arg))
            else:
                self.assertIsNone(func())

    def build_load_limits_test(self, expected, actual):
        self.assertEqual(expected, actual)

    def write_load_limits_test(self, data):
        filename = self.client.limits_filename
        with open(filename, "w") as limits:
            limits.write(str(data))

    def assertBuildEventData(self, function):
        def traceback():
            class Code:
                co_code = "file_name"
                co_name = ""

            class Frame:
                f_code = Code()
                f_lineno = 0
                f_locals = ""

            class Traceback:
                tb_lineno = 0
                tb_frame = Frame()
                tb_next = None
            return Traceback

        with patch(
                'auklet.monitoring.utils.Event', new=self.get_mock_event):
            self.monitoring_tree.cached_filenames["file_name"] = "file_name"
            self.assertNotEqual(
                function(
                    type=Exception,
                    tb=traceback(),
                    tree=self.monitoring_tree),
                None)

    def assertBuildLogData(self, function):
        self.assertNotEqual(function, None)

    none = True
    cellular_data_limit = None
    storage_limit = None
    cell_plan_date = 1

    def _get_config(self):
        if self.none:
            return None
        else:
            return {"storage":
                        {"storage_limit": self.storage_limit},
                    "emission_period": 60,
                    "features":
                        {"performance_metrics": True,
                         "user_metrics": False},
                    "data":
                        {"cellular_data_limit": self.cellular_data_limit,
                         "normalized_cell_plan_date": self.cell_plan_date}}

    @staticmethod
    def __register_device(self):
        return True

    class MockResult(object):
        def read(self):
            return b(json.dumps({"test": "object"}))


if __name__ == '__main__':
    unittest.main()
