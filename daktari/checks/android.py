from daktari.check import Check, CheckResult
from daktari.os import OS, get_env_var_value


class AndroidNdkHomeSet(Check):
    name = "android.ndkHomeSet"

    def __init__(self, expected_version):
        self.variable_name = "ANDROID_NDK_HOME"
        self.expected_version = expected_version
        self.suggestions = {OS.GENERIC: f"""
            Export {self.variable_name} in your shell config.
            The expected value is ANDROID_SDK_HOME/ndk/{self.expected_version}.
            If you manage your android sdk using Android Studio, you can find your ANDROID_SDK_HOME by going to
            Tools > SDK Manager and copying the Android SDK location.
            You may need to check under SDK Tools that you have the NDK installed.
            """}

    def check(self) -> CheckResult:
        expected_substring = f"ndk/{self.expected_version}"
        return self.verify(
            expected_substring in get_env_var_value(self.variable_name),
            f"{self.variable_name} is <not/> set with expected version {self.expected_version}",
        )
