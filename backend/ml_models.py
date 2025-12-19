import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor, IsolationForest
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

def detect_hotspots(df):
    if df.empty or len(df) < 5: return []
    features = ['Crime_Rate_2022', 'Severity_Score']
    X = df[features].fillna(0)
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    kmeans = KMeans(n_clusters=3, random_state=42, n_init=10)
    df['Cluster_ID'] = kmeans.fit_predict(X_scaled)
    return df['Cluster_ID'].tolist()

def predict_risk_drivers(df):
    features = ['Population', 'Road_Accidents', 'Murder', 'Suicides', 'Harassment']
    available = [f for f in features if f in df.columns]
    if not available: return []
    X = df[available].fillna(0)
    y = df['Total_Crime_Count_2022']
    model = RandomForestRegressor(n_estimators=100, random_state=42)
    model.fit(X, y)
    importance = pd.DataFrame({'Factor': available, 'Impact_Score': model.feature_importances_})
    return importance.sort_values(by='Impact_Score', ascending=False).head(5).to_dict('records')

def detect_anomalies(df):
    if df.empty: return []
    model = IsolationForest(contamination=0.1, random_state=42)
    features = ['Total_Crime_Count_2022', 'Severity_Score']
    X = df[features].fillna(0)
    df['Is_Anomaly'] = model.fit_predict(X)
    anomalies = df[df['Is_Anomaly'] == -1][['District', 'Severity_Score']]
    return anomalies.to_dict('records')