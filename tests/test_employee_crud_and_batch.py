import unittest
import io
import os
import pandas as pd
from app import create_app
from app.extensions import db
from app.models.employee import Employee
from app.models.prediction import Prediction
from app.models.user import User
from config import Config
from werkzeug.security import generate_password_hash

class TestCrudBatchConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False

class TestEmployeeCrudAndBatch(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestCrudBatchConfig)
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()
        
        # Create a test user and log them in
        hashed_password = generate_password_hash('test_pass')
        self.user = User(username='test_user', email='test@example.com', password_hash=hashed_password)
        db.session.add(self.user)
        db.session.commit()
        
        # Log in the user using the client
        with self.client.session_transaction() as sess:
            sess['_user_id'] = str(self.user.id)
            sess['_fresh'] = True

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_search_and_filtering(self):
        # Create some employees
        emp1 = Employee(
            employee_id='EMP9001', first_name='Alice', last_name='Smith',
            department='Sales', overtime=True, age=30
        )
        emp2 = Employee(
            employee_id='EMP9002', first_name='Bob', last_name='Jones',
            department='Research & Development', overtime=False, age=40
        )
        db.session.add_all([emp1, emp2])
        db.session.commit()
        
        # Test Search
        response = self.client.get('/employee/?search=Alice')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Alice', response.data)
        self.assertNotIn(b'Bob', response.data)
        
        # Test Department Filter
        response = self.client.get('/employee/?department=Sales')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Alice', response.data)
        self.assertNotIn(b'Bob', response.data)
        
        # Test Overtime Filter
        response = self.client.get('/employee/?overtime=false')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Bob', response.data)
        self.assertNotIn(b'Alice', response.data)

    def test_batch_upload_prediction(self):
        # Make a mock CSV data stream
        csv_content = (
            "employee_id,first_name,last_name,age,business_travel,daily_rate,department,overtime\n"
            "EMP9003,Charlie,Brown,28,Travel_Rarely,800,Human Resources,Yes\n"
            "EMP9004,David,Miller,45,Non-Travel,1200,Research & Development,No\n"
        )
        data = {
            'file': (io.BytesIO(csv_content.encode('utf-8')), 'test_upload.csv')
        }
        
        # Send POST request to batch route
        response = self.client.post('/prediction/batch', data=data, content_type='multipart/form-data', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Batch Prediction Results', response.data)
        
        # Verify employees are in the database
        emp_c = Employee.query.filter_by(employee_id='EMP9003').first()
        emp_d = Employee.query.filter_by(employee_id='EMP9004').first()
        self.assertIsNotNone(emp_c)
        self.assertIsNotNone(emp_d)
        self.assertEqual(emp_c.first_name, 'Charlie')
        self.assertEqual(emp_d.first_name, 'David')
        self.assertEqual(emp_c.overtime, True)
        self.assertEqual(emp_d.overtime, False)
        
        # Verify predictions were generated
        pred_c = Prediction.query.filter_by(employee_id='EMP9003').first()
        pred_d = Prediction.query.filter_by(employee_id='EMP9004').first()
        self.assertIsNotNone(pred_c)
        self.assertIsNotNone(pred_d)
        
    def test_download_template(self):
        response = self.client.get('/prediction/download-template')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, 'text/csv')
        self.assertIn(b'employee_id', response.data)
        self.assertIn(b'first_name', response.data)

    def test_cohort_analytics(self):
        # Create some employees and baseline predictions
        emp1 = Employee(
            employee_id='EMP9005', first_name='Frank', last_name='Sinatra',
            department='Sales', overtime=True, age=30, monthly_income=2500.0,
            job_satisfaction=1, work_life_balance=1
        )
        emp2 = Employee(
            employee_id='EMP9006', first_name='Dean', last_name='Martin',
            department='Research & Development', overtime=False, age=50, monthly_income=12000.0,
            job_satisfaction=4, work_life_balance=4
        )
        db.session.add_all([emp1, emp2])
        db.session.commit()
        
        # Add predictions (EMP9005 = High Risk, EMP9006 = Low Risk)
        pred1 = Prediction(employee_id='EMP9005', risk_score=0.85, prediction_class=True)
        pred2 = Prediction(employee_id='EMP9006', risk_score=0.15, prediction_class=False)
        db.session.add_all([pred1, pred2])
        db.session.commit()
        
        response = self.client.get('/dashboard/cohort-analytics')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Comparative Cohort Analytics', response.data)
        self.assertIn(b'High Attrition Risk Cohort', response.data)
        self.assertIn(b'Low Attrition Risk Cohort', response.data)

    def test_hr_chatbot(self):
        # Create some employees and predictions
        emp = Employee(
            employee_id='EMP9007', first_name='Frankie', last_name='Valli',
            department='Sales', overtime=True, age=35, monthly_income=3000.0,
            job_satisfaction=1, work_life_balance=1
        )
        db.session.add(emp)
        db.session.commit()
        
        pred = Prediction(employee_id='EMP9007', risk_score=0.92, prediction_class=True, recommended_actions="Check compensation.")
        db.session.add(pred)
        db.session.commit()
        
        # Test Chat View GET
        response = self.client.get('/dashboard/chat')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'HR AI Assistant', response.data)
        
        # Test Chat Query POST - Greetings
        response = self.client.post('/dashboard/chat/query', json={'query': 'hello'}, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn('RetainAI HR assistant', data['response'])
        
        # Test Chat Query POST - Highest Risk
        response = self.client.post('/dashboard/chat/query', json={'query': 'highest risk'}, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn('Frankie Valli', data['response'])
        self.assertIn('92%', data['response'])
        
        # Test Chat Query POST - Specific Employee
        response = self.client.post('/dashboard/chat/query', json={'query': 'Frankie'}, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn('Frankie Valli', data['response'])
        self.assertIn('92%', data['response'])
        
        # Test Chat Query POST - Why is Attrition High (drivers analysis)
        response = self.client.post('/dashboard/chat/query', json={'query': 'why is employee attrition high?'}, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn('Attrition Driver Analysis', data['response'])
        self.assertIn('Overtime Strain', data['response'])
        self.assertIn('Compensation Gaps', data['response'])

if __name__ == '__main__':
    unittest.main()
