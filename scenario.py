"""Portable Fall scenarios. Recalculate outputs from validated inputs on every load."""
import hashlib
import json
from assumptions import dumps as cost_dumps, loads as cost_loads
from energy import compare_energy, export_results

SCHEMA_VERSION = 1


def validate(payload):
    if not isinstance(payload, dict) or set(payload) != {'schema_version', 'costs', 'actual', 'expected'}:
        raise ValueError('Scenario requires schema_version, costs, actual and expected only.')
    if type(payload['schema_version']) is not int or payload['schema_version'] != SCHEMA_VERSION:
        raise ValueError('Unsupported scenario schema version.')
    costs = payload['costs']
    if not isinstance(costs, list) or not all(isinstance(r, dict) and all(isinstance(v, str) for v in r.values()) for r in costs):
        raise ValueError('Costs must be a list of CSV-style text records.')
    try:
        costs = cost_loads(cost_dumps(costs))
        for name in ('actual', 'expected'):
            record = payload[name]
            if not isinstance(record, dict) or set(record) != {'asset', 'start', 'end', 'timezone', 'unit', 'source', 'energy_kwh'}:
                raise ValueError(f'{name}: invalid interval fields.')
            if not all(isinstance(record[k], str) for k in record if k != 'energy_kwh'):
                raise ValueError(f'{name}: context fields must be text.')
            if isinstance(record['energy_kwh'], bool) or not isinstance(record['energy_kwh'], (str, int, float, type(None))):
                raise ValueError(f'{name}: invalid energy value.')
        compare_energy(payload['actual'], payload['expected'])
    except (TypeError, KeyError, AttributeError) as exc:
        raise ValueError('Malformed scenario input.') from exc
    return dict(payload, costs=costs)


def dumps(payload):
    return json.dumps(validate(payload), indent=2, sort_keys=True, allow_nan=False) + '\n'


def loads(data):
    try:
        return validate(json.loads(data))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError('Open a valid UTF-8 scenario JSON file.') from exc


def calculate(payload):
    payload = validate(payload)
    result = compare_energy(payload['actual'], payload['expected'])
    costs = {r['parameter']: r for r in payload['costs']}
    tariff = float(costs['tariff']['value'])
    result.update(scenario=payload['costs'][0]['scenario'], schema_version=SCHEMA_VERSION,
                  scenario_sha256=hashlib.sha256(dumps(payload).encode()).hexdigest(),
                  formula='max(0, expected_kwh - actual_kwh) * tariff_usd_per_kwh',
                  tariff_usd_per_kwh=tariff, tariff_source=costs['tariff']['source'],
                  tariff_is_assumption=costs['tariff']['is_assumption'],
                  scenario_shortfall_value_usd=None if result['shortfall_kwh'] is None else result['shortfall_kwh'] * tariff)
    for parameter, row in costs.items():
        for field in ('value', 'unit', 'source', 'is_assumption'):
            result[f'input_{parameter}_{field}'] = row[field]
    return result


def export_csv(payload):
    return export_results([calculate(payload)])
