from __future__ import absolute_import

import os
import json
import logging

from pubnub.pubnub import PubNub
from pubnub.pnconfiguration import PNConfiguration

from auklet.utils import build_url, create_file, open_auklet_url, \
    post_auklet_url, u

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
    com_config_filename = ".auklet/communication"
    producer_types = {
        "monitoring": "python/profiler/{}/{}",
        "event": "python/events/{}/{}",
        "send": "datapoints/{}/{}"
    }
    pubnub = None
    publish_key = None
    subscribe_key = None
    topic_suffix = None

    def __init__(self, client):
        self.client = client
        self._get_conf()
        self.create_producer()
        self.topic_suffix = "{}/{}".format(
            self.client.org_id, self.client.broker_username)
        self.producer_types = {
            "monitoring": "python.profiler",
            "event": "python.events",
            "send": "python.datapoints"
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
        certs_filename = "{}/pubnub.json".format(self.client.auklet_dir)
        if not os.path.isfile(certs_filename):
            url = Request(
                build_url(self.client.base_url, "private/devices/certificates/?cert_format=json"),
                headers={"Authorization": "JWT %s" % self.client.apikey})
            try:
                try:
                    res = urlopen(url)
                except HTTPError as e:
                    # Allow for accessing redirect w/o including the
                    # Authorization token.
                    res = urlopen(e.geturl())
            except URLError as e:
                return False
            create_file(certs_filename)
            f = open(certs_filename, "wb")
            f.write(res.read())
        with open(certs_filename) as f:
            keys = json.loads(f.read())
            self.publish_key = keys['publish_key']
            self.subscribe_key = keys['subscribe_key']
        return True

    def _read_from_conf(self, data):
        self.brokers = data['brokers']
        self.port = int(data['port'])

    def on_disconnect(self, client, userdata, rc):
        if rc != 0:
            logging.debug("Unexpected disconnection from MQTT")

    def create_producer(self):
        if self._get_certs():
            pubnub_config = PNConfiguration()
            pubnub_config.publish_key = self.publish_key
            pubnub_config.subscribe_key = self.subscribe_key
            pubnub_config.uuid = self.client.broker_username
            self.producer = PubNub(pubnub_config)

    def produce(self, data, data_type="monitoring"):
        if data_type == "monitoring":
            return post_auklet_url(
                build_url(
                    self.client.base_url,
                    "private/metrics/store/"
                ),
                self.client.apikey,
                data
            )
        elif data_type == "event":
            return post_auklet_url(
                build_url(
                    self.client.base_url,
                    "private/events/store/"
                ),
                self.client.apikey,
                data
            )
        print("publishing {} to {}".format(data, self.producer_types[data_type]))
        # self.producer.publish(self.producer_types[data_type], data)
        self.producer.publish().channel(
            self.producer_types[data_type]).message(data).sync()
