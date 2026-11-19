"""Strict import and coverage diagnostics for a single physical meter's exports."""
import csv
import hashlib
import io
import math
from datetime import datetime
import pandas as pd

TIME = 'DateTime'
POWER = 'Meter: power_true_kw (kW)'
ENERGY = 'Meter: energy_accumulated (kWh)'
MISSING = {'', 'null', 'undefined', 'nan', 'na', 'n/a'}


def import_exports(files):
    """files is [(display name, bytes)]. Reject conflicts; merge exact duplicates."""
    if not files:
        raise ValueError('Select at least one CSV export.')
    records, manifest, headers = {}, [], None
    duplicate_count = 0
    for name, raw in files:
        try:
            reader = csv.DictReader(io.StringIO(raw.decode('utf-8-sig')))
        except UnicodeError as exc:
            raise ValueError(f'{name}: CSV must use UTF-8 encoding.') from exc
        columns = reader.fieldnames
        if not columns or len(set(columns)) != len(columns) or not {TIME, POWER, ENERGY}.issubset(columns):
            raise ValueError(f'{name}: unique columns including {TIME}, {POWER}, and {ENERGY} are required.')
        if headers is not None and set(columns) != set(headers):
            raise ValueError(f'{name}: column schema differs from the other exports.')
        headers = columns
        count = 0
        for line, row in enumerate(reader, 2):
            count += 1
            if None in row or None in row.values():
                raise ValueError(f'{name}, row {line}: incorrect number of fields.')
            try:
                stamp = datetime.strptime(row[TIME].strip(), '%Y-%m-%d %H:%M')
            except ValueError as exc:
                raise ValueError(f'{name}, row {line}: expected YYYY-MM-DD HH:MM timestamp.') from exc
            values = {}
            for col in columns:
                if col == TIME:
                    continue
                token = row[col].strip()
                if token.lower() in MISSING:
                    values[col] = None
                    continue
                try:
                    value = float(token)
                    if not math.isfinite(value):
                        raise ValueError()
                except ValueError as exc:
                    raise ValueError(f'{name}, row {line}, {col}: invalid numeric value {token!r}.') from exc
                values[col] = value
            provenance = f'{name}:row {line}'
            if stamp in records:
                old = records[stamp]
                if old['values'] != values:
                    raise ValueError(f'Conflicting readings at {stamp}: {old["sources"][0]} versus {provenance}. Resolve the source conflict before analysis.')
                old['sources'].append(provenance)
                duplicate_count += 1
            else:
                records[stamp] = {'values': values, 'sources': [provenance]}
        if not count:
            raise ValueError(f'{name}: no measurement rows.')
        manifest.append({'source': name, 'rows': count, 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()})
    frame = pd.DataFrame([{TIME: t, **r['values'], 'source_rows': ' | '.join(r['sources'])} for t,r in sorted(records.items())])
    return frame, pd.DataFrame(manifest), duplicate_count


def coverage(frame, cadence_minutes=5):
    """Coverage uses confirmed nominal cadence, no inference or filling readings."""
    if cadence_minutes <= 0 or 1440 % cadence_minutes:
        raise ValueError('Cadence must be a positive whole-minute divisor of 1440.')
    times = pd.DatetimeIndex(frame[TIME])
    if len(times) > 1 and any((times-times[0]).total_seconds() % (cadence_minutes*60) != 0):
        raise ValueError('Timestamps do not align to the selected cadence. Confirm export timing before calculating coverage.')
    expected_count = int((times.max()-times.min()).total_seconds() / (cadence_minutes*60)) + 1
    if expected_count > 2_000_000:
        raise ValueError('Selected span is too large for the chosen cadence.')
    grid = pd.date_range(times.min(), times.max(), freq=f'{cadence_minutes}min')
    indexed = frame.set_index(TIME)
    aligned = indexed.reindex(grid)
    aligned['timestamp_present'] = aligned.index.isin(times)
    daily = []
    for day, rows in aligned.groupby(aligned.index.date):
        present = int(rows['timestamp_present'].sum())
        valid = int(rows[POWER].notna().sum())
        daily.append({'date': str(day), 'expected_slots_within_export_span': len(rows), 'present_rows': present,
                      'absent_timestamps': len(rows)-present, 'null_power_rows': present-valid,
                      'valid_power_rows': valid, 'power_coverage_span_pct': round(100*valid/len(rows),2),
                      'power_coverage_full_day_pct': round(100*valid/(1440/cadence_minutes),2)})
    gaps=[]
    for a,b in zip(times,times[1:]):
        minutes=(b-a).total_seconds()/60
        if minutes > cadence_minutes:
            gaps.append({'previous_timestamp':a,'next_timestamp':b,'elapsed_minutes':minutes,'absent_timestamps':int(minutes/cadence_minutes)-1})
    aligned.index.name = TIME
    return pd.DataFrame(daily), pd.DataFrame(gaps,columns=['previous_timestamp','next_timestamp','elapsed_minutes','absent_timestamps']), aligned
