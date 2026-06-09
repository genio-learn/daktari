import os
import tempfile
import unittest

from daktari.check import CheckStatus
from daktari.checks.misc import HostAliasesConfigured

# Stock macOS /etc/hosts maps "localhost" to both 127.0.0.1 and ::1, with the
# ::1 line appearing last. The check must treat the IPv4 alias as satisfied
# regardless of the order the two lines appear in (see HostAliasesConfigured).
DUAL_STACK_IPV6_LAST = "127.0.0.1 localhost\n255.255.255.255 broadcasthost\n::1 localhost\n"
DUAL_STACK_IPV4_LAST = "::1 localhost\n255.255.255.255 broadcasthost\n127.0.0.1 localhost\n"


class TestHostAliasesConfigured(unittest.TestCase):
    def _hosts_fixture(self, content):
        f = tempfile.NamedTemporaryFile("w", suffix=".hosts", delete=False)
        f.write(content)
        f.close()
        self.addCleanup(os.unlink, f.name)
        return f.name

    def test_checking_hosts_does_not_blow_up_on_success(self):
        result = HostAliasesConfigured({}).check()
        self.assertEqual(result.status, CheckStatus.PASS)

    def test_checking_hosts_does_not_blow_up_on_failure(self):
        result = HostAliasesConfigured({"host": "no.such.entry.surely"}).check()
        self.assertEqual(result.status, CheckStatus.FAIL)

    def test_dual_stack_alias_passes_with_ipv6_entry_last(self):
        path = self._hosts_fixture(DUAL_STACK_IPV6_LAST)
        result = HostAliasesConfigured({"localhost": "127.0.0.1"}, hosts_path=path).check()
        self.assertEqual(result.status, CheckStatus.PASS)

    def test_dual_stack_alias_passes_with_ipv4_entry_last(self):
        path = self._hosts_fixture(DUAL_STACK_IPV4_LAST)
        result = HostAliasesConfigured({"localhost": "127.0.0.1"}, hosts_path=path).check()
        self.assertEqual(result.status, CheckStatus.PASS)

    def test_dual_stack_ipv6_alias_also_satisfied(self):
        path = self._hosts_fixture(DUAL_STACK_IPV6_LAST)
        result = HostAliasesConfigured({"localhost": "::1"}, hosts_path=path).check()
        self.assertEqual(result.status, CheckStatus.PASS)

    def test_missing_alias_still_fails(self):
        path = self._hosts_fixture(DUAL_STACK_IPV6_LAST)
        result = HostAliasesConfigured({"localhost": "10.0.0.1"}, hosts_path=path).check()
        self.assertEqual(result.status, CheckStatus.FAIL)


if __name__ == "__main__":
    unittest.main()
