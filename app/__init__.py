import os
import click
from flask import Flask
from flask.cli import with_appcontext
from config import Config
from app.extensions import db, login_manager

def create_app(config_class=Config):
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config.from_object(config_class)

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)

    # User loader callback
    @login_manager.user_loader
    def load_user(user_id):
        from app.models.user import User
        return User.query.get(int(user_id))

    # Register blueprints
    from app.auth import auth_bp
    from app.dashboard import dashboard_bp
    from app.employee import employee_bp
    from app.prediction import prediction_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(employee_bp)
    app.register_blueprint(prediction_bp)

    # Register CLI commands
    app.cli.add_command(init_db_command)

    # Initialize database tables automatically on app start
    with app.app_context():
        try:
            os.makedirs(app.instance_path, exist_ok=True)
            # Import models before create_all to register them with metadata
            from app.models import User, Employee, Prediction
            db.create_all()
            from werkzeug.security import generate_password_hash
            if not User.query.filter_by(username='hr_admin').first():
                default_password = os.environ.get('DEFAULT_ADMIN_PASSWORD', 'password123')
                hashed_password = generate_password_hash(default_password)
                default_user = User(
                    username='hr_admin',
                    email='admin@retain.ai',
                    password_hash=hashed_password,
                    role='hr_manager'
                )
                db.session.add(default_user)
                db.session.commit()
                app.logger.info('Database initialized with default user.')

            # Pre-populate database with synthetic dataset if empty
            from app.models.employee import Employee
            from app.models.prediction import Prediction
            if Employee.query.count() == 0:
                import pandas as pd
                csv_path = os.path.join(app.root_path, "..", "dataset", "employee_attrition.csv")
                if os.path.exists(csv_path):
                    df = pd.read_csv(csv_path)
                    for _, row in df.iterrows():
                        emp_id = f"EMP{row['EmployeeNumber']}"
                        emp = Employee(
                            employee_id=emp_id,
                            first_name="Employee",
                            last_name=str(row['EmployeeNumber']),
                            age=int(row['Age']),
                            business_travel=row['BusinessTravel'],
                            daily_rate=int(row['DailyRate']),
                            department=row['Department'],
                            distance_from_home=int(row['DistanceFromHome']),
                            education=int(row['Education']),
                            education_field=row['EducationField'],
                            employee_count=int(row['EmployeeCount']),
                            employee_number=int(row['EmployeeNumber']),
                            environment_satisfaction=int(row['EnvironmentSatisfaction']),
                            gender=row['Gender'],
                            hourly_rate=int(row['HourlyRate']),
                            job_involvement=int(row['JobInvolvement']),
                            job_level=int(row['JobLevel']),
                            job_role=row['JobRole'],
                            job_satisfaction=int(row['JobSatisfaction']),
                            marital_status=row['MaritalStatus'],
                            monthly_income=float(row['MonthlyIncome']),
                            monthly_rate=int(row['MonthlyRate']),
                            num_companies_worked=int(row['NumCompaniesWorked']),
                            over_18=row['Over18'],
                            overtime=(row['OverTime'] == 'Yes'),
                            percent_salary_hike=int(row['PercentSalaryHike']),
                            performance_rating=int(row['PerformanceRating']),
                            relationship_satisfaction=int(row['RelationshipSatisfaction']),
                            standard_hours=int(row['StandardHours']),
                            stock_option_level=int(row['StockOptionLevel']),
                            total_working_years=int(row['TotalWorkingYears']),
                            training_times_last_year=int(row['TrainingTimesLastYear']),
                            work_life_balance=int(row['WorkLifeBalance']),
                            years_at_company=int(row['YearsAtCompany']),
                            years_in_current_role=int(row['YearsInCurrentRole']),
                            years_since_last_promotion=int(row['YearsSinceLastPromotion']),
                            years_with_curr_manager=int(row['YearsWithCurrManager'])
                        )
                        db.session.add(emp)
                        
                        # Populate a prediction record to fill dashboard charts
                        is_high_risk = (row['Attrition'] == 'Yes')
                        prob = 0.85 if is_high_risk else 0.12
                        pred = Prediction(
                            employee_id=emp_id,
                            risk_score=prob,
                            prediction_class=is_high_risk,
                            features_snapshot={
                                "Age": int(row['Age']),
                                "OverTime": row['OverTime'],
                                "JobSatisfaction": int(row['JobSatisfaction']),
                                "MonthlyIncome": float(row['MonthlyIncome'])
                            },
                            recommended_actions="Initial dataset import baseline."
                        )
                        db.session.add(pred)
                    db.session.commit()
                    app.logger.info("Successfully pre-populated database with 1200 employee records.")
        except Exception as e:
            app.logger.error(f"Error auto-initializing database: {e}")

    # Fallback route for home page
    @app.route("/")
    def home():
        from flask import render_template
        return render_template("home.html")

    return app

@click.command('init-db')
@with_appcontext
def init_db_command():
    """Clear the existing data and create new tables."""
    from flask import current_app
    try:
        os.makedirs(current_app.instance_path, exist_ok=True)
    except OSError:
        pass

    from app.models import User, Employee, Prediction
    db.create_all()
    click.echo('Initialized the database.')

    # Prepopulate default HR Manager if database is empty
    from werkzeug.security import generate_password_hash
    if not User.query.filter_by(username='hr_admin').first():
        default_password = os.environ.get('DEFAULT_ADMIN_PASSWORD', 'password123')
        hashed_password = generate_password_hash(default_password)
        default_user = User(
            username='hr_admin',
            email='admin@retain.ai',
            password_hash=hashed_password,
            role='hr_manager'
        )
        db.session.add(default_user)
        db.session.commit()
        click.echo('Created default HR account (Username: hr_admin, Password: password123).')
