from __future__ import absolute_import, unicode_literals

import sys
import functools
import threading

from auklet.base import deferral, Runnable, setup_thread_excepthook


__all__ = ['AukletSampler']

INTERVAL = 1e-3  # 1ms


class AukletSampler(Runnable):
    """Uses :func:`sys.setprofile` and :func:`threading.setprofile` to sample
    running frames per thread.  It can be used at systems which do not support
    profiling signals.
    Just like :class:`profiling.tracing.timers.ThreadTimer`, `Yappi`_ is
    required for earlier than Python 3.3.
    .. _Yappi: https://code.google.com/p/yappi/
    """
    client = None

    def __init__(self, client, tree, *args, **kwargs):
        sys.excepthook = self.handle_exc
        self.sampled_times = {}
        self.counter = 0
        self.interval = INTERVAL
        self.client = client
        self.tree = tree
        setup_thread_excepthook()

    def _profile(self, profiler, frame, event, arg):
        profiler.sample(frame, event)
        self.counter += 1
        if self.counter % 10000 == 0:
            # Produce tree to kafka every 10 seconds
            # TODO read the produce interval from application on the backend
            self.client.produce(
                self.tree.build_tree(self.client.app_id))
            self.tree.clear_root()

    def handle_exc(self, type, value, traceback):
        event = self.client.build_event_data(type, traceback,
                                             self.tree)
        self.client.produce(event, "event")

    def run(self, profiler):
        profile = functools.partial(self._profile, profiler)
        with deferral() as defer:
            sys.setprofile(profile)
            defer(sys.setprofile, None)
            threading.setprofile(profile)
            defer(threading.setprofile, None)
            yield