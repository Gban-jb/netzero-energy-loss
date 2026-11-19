"""Transparent action-cost comparison; does not estimate benefits or rank actions."""
import csv
import hashlib
import io
import json
import math

ACTIONS = ('inspect', 'clean', 'repair', 'replace', 'wait')
ROW_FIELDS = {'action', 'direct_cost_usd', 'labor_hours', 'downtime_hours', 'source', 'is_assumption'}


def number(value, label):
    if value is None or value == '':
        return None
    if isinstance(value, bool):
        raise ValueError(f'{label}: enter a finite nonnegative number or leave blank.')
    try:
        value = float(value)
    except (ValueError, TypeError):
        raise ValueError(f'{label}: enter a finite nonnegative number or leave blank.') from None
    if not math.isfinite(value) or value < 0:
        raise ValueError(f'{label}: enter a finite nonnegative number or leave blank.')
    return value


def provenance(record):
    if not isinstance(record['source'], str) or not record['source'].strip():
        raise ValueError('Provide a source or explain each assumption, including missing values.')
    if record['is_assumption'] not in ('true', 'false'):
        raise ValueError('is_assumption must be true or false.')


def validate(payload):
    if not isinstance(payload, dict) or set(payload) != {'schema_version', 'scenario', 'asset', 'labor_rate', 'downtime_rate', 'options'}:
        raise ValueError('Invalid maintenance scenario fields.')
    if type(payload['schema_version']) is not int or payload['schema_version'] != 1:
        raise ValueError('Unsupported maintenance schema version.')
    result = dict(payload)
    for field in ('scenario', 'asset'):
        if not isinstance(payload[field], str) or not payload[field].strip():
            raise ValueError(f'{field} is required.')
    for field in ('labor_rate', 'downtime_rate'):
        rate = payload[field]
        if not isinstance(rate, dict) or set(rate) != {'value', 'source', 'is_assumption'}:
            raise ValueError(f'{field}: invalid fields.')
        provenance(rate)
        result[field] = dict(rate, value=number(rate['value'], field))
    rows = payload['options']
    if not isinstance(rows, list) or len(rows) != len(ACTIONS):
        raise ValueError('Include exactly one row for inspect, clean, repair, replace and wait.')
    normalized = []
    for row in rows:
        if not isinstance(row, dict) or set(row) != ROW_FIELDS:
            raise ValueError('Invalid action fields.')
        if not isinstance(row['action'], str) or row['action'] not in ACTIONS:
            raise ValueError('Unknown maintenance action.')
        provenance(row)
        normalized.append(dict(row, **{k:number(row[k], row['action'] + ' ' + k)
                                       for k in ('direct_cost_usd', 'labor_hours', 'downtime_hours')}))
    if {r['action'] for r in normalized} != set(ACTIONS):
        raise ValueError('Each maintenance action must appear exactly once.')
    result['options'] = sorted(normalized, key=lambda r:ACTIONS.index(r['action']))
    return result


def dumps(payload):
    return json.dumps(validate(payload), indent=2, sort_keys=True, allow_nan=False) + '\n'


def loads(data):
    try:
        return validate(json.loads(data))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError('Open a valid maintenance scenario JSON file.') from exc


def product(hours, rate):
    # No charge accrues for an explicit zero duration, even if its rate is unknown.
    if hours == 0 or rate == 0:
        return 0.0
    return None if hours is None or rate is None else hours * rate


def compare(payload):
    p = validate(payload)
    fingerprint = hashlib.sha256(dumps(p).encode()).hexdigest()
    results = []
    for row in p['options']:
        labor = product(row['labor_hours'], p['labor_rate']['value'])
        downtime = product(row['downtime_hours'], p['downtime_rate']['value'])
        parts = [row['direct_cost_usd'], labor, downtime]
        total = None if None in parts else sum(parts)
        if any(v is not None and not math.isfinite(v) for v in [*parts, total]):
            raise ValueError('Calculated cost exceeds the supported numeric range.')
        missing = [k for k in ('direct_cost_usd', 'labor_hours', 'downtime_hours') if row[k] is None]
        missing += [k for k in ('labor_rate', 'downtime_rate') if p[k]['value'] is None]
        results.append(dict(scenario=p['scenario'], asset=p['asset'], **row,
                            labor_rate_usd_per_hour=p['labor_rate']['value'],
                            labor_rate_source=p['labor_rate']['source'],
                            labor_rate_is_assumption=p['labor_rate']['is_assumption'],
                            downtime_rate_usd_per_hour=p['downtime_rate']['value'],
                            downtime_rate_source=p['downtime_rate']['source'],
                            downtime_rate_is_assumption=p['downtime_rate']['is_assumption'],
                            labor_cost_usd=labor, downtime_cost_usd=downtime,
                            priced_action_cost_usd=total,
                            status='unavailable' if total is None else 'scenario estimate',
                            missing_inputs=', '.join(missing),
                            formula='direct cost + labor hours * labor rate + downtime hours * downtime rate',
                            scope='One action only; excludes ongoing loss, future costs, effectiveness and benefits. Wait is not free over time.',
                            scenario_sha256=fingerprint))
    return results


def export_csv(payload):
    rows = compare(payload)
    stream = io.StringIO(newline='')
    writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue()
