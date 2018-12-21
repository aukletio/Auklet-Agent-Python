import sys
import unittest
from mock import patch

from auklet.stats import Function, Event, MonitoringTree, SystemMetrics

try:
    import psutil
except ImportError:
    # Some platforms that applications could be running on require specific
    # installation of psutil which we cannot configure currently
    psutil = None


class TestFunction(unittest.TestCase):
    def setUp(self):
        self.function = Function(line_num=0, func_name="UnitTest")

    def test___str__(self):
        self.assertNotEqual(self.function.__str__(), None)

    def test___iter__(self):
        for t in self.function.__iter__():
            self.assertNotEqual(t, None)

    def test_has_child(self):
        self.assertFalse(self.function.has_child(test_child=""))
        self.function.children.append(self.get_test_child())
        self.assertNotEqual(
            self.function.has_child(test_child=self.get_test_child()), False)

    def get_test_child(self):
        class TestChild:
            func_name = "test_child"
            file_path = "file_path"
        return TestChild


class TestEvent(unittest.TestCase):
    def setUp(self):
        self.tree = MonitoringTree()
        self.patcher = patch(
            'auklet.stats.MonitoringTree.get_filename', new=self.get_filename)
        self.patcher.start()
        self.event = Event(
            exc_type=str, tb=self.get_traceback(),
            tree=self.tree, abs_path="/")

    def tearDown(self):
        self.patcher.stop()

    def test___iter__(self):
        for t in self.event.__iter__():
            self.assertNotEqual(t, None)

    def test_convert_locals_to_string(self):
        self.assertNotEqual(
            self.event._convert_locals_to_string(
                local_vars={"key": "value"}), None)
        self.assertNotEqual(
            self.event._convert_locals_to_string(
                local_vars={"key": True}), None)

    def test_build_traceback(self):
        self.build_patcher('auklet.stats.MonitoringTree.get_filename', "")

    def get_filename(self, code="code", frame="frame"):
        _ = code
        _ = frame
        return ""

    def get_traceback(self):
        class Code:
            co_name = None
        class Frame:
            f_code = Code()
            f_lineno = 0
            f_locals = {"key": "value"}
        class Traceback:
            tb_lineno = 0
            tb_frame = Frame()
            tb_next = None
        return Traceback

    def build_patcher(self, patch_location, return_value,
                      expected=[{'functionName': None,
                                 'filePath': '',
                                 'lineNumber': 0,
                                 'locals': {'key': 'value'}}]):

        with patch(patch_location) as mock_patcher:
            mock_patcher.return_value = return_value
            self.event._build_traceback(
                trace=self.get_traceback(), tree=self.tree)
            self.assertEqual(expected, self.event.trace)



class TestMonitoringTree(unittest.TestCase):
    def setUp(self):
        self.monitoring_tree = MonitoringTree()
        self.function = Function(line_num=0, func_name="UnitTest")

    def test_get_filename(self):
        self.monitoring_tree.cached_filenames.clear()
        self.monitoring_tree.cached_filenames['file_name'] = "file_name"
        self.assertEqual(
            self.monitoring_tree.get_filename(
                code=self.get_code(), frame="frame"), self.get_code().co_code)

        self.monitoring_tree.cached_filenames.clear()
        self.monitoring_tree.cached_filenames['file_name'] = None
        self.assertIsNone(self.monitoring_tree.get_filename(
            code=self.get_code(), frame="frame"))

        with patch('inspect.getsourcefile') as _get_source_file:
            _get_source_file.return_value = "file_name"
            self.assertIsNotNone(self.monitoring_tree.get_filename(
                code=self.get_code(), frame="frame"))

    def test_create_frame_function(self):
        class Code:
            co_firstlineno = 0
            co_name = ""

        class Frame:
            f_code = Code

        self.assertIsNotNone(
            self.monitoring_tree._create_frame_func("", root=True))
        with patch(
                'auklet.stats.MonitoringTree.get_filename') as _get_filename:
            _get_filename.return_value = None
            self.assertIsNotNone(
                self.monitoring_tree._create_frame_func(Frame))
            self.monitoring_tree.abs_path = "/tests/"
            _get_filename.return_value = "/tests/test_stats.py"
            self.assertIsNotNone(
                self.monitoring_tree._create_frame_func(Frame))

    def test__build_tree(self):
        class Code:
            co_firstlineno = 0
            co_name = ""
            co_code = ""

        class Frame:
            f_code = Code
            file_path = ""
            children = []

        self.assertIsNotNone(self.monitoring_tree._build_tree([Frame, Frame]))

        with patch(
                'auklet.stats.MonitoringTree._create_frame_func') as \
                create_frame_func:
            create_frame_func.return_value = Frame
            self.monitoring_tree._build_tree([Frame])
        self.assertIsNotNone(self.monitoring_tree._build_tree([Frame, Frame]))

    def test_update_sample_count(self):
        self.assertTrue(self.monitoring_tree._update_sample_count(
            parent=None, new_parent=self.get_new_parent()))

        if sys.version_info < (3,):
            self.build_assert_raises(
                "class NewChild has no attribute 'children'", True)
            self.build_assert_raises(
                "Parent instance has no attribute 'children'", False)
        else:
            self.build_assert_raises(
                "type object 'NewChild' has no attribute 'children'", True)
            self.build_assert_raises(
                "'Parent' object has no attribute 'children'", False)

    def test_update_hash(self):
        self.assertNotEqual(
            self.monitoring_tree.update_hash(new_stack=""), None)

        def _update_sample_count(self, parent, new_parent):
            global test_update_hash_parent  # used to tell if hash was created
            test_update_hash_parent = parent

        self.monitoring_tree.root_func = self.function
        with patch('auklet.stats.MonitoringTree._update_sample_count',
                   new=_update_sample_count):
            self.monitoring_tree.update_hash(new_stack="")

        self.assertNotEqual(test_update_hash_parent, None)  # global used here

    def test_clear_root(self):
        self.monitoring_tree.root_func = self.get_root_function()
        self.assertTrue(self.monitoring_tree.clear_root())
        self.assertEqual(self.monitoring_tree.root_func, None)

    def test_build_tree(self):
        self.monitoring_tree.root_func = None
        self.assertEqual({}, self.monitoring_tree.build_tree(self.Client()))
        self.monitoring_tree.root_func = self.get_root_function()
        self.assertIsNotNone(self.monitoring_tree.build_tree(self.Client()))

    def test_build_msgpack_tree(self):
        self.monitoring_tree.root_func = self.get_root_function()
        self.assertNotEqual(
            self.monitoring_tree.build_msgpack_tree(self.Client()),
            None)

    def get_code(self):
        class Code:
            co_code = "file_name"
            co_firstlineno = 0
            co_name = ""
        return Code

    def get_frame(self):
        class Frame:
            f_code = self.get_code()
        frame = [Frame, Frame]
        return frame

    def get_root_function(self):
        return {'callees': [],
                'filePath': None,
                'functionName': 'root',
                'lineNumber': 1,
                'nCalls': 1,
                'nSamples': 1}

    def get_parent(self):
        pass

    def get_new_parent(self):
        class Parent:
            children = []
        return Parent

    def build_assert_raises(self, expected, child_state):
        global child_exists  # For some reason this needs to be done twice
        child_exists = child_state
        with self.assertRaises(AttributeError) as error:
            self.monitoring_tree._update_sample_count(
                parent=self.Parent(), new_parent=self.NewParent())
        self.assertEqual(expected, str(error.exception))

    class Client:
        broker_username = "None"
        abs_path = "/Test/abs/path/"
        app_id = "12345"
        version = None

    class Parent:
        calls = 0
        samples = 0

        def has_child(self, new_child):
            global child_exists  # Must be used to pass variable in class
            if child_exists:
                class Child:
                    calls = 0
                    samples = 0

                child = Child
                child_exists = False
                return child
            else:
                return False

    class NewParent:
        class NewChild:
            calls = 0

        children = [NewChild]


class TestSystemMetrics(unittest.TestCase):
    def setUp(self):
        self.system_metrics = SystemMetrics()

    @patch('auklet.stats.psutil.sensors_battery')
    @patch('auklet.stats.psutil.virtual_memory')
    @patch('auklet.stats.psutil.cpu_percent')
    def test___init__(self, _cpu_percent, _virtual_memory, _sensors_battery):
        _cpu_percent.return_value = 1.0
        _virtual_memory.side_effect = self.VirtualMemory
        _sensors_battery.side_effect = self.SensorsBattery
        self.system_metrics.__init__()

        self.assertIsNotNone(self.system_metrics.cpu_usage)
        self.assertIsNotNone(self.system_metrics.mem_usage)
        self.assertIsNotNone(self.system_metrics.current_battery_percent)
        self.assertIsNotNone(self.system_metrics.power_plugged_in)
        self.assertIsNotNone(self.system_metrics.battery_seconds_left)

        with patch('auklet.stats.psutil.sensors_battery') as _sensors_battery:
            _sensors_battery.return_value = self.SensorsBatteryUnknown
            self.system_metrics.__init__()
            self.assertIs(psutil.POWER_TIME_UNKNOWN,
                          self.system_metrics.battery_seconds_left)

        with patch('auklet.stats.psutil.sensors_temperatures') \
                as _sensors_temperature:
            _sensors_temperature.side_effect = AttributeError
            self.system_metrics.__init__()

    def test___iter__(self):
        for value in self.system_metrics.__iter__():
            self.assertIsNotNone(value)

    class VirtualMemory:
        percent = 1.0

    class SensorsBattery:
        percent = 1.0
        power_plugged = True
        secsleft = 1

    class SensorsBatteryUnknown:
        percent = 1.0
        power_plugged = True
        secsleft = psutil.POWER_TIME_UNKNOWN


if __name__ == '__main__':
    unittest.main()
