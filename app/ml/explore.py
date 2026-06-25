import os
import pandas as pd
import numpy as np

def run_exploration():
    print("================================================== ")
    print("RetainAI - Dataset Exploration & Preprocessing")
    print("================================================== \n")
    
    csv_path = 'dataset/employee_attrition.csv'
    
    # Generate dataset if it does not exist
    if not os.path.exists(csv_path):
        print(f"Dataset not found at '{csv_path}'. Generating synthetic dataset...")
        from app.ml.train import generate_synthetic_data
        df = generate_synthetic_data(num_records=1200)
        os.makedirs('dataset', exist_ok=True)
        df.to_csv(csv_path, index=False)
        print(f"Synthetic dataset saved to: {csv_path}\n")
    else:
        df = pd.read_csv(csv_path)
        print(f"Loaded existing dataset from '{csv_path}'.")
        
    print(f"Total Records: {df.shape[0]}")
    print(f"Total Features: {df.shape[1]}\n")
    
    # Target distribution
    target_counts = df['Attrition'].value_counts()
    target_pcts = df['Attrition'].value_counts(normalize=True) * 100
    print("Target Variable Distribution (Attrition):")
    for val in target_counts.index:
        print(f" - {val}: {target_counts[val]} ({target_pcts[val]:.1f}%)")
    print()
    
    # Encode target for correlation analysis
    df_numeric = df.copy()
    df_numeric['Attrition_Encoded'] = df_numeric['Attrition'].map({'Yes': 1, 'No': 0})
    
    # Exclude non-predictive/constant columns
    exclude_cols = ['Attrition', 'EmployeeNumber', 'EmployeeCount', 'StandardHours', 'Over18', 'Attrition_Encoded']
    numeric_cols = df_numeric.select_dtypes(include=[np.number]).columns
    numeric_cols = [c for c in numeric_cols if c not in exclude_cols]
    
    # Calculate correlations
    correlations = {}
    for col in numeric_cols:
        corr = df_numeric['Attrition_Encoded'].corr(df_numeric[col])
        correlations[col] = corr
        
    # Sort correlations by absolute value
    sorted_corr = sorted(correlations.items(), key=lambda x: abs(x[1]), reverse=True)
    
    print("Feature Correlations with Attrition (Top 5 Numeric):")
    for col, corr in sorted_corr[:5]:
        direction = "Positive" if corr > 0 else "Negative"
        print(f" - {col}: {corr:.4f} ({direction} correlation)")
    print()
    
    # Categorical fields analysis (specifically Overtime)
    print("Categorical Feature Analysis (Attrition Rate Impact):")
    if 'OverTime' in df.columns:
        ot_attrition = df.groupby('OverTime')['Attrition'].value_counts(normalize=True).unstack() * 100
        print(" - Overtime Impact:")
        print(f"   • Works Overtime: Attrition Rate = {ot_attrition.loc['Yes', 'Yes']:.1f}%")
        print(f"   • No Overtime: Attrition Rate = {ot_attrition.loc['No', 'Yes']:.1f}%")
    print()
    
    # Explain Preprocessing
    categorical_cols = df.drop(columns=['Attrition', 'EmployeeNumber', 'EmployeeCount', 'StandardHours', 'Over18']).select_dtypes(include=['object']).columns.tolist()
    num_cols_list = df.drop(columns=['Attrition', 'EmployeeNumber', 'EmployeeCount', 'StandardHours', 'Over18']).select_dtypes(include=[np.number]).columns.tolist()
    
    print("Preprocessing Pipeline Summary:")
    print(f" - Numerical Features ({len(num_cols_list)}): Scaling via StandardScaler")
    print(f" - Categorical Features ({len(categorical_cols)}): One-Hot Encoding (handle_unknown='ignore')")
    print(f" - Excluded Features: EmployeeNumber, EmployeeCount, StandardHours, Over18 (non-predictive/constants)\n")
    
    # Save report
    report_path = 'dataset/exploration_summary.txt'
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("RetainAI Dataset Exploration Summary\n")
        f.write("=====================================\n\n")
        f.write(f"Total Records: {df.shape[0]}\n")
        f.write(f"Total Features: {df.shape[1]}\n\n")
        f.write("Target Variable Distribution (Attrition):\n")
        for val in target_counts.index:
            f.write(f" - {val}: {target_counts[val]} ({target_pcts[val]:.1f}%)\n")
        f.write("\nTop Correlations with Attrition:\n")
        for col, corr in sorted_corr:
            f.write(f" - {col}: {corr:.4f}\n")
        f.write("\nPreprocessing configuration:\n")
        f.write(f" - Numeric columns: {num_cols_list}\n")
        f.write(f" - Categorical columns: {categorical_cols}\n")
        
    print(f"Saved complete exploration report to: {report_path}")
    print("================================================== ")

if __name__ == '__main__':
    run_exploration()
