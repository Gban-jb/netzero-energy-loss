"""CSV assumptions prototype. No plant costs are supplied by default."""
import csv
import io
import math

FIELDS = {
    'tariff': 'USD/kWh', 'inspection': 'USD/action',
    'cleaning': 'USD/action', 'repair': 'USD/action',
    'replacement': 'USD/action', 'labor': 'USD/hour',
    'downtime': 'hours/action',
}
HEADER = ['scenario', 'parameter', 'value', 'unit', 'source', 'is_assumption']

def validate(rows):
    errors = []
    seen = set()
    scenarios = set()
    for n, row in enumerate(rows, 2):
        key = row.get('parameter', '')
        if key not in FIELDS:
            errors.append(f'Row {n}: unknown parameter {key!r}.')
            continue
        if key in seen:
            errors.append(f'Row {n}: duplicate parameter {key}.')
        seen.add(key)
        scenarios.add(row.get('scenario', '').strip())
        if not row.get('scenario', '').strip():
            errors.append(f'Row {n}: scenario name is required.')
        if row.get('unit') != FIELDS[key]:
            errors.append(f'Row {n}: expected unit {FIELDS[key]}.')
        try:
            value = float(row.get('value', ''))
            if not math.isfinite(value) or value < 0:
                raise ValueError()
        except (ValueError, TypeError):
            errors.append(f'Row {n}: enter a finite nonnegative value; blank is unknown, not zero.')
        if not row.get('source', '').strip():
            errors.append(f'Row {n}: identify a source or explain the assumption.')
        if row.get('is_assumption') not in ('true', 'false'):
            errors.append(f'Row {n}: is_assumption must be true or false.')
    if len(scenarios) > 1:
        errors.append('One scenario per file is required.')
    for key in FIELDS.keys() - seen:
        errors.append(f'Missing parameter: {key}.')
    return errors

def loads(text):
    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames != HEADER:
        raise ValueError('CSV columns must be: ' + ','.join(HEADER))
    rows = list(reader)
    if any(None in row or None in row.values() for row in rows):
        raise ValueError('CSV rows must have exactly six columns.')
    return rows

def dumps(rows):
    errors = validate(rows)
    if errors:
        raise ValueError('\n'.join(errors))
    stream = io.StringIO(newline='')
    writer = csv.DictWriter(stream, fieldnames=HEADER)
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue()
