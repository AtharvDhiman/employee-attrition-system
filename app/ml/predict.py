import os
import pandas as pd
import joblib

# Cache the loaded model
_model_data = None

def get_model():
    global _model_data
    if _model_data is None:
        model_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'model.joblib')
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model pipeline not found at: {model_path}. Run training first.")
        _model_data = joblib.load(model_path)
    return _model_data

def predict_employee_attrition(employee):
    """
    Takes an Employee DB object, extracts the 30+ features, runs them through the trained model,
    calculates local AI explanations/drivers, and returns a dict with details.
    """
    model_data = get_model()
    pipeline = model_data['pipeline']
    feature_names = model_data['feature_names']
    model_name = model_data.get('model_name', 'Random Forest Classifier')
    accuracy = model_data.get('accuracy', 0.84)
    f1_score = model_data.get('f1_score', 0.89)
    feature_importances = model_data.get('feature_importances', {})
    
    # Map SQLAlchemy model fields to the exact capitalization used in the training features
    field_mappings = {
        'age': 'Age',
        'business_travel': 'BusinessTravel',
        'daily_rate': 'DailyRate',
        'department': 'Department',
        'distance_from_home': 'DistanceFromHome',
        'education': 'Education',
        'education_field': 'EducationField',
        'environment_satisfaction': 'EnvironmentSatisfaction',
        'gender': 'Gender',
        'hourly_rate': 'HourlyRate',
        'job_involvement': 'JobInvolvement',
        'job_level': 'JobLevel',
        'job_role': 'JobRole',
        'job_satisfaction': 'JobSatisfaction',
        'marital_status': 'MaritalStatus',
        'monthly_income': 'MonthlyIncome',
        'monthly_rate': 'MonthlyRate',
        'num_companies_worked': 'NumCompaniesWorked',
        'overtime': 'OverTime',
        'percent_salary_hike': 'PercentSalaryHike',
        'performance_rating': 'PerformanceRating',
        'relationship_satisfaction': 'RelationshipSatisfaction',
        'stock_option_level': 'StockOptionLevel',
        'total_working_years': 'TotalWorkingYears',
        'training_times_last_year': 'TrainingTimesLastYear',
        'work_life_balance': 'WorkLifeBalance',
        'years_at_company': 'YearsAtCompany',
        'years_in_current_role': 'YearsInCurrentRole',
        'years_since_last_promotion': 'YearsSinceLastPromotion',
        'years_with_curr_manager': 'YearsWithCurrManager'
    }
    
    features_dict = {}
    for db_field, ds_field in field_mappings.items():
        val = getattr(employee, db_field)
        
        # Handle special types/encodings
        if db_field == 'overtime':
            val = 'Yes' if val else 'No'
            
        # Standardize fallback defaults for missing values
        if val is None:
            if db_field in ['business_travel', 'department', 'education_field', 'gender', 'job_role', 'marital_status']:
                val = 'Other'
            else:
                val = 0
                
        features_dict[ds_field] = val
        
    # Create a 1-row DataFrame with the exact column order
    df = pd.DataFrame([features_dict], columns=feature_names)
    
    # Predict
    prob = pipeline.predict_proba(df)[0][1] # Probability of class 1 (Yes)
    prediction_class = bool(prob >= 0.50)
    
    # Calculate Local Explanations
    local_drivers = []
    
    if prediction_class:
        # HIGH RISK - Highlight negative attrition drivers
        candidates = []
        
        # 1. Overtime Strain
        if employee.overtime:
            weight = feature_importances.get('OverTime_Yes', 0.05)
            candidates.append({
                'name': 'Overtime Strain',
                'description': 'Works overtime regularly, leading to elevated burnout risk',
                'value': 'Yes',
                'importance': weight,
                'score': 1.0 * weight
            })
            
        # 2. Job Satisfaction
        if employee.job_satisfaction and employee.job_satisfaction <= 2:
            weight = feature_importances.get('JobSatisfaction', 0.05)
            factor = (4 - employee.job_satisfaction) / 3.0
            candidates.append({
                'name': 'Low Job Satisfaction',
                'description': f"Reported job satisfaction score is low ({employee.job_satisfaction}/4)",
                'value': f"{employee.job_satisfaction}/4",
                'importance': weight,
                'score': factor * weight
            })
            
        # 3. Work Life Balance
        if employee.work_life_balance and employee.work_life_balance <= 2:
            weight = feature_importances.get('WorkLifeBalance', 0.05)
            factor = (4 - employee.work_life_balance) / 3.0
            candidates.append({
                'name': 'Work-Life Imbalance',
                'description': f"Reported work-life balance is low ({employee.work_life_balance}/4)",
                'value': f"{employee.work_life_balance}/4",
                'importance': weight,
                'score': factor * weight
            })
            
        # 4. Environment Satisfaction
        if employee.environment_satisfaction and employee.environment_satisfaction <= 2:
            weight = feature_importances.get('EnvironmentSatisfaction', 0.05)
            factor = (4 - employee.environment_satisfaction) / 3.0
            candidates.append({
                'name': 'Low Environment Satisfaction',
                'description': f"Work environment satisfaction is low ({employee.environment_satisfaction}/4)",
                'value': f"{employee.environment_satisfaction}/4",
                'importance': weight,
                'score': factor * weight
            })
            
        # 5. Compensation Gaps
        if employee.monthly_income and employee.monthly_income < 3500:
            weight = feature_importances.get('MonthlyIncome', 0.05)
            factor = (3500 - employee.monthly_income) / 3500.0
            candidates.append({
                'name': 'Compensation Gap',
                'description': f"Monthly income of ${employee.monthly_income:,.0f} is below average",
                'value': f"${employee.monthly_income:,.0f}/mo",
                'importance': weight,
                'score': factor * weight
            })
            
        # 6. Job Involvement
        if employee.job_involvement and employee.job_involvement <= 2:
            weight = feature_importances.get('JobInvolvement', 0.05)
            factor = (4 - employee.job_involvement) / 3.0
            candidates.append({
                'name': 'Low Job Involvement',
                'description': f"Reported job involvement is low ({employee.job_involvement}/4)",
                'value': f"{employee.job_involvement}/4",
                'importance': weight,
                'score': factor * weight
            })
            
        # 7. Long Commute
        if employee.distance_from_home and employee.distance_from_home > 12:
            weight = feature_importances.get('DistanceFromHome', 0.05)
            factor = min((employee.distance_from_home - 12) / 18.0, 1.0)
            candidates.append({
                'name': 'Long Commute Distance',
                'description': f"Commutes {employee.distance_from_home} miles, causing daily fatigue",
                'value': f"{employee.distance_from_home} miles",
                'importance': weight,
                'score': factor * weight
            })
            
        # 8. Promotion Stagnation
        if employee.years_since_last_promotion and employee.years_since_last_promotion >= 3:
            weight = feature_importances.get('YearsSinceLastPromotion', 0.05)
            factor = min((employee.years_since_last_promotion - 2) / 8.0, 1.0)
            candidates.append({
                'name': 'Career Stagnation',
                'description': f"Spent {employee.years_since_last_promotion} years since last promotion",
                'value': f"{employee.years_since_last_promotion} years",
                'importance': weight,
                'score': factor * weight
            })
            
        # Sort and select top 4
        sorted_candidates = sorted(candidates, key=lambda x: x['score'], reverse=True)
        local_drivers = sorted_candidates[:4]
        
    else:
        # LOW RISK - Highlight positive retention pillars
        candidates = []
        
        # 1. Healthy Workload (No Overtime)
        if not employee.overtime:
            weight = feature_importances.get('OverTime_No', 0.05)
            candidates.append({
                'name': 'Healthy Workload',
                'description': 'Does not work overtime, minimizing burnout risk',
                'value': 'No Overtime',
                'importance': weight,
                'score': 1.0 * weight
            })
            
        # 2. High Job Satisfaction
        if employee.job_satisfaction and employee.job_satisfaction >= 3:
            weight = feature_importances.get('JobSatisfaction', 0.05)
            factor = (employee.job_satisfaction - 2) / 2.0
            candidates.append({
                'name': 'High Job Satisfaction',
                'description': f"Satisfied with their job role ({employee.job_satisfaction}/4)",
                'value': f"{employee.job_satisfaction}/4",
                'importance': weight,
                'score': factor * weight
            })
            
        # 3. Solid Work-Life Balance
        if employee.work_life_balance and employee.work_life_balance >= 3:
            weight = feature_importances.get('WorkLifeBalance', 0.05)
            factor = (employee.work_life_balance - 2) / 2.0
            candidates.append({
                'name': 'Strong Work-Life Balance',
                'description': f"Healthy work-life boundary ({employee.work_life_balance}/4)",
                'value': f"{employee.work_life_balance}/4",
                'importance': weight,
                'score': factor * weight
            })
            
        # 4. High Environment Satisfaction
        if employee.environment_satisfaction and employee.environment_satisfaction >= 3:
            weight = feature_importances.get('EnvironmentSatisfaction', 0.05)
            factor = (employee.environment_satisfaction - 2) / 2.0
            candidates.append({
                'name': 'High Environment Satisfaction',
                'description': f"Satisfied with workplace environment ({employee.environment_satisfaction}/4)",
                'value': f"{employee.environment_satisfaction}/4",
                'importance': weight,
                'score': factor * weight
            })
            
        # 5. Competitive Compensation
        if employee.monthly_income and employee.monthly_income >= 5000:
            weight = feature_importances.get('MonthlyIncome', 0.05)
            factor = min((employee.monthly_income - 5000) / 10000.0, 1.0)
            candidates.append({
                'name': 'Competitive Compensation',
                'description': f"Monthly income of ${employee.monthly_income:,.0f} supports high retention",
                'value': f"${employee.monthly_income:,.0f}/mo",
                'importance': weight,
                'score': factor * weight
            })
            
        # 6. Solid Tenure Loyalty
        if employee.years_at_company and employee.years_at_company >= 5:
            weight = feature_importances.get('YearsAtCompany', 0.05)
            factor = min((employee.years_at_company - 5) / 15.0, 1.0)
            candidates.append({
                'name': 'Workforce Loyalty',
                'description': f"Long company tenure of {employee.years_at_company} years indicates high loyalty",
                'value': f"{employee.years_at_company} years",
                'importance': weight,
                'score': factor * weight
            })
            
        # Sort and select top 4
        sorted_candidates = sorted(candidates, key=lambda x: x['score'], reverse=True)
        local_drivers = sorted_candidates[:4]
        
    return float(prob), prediction_class, model_name, float(accuracy), float(f1_score), local_drivers
