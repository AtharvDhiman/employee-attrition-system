from datetime import datetime, timezone
from app.extensions import db

class Prediction(db.Model):
    __tablename__ = 'predictions'

    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.String(64), db.ForeignKey('employees.employee_id'), nullable=False)
    risk_score = db.Column(db.Float, nullable=False) # e.g. 0.74
    prediction_class = db.Column(db.Boolean, nullable=False) # True/False
    features_snapshot = db.Column(db.JSON, nullable=True) # Full feature values dict
    recommended_actions = db.Column(db.Text, nullable=True)
    run_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f'<Prediction Emp:{self.employee_id} Score:{self.risk_score:.2f}>'
