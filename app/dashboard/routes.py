from flask import render_template, request, jsonify
from flask_login import login_required
from app.extensions import db
from app.dashboard import dashboard_bp
from app.models.employee import Employee
from app.models.prediction import Prediction

@dashboard_bp.route("/")
@login_required
def index():
    total_employees = Employee.query.count()
    total_predictions = Prediction.query.count()
    
    # Calculate some dashboard stats
    high_risk_count = Prediction.query.filter_by(prediction_class=True).count()
    recent_predictions = Prediction.query.order_by(Prediction.run_at.desc()).limit(5).all()
    
    # Attrition by Department
    dept_stats = db.session.query(
        Employee.department, 
        db.func.count(Prediction.id)
    ).join(Prediction).filter(Prediction.prediction_class == True).group_by(Employee.department).all()
    
    dept_data = {dept: count for dept, count in dept_stats}
    departments = ['Sales', 'Research & Development', 'Human Resources']
    dept_counts = [dept_data.get(dept, 0) for dept in departments]
    
    # Attrition by Overtime
    ot_stats = db.session.query(
        Employee.overtime, 
        db.func.count(Prediction.id)
    ).join(Prediction).filter(Prediction.prediction_class == True).group_by(Employee.overtime).all()
    
    ot_data = {ot: count for ot, count in ot_stats}
    ot_counts = [ot_data.get(True, 0), ot_data.get(False, 0)] # Overtime, No Overtime
    
    # Attrition by Job Satisfaction
    sat_stats = db.session.query(
        Employee.job_satisfaction, 
        db.func.count(Prediction.id)
    ).join(Prediction).filter(Prediction.prediction_class == True).group_by(Employee.job_satisfaction).all()
    
    sat_data = {sat: count for sat, count in sat_stats}
    sat_counts = [sat_data.get(i, 0) for i in range(1, 5)] # 1, 2, 3, 4
    
    return render_template(
        "dashboard/index.html",
        title="Dashboard",
        total_employees=total_employees,
        total_predictions=total_predictions,
        high_risk_count=high_risk_count,
        recent_predictions=recent_predictions,
        departments=departments,
        dept_counts=dept_counts,
        ot_counts=ot_counts,
        sat_counts=sat_counts
    )

@dashboard_bp.route("/cohort-analytics")
@login_required
def cohort_analytics():
    # Subquery to get the latest prediction run_at for each employee
    subquery = db.session.query(
        Prediction.employee_id,
        db.func.max(Prediction.run_at).label('max_run_at')
    ).group_by(Prediction.employee_id).subquery()
    
    # Join employees with their latest prediction
    latest_predictions = db.session.query(Employee, Prediction).join(
        Prediction, Employee.employee_id == Prediction.employee_id
    ).join(
        subquery, 
        (Prediction.employee_id == subquery.c.employee_id) & 
        (Prediction.run_at == subquery.c.max_run_at)
    ).all()
    
    high_risk_list = []
    low_risk_list = []
    
    for emp, pred in latest_predictions:
        if pred.prediction_class:
            high_risk_list.append(emp)
        else:
            low_risk_list.append(emp)
            
    # Helper to calculate mean of an attribute
    def get_mean(cohort, attr):
        vals = [getattr(emp, attr) for emp in cohort if getattr(emp, attr) is not None]
        return sum(vals) / len(vals) if vals else 0.0
        
    def get_pct_true(cohort, attr):
        vals = [getattr(emp, attr) for emp in cohort if getattr(emp, attr) is not None]
        if not vals:
            return 0.0
        return (sum(1 for v in vals if v is True) / len(vals)) * 100
        
    stats = {
        'high': {
            'count': len(high_risk_list),
            'avg_income': round(get_mean(high_risk_list, 'monthly_income'), 2),
            'avg_satisfaction': round(get_mean(high_risk_list, 'job_satisfaction'), 2),
            'avg_work_life': round(get_mean(high_risk_list, 'work_life_balance'), 2),
            'ot_rate': round(get_pct_true(high_risk_list, 'overtime'), 1),
            'avg_years': round(get_mean(high_risk_list, 'years_at_company'), 1),
            'avg_distance': round(get_mean(high_risk_list, 'distance_from_home'), 1),
            'avg_env_satisfaction': round(get_mean(high_risk_list, 'environment_satisfaction'), 2),
            'avg_involvement': round(get_mean(high_risk_list, 'job_involvement'), 2),
            'avg_years_role': round(get_mean(high_risk_list, 'years_in_current_role'), 1),
            'avg_years_promotion': round(get_mean(high_risk_list, 'years_since_last_promotion'), 1)
        },
        'low': {
            'count': len(low_risk_list),
            'avg_income': round(get_mean(low_risk_list, 'monthly_income'), 2),
            'avg_satisfaction': round(get_mean(low_risk_list, 'job_satisfaction'), 2),
            'avg_work_life': round(get_mean(low_risk_list, 'work_life_balance'), 2),
            'ot_rate': round(get_pct_true(low_risk_list, 'overtime'), 1),
            'avg_years': round(get_mean(low_risk_list, 'years_at_company'), 1),
            'avg_distance': round(get_mean(low_risk_list, 'distance_from_home'), 1),
            'avg_env_satisfaction': round(get_mean(low_risk_list, 'environment_satisfaction'), 2),
            'avg_involvement': round(get_mean(low_risk_list, 'job_involvement'), 2),
            'avg_years_role': round(get_mean(low_risk_list, 'years_in_current_role'), 1),
            'avg_years_promotion': round(get_mean(low_risk_list, 'years_since_last_promotion'), 1)
        }
    }
    
    return render_template(
        "dashboard/cohort_analytics.html",
        title="Cohort Analytics",
        stats=stats
    )

@dashboard_bp.route("/chat")
@login_required
def chat_view():
    return render_template("dashboard/chat.html", title="HR AI Chatbot")

@dashboard_bp.route("/chat/query", methods=['POST'])
@login_required
def chat_query():
    data = request.get_json()
    if not data or 'query' not in data:
        return jsonify({'response': "Please provide a valid query."}), 400
        
    query = data['query'].strip().lower()
    # Strip punctuation for cleaner keyword matching
    clean_query = "".join(c for c in query if c.isalnum() or c.isspace())
    clean_words = set(clean_query.split())
    
    # Imports inside route to avoid circular dependency
    from app.models.employee import Employee
    from app.models.prediction import Prediction
    from app.extensions import db
    
    # 1. GREETINGS & HELP
    greeting_words = {'hi', 'hello', 'hey', 'greetings', 'help'}
    if (clean_words & greeting_words) or 'what can you do' in clean_query:
        response = (
            "Hello! I am your RetainAI HR assistant. I can query real-time database statistics and employee records. "
            "Here are some examples of what you can ask me:\n\n"
            "• **Employee Risk Details:** *'Is Alice Smith at risk?'* or *'Show risk for EMP1001'*\n"
            "• **Workforce Overviews:** *'List high risk employees'* or *'Who has the highest risk?'*\n"
            "• **Department Analytics:** *'Risk in Sales'* or *'Which department has the highest risk?'*\n"
            "• **Playbook Recommendations:** *'How can I retain EMP1002?'*"
        )
        return jsonify({'response': response})
        
    # 2. WHY IS ATTRITION HIGH / CAUSES OF ATTRITION
    if any(k in clean_query for k in ['why is attrition', 'why is employee attrition', 'what causes attrition', 'why are employees leaving', 'attrition reasons', 'attrition factors', 'attrition drivers', 'main drivers']):
        subquery = db.session.query(
            Prediction.employee_id,
            db.func.max(Prediction.run_at).label('max_run_at')
        ).group_by(Prediction.employee_id).subquery()
        
        latest_predictions = db.session.query(Employee, Prediction).join(
            Prediction, Employee.employee_id == Prediction.employee_id
        ).join(
            subquery, 
            (Prediction.employee_id == subquery.c.employee_id) & 
            (Prediction.run_at == subquery.c.max_run_at)
        ).all()
        
        high_risk_list = []
        low_risk_list = []
        
        for emp, pred in latest_predictions:
            if pred.prediction_class:
                high_risk_list.append(emp)
            else:
                low_risk_list.append(emp)
                
        if not latest_predictions:
            response = "I couldn't calculate attrition drivers because there are no prediction records in the database. Please run predictions first."
            return jsonify({'response': response})
            
        def get_mean(cohort, attr):
            vals = [getattr(emp, attr) for emp in cohort if getattr(emp, attr) is not None]
            return sum(vals) / len(vals) if vals else 0.0
            
        def get_pct_true(cohort, attr):
            vals = [getattr(emp, attr) for emp in cohort if getattr(emp, attr) is not None]
            if not vals:
                return 0.0
            return (sum(1 for v in vals if v is True) / len(vals)) * 100

        avg_income_high = get_mean(high_risk_list, 'monthly_income')
        avg_income_low = get_mean(low_risk_list, 'monthly_income')
        income_diff_pct = ((avg_income_low - avg_income_high) / avg_income_low * 100) if avg_income_low > 0 else 0.0
        
        ot_rate_high = get_pct_true(high_risk_list, 'overtime')
        ot_rate_low = get_pct_true(low_risk_list, 'overtime')
        
        avg_sat_high = get_mean(high_risk_list, 'job_satisfaction')
        avg_sat_low = get_mean(low_risk_list, 'job_satisfaction')
        
        avg_wlb_high = get_mean(high_risk_list, 'work_life_balance')
        avg_wlb_low = get_mean(low_risk_list, 'work_life_balance')
        
        avg_promo_high = get_mean(high_risk_list, 'years_since_last_promotion')
        avg_promo_low = get_mean(low_risk_list, 'years_since_last_promotion')
        
        response = (
            "### 📊 Attrition Driver Analysis\n"
            "Based on the latest ML predictions and employee metrics in our database, here is why attrition risk is elevated:\n\n"
            f"• **Overtime Strain:** **{ot_rate_high:.1f}%** of high-risk employees work overtime, compared to only **{ot_rate_low:.1f}%** of low-risk employees.\n"
            f"• **Compensation Gaps:** High-risk employees earn an average of **${avg_income_high:,.2f}/mo**, which is **{income_diff_pct:.1f}% lower** than low-risk employees (${avg_income_low:,.2f}/mo).\n"
            f"• **Job Satisfaction:** High-risk employees report an average job satisfaction of **{avg_sat_high:.1f}/4** (vs **{avg_sat_low:.1f}/4** for stable employees).\n"
            f"• **Work-Life Balance:** The average work-life balance for high-risk employees is **{avg_wlb_high:.1f}/4** (vs **{avg_wlb_low:.1f}/4** for stable employees).\n"
            f"• **Career Stagnation:** High-risk employees have spent an average of **{avg_promo_high:.1f} years** since their last promotion vs **{avg_promo_low:.1f} years** for low-risk employees.\n\n"
            "**Recommended Action:** Target these friction points by reducing overtime workloads, adjusting compensation for high performers, and scheduling career reviews."
        )
        return jsonify({'response': response})

    # 3. HIGHEST RISK
    if any(k in clean_query for k in ['highest risk', 'most likely to leave', 'worst risk']):
        # Find prediction with highest risk score
        subquery = db.session.query(
            Prediction.employee_id,
            db.func.max(Prediction.run_at).label('max_run_at')
        ).group_by(Prediction.employee_id).subquery()
        
        highest_pred = db.session.query(Employee, Prediction).join(
            Prediction, Employee.employee_id == Prediction.employee_id
        ).join(
            subquery,
            (Prediction.employee_id == subquery.c.employee_id) &
            (Prediction.run_at == subquery.c.max_run_at)
        ).order_by(Prediction.risk_score.desc()).first()
        
        if highest_pred:
            emp, pred = highest_pred
            response = (
                f"The employee with the highest attrition risk is **{emp.full_name}** (ID: `{emp.employee_id}`) "
                f"with a risk score of **{int(pred.risk_score * 100)}%** (High Risk).\n\n"
                f"**Key factors:**\n"
                f"• Department: {emp.department or 'N/A'}\n"
                f"• Overtime: {'Yes' if emp.overtime else 'No'}\n"
                f"• Job Satisfaction: {emp.job_satisfaction or 'N/A'}/4\n\n"
                f"**Playbook Recommendation:** {pred.recommended_actions.split('\n')[0] if pred.recommended_actions else 'Monitor closely.'}"
            )
        else:
            response = "No prediction records found in the database. Please run predictions first."
        return jsonify({'response': response})
        
    # 3. LIST HIGH RISK EMPLOYEES
    if any(k in clean_query for k in ['list high risk', 'who is at risk', 'flagged employees', 'at risk']):
        subquery = db.session.query(
            Prediction.employee_id,
            db.func.max(Prediction.run_at).label('max_run_at')
        ).group_by(Prediction.employee_id).subquery()
        
        high_risk = db.session.query(Employee, Prediction).join(
            Prediction, Employee.employee_id == Prediction.employee_id
        ).join(
            subquery,
            (Prediction.employee_id == subquery.c.employee_id) &
            (Prediction.run_at == subquery.c.max_run_at)
        ).filter(Prediction.prediction_class == True).order_by(Prediction.risk_score.desc()).all()
        
        if high_risk:
            lines = [f"I found **{len(high_risk)}** employees currently flagged as **High Attrition Risk**:\n"]
            for emp, pred in high_risk[:10]: # Limit to top 10
                lines.append(f"• **{emp.full_name}** (`{emp.employee_id}`) — **{int(pred.risk_score * 100)}%** (Dept: {emp.department or 'N/A'})")
            if len(high_risk) > 10:
                lines.append(f"\n*...and {len(high_risk) - 10} more. View all in the Employees directory.*")
            response = "\n".join(lines)
        else:
            response = "Excellent news! There are currently no employees flagged as High Attrition Risk in the database."
        return jsonify({'response': response})

    # 4. DEPARTMENT ANALYSIS
    if 'department' in clean_query or 'dept' in clean_query or 'sales' in clean_query or 'engineering' in clean_query or 'research' in clean_query or 'human resources' in clean_query or 'hr' in clean_query:
        # Check specific department
        target_dept = None
        if 'sales' in clean_query:
            target_dept = 'Sales'
        elif 'research' in clean_query or 'development' in clean_query or 'rd' in clean_query:
            target_dept = 'Research & Development'
        elif 'human resources' in clean_query or 'hr' in clean_query:
            target_dept = 'Human Resources'
            
        subquery = db.session.query(
            Prediction.employee_id,
            db.func.max(Prediction.run_at).label('max_run_at')
        ).group_by(Prediction.employee_id).subquery()
        
        if target_dept:
            # Stats for specific department
            dept_employees = Employee.query.filter_by(department=target_dept).all()
            if not dept_employees:
                return jsonify({'response': f"No employees found in the '{target_dept}' department."})
                
            dept_preds = db.session.query(Prediction).join(
                subquery,
                (Prediction.employee_id == subquery.c.employee_id) &
                (Prediction.run_at == subquery.c.max_run_at)
            ).join(Employee).filter(Employee.department == target_dept).all()
            
            high_count = sum(1 for p in dept_preds if p.prediction_class)
            avg_score = (sum(p.risk_score for p in dept_preds) / len(dept_preds)) * 100 if dept_preds else 0.0
            
            response = (
                f"### Department Report: **{target_dept}**\n"
                f"• Total Employees: **{len(dept_employees)}**\n"
                f"• High Attrition Risk: **{high_count}** employees\n"
                f"• Average Risk Score: **{avg_score:.1f}%**\n\n"
                f"**Strategic Advice:** "
            )
            if high_count > 0:
                response += f"Review the {high_count} flagged profiles. Check for department-wide issues like overtime load."
            else:
                response += "The department is currently stable with low attrition indicators."
        else:
            # General department comparison
            dept_stats = db.session.query(
                Employee.department,
                db.func.count(Employee.id)
            ).group_by(Employee.department).all()
            
            lines = ["Here is a summary of attrition risks across departments:\n"]
            for dept, count in dept_stats:
                if not dept: continue
                # Count high risk in dept
                dept_high = db.session.query(Prediction).join(
                    subquery,
                    (Prediction.employee_id == subquery.c.employee_id) &
                    (Prediction.run_at == subquery.c.max_run_at)
                ).join(Employee).filter((Employee.department == dept) & (Prediction.prediction_class == True)).count()
                lines.append(f"• **{dept}**: {count} employees, **{dept_high}** at high risk")
            response = "\n".join(lines)
        return jsonify({'response': response})

    # 5. SPECIFIC EMPLOYEE SEARCH (by ID or Name)
    words = clean_query.split()
    emp_match = None
    
    # Try searching by ID
    for word in words:
        if 'emp' in word or word.isalnum():
            emp_match = Employee.query.filter(Employee.employee_id.ilike(f"%{word}%")).first()
            if emp_match:
                break
                
    # Try searching by name
    if not emp_match:
        for word in words:
            if len(word) > 2 and word not in ['show', 'risk', 'info', 'about', 'find', 'retain']:
                emp_match = Employee.query.filter(
                    Employee.first_name.ilike(f"%{word}%") | 
                    Employee.last_name.ilike(f"%{word}%")
                ).first()
                if emp_match:
                    break
                    
    if emp_match:
        # Get latest prediction
        latest_pred = Prediction.query.filter_by(employee_id=emp_match.employee_id).order_by(Prediction.run_at.desc()).first()
        score_text = "N/A"
        class_text = "No Prediction Run"
        recs_text = "Run a risk assessment from their profile to get recommendations."
        
        if latest_pred:
            score_text = f"{int(latest_pred.risk_score * 100)}%"
            class_text = "**High Attrition Risk**" if latest_pred.prediction_class else "**Low Attrition Risk**"
            recs_text = latest_pred.recommended_actions.replace('\n', '\n• ') if latest_pred.recommended_actions else 'Monitor engagement.'
            
        response = (
            f"### Employee Risk Assessment: **{emp_match.full_name}** (`{emp_match.employee_id}`)\n"
            f"• **Role:** {emp_match.job_role or 'N/A'} (Dept: {emp_match.department or 'N/A'})\n"
            f"• **Current Risk Level:** {class_text} ({score_text})\n"
            f"• **Monthly Income:** ${emp_match.monthly_income or 'N/A'}\n"
            f"• **Overtime Works:** {'Yes' if emp_match.overtime else 'No'}\n\n"
            f"**Recommended Playbook Actions:**\n• {recs_text}"
        )
        return jsonify({'response': response})

    # 6. DEFAULT FALLBACK
    response = (
        "I'm sorry, I couldn't find matches in the database for your query. "
        "Try asking me things like:\n"
        "• *'Who is the employee with the highest risk?'*\n"
        "• *'List all employees at risk'* or *'Show risk in Sales department'*\n"
        "• *'Is John Doe at risk?'* (Use employee names or IDs)"
    )
    return jsonify({'response': response})
