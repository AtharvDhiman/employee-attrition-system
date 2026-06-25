import os
import csv
import io
from datetime import datetime
import pandas as pd
from flask import render_template, url_for, flash, redirect, request, current_app, send_from_directory, Response
from flask_login import login_required
from app.extensions import db
from app.prediction import prediction_bp
from app.models.employee import Employee
from app.models.prediction import Prediction
from app.ml.predict import predict_employee_attrition

@prediction_bp.route("/run/<string:employee_id>", methods=['POST'])
@login_required
def run_prediction(employee_id):
    employee = Employee.query.filter_by(employee_id=employee_id).first_or_404()
    
    # Run scikit-learn model prediction
    prob, is_high_risk, model_name, accuracy, f1_score, local_drivers = predict_employee_attrition(employee)
    
    # Generate recommendations based on risk factors
    recs = []
    if employee.overtime:
        recs.append("Reduce overtime load where possible to prevent burnout.")
    if employee.job_satisfaction == 1:
        recs.append("Low job satisfaction detected. Recommend a career development check-in.")
    elif employee.job_satisfaction == 2:
        recs.append("Moderate job satisfaction. Seek feedback on potential workplace friction points.")
        
    if employee.work_life_balance == 1:
        recs.append("Critical work-life balance issues. Explore flexible hours or remote work options.")
    elif employee.work_life_balance == 2:
        recs.append("Review work schedule for better balance.")
        
    if employee.years_at_company and employee.years_at_company < 2:
        recs.append("New hire (under 2 years). Prioritize onboarding feedback and mentorship programs.")
        
    if employee.monthly_income and employee.monthly_income < 3500:
        recs.append("Compensation check. Monthly income is below average; review compensation structure.")
        
    if not recs:
        recs.append("Continue standard engagement and positive reinforcement.")
        
    # Snapshot of the features used (all 35 features)
    features = {
        "Age": employee.age,
        "BusinessTravel": employee.business_travel,
        "DailyRate": employee.daily_rate,
        "Department": employee.department,
        "DistanceFromHome": employee.distance_from_home,
        "Education": employee.education,
        "EducationField": employee.education_field,
        "EnvironmentSatisfaction": employee.environment_satisfaction,
        "Gender": employee.gender,
        "HourlyRate": employee.hourly_rate,
        "JobInvolvement": employee.job_involvement,
        "JobLevel": employee.job_level,
        "JobRole": employee.job_role,
        "JobSatisfaction": employee.job_satisfaction,
        "MaritalStatus": employee.marital_status,
        "MonthlyIncome": employee.monthly_income,
        "MonthlyRate": employee.monthly_rate,
        "NumCompaniesWorked": employee.num_companies_worked,
        "OverTime": "Yes" if employee.overtime else "No",
        "PercentSalaryHike": employee.percent_salary_hike,
        "PerformanceRating": employee.performance_rating,
        "RelationshipSatisfaction": employee.relationship_satisfaction,
        "StockOptionLevel": employee.stock_option_level,
        "TotalWorkingYears": employee.total_working_years,
        "TrainingTimesLastYear": employee.training_times_last_year,
        "WorkLifeBalance": employee.work_life_balance,
        "YearsAtCompany": employee.years_at_company,
        "YearsInCurrentRole": employee.years_in_current_role,
        "YearsSinceLastPromotion": employee.years_since_last_promotion,
        "YearsWithCurrManager": employee.years_with_curr_manager,
        "_model_name": model_name,
        "_accuracy": accuracy,
        "_f1_score": f1_score,
        "_local_drivers": local_drivers
    }
    
    prediction = Prediction(
        employee_id=employee.employee_id,
        risk_score=prob,
        prediction_class=is_high_risk,
        features_snapshot=features,
        recommended_actions="\n".join(recs)
    )
    
    db.session.add(prediction)
    db.session.commit()
    
    flash(f"Attrition prediction calculated for {employee.full_name} using {model_name}!", "success")
    return redirect(url_for('employee.detail', employee_id=employee.employee_id))

@prediction_bp.route("/history")
@login_required
def history():
    predictions = Prediction.query.order_by(Prediction.run_at.desc()).all()
    return render_template("prediction/history.html", title="Prediction History", predictions=predictions)

@prediction_bp.route("/download-template")
@login_required
def download_template():
    # Construct CSV headers matching features exactly
    headers = [
        "employee_id", "first_name", "last_name", "age", "business_travel", "daily_rate",
        "department", "distance_from_home", "education", "education_field", "employee_number",
        "environment_satisfaction", "gender", "hourly_rate", "job_involvement", "job_level",
        "job_role", "job_satisfaction", "marital_status", "monthly_income", "monthly_rate",
        "num_companies_worked", "overtime", "percent_salary_hike", "performance_rating",
        "relationship_satisfaction", "stock_option_level", "total_working_years",
        "training_times_last_year", "work_life_balance", "years_at_company",
        "years_in_current_role", "years_since_last_promotion", "years_with_curr_manager"
    ]
    # Row of sample values
    sample = [
        "EMP1001", "John", "Doe", "35", "Travel_Rarely", "800",
        "Research & Development", "8", "3", "Medical", "1001",
        "3", "Male", "60", "3", "2",
        "Research Scientist", "4", "Married", "5000", "15000",
        "1", "No", "12", "3",
        "3", "1", "10",
        "2", "3", "8",
        "7", "1", "6"
    ]
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(headers)
    writer.writerow(sample)
    
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-disposition": "attachment; filename=employee_template.csv"}
    )

@prediction_bp.route("/download/<string:filename>")
@login_required
def download_report(filename):
    is_vercel = os.environ.get("VERCEL", "false") == "true" or os.environ.get("NOW_REGION") is not None
    if is_vercel:
        reports_dir = "/tmp"
    else:
        reports_dir = os.path.abspath(os.path.join(current_app.root_path, "..", "reports"))
    return send_from_directory(reports_dir, filename, as_attachment=True)

@prediction_bp.route("/batch", methods=['GET', 'POST'])
@login_required
def batch():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash("No file part in the request.", "danger")
            return redirect(url_for('prediction.batch'))
            
        file = request.files['file']
        if file.filename == '':
            flash("No file selected.", "danger")
            return redirect(url_for('prediction.batch'))
            
        if not file.filename.endswith('.csv'):
            flash("Please upload a CSV file.", "danger")
            return redirect(url_for('prediction.batch'))
            
        try:
            # Read CSV
            df = pd.read_csv(file)
            
            # Map column names case-insensitively
            df.columns = [c.strip().lower() for c in df.columns]
            
            # We must map input columns to database fields.
            # Define standard fields mapping
            mappings = {
                'employee_id': ['employee_id', 'employeeid', 'id'],
                'first_name': ['first_name', 'firstname'],
                'last_name': ['last_name', 'lastname'],
                'age': ['age'],
                'business_travel': ['business_travel', 'businesstravel'],
                'daily_rate': ['daily_rate', 'dailyrate'],
                'department': ['department'],
                'distance_from_home': ['distance_from_home', 'distancefromhome'],
                'education': ['education'],
                'education_field': ['education_field', 'educationfield'],
                'employee_number': ['employee_number', 'employeenumber'],
                'environment_satisfaction': ['environment_satisfaction', 'environmentsatisfaction'],
                'gender': ['gender'],
                'hourly_rate': ['hourly_rate', 'hourlyrate'],
                'job_involvement': ['job_involvement', 'jobinvolvement'],
                'job_level': ['job_level', 'joblevel'],
                'job_role': ['job_role', 'jobrole'],
                'job_satisfaction': ['job_satisfaction', 'jobsatisfaction'],
                'marital_status': ['marital_status', 'maritalstatus'],
                'monthly_income': ['monthly_income', 'monthlyincome'],
                'monthly_rate': ['monthly_rate', 'monthlyrate'],
                'num_companies_worked': ['num_companies_worked', 'numcompaniesworked'],
                'overtime': ['overtime', 'over_time'],
                'percent_salary_hike': ['percent_salary_hike', 'percentsalaryhike'],
                'performance_rating': ['performance_rating', 'performancerating'],
                'relationship_satisfaction': ['relationship_satisfaction', 'relationshipsatisfaction'],
                'stock_option_level': ['stock_option_level', 'stockoptionlevel'],
                'total_working_years': ['total_working_years', 'totalworkingyears'],
                'training_times_last_year': ['training_times_last_year', 'trainingtimeslastyear'],
                'work_life_balance': ['work_life_balance', 'worklifebalance'],
                'years_at_company': ['years_at_company', 'yearsatcompany'],
                'years_in_current_role': ['years_in_current_role', 'yearsincurrentrole'],
                'years_since_last_promotion': ['years_since_last_promotion', 'yearssincelastpromotion'],
                'years_with_curr_manager': ['years_with_curr_manager', 'yearswithcurrmanager']
            }
            
            # Find which mapping applies for each field
            df_cols = list(df.columns)
            found_mappings = {}
            for field, aliases in mappings.items():
                for alias in aliases:
                    if alias in df_cols:
                        found_mappings[field] = alias
                        break
                        
            # Validate that employee_id is mapped (or fallback to employee_number)
            is_using_emp_number_fallback = False
            if 'employee_id' not in found_mappings:
                if 'employee_number' in found_mappings:
                    found_mappings['employee_id'] = found_mappings['employee_number']
                    is_using_emp_number_fallback = True
                else:
                    flash("CSV file must contain an 'employee_id' or 'employee_number' column.", "danger")
                    return redirect(url_for('prediction.batch'))
                
            results_records = []
            
            # Process each row
            for idx, row in df.iterrows():
                # Extract employee_id
                raw_emp_id = row[found_mappings['employee_id']]
                if pd.isna(raw_emp_id) or str(raw_emp_id).strip() == '':
                    continue # Skip rows without employee_id
                
                if is_using_emp_number_fallback:
                    try:
                        emp_id = f"EMP{int(float(raw_emp_id))}"
                    except ValueError:
                        emp_id = str(raw_emp_id).strip()
                else:
                    emp_id = str(raw_emp_id).strip()
                
                # Check if employee already exists
                employee = Employee.query.filter_by(employee_id=emp_id).first()
                is_new = False
                if not employee:
                    is_new = True
                    employee = Employee(employee_id=emp_id)
                    
                # Set first_name and last_name defaults or values
                if 'first_name' in found_mappings and not pd.isna(row[found_mappings['first_name']]):
                    employee.first_name = str(row[found_mappings['first_name']]).strip()
                elif is_new:
                    employee.first_name = "Employee"
                    
                if 'last_name' in found_mappings and not pd.isna(row[found_mappings['last_name']]):
                    employee.last_name = str(row[found_mappings['last_name']]).strip()
                elif is_new:
                    # use row index or employee number
                    emp_num = None
                    if 'employee_number' in found_mappings:
                        emp_num = row[found_mappings['employee_number']]
                    employee.last_name = f"#{int(emp_num)}" if emp_num is not None and not pd.isna(emp_num) else f"#{idx}"
                
                # Helper function to convert to int/float safely
                def to_int(val):
                    if pd.isna(val) or str(val).strip() == '':
                        return None
                    try:
                        return int(float(val))
                    except ValueError:
                        return None
                        
                def to_float(val):
                    if pd.isna(val) or str(val).strip() == '':
                        return None
                    try:
                        return float(val)
                    except ValueError:
                        return None
                        
                def to_bool(val):
                    if pd.isna(val) or str(val).strip() == '':
                        return False
                    s = str(val).strip().lower()
                    return s in ['yes', 'true', '1', 'y', 't']
                    
                # Parse all other fields
                int_fields = [
                    'age', 'daily_rate', 'distance_from_home', 'education', 'employee_number', 
                    'environment_satisfaction', 'hourly_rate', 'job_involvement', 'job_level', 
                    'job_satisfaction', 'monthly_rate', 'num_companies_worked', 'percent_salary_hike', 
                    'performance_rating', 'relationship_satisfaction', 'stock_option_level', 
                    'total_working_years', 'training_times_last_year', 'work_life_balance', 
                    'years_at_company', 'years_in_current_role', 'years_since_last_promotion', 
                    'years_with_curr_manager'
                ]
                for field in int_fields:
                    if field in found_mappings:
                        setattr(employee, field, to_int(row[found_mappings[field]]))
                        
                if 'monthly_income' in found_mappings:
                    employee.monthly_income = to_float(row[found_mappings['monthly_income']])
                    
                if 'overtime' in found_mappings:
                    employee.overtime = to_bool(row[found_mappings['overtime']])
                    
                str_fields = ['business_travel', 'department', 'education_field', 'gender', 'job_role', 'marital_status']
                for field in str_fields:
                    if field in found_mappings:
                        val = row[found_mappings[field]]
                        setattr(employee, field, str(val).strip() if not pd.isna(val) else None)
                
                # Save or update employee
                if is_new:
                    db.session.add(employee)
                db.session.commit()
                
                # Run prediction
                prob, is_high_risk, model_name, accuracy, f1_score, local_drivers = predict_employee_attrition(employee)
                
                # Generate recommendations based on risk factors
                recs = []
                if employee.overtime:
                    recs.append("Reduce overtime load where possible to prevent burnout.")
                if employee.job_satisfaction == 1:
                    recs.append("Low job satisfaction detected. Recommend a career development check-in.")
                elif employee.job_satisfaction == 2:
                    recs.append("Moderate job satisfaction. Seek feedback on potential workplace friction points.")
                    
                if employee.work_life_balance == 1:
                    recs.append("Critical work-life balance issues. Explore flexible hours or remote work options.")
                elif employee.work_life_balance == 2:
                    recs.append("Review work schedule for better balance.")
                    
                if employee.years_at_company and employee.years_at_company < 2:
                    recs.append("New hire (under 2 years). Prioritize onboarding feedback and mentorship programs.")
                    
                if employee.monthly_income and employee.monthly_income < 3500:
                    recs.append("Compensation check. Monthly income is below average; review compensation structure.")
                    
                if not recs:
                    recs.append("Continue standard engagement and positive reinforcement.")
                
                # Features snapshot
                features = {
                    "Age": employee.age,
                    "BusinessTravel": employee.business_travel,
                    "DailyRate": employee.daily_rate,
                    "Department": employee.department,
                    "DistanceFromHome": employee.distance_from_home,
                    "Education": employee.education,
                    "EducationField": employee.education_field,
                    "EnvironmentSatisfaction": employee.environment_satisfaction,
                    "Gender": employee.gender,
                    "HourlyRate": employee.hourly_rate,
                    "JobInvolvement": employee.job_involvement,
                    "JobLevel": employee.job_level,
                    "JobRole": employee.job_role,
                    "JobSatisfaction": employee.job_satisfaction,
                    "MaritalStatus": employee.marital_status,
                    "MonthlyIncome": employee.monthly_income,
                    "MonthlyRate": employee.monthly_rate,
                    "NumCompaniesWorked": employee.num_companies_worked,
                    "OverTime": "Yes" if employee.overtime else "No",
                    "PercentSalaryHike": employee.percent_salary_hike,
                    "PerformanceRating": employee.performance_rating,
                    "RelationshipSatisfaction": employee.relationship_satisfaction,
                    "StockOptionLevel": employee.stock_option_level,
                    "TotalWorkingYears": employee.total_working_years,
                    "TrainingTimesLastYear": employee.training_times_last_year,
                    "WorkLifeBalance": employee.work_life_balance,
                    "YearsAtCompany": employee.years_at_company,
                    "YearsInCurrentRole": employee.years_in_current_role,
                    "YearsSinceLastPromotion": employee.years_since_last_promotion,
                    "YearsWithCurrManager": employee.years_with_curr_manager,
                    "_model_name": model_name,
                    "_accuracy": accuracy,
                    "_f1_score": f1_score,
                    "_local_drivers": local_drivers
                }
                
                prediction = Prediction(
                    employee_id=employee.employee_id,
                    risk_score=prob,
                    prediction_class=is_high_risk,
                    features_snapshot=features,
                    recommended_actions="\n".join(recs)
                )
                db.session.add(prediction)
                db.session.commit()
                
                # Append to result records for report generation
                results_records.append({
                    'employee_id': employee.employee_id,
                    'full_name': employee.full_name,
                    'department': employee.department or 'N/A',
                    'job_role': employee.job_role or 'N/A',
                    'monthly_income': employee.monthly_income or 0.0,
                    'overtime': 'Yes' if employee.overtime else 'No',
                    'risk_score': prob,
                    'risk_category': 'High Risk' if is_high_risk else 'Low Risk',
                    'recommended_actions': '; '.join(recs)
                })
                
            if not results_records:
                flash("No valid employee rows processed from CSV.", "warning")
                return redirect(url_for('prediction.batch'))
                
            # Generate Report CSV
            is_vercel = os.environ.get("VERCEL", "false") == "true" or os.environ.get("NOW_REGION") is not None
            if is_vercel:
                reports_dir = "/tmp"
            else:
                reports_dir = os.path.abspath(os.path.join(current_app.root_path, "..", "reports"))
            os.makedirs(reports_dir, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"batch_report_{timestamp}.csv"
            report_path = os.path.join(reports_dir, filename)
            
            report_df = pd.DataFrame(results_records)
            report_df.to_csv(report_path, index=False)
            
            flash(f"Successfully processed {len(results_records)} employees and generated batch prediction report!", "success")
            return redirect(url_for('prediction.batch_results', filename=filename))
            
        except Exception as e:
            flash(f"An error occurred while processing the CSV file: {str(e)}", "danger")
            return redirect(url_for('prediction.batch'))
            
    return render_template("prediction/batch.html", title="Batch Prediction")

@prediction_bp.route("/batch-results/<string:filename>")
@login_required
def batch_results(filename):
    is_vercel = os.environ.get("VERCEL", "false") == "true" or os.environ.get("NOW_REGION") is not None
    if is_vercel:
        reports_dir = "/tmp"
    else:
        reports_dir = os.path.abspath(os.path.join(current_app.root_path, "..", "reports"))
    report_path = os.path.join(reports_dir, filename)
    
    if not os.path.exists(report_path):
        flash("The requested batch report does not exist.", "danger")
        return redirect(url_for('prediction.batch'))
        
    try:
        df = pd.read_csv(report_path)
        records = df.to_dict(orient='records')
        
        # Calculate summary statistics
        total_count = len(df)
        high_risk_count = int((df['risk_category'] == 'High Risk').sum())
        low_risk_count = total_count - high_risk_count
        high_risk_rate = (high_risk_count / total_count * 100) if total_count > 0 else 0.0
        avg_risk_score = float(df['risk_score'].mean() * 100) if total_count > 0 else 0.0
        
        summary = {
            'total_count': total_count,
            'high_risk_count': high_risk_count,
            'low_risk_count': low_risk_count,
            'high_risk_rate': round(high_risk_rate, 1),
            'avg_risk_score': round(avg_risk_score, 1),
            'filename': filename
        }
        
        return render_template(
            "prediction/batch_results.html", 
            title="Batch Prediction Results", 
            records=records, 
            summary=summary
        )
    except Exception as e:
        flash(f"Error loading batch report: {str(e)}", "danger")
        return redirect(url_for('prediction.batch'))
