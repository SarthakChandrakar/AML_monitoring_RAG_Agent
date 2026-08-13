"""Top-level launcher for AML Monitoring RAG Agent Streamlit App.

Can be run via:
    streamlit run app.py
or:
    streamlit run ui/app.py
"""

import runpy
from pathlib import Path

ui_app = Path(__file__).resolve().parent / "ui" / "app.py"
runpy.run_path(str(ui_app), run_name="__main__")
