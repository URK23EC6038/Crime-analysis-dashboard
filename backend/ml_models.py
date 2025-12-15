import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from prophet import Prophet
from transformers import pipeline
import spacy
import warnings

# Suppress warnings from Prophet/Transformers
warnings.filterwarnings("ignore")

# --- 1. Predictive Analytics: Random Forest ---
def train_random_forest(df):
    """
    Trains a Random Forest model to find key crime drivers.
    """
    print("Training Random Forest...")
    features = [
        'Population', 'Suicide_Rate', 'Road_Accident_Rate', 
        'Harassment', 'Complaints_per_Capita', 'Murder_Rate'
    ]
    
    # Ensure all columns exist and are numeric
    valid_features = [col for col in features if col in df.columns and pd.api.types.is_numeric_dtype(df[col])]
    if not valid_features:
        return {'features': [], 'importance': []}

    X = df[valid_features].fillna(0)
    y = df['Crime_Rate_2022'].fillna(0)
    
    rf_model = RandomForestRegressor(n_estimators=100, random_state=42)
    rf_model.fit(X, y)
    
    importance_df = pd.DataFrame({
        'feature': X.columns,
        'importance': rf_model.feature_importances_
    }).sort_values(by='importance', ascending=False)
    
    return {
        'features': importance_df['feature'].tolist(),
        'importance': importance_df['importance'].tolist()
    }

# --- 2. Time-Series Forecasting: Prophet ---
def get_prophet_forecast(df, district_name):
    """
    Generates a 1-year forecast for a specific district using Prophet.
    """
    print(f"Running Prophet forecast for {district_name}...")
    district_data = df[df['District'] == district_name]
    
    if district_data.empty:
        return {} # No data for this district
        
    history = {
        '2020-12-31': district_data['Total_Crime_Count_2020'].values[0],
        '2021-12-31': district_data['Total_Crime_Count_2021'].values[0],
        '2022-12-31': district_data['Total_Crime_Count_2022'].values[0],
    }
    
    prophet_df = pd.DataFrame(history.items(), columns=['ds', 'y'])
    prophet_df['ds'] = pd.to_datetime(prophet_df['ds'])
    
    m = Prophet(yearly_seasonality=False, weekly_seasonality=False, daily_seasonality=False,
                changepoint_prior_scale=0.01) # Simple model for few data points
    m.fit(prophet_df)
    
    future = m.make_future_dataframe(periods=1, freq='Y')
    forecast = m.predict(future)
    
    results = {
        'history_dates': prophet_df['ds'].dt.strftime('%Y').tolist(),
        'history_values': prophet_df['y'].tolist(),
        'forecast_dates': forecast['ds'].dt.strftime('%Y').tolist(),
        'forecast_values': forecast['yhat'].round().tolist(),
        'forecast_lower': forecast['yhat_lower'].round().tolist(),
        'forecast_upper': forecast['yhat_upper'].round().tolist(),
    }
    return results

# --- 3. Clustering: K-Means District Profiles ---
def get_kmeans_clusters(df):
    """
    Groups districts into clusters based on their crime profiles.
    """
    print("Running K-Means clustering...")
    features = [
        'Crime_Rate_2022', 'Severity_Score', 
        'Suicide_Rate', 'Road_Accident_Rate', 'Murder_Rate', 'Harassment'
    ]
    valid_features = [col for col in features if col in df.columns and pd.api.types.is_numeric_dtype(df[col])]
    if not valid_features:
        return {'labels': [], 'counts': [], 'analysis': []}

    cluster_data = df[valid_features].fillna(0)
    scaled_data = StandardScaler().fit_transform(cluster_data)
    
    k = 4 # Number of clusters
    kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
    df['Cluster'] = kmeans.fit_predict(scaled_data)
    
    cluster_counts = df['Cluster'].value_counts().sort_index()
    
    return {
        'labels': [f"Profile {c+1}" for c in cluster_counts.index],
        'counts': cluster_counts.values.tolist(),
    }

# --- 4. Advanced NLP: Summarization and NER ---

# Load models once (this is slow, so it's done globally)
try:
    print("Loading NLP models... (This may take a moment)")
    summarizer = pipeline("summarization", model="sshleifer/distilbart-cnn-12-6")
    nlp_ner = spacy.load("en_core_web_sm")
    print("NLP models loaded successfully.")
except Exception as e:
    print(f"Error loading NLP models: {e}")
    print("NLP features will be unavailable.")
    summarizer = None
    nlp_ner = None

def analyze_fir_text(text):
    """
    Summarizes text and performs NER.
    """
    if summarizer is None or nlp_ner is None:
        return {"error": "NLP models are not available."}
        
    print("Running NLP analysis on text...")
    # 1. Summarization
    min_length = max(10, int(len(text.split()) * 0.2))
    max_length = min(150, int(len(text.split()) * 0.5))
    
    if max_length <= min_length:
         min_length = max(5, max_length // 2) # Ensure min_length is valid
         
    summary = summarizer(text, max_length=max_length, min_length=min_length, do_sample=False)[0]['summary_text']
    
    # 2. Named Entity Recognition (NER)
    doc = nlp_ner(text)
    entities = []
    for ent in doc.ents:
        entities.append({
            'text': ent.text,
            'label': ent.label_
        })
        
    return {
        'summary': summary,
        'entities': entities
    }