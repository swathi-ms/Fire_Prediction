# 🔥 Executive Summary: 

# 🧯 Problem Definition and Intended Audience

Wildfires in California have grown in both frequency and intensity, threatening lives, ecosystems, and infrastructure. Emergency fire responders often face the daunting challenge of allocating resources effectively and rapidly responding to incidents with limited data. One critical aspect of firefighting preparation is the **ability to estimate the potential size of a fire** as early as possible, based on environmental and contextual factors.

This project aims to develop a **predictive model to estimate the size of a wildfire (in acres)** on the day it is reported. The model leverages:
- Meteorological data (temperature, wind speed, precipitation)
- Historical fire records
- Satellite fire detection readings (MODIS)

By estimating fire size early, **emergency fire responders** can prioritize incidents that are likely to escalate, optimize deployment of firefighting units, and plan evacuation or containment strategies with greater confidence.

# Data Collection - [`data_collection.ipynb`](./code/data_collection.ipynb)

My project aims to estimate wildfire size in California using weather, geospatial, and satellite fire detection data. I began by collecting two primary datasets:

- **Weather and Environmental Data** from [Zenodo](https://zenodo.org/records/14712845)  
- **Wildfire Incident Records** from [CAL FIRE](https://www.fire.ca.gov/incidents)

The raw CSV files used were:
- `zenodo.csv` (weather-related features)
- `calfire.csv` (incident-level fire data from CAL FIRE)

These two datasets were **merged on the `fire_dateonly_created` field**, which aligns the date of fire incidents with the corresponding weather conditions.

The merged and cleaned dataset was saved as:
- ✅ **`calfire_zenodo.csv`**

## 🧾 Features Merged (Renamed & Retained in `calfire_zenodo.csv`)

| Original Column | Renamed As             | Description |
|------------------|-------------------------|-------------|
| `incident_name` | `fire_name`            | Name of the fire incident |
| `incident_dateonly_created` | `fire_dateonly_created` | Date the fire was reported |
| `PRECIPITATION` | `precipitation`        | Daily precipitation (mm/inches) |
| `MAX_TEMP`      | `max_temp`             | Maximum temperature (°C/°F) |
| `MIN_TEMP`      | `min_temp`             | Minimum temperature (°C/°F) |
| `AVG_WIND_SPEED`| `avg_wind_speed`       | Average wind speed (mph or km/h) |
| `TEMP_RANGE`    | `temp_range`           | Daily temperature range |
| `WIND_TEMP_RATIO`| `wind_temp_ratio`     | Ratio of wind speed to temperature |
| `LAGGED_PRECIPITATION` | `lagged_precipitation` | Precipitation on the previous day |
| `LAGGED_AVG_WIND_SPEED` | `lagged_avg_wind_speed` | Wind speed on the previous day |
| `MONTH`         | `month`                | Month of the fire |
| `SEASON`        | `season`               | Season identifier (1 to 4) |
| `incident_longitude` | `fire_longitude`   | Longitude of fire origin |
| `incident_latitude`  | `fire_latitude`    | Latitude of fire origin |
| `incident_acres_burned` | `fire_acres_burned` | Total area burned in acres |
| `incident_county`     | `fire_county`      | County where fire occurred |

## 🛰️ Satellite Data Enrichment

After the merge, I looped through **MODIS satellite data CSV files** (`modis_*_United_States.csv`) sourced from NASA's [FIRMS](https://firms.modaps.eosdis.nasa.gov/country/), which contains near real-time fire detection data. For each fire incident:

- The script matches MODIS data by both **date** and **approximate location (latitude and longitude rounded to 2 decimal places)**.
- Fire detection features such as **brightness**, **thermal anomalies**, and **FRP (Fire Radiative Power)** are integrated when matched.
- These matches aim to link ground fire reports with satellite-based observations

The project originally included a plan to dynamically fetch historical weather data from the **NOAA Climate Data Online (CDO) API** using a pipeline implemented in `fire_weather_pipieline.ipynb`. This pipeline was designed to:

- Identify the nearest NOAA weather station to each fire event using `geopy`
- Fetch temperature, precipitation, and wind data from the NOAA CDO API for the fire incident date

However,the implementation was not fully successful.As a result, weather data was instead sourced from a precompiled and publicly available dataset on [Zenodo](https://zenodo.org/records/14712845), ensuring consistency and continuity for the modeling workflow.

The pipeline notebook (`fire_weather_pipieline.ipynb`) remains available for future development or debugging to enable live NOAA integration if needed.

## 🔍 Data Cleaning - [`data_cleaning&EDA.ipynb`](./code/data_cleaning&EDA.ipynb)

1. **Loaded Source**  
   - Dataset: `combined.csv` (merged weather, fire, and satellite data)

2. **Geographic Validation**  
   - Ensured all fire coordinates are within California’s boundaries:
     - Latitude between `32.5°` and `42.0°`
     - Longitude between `-124.5°` and `-114.0°`
   - Identified and removed rows with invalid or out-of-bound coordinates.
   - Detected issues such as:
     - Corrupted longitudes (e.g., `-1,191,414,610.0`)
     - Positive longitudes that should have been negative
     - Out-of-state entries (e.g., fires marked in "State of Oregon")

3. **County Name Cleanup**  
   - Used **geospatial joins** with a California counties GeoJSON file (`California_Counties.geojson`) to assign a valid `clean_county` to each fire point.
   - This replaced inconsistent or missing entries in the original `fire_county` column.
   - County names were corrected using spatial logic instead of relying on raw text.

4. **Final Output**  
   - A cleaned DataFrame (`df_cleaned_final`) containing only valid California wildfire records with accurate coordinates and verified counties.

## 🚫 Outliers Removed

To ensure geographic integrity:
- **Fire incidents outside California's bounds** were removed:
  - Latitude not between **32.5° and 42.0°**
  - Longitude not between **-124.5° and -114.0°**
- Examples of removed outliers include:
  - `fire_latitude = 5487.00` (impossible Earth coordinate)
  - `fire_longitude = -1,191,414,610.0` (clearly corrupted)
  - Fires located in **"State of Oregon"** or missing proper geotags

These records were dropped after validating against official California county boundaries.

## 🩺 Data Imputation

Two types of imputation were used to handle missing values in key features:

### 1. Iterative Imputation (Multivariate)
- Applied to **satellite features** such as:
  - `brightness`
  - `frp`
  - `bright_t31`
- Used `IterativeImputer` from `sklearn.impute` to estimate missing values based on patterns from other correlated features.

### 2. Median Imputation
- Used for **wind-related variables** when applicable.
- Aimed to handle occasional missing values in:
  - `avg_wind_speed`
  - `wind_temp_ratio`

These imputations ensured model-ready completeness while minimizing bias from deletion or zero-filling.

## 📊 Exploratory Data Analysis (EDA)

- Performed summary statistics on temperature, brightness, FRP, and other numeric variables.
- Checked correlations between satellite features (`brightness`, `bright_t31`, `frp`) to assess multicollinearity.
- Analyzed missing values across features to guide imputation or dropping.
- Identified and documented feature distributions, outliers, and dependencies relevant to fire size.

## 🧠 Models Built - [`modelling.ipynb`](./code/modelling.ipynb)

Three regression models were trained on a cleaned dataset:

- **Linear Regression** (baseline)
- **Random Forest Regressor**
- **Gradient Boosting Regressor**
- **XGBoost Regressor**

The target variable `fire_acres_burned` was **log-transformed** to normalize skewed data, and later inverse-transformed for interpretability in acres.

Key features used include:

- **Weather**: precipitation, temperature, wind speed
- **Geographic**: latitude/longitude (converted to Cartesian coordinates), top 10 counties with highest burnt area
- **Satellite**: brightness, fire radiative power (FRP)
- **Temporal**: month, season

## 📈 Inference and Insights

- **Baseline (mean-based)** MAE was significantly reduced with all models.
- **Linear Regression** achieved a test MAE of around **3434.86 acres**, showing basic patterns are detectable.
- **Ensemble models** like XGBoost and Gradient Boosting performed better, reducing MAE further (exact MAEs available in notebook).

### 🔥 What this means for fire responders:

- **High-potential fires can be flagged early** using model predictions on the day of incident creation.
- The absence of clear seasonal patterns indicates **real-time factors (like wind + fuel) dominate**, reinforcing the need for contextual data at incident time.
- These predictions support **prioritizing resource allocation** to large fires that may otherwise escalate.

# ⚠️ Risks, Limitations, and Assumptions

## 🔍 Assumptions

- The **date of fire creation** is assumed to be the most relevant timestamp for predicting fire size.
- The **weather data** used from Zenodo is assumed to be an accurate proxy for real-time environmental conditions at the fire location and date.
- All fires within the same **county and day** are treated independently, even though real-world spread and containment may involve overlap.
- The **top 10 counties** (by total acres burned) are assumed to be representative of high-risk zones for focused modeling.

## 🚧 Limitations

- **NOAA API data** integration failed, limiting the use of real-time station-based weather data. Instead, the analysis relies on static Zenodo data.
- **MODIS satellite data** did not have data for 2024,2025
- **Ground truth data on vegetation, fuel load, and suppression efforts** was not available, which are important for fire growth modeling.
- Fire size is treated as a **point-in-time prediction** without modeling time evolution or spread.
- The **target variable (fire_acres_burned)** may include reporting delays or errors in official sources like CAL FIRE.
- **No economic, human impact, or containment effectiveness data** is modeled.

## 🧨 Risks

- Model overfitting to historical fire patterns in the **top 10 counties** may reduce generalization across the state.
- **Real-time application** may suffer from prediction uncertainty if wind or other short-term weather changes rapidly.
- Counties or locations **outside the training set** may yield poor predictions due to lack of representativeness.
- **Imputation or removal of invalid coordinates** may introduce bias or lead to loss of important edge cases.
- **Temporal drift**: the conditions influencing fire size may evolve over years (e.g., drought, development), but the model assumes feature relationships remain stable.