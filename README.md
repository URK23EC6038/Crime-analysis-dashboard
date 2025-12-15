# Crime-analysis-dashboard
Markdown# 🔍 Crime Analysis Dashboard Using Machine Learning

> **A Multi-Modal Approach for Smart Crime Prediction and Monitoring**

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue)](https://www.python.org/)
[![PyTorch](https://img.shields.io/badge/PyTorch-Fusion%20Network-red)](https://pytorch.org/)
[![Status](https://img.shields.io/badge/Status-Research%20Prototype-green)]()

## 📜 Project Overview
[cite_start]This project presents a **Crime Analytics System** developed to study district-level crime trends across Tamil Nadu[cite: 14]. [cite_start]Unlike traditional methods that rely solely on raw crime counts, our model integrates **crime records, accident data, socioeconomic indicators, and population statistics**[cite: 15].

[cite_start]By fusing these diverse datasets, the system identifies key crime drivers, groups similar districts, and predicts short-term trends using a combination of **Machine Learning** and **Deep Learning** fusion techniques[cite: 16].

## 🚀 Key Features
* [cite_start]**Multi-Modal Data Integration:** Combines crime stats, suicides, harassment reports, and road accidents for a holistic view[cite: 24].
* [cite_start]**Predictive Modelling:** Uses **Prophet** to forecast future crime trends based on time-series data (2020–2022)[cite: 42].
* [cite_start]**Factor Analysis:** Uses **Random Forest** to identify the most influential factors affecting crime levels[cite: 55].
* [cite_start]**District Profiling:** Applies **K-Means Clustering** to group districts by crime behavior and severity[cite: 55].
* [cite_start]**Deep Learning Fusion:** A custom **Fully Connected Fusion Network** merges features from all models to achieve superior prediction accuracy[cite: 76].
* [cite_start]**Interactive Dashboard:** A visualization tool for exploring hotspots, severity levels, and risk correlations[cite: 17].

---

## 🛠️ Tech Stack & Methodology

The system follows a modular architecture where different data modalities are processed separately and then fused.

| Component | Model / Algorithm | Feature Size | Purpose |
| :--- | :--- | :--- | :--- |
| **Crime Statistics** | Random Forest | 128 features | [cite_start]Factor importance analysis [cite: 55] |
| **Historical Trends** | Facebook Prophet | 64 features | [cite_start]Time-series forecasting [cite: 55] |
| **District Profiles** | K-Means Clustering | 32 features | [cite_start]Geospatial/behavioral clustering [cite: 55] |
| **Final Prediction** | **Feature Fusion Network** | 224 → Output | [cite_start]Combined insight generation [cite: 71] |

### Feature Fusion Logic
[cite_start]The core innovation is the fusion of feature vectors into a single representation[cite: 74]:
```python
# Conceptual implementation of the Fusion Layer
fusion_vector = torch.cat([crime_features, trend_features, cluster_features], dim=1)
# Input Dimension: 128 + 64 + 32 = 224
📂 Project StructureThe codebase is organized into modular scripts for reproducibility1.Bash├── data_processor.py      # Cleaning, normalization, and preprocessing of datasets
├── ml_models.py           # Definitions for Random Forest, Prophet, and K-Means models
├── main.py                # Main execution script to train models and generate features
├── fusion_model.sav       # Saved trained model for real-time analytics
├── dashboard.py           # (Optional) Code for the interactive UI
├── requirements.txt       # Python dependencies
└── README.md              # Project documentation
📊 Performance ResultsWe evaluated the models individually and as a fused system. The Fusion Model demonstrated a significant improvement in accuracy by leveraging multiple data sources2.Model TypeAccuracy / ReliabilityRandom Forest Only~82% 3Prophet Trend Only~76% 4K-Means Clustering~79% 5Fusion Model (Proposed)~90–92% 6⚙️ Installation & UsageClone the RepositoryBashgit clone [https://github.com/URK23EC6038/Crime-analysis-dashboard.git](https://github.com/URK23EC6038/Crime-analysis-dashboard.git)
cd Crime-analysis-dashboard
Install DependenciesBashpip install -r requirements.txt
Run the AnalysisTo train the models and generate the fusion vector:Bashpython main.py
