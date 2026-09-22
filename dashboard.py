"""Old entry point, kept so `streamlit run dashboard.py` still works. The real front page is Trading_Desk.py."""
import runpy
import os

runpy.run_path(os.path.join(os.path.dirname(os.path.abspath(__file__)), "Trading_Desk.py"), run_name="__main__")
