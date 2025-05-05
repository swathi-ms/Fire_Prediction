import streamlit as st
import numpy as np
import pandas as pd
import joblib
import folium
import os
from branca.element import Template, MacroElement
from streamlit_folium import st_folium
from sklearn.ensemble import RandomForestRegressor

# Page layout
st.set_page_config(layout="wide")

# Sidebar year selection for Viewer
st.sidebar.title("Year Selection")
year = st.sidebar.slider('Select Year', 2000, 2023, 2000)

# California bounds
CA_BOUNDS = [[32.5, -124.5], [42.0, -114.0]]

# Create two tabs
viewer_tab, predictor_tab = st.tabs(["🗺️ California Fire Viewer (2000–2023)", "🔥 Wildfire Size Predictor"])

# === TAB: Fire Viewer ===
with viewer_tab:
    st.title("🗺️ California Fire Data Viewer (2000–2023)")

    input_folder = '../data/modis_satellite_data/california_data'
    yearly_data = {}
    for y in range(2000, 2024):
        filename = f'california_{y}.csv'
        filepath = os.path.join(input_folder, filename)
        if os.path.exists(filepath):
            df = pd.read_csv(filepath)
            df.columns = [col.lower() for col in df.columns]
            yearly_data[y] = df

    if year in yearly_data:
        df_year = yearly_data[year]
        m = folium.Map(
            location=[37.0, -119.5],
            zoom_start=6,
            tiles='CartoDB positron',
            max_bounds=True
        )
        m.fit_bounds(CA_BOUNDS)

        california_geojson = "../data/California_State_Boundary.geojson"
        folium.GeoJson(
            california_geojson,
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
            bottom: 50px; left: 50px; width: 160px; height: 120px; 
            background-color: white;
            border:2px solid grey;
            z-index:9999;
            font-size:14px;
            padding:10px;
            opacity: 0.8;
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

# === TAB: Wildfire Predictor ===
with predictor_tab:
    st.title("🔥 Wildfire Size Predictor (California)")
    st.markdown("Estimate wildfire size using environmental features and geographic location. Adjust inputs on the left. View predicted size and location on the map.")

    rf = joblib.load("random_forest_fire_model_minimal_updated.pkl")

    with st.sidebar:
        st.header("Prediction Inputs")
        brightness = st.slider("Brightness", 200.0, 500.0, 320.0)
        frp = st.slider("Fire Radiative Power (FRP)", 0.0, 400.0, 100.0)
        avg_wind_speed = st.slider("Average Wind Speed (mph)", 0.0, 25.0, 7.0)
        max_temp = st.slider("Max Temperature (°F)", 60, 120, 85)
        lat = st.number_input("Latitude\n(min: 32.5, max: 42.0)", min_value=32.5, max_value=42.0, value=37.0, step=0.01)
        lon = st.number_input("Longitude\n(min: -124.5, max: -114.0)", min_value=-124.5, max_value=-114.0, value=-120.0, step=0.01)

    # Coordinate feature engineering
    x = np.cos(np.radians(lat)) * np.cos(np.radians(lon))
    y = np.cos(np.radians(lat)) * np.sin(np.radians(lon))
    z = np.sin(np.radians(lat))

    input_df = pd.DataFrame([{
        "brightness": brightness,
        "frp": frp,
        "avg_wind_speed": avg_wind_speed,
        "max_temp": max_temp,
        "x": x,
        "y": y,
        "z": z
    }])

    log_pred = rf.predict(input_df)[0]
    predicted_size = np.expm1(log_pred)

    st.subheader(f" Predicted Fire Size: {predicted_size:.2f} acres")

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

    # Color coding
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
        bottom: 50px; left: 50px; width: 160px; height: 120px; 
        background-color: white;
        border:2px solid grey;
        z-index:9999;
        font-size:14px;
        padding:10px;
        opacity: 0.8;
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
