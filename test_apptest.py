import os

from streamlit.testing.v1 import AppTest

os.environ.setdefault("ALGOBOT_PASSWORD", "open-sesame")

at = AppTest.from_file("pages/1_Position_size.py")
at.run()
at.text_input(key="ab_pw").set_value("open-sesame")
at.button(key="ab_login_btn").click().run()

for m in at.markdown:
    print(m.value)
