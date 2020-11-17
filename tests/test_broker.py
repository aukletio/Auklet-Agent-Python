import os
import ast
import json
import unittest

from mock import patch
from tests import data_factory

from auklet.monitoring.processing import Client
from auklet.broker import MQTTClient


def recreate_files():
    os.system("touch .auklet/version")
    os.system("touch .auklet/communication")
    os.system("touch .auklet/usage")
    os.system("touch .auklet/limits")


class TestMQTTBroker(unittest.TestCase):
    data = ast.literal_eval(str(data_factory.MonitoringDataFactory()))
    config = ast.literal_eval(str(data_factory.ConfigFactory()))

    def setUp(self):
        with patch("auklet.monitoring.processing.Client._register_device",
                   new=self.__register_device):
            self.client = Client(
                api_key="", app_id="",
                base_url="https://api-staging.auklet.io/",
                auklet_dir=".auklet"
            )
            with patch('auklet.broker.MQTTClient._get_conf') as _get_conf:
                with patch("os.path.isfile") as is_file_mock:
                    is_file_mock.return_value = False
                    _get_conf.side_effect = self.get_conf
                    self.broker = MQTTClient(self.client)

    def test_write_conf(self):
        self.broker._write_conf(self.config)
        self.assertGreater(os.path.getsize(self.client.com_config_filename), 0)
        open(self.client.com_config_filename, "w").close()

    def test_get_certs(self):
        pubnub_cert_filename = ".auklet/pubnub.json"
        with open("key.pem.zip", "wb"):
            pass
        class urlopen:
            @staticmethod
            def read():
                with open("key.pem.zip", "rb") as file:
                    return file.read()
        if os.path.exists(pubnub_cert_filename):
            os.remove(pubnub_cert_filename)
        self.assertFalse(self.broker._get_certs())
        with patch('auklet.broker.urlopen') as _urlopen:
            _urlopen.return_value = urlopen
            with open(pubnub_cert_filename, "wb") as f:
                f.write(
                    json.dumps(
                        {"publish_key": "", "subscribe_key": ""},
                        ensure_ascii=False).encode("gbk"))
            self.assertTrue(self.broker._get_certs())

    def test_read_from_conf(self):
        self.broker._read_from_conf({"brokers": "mqtt",
                                     "port": "8333",
                                     "prof_topic": "",
                                     "event_topic": "",
                                     "log_topic": ""})
        self.assertIsNotNone(self.broker.brokers)
        self.assertIsNotNone(self.broker.port)
        self.assertIsNotNone(self.broker.producer_types)

    def test_on_disconnect(self):
        def debug(msg):
            global debug_msg
            debug_msg = msg

        with patch('logging.debug') as _debug:
            _debug.side_effect = debug
            self.broker.on_disconnect(None, "", 1)
            self.assertIsNotNone(debug_msg)

    def test_create_producer(self):
        global create_producer_pass
        create_producer_pass = False

        with patch('auklet.broker.MQTTClient._get_certs') as get_certs:
            with patch('pubnub.pubnub.PubNub') as _Client:
                _Client.side_effect = self.MockClient
                get_certs.return_value = True
                os.system("touch .auklet/pubnub.json")
                self.broker.create_producer()

    def test_produce(self):
        with patch('pubnub.pubnub.PubNub.publish') as _publish:
            with patch('auklet.broker.MQTTClient._get_certs') as get_certs:
                with patch('pubnub.pubnub.PubNub') as _PubNub_Client:
                    _PubNub_Client.side_effect = self.MockClient
                    get_certs.return_value = True
                    _publish.side_effect = self.publish
                    self.broker.create_producer()
                    self.broker.produce(str(self.data), "event")
                    self.assertIsNotNone(test_produce_payload)

    def test_get_conf(self):
        with patch('auklet.broker.open_auklet_url', new=self._open_auklet_url):
            with patch('auklet.broker.json.loads', new=self._loads):
                self.broker._get_conf()

    class MockClient:
        def __init__(self, config):
            global create_producer_pass
            create_producer_pass = True

        def tls_set(self, ca_certs):
            pass

        def tls_set_context(self, context):
            pass

        def connect_async(self, broker, port):
            pass

        def enable_logger(self):
            pass

        def username_pw_set(self, username, password):
            pass

        def publish(self):
            global test_produce_payload
            test_produce_payload = True

    @staticmethod
    def publish():
        global test_produce_payload
        test_produce_payload = True
        class Channel:
            def channel(self, channel):
                class Message:
                    def message(self, message):
                        class Sync:
                            def sync(self):
                                pass
                        return Sync()
                return Message()
        return Channel()

    @staticmethod
    def get_conf():
        return True

    @staticmethod
    def _open_auklet_url(url, apikey):
        class MyObject:
            def read(self):
                return b"test_str"
        return MyObject()

    @staticmethod
    def _loads(data):
        return {
            "brokers": "mqtt",
            "port": "8883"
        }

    @staticmethod
    def __register_device(self):
        return True


if __name__ == '__main__':
    unittest.main()
