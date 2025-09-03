# divar_crl/compat_distutils.py
'''
import sys
import types
# raise error when run python no module distutils.version import LooseVersion, so we fix it by beloow
if sys.version_info < (3, 12):
    # On 3.6–3.11 we already have distutils; just expose the real LooseVersion
    from distutils.version import LooseVersion
else:
    # On 3.12+ distutils is gone, so patch it in from packaging
    # Create fake distutils.version module
    from packaging.version import Version as _PkgVersion
    dist_mod = types.ModuleType("distutils.version")


    class LooseVersion(_PkgVersion):
        @property
        def version(self):
            # mimic distutils.LooseVersion.version list
            return list(self.release)


    dist_mod.LooseVersion = LooseVersion

    # Ensure the distutils namespace exists
    if "distutils" not in sys.modules:
        sys.modules["distutils"] = types.ModuleType("distutils")
    sys.modules["distutils.version"] = dist_mod
'''
