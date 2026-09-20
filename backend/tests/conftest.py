import sys
import platform

# Dev/test-only workaround: On local Windows machines running Python >= 3.13,
# platform.machine() queries the Windows WMI service via _wmi.pyd which can hang indefinitely.
# In Linux/Docker production containers, this condition is False and is never evaluated.
if sys.platform.startswith("win") and sys.version_info >= (3, 13):
    try:
        platform.machine = lambda *args, **kwargs: "AMD64"
        platform.uname = lambda *args, **kwargs: platform.uname_result("Windows", "localhost", "10", "10.0.19041", "AMD64")
    except Exception:
        pass
