"""Deterministic synthetic solar-farm dataset and transparent scenario rules.

All panel-level outputs are illustrative. They are not image diagnoses or validated forecasts.
"""
from __future__ import annotations

import csv
import io
import math
import random

SEED = 20261118
HORIZONS = (1, 3, 6, 12)
FAULTS = ('Hotspot', 'Soiling', 'Shading', 'Glass damage', 'Open circuit')
SEVERITY_ORDER = {'Critical': 0, 'High': 1, 'Medium': 2, 'Low': 3, 'Healthy': 4}


def generate_panels(rows: int = 8, columns: int = 12) -> list[dict]:
    """Generate a stable synthetic array containing varied findings and missing data."""
    rng = random.Random(SEED)
    panels = []
    faults = [
        ('Hotspot', 'Critical', 24.0, 0.22, 0.22, True),
        ('Hotspot', 'High', 15.0, 0.16, 0.14, False),
        ('Soiling', 'Medium', 2.0, 0.12, 0.08, False),
        ('Shading', 'High', 1.0, 0.25, 0.18, False),
        ('Glass damage', 'Medium', 4.0, 0.10, 0.11, False),
        ('Open circuit', 'Critical', -5.0, 1.0, 0.35, True),
        ('Soiling', 'Low', 1.0, 0.05, 0.04, False),
        ('Hotspot', 'Medium', 8.0, 0.10, 0.10, False),
    ]
    fault_indices = {3, 18, 29, 47, 63, 71, 84, 95}
    for idx in range(rows * columns):
        row, col = divmod(idx, columns)
        inverter = f'INV-{row // 2 + 1:02d}'
        string = f'{inverter}-S{row % 2 + 1:02d}-{col // 4 + 1:02d}'
        record = {
            'panel_id': f'PNL-{row + 1:02d}-{col + 1:02d}',
            'row': row + 1,
            'column': col + 1,
            'string_id': string,
            'inverter_id': inverter,
            'rated_w': 550,
            'install_date': '2022-06-15',
            'warranty_status': 'Synthetic · active',
            'fault_type': 'Healthy',
            'severity': 'Healthy',
            'delta_t_c': round(rng.uniform(-0.7, 0.7), 1),
            'affected_area_pct': 0.0,
            'current_loss_pct': 0.0,
            'safety_flag': False,
            'inspection_date': '2026-10-30',
            'irradiance_w_m2': 820,
            'ambient_temp_c': 28,
            'wind_m_s': 2.4,
            'data_complete': True,
            'source': 'Deterministic synthetic demonstration data',
            'is_synthetic': True,
        }
        if idx in fault_indices:
            fault, severity, delta, affected, loss, safety = faults[list(sorted(fault_indices)).index(idx)]
            record.update(fault_type=fault, severity=severity, delta_t_c=delta,
                          affected_area_pct=affected * 100, current_loss_pct=loss * 100,
                          safety_flag=safety)
        if idx in (18, 47):
            record['irradiance_w_m2'] = None
            record['data_complete'] = False
        if idx == 71:
            record['warranty_status'] = 'Unknown'
            record['data_complete'] = False
        panels.append(record)
    return panels


def estimate(panel: dict, tariff: float, persistence_pct_per_month: float,
             replacement_cost: float, wait_months: int = 6,
             critical_loss_pct: float = 40.0) -> dict:
    """Return transparent scenario estimates; missing rated inputs stay unavailable."""
    if not math.isfinite(tariff) or tariff < 0:
        raise ValueError('Tariff must be a finite, nonnegative value.')
    if not math.isfinite(persistence_pct_per_month) or persistence_pct_per_month < 0:
        raise ValueError('Loss persistence must be a finite, nonnegative value.')
    if not math.isfinite(replacement_cost) or replacement_cost < 0:
        raise ValueError('Replacement cost must be a finite, nonnegative value.')
    if not math.isfinite(critical_loss_pct) or critical_loss_pct <= 0 or critical_loss_pct > 100:
        raise ValueError('Critical loss threshold must be above 0% and at most 100%.')
    wait_months = max(1, min(12, int(wait_months)))
    if panel.get('irradiance_w_m2') is None or panel.get('rated_w') is None or panel.get('current_loss_pct') is None:
        current_loss_w = current_daily_kwh = None
    else:
        current_loss_w = panel['rated_w'] * panel['current_loss_pct'] / 100
        # Demo convention: 4.5 peak-sun-hours/day, 30 days/month.
        current_daily_kwh = current_loss_w / 1000 * 4.5
    result = dict(panel)
    result['current_loss_w'] = current_loss_w
    result['persistence_pct_per_month'] = persistence_pct_per_month
    result['critical_loss_threshold_pct'] = critical_loss_pct
    result['threshold_months'] = None
    result['threshold_status'] = 'Insufficient data' if current_loss_w is None else 'Not reached in 12-month scenario'
    if current_loss_w is not None:
        current_pct = float(panel['current_loss_pct'])
        if current_pct >= critical_loss_pct:
            result['threshold_months'] = 0
            result['threshold_status'] = 'Threshold already met in scenario'
        elif persistence_pct_per_month > 0:
            for month in range(1, 13):
                projected = current_pct * (1 + persistence_pct_per_month / 100) ** month
                if projected >= critical_loss_pct:
                    result['threshold_months'] = month
                    result['threshold_status'] = f'Could cross in about {month} months'
                    break
    result['horizon_scenarios'] = {}
    for months in HORIZONS:
        growth = (1 + persistence_pct_per_month / 100) ** months
        kwh = None if current_daily_kwh is None else current_daily_kwh * 30 * months * growth
        result['horizon_scenarios'][months] = {
            'energy_at_risk_kwh': kwh,
            'tariff_exposure_usd': None if kwh is None else kwh * tariff,
        }
    wait = result['horizon_scenarios'][wait_months]['tariff_exposure_usd']
    replacement_total = replacement_cost
    result['wait_months'] = wait_months
    result['act_now_cost_usd'] = replacement_total
    result['wait_exposure_usd'] = wait
    result['wait_plus_replacement_usd'] = None if wait is None else wait + replacement_total
    result['opportunity_cost_usd'] = wait
    result['break_even_months'] = None
    if current_daily_kwh and tariff > 0:
        monthly_cost = current_daily_kwh * 30 * tariff
        result['break_even_months'] = replacement_total / monthly_cost if monthly_cost else None
    result['due_window'] = due_window(panel)
    result['priority_score'] = priority_score(panel)
    result['priority_reason'] = priority_reason(panel, result)
    result['scenario_label'] = 'Illustrative synthetic scenario; not a measured forecast'
    return result


def due_window(panel: dict) -> str:
    if panel['safety_flag'] or panel['severity'] == 'Critical':
        return 'Now'
    if panel['severity'] == 'High':
        return 'Within 3 months'
    if panel['severity'] == 'Medium':
        return 'Within 6 months'
    return 'Monitor'


def priority_score(panel: dict) -> int:
    severity = {'Critical': 80, 'High': 55, 'Medium': 30, 'Low': 12, 'Healthy': 0}[panel['severity']]
    return severity + (20 if panel['safety_flag'] else 0) + (8 if not panel['data_complete'] else 0) + round(panel['current_loss_pct'] * 20)


def priority_reason(panel: dict, result: dict | None = None) -> str:
    reasons = []
    if panel['safety_flag']:
        reasons.append('synthetic safety rule flags prompt inspection')
    if panel['severity'] != 'Healthy':
        reasons.append(f"{panel['severity'].lower()} {panel['fault_type'].lower()} finding")
    if not panel['data_complete']:
        reasons.append('some metadata is missing; verify before action')
    if not reasons:
        return 'No synthetic finding; routine monitoring.'
    return '; '.join(reasons) + '.'


def export_findings(rows: list[dict]) -> str:
    fields = ['panel_id', 'row', 'column', 'string_id', 'inverter_id', 'fault_type',
              'severity', 'delta_t_c', 'affected_area_pct', 'current_loss_pct',
              'safety_flag', 'due_window', 'priority_score', 'priority_reason',
              'source', 'is_synthetic', 'scenario_label']
    out = io.StringIO(newline='')
    writer = csv.DictWriter(out, fieldnames=fields, extrasaction='ignore')
    writer.writeheader()
    writer.writerows(rows)
    return out.getvalue()
