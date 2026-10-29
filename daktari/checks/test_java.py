import unittest

from semver import VersionInfo

from .java import parse_java_version_output, parse_javac_version_output


class TestJava(unittest.TestCase):
    def test_parse_java_non_semver_format_version(self):
        # JRE versions prior to 9 do not use semver format
        version_output = """openjdk version "1.8.0_292"
OpenJDK Runtime Environment (build 1.8.0_292-8u292-b10-0ubuntu1~20.04-b10)
OpenJDK 64-Bit Server VM (build 25.292-b10, mixed mode)
"""
        version = parse_java_version_output(version_output)
        self.assertEqual(version, VersionInfo(8))

    def test_parse_ubuntu_openjdk_17_version(self):
        version_output = """openjdk version "17" 2021-09-14
OpenJDK Runtime Environment (build 17+35-Ubuntu-121.04)
OpenJDK 64-Bit Server VM (build 17+35-Ubuntu-121.04, mixed mode, sharing)
"""
        version = parse_java_version_output(version_output)
        self.assertEqual(version, VersionInfo(17, 0, 0))

    def test_parse_java_semver_format_version(self):
        version_output = """openjdk version "11.0.9" 2020-10-20
OpenJDK Runtime Environment AdoptOpenJDK (build 11.0.9+11)
OpenJDK 64-Bit Server VM AdoptOpenJDK (build 11.0.9+11, mixed mode)
"""
        version = parse_java_version_output(version_output)
        self.assertEqual(version, VersionInfo(11, 0, 9))

    def test_parse_java_four_part_version(self):
        version_output = """openjdk version "21.0.12.1" 2026-08-18 LTS
OpenJDK Runtime Environment Temurin-21.0.12.1+1 (build 21.0.12.1+1-LTS)
OpenJDK 64-Bit Server VM Temurin-21.0.12.1+1 (build 21.0.12.1+1-LTS, mixed mode, sharing)
"""
        version = parse_java_version_output(version_output)
        self.assertEqual(version, VersionInfo(21))

    def test_parse_java_unknown_format_version(self):
        version_output = 'openjdk version "a.b.c"'
        version = parse_java_version_output(version_output)
        self.assertEqual(version, None)

    def test_parse_java_unknown_format_output(self):
        version_output = """

Command 'java' not found, but can be installed with:

sudo apt install openjdk-11-jre-headless  # version 11.0.11+9-0ubuntu2~20.04, or
sudo apt install default-jre              # version 2:1.11-72
sudo apt install openjdk-13-jre-headless  # version 13.0.7+5-0ubuntu1~20.04
sudo apt install openjdk-16-jre-headless  # version 16.0.1+9-1~20.04
sudo apt install openjdk-8-jre-headless   # version 8u292-b10-0ubuntu1~20.04
sudo apt install openjdk-14-jre-headless  # version 14.0.2+12-1~20.04

"""
        version = parse_java_version_output(version_output)
        self.assertEqual(version, None)

    def test_parse_javac_non_semver_format_version(self):
        version_output = "javac 1.8.0_292\n"
        version = parse_javac_version_output(version_output)
        self.assertEqual(version, VersionInfo(8, 0, 0))

    def test_parse_javac_semver_format_version(self):
        version_output = "javac 11.0.9\n"
        version = parse_javac_version_output(version_output)
        self.assertEqual(version, VersionInfo(11, 0, 9))

    def test_parse_javac_unknown_format_version(self):
        version_output = "javac a.b.c\n"
        version = parse_javac_version_output(version_output)
        self.assertEqual(version, None)

    def test_parse_javac_unknown_format_output(self):
        version_output = """
Command 'javac' not found, but can be installed with:

sudo apt install openjdk-11-jdk-headless  # version 11.0.11+9-0ubuntu2~20.04, or
sudo apt install default-jdk              # version 2:1.11-72
sudo apt install openjdk-13-jdk-headless  # version 13.0.7+5-0ubuntu1~20.04
sudo apt install openjdk-16-jdk-headless  # version 16.0.1+9-1~20.04
sudo apt install openjdk-8-jdk-headless   # version 8u292-b10-0ubuntu1~20.04
sudo apt install ecj                      # version 3.16.0-1
sudo apt install openjdk-14-jdk-headless  # version 14.0.2+12-1~20.04

"""
        version = parse_javac_version_output(version_output)
        self.assertEqual(version, None)


if __name__ == "__main__":
    unittest.main()
