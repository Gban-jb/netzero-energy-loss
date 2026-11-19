"""Interactive investigation of one meter's timestamped observations."""
from pathlib import Path
import altair as alt
import pandas as pd
import streamlit as st
from scada_import import import_exports, coverage, TIME, POWER, ENERGY


def render():
    st.header('SCADA import and investigation')
    st.caption('Inspect observations, missing telemetry and source evidence. This view does not calculate generation or lost energy.')
    source = st.radio('Data source', ['Upload CSV exports', 'Use packaged synthetic meter samples'], key='scada_source')
    if source == 'Upload CSV exports':
        uploads = st.file_uploader('Exports from one physical meter', type='csv', accept_multiple_files=True, key='scada_uploads')
        files = [(u.name,u.getvalue()) for u in uploads]
        if not files:
            st.info('Upload one or more exports with DateTime, true power (kW), and accumulated energy (kWh) columns.')
            return
    else:
        sample_dir = Path(__file__).parent / 'sample-inputs' / '05-energy-scada'
        files = [(p.name, p.read_bytes()) for p in sorted(sample_dir.glob('UPLOAD-SCADA-*.csv'))]
        st.info('Synthetic sample meter: 5-minute cadence, one deliberate timestamp gap. These are not site measurements.')
    st.warning('Only combine exports known to describe the same meter. These files contain no meter ID or timezone. Negative power and flat readings need interpretation from the data owner.')
    cadence = st.selectbox('Nominal sampling interval (minutes)', [5,1,10,15,30,60], key='scada_cadence')
    try:
        frame, manifest, duplicates = import_exports(files)
        daily,gaps,aligned = coverage(frame,cadence)
    except ValueError as exc:
        st.error(str(exc)); return
    cols=st.columns(3)
    cols[0].metric('Unique observations',f'{len(frame):,}')
    cols[1].metric('Missing power readings',f'{int(frame[POWER].isna().sum()):,}')
    cols[2].metric('Absent timestamps in span',f'{int(daily.absent_timestamps.sum()):,}')
    if duplicates:
        st.info(f'{duplicates:,} identical duplicate rows merged; all source-row references retained. Conflicting duplicates stop import.')
    dates=st.date_input('Investigation date range', value=(frame[TIME].min().date(),frame[TIME].max().date()), min_value=frame[TIME].min().date(),max_value=frame[TIME].max().date(),key='scada_dates')
    if len(dates)!=2:
        st.info('Choose a start and end date.'); return
    mask=(aligned.index.date>=dates[0])&(aligned.index.date<=dates[1])
    selected=aligned.loc[mask].reset_index()
    st.subheader('Power observations and missing telemetry')
    # Separate contiguous valid runs so the line never bridges missing samples.
    selected['segment']=selected[POWER].isna().cumsum()
    line=alt.Chart(selected).mark_line().encode(x=alt.X(f'{TIME}:T',title='Timestamp as exported (timezone unconfirmed)'),y=alt.Y(field=POWER,type='quantitative',title='True power (kW)'),detail='segment:N',tooltip=[alt.Tooltip(field=TIME,type='temporal'),alt.Tooltip(field=POWER,type='quantitative'),alt.Tooltip(field='source_rows',type='nominal')]).transform_filter(alt.datum[POWER]!=None)
    missing=selected[selected[POWER].isna()][[TIME]].copy()
    missing['end']=missing[TIME]+pd.Timedelta(minutes=cadence)
    shade=alt.Chart(missing).mark_rect(opacity=.15,color='#db4a39').encode(x=f'{TIME}:T',x2='end:T')
    # Altair's row limit is avoided through explicit chart data records.
    with alt.data_transformers.enable('default',max_rows=None):
        st.altair_chart(shade+line,use_container_width=True)
    st.caption('Red shading marks missing or absent power samples. Gaps are not interpolated. Select a shorter range to inspect individual readings.')
    st.subheader('Accumulated register observations')
    register = selected.copy()
    register['register_segment'] = register[ENERGY].isna().cumsum()
    register_chart = alt.Chart(register).mark_line().encode(x=alt.X(field=TIME,type='temporal'), y=alt.Y(field=ENERGY,type='quantitative',scale=alt.Scale(zero=False),title='Accumulated register (kWh)'),detail='register_segment:N',tooltip=[alt.Tooltip(field=TIME,type='temporal'),alt.Tooltip(field=ENERGY,type='quantitative')]).transform_filter(alt.datum[ENERGY]!=None)
    with alt.data_transformers.enable('default',max_rows=None):
        st.altair_chart(register_chart,use_container_width=True)
    st.caption('Flat register periods are investigation targets; they do not by themselves prove plant downtime. Register values are not interval production totals.')
    st.subheader('Daily data coverage')
    chosen=daily[(daily.date>=str(dates[0]))&(daily.date<=str(dates[1]))]
    st.bar_chart(chosen.set_index('date')[['power_coverage_span_pct']])
    st.caption('Span coverage uses expected timestamps between the first and last imported observations. Full-day coverage uses the nominal samples per 24 hours; boundary days can be partial. Timezone/DST is not resolved.')
    st.dataframe(chosen,use_container_width=True)
    with st.expander('Timestamp gaps and source fingerprints'):
        st.dataframe(gaps,use_container_width=True); st.dataframe(manifest,use_container_width=True)
    with st.expander('Inspect selected readings and original source row references'):
        st.dataframe(selected.drop(columns=['segment']),use_container_width=True)
    for label,data,name in [('Selected readings',selected.drop(columns=['segment']),'scada-selected-readings.csv'),('Daily coverage',daily,'scada-daily-coverage.csv'),('Source manifest',manifest,'scada-source-manifest.csv'),('Timestamp gaps',gaps,'scada-timestamp-gaps.csv')]:
        st.download_button('Download '+label,data.to_csv(index=False),name,'text/csv',key='download_'+name)
