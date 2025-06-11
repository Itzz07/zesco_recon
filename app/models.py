from . import db

class EnergyRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.String(20), nullable=False)
    token_amount = db.Column(db.Float, nullable=False)
    units_received = db.Column(db.Float, nullable=False)
    meter_no = db.Column(db.String(50), nullable=False)
