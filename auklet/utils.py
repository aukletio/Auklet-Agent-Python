import os
import sys
import uuid
import json
import hashlib
import requests
import tempfile

from auklet.__about__ import __version__ as auklet_version
from auklet.errors import AukletConfigurationError

__all__ = ['open_auklet_url', 'post_auklet_url', 'create_file', 'clear_file',
           'build_url', 'get_mac', 'get_device_ip', 'create_dir',
           'setup_thread_excepthook', 'get_abs_path', 'get_agent_version',
           'b', 'u']

try:
    # For Python 3.0 and later
    from urllib.error import HTTPError, URLError
    from urllib.request import Request, urlopen
except ImportError:
    # Fall back to Python 2's urllib2
    from urllib2 import urlopen, Request, HTTPError, URLError


def open_auklet_url(url, apikey):
    url = Request(url, headers={"Authorization": "JWT %s" % apikey})
    try:
        res = urlopen(url)
    except HTTPError as e:
        if e.code == 401:
            raise AukletConfigurationError(
                "Invalid configuration of Auklet Monitoring, "
                "ensure proper API key and app ID passed to "
                "Monitoring class"
            )
        raise e
    except URLError:
        return None
    return res


def post_auklet_url(url, apikey, data):
    try:
        res = requests.post(
            url,
            json=data,
            headers={"Authorization": "JWT %s" % apikey,
                     "Content-Type": "application/json"})
    except requests.HTTPError:
        return None
    try:
        return res.json()
    except json.decoder.JSONDecodeError:
        return res


def create_file(filename):
    open(filename, "a").close()


def create_dir(dir_name=".auklet"):
    dirs = [os.getcwd(), os.path.expanduser("~")]
    for directory in dirs:
        full_path = "{}/{}".format(directory, dir_name)
        if os.access(directory, os.W_OK):
            if not os.path.exists(full_path):
                os.mkdir(full_path)
            return full_path
    return tempfile.gettempdir()


def clear_file(filename):
    open(filename, "w").close()


def build_url(base_url, extension):
    return '{}{}'.format(base_url, extension)


def get_mac():
    mac_num = hex(uuid.getnode()).replace('0x', '').upper()
    mac = '-'.join(mac_num[i: i + 2] for i in range(0, 11, 2))
    return hashlib.md5(b(mac)).hexdigest()


def get_abs_path(path):
    try:
        return os.path.abspath(path).split('/.auklet')[0]
    except IndexError:
        return ''


def get_device_ip():
    try:
        request = Request("https://api.ipify.org")
        res = urlopen(request)
        return u(res.read())
    except (HTTPError, URLError, Exception):
        # TODO log to kafka if the ip service fails for any reason
        return None


def get_agent_version():
    return auklet_version


def setup_thread_excepthook():
    import threading
    """
    Workaround for `sys.excepthook` thread bug from:
    http://bugs.python.org/issue1230540

    Call once from the main thread before creating any threads.
    """
    init_original = threading.Thread.__init__

    def init(self, *args, **kwargs):

        init_original(self, *args, **kwargs)
        run_original = self.run

        def run_with_except_hook(*args2, **kwargs2):
            try:
                run_original(*args2, **kwargs2)
            except (KeyboardInterrupt, SystemExit):
                raise
            except:
                sys.excepthook(*sys.exc_info())

        self.run = run_with_except_hook

    threading.Thread.__init__ = init


if sys.version_info < (3,):
    # Python 2 and 3 String Compatibility
    def b(x):
        return x

    def u(x):
        return x
else:
    # https://pythonhosted.org/six/#binary-and-text-data
    import codecs

    def b(x):
        # Produces a unicode string to encoded bytes
        return codecs.utf_8_encode(x)[0]

    def u(x):
        # Produces a byte string from a unicode object
        return codecs.utf_8_decode(x)[0]
