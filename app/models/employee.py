from datetime import datetime, timezone
from app.extensions import db

class Employee(db.Model):
    __tablename__ = 'employees'

    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.String(64), unique=True, nullable=False, index=True)
    first_name = db.Column(db.String(64), nullable=False)
    last_name = db.Column(db.String(64), nullable=False)
    
    # --- 35 IBM HR Dataset Features ---
    age = db.Column(db.Integer, nullable=True)
    business_travel = db.Column(db.String(64), nullable=True) # Travel_Rarely, Travel_Frequently, Non-Travel
    daily_rate = db.Column(db.Integer, nullable=True)
    department = db.Column(db.String(64), nullable=True)
    distance_from_home = db.Column(db.Integer, nullable=True)
    education = db.Column(db.Integer, nullable=True) # 1-5
    education_field = db.Column(db.String(64), nullable=True)
    employee_count = db.Column(db.Integer, nullable=True, default=1)
    employee_number = db.Column(db.Integer, nullable=True)
    environment_satisfaction = db.Column(db.Integer, nullable=True) # 1-4
    gender = db.Column(db.String(20), nullable=True)
    hourly_rate = db.Column(db.Integer, nullable=True)
    job_involvement = db.Column(db.Integer, nullable=True) # 1-4
    job_level = db.Column(db.Integer, nullable=True) # 1-5
    job_role = db.Column(db.String(64), nullable=True)
    job_satisfaction = db.Column(db.Integer, nullable=True) # 1-4
    marital_status = db.Column(db.String(32), nullable=True) # Single, Married, Divorced
    monthly_income = db.Column(db.Float, nullable=True)
    monthly_rate = db.Column(db.Integer, nullable=True)
    num_companies_worked = db.Column(db.Integer, nullable=True)
    over_18 = db.Column(db.String(10), nullable=True, default='Y')
    overtime = db.Column(db.Boolean, default=False)
    percent_salary_hike = db.Column(db.Integer, nullable=True)
    performance_rating = db.Column(db.Integer, nullable=True) # 1-4
    relationship_satisfaction = db.Column(db.Integer, nullable=True) # 1-4
    standard_hours = db.Column(db.Integer, nullable=True, default=80)
    stock_option_level = db.Column(db.Integer, nullable=True) # 0-3
    total_working_years = db.Column(db.Integer, nullable=True)
    training_times_last_year = db.Column(db.Integer, nullable=True)
    work_life_balance = db.Column(db.Integer, nullable=True) # 1-4
    years_at_company = db.Column(db.Integer, nullable=True)
    years_in_current_role = db.Column(db.Integer, nullable=True)
    years_since_last_promotion = db.Column(db.Integer, nullable=True)
    years_with_curr_manager = db.Column(db.Integer, nullable=True)
    
    # --- Metadata ---
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    # Relationship to prediction history
    predictions = db.relationship('Prediction', backref='employee', lazy=True, cascade="all, delete-orphan")

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    def __repr__(self):
        return f'<Employee {self.employee_id} - {self.full_name}>'
