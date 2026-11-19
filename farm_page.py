"""Overview, findings, decisions and work-order screens for the synthetic array."""
from collections import Counter
import pandas as pd
import plotly.express as px
import streamlit as st

from synthetic_farm import generate_panels, estimate, export_findings
from ui_components import hero, card

COLORS = {'Critical':'#D96A5F','High':'#E6A15B','Medium':'#E8D17D','Low':'#71B6A1','Healthy':'#829087'}


def _scenario():
    with st.sidebar:
        st.markdown('### Explore a what-if')
        tariff = st.number_input('Electricity price · $/kWh', min_value=0.0, value=None, step=.01, format='%.3f', key='farm_tariff')
        persistence = st.number_input('How quickly loss grows each month · %', min_value=0.0, value=None, step=.5, key='farm_persist')
        replacement = st.number_input('Replacement action · $/panel', min_value=0.0, value=None, step=25.0, key='farm_replace')
        wait = st.select_slider('Wait period · months', [1,3,6,12], value=None, key='farm_wait')
        st.button('Electricity price +15%', use_container_width=True, on_click=lambda: st.session_state.update(farm_tariff=round(st.session_state['farm_tariff'] * 1.15, 4)))
    panels = generate_panels()
    results = [estimate(p, tariff, persistence, replacement, wait) for p in panels]
    return panels, results, tariff, persistence, replacement, wait


def _work(results):
    findings = [r for r in results if r['severity'] != 'Healthy']
    return sorted(findings, key=lambda r:(-r['priority_score'],r['panel_id']))


def _metrics(results):
    findings = _work(results)
    at_risk = sum(r['horizon_scenarios'][6]['energy_at_risk_kwh'] or 0 for r in findings)
    urgent = sum(r['due_window'] == 'Now' for r in findings)
    cols = st.columns(4)
    cols[0].metric('Panels in this demo',f'{len(results):,}')
    cols[1].metric('Panels with an issue',str(len(findings)))
    cols[2].metric('Need prompt inspection',str(urgent))
    cols[3].metric('6-month loss · partial estimate',f'{at_risk:,.1f} kWh')
    st.caption('Estimates cover 6 of 8 flagged panels. Two panels lack required inputs; their losses are unknown.')


def _fig_layout(fig, height=350):
    fig.update_layout(height=height, margin=dict(l=8,r=8,t=18,b=8), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                      font=dict(family='DM Sans, sans-serif',color='#ADB7AD'), legend_title_text='',
                      xaxis=dict(gridcolor='rgba(173,183,173,.12)',zerolinecolor='rgba(173,183,173,.12)'),
                      yaxis=dict(gridcolor='rgba(173,183,173,.12)',zerolinecolor='rgba(173,183,173,.12)'))
    return fig


def _map(results, selection_key='farm_panel'):
    grid = pd.DataFrame(results)
    fig = px.scatter(grid,x='column',y='row',color='severity',hover_name='panel_id',custom_data=['panel_id'],
                     hover_data={'fault_type':True,'inverter_id':True,'due_window':True,'column':False,'row':False},
                     color_discrete_map=COLORS,category_orders={'severity':['Critical','High','Medium','Low','Healthy']})
    fig.update_traces(marker={'size':23,'symbol':'square','line':{'width':1.2,'color':'#111713'}})
    fig.update_layout(yaxis=dict(autorange='reversed',dtick=1,title='Array row'),xaxis=dict(dtick=1,title='Column'),legend_title='Finding',clickmode='event+select')
    chart_state=st.plotly_chart(_fig_layout(fig,440),use_container_width=True,key='farm_grid',on_select='rerun',selection_mode='points',
                               config={'displayModeBar':False},alt='Synthetic solar array schematic. Each square is one panel, colored by labeled severity.')
    if chart_state and chart_state.selection.points:
        point=chart_state.selection.points[0]
        identity = point.get('customdata', [None])[0]
        if identity in {r['panel_id'] for r in results} and identity != st.session_state.get('last_map_selection'):
            st.session_state[selection_key] = identity
            st.session_state['last_map_selection'] = identity
    st.caption('Click a panel square to open its details below. This is a schematic layout, not GPS or drone imagery. Severity is labeled as well as color-coded.')


def _detail(results, selected_id):
    selected = next(r for r in results if r['panel_id']==selected_id)
    st.markdown('### What is happening with this panel?')
    a,b,c = st.columns(3)
    a.metric('Finding',selected['fault_type'])
    b.metric('Severity',selected['severity'])
    c.metric('Suggested timing',selected['due_window'])
    st.markdown(f"**{selected['panel_id']}** · Row {selected['row']}, column {selected['column']} · {selected['string_id']} · {selected['inverter_id']}")
    left,right = st.columns([1,1])
    with left:
        st.markdown(f"**Why it was flagged:** {selected['priority_reason']}")
        loss_w = 'unavailable' if selected['current_loss_w'] is None else f"{selected['current_loss_w']:.0f} W"
        st.markdown(f"**Estimated output today:** {selected['current_loss_pct']:.0f}% lower than the healthy-panel scenario ({loss_w})")
        with st.expander('What do the evidence numbers mean?'):
            st.write(f"Synthetic temperature difference: **{selected['delta_t_c']:.1f} °C**. The generated sample assigns **{selected['affected_area_pct']:.0f}%** affected panel area. These are example values, not readings from a thermal image.")
        st.caption(f"Warranty: {selected['warranty_status']} · Inspection: {selected['inspection_date']}")
        if not selected['data_complete']:
            st.warning('Some synthetic metadata is missing. Verify before relying on the estimate.')
    with right:
        rows=[]
        for month,scenario in selected['horizon_scenarios'].items():
            rows.append({'Horizon':f'{month} months','Energy at risk': 'Unavailable' if scenario['energy_at_risk_kwh'] is None else f"{scenario['energy_at_risk_kwh']:.2f} kWh",'Tariff exposure':'Unavailable' if scenario['tariff_exposure_usd'] is None else f"${scenario['tariff_exposure_usd']:.2f}"})
        st.dataframe(pd.DataFrame(rows),hide_index=True,use_container_width=True)
    _damage_story(selected)
    st.caption('Rule-based scenario only: rated power × assigned synthetic loss; 4.5 peak-sun-hours/day; editable monthly persistence. Not a trained forecast.')


def _damage_story(selected):
    if selected['severity'] == 'Healthy':
        st.success('No issue is assigned to this panel. Continue routine monitoring; this demo does not suggest replacement.')
        return
    st.markdown('#### If we wait: what could happen?')
    if selected['current_loss_w'] is None:
        st.warning('Time-to-threshold and waiting cost are unavailable because required synthetic production inputs are missing.')
        return
    threshold = selected['critical_loss_threshold_pct']
    if selected['threshold_months'] == 0:
        st.error(f"Scenario threshold already met: current estimated loss is {selected['current_loss_pct']:.0f}% versus a {threshold:.0f}% scenario threshold.")
    elif selected['threshold_months'] is None:
        st.info(f"This persistence scenario does not reach the {threshold:.0f}% loss threshold within 12 months.")
    else:
        st.warning(f"Under this scenario, output loss could reach the {threshold:.0f}% high-loss marker in about {selected['threshold_months']} months.")
    months = [0,1,3,6,12]
    base_loss = selected['current_loss_pct']
    persistence = selected['persistence_pct_per_month']
    points=[]
    for m in months:
        loss = base_loss * (1 + persistence/100)**m
        points.append({'Month':m,'Scenario loss (%)':loss,'Threshold (%)':threshold})
    df=pd.DataFrame(points)
    fig=px.line(df,x='Month',y=['Scenario loss (%)','Threshold (%)'],markers=True,
                color_discrete_sequence=['#E6A15B','#D96A5F'])
    fig.update_layout(xaxis=dict(tickmode='array',tickvals=months),yaxis=dict(title='Estimated loss · %',range=[0,max(45,threshold+5)]),legend_title='Scenario line')
    st.plotly_chart(_fig_layout(fig,270),use_container_width=True)
    st.caption('Amber line = this scenario’s estimated output loss. Red line = user-set high-loss marker. The marker is a planning threshold, not a failure date.')
    horizon=selected['horizon_scenarios'][selected['wait_months']]
    exposure=horizon['tariff_exposure_usd']
    delta=selected['wait_plus_replacement_usd']
    c1,c2,c3=st.columns(3)
    c1.metric(f"Wait exposure · {selected['wait_months']} mo",'Unavailable' if exposure is None else f'${exposure:,.2f}')
    c2.metric('Replace scenario cost',f"${selected['act_now_cost_usd']:,.2f}")
    c3.metric('Wait + later replacement','Unavailable' if delta is None else f'${delta:,.2f}')
    st.markdown('**Plain-language read:** the waiting amount estimates the value of energy this panel might not produce before the selected date. The “wait + replace” amount adds the assumed replacement expense afterward.')
    st.caption('Scenario only. Does not include repair recovery, weather variation, downtime valuation, contract terms, or forecast uncertainty.')


def render_overview():
    panels,results,tariff,persistence,replacement,wait = _scenario()
    findings = _work(results)
    urgent = [r for r in findings if r['due_window']=='Now']
    headline = f"{len(urgent)} panels need prompt inspection" if urgent else 'No urgent rule flags in this scenario'
    hero('North Field · Solar operations',headline,
         'Find the panels that need attention. Explore how much energy could be lost while you wait.',
         'SYNTHETIC DATA')
    st.write('')
    _metrics(results)
    left,right = st.columns([1.55,1],gap='large')
    with left:
        with st.container(border=True):
            st.markdown('### Array health')
            st.caption('Each square is one generated panel. Select a panel below for its scenario detail.')
            _map(results)
    with right:
        with st.container(border=True):
            st.markdown('### Attention now')
            if urgent:
                for item in urgent:
                    st.markdown(f"**{item['panel_id']}** · :red[{item['severity']}]  \n{item['fault_type']} · {item['priority_reason']}")
                    st.divider()
            else:
                st.success('No panels meet the current urgent rule.')
            st.markdown('**Next:** review evidence and confirm the scenario assumptions before scheduling work.')
            st.caption(f'Tariff ${tariff:.3f}/kWh · {persistence:.1f}% monthly persistence · {wait}-month wait')
    with st.container(border=True):
        st.markdown('### Scenario outlook')
        _scenario_chart(findings)
    with st.container(border=True):
        st.markdown('### Compare acting with waiting')
        _decision_cards(findings,replacement,wait)
    ids=[r['panel_id'] for r in findings] + [r['panel_id'] for r in results if r['severity']=='Healthy']
    selected=st.selectbox('Open a panel detail',ids,key='farm_panel')
    with st.container(border=True): _detail(results,selected)
    st.warning('All findings, thermal differences, energy losses, and costs on this screen are generated demonstration values. They are not field measurements, diagnoses, or guaranteed savings.')


def _scenario_chart(findings):
    data=[]
    for months in (1,3,6,12):
        kwh=sum(r['horizon_scenarios'][months]['energy_at_risk_kwh'] or 0 for r in findings)
        usd=sum(r['horizon_scenarios'][months]['tariff_exposure_usd'] or 0 for r in findings)
        data.append({'Months':months,'Energy at risk (kWh)':kwh,'Tariff exposure ($)':usd})
    df=pd.DataFrame(data)
    fig=px.line(df,x='Months',y='Energy at risk (kWh)',markers=True)
    fig.update_traces(line_color='#E6A15B',line_width=3,marker_size=10,hovertemplate='%{x} months<br>%{y:.1f} kWh<extra></extra>')
    fig.update_layout(xaxis=dict(tickmode='array',tickvals=[1,3,6,12]),yaxis_title='Energy at risk · kWh')
    st.plotly_chart(_fig_layout(fig,290),use_container_width=True)
    with st.expander('See the numbers behind this chart'):
        st.dataframe(df,hide_index=True,use_container_width=True)
    st.caption('Partial estimate: panels without the required inputs are excluded. Missing values are not zero losses.')


def _decision_cards(findings,replacement,wait):
    exposure=sum(r['horizon_scenarios'][wait]['tariff_exposure_usd'] or 0 for r in findings)
    action_cost=replacement*len(findings)
    a,b=st.columns(2)
    with a:
        card('Act now',f'<div style="font-size:1.8rem;font-weight:800;color:#F4F2E9">${action_cost:,.0f}</div><div class="muted-small">Scenario replacement cost for {len(findings)} findings</div>', 'Flat synthetic cost per panel; excludes other costs.')
    with b:
        card(f'Wait {wait} months',f'<div style="font-size:1.8rem;font-weight:800;color:#F1C27D">${exposure:,.0f}</div><div class="muted-small">Estimated tariff exposure during the wait</div>', 'Exposure is not a bill or guaranteed loss; later action cost is additional.')


def render_findings():
    _,results,*_=_scenario()
    hero('Asset inspection','Findings explorer','Filter the synthetic inspection set, then open a panel to see the generated evidence and scenario assumptions.','SYNTHETIC DATA')
    rows=[r for r in results if r['severity']!='Healthy']
    a,b,c,d=st.columns([1.4,1,1,1])
    search=a.text_input('Search panel ID',key='find_search')
    severity=b.selectbox('Severity',['All','Critical','High','Medium','Low'],key='find_severity')
    fault=c.selectbox('Finding type',['All']+sorted({r['fault_type'] for r in rows}),key='find_fault')
    inverter=d.selectbox('Inverter',['All']+sorted({r['inverter_id'] for r in rows}),key='find_inverter')
    filtered=[r for r in rows if (not search or search.lower() in r['panel_id'].lower()) and (severity=='All' or r['severity']==severity) and (fault=='All' or r['fault_type']==fault) and (inverter=='All' or r['inverter_id']==inverter)]
    st.caption(f'Showing {len(filtered)} of {len(rows)} generated findings. Healthy panels are hidden by default.')
    view=pd.DataFrame([{'Panel':r['panel_id'],'Severity':r['severity'],'Finding':r['fault_type'],'Scenario loss':f"{r['current_loss_pct']:.0f}%",'Synthetic ΔT':f"{r['delta_t_c']:.1f} °C",'Timing':r['due_window'],'Data quality':'Check' if not r['data_complete'] else 'Complete','Reason':r['priority_reason']} for r in filtered])
    st.dataframe(view,hide_index=True,use_container_width=True)
    if filtered:
        selected=st.selectbox('Open finding', [r['panel_id'] for r in filtered],key='finding_detail')
        with st.container(border=True): _detail(results,selected)
        st.download_button('Export filtered findings CSV',export_findings(filtered),'solar-findings.csv','text/csv',type='primary')
    else: st.info('No findings match these filters. Try clearing a filter.')


def render_decisions():
    _,results,tariff,persistence,replacement,wait=_scenario()
    findings=_work(results)
    hero('Maintenance planning','Compare the cost of action and waiting','Adjust the scenario controls in the left rail. Outputs update immediately and retain the synthetic-data label.','ILLUSTRATIVE SCENARIO')
    st.markdown('### Shared assumptions')
    x,y,z=st.columns(3)
    x.metric('Electricity price',f'${tariff:.3f}/kWh')
    y.metric('Monthly persistence',f'{persistence:.1f}%')
    z.metric('Wait period',f'{wait} months')
    _decision_cards(findings,replacement,wait)
    st.markdown('### Sensitivity: current price vs. +15%')
    horizons=[]
    for months in (1,3,6,12):
        kwh=sum(r['horizon_scenarios'][months]['energy_at_risk_kwh'] or 0 for r in findings)
        horizons.append({'Months':months,'Current tariff ($)':kwh*tariff,'Tariff +15% ($)':kwh*tariff*1.15})
    df=pd.DataFrame(horizons)
    fig=px.line(df,x='Months',y=['Current tariff ($)','Tariff +15% ($)'],markers=True,color_discrete_sequence=['#71B6A1','#E6A15B'])
    fig.update_layout(xaxis=dict(tickmode='array',tickvals=[1,3,6,12]),yaxis_title='Scenario exposure · USD',legend_title='Price scenario')
    st.plotly_chart(_fig_layout(fig,340),use_container_width=True)
    st.dataframe(df,hide_index=True,use_container_width=True)
    st.info('Current break-even estimate uses replacement cost divided by current monthly tariff exposure. It does not model repair effectiveness, avoided failure, changing weather, or uncertainty; therefore it is not an engineering recommendation.')
    st.download_button('Export decision scenarios CSV',df.to_csv(index=False),'solar-decision-scenarios.csv','text/csv')


def render_work_orders():
    _,results,*_=_scenario()
    work=_work(results)
    hero('Maintenance queue','Prioritized work orders','The visible order follows documented deterministic severity, safety, data-completeness, and loss rules. Use the reason to understand each position.','RULE-BASED')
    timing=st.multiselect('Due window',['Now','Within 3 months','Within 6 months','Monitor'],default=['Now','Within 3 months','Within 6 months'],key='work_timing')
    filtered=[r for r in work if r['due_window'] in timing]
    st.metric('Items in current queue',len(filtered),f'{sum(r["safety_flag"] for r in filtered)} safety flags')
    table=pd.DataFrame([{'Priority':i,'Panel':r['panel_id'],'Action':'Inspect promptly' if r['safety_flag'] else ('Review '+r['fault_type'].lower()),'Finding':r['fault_type'],'Severity':r['severity'],'Due':r['due_window'],'Scenario loss':f"{r['current_loss_pct']:.0f}%",'Data status':'Verify' if not r['data_complete'] else 'Complete','Why this rank':r['priority_reason']} for i,r in enumerate(filtered,1)])
    st.dataframe(table,hide_index=True,use_container_width=True)
    st.download_button('Download work orders CSV',export_findings(filtered),'solar-work-orders.csv','text/csv',type='primary')
    st.caption('Rank order is a prototype rule, not a certified maintenance prescription. Safety-related synthetic flags remain visible if financial inputs are unavailable.')
