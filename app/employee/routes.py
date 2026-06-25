from flask import render_template, url_for, flash, redirect, request
from flask_login import login_required
from app.extensions import db
from app.employee import employee_bp
from app.models.employee import Employee

@employee_bp.route("/")
@login_required
def list_employees():
    page = request.args.get('page', 1, type=int)
    search_query = request.args.get('search', '').strip()
    dept_filter = request.args.get('department', '').strip()
    ot_filter = request.args.get('overtime', '').strip()
    
    query = Employee.query
    
    if search_query:
        # Search by employee_id, first_name, or last_name
        query = query.filter(
            Employee.employee_id.ilike(f"%{search_query}%") |
            Employee.first_name.ilike(f"%{search_query}%") |
            Employee.last_name.ilike(f"%{search_query}%")
        )
        
    if dept_filter:
        query = query.filter(Employee.department == dept_filter)
        
    if ot_filter:
        is_ot = ot_filter == 'true'
        query = query.filter(Employee.overtime == is_ot)
        
    # Paginate (10 employees per page)
    pagination = query.order_by(Employee.created_at.desc()).paginate(page=page, per_page=10, error_out=False)
    employees = pagination.items
    
    return render_template(
        "employee/list.html", 
        title="Employees", 
        employees=employees,
        pagination=pagination,
        search=search_query,
        department=dept_filter,
        overtime=ot_filter
    )

@employee_bp.route("/add", methods=['GET', 'POST'])
@login_required
def add_employee():
    if request.method == 'POST':
        # Base core information
        employee_data = {
            "employee_id": request.form.get("employee_id"),
            "first_name": request.form.get("first_name"),
            "last_name": request.form.get("last_name"),
        }

        # Parse string fields
        str_fields = ['business_travel', 'department', 'education_field', 'gender', 'job_role', 'marital_status']
        for field in str_fields:
            employee_data[field] = request.form.get(field)

        # Parse integer fields
        int_fields = [
            'age', 'daily_rate', 'distance_from_home', 'education', 'employee_number', 
            'environment_satisfaction', 'hourly_rate', 'job_involvement', 'job_level', 
            'job_satisfaction', 'monthly_rate', 'num_companies_worked', 'percent_salary_hike', 
            'performance_rating', 'relationship_satisfaction', 'stock_option_level', 
            'total_working_years', 'training_times_last_year', 'work_life_balance', 
            'years_at_company', 'years_in_current_role', 'years_since_last_promotion', 
            'years_with_curr_manager'
        ]
        try:
            for field in int_fields:
                val = request.form.get(field)
                employee_data[field] = int(val) if val and val.strip() != "" else None

            # Parse float fields
            val = request.form.get("monthly_income")
            employee_data["monthly_income"] = float(val) if val and val.strip() != "" else None
        except ValueError:
            flash("Invalid format for numeric inputs.", "danger")
            return redirect(url_for('employee.add_employee'))

        # Parse boolean fields
        employee_data['overtime'] = request.form.get('overtime') == 'true'
        
        # Simple server-side validation
        if not employee_data["employee_id"] or not employee_data["first_name"] or not employee_data["last_name"]:
            flash("Employee ID, First Name and Last Name are required.", "danger")
            return redirect(url_for('employee.add_employee'))
            
        existing = Employee.query.filter_by(employee_id=employee_data["employee_id"]).first()
        if existing:
            flash(f"An employee with ID {employee_data['employee_id']} already exists.", "danger")
            return redirect(url_for('employee.add_employee'))
            
        employee = Employee(**employee_data)
        db.session.add(employee)
        db.session.commit()
        flash("Employee successfully added!", "success")
        return redirect(url_for('employee.list_employees'))
        
    return render_template("employee/add.html", title="Add Employee")

@employee_bp.route("/<string:employee_id>")
@login_required
def detail(employee_id):
    employee = Employee.query.filter_by(employee_id=employee_id).first_or_404()
    return render_template("employee/detail.html", title=f"Employee - {employee.full_name}", employee=employee)

@employee_bp.route("/edit/<string:employee_id>", methods=['GET', 'POST'])
@login_required
def edit_employee(employee_id):
    employee = Employee.query.filter_by(employee_id=employee_id).first_or_404()
    
    if request.method == 'POST':
        # Extracted data structure
        employee_data = {}
        
        # Parse string fields
        str_fields = ['business_travel', 'department', 'education_field', 'gender', 'job_role', 'marital_status']
        for field in str_fields:
            employee_data[field] = request.form.get(field)

        # Parse integer fields
        int_fields = [
            'age', 'daily_rate', 'distance_from_home', 'education', 'employee_number', 
            'environment_satisfaction', 'hourly_rate', 'job_involvement', 'job_level', 
            'job_satisfaction', 'monthly_rate', 'num_companies_worked', 'percent_salary_hike', 
            'performance_rating', 'relationship_satisfaction', 'stock_option_level', 
            'total_working_years', 'training_times_last_year', 'work_life_balance', 
            'years_at_company', 'years_in_current_role', 'years_since_last_promotion', 
            'years_with_curr_manager'
        ]
        try:
            for field in int_fields:
                val = request.form.get(field)
                employee_data[field] = int(val) if val and val.strip() != "" else None

            # Parse float fields
            val = request.form.get("monthly_income")
            employee_data["monthly_income"] = float(val) if val and val.strip() != "" else None
        except ValueError:
            flash("Invalid format for numeric inputs.", "danger")
            return redirect(url_for('employee.edit_employee', employee_id=employee_id))

        # Parse boolean fields
        employee_data['overtime'] = request.form.get('overtime') == 'true'
        
        # Populate fields
        employee.first_name = request.form.get("first_name")
        employee.last_name = request.form.get("last_name")
        
        if not employee.first_name or not employee.last_name:
            flash("First Name and Last Name are required.", "danger")
            return redirect(url_for('employee.edit_employee', employee_id=employee_id))
            
        # Dynamically set remaining attributes
        for key, val in employee_data.items():
            setattr(employee, key, val)
            
        db.session.commit()
        flash("Employee profile successfully updated!", "success")
        return redirect(url_for('employee.detail', employee_id=employee.employee_id))
        
    return render_template("employee/edit.html", title="Edit Employee", employee=employee)

@employee_bp.route("/delete/<string:employee_id>", methods=['POST'])
@login_required
def delete_employee(employee_id):
    employee = Employee.query.filter_by(employee_id=employee_id).first_or_404()
    db.session.delete(employee)
    db.session.commit()
    flash(f"Employee {employee.full_name} and their prediction logs have been deleted.", "success")
    return redirect(url_for('employee.list_employees'))
