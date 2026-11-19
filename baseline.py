"""Strict interval-energy CSV alignment; does not infer energy from SCADA power."""
import csv
import io
from collections import defaultdict
from datetime import datetime
from energy import _validate, compare_energy

FIELDS = ['asset', 'start', 'end', 'timezone', 'unit', 'source', 'energy_kwh']
KEYS = ('asset', 'start', 'end', 'timezone', 'unit')

def read_intervals(data, expected=False):
    text = data.decode('utf-8-sig') if isinstance(data, bytes) else data
    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames != FIELDS:
        raise ValueError('CSV columns must be: ' + ','.join(FIELDS))
    rows = list(reader)
    if not rows:
        raise ValueError('CSV contains no intervals')
    groups = defaultdict(list)
    for i, row in enumerate(rows, 2):
        if None in row or None in row.values():
            raise ValueError(f'Row {i}: malformed CSV row')
        row.update({k:v.strip() for k,v in row.items()})
        try:
            row['energy_kwh'] = _validate(row, allow_missing=expected)
        except (ValueError, KeyError) as exc:
            raise ValueError(f'Row {i}: {exc}') from exc
        row['start'] = datetime.fromisoformat(row['start']).isoformat()
        row['end'] = datetime.fromisoformat(row['end']).isoformat()
        groups[row['asset']].append(row)
    for asset, values in groups.items():
        if len({r['timezone'] for r in values}) != 1:
            raise ValueError(f'{asset}: multiple timezones are not supported')
        values.sort(key=lambda r:r['start'])
        for previous, current in zip(values, values[1:]):
            if current['start'] < previous['end']:
                raise ValueError(f'{asset}: duplicate or overlapping intervals')
    return rows

def align_intervals(actual, expected):
    lookup = {tuple(r[k] for k in KEYS):r for r in expected}
    results, used = [], set()
    for row in actual:
        key = tuple(row[k] for k in KEYS)
        baseline = lookup.get(key)
        if baseline is None:
            baseline = dict(row, energy_kwh=None, source='No matching expected interval supplied')
        else:
            used.add(key)
        results.append(compare_energy(row, baseline))
    matched = sum(r['shortfall_kwh'] is not None for r in results)
    summary = {'actual_intervals':len(actual), 'comparable_intervals':matched,
               'unavailable_intervals':len(actual)-matched,
               'unmatched_baseline_intervals':len(expected)-len(used),
               'interval_coverage_percent':100*matched/len(actual) if actual else 0}
    return results, summary

def value_shortfalls(results, tariff, source, is_assumption=True):
    import math
    try:
        tariff = float(tariff)
    except (TypeError, ValueError):
        raise ValueError('Tariff must be a finite nonnegative USD/kWh value') from None
    if not math.isfinite(tariff) or tariff < 0:
        raise ValueError('Tariff must be a finite nonnegative USD/kWh value')
    if not source.strip():
        raise ValueError('Tariff source is required')
    return [dict(r, tariff_usd_per_kwh=tariff, tariff_source=source,
                 tariff_is_assumption=is_assumption,
                 scenario_shortfall_value_usd=None if r['shortfall_kwh'] is None else r['shortfall_kwh']*tariff)
            for r in results]
