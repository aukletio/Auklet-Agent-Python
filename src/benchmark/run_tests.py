from __future__ import print_function

from mock import patch
import paho.mqtt.client as mqtt

from auklet.monitoring import Monitoring
from src.benchmark import base


def without_auklet():
    """
    Runs tests for a baseline number on how long the tests should take.
    """
    print("\n\nStarting benchmark tests without the Auklet Agent...")
    base.start(state="WithoutAuklet")


@patch('auklet.monitoring.update_data_limits')
@patch('auklet.broker.MQTTClient._get_certs')
def with_auklet_and_mqtt(get_certs_mock, update_limits_mock):
    """
    With a little help from mock, this test will push data that
    would normally go to the front end, to a MQTT container created locally.
    """
    print("\n\nStarting benchmark tests with the Auklet Agent and MQTT...")

    def _load_conf(self):
        self.brokers = "mqtt"
        self.port = 1883

    def create_producer(self):
        # Make non SSL producer for testing
        self.producer = mqtt.Client()
        self.producer.on_disconnect = self.on_disconnect
        self.producer.connect_async("mqtt", 1883)
        self.producer.loop_start()

    def _get_conf(self):
        return True

    def register_device(self):
        return True

    update_limits_mock.return_value = 10000
    get_certs_mock.return_value = True

    conf_patcher = patch('auklet.broker.MQTTClient._read_from_conf',
                         new=_load_conf)
    producer_patcher = patch('auklet.broker.MQTTClient.create_producer',
                             new=create_producer)
    get_conf_patcher = patch('auklet.broker.MQTTClient._get_conf',
                             new=_get_conf)
    register_device_patcher = patch(
        'auklet.monitoring.processing.Client._register_device',
        new=register_device)
    conf_patcher.start()
    producer_patcher.start()
    get_conf_patcher.start()
    register_device_patcher.start()

    auklet_monitoring = Monitoring("", "", "")
    auklet_monitoring.start()
    base.start(state="WithAukletMQTT")

    conf_patcher.stop()
    producer_patcher.stop()


def display_complete_results():
    """
    This function displays the final
    compared result.  Results are in table format.
    """
    with open('/tmp/benchmark_results') as file:
        my_list = tuple(tuple(map(str, line.split())) for line in file)

    without_auklet_run_time = with_auklet_mmqt_run_time = 0
    number_of_tests = int(len(my_list) / 2)

    try:
        print("\n\nTests comparison.")
        print(my_list[0][0].split('_')[0],
              my_list[number_of_tests][0].split('_')[0], sep='\t')
        print("seconds", "seconds", "name", sep='\t\t')

        for i in range(0, number_of_tests):
            without_auklet = round(float(my_list[i][2]), 6)
            with_auklet_mmqt = round(float(my_list[i+number_of_tests][2]), 6)

            print(without_auklet, with_auklet_mmqt, my_list[i][1], sep='\t\t')

        for i in range(0, number_of_tests):  # Calculates total runtime
            without_auklet_run_time = \
                without_auklet_run_time + float(my_list[i][2])

            with_auklet_mmqt_run_time = with_auklet_mmqt_run_time + \
                float(my_list[number_of_tests+i][2])

        print("---")
        print(str(round(without_auklet_run_time, 6)),
              str(round(with_auklet_mmqt_run_time, 6)),
              "Total Run Time", sep='\t\t')

    except IndexError:
        print("Tests did not fully complete.")


def main():
    without_auklet()
    with_auklet_and_mqtt()
    display_complete_results()


if __name__ == "__main__":
    main()
