# -*- coding: utf-8 -*-
"""
   profiling.stats
   ~~~~~~~~~~~~~~~

   Statistics classes.

   :copyright: (c) 2014-2017, What! Studio
   :license: BSD, see LICENSE for more details.

"""
from __future__ import absolute_import, division

import time
import psutil
import pprint
import inspect
from uuid import uuid4
from ipify import get_ip

__all__ = ['AukletProfileTree', 'Event']


class Function(object):
    samples = 1
    calls = 0
    line_num = ''
    func_name = ''
    file_path = ''

    children = []
    parent = None

    def __init__(self, line_num, func_name, file_path=None,
                 parent=None, calls=0):
        self.line_num = line_num
        self.func_name = func_name
        self.parent = parent
        self.children = []
        self.file_path = file_path
        self.calls = calls

    def __str__(self):
        pp = pprint.PrettyPrinter()
        return pp.pformat(dict(self))

    def __iter__(self):
        yield "functionName", self.func_name
        yield "nSamples", self.samples
        yield "lineNum", self.line_num
        yield "nCalls", self.calls
        yield "filePath", self.file_path
        yield "callees", [dict(item) for item in self.children]

    def has_child(self, test_child):
        for child in self.children:
            if test_child.func_name == child.func_name \
                    and test_child.file_path == child.file_path:
                return child
        return False


class Event(object):
    trace = []
    exc_type = None
    line_num = 0

    def __init__(self, exc_type, value, tb, tree):
        self.exc_type = exc_type.__name__
        self.line_num = tb.tb_lineno
        self._build_traceback(tb, tree)

    def __iter__(self):
        yield "stackTrace", self.trace
        yield "excType", self.exc_type

    def _filter_frame(self, file_name):
        if "site-packages" in file_name or \
                "Python.framework" in file_name:
            return True
        return False

    def _convert_locals_to_string(self, local_vars):
        for key in local_vars:
            if type(local_vars[key]) != str and type(local_vars[key]) != int:
                local_vars[key] = str(local_vars[key])
        return local_vars

    def _build_traceback(self, trace, tree):
        tb = []
        while trace:
            frame = trace.tb_frame
            path = inspect.getsourcefile(frame) or inspect.getfile(frame)
            if self._filter_frame(path):
                trace = trace.tb_next
                continue
            tb.append({"functionName": frame.f_code.co_name,
                       "filePath": path,
                       "locals": self._convert_locals_to_string(frame.f_locals)})
            trace = trace.tb_next
        self.trace = tb


class AukletProfileTree(object):
    git_hash = None
    root_func = None
    public_ip = None

    def __init__(self):
        self.public_ip = get_ip()

    def _create_frame_func(self, frame, root=False, parent=None):
        if root:
            return Function(
                line_num=1,
                func_name="root",
                parent=None,
                file_path=None,
                calls=1
            )

        calls = 0
        if frame[1]:
            calls = 1
        frame = frame[0]

        file_path = inspect.getsourcefile(frame) or inspect.getfile(frame)
        return Function(
            line_num=frame.f_code.co_firstlineno,
            func_name=frame.f_code.co_name,
            parent=parent,
            file_path=file_path,
            calls=calls
        )

    def _remove_ignored_frames(self, new_stack):
        cleansed_stack = []
        for frame in new_stack:
            file_name = inspect.getsourcefile(frame[0]) or \
                        inspect.getfile(frame[0])
            if "site-packages" not in file_name and \
                    "Python.framework" not in file_name:
                cleansed_stack.append(frame)
        return cleansed_stack

    def _build_tree(self, new_stack):
        new_stack = self._remove_ignored_frames(new_stack)
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
            has_child.calls += new_child.calls
            has_child.samples += 1
            return self._update_sample_count(has_child, new_child)
        parent.children.append(new_child)

    def update_hash(self, new_stack):
        new_tree_root = self._build_tree(new_stack)
        if self.root_func is None:
            self.root_func = new_tree_root
            return self.root_func
        self.root_func.samples += 1
        self._update_sample_count(self.root_func, new_tree_root)

    def clear_root(self):
        self.root_func = None
        return True

    def build_profiler_object(self, app_id):
        return {
            "application": app_id,
            "publicIp": self.public_ip,
            "id": str(uuid4()),
            "timestamp": int(round(time.time() * 1000)),
            "tree": dict(self.root_func)
        }


class SystemMetrics(object):
    cpu_usage = 0.0
    mem_usage = 0.0
    inbound_network = 0
    outbound_network = 0

    def __init__(self):
        self.cpu_usage = psutil.cpu_percent(interval=1)
        self.mem_usage = psutil.virtual_memory().used
        network = psutil.net_io_counters()
        self.inbound_network = network.bytes_recv
        self.outbound_network = network.bytes_sent

    def __iter__(self):
        yield "cpuUsage", self.cpu_usage
        yield "memoryUsage", self.mem_usage
        yield "inboundNetwork", self.inbound_network
        yield "outboundNetwork", self.outbound_network
