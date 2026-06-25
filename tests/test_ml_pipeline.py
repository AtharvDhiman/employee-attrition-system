import unittest
import os
import joblib
from app import create_app
from app.extensions import db
from app.models.employee import Employee
from app.ml.predict import predict_employee_attrition
from config import Config

class TestMLConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'

class TestMLPipeline(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestMLConfig)
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_attrition_prediction(self):
        # Create an employee with high attrition risk characteristics (e.g. overtime=True, job_satisfaction=1)
        emp_high = Employee(
            employee_id='EMP888',
            first_name='High',
            last_name='Risk',
            age=25,
            business_travel='Travel_Frequently',
            department='Sales',
            job_role='Sales Representative',
            monthly_income=2200.0,
            overtime=True,
            job_satisfaction=1,
            work_life_balance=1,
            years_at_company=1,
            environment_satisfaction=1,
            job_involvement=1,
            distance_from_home=20
        )
        db.session.add(emp_high)
        db.session.commit()

        # Create an employee with low risk characteristics
        emp_low = Employee(
            employee_id='EMP111',
            first_name='Low',
            last_name='Risk',
            age=45,
            business_travel='Non-Travel',
            department='Research & Development',
            job_role='Manager',
            monthly_income=12000.0,
            overtime=False,
            job_satisfaction=4,
            work_life_balance=4,
            years_at_company=10,
            environment_satisfaction=4,
            job_involvement=4,
            distance_from_home=2
        )
        db.session.add(emp_low)
        db.session.commit()

        # Run predictions
        prob_high, class_high, model_name, accuracy, f1_score, drivers_high = predict_employee_attrition(emp_high)
        prob_low, class_low, _, _, _, drivers_low = predict_employee_attrition(emp_low)
        
        print(f"\nPrediction for High Risk employee: Prob={prob_high:.4f}, Class={class_high}, Model={model_name}")
        print(f"Prediction for Low Risk employee: Prob={prob_low:.4f}, Class={class_low}")
        print(f"High Risk Top Drivers: {[d['name'] for d in drivers_high]}")
        print(f"Low Risk Retention Pillars: {[d['name'] for d in drivers_low]}")
        
        # Assertions
        self.assertGreater(prob_high, prob_low)
        self.assertTrue(class_high)
        self.assertFalse(class_low)
        self.assertEqual(model_name, "Gradient Boosting Classifier")
        self.assertGreaterEqual(accuracy, 0.70)
        self.assertGreaterEqual(f1_score, 0.70)
        self.assertGreater(len(drivers_high), 0)
        self.assertGreater(len(drivers_low), 0)
        
        # Check that high risk driver lists overtime strain (since emp_high works overtime)
        high_driver_names = [d['name'] for d in drivers_high]
        self.assertIn("Overtime Strain", high_driver_names)
        self.assertIn("Low Job Satisfaction", high_driver_names)

if __name__ == '__main__':
    unittest.main()
