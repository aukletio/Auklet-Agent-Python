from __future__ import absolute_import, division, unicode_literals

import msgpack

import pprint
import inspect
from uuid import uuid4
from time import time
from auklet.utils import get_agent_version

try:
    import psutil
except ImportError:  # pragma: no cover
    # Some platforms that applications could be running on require specific
    # installation of psutil which we cannot configure currently
    psutil = None

__all__ = ['MonitoringTree', 'Event', 'SystemMetrics', 'Function']


class Function(object):
    __slots__ = ['samples', 'line_num', 'func_name', 'file_path',
                 'children', 'parent']

    def __init__(self, line_num, func_name, file_path="",
                 parent=None, samples=1):
        self.line_num = line_num
        self.func_name = func_name
        self.parent = parent
        self.children = []
        self.file_path = file_path
        self.samples = samples

    def __str__(self):
        pp = pprint.PrettyPrinter()
        return pp.pformat(dict(self))

    def __iter__(self):
        yield "functionName", self.func_name
        yield "nSamples", self.samples
        yield "lineNumber", self.line_num
        yield "filePath", self.file_path
        yield "callees", [dict(item) for item in self.children]

    def has_child(self, test_child):
        for child in self.children:
            if test_child.func_name == child.func_name \
                    and test_child.file_path == child.file_path:
                return child
        return False


class Event(object):
    __slots__ = ['trace', 'exc_type', 'line_num', 'abs_path']

    def __init__(self, exc_type, tb, tree, abs_path):
        self.exc_type = exc_type.__name__
        self.line_num = tb.tb_lineno
        self.abs_path = abs_path
        self._build_traceback(tb, tree)

    def __iter__(self):
        yield "stackTrace", self.trace
        yield "excType", self.exc_type

    def _convert_locals_to_string(self, local_vars):
        for key in local_vars:
            if type(local_vars[key]) != str and type(local_vars[key]) != int:
                local_vars[key] = str(local_vars[key])
        return local_vars

    def _build_traceback(self, trace, tree):
        tb = []
        while trace:
            frame = trace.tb_frame
            path = tree.get_filename(frame.f_code, frame)
            tb.append({"functionName": frame.f_code.co_name,
                       "filePath": path,
                       "lineNumber": frame.f_lineno,
                       "locals":
                           self._convert_locals_to_string(frame.f_locals)})
            trace = trace.tb_next
        self.trace = tb


class MonitoringTree(object):
    __slots__ = ['commit_hash', 'public_ip', 'mac_hash',
                 'abs_path', 'root_func']
    cached_filenames = {}

    def __init__(self, mac_hash=None, release=None):
        from auklet.utils import get_device_ip, get_abs_path
        self.commit_hash = release
        self.public_ip = get_device_ip()
        self.abs_path = get_abs_path('.auklet/version')
        self.mac_hash = mac_hash
        self.root_func = None

    def get_filename(self, code, frame):
        key = code.co_code
        file_name = self.cached_filenames.get(code.co_code, None)
        if file_name is None:
            try:
                file_name = inspect.getsourcefile(frame) or \
                            inspect.getfile(frame)
            except (TypeError, AttributeError):
                # These functions will fail if the frame is of a
                # built-in module, class or function
                return None
            self.cached_filenames[key] = file_name
        return file_name

    def _create_frame_func(self, frame, root=False, parent=None):
        if root:
            return Function(
                line_num=1,
                func_name="root",
                parent=None,
                file_path="",
                samples=1
            )

        file_path = self.get_filename(frame.f_code, frame)
        return Function(
            line_num=frame.f_code.co_firstlineno,
            func_name=frame.f_code.co_name,
            parent=parent,
            file_path=file_path
        )

    def _build_tree(self, new_stack):
        root_func = self._create_frame_func(None, True)
        parent_func = root_func
        for frame in reversed(new_stack):
            current_func = self._create_frame_func(
                frame, parent=parent_func)
            parent_func.children.append(current_func)
            parent_func = current_func
        return root_func

    def _update_sample_count(self, parent, new_parent):
        if not new_parent.children:
            return True
        new_child = new_parent.children[0]
        has_child = parent.has_child(new_child)
        if has_child:
            has_child.samples += 1
            return self._update_sample_count(has_child, new_child)
        parent.children.append(new_child)

    def update_hash(self, new_stack):
        new_tree_root = self._build_tree(new_stack)
        if self.root_func is None:
            self.root_func = new_tree_root
            return self.root_func
        self._update_sample_count(self.root_func, new_tree_root)

    def clear_root(self):
        self.root_func = None
        return True

    def build_tree(self, client):
        if self.root_func is not None:
            return {
                "application": client.app_id,
                "publicIP": self.public_ip,
                "id": str(uuid4()),
                "timestamp": int(round(time() * 1000)),
                "macAddressHash": self.mac_hash,
                "release": self.commit_hash,
                "agentVersion": get_agent_version(),
                "tree": dict(self.root_func),
                "device": client.broker_username,
                "absPath": client.abs_path,
                "version": client.version
            }
        return {}

    def build_msgpack_tree(self, client):
        return msgpack.packb(self.build_tree(client), use_bin_type=False)


class SystemMetrics(object):
    cpu_usage = 0.0
    mem_usage = 0.0
    inbound_network = 0
    outbound_network = 0
    prev_inbound = 0
    prev_outbound = 0
    current_battery_percent = 0.0
    battery_seconds_left = 0
    power_plugged_in = None
    current_cpu_temperature = 0.0

    def __init__(self):
        if psutil is not None:
            self.cpu_usage = psutil.cpu_percent(interval=1)
            self.mem_usage = psutil.virtual_memory().percent

            # If no battery is installed or metrics can not be determined None
            # is returned.
            # https://psutil.readthedocs.io/en/latest/#psutil.sensors_battery
            if psutil.sensors_battery() is not None:
                self.current_battery_percent = psutil.sensors_battery().percent
                self.power_plugged_in = psutil.sensors_battery().power_plugged
                # If the battery is plugged in it will return
                # POWER_TIME_UNLIMITED.  If the battery was just unplugged or
                # can not receive the information it will return
                # POWER_TIME_UNKNOWN.
                battery_seconds_left = psutil.sensors_battery().secsleft
                if battery_seconds_left in (psutil.POWER_TIME_UNLIMITED,
                                            psutil.POWER_TIME_UNKNOWN):
                    self.battery_seconds_left = battery_seconds_left
                else:
                    self.battery_seconds_left = battery_seconds_left / 60

            # Certain platforms do not support the sensors_teperatures() module
            try:
                self.current_cpu_temperature = psutil.sensors_temperatures()
            except AttributeError:
                pass

    def __iter__(self):
        yield "cpuUsage", self.cpu_usage
        yield "memoryUsage", self.mem_usage
        yield "inboundNetwork", self.inbound_network
        yield "outboundNetwork", self.outbound_network
        yield "currentBatteryPercent", self.current_battery_percent
        yield "batterySecondsLeft", self.battery_seconds_left
        yield "powerPluggedIn", self.power_plugged_in
        yield "currentCPUTemperature", self.current_cpu_temperature
