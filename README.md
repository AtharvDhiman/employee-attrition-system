# RetainAI - Employee Attrition & Predictive HR Insights System

RetainAI is a premium, data-driven web platform designed to analyze employee demographics, financial metrics, and engagement variables to predict attrition risk. Built on Flask and powered by a machine learning classification engine, the system delivers visual cohort analytics, batch upload processing, strategic HR playbooks, and a conversational HR AI Assistant.

---

## 🚀 Key Features

* **Advanced Predictive ML Engine:**
  - Evaluates Logistic Regression, Random Forest, and Gradient Boosting algorithms on a 30-feature HR dataset.
  - Automatically selects the winner model (Gradient Boosting Classifier) based on **F1-Score (91.6%)** and **ROC-AUC (92.7%)**.
  - Dynamically calculates **Local AI Explanations** to rank and display the top 4 risk drivers (e.g. Overtime Strain, Job Satisfaction, Compensation Gaps) for high-risk profiles, or retention pillars for stable employees.
* **HR AI Assistant Chatbot:**
  - Modern conversational ChatGPT-style layout with suggested query chips.
  - State-free keyword-based local NLP parser that runs real-time SQLite analytics.
  - Answers workforce stats, specific employee details, department risks, and dynamic driver questions (*"Why is employee attrition high?"*).
* **Comparative Cohort Analytics:**
  - Segments the workforce into High Attrition Risk vs. Low Attrition Risk cohorts.
  - Renders a 2x2 grid of high-DPI bar charts (income, engagement, work friction, tenure) comparing both groups.
  - Triggers strategic playbooks offering targeted retention recommendations based on cohort metric variances.
* **Batch Upload & CSV Reports:**
  - Interactive drag-and-drop CSV uploader interface with real-time feedback.
  - Processes batches of employee profiles, updates/saves records, executes predictions, and builds downloadable reports.
  - Displays summary statistics and Doughnut charts of upload risk distribution.
* **Employee Directory (CRUD):**
  - Fully featured directory with Name/ID search, Department and Overtime filters, and pagination.
  - Profile detail pages with radial probability graphics and action logs.
  - Database relational cascades to safely delete employee files and history.
* **High-DPI Retina Sharpness:**
  - Chart.js scaled with pixel density options to guarantee high-DPI sharpness on standard and retina monitors.

---

## 🛠️ Tech Stack

* **Backend:** Python, Flask, Flask-SQLAlchemy (SQLite / PostgreSQL ready), Flask-Login, Flask-WTF
* **Frontend:** Vanilla HTML5, CSS3, Javascript, Chart.js, FontAwesome Icons
* **Data Science & ML:** Scikit-Learn, Pandas, NumPy, Joblib, Gunicorn

---

## 💻 Local Installation & Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/AtharvDhiman/employee-attrition-system.git
   cd employee-attrition-system
   ```

2. **Create and activate a virtual environment:**
   ```bash
   python -m venv .venv
   # Windows (PowerShell):
   .venv\Scripts\Activate.ps1
   # macOS/Linux:
   source .venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Train the ML model & generate synthetic data:**
   ```bash
   python app/ml/train.py
   ```
   *This creates `dataset/employee_attrition.csv` and serializes the winning model pipeline to `app/ml/model.joblib`.*

5. **Run the application locally:**
   ```bash
   python app.py
   ```
   *Open http://127.0.0.1:5000 in your browser. Default Admin Credentials:*
   - **Username:** `hr_admin`
   - **Password:** `password123`

---

## 🧪 Running Unit Tests

To run the full suite of unit tests validating database models, CRUD filters, chatbot responses, and ML prediction dimensions:
```bash
python -m unittest discover tests
```

---

## 🌐 Production Deployment

The project is fully configured for deployment on **Render** (or similar web hosting platforms) via the blueprint specification:

* **Configuration file:** `render.yaml` in the root folder.
* **Persistent Disk:** Creates a 1 GB persistent SQLite disk mounted at `/data/app.db` so database records persist across server restarts.
* **Gunicorn Server:** Uses `gunicorn app:app` for high-performance WSGI production serving.
