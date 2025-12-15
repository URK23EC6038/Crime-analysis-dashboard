import pandas as pd
import glob
import os

# --- CRITICAL: Customize this section ---
# This function assumes your CSVs can be merged on a 'District' column.
# You MUST adapt this to match your exact CSV structures.
# The goal is ONE master DataFrame.
#
# To make this example runnable, I am creating MOCK data
# if the 6 CSVs aren't found.
# ------------------------------------------

def create_mock_data(data_folder_path):
    print("Warning: CSV files not found. Creating mock data...")
    districts = [
        'Ariyalur', 'Chengalpattu', 'Chennai', 'Coimbatore', 'Cuddalore', 'Dharmapuri', 
        'Dindigul', 'Erode', 'Kallakurichi', 'Kancheepuram', 'Karur', 'Krishnagiri', 
        'Madurai', 'Nagapattinam', 'Kanyakumari', 'Namakkal', 'Perambalur', 'Pudukkottai', 
        'Ramanathapuram', 'Ranipet', 'Salem', 'Sivaganga', 'Tenkasi', 'Thanjavur', 
        'Theni', 'Thoothukudi', 'Tiruchirappalli', 'Tirunelveli', 'Tirupathur', 'Tiruppur', 
        'Tiruvallur', 'Tiruvannamalai', 'Tiruvarur', 'Vellore', 'Viluppuram', 'Virudhunagar'
    ]
    data = []
    for d in districts:
        pop = 10_00_000 + (hash(d) % 15_00_000)
        data.append({
            'District': d,
            'Population': pop,
            'Total_Crime_Count_2022': 500 + (hash(d) % 2500),
            'Total_Crime_Count_2021': 450 + (hash(d) % 2000),
            'Total_Crime_Count_2020': 400 + (hash(d) % 1800),
            'Suicides': 50 + (hash(d) % 300),
            'Harassment': 100 + (hash(d) % 500),
            'Road_Accidents': 200 + (hash(d) % 1000),
            'Deaths': 10 + (hash(d) % 50),
            'Murder': 5 + (hash(d) % 20),
            'Rape': 3 + (hash(d) % 15),
            'Complaints_Registered': 1000 + (hash(d) % 5000)
        })
    df = pd.DataFrame(data)
    # Save mock files to simulate the upload
    df[['District', 'Suicides']].to_csv(os.path.join(data_folder_path, '01_suicides.csv'), index=False)
    df[['District', 'Harassment']].to_csv(os.path.join(data_folder_path, '02_harassment.csv'), index=False)
    df[['District', 'Road_Accidents']].to_csv(os.path.join(data_folder_path, '03_accidents.csv'), index=False)
    df[['District', 'Deaths', 'Murder', 'Rape']].to_csv(os.path.join(data_folder_path, '04_deaths.csv'), index=False)
    df[['District', 'Population', 'Total_Crime_Count_2020', 'Total_Crime_Count_2021', 'Total_Crime_Count_2022']].to_csv(os.path.join(data_folder_path, '05_crime_rate.csv'), index=False)
    df[['District', 'Complaints_Registered']].to_csv(os.path.join(data_folder_path, '06_complaints.csv'), index=False)
    return df

def load_and_merge_data(data_folder_path):
    print("Loading data...")
    file_paths = {
        'suicides': os.path.join(data_folder_path, '01_suicides.csv'),
        'harassment': os.path.join(data_folder_path, '02_harassment.csv'),
        'accidents': os.path.join(data_folder_path, '03_accidents.csv'),
        'deaths': os.path.join(data_folder_path, '04_deaths.csv'),
        'crime_rate': os.path.join(data_folder_path, '05_crime_rate.csv'),
        'complaints': os.path.join(data_folder_path, '06_complaints.csv'),
    }

    try:
        # --- This is where you load your 6 files ---
        # Example:
        df_suicides = pd.read_csv(file_paths['suicides'])
        df_harassment = pd.read_csv(file_paths['harassment'])
        df_accidents = pd.read_csv(file_paths['accidents'])
        df_deaths = pd.read_csv(file_paths['deaths'])
        df_crime_rate = pd.read_csv(file_paths['crime_rate'])
        df_complaints = pd.read_csv(file_paths['complaints'])

        # --- This is where you merge them ---
        # Example: (assumes all have a 'District' column)
        df = pd.merge(df_crime_rate, df_suicides, on='District', how='left')
        df = pd.merge(df, df_harassment, on='District', how='left')
        df = pd.merge(df, df_accidents, on='District', how='left')
        df = pd.merge(df, df_deaths, on='District', how='left')
        df = pd.merge(df, df_complaints, on='District', how='left')

    except FileNotFoundError:
        # If files don't exist, create mock data
        df = create_mock_data(data_folder_path)

    # --- Feature Engineering ---
    # Normalize by population (per 1 Lakh)
    pop_lakh = df['Population'] / 1_00_000
    
    df['Crime_Rate_2022'] = df['Total_Crime_Count_2022'] / pop_lakh
    df['Suicide_Rate'] = df['Suicides'] / pop_lakh
    df['Road_Accident_Rate'] = df['Road_Accidents'] / pop_lakh
    df['Murder_Rate'] = df['Murder'] / pop_lakh
    df['Rape_Rate'] = df['Rape'] / pop_lakh
    df['Complaints_per_Capita'] = df['Complaints_Registered'] / pop_lakh
    
    # Calculate Severity Score
    # (Serious Crimes) / (High-Volume but less severe)
    # Added 1 to denominator to avoid division by zero
    df['Severity_Score'] = (df['Murder'] + df['Rape']) / (df['Harassment'] + df['Road_Accidents'] + 1) * 100

    print("Data processing complete.")
    df = df.fillna(0) # Fill any NaNs with 0
    return df