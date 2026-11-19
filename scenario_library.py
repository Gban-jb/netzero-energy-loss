"""Local SQLite scenario persistence for the single-user solar console."""
from pathlib import Path
import sqlite3
import json
from datetime import datetime, timezone
import streamlit as st

DEFAULTS = {'farm_tariff': .12, 'farm_persist': 1.0, 'farm_replace': 325.0, 'farm_wait': 6}
DB = Path(__file__).parent / 'local-data' / 'scenarios.sqlite3'


def connect():
    DB.parent.mkdir(exist_ok=True)
    connection = sqlite3.connect(DB)
    connection.execute('CREATE TABLE IF NOT EXISTS scenarios (id INTEGER PRIMARY KEY, name TEXT NOT NULL, created TEXT NOT NULL, payload TEXT NOT NULL)')
    return connection


def render():
    st.title('Your saved scenarios')
    st.caption('Save a set of assumptions, reopen it later, and compare the effect of your decisions. Stored on the app server. On a shared demo, saved scenarios are visible to other visitors. Download JSON to keep a copy; server storage may reset.')
    with st.form('save_scenario'):
        name = st.text_input('Scenario name', placeholder='Example: Higher electricity price, six-month wait', max_chars=100)
        st.write('Current assumptions', {k.replace('farm_', ''): st.session_state.get(k,v) for k,v in DEFAULTS.items()})
        save = st.form_submit_button('Save current scenario', type='primary')
    if save:
        if not name.strip():
            st.error('Give this scenario a name so you can find it later.')
        else:
            payload = {k: st.session_state.get(k,v) for k,v in DEFAULTS.items()}
            with connect() as db:
                db.execute('INSERT INTO scenarios(name,created,payload) VALUES(?,?,?)', (name.strip(),datetime.now(timezone.utc).isoformat(),json.dumps(payload)))
            st.success('Scenario saved on the app server.')
    with connect() as db:
        rows = db.execute('SELECT id,name,created,payload FROM scenarios ORDER BY id DESC').fetchall()
    if not rows:
        st.info('Your library is empty. Save the current assumptions to create your first scenario.')
    for identity,name,created,payload in rows:
        with st.container(border=True):
            st.subheader(name)
            st.caption('Saved '+created[:16].replace('T',' ')+' UTC · Synthetic assumptions')
            values=json.loads(payload)
            st.write(f"Electricity price ${values['farm_tariff']:.3f}/kWh · Monthly loss growth {values['farm_persist']:g}% · Replacement ${values['farm_replace']:g} · Wait {values['farm_wait']} months")
            if st.button('Use this scenario',key=f'load_{identity}'):
                st.session_state.update(values)
                st.success('Loaded. Open Overview or Decisions to see the results.')
            st.download_button('Download assumptions JSON',json.dumps(values,indent=2),f'solar-scenario-{identity}.json','application/json',key=f'dl_{identity}')
