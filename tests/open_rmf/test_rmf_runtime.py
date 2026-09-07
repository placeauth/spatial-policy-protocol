"""Optional real Humble bid path; run with a packaged traffic schedule node."""
import os
from pathlib import Path
import runpy
import sys

import pytest


def test_real_delivery_gating():
    if os.environ.get('SPP_RMF_RUNTIME') != '1':
        pytest.skip('Set SPP_RMF_RUNTIME=1 in the documented Humble environment')
    root = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(root / 'reference/admission/src'))
    runpy.run_path(str(root / 'tests/open_rmf/runtime_fixture.py'), run_name='__main__')
