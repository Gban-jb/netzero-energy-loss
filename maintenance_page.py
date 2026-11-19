"""Student 3 Task 5: editable maintenance option comparison."""
from pathlib import Path
import hashlib
import streamlit as st
import maintenance
from ui_components import hero


def render():
    hero('Maintenance planning','Maintenance option comparison','Compare inspect, clean, repair, replace, and wait costs for one asset scenario.','COST SCENARIO')
    st.info('Synthetic starting values. Direct costs must exclude labor and downtime charges, which are added separately. Enter an explicit zero for no cost or duration; leave unknown values blank.')
    st.warning('This table does not rank actions or estimate savings. Ongoing production loss, future maintenance, recovery effectiveness and benefits are excluded. A zero immediate wait cost does not mean waiting is free over time.')
    uploaded = st.file_uploader('Open maintenance scenario JSON', type='json', key='maintenance_upload')
    raw = uploaded.getvalue() if uploaded else Path(__file__).with_name('sample-maintenance-scenario.json').read_bytes()
    try:
        p = maintenance.loads(raw)
    except ValueError as exc:
        st.error(str(exc))
        return
    key = hashlib.sha256(raw).hexdigest()
    p['scenario'] = st.text_input('Maintenance scenario name', p['scenario'], key='maintenance_name' + key)
    p['asset'] = st.text_input('Maintenance site or inverter ID', p['asset'], key='maintenance_asset' + key)
    for field, label in [('labor_rate', 'Labor rate'), ('downtime_rate', 'Downtime valuation')]:
        rate = p[field]
        rate['value'] = st.text_input(label + ' (USD/hour); blank if unknown', '' if rate['value'] is None else str(rate['value']), key=field + key)
        rate['source'] = st.text_input(label + ' source / assumption basis', rate['source'], key=field + '_source' + key)
        rate['is_assumption'] = 'true' if st.checkbox(label + ' is an assumption', rate['is_assumption'] == 'true', key=field + '_assumption' + key) else 'false'
    st.caption('Downtime valuation is a documented USD per hour estimate for the affected asset during the action, not a tariff in USD/kWh. Use zero only when no downtime cost is expected.')
    rows = [{**r, **{f:'' if r[f] is None else str(r[f]) for f in ('direct_cost_usd', 'labor_hours', 'downtime_hours')}} for r in p['options']]
    p['options'] = st.data_editor(rows, num_rows='fixed', disabled=['action'], key='maintenance_options' + key)
    try:
        results = maintenance.compare(p)
        saved = maintenance.dumps(p)
        exported = maintenance.export_csv(p)
    except ValueError as exc:
        st.error(str(exc))
        return
    st.subheader('Action cost table')
    st.caption('Priced action cost = direct cost + labor hours × labor rate + downtime hours × downtime valuation.')
    st.dataframe([{k:r[k] for k in ('action', 'direct_cost_usd', 'labor_cost_usd', 'downtime_cost_usd', 'priced_action_cost_usd', 'status', 'missing_inputs')} for r in results], use_container_width=True)
    for r in results:
        if r['missing_inputs']:
            st.warning(f"{r['action'].title()}: missing {r['missing_inputs']}. " + ('Total is unavailable.' if r['priced_action_cost_usd'] is None else 'An explicit zero makes the affected cost component zero.'))
    st.download_button('Save maintenance scenario JSON', saved, 'maintenance-scenario.json', 'application/json')
    st.download_button('Download maintenance comparison CSV', exported, 'maintenance-comparison.csv', 'text/csv')
    st.caption('The export preserves all input values, sources, assumption flags, missing-data warnings and the scenario fingerprint. Unavailable numeric results are blank.')
