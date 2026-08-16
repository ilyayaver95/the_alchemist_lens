"""Test-wide environment.

`app.db` builds its engine at import time from DATABASE_URL, so this has to run
before anything imports the app — hence module level in conftest rather than a
fixture. Without it, `create_app()` would write alchemist.db into the repo.
"""

import os
import tempfile

_TMP_DIR = tempfile.mkdtemp(prefix="alchemist-tests-")
os.environ.setdefault("DATABASE_URL", f"sqlite:///{_TMP_DIR}/test.db")
os.environ.setdefault("VISION_PROVIDER", "fake")
os.environ.setdefault("JWT_SECRET", "test-secret")
