"""UI checks for Student 3 Task 5, without a browser."""
from streamlit.testing.v1 import AppTest

app=AppTest.from_file('app.py').run()
app.sidebar.radio[0].set_value('Maintenance options').run()
assert not app.exception, app.exception
rows=app.dataframe[-1].value
assert list(rows['action']) == ['inspect','clean','repair','replace','wait']
assert rows.iloc[1]['priced_action_cost_usd'] == 82
assert any('Replace: missing downtime_hours' in w.value for w in app.warning)
next(x for x in app.text_input if x.label.startswith('Labor rate (')).set_value('30').run()
assert not app.exception
assert app.dataframe[-1].value.iloc[1]['priced_action_cost_usd'] == 92
next(x for x in app.text_input if x.label.startswith('Downtime valuation (')).set_value('').run()
assert any('Clean: missing downtime_rate' in w.value for w in app.warning)
assert len(app.get('download_button')) == 2
next(x for x in app.text_input if x.label.startswith('Labor rate (')).set_value('-1').run()
assert app.error and len(app.get('download_button')) == 0
print('PASS: Maintenance comparison behavior preserved in redesigned console shell.')
