import streamlit as st
import pandas as pd
import numpy as np
import joblib
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error
import folium
from streamlit_folium import st_folium
from branca.element import Template, MacroElement
import os

st.set_page_config(layout="wide")

# Load data
df = pd.read_csv("../data/cleaned.csv", parse_dates=['fire_dateonly_created'])
df.dropna(inplace=True)
df = df[df["fire_acres_burned"] < 1000].copy()

# Drop unnecessary columns
df.drop(columns=["fire_name", "min_temp", "wind_temp_ratio", "season", "bright_t31", "year"], errors='ignore', inplace=True)

# Log-transform the target
df["log_fire_acres_burned"] = np.log1p(df["fire_acres_burned"])

# Filter top 10 counties
top_counties = df.groupby("clean_county")["fire_acres_burned"].sum().nlargest(10).index
df = df[df["clean_county"].isin(top_counties)]

# One-hot encode counties
df = pd.get_dummies(df, columns=["clean_county"], drop_first=True)

# Cartesian coordinates
df["x"] = np.cos(np.radians(df["fire_latitude"])) * np.cos(np.radians(df["fire_longitude"]))
df["y"] = np.cos(np.radians(df["fire_latitude"])) * np.sin(np.radians(df["fire_longitude"]))
df["z"] = np.sin(np.radians(df["fire_latitude"]))

# Feature columns
feature_cols = [col for col in df.columns if col not in [
    "fire_acres_burned", "log_fire_acres_burned", "fire_dateonly_created",
    "fire_size_bucket", "fire_latitude", "fire_longitude"
]]

X = df[feature_cols]
y_log = df["log_fire_acres_burned"]
y_actual = df["fire_acres_burned"]

# Train-test split
X_train, X_test, y_train_log, y_test_log, y_train_actual, y_test_actual = train_test_split(
    X, y_log, y_actual, test_size=0.2, random_state=42
)

# Train Random Forest model
rf = RandomForestRegressor(
    n_estimators=200,
    max_depth=10,
    min_samples_split=5,
    min_samples_leaf=2,
    max_features='sqrt',
    bootstrap=True,
    random_state=42,
    n_jobs=-1
)
rf.fit(X_train, y_train_log)
rf_preds = np.expm1(rf.predict(X_test))
mae_rf = mean_absolute_error(y_test_actual, rf_preds)

# Save model and columns for deployment
county_columns = [col for col in df.columns if col.startswith("clean_county_")]
joblib.dump(county_columns, "../app/county_columns.pkl")
joblib.dump(rf, "../app/random_forest_fire_model.pkl")

# --- Tabs ---
st.markdown("""
<style>
    div[data-testid="stTabs"] button {
        font-size: 80px !important;
        font-weight: 800 !important;
        padding: 8px 16px !important;
    }
</style>
""", unsafe_allow_html=True)
viewer_tab, predictor_tab = st.tabs(["🗺️ California Fire Viewer (2000–2023)", "🔥 Wildfire Size Predictor"])

# === Viewer TAB ===
with viewer_tab:
    st.sidebar.title("Year Selection")
    year = st.sidebar.slider('Select Year', 2000, 2023, 2000)

    input_folder = '../data/modis_satellite_data/california_data'
    yearly_data = {}
    for y in range(2000, 2024):
        filename = f'california_{y}.csv'
        filepath = os.path.join(input_folder, filename)
        if os.path.exists(filepath):
            temp_df = pd.read_csv(filepath)
            temp_df.columns = [col.lower() for col in temp_df.columns]
            yearly_data[y] = temp_df

    if year in yearly_data:
        df_year = yearly_data[year]
        st.subheader(f"Total Fires in {year}: {len(df_year)}")
        m = folium.Map(
            location=[37.0, -119.5],
            zoom_start=6,
            tiles='CartoDB positron',
            max_bounds=True
        )
        m.fit_bounds([[32.5, -124.5], [42.0, -114.0]])

        folium.GeoJson(
            "../data/California_State_Boundary.geojson",
            style_function=lambda feature: {
                'fillOpacity': 0,
                'color': 'brown',
                'weight': 3
            }
        ).add_to(m)

        def get_color(brightness):
            if brightness < 330:
                return 'blue'
            elif 330 <= brightness < 360:
                return 'orange'
            else:
                return 'red'

        for _, row in df_year.iterrows():
            brightness = row.get('brightness', 300)
            folium.CircleMarker(
                location=[row['latitude'], row['longitude']],
                radius=3,
                color=get_color(brightness),
                fill=True,
                fill_opacity=0.7
            ).add_to(m)

        legend_template = """
        {% macro html(this, kwargs) %}
        <div style="
            position: fixed; 
            top: 180px; left: 30px; width: 160px; height: 120px; 
            background-color: white;
            border:2px solid grey;
            z-index:9999;
            font-size:13px;
            padding:10px;
            opacity: 0.9;
        ">
            <b>Fire Intensity</b><br>
            <i style=\"background:blue;width:10px;height:10px;display:inline-block;\"></i> Low (&lt;330)<br>
            <i style=\"background:orange;width:10px;height:10px;display:inline-block;\"></i> Medium (330-360)<br>
            <i style=\"background:red;width:10px;height:10px;display:inline-block;\"></i> High (&gt;360)
        </div>
        {% endmacro %}
        """
        legend = MacroElement()
        legend._template = Template(legend_template)
        m.get_root().add_child(legend)

        st_folium(m, use_container_width=True, height=600)
    else:
        st.warning("No data available for the selected year.")

# === Predictor TAB ===
with predictor_tab:

    rf = joblib.load("../app/random_forest_fire_model.pkl")
    county_columns = joblib.load("../app/county_columns.pkl")

    with st.sidebar:
        st.header("Prediction Inputs")
        brightness = st.slider("Brightness", 200.0, 500.0, 320.0)
        frp = st.slider("Fire Radiative Power (FRP)", 0.0, 400.0, 100.0)
        avg_wind_speed = st.slider("Average Wind Speed (mph)", 0.0, 25.0, 7.0)
        max_temp = st.slider("Max Temperature (°F)", 60, 120, 85)
        lat = st.number_input("Latitude\n(min: 32.5, max: 42.0)", min_value=32.5, max_value=42.0, value=37.0, step=0.01)
        lon = st.number_input("Longitude\n(min: -124.5, max: -114.0)", min_value=-124.5, max_value=-114.0, value=-120.0, step=0.01)
        county = st.selectbox("County", [col.replace("clean_county_", "") for col in county_columns])

    # Coordinate feature engineering
    x = np.cos(np.radians(lat)) * np.cos(np.radians(lon))
    y = np.cos(np.radians(lat)) * np.sin(np.radians(lon))
    z = np.sin(np.radians(lat))

    input_data = {
        "brightness": brightness,
        "frp": frp,
        "avg_wind_speed": avg_wind_speed,
        "max_temp": max_temp,
        "x": x,
        "y": y,
        "z": z
    }
    for col in county_columns:
        input_data[col] = 1 if county in col else 0

    input_df = pd.DataFrame([input_data])
    input_df = input_df.reindex(columns=feature_cols, fill_value=0)

    log_pred = rf.predict(input_df)[0]
    predicted_size = np.expm1(log_pred)

    st.subheader(f"Predicted Fire Size: {predicted_size:.2f} acres")

    CA_BOUNDS = [[32.5, -124.5], [42.0, -114.0]]
    m = folium.Map(
        location=[37.0, -119.5],
        zoom_start=6,
        tiles="CartoDB positron",
        control_scale=True,
        zoom_control=True,
        prefer_canvas=True,
        max_bounds=True
    )
    m.fit_bounds(CA_BOUNDS)

    if predicted_size < 330:
        color = 'blue'
    elif 330 <= predicted_size < 360:
        color = 'orange'
    else:
        color = 'red'

    folium.CircleMarker(
        location=[lat, lon],
        radius=10,
        popup=f"Predicted: {predicted_size:.2f} acres",
        color=color,
        fill=True,
        fill_color=color,
        fill_opacity=0.8
    ).add_to(m)

    folium.GeoJson(
        "../data/California_State_Boundary.geojson",
        style_function=lambda feature: {
            'color': 'brown',
            'weight': 2,
            'fillOpacity': 0
        }
    ).add_to(m)

    legend_template = """
    {% macro html(this, kwargs) %}
    <div style="
        position: fixed; 
        top: 180px; left: 30px; width: 160px; height: 120px; 
        background-color: white;
        border:2px solid grey;
        z-index:9999;
        font-size:13px;
        padding:10px;
        opacity: 0.9;
    ">
        <b>Fire Intensity</b><br>
        <i style=\"background:blue;width:10px;height:10px;display:inline-block;\"></i> Low (&lt;330)<br>
        <i style=\"background:orange;width:10px;height:10px;display:inline-block;\"></i> Medium (330-360)<br>
        <i style=\"background:red;width:10px;height:10px;display:inline-block;\"></i> High (&gt;360)
    </div>
    {% endmacro %}
    """
    legend = MacroElement()
    legend._template = Template(legend_template)
    m.get_root().add_child(legend)

    st_folium(m, use_container_width=True, height=600)
