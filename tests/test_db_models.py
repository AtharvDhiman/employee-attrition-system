import unittest
from app import create_app
from app.extensions import db
from app.models.user import User
from app.models.employee import Employee
from app.models.prediction import Prediction
from config import Config

class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'

class TestDatabaseModels(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestConfig)
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_user_creation(self):
        user = User(username='test_user', email='test@example.com', password_hash='hashed_pass')
        db.session.add(user)
        db.session.commit()
        
        db_user = User.query.filter_by(username='test_user').first()
        self.assertIsNotNone(db_user)
        self.assertEqual(db_user.email, 'test@example.com')

    def test_employee_and_prediction(self):
        emp = Employee(
            employee_id='EMP999',
            first_name='John',
            last_name='Doe',
            department='Engineering',
            job_role='Software Engineer',
            monthly_income=6000.0,
            overtime=True,
            job_satisfaction=4,
            work_life_balance=3,
            years_at_company=5
        )
        db.session.add(emp)
        db.session.commit()

        pred = Prediction(
            employee_id='EMP999',
            risk_score=0.45,
            prediction_class=False,
            features_snapshot={"overtime": True, "job_satisfaction": 4},
            recommended_actions="Keep going!"
        )
        db.session.add(pred)
        db.session.commit()

        db_emp = Employee.query.filter_by(employee_id='EMP999').first()
        self.assertIsNotNone(db_emp)
        self.assertEqual(len(db_emp.predictions), 1)
        self.assertEqual(db_emp.predictions[0].risk_score, 0.45)

if __name__ == '__main__':
    unittest.main()
