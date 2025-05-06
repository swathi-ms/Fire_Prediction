# 🔥 Executive Summary: 

# 🧯 Problem Definition and Intended Audience

Wildfires in California have grown in both frequency and intensity, threatening lives, ecosystems, and infrastructure. Emergency fire responders often face the daunting challenge of allocating resources effectively and rapidly responding to incidents with limited data. One critical aspect of firefighting preparation is the **ability to estimate the potential size of a fire** as early as possible, based on environmental and contextual factors.

This project aims to develop a **predictive model to estimate the size of a wildfire (in acres)** on the day it is reported. The model leverages:
- Meteorological data (temperature, wind speed, precipitation)
- Historical fire records
- Satellite fire detection readings (MODIS)

By estimating fire size early, **emergency fire responders** can prioritize incidents that are likely to escalate, optimize deployment of firefighting units, and plan evacuation or containment strategies with greater confidence.

## Data Collection - 
[`data_collection.ipynb`](./code/data_collection.ipynb)

My project aims to estimate wildfire size in California using weather, geospatial, and satellite fire detection data. I began by collecting two primary datasets:

- **Weather and Environmental Data** from [Zenodo](https://zenodo.org/records/14712845)  
- **Wildfire Incident Records** from [CAL FIRE](https://www.fire.ca.gov/incidents)

The raw CSV files used were:
- `zenodo.csv` (weather-related features)
- `calfire.csv` (incident-level fire data from CAL FIRE)

These two datasets were **merged on the `fire_dateonly_created` field**, which aligns the date of fire incidents with the corresponding weather conditions.

The merged and cleaned dataset was saved as:
- ✅ **`calfire_zenodo.csv`**

## 🧾 Features Merged 
(Renamed & Retained in `calfire_zenodo.csv`)

| Original Column | Renamed As             | Description |
|------------------|-------------------------|-------------|
| `incident_name` | `fire_name`            | Name of the fire incident |
| `incident_dateonly_created` | `fire_dateonly_created` | Date the fire was reported |
| `PRECIPITATION` | `precipitation`        | Daily precipitation (mm/inches) |
| `MAX_TEMP`      | `max_temp`             | Maximum temperature (°F) |
| `MIN_TEMP`      | `min_temp`             | Minimum temperature (°F) |
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

## 🔍 Data Cleaning 
[`data_cleaning&EDA.ipynb`](./code/data_cleaning&EDA.ipynb)

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
   - A cleaned data (`cleaned.csv`) containing only valid California wildfire records with accurate coordinates and verified counties.

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

### 1. Iterative Imputation
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

## 🧠 Models Built - 
[`modelling.ipynb`](./code/modelling.ipynb)

Three regression models were trained on a cleaned dataset:

- **Linear Regression**
- **Random Forest Regressor**
- **Gradient Boosting Regressor**
- **XGBoost Regressor**
The target variable `fire_acres_burned` was **log-transformed** to normalize skewed data, and later inverse-transformed for interpretability in acres.

| Model                 | Test MAE (acres) |
|-----------------------|------------------|
| Baseline         |  135.12 |
| Linear Regression     | 112.46 (105.03)           |
| Ridge Regression      | 112.18          |
| Lasso Regression      | 111.71           |
| Random Forest         | **108.95**       |
| XGBoost               | 114.52           |

On average, my model's predictions are off by about 109 acres.

## Summary

Key features used include:

- **Weather**: precipitation, temperature, wind speed
- **Geographic**: latitude/longitude (converted to Cartesian coordinates), top 10 counties with highest burnt area
- **Satellite**: brightness, fire radiative power (FRP)
- **Temporal**: month, season

- **Fire Trends Over Time**: 
  - The number of wildfires and total acres burned have increased significantly from 2000 to 2023.
  - A clear seasonal pattern was observed: **July to September** had the highest concentration of large fires.

- **Fire Size Distribution**:
  - While **most fires were small (< 1000 acres)**, a few **very large fires (> 100,000 acres)** contributed to the majority of area burned.
  - Fires larger than 1000 acres have been steadily increasing over the years.

- **Spatial Hotspots**:
  - Counties such as **Plumas, Glenn, Siskiyou, Butte, and Shasta** consistently recorded high total acreage burned, making them geographic hotspots for large-scale fires.

- **Predictive Features**:
  - The most important factors in predicting fire size were:
    - **Brightness** and **Fire Radiative Power (FRP)**: Proxy indicators of fire energy and intensity.
    - **Temperature** and **Wind Speed**: Weather conditions that affect fire spread.
    - **Latitude and Longitude (spatial features)**: Certain regions are more prone to large fires.

- **Model Performance**:
  - A **Random Forest Regressor** was trained using environmental and spatial features.
  - The model was evaluated using **Mean Absolute Error (MAE)** and was able to reasonably predict fire size in acres.
  - Smaller fires were predicted with higher accuracy, while larger fires showed more variability — a natural challenge in imbalanced datasets.


## Recommendations

1. **Use the model as soon as a fire is detected**  
   The model can give a quick estimate of how big a fire might get. This helps responders act faster and make better decisions.

2. **Send more help to high-risk areas**  
   Some counties (like Plumas and Siskiyou) often have large fires. More equipment and teams should be ready in these places.

3. **Be more prepared in summer and fall**  
   Most large fires happen between July and September. Extra resources should be available during these months.

4. **Educate communities in fire-prone areas**  
   People living in areas that often have big fires should be informed and trained on fire safety and evacuation.

5. **Show predictions on a live map**  
   Fire departments can use the model’s predictions in a map view to easily see where the biggest risks are and plan accordingly.

6. **Improve the model over time**  
   Add more data like wind, drought, and vegetation to make predictions even more accurate.


## Why It Matters to Fire Responders

- **Saves time**: Helps responders decide quickly where to go and what to do.
- **Protects lives and property**: Knowing how big a fire might get helps keep people and firefighters safer.
- **Uses resources better**: Teams and equipment can be sent where they’re needed most, not wasted on smaller fires.
- **Supports teamwork**: A clear prediction helps local, state, and national teams work together more effectively.
- **Prepares for the future**: Data and predictions help fire agencies get ready before a fire becomes a big problem.


## California Wildfire Prediction App – Summary

Built an interactive Streamlit application provides two key tools to understand and respond to wildfires in California:

### 1. California Fire Viewer (2000–2023)
- **Visualizes fire incidents** on a map for each year from 2000 to 2023.
- Pulls data from satellite observations filtered for California.
- Uses color-coded circle markers to indicate **fire brightness intensity**:
  - **Blue**: Low intensity (< 330)
  - **Orange**: Medium (330–360)
  - **Red**: High (> 360)
- Overlays a California state boundary for geographic context.
- Includes a year selector slider to explore changes over time.

### 2. Wildfire Size Predictor
- Allows users to **input environmental conditions** (e.g., brightness, FRP, wind speed, temperature, location).
- Uses a **trained minimal Random Forest model** to predict the estimated **fire size in acres**.
- Transforms latitude and longitude into 3D Cartesian coordinates (`x`, `y`, `z`) for better spatial modeling.
- Displays the predicted fire location and its expected severity on the map using a color-coded circle marker.
- Categorizes predicted size as low, medium, or high intensity, with an explanatory legend.

### Technical Highlights
- Built using Python libraries: `pandas`, `numpy`, `scikit-learn`, `folium`, and `streamlit`.
- Fire size predictions are **log-transformed** during modeling and **exponentiated** before display.
- Geo-visualization is handled with `folium` and integrated into the Streamlit app using `streamlit-folium`.

### Purpose
This app is designed to help:
- **Visualize historical fire trends**
- **Predict potential fire severity based on real-time inputs**
- **Support fire responders and planners** in resource allocation and risk awareness.

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

## 🔮 Future Work and Enhancements

- **Incorporate vegetation and fuel data** (e.g., vegetation type, fuel moisture from remote sensing or USDA databases) to better model fire spread potential.
- **Integrate elevation and topography** using DEM (Digital Elevation Models) to understand terrain-driven fire behavior.
- Fix and implement the **NOAA API** pipeline for dynamic weather data retrieval at fire locations.
- Use **live feeds from FIRMS** to enable real-time prediction or alerting tools.
- Improve **time-series modeling** (e.g., ARIMA, Prophet) to forecast fire activity trends based on seasonality and climate conditions.
- Overlay fire prediction results on **ArcGIS maps** with county boundaries, population density, or critical infrastructure.

## 📚 Data and Reference Sources

- [Zenodo Wildfire & Weather Dataset (NOAA & CAL FIRE combined)](https://zenodo.org/records/14712845)
- [CAL FIRE Official Incident Archive](https://www.fire.ca.gov/incidents)
- [NASA FIRMS - Fire Information for Resource Management System](https://firms.modaps.eosdis.nasa.gov/country/)
- [MODIS Satellite Fire Detection Data](https://firms.modaps.eosdis.nasa.gov/download/)
- [NOAA Climate Data Online (CDO) API Documentation](https://www.ncdc.noaa.gov/cdo-web/webservices/v2)
- [California County GeoJSON Boundaries (via public shapefiles)](https://data.ca.gov/dataset/ca-geographic-boundaries)
- [California Counties GIS Boundary](https://www.california-demographics.com/counties_map)

## Acknowledgments

I would like to extend my heartfelt thanks to the following people that made this project possible:

- **Matt Brems** – for your invaluable insights, especially around preprocessing and spatial transformations. Your feedback helped refine the approach and improve the quality of the analysis.
- **Eric Bayless** – for your helpful feedback and suggestions, particularly regarding the use of satellite data sources, which strengthened the scope and direction of the project.
- **Andranique Green** – for sharing the `zenodo.csv` dataset.
- **ChatGPT by OpenAI** – This incredible tool was used for answering many questions when I was stuck.
