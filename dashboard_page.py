"""Combined Fall milestone: inputs, calculated outputs, persistence and export."""
import hashlib
from pathlib import Path
import streamlit as st
import scenario
from ui_components import hero


def render():
    hero('Integrated energy workflow','Fall dashboard','Edit a site or inverter interval, update assumptions, and export a traceable scenario result.','LEGACY WORKSPACE')
    st.caption('Shortfall = max(0, expected − actual). Scenario dollar value = shortfall × tariff. Values are estimates, not validated savings. Maintenance inputs are recorded for later comparisons; they are not added to energy loss.')
    uploaded = st.file_uploader('Open complete scenario JSON', type='json', key='complete_upload')
    raw = uploaded.getvalue() if uploaded else Path(__file__).with_name('sample-complete-scenario.json').read_bytes()
    try:
        original = scenario.loads(raw)
    except ValueError as exc:
        st.error(str(exc))
        return
    token = hashlib.sha256(raw).hexdigest()
    st.info('The default scenario is synthetic. Replace its values and source descriptions before using approved site inputs.')
    costs = st.data_editor(original['costs'], num_rows='fixed', disabled=['parameter', 'unit'], key='combined_costs_' + token)
    st.subheader('Interval inputs')
    a, e = original['actual'], original['expected']
    values = {}
    for field, label in [('asset', 'Site or inverter ID'), ('start', 'Interval start (local ISO)'), ('end', 'Interval end (local ISO)'), ('timezone', 'IANA timezone')]:
        values[field] = st.text_input(label, a[field], key='combined_' + field + token)
    actual = st.text_input('Actual energy (kWh)', str(a['energy_kwh']), key='combined_actual' + token)
    expected = st.text_input('Expected energy (kWh); blank means unavailable', '' if e['energy_kwh'] is None else str(e['energy_kwh']), key='combined_expected' + token)
    actual_source = st.text_input('Actual energy source', a['source'], key='combined_actual_source' + token)
    expected_source = st.text_input('Expected baseline source or reason unavailable', e['source'], key='combined_expected_source' + token)
    st.caption('Both energy values must cover the displayed asset, interval, timezone and kWh units. Raw power and cumulative meter readings are not interval energy.')
    base = dict(values, unit='kWh')
    payload = dict(schema_version=1, costs=costs,
                   actual=dict(base, energy_kwh=actual, source=actual_source),
                   expected=dict(base, energy_kwh=expected, source=expected_source))
    try:
        result = scenario.calculate(payload)
        saved = scenario.dumps(payload)
        exported = scenario.export_csv(payload)
    except ValueError as exc:
        st.error(str(exc))
        return
    st.subheader('Scenario outputs')
    if result['status'] == 'unavailable':
        st.warning('Expected generation is missing. Energy shortfall and dollar value are unavailable, not zero.')
    else:
        left, right = st.columns(2)
        left.metric('Energy shortfall', f"{result['shortfall_kwh']:,.2f} kWh")
        right.metric('Scenario dollar value', f"${result['scenario_shortfall_value_usd']:,.2f}")
        st.write(f"{result['shortfall_kwh']:g} kWh × ${result['tariff_usd_per_kwh']:g}/kWh = ${result['scenario_shortfall_value_usd']:g}")
    st.dataframe([result], use_container_width=True)
    st.download_button('Save complete scenario JSON', saved, 'complete-scenario.json', 'application/json')
    st.download_button('Download traceable result CSV', exported, 'complete-scenario-result.csv', 'text/csv')
    st.caption('JSON restores all cost and interval inputs. CSV includes sources, assumption flags, the formula and a SHA-256 fingerprint of the saved scenario. Invalid inputs block both downloads.')
