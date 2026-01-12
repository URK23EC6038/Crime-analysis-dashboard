import uvicorn
from fastapi import FastAPI, HTTPException, Body
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import json
import os
import pandas as pd
import numpy as np 
import math
from data_processor import load_and_merge_data, append_new_case
import ml_models

app = FastAPI(title="Sentinel API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FOLDER = os.path.join(BASE_DIR, "data")
FRONTEND_FOLDER = os.path.join(os.path.dirname(BASE_DIR), "frontend")

app.state.df = None
app.state.geojson = None
app.state.analysis_results = {}

# 🔥 FIXES CRASHES
def convert_to_safe_json(obj):
    if isinstance(obj, (np.integer, int)): return int(obj)
    elif isinstance(obj, (np.floating, float)):
        if np.isnan(obj) or np.isinf(obj): return 0.0
        return float(obj)
    elif isinstance(obj, np.ndarray): return convert_to_safe_json(obj.tolist())
    elif isinstance(obj, dict): return {k: convert_to_safe_json(v) for k, v in obj.items()}
    elif isinstance(obj, list): return [convert_to_safe_json(i) for i in obj]
    return obj

@app.on_event("startup")
def startup_event():
    refresh_data()

def refresh_data():
    try:
        if not os.path.exists(DATA_FOLDER): os.makedirs(DATA_FOLDER)
        app.state.df = load_and_merge_data(DATA_FOLDER)
        
        geojson_path = os.path.join(DATA_FOLDER, "tamil_nadu_districts.geojson")
        if os.path.exists(geojson_path):
            with open(geojson_path, "r") as f: app.state.geojson = json.load(f)
            print("✅ GeoJSON Map Loaded.")
        else:
            print("⚠️ GeoJSON Map Missing.")

        if not app.state.df.empty: run_ai_engine()
    except Exception as e:
        print(f"❌ Startup Error: {e}")

def run_ai_engine():
    df = app.state.df
    try:
        app.state.analysis_results['clusters'] = ml_models.detect_hotspots(df)
        app.state.analysis_results['feature_importance'] = ml_models.predict_risk_drivers(df)
        app.state.analysis_results['anomalies'] = ml_models.detect_anomalies(df)
        
        highest_risk = df.loc[df['Severity_Score'].idxmax()]
        safest = df.loc[df['Severity_Score'].idxmin()]
        
        app.state.analysis_results['intel_brief'] = {
            "critical_zone": highest_risk['District'],
            "critical_score": round(highest_risk['Severity_Score'], 2),
            "safe_zone": safest['District'],
            "total_incidents": int(df['Total_Crime_Count_2022'].sum()),
            "alert_level": "RED" if df['Severity_Score'].mean() > 50 else "AMBER"
        }
    except Exception as e:
        print(f"AI Engine Error: {e}")

@app.get("/api/intel-feed")
def get_intel_feed():
    if app.state.df is None or app.state.df.empty: return {"status": "Initializing"}
    df = app.state.df
    results = app.state.analysis_results
    
    raw_data = {
        "brief": results.get('intel_brief', {}),
        "hotspots": results.get('clusters', []),
        "anomalies": results.get('anomalies', []),
        "predictive_drivers": results.get('feature_importance', []),
        "chart_data": {
            "districts": df['District'].tolist(),
            "composition": {
                "suicides": df['Suicides'].sum(),
                "accidents": df['Road_Accidents'].sum(),
                "murders": df['Murder'].sum(),
                "harassment": df['Harassment'].sum()
            }
        }
    }
    return convert_to_safe_json(raw_data)

@app.get("/api/geo-layers")
def get_geo_layers():
    if not app.state.geojson: return {}
    if app.state.df is None: return convert_to_safe_json(app.state.geojson)
    
    geojson = app.state.geojson.copy()
    df = app.state.df.set_index('District')
    
    for feature in geojson['features']:
        props = feature['properties']
        district_name = None
        for key in ['dtname', 'DISTRICT', 'NAME', 'Name', 'district', 'District']:
            if key in props:
                district_name = props[key]
                break
        
        # 🔥 FIXES MAP UNDEFINED
        if district_name: props['DISTRICT'] = district_name
        else: props['DISTRICT'] = "Unknown Zone"

        found = False
        if district_name:
            match = None
            if district_name in df.index: match = df.loc[district_name]
            else:
                for idx in df.index:
                    if str(idx).lower().strip() == str(district_name).lower().strip():
                        match = df.loc[idx]; break
            
            if match is not None:
                props['risk_score'] = float(match['Severity_Score'])
                props['accidents'] = int(match['Road_Accidents'])
                props['murders'] = int(match['Murder'])
                props['suicides'] = int(match['Suicides'])
                props['harassment'] = int(match['Harassment'])
                found = True
        
        if not found:
            props['risk_score'] = 0; props['accidents'] = 0; props['murders'] = 0; props['suicides'] = 0; props['harassment'] = 0
            
    return convert_to_safe_json(geojson)

@app.post("/api/add-case")
async def add_case_record(
    district: str = Body(...), crime_type: str = Body(...),
    description: str = Body(...), severity: str = Body(...)
):
    try:
        success = append_new_case(DATA_FOLDER, district, crime_type, description, severity)
        if success:
            refresh_data()
            return {"status": "success"}
        else: raise HTTPException(500, "Write Failed")
    except Exception as e: raise HTTPException(500, str(e))

@app.get("/api/case-logs")
def get_case_logs():
    try:
        log_path = os.path.join(DATA_FOLDER, "new_case_logs.csv")
        if os.path.exists(log_path): return pd.read_csv(log_path).iloc[::-1].to_dict('records')
        return []
    except: return []

if os.path.exists(os.path.join(FRONTEND_FOLDER, "js")):
    app.mount("/js", StaticFiles(directory=os.path.join(FRONTEND_FOLDER, "js")), name="js")

@app.get("/{full_path:path}")
async def serve_frontend(full_path: str):
    file_path = os.path.join(FRONTEND_FOLDER, full_path)
    if os.path.isfile(file_path): return FileResponse(file_path)
    return FileResponse(os.path.join(FRONTEND_FOLDER, "index.html"))

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)