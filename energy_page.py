"""Streamlit section; call render_energy_page() from the dashboard."""
import streamlit as st
from pathlib import Path
from baseline import read_intervals, align_intervals, value_shortfalls
from energy import compare_energy, export_results, demonstration_results


def render_energy_page():
    st.header('Interval energy comparison')
    st.write('Compare expected and actual energy for the same site or inverter and time interval. The downloaded meter exports do not contain an approved expected-generation baseline.')
    st.caption('Signed difference = expected − actual. Shortfall = max(0, signed difference). These are scenario estimates, not proof of a fault or recoverable energy.')
    mode = st.radio('Input mode', ['Synthetic demonstrations', 'Upload interval CSVs', 'Enter a documented interval'], key='energy_mode')
    if mode == 'Synthetic demonstrations':
        results = demonstration_results()
        st.info('All three examples below are synthetic and are not AAMU measurements.')
        st.dataframe(results, use_container_width=True)
        st.download_button('Download demonstration results', export_results(results), 'synthetic-energy-examples.csv', 'text/csv')
        financial_controls(results)
        return
    if mode == 'Upload interval CSVs':
        upload_intervals()
        return
    with st.form('energy_inputs'):
        asset = st.text_input('Site or inverter ID')
        start = st.text_input('Interval start (local ISO date/time)', '2026-10-28T00:00')
        end = st.text_input('Interval end (local ISO date/time)', '2026-10-29T00:00')
        timezone = st.text_input('Confirmed IANA timezone', placeholder='For example: America/Chicago')
        actual = st.text_input('Actual interval energy (kWh)')
        actual_source = st.text_input('Actual energy source and conversion method')
        expected = st.text_input('Expected interval energy (kWh); leave blank if unavailable')
        expected_source = st.text_input('Expected baseline source or reason unavailable')
        confirmed = st.checkbox('I confirmed that both values cover this asset, interval, timezone and kWh units.')
        submitted = st.form_submit_button('Calculate comparison')
    if submitted:
        st.session_state.pop('energy_result', None)
        if not confirmed:
            st.error('Confirm the comparison context before calculating.')
        else:
            base = dict(asset=asset, start=start, end=end, timezone=timezone, unit='kWh')
            try:
                st.session_state['energy_result'] = compare_energy(dict(base, energy_kwh=actual, source=actual_source), dict(base, energy_kwh=expected, source=expected_source))
            except (ValueError, KeyError) as exc:
                st.error(str(exc))
    result = st.session_state.get('energy_result')
    if result:
        st.caption('Last submitted calculation. Submit again after editing inputs.')
        if result['status'] == 'unavailable':
            st.warning(result['reason'])
        else:
            st.metric('Scenario energy shortfall', f"{result['shortfall_kwh']:,.2f} kWh")
            st.write(f"Signed difference: {result['signed_difference_kwh']:,.2f} kWh")
        st.dataframe([result], use_container_width=True)
        st.download_button('Download comparison and provenance', export_results([result]), 'energy-comparison.csv', 'text/csv')
        financial_controls([result])

# Dashboard entry point.
render = render_energy_page


def financial_controls(results):
    st.subheader('Tariff scenario')
    st.caption('Scenario value = nonnegative energy shortfall × tariff. This excludes demand charges, contracts, taxes, and recovery assumptions; it is not validated savings.')
    tariff = st.number_input('Tariff (USD/kWh)', min_value=0.0, value=0.10, step=0.01, format='%.4f')
    source = st.text_input('Tariff source', 'Illustrative demonstration assumption; not an approved site tariff')
    assumption = st.checkbox('Tariff is an assumption', value=True)
    try:
        valued = value_shortfalls(results, tariff, source, assumption)
    except ValueError as exc:
        st.error(str(exc))
        return
    st.dataframe(valued, use_container_width=True)
    available = [r['scenario_shortfall_value_usd'] for r in valued if r['scenario_shortfall_value_usd'] is not None]
    st.caption(f'{len(available)} of {len(valued)} intervals valued. Unavailable intervals remain blank; no complete-period loss total is implied.')
    st.download_button('Download tariff scenario', export_results(valued), 'energy-tariff-scenario.csv', 'text/csv')


def upload_intervals():
    st.write('Upload documented interval energy in kWh. Raw SCADA power or cumulative readings must first be converted using confirmed meter definitions. Exact asset, interval, timezone and units must match; no interpolation is performed.')
    root = Path(__file__).parent
    for name in ('sample-actual-energy.csv', 'sample-baseline.csv'):
        st.download_button('Download ' + name, (root/name).read_bytes(), name, 'text/csv')
    use_samples = st.checkbox('Load synthetic sample CSV pair', value=False)
    actual = st.file_uploader('Actual interval energy CSV', type='csv', key='actual_energy_upload')
    expected = st.file_uploader('Expected interval energy CSV (optional)', type='csv', key='expected_energy_upload')
    if use_samples:
        actual_data = (root/'sample-actual-energy.csv').read_bytes()
        expected_data = (root/'sample-baseline.csv').read_bytes()
        st.info('Synthetic sample files selected; uploaded files are not used in this mode.')
    elif actual:
        actual_data = actual.getvalue()
        expected_data = expected.getvalue() if expected else None
    else:
        st.info('Upload actual interval energy or load the synthetic pair to begin.')
        return
    try:
        actual_rows = read_intervals(actual_data)
        expected_rows = read_intervals(expected_data, expected=True) if expected_data else []
        results, coverage = align_intervals(actual_rows, expected_rows)
    except (ValueError, UnicodeError) as exc:
        st.error(str(exc))
        return
    st.write(coverage)
    st.caption('Coverage is the proportion of supplied actual intervals with usable matching expected values. It is not calendar or telemetry coverage; unequal interval lengths are not time weighted.')
    if coverage['unavailable_intervals'] or coverage['unmatched_baseline_intervals']:
        st.warning('Incomplete alignment: inspect missing expected values and unused baseline intervals before drawing conclusions.')
    st.dataframe(results, use_container_width=True)
    st.download_button('Download aligned energy results', export_results(results), 'aligned-energy-results.csv', 'text/csv')
    financial_controls(results)
