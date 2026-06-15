"""Mock revenueholdings_license for tests so CLI commands don't hit the paywall."""
import sys
from unittest.mock import MagicMock

# Replace the module before any import resolves it
_mock = MagicMock()
_mock.require_license = MagicMock(return_value=None)
sys.modules.setdefault("revenueholdings_license", _mock)

# Also mock submodules
sys.modules.setdefault("revenueholdings_license.gate", MagicMock())
sys.modules.setdefault("revenueholdings_license.rate_limiter", MagicMock())
sys.modules.setdefault("revenueholdings_license.license", MagicMock())
sys.modules.setdefault("revenueholdings_license.integration", MagicMock())
