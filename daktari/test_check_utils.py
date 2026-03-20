import unittest
from unittest import mock

from daktari.check_utils import (
    CyclicCheckException,
    filter_checks_by_env_var,
    filter_checks_by_name,
    filter_out_checks_by_name,
    get_all_dependent_check_names,
)
from daktari.test_check_factory import DummyCheck


class TestCheckUtils(unittest.TestCase):
    def test_get_all_dependent_check_names(self):
        # Dummy checks set up with dependencies as follows (A <- B means "B depends on A")
        #
        #   A <- B <- C <- E
        #             D <- E
        #
        check_a = DummyCheck("A")
        check_b = DummyCheck("B", [check_a])
        check_c = DummyCheck("C", [check_b])
        check_d = DummyCheck("D")
        check_e = DummyCheck("E", [check_c, check_d])

        self.assertEqual(set(), get_all_dependent_check_names(check_a))
        self.assertEqual({"A"}, get_all_dependent_check_names(check_b))
        self.assertEqual({"A", "B"}, get_all_dependent_check_names(check_c))
        self.assertEqual({"A", "B", "C", "D"}, get_all_dependent_check_names(check_e))

    def test_self_cycle(self):
        check = DummyCheck("A")
        check.depends_on = [check]
        with self.assertRaises(CyclicCheckException):
            get_all_dependent_check_names(check)

    def test_simple_cycle(self):
        check_a = DummyCheck("A")
        check_b = DummyCheck("B")

        check_a.depends_on = [check_b]
        check_b.depends_on = [check_a]
        with self.assertRaises(CyclicCheckException):
            get_all_dependent_check_names(check_a)

    def test_larger_cycle(self):
        check_a = DummyCheck("A")
        check_b = DummyCheck("B")
        check_c = DummyCheck("C")

        check_a.depends_on = [check_b]
        check_b.depends_on = [check_c]
        check_c.depends_on = [check_a]

        with self.assertRaises(CyclicCheckException):
            get_all_dependent_check_names(check_a)

    def test_depends_on_cycle(self):
        check_a = DummyCheck("A")
        check_b = DummyCheck("B")
        check_c = DummyCheck("C")
        check_d = DummyCheck("D")

        check_a.depends_on = [check_b]
        check_b.depends_on = [check_c]
        check_c.depends_on = [check_d]
        check_d.depends_on = [check_b]

        with self.assertRaises(CyclicCheckException):
            get_all_dependent_check_names(check_a)

    def test_filter_checks_by_name_includes_dependencies(self):
        check_a = DummyCheck("A")
        check_b = DummyCheck("B", [check_a])
        check_c = DummyCheck("C", [check_b])
        check_d = DummyCheck("D")

        filtered_checks = filter_checks_by_name([check_a, check_b, check_c, check_d], {"C"})

        self.assertEqual(["A", "B", "C"], [check.name for check in filtered_checks])

    def test_filter_checks_by_name_raises_for_unknown_checks(self):
        with self.assertRaisesRegex(ValueError, "Unknown Daktari check names"):
            filter_checks_by_name([DummyCheck("A")], {"B"})

    def test_filter_out_checks_by_name_removes_requested_checks_and_dependants(self):
        check_a = DummyCheck("A")
        check_b = DummyCheck("B", [check_a])
        check_c = DummyCheck("C", [check_b])
        check_d = DummyCheck("D")

        filtered_checks = filter_out_checks_by_name([check_a, check_b, check_c, check_d], {"B"})

        self.assertEqual(["A", "D"], [check.name for check in filtered_checks])

    @mock.patch.dict("os.environ", {}, clear=True)
    def test_filter_checks_by_env_var_returns_all_checks_when_not_set(self):
        check_a = DummyCheck("A")
        check_b = DummyCheck("B")

        filtered_checks = filter_checks_by_env_var([check_a, check_b])

        self.assertEqual(["A", "B"], [check.name for check in filtered_checks])

    @mock.patch.dict("os.environ", {"DAKTARI_ONLY_CHECKS": "C"}, clear=True)
    def test_filter_checks_by_env_var_filters_checks_and_dependencies(self):
        check_a = DummyCheck("A")
        check_b = DummyCheck("B", [check_a])
        check_c = DummyCheck("C", [check_b])
        check_d = DummyCheck("D")

        filtered_checks = filter_checks_by_env_var([check_a, check_b, check_c, check_d])

        self.assertEqual(["A", "B", "C"], [check.name for check in filtered_checks])

    @mock.patch.dict("os.environ", {"DAKTARI_ONLY_CHECKS": "unknown"}, clear=True)
    def test_filter_checks_by_env_var_raises_for_unknown_checks(self):
        with self.assertRaisesRegex(ValueError, "Unknown Daktari check names in DAKTARI_ONLY_CHECKS"):
            filter_checks_by_env_var([DummyCheck("A")])


if __name__ == "__main__":
    unittest.main()
