import pandas as pd
import os
import numpy as np
from datetime import datetime

NEW_CASES_FILE = "new_case_logs.csv"

def load_and_merge_data(data_folder):
    """Loads CSVs, filters out bad rows (Cyber Cell, Total), and merges logs."""
    try:
        # 1. Load Original Data
        df_stats = pd.read_csv(os.path.join(data_folder, "03_accidents.csv"))
        df_accidents = pd.read_csv(os.path.join(data_folder, "05_crime_rate.csv"))
        df_murders = pd.read_csv(os.path.join(data_folder, "06_complaints.csv"))
        df_suicides = pd.read_csv(os.path.join(data_folder, "01_suicides.csv"))
        df_harassment = pd.read_csv(os.path.join(data_folder, "02_harassment.csv"))
        
        # Standardize 'District' Column
        for df in [df_stats, df_accidents, df_murders, df_suicides, df_harassment]:
            if 'Districts' in df.columns: df.rename(columns={'Districts': 'District'}, inplace=True)

        # Base Merge
        df_final = df_stats[['District', '2022', 'Projected population (lakhs)']].copy()
        df_final.rename(columns={'2022': 'Total_Crime_Count_2022', 'Projected population (lakhs)': 'Population'}, inplace=True)
        
        # Clean Population
        df_final['Population'] = pd.to_numeric(df_final['Population'].astype(str).str.replace(',', ''), errors='coerce').fillna(1)

        # Merge Categories
        df_final = df_final.merge(df_accidents[['District', 'Total Road Accidents - Incidence']], on='District', how='left').rename(columns={'Total Road Accidents - Incidence': 'Road_Accidents'})
        df_final = df_final.merge(df_murders[['District', 'Murder -Incidence']], on='District', how='left').rename(columns={'Murder -Incidence': 'Murder'})
        df_final = df_final.merge(df_suicides[['District', 'Total']], on='District', how='left').rename(columns={'Total': 'Suicides'})
        df_final = df_final.merge(df_harassment[['District', 'Sexual Harrassment Total - I']], on='District', how='left').rename(columns={'Sexual Harrassment Total - I': 'Harassment'})
        
        df_final.fillna(0, inplace=True)

        # --- 🔥 CRITICAL FIX: REMOVE FAKE DISTRICTS ---
        ignore_words = ["TOTAL", "Total", "Cyber", "Railway", "CID", "Unit", "Zone", "Range", "Pool"]
        df_final = df_final[~df_final['District'].str.contains('|'.join(ignore_words), case=False, na=False)]
        # -----------------------------------------------

        # Integrate New Logs
        log_path = os.path.join(data_folder, NEW_CASES_FILE)
        if os.path.exists(log_path):
            try:
                df_logs = pd.read_csv(log_path)
                if not df_logs.empty:
                    summary = df_logs.groupby(['District', 'Crime_Type']).size().unstack(fill_value=0)
                    for district in summary.index:
                        if district in df_final['District'].values:
                            if 'Theft' in summary.columns: 
                                df_final.loc[df_final['District'] == district, 'Total_Crime_Count_2022'] += summary.loc[district, 'Theft']
                            if 'Murder' in summary.columns:
                                df_final.loc[df_final['District'] == district, 'Murder'] += summary.loc[district, 'Murder']
                                df_final.loc[df_final['District'] == district, 'Total_Crime_Count_2022'] += summary.loc[district, 'Murder']
                            if 'Accident' in summary.columns:
                                df_final.loc[df_final['District'] == district, 'Road_Accidents'] += summary.loc[district, 'Accident']
                            if 'Harassment' in summary.columns:
                                df_final.loc[df_final['District'] == district, 'Harassment'] += summary.loc[district, 'Harassment']
                            if 'Suicide' in summary.columns:
                                df_final.loc[df_final['District'] == district, 'Suicides'] += summary.loc[district, 'Suicide']
            except Exception as e:
                print(f"⚠️ Error merging logs: {e}")

        # Recalculate Scores
        df_final['Crime_Rate_2022'] = df_final['Total_Crime_Count_2022'] / df_final['Population']
        
        df_final['Severity_Score'] = (
            (df_final['Murder'] * 10) + 
            (df_final['Harassment'] * 5) + 
            (df_final['Road_Accidents'] * 2) + 
            (df_final['Total_Crime_Count_2022'] * 0.5)
        )
        
        max_score = df_final['Severity_Score'].max()
        if max_score > 0: df_final['Severity_Score'] = (df_final['Severity_Score'] / max_score) * 100
        
        df_final['Projected_Risk'] = df_final['Severity_Score'] * 1.05 
        
        # Remove Infinity/NaN
        df_final = df_final.replace([np.inf, -np.inf], 0)
        df_final.fillna(0, inplace=True)
        
        return df_final

    except Exception as e:
        print(f"❌ Data Load Error: {e}")
        return pd.DataFrame()

def append_new_case(data_folder, district, crime_type, description, severity):
    try:
        log_path = os.path.join(data_folder, NEW_CASES_FILE)
        if not os.path.exists(log_path):
            df = pd.DataFrame(columns=["Timestamp", "District", "Crime_Type", "Description", "Severity"])
            df.to_csv(log_path, index=False)
            
        new_row = {
            "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "District": district,
            "Crime_Type": crime_type,
            "Description": description,
            "Severity": severity
        }
        df = pd.DataFrame([new_row])
        df.to_csv(log_path, mode='a', header=False, index=False)
        return True
    except Exception as e:
        print(f"Error logging case: {e}")
        return False