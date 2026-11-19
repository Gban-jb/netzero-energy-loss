"""Traceable interval energy comparisons. Inputs are interval energy, never power."""
import csv
import io
import math
from datetime import datetime
from zoneinfo import ZoneInfo


def _validate(record, allow_missing=False):
    for field in ('asset', 'start', 'end', 'timezone', 'unit', 'source'):
        if record.get(field) is None or not str(record.get(field, '')).strip():
            raise ValueError(f'{field} is required')
    if record['unit'] != 'kWh':
        raise ValueError('Energy unit must be kWh')
    try:
        zone = ZoneInfo(record['timezone'])
    except (KeyError, ValueError) as exc:
        raise ValueError('Timezone must be a valid IANA identifier') from exc
    start, end = datetime.fromisoformat(record['start']), datetime.fromisoformat(record['end'])
    if start.tzinfo is not None or end.tzinfo is not None:
        raise ValueError('Use local ISO timestamps without offsets and specify timezone separately')
    if end <= start:
        raise ValueError('End must be later than start')
    # Local wall times at DST transitions are ambiguous or nonexistent.
    from datetime import timezone
    for stamp in (start, end):
        first, second = stamp.replace(tzinfo=zone, fold=0), stamp.replace(tzinfo=zone, fold=1)
        if first.utcoffset() != second.utcoffset() or first.astimezone(timezone.utc).astimezone(zone).replace(tzinfo=None) != stamp:
            raise ValueError('Ambiguous or nonexistent local timestamp; use UTC intervals')
    value = record.get('energy_kwh')
    if allow_missing and value in (None, ''):
        return None
    try:
        value = float(value)
    except (TypeError, ValueError):
        raise ValueError('Energy must be a finite nonnegative number') from None
    if not math.isfinite(value) or value < 0:
        raise ValueError('Energy must be a finite nonnegative number')
    return value


def compare_energy(actual, expected):
    """Require identical comparison context. Missing expected stays unavailable."""
    av = _validate(actual)
    ev = _validate(expected, allow_missing=True)
    for field in ('asset', 'start', 'end', 'timezone', 'unit'):
        if actual[field] != expected[field]:
            raise ValueError(f'Actual and expected {field} must match')
    return {**{k: actual[k] for k in ('asset', 'start', 'end', 'timezone', 'unit')},
            'actual_kwh': av, 'expected_kwh': ev,
            'actual_source': actual['source'], 'expected_source': expected['source'],
            'status': 'unavailable' if ev is None else 'scenario estimate',
            'reason': 'Expected generation is missing' if ev is None else '',
            'signed_difference_kwh': None if ev is None else ev-av,
            'shortfall_kwh': None if ev is None else max(0., ev-av)}


def export_results(results):
    output = io.StringIO(newline='')
    writer = csv.DictWriter(output, fieldnames=list(results[0]))
    writer.writeheader()
    writer.writerows(results)
    return output.getvalue()


def demonstration_results():
    base = dict(asset='SYNTHETIC_SITE', start='2026-10-28T00:00', end='2026-10-29T00:00',
                timezone='America/Chicago', unit='kWh', source='Synthetic demonstration; not site measurements')
    return [compare_energy(dict(base, energy_kwh=a), dict(base, energy_kwh=e))
            for a, e in ((80,100), (110,100), (80,None))]
