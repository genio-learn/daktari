import json
import unittest
from unittest import mock

from daktari.checks.mobile import command_failure_summary, get_available_android_avds, get_available_ios_simulators
from daktari.command_utils import CommandErrorException


class TestCommandFailureSummary(unittest.TestCase):
    def test_extracts_first_non_empty_line_from_command_error(self):
        error = CommandErrorException("failed", 1, "", "\nfirst line\nsecond line")

        self.assertEqual("first line", command_failure_summary(error))

    def test_falls_back_to_error_string(self):
        self.assertEqual("boom", command_failure_summary(Exception("boom")))


class TestMobileHelpers(unittest.TestCase):
    @mock.patch("daktari.checks.mobile.run_command")
    def test_get_available_ios_simulators_filters_non_ios_and_unavailable(self, mock_run_command):
        payload = {
            "devices": {
                "com.apple.CoreSimulator.SimRuntime.iOS-18-0": [
                    {
                        "name": "iPhone 16",
                        "udid": "ios-1",
                        "state": "Shutdown",
                        "isAvailable": True,
                        "dataPath": "/tmp/ios-1",
                    },
                    {
                        "name": "Unavailable",
                        "udid": "ios-2",
                        "state": "Shutdown",
                        "isAvailable": False,
                        "dataPath": "/tmp/ios-2",
                    },
                ],
                "com.apple.CoreSimulator.SimRuntime.tvOS-18-0": [
                    {
                        "name": "Apple TV",
                        "udid": "tvos-1",
                        "state": "Shutdown",
                        "isAvailable": True,
                        "dataPath": "/tmp/tvos-1",
                    }
                ],
            }
        }
        mock_run_command.return_value.stdout = json.dumps(payload)

        simulators = get_available_ios_simulators()

        self.assertEqual(1, len(simulators))
        self.assertEqual("iPhone 16", simulators[0]["name"])

    @mock.patch("daktari.checks.mobile.run_command")
    def test_get_available_android_avds_returns_sorted_list(self, mock_run_command):
        mock_run_command.return_value.stdout = "Pixel_8\n\nPixel_7\n"

        self.assertEqual(["Pixel_7", "Pixel_8"], get_available_android_avds())

    @mock.patch("daktari.checks.mobile.run_command")
    def test_get_available_android_avds_raises_when_none_available(self, mock_run_command):
        mock_run_command.return_value.stdout = "\n"

        with self.assertRaisesRegex(CommandErrorException, "No Android AVDs found"):
            get_available_android_avds()


if __name__ == "__main__":
    unittest.main()
