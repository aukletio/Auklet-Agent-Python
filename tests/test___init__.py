import unittest
from mock import patch

from auklet.monitoring import Monitoring
from auklet.errors import AukletConfigurationError


class TestMonitoring(unittest.TestCase):
    def setUp(self):
        with patch('auklet.broker.MQTTClient._get_conf') as _get_conf:
            with patch("auklet.monitoring.processing.Client._register_device",
                       new=self.__register_device):
                with patch("os.path.isfile") as is_file_mock:
                    is_file_mock.return_value = False
                    _get_conf.side_effect = self.get_conf
                    self.monitoring = Monitoring(
                        api_key="",
                        app_id="",
                        release="",
                        base_url="https://api-staging.io",
                        monitoring=True)
                    self.monitoring.monitor = True

    def test_start(self):
        self.assertIsNone(self.monitoring.start())
        self.monitoring.stop()

    def test_initialize_without_release(self):
        self.assertRaises(
            AukletConfigurationError, Monitoring,
            api_key="", app_id="", base_url="https://api.auklet.io/")

    def test_stop(self):
        self.monitoring.start()
        self.monitoring.stop()
        self.assertTrue(self.monitoring.stopping)

    def test_sample(self):
        class CoCode:
            co_code = None
            co_firstlineno = None
            co_name = None
        class FBack:
            f_back = None
            f_code = CoCode()
        class Frame:
            f_back = FBack()
            f_code = CoCode()

        def update_hash(self, stack):
            global test_sample_stack  # used to tell if stack was created
            test_sample_stack = stack

        with patch('auklet.stats.MonitoringTree.update_hash', new=update_hash):
            self.monitoring.sample(None, current_frame=Frame())
            self.assertIsNotNone(test_sample_stack)
            self.monitoring.sample(None, current_frame=Frame())
            self.assertTrue(test_sample_stack)

    def test_process_periodic(self):
        def produce(self, data):
            global test_process_periodic_produce_data
            test_process_periodic_produce_data = True

        def check_date(self):
            global test_process_periodic_check_date
            test_process_periodic_check_date = True

        with patch('auklet.broker.MQTTClient.produce', new=produce):
            with patch('auklet.monitoring.processing.Client.check_date',
                       new=check_date):
                self.monitoring.process_periodic()
                self.assertTrue(test_process_periodic_produce_data)
                self.assertTrue(test_process_periodic_check_date)
                self.assertEqual(60000, self.monitoring.emission_rate)

    def test_handle_exc(self):
        with patch('auklet.broker.MQTTClient.produce') as _produce:
            with patch(
                    'auklet.monitoring.processing.'
                    'Client.build_msgpack_event_data') \
                    as _build_msgpack_event_data:
                with patch('sys.__excepthook__') as ___excepthook__:
                    ___excepthook__.side_effect = self.__excepthook__
                    _build_msgpack_event_data.return_value = True
                    _produce.side_effect = self.produce
                    self.monitoring.handle_exc(None, None, None)
                    self.assertTrue(test_handle_exc___excepthook___)

    def test_log(self):
        with patch('auklet.broker.MQTTClient.produce') as _produce:
            _produce.side_effect = self.produce
            self.monitoring.log("", "")
            self.assertIsNotNone(test_log_data)

    def test_send(self):
        with patch('auklet.broker.MQTTClient.produce') as _produce:
            _produce.side_effect = self.produce
            self.monitoring.send({"latitude": 0.0, "longitude": 0.0},
                                 data_type="location")

    def build_msgpack_tree(self, app_id):
        print(app_id)

    def __register_device(self):
        return True

    @staticmethod
    def produce(data, data_type):
        global test_log_data
        test_log_data = data

    @staticmethod
    def send_produce(data, data_type):
        global test_send_data
        test_send_data = data

    @staticmethod
    def get_conf():
        return True

    @staticmethod
    def __excepthook__(type, value, traceback):
        global test_handle_exc___excepthook___
        test_handle_exc___excepthook___ = True


if __name__ == '__main__':
    unittest.main()
