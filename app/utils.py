# import csv
# from app.models import db, EnergyRecord

# def process_csv(filepath):
#     with open(filepath, 'r') as f:
#         reader = csv.DictReader(f)
#         for row in reader:
#             record = EnergyRecord(
#                 date=row['Date'],
#                 token_amount=float(row['Token (ZMW)']),
#                 units_received=float(row['Units Received (kWh)']),
#                 meter_no=row['Meter No.']
#             )
#             db.session.add(record)
#         db.session.commit()
import csv
from app.models import db, EnergyRecord
from datetime import datetime, timedelta
from sqlalchemy import func
from collections import defaultdict

from datetime import datetime, timedelta
from .models import EnergyRecord

def detect_anomalies(records):
    anomalies = []

    # Convert records to tuples with parsed date for easier filtering
    records_with_date = [
        (r, datetime.strptime(str(r.date), "%Y-%m-%d"))
        for r in records
    ]

    for idx, (record, record_date) in enumerate(records_with_date):
        # Get past 7 days of records
        past_week = [
            r.units_received for r, d in records_with_date
            if record_date - timedelta(days=7) <= d < record_date
        ]
        past_tokens = [
            r.token_amount for r, d in records_with_date
            if record_date - timedelta(days=7) <= d < record_date
        ]

        # Rule 1: Sudden spike in units
        if len(past_week) >= 3:
            avg_units = sum(past_week) / len(past_week)
            if record.units_received > 2 * avg_units:
                anomalies.append({
                    "date": record.date,
                    "meter_no": record.meter_no,
                    "token_amount": record.token_amount,
                    "units_received": record.units_received,
                    "reason": "Sudden spike in units received"
                })

        # Rule 2: Token purchased but no units
        if record.token_amount > 0 and record.units_received == 0:
            anomalies.append({
                "date": record.date,
                "meter_no": record.meter_no,
                "token_amount": record.token_amount,
                "units_received": record.units_received,
                "reason": "Token purchased but no units received"
            })

        # Rule 3: Low efficiency (units per ZMW)
        if record.token_amount > 0:
            efficiency = record.units_received / record.token_amount
            expected_efficiency = calculate_expected_efficiency(record.token_amount)
            if efficiency < expected_efficiency * 0.8:
                anomalies.append({
                    "date": record.date,
                    "meter_no": record.meter_no,
                    "token_amount": record.token_amount,
                    "units_received": record.units_received,
                    "reason": "Suspiciously low units per ZMW"
                })

        # Rule 4: No activity
        if record.token_amount == 0 and record.units_received == 0:
            anomalies.append({
                "date": record.date,
                "meter_no": record.meter_no,
                "token_amount": record.token_amount,
                "units_received": record.units_received,
                "reason": "No activity (token and units both zero)"
            })

        # Rule 5: Units without token
        if record.token_amount == 0 and record.units_received > 0:
            anomalies.append({
                "date": record.date,
                "meter_no": record.meter_no,
                "token_amount": record.token_amount,
                "units_received": record.units_received,
                "reason": "Units received without token purchase"
            })

        # Rule 6: Unusual high token spending
        if past_tokens and record.token_amount > 2.5 * (sum(past_tokens) / len(past_tokens)):
            anomalies.append({
                "date": record.date,
                "meter_no": record.meter_no,
                "token_amount": record.token_amount,
                "units_received": record.units_received,
                "reason": "Unusually high token purchase"
            })

        # Rule 7: Suspiciously high efficiency
        if record.token_amount > 0:
            efficiency = record.units_received / record.token_amount
            expected_efficiency = calculate_expected_efficiency(record.token_amount)
            if efficiency > expected_efficiency * 1.5:
                anomalies.append({
                    "date": record.date,
                    "meter_no": record.meter_no,
                    "token_amount": record.token_amount,
                    "units_received": record.units_received,
                    "reason": "Suspiciously high units per ZMW"
                })

    return anomalies

def calculate_expected_efficiency(token_amount):
    # Define tariff tiers (example values)
    tier1_rate = 0.5  # ZMW per kWh
    tier2_rate = 0.8
    tier3_rate = 1.2
    tier1_limit = 100
    tier2_limit = 200

    # Calculate expected units based on token amount
    remaining_amount = token_amount
    units = 0

    # Tier 1
    tier1_cost = tier1_limit * tier1_rate
    if remaining_amount >= tier1_cost:
        units += tier1_limit
        remaining_amount -= tier1_cost
    else:
        units += remaining_amount / tier1_rate
        return units / token_amount

    # Tier 2
    tier2_cost = tier2_limit * tier2_rate
    if remaining_amount >= tier2_cost:
        units += tier2_limit
        remaining_amount -= tier2_cost
    else:
        units += remaining_amount / tier2_rate
        return units / token_amount

    # Tier 3
    units += remaining_amount / tier3_rate

    return units / token_amount

def process_csv(filepath):
    try:
        with open(filepath, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                record = EnergyRecord(
                    date=row['Date'],
                    token_amount=float(row['Token (ZMW)']),
                    units_received=float(row['Units Received (kWh)']),
                    meter_no=row['Meter No.']
                )
                db.session.add(record)
            db.session.commit()
        return True
    except Exception as e:
        print(f"Error processing CSV: {e}")  # For debugging in console/log
        return False
