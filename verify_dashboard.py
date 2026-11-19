"""Run with .venv/bin/python verify_dashboard.py; no browser required."""
from streamlit.testing.v1 import AppTest

app = AppTest.from_file('app.py').run()
assert not app.exception, app.exception
app.sidebar.radio[0].set_value('Fall dashboard').run()
assert not app.exception, app.exception
assert app.metric[1].value == '$2.00'
next(x for x in app.text_input if x.label.startswith('Actual energy (')).set_value('70').run()
assert app.metric[1].value == '$3.00'
next(x for x in app.text_input if x.label.startswith('Expected energy (')).set_value('').run()
assert len(app.metric) == 0 and app.warning
next(x for x in app.text_input if x.label.startswith('Actual energy (')).set_value('-1').run()
assert app.error and len(app.get('download_button')) == 0
for page in ['Assumptions', 'Energy & SCADA', 'Findings', 'Decisions', 'Work orders', 'Overview']:
    app.sidebar.radio[0].set_value(page).run()
    assert not app.exception, (page, app.exception)
print('PASS: Fall calculation behavior preserved; new overview, findings, decisions, work orders, assumptions and energy workspaces load.')
