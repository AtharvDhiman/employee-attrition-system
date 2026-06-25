import os
import numpy as np
import pandas as pd
import joblib
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.pipeline import Pipeline
from sklearn.metrics import classification_report, accuracy_score, f1_score, precision_score, recall_score, roc_auc_score

def generate_synthetic_data(num_records=1200, seed=42):
    np.random.seed(seed)
    
    # 1. Base arrays
    age = np.random.normal(37, 9, num_records).astype(int)
    age = np.clip(age, 18, 60)
    
    travel_choices = ['Travel_Rarely', 'Travel_Frequently', 'Non-Travel']
    business_travel = np.random.choice(travel_choices, num_records, p=[0.70, 0.20, 0.10])
    
    daily_rate = np.random.randint(100, 1500, num_records)
    
    dept_choices = ['Research & Development', 'Sales', 'Human Resources']
    department = np.random.choice(dept_choices, num_records, p=[0.65, 0.30, 0.05])
    
    distance_from_home = np.random.randint(1, 30, num_records)
    
    education = np.random.randint(1, 6, num_records)
    
    field_choices = ['Life Sciences', 'Medical', 'Marketing', 'Technical Degree', 'Other', 'Human Resources']
    education_field = np.random.choice(field_choices, num_records, p=[0.40, 0.30, 0.15, 0.10, 0.03, 0.02])
    
    employee_count = np.ones(num_records, dtype=int)
    employee_number = np.arange(1000, 1000 + num_records)
    
    env_satisfaction = np.random.randint(1, 5, num_records)
    
    gender = np.random.choice(['Male', 'Female'], num_records, p=[0.60, 0.40])
    
    hourly_rate = np.random.randint(30, 101, num_records)
    
    job_involvement = np.random.randint(1, 5, num_records)
    
    job_level = np.random.choice([1, 2, 3, 4, 5], num_records, p=[0.35, 0.30, 0.20, 0.10, 0.05])
    
    # Assign job roles based on department
    job_roles = []
    for dept in department:
        if dept == 'Research & Development':
            role = np.random.choice(['Research Scientist', 'Laboratory Technician', 'Manufacturing Director', 'Healthcare Representative', 'Research Director'], p=[0.40, 0.35, 0.12, 0.10, 0.03])
        elif dept == 'Sales':
            role = np.random.choice(['Sales Executive', 'Sales Representative', 'Manager'], p=[0.75, 0.20, 0.05])
        else:
            role = 'Human Resources'
        job_roles.append(role)
    job_role = np.array(job_roles)
    
    job_satisfaction = np.random.randint(1, 5, num_records)
    
    marital_status = np.random.choice(['Single', 'Married', 'Divorced'], num_records, p=[0.35, 0.45, 0.20])
    
    # Income highly correlated with job level
    monthly_income = (job_level * 2000) + np.random.normal(1500, 500, num_records)
    monthly_income = np.clip(monthly_income, 1000, 20000).round(2)
    
    monthly_rate = np.random.randint(2000, 26000, num_records)
    
    num_companies_worked = np.random.randint(0, 10, num_records)
    
    over_18 = np.array(['Y'] * num_records)
    
    overtime_choices = ['Yes', 'No']
    overtime = np.random.choice(overtime_choices, num_records, p=[0.30, 0.70])
    
    percent_salary_hike = np.random.randint(11, 26, num_records)
    
    perf_choices = [3, 4]
    performance_rating = np.random.choice(perf_choices, num_records, p=[0.85, 0.15])
    
    relationship_satisfaction = np.random.randint(1, 5, num_records)
    
    standard_hours = np.array([80] * num_records)
    
    stock_option_level = np.random.randint(0, 4, num_records)
    
    total_working_years = (age - 18) - np.random.randint(0, 5, num_records)
    total_working_years = np.clip(total_working_years, 0, 40)
    
    training_times_last_year = np.random.randint(0, 7, num_records)
    
    work_life_balance = np.random.randint(1, 5, num_records)
    
    # Tenure variables
    years_at_company = np.zeros(num_records, dtype=int)
    for i in range(num_records):
        years_at_company[i] = np.random.randint(0, int(total_working_years[i]) + 1)
        
    years_in_current_role = np.zeros(num_records, dtype=int)
    years_since_last_promotion = np.zeros(num_records, dtype=int)
    years_with_curr_manager = np.zeros(num_records, dtype=int)
    
    for i in range(num_records):
        yac = years_at_company[i]
        years_in_current_role[i] = np.random.randint(0, yac + 1)
        years_since_last_promotion[i] = np.random.randint(0, yac + 1)
        years_with_curr_manager[i] = np.random.randint(0, yac + 1)
        
    # 2. Determine Attrition based on a logit score
    logit = -1.5 # Base logit intercept
    
    logit += np.where(overtime == 'Yes', 1.3, 0)
    logit += np.where(job_satisfaction == 1, 1.1, 0)
    logit += np.where(job_satisfaction == 2, 0.4, 0)
    logit += np.where(env_satisfaction == 1, 0.8, 0)
    logit += np.where(work_life_balance == 1, 1.2, 0)
    logit += np.where(years_at_company < 2, 0.7, 0)
    logit += np.where(monthly_income < 3500, 0.9, 0)
    logit += np.where(job_involvement == 1, 0.9, 0)
    logit += np.where(distance_from_home > 15, 0.5, 0)
    logit += np.where(business_travel == 'Travel_Frequently', 0.6, 0)
    logit += np.where(years_with_curr_manager < 1, 0.4, 0)
    
    # Add normal random noise
    logit += np.random.normal(0, 0.5, num_records)
    
    # Sigmoid function
    prob = 1 / (1 + np.exp(-logit))
    attrition = np.where(prob >= 0.50, 'Yes', 'No')
    
    # Assemble DataFrame
    df = pd.DataFrame({
        'Age': age,
        'BusinessTravel': business_travel,
        'DailyRate': daily_rate,
        'Department': department,
        'DistanceFromHome': distance_from_home,
        'Education': education,
        'EducationField': education_field,
        'EmployeeCount': employee_count,
        'EmployeeNumber': employee_number,
        'EnvironmentSatisfaction': env_satisfaction,
        'Gender': gender,
        'HourlyRate': hourly_rate,
        'JobInvolvement': job_involvement,
        'JobLevel': job_level,
        'JobRole': job_role,
        'JobSatisfaction': job_satisfaction,
        'MaritalStatus': marital_status,
        'MonthlyIncome': monthly_income,
        'MonthlyRate': monthly_rate,
        'NumCompaniesWorked': num_companies_worked,
        'Over18': over_18,
        'OverTime': overtime,
        'PercentSalaryHike': percent_salary_hike,
        'PerformanceRating': performance_rating,
        'RelationshipSatisfaction': relationship_satisfaction,
        'StandardHours': standard_hours,
        'StockOptionLevel': stock_option_level,
        'TotalWorkingYears': total_working_years,
        'TrainingTimesLastYear': training_times_last_year,
        'WorkLifeBalance': work_life_balance,
        'YearsAtCompany': years_at_company,
        'YearsInCurrentRole': years_in_current_role,
        'YearsSinceLastPromotion': years_since_last_promotion,
        'YearsWithCurrManager': years_with_curr_manager,
        'Attrition': attrition
    })
    
    return df

def train_pipeline():
    print("Generating synthetic HR dataset (1200 records)...")
    df = generate_synthetic_data(num_records=1200)
    
    # Ensure dataset directory exists
    os.makedirs('dataset', exist_ok=True)
    csv_path = 'dataset/employee_attrition.csv'
    df.to_csv(csv_path, index=False)
    print(f"Dataset saved to: {csv_path}")
    
    # Separate Features & Target
    X = df.drop(columns=['Attrition', 'EmployeeNumber', 'EmployeeCount', 'StandardHours', 'Over18'])
    y = df['Attrition'].map({'Yes': 1, 'No': 0})
    
    # Identify column groups
    categorical_cols = X.select_dtypes(include=['object']).columns.tolist()
    numeric_cols = X.select_dtypes(include=['int', 'float']).columns.tolist()
    
    # Preprocessor definition
    preprocessor = ColumnTransformer(
        transformers=[
            ('num', StandardScaler(), numeric_cols),
            ('cat', OneHotEncoder(handle_unknown='ignore', sparse_output=False), categorical_cols)
        ]
    )
    
    # Split
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.25, random_state=42, stratify=y)
    
    # Candidate models dict
    candidates = {
        'Logistic Regression': LogisticRegression(max_iter=1000, random_state=42),
        'Random Forest Classifier': RandomForestClassifier(n_estimators=100, max_depth=8, random_state=42),
        'Gradient Boosting Classifier': GradientBoostingClassifier(n_estimators=100, learning_rate=0.1, max_depth=4, random_state=42)
    }
    
    best_name = None
    best_pipeline = None
    best_f1 = -1.0
    best_metrics = {}
    
    print("\nTraining and evaluating multiple models...")
    print("-" * 75)
    print(f"{'Model Name':<30} | {'Accuracy':<8} | {'F1-Score':<8} | {'Precision':<9} | {'Recall':<6} | {'ROC-AUC':<7}")
    print("-" * 75)
    
    results = {}
    for name, clf in candidates.items():
        pipeline = Pipeline(steps=[
            ('preprocessor', preprocessor),
            ('classifier', clf)
        ])
        
        # Fit
        pipeline.fit(X_train, y_train)
        
        # Evaluate
        y_pred = pipeline.predict(X_test)
        y_prob = pipeline.predict_proba(X_test)[:, 1]
        
        acc = accuracy_score(y_test, y_pred)
        f1 = f1_score(y_test, y_pred)
        prec = precision_score(y_test, y_pred)
        rec = recall_score(y_test, y_pred)
        auc = roc_auc_score(y_test, y_prob)
        
        print(f"{name:<30} | {acc:.4f}   | {f1:.4f}   | {prec:.4f}    | {rec:.4f} | {auc:.4f}")
        
        results[name] = {
            'pipeline': pipeline,
            'accuracy': acc,
            'f1_score': f1,
            'precision': prec,
            'recall': rec,
            'roc_auc': auc
        }
        
        # Select best model based on F1-Score
        if f1 > best_f1:
            best_f1 = f1
            best_name = name
            best_pipeline = pipeline
            best_metrics = results[name]
            
    print("-" * 75)
    print(f"Winner Model: {best_name} with F1-Score of {best_f1:.4f}\n")
    
    # Generate feature importances for the winner model
    print(f"Extracting feature importances for {best_name}...")
    numeric_features = numeric_cols
    cat_encoder = best_pipeline.named_steps['preprocessor'].named_transformers_['cat']
    categorical_features = cat_encoder.get_feature_names_out(categorical_cols).tolist()
    all_features = numeric_features + categorical_features
    
    clf_winner = best_pipeline.named_steps['classifier']
    if hasattr(clf_winner, 'feature_importances_'):
        importances = clf_winner.feature_importances_.tolist()
    elif hasattr(clf_winner, 'coef_'):
        raw_coef = np.abs(clf_winner.coef_[0])
        coef_sum = raw_coef.sum()
        importances = (raw_coef / coef_sum).tolist() if coef_sum > 0 else raw_coef.tolist()
    else:
        importances = [0.0] * len(all_features)
        
    feature_importances = dict(zip(all_features, importances))
    
    # Save best model and metadata
    os.makedirs('app/ml', exist_ok=True)
    
    feature_names = X.columns.tolist()
    model_data = {
        'pipeline': best_pipeline,
        'model_name': best_name,
        'feature_names': feature_names,
        'categorical_cols': categorical_cols,
        'numeric_cols': numeric_cols,
        'accuracy': best_metrics['accuracy'],
        'f1_score': best_metrics['f1_score'],
        'precision': best_metrics['precision'],
        'recall': best_metrics['recall'],
        'roc_auc': best_metrics['roc_auc'],
        'feature_importances': feature_importances
    }
    
    model_path = 'app/ml/model.joblib'
    joblib.dump(model_data, model_path)
    print(f"Saved winner model to: {model_path}\n")

if __name__ == "__main__":
    train_pipeline()
