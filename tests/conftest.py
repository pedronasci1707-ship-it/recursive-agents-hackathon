import os
import tempfile

# Tests use a throwaway product database, never data/campusloop.db.
os.environ.setdefault("CAMPUSLOOP_DB", os.path.join(tempfile.mkdtemp(), "test.db"))
