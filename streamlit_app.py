"""Entry point for Streamlit Community Cloud.

Streamlit Cloud looks for `streamlit_app.py` at the repository root by
default. The dashboard itself lives in `app.py`; this file only runs it,
so the app deploys without anyone having to set a custom main file path.

Running `streamlit run app.py` locally still works exactly as before.
"""

import runpy
from pathlib import Path

runpy.run_path(str(Path(__file__).parent / "app.py"), run_name="__main__")
