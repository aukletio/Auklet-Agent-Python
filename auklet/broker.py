from __future__ import absolute_import

import os
import ssl
import json
import logging
import paho.mqtt.client as mqtt

from auklet.utils import build_url, create_file, open_auklet_url, u

try:
    # For Python 3.0 and later
    from urllib.error import HTTPError, URLError
    from urllib.request import Request, urlopen
except ImportError:
    # Fall back to Python 2's urllib2
    from urllib2 import urlopen, Request, HTTPError, URLError

__all__ = ["MQTTClient"]


class MQTTClient(object):
    producer = None
    brokers = None
    client = None
    username = None
    password = None
    com_config_filename = ".auklet/communication"
    port = None
    producer_types = {
        "monitoring": "python/profiler/{}/{}",
        "event": "python/events/{}/{}",
        "send": "datapoints/{}/{}"
    }

    def __init__(self, client):
        self.client = client
        self._get_conf()
        self.create_producer()
        topic_suffix = "{}/{}".format(
            self.client.org_id, self.client.broker_username)
        self.producer_types = {
            "monitoring": "python/profiler/{}".format(topic_suffix),
            "event": "python/events/{}".format(topic_suffix),
            "send": "datapoints/{}".format(topic_suffix)
        }

    def _write_conf(self, info):
        with open(self.com_config_filename, "w") as conf:
            conf.write(json.dumps(info))

    def _get_conf(self):
        res = open_auklet_url(
            build_url(
                self.client.base_url, "private/devices/config/"
            ),
            self.client.apikey
        )
        loaded = json.loads(u(res.read()))
        self._write_conf(loaded)
        self._read_from_conf(loaded)

    def _get_certs(self):
        if not os.path.isfile("{}/ca.pem".format(self.client.auklet_dir)):
            url = Request(
                build_url(self.client.base_url, "private/devices/certificates/"),
                headers={"Authorization": "JWT %s" % self.client.apikey})
            try:
                try:
                    res = urlopen(url)
                except HTTPError as e:
                    # Allow for accessing redirect w/o including the
                    # Authorization token.
                    res = urlopen(e.geturl())
            except URLError:
                return False
            filename = "{}/ca.pem".format(self.client.auklet_dir)
            create_file(filename)
            f = open(filename, "wb")
            f.write(res.read())
        return True

    def _read_from_conf(self, data):
        self.brokers = data['brokers']
        self.port = int(data['port'])

    def on_disconnect(self, client, userdata, rc):
        if rc != 0:
            logging.debug("Unexpected disconnection from MQTT")

    def create_producer(self):
        if self._get_certs():
            self.producer = mqtt.Client(client_id=self.client.client_id,
                                        protocol=mqtt.MQTTv311,
                                        transport="ssl",
                                        clean_session=False)
            self.producer.username_pw_set(
                username=self.client.broker_username,
                password=self.client.broker_password)
            self.producer.enable_logger()
            context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
            context.verify_mode = ssl.CERT_REQUIRED
            context.load_verify_locations(
                capath="{}/".format(self.client.auklet_dir))
            context.options &= ~ssl.OP_NO_SSLv3
            self.producer.tls_set_context(context)
            self.producer.on_disconnect = self.on_disconnect
            self.producer.connect_async(self.brokers, self.port)
            self.producer.loop_start()

    def produce(self, data, data_type="monitoring"):
        self.producer.publish(
            self.producer_types[data_type], payload=data, qos=1)
