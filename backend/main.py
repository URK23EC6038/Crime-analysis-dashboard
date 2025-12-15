import uvicorn
from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import json
import os
from typing import List

# Import our custom modules
from data_processor import load_and_merge_data
import ml_models

app = FastAPI(
    title="Tamil Nadu Crime Analytics API",
    description="API for the Advanced Crime Analytics Dashboard"
)

# --- Allow CORS ---
# This allows your frontend (on port 8000) to talk to your backend (also on 8000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allows all origins
    allow_credentials=True,
    allow_methods=["*"], # Allows all methods
    allow_headers=["*"], # Allows all headers
)

# --- Global State ---
app.state.df = None
app.state.geojson = None
app.state.analysis_results = {}

# --- Data Path ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FOLDER = os.path.join(BASE_DIR, "data")
FRONTEND_FOLDER = os.path.join(os.path.dirname(BASE_DIR), "frontend")


# --- 1. Server Startup ---
@app.on_event("startup")
def startup_event():
    """
    On server startup, load the data and the GeoJSON file.
    """
    try:
        app.state.df = load_and_merge_data(DATA_FOLDER)
        print("DataFrame loaded on startup.")
    except Exception as e:
        print(f"Error loading data on startup: {e}")
        app.state.df = pd.DataFrame() 

    try:
        # Load the GeoJSON file for the map
        geojson_path = os.path.join(DATA_FOLDER, "tamil_nadu_districts.geojson")
        with open(geojson_path, "r") as f:
            app.state.geojson = json.load(f)
        print("GeoJSON loaded on startup.")
    except FileNotFoundError:
        print(f"!!! CRITICAL WARNING !!!")
        print(f"GeoJSON file not found at: {geojson_path}")
        print("The map will be empty. Please download a GeoJSON file.")
        app.state.geojson = None
    
    # Pre-run analysis
    if not app.state.df.empty:
        run_full_analysis()

def run_full_analysis():
    """Helper function to run all ML models and store results."""
    df = app.state.df
    if df is None or df.empty:
        print("Analysis skipped: DataFrame is empty.")
        return
        
    print("Running full analysis on server...")
    app.state.analysis_results['rf_importance'] = ml_models.train_random_forest(df)
    app.state.analysis_results['kmeans_clusters'] = ml_models.get_kmeans_clusters(df)
    
    # Pre-calculate summary stats
    highest_crime_district = df.loc[df['Crime_Rate_2022'].idxmax()]
    highest_severity_district = df.loc[df['Severity_Score'].idxmax()]
    
    app.state.analysis_results['summary_stats'] = {
        "highest_crime_district": highest_crime_district['District'],
        "highest_crime_rate": round(highest_crime_district['Crime_Rate_2022'], 2),
        "average_crime_rate": round(df['Crime_Rate_2022'].mean(), 2),
        "highest_severity_district": highest_severity_district['District'],
        "highest_severity_score": round(highest_severity_district['Severity_Score'], 2),
        "total_population": round(df['Population'].sum() / 1_00_000, 2)
    }
    print("Analysis complete.")

# --- 2. API Endpoints ---
@app.post("/api/upload-and-analyze")
async def upload_and_analyze(files: List[UploadFile] = File(...)):
    """
    Receives all 6 CSV files, saves them, and re-runs all analysis.
    """
    if len(files) != 6:
        raise HTTPException(status_code=400, detail=f"Expected 6 files, got {len(files)}")
        
    file_names = [
        '01_suicides.csv', '02_harassment.csv', '03_accidents.csv', 
        '04_deaths.csv', '05_crime_rate.csv', '06_complaints.csv'
    ]
    
    print("Receiving uploaded files...")
    for i, file in enumerate(files):
        file_path = os.path.join(DATA_FOLDER, file_names[i])
        try:
            with open(file_path, "wb") as buffer:
                buffer.write(await file.read())
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Could not save file {file.filename}: {e}")
            
    # Now that files are saved, reload and re-analyze
    try:
        app.state.df = load_and_merge_data(DATA_FOLDER)
        run_full_analysis()
        return {"message": "Files uploaded and analysis complete!"}
    except Exception as e:
        print(f"Error during analysis: {e}")
        raise HTTPException(status_code=500, detail=f"Error during analysis: {e}")

@app.get("/api/all-data")
def get_all_data():
    """Returns all calculated data for the dashboard in one go."""
    if app.state.df is None or app.state.df.empty:
        return JSONResponse(status_code=404, content={"error": "Data not loaded. Please upload files."})

    df = app.state.df
    
    response_data = {
        "summary_stats": app.state.analysis_results.get('summary_stats'),
        "rf_importance": app.state.analysis_results.get('rf_importance'),
        "kmeans_clusters": app.state.analysis_results.get('kmeans_clusters'),
        
        "district_crime_rates": df.sort_values('Crime_Rate_2022', ascending=False)[['District', 'Crime_Rate_2022']].to_dict('records'),
        "district_severity_scores": df.sort_values('Severity_Score', ascending=False)[['District', 'Severity_Score']].to_dict('records'),
        "risk_analysis_data": df[['District', 'Crime_Rate_2022', 'Suicide_Rate', 'Road_Accident_Rate']].to_dict('records'),
        "correlation_data": df.to_dict('records'), 
        
        "profile_data": df[[
            'District', 'Harassment', 'Road_Accidents', 
            'Murder', 'Rape', 'Suicides', 'Deaths'
        ]].to_dict('records'),
        
        "districts_list": sorted(df['District'].unique().tolist())
    }
    return response_data

@app.get("/api/map-geojson")
def get_map_geojson():
    """
    Merges crime data with GeoJSON and returns it.
    """
    if app.state.geojson is None:
        raise HTTPException(status_code=404, detail="GeoJSON file not found on server.")
    if app.state.df is None:
        raise HTTPException(status_code=404, detail="Data not loaded.")
        
    df = app.state.df
    geojson = app.state.geojson.copy()
    
    data_lookup = df.set_index('District')
    
    for feature in geojson['features']:
        # This property MUST match your GeoJSON's district name field
        # Common names are 'DISTRICT', 'DIST_NAME', 'name'
        # Check your file and update this line if needed
        district_name = feature['properties'].get('DISTRICT') 
        
        if district_name and district_name in data_lookup.index:
            data = data_lookup.loc[district_name]
            feature['properties']['Crime_Rate_2022'] = data['Crime_Rate_2022']
            feature['properties']['Severity_Score'] = data['Severity_Score']
            feature['properties']['Population'] = data['Population']
            feature['properties']['Total_Crimes'] = data['Total_Crime_Count_2022']
        else:
            feature['properties']['Crime_Rate_2022'] = None
            
    return geojson

@app.get("/api/forecast/{district_name}")
def get_forecast(district_name: str):
    """
    Runs the Prophet forecast for a single, requested district.
    """
    if app.state.df is None:
        raise HTTPException(status_code=404, detail="Data not loaded.")
        
    forecast_data = ml_models.get_prophet_forecast(app.state.df, district_name)
    if not forecast_data:
        raise HTTPException(status_code=404, detail=f"No data for district: {district_name}")
        
    return forecast_data

@app.post("/api/analyze-text")
async def analyze_text(text: str = Form(...)):
    """
    Receives text and returns NLP analysis.
    """
    if not text:
        raise HTTPException(status_code=400, detail="No text provided.")
        
    try:
        results = ml_models.analyze_fir_text(text)
        return results
    except Exception as e:
        print(f"NLP Analysis Error: {e}")
        raise HTTPException(status_code=500, detail=f"Error during NLP analysis: {e}")

# --- 3. Serve Frontend ---
app.mount("/js", StaticFiles(directory=os.path.join(FRONTEND_FOLDER, "js")), name="js")

@app.get("/{full_path:path}")
async def serve_frontend(full_path: str):
    """Catch-all to serve index.html."""
    file_path = os.path.join(FRONTEND_FOLDER, full_path)
    if os.path.isfile(file_path):
        return FileResponse(file_path)
    return FileResponse(os.path.join(FRONTEND_FOLDER, "index.html"))

# --- 4. Run the Server ---
if __name__ == "__main__":
    print("--- Starting Tamil Nadu Crime Analytics Server ---")
    print(f"Serving frontend from: {FRONTEND_FOLDER}")
    print(f"Loading data from: {DATA_FOLDER}")
    print("Find your dashboard at: http://127.0.0.1:8000")
    uvicorn.run(app, host="127.0.0.1", port=8000)