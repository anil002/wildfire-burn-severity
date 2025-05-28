
"""
Original Project Author: IndigoWizard, Sep 24, 2022.
Project Name: Wildfire Burn Severity Analysis
License: GPL-3.0 (See LICENSE file for details)
"""

import streamlit as st
import ee
from ee import oauth
from google.oauth2 import service_account
import folium
from streamlit_folium import folium_static
from streamlit_elements import elements, mui
from streamlit_elements import nivo
from datetime import datetime, timedelta
import json
import pandas as pd
import calendar
import altair as alt
from typing import Dict

st.set_page_config(
    page_title="Wildfire Burn Severity Analysis",
    page_icon="https://cdn-icons-png.flaticon.com/512/7204/7204183.png",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': "https://github.com/IndigoWizard/wildfire-burn-severity",
        'Report a Bug': "https://github.com/IndigoWizard/wildfire-burn-severity/issues",
        'About': "This app was developed by [IndigoWizard](https://github.com/IndigoWizard/wildfire-burn-severity) for environmental monitoring and geospatial analysis. Give proper credit when forking/using the open source code."
    }
)

### CSS Styling
st.markdown(
"""
<style>
    /* Header */
    header {
        height: 1rem;
        background: none;
    }
    /* Title */
    h1#wildfire-burn-severity-analysis {
        font-size: 1.75rem;
        padding: 1.8rem 0 0.5rem;
    }
    /* Main body */
    main {
        scroll-behavior: smooth;
        padding: 0.2rem 2rem;
    }
    @media (min-width: 744px) {
        main {
            padding: 0.2rem 2rem;
        }
    }
    /* Sidebar */
    .stSidebar {
        min-width: 280px;
        max-width: fit-content;
        background-color: rgb(38, 39, 48);
        color: #fafafa;
    }
    @media (max-width: 576px) {
        .stSidebar {
            background-color: rgb(38, 39, 48);
            color: #fafafa;
        }
    }
    /* Sidebar logo */
    .stSidebar img {
        display: block;
        margin: auto;
        width: 90px;
    }
    /* Sidebar navigation */
    .stSidebar ul {
        margin: 0;
        padding: 0;
        list-style: none;
    }
    .stSidebar ul li {
        padding: 0;
        font-weight: 600;
    }
    .stSidebar ul li a {
        text-decoration: none;
        transition: 0.2s ease-in-out;
        padding: 0 10px;
        color: #fafafa;
    }
    .stSidebar ul li a:hover {
        color: rgb(46, 206, 255);
        background: #131720;
        border-radius: 4px;
    }
    /* Sidebar socials */
    .stSidebar p {
        display: flex;
        flex-direction: row;
        gap: 0.8rem;
        padding: 0 10px;
    }
    .stSidebar p a img {
        width: 32px;
    }
    .stSidebar p a:nth-child(2) img {
        background-color: #26273040;
        border-radius: 50%;
    }
    /* Upload section */
    .upload-info {
        background-color: rgb(215, 210, 225);
        color: rgb(40, 40, 55);
        padding: 1rem;
        border-radius: 5px;
    }
    .stButton button {
        width: 100%;
        background: rgba(0, 3, 172, 0.25);
    }
    .stButton button:hover {
        border-color: rgb(255, 0, 110);
        color: rgb(255, 0, 110);
    }
    /* Legend */
    .ndwilegend, .reclassifieddNBR {
        transition: 0.2s ease-in-out;
        border-radius: 5px;
        box-shadow: 0 0 5px rgba(0, 0, 0, 0.2);
        background: rgba(0, 0, 0, 0.05);
        padding: 1rem;
    }
    .ndwilegend:hover, .reclassifieddNBR:hover {
        box-shadow: 0 0 5px rgba(0, 0, 0, 0.8);
        background: rgba(0, 0, 0, 0.12);
        cursor: pointer;
    }
    /* Map iframe */
    iframe {
        width: 100%;
    }
    /* Date picker styling */
    .date-picker-container {
        padding: 0.5rem;
        border-radius: 5px;
        margin-bottom: 1rem;
    }
    .pre-fire-date {
        background-color: rgba(255, 193, 7, 0.1);
        border: 1px solid #ffc107;
    }
    .post-fire-date {
        background-color: rgba(40, 167, 69, 0.1);
        border: 1px solid #28a745;
    }
</style>
""", unsafe_allow_html=True)

# Google Earth Engine Authentication
@st.cache_resource
def ee_authenticate():
    """
    Authenticate with Google Earth Engine using a service account or local CLI credentials.
    """
    try:
        if "json_key" in st.secrets:
            st.info("Authenticating with Google Earth Engine using service account...")
            json_creds = st.secrets["json_key"]
            if isinstance(json_creds, (dict, st.runtime.secrets.AttrDict)):
                service_account_info = dict(json_creds)
            elif isinstance(json_creds, str):
                service_account_info = json.loads(json_creds)
            else:
                raise ValueError("Invalid json_key format in secrets. Expected dict, AttrDict, or JSON string.")
            if "client_email" not in service_account_info:
                raise ValueError("Service account email address missing in json_key")
            creds = service_account.Credentials.from_service_account_info(
                service_account_info, scopes=oauth.SCOPES
            )
            ee.Initialize(creds)
            st.success("Successfully authenticated with Google Earth Engine using service account.")
        else:
            st.info("Attempting authentication using Earth Engine CLI credentials...")
            ee.Initialize()
            st.success("Authenticated with Google Earth Engine using local CLI credentials.")
    except Exception as e:
        st.error(f"Failed to authenticate with Google Earth Engine: {str(e)}")
        st.markdown(
            "**Steps to resolve:**\n"
            "- **Local setup**: Create `.streamlit/secrets.toml` with a valid service account key, or run `earthengine authenticate`.\n"
            "  Example `secrets.toml`:\n"
            "  ```toml\n"
            "  [json_key]\n"
            "  type = 'service_account'\n"
            "  project_id = 'your-project-id'\n"
            "  private_key_id = 'your-private-key-id'\n"
            "  private_key = '-----BEGIN PRIVATE KEY-----\\n...\\n-----END PRIVATE KEY-----\\n'\n"
            "  client_email = 'your-service-account@your-project-id.iam.gserviceaccount.com'\n"
            "  client_id = 'your-client-id'\n"
            "  auth_uri = 'https://accounts.google.com/o/oauth2/auth'\n"
            "  token_uri = 'https://oauth2.googleapis.com/token'\n"
            "  auth_provider_x509_url = 'https://www.googleapis.com/oauth2/v1/certs'\n"
            "  client_x509_cert_url = 'https://www.googleapis.com/robot/v1/metadata/x509/your-service-account%40your-project-id.iam.gserviceaccount.com'\n"
            "  universe_domain = 'googleapis.com'\n"
            "  ```\n"
            "- **Cloud deployment**: Configure `[json_key]` in Streamlit secrets.\n"
            "- Ensure the service account has Earth Engine permissions (`roles/earthengine.user`).\n"
            "- Register at https://developers.google.com/earth-engine/guides/access.\n"
            "- Verify internet and Google Cloud project settings."
        )
        st.stop()

# Add Earth Engine layer to Folium map
def add_ee_layer(self, ee_image_object: ee.Image, vis_params: Dict, name: str):
    """Add a Google Earth Engine image layer to a Folium map."""
    try:
        map_id_dict = ee.Image(ee_image_object).getMapId(vis_params)
        layer = folium.raster_layers.TileLayer(
            tiles=map_id_dict['tile_fetcher'].url_format,
            attr='Map Data © <a href="https://earthengine.google.com/">Google Earth Engine</a>',
            name=name,
            overlay=True,
            control=True
        )
        layer.add_to(self)
        return layer
    except Exception as e:
        st.error(f"Error adding layer to map: {str(e)}")
        return None

folium.Map.add_ee_layer = add_ee_layer

# Create and filter GEE image collection
@st.cache_resource
def satCollection(start_date, end_date, cloud_rate, _aoi):
    try:
        collection = (
            ee.ImageCollection('COPERNICUS/S2_SR')
            .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", cloud_rate))
            .filterDate(start_date, end_date)
            .filterBounds(_aoi)
        )
        
        if collection.size().getInfo() == 0:
            st.warning(f"No Sentinel-2 images found for {start_date} to {end_date} with cloud coverage < {cloud_rate}%. Try expanding the date range or increasing cloud tolerance.")
            return None
        
        def clipCollection(image):
            return image.clip(_aoi).divide(10000)
        
        collection = collection.map(clipCollection)
        return collection
    except Exception as e:
        st.error(f"Error fetching satellite data: {str(e)}")
        return None

# Upload GeoJSON files
last_uploaded_centroid = None
def upload_files_proc(upload_files):
    global last_uploaded_centroid
    geometry_aoi_list = []

    if not upload_files:
        return ee.Geometry.Point([16.25, 36.65]), None

    try:
        for upload_file in upload_files:
            bytes_data = upload_file.read()
            geojson_data = json.loads(bytes_data)

            if 'features' in geojson_data and isinstance(geojson_data['features'], list):
                features = geojson_data['features']
            elif 'geometries' in geojson_data and isinstance(geojson_data['geometries'], list):
                features = [{'geometry': geo} for geo in geojson_data['geometries']]
            else:
                st.warning("Invalid GeoJSON format. Expected 'features' or 'geometries'.")
                continue

            for feature in features:
                if 'geometry' in feature and 'coordinates' in feature['geometry']:
                    coordinates = feature['geometry']['coordinates']
                    geometry = ee.Geometry.Polygon(coordinates) if feature['geometry']['type'] == 'Polygon' else ee.Geometry.MultiPolygon(coordinates)
                    geometry_aoi_list.append(geometry)
                    last_uploaded_centroid = geometry.centroid(maxError=1).getInfo()['coordinates']
                else:
                    st.warning("Invalid geometry in GeoJSON file.")

        if geometry_aoi_list:
            return ee.Geometry.MultiPolygon(geometry_aoi_list), last_uploaded_centroid
        else:
            st.warning("No valid geometries found in uploaded files.")
            return ee.Geometry.Point([16.25, 36.65]), None
    except Exception as e:
        st.error(f"Error processing GeoJSON: {str(e)}")
        return ee.Geometry.Point([16.25, 36.65]), None

# Calculate raster area
@st.cache_resource
def calculate_class_area(_classified_image, _geometry_aoi, class_value):
    try:
        class_pixel_area = _classified_image.eq(class_value).multiply(ee.Image.pixelArea())
        class_area = class_pixel_area.reduceRegion(
            reducer=ee.Reducer.sum(),
            geometry=_geometry_aoi,
            scale=10,
            maxPixels=1e10
        )
        area_value = class_area.getInfo()
        return area_value.get(list(area_value.keys())[0], 0)
    except Exception as e:
        st.error(f"Error calculating class area: {str(e)}")
        return 0

# Calculate GeoJSON area
@st.cache_resource
def geojson_area(_aoi):
    try:
        aoi_area_sqm = _aoi.area()
        aoi_area_rounded = round(aoi_area_sqm.getInfo()/1e6, 4)
        return aoi_area_rounded
    except Exception as e:
        st.error(f"Error calculating GeoJSON area: {str(e)}")
        return 0

# Main function
def main():
    # Initialize GEE
    with st.spinner("Initializing Google Earth Engine..."):
        ee_authenticate()

    # Sidebar
    with st.sidebar:
        st.logo(image="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAAC0lEQVQIW2NgAAIAAAUAAR4f7BQAAAAASUVORK5CYII=", icon_image="https://cdn-icons-png.flaticon.com/512/7204/7204183.png")
        st.image("https://cdn-icons-png.flaticon.com/512/7204/7204183.png", width=90)
        st.markdown("#### Wildfire Burn Severity Analysis")
        st.subheader("Navigation:")
        st.markdown(
            """
            - [Wildfire Map](#wildfire-burn-severity-analysis)
            - [Map Legend](#map-legend)
            - [Analysis Report](#analysis-report)
            - [Interpreting the Results](#interpreting-the-results)
            - [Environmental Index](#usage-the-environmental-index-nbr-dnbr)
            - [Data](#data)
            - [Credit](#credit)
            """
        )
        st.subheader("Contact:")
        st.markdown(
            """
            [![LinkedIn](https://content.linkedin.com/content/dam/me/brand/en-us/brand-home/logos/In-Blue-Logo.png.original.png)](https://www.linkedin.com/in/anil-kumar-singh-phd-b192554a/)
            [![ResearchGate](https://images.seeklogo.com/logo-png/38/1/researchgate-logo-png_seeklogo-380355.png)](https://www.researchgate.net/profile/Anil-Kumar-Singh-6?ev=hdr_xprf)
            """
        )
        
    with st.container():
        st.title("Wildfire Burn Severity Analysis")
        st.markdown("**Evaluate Wildfire Burn Severity through NBR Analysis: Assess the Impact of Wildfires Through Delta NBR Index Values Using Sentinel-2 Satellite Images!**")

    # User input form
    with st.form("input_form"):
        c1, c2 = st.columns([3, 1])

        with c2:
            st.info("Cloud Coverage 🌥️", icon="🌥️")
            cloud_pixel_percentage = st.slider(
                label="Cloud pixel rate (%)",
                min_value=5,
                max_value=100,
                step=5,
                value=75,
                help="Set maximum allowable cloud cover for satellite images. Lower values ensure clearer images but may reduce data availability."
            )

            st.info("Upload Area Of Interest file:", icon="📁")
            upload_files = st.file_uploader(
                "Create a GeoJSON file at: [geojson.io](https://geojson.io/)",
                accept_multiple_files=True,
                help="Upload GeoJSON files defining the region to analyze."
            )
            geometry_aoi, centroid = upload_files_proc(upload_files)

            st.info("Custom Color Palettes", icon="🎨")
            accessibility = st.selectbox(
                "Accessibility: Colorblind-friendly Palettes",
                ["Normal", "Deuteranopia", "Protanopia", "Tritanopia", "Achromatopsia"],
                help="Choose a palette optimized for color vision deficiencies."
            )

            default_dnbr_palette = ["#ffffe5", "#f7fcb9", "#78c679", "#41ab5d", "#238443", "#005a32"]
            default_dNBR_classified_palette = ['#1c742c', '#2aae29', '#a1d574', '#f8ebb0', '#f7a769', '#e86c4e', '#902cd6']
            default_ndwi_palette = ["#caf0f8", "#00b4d8", "#023e8a"]

            ndwi_palette = default_ndwi_palette.copy()
            dnbr_palette = default_dnbr_palette.copy()
            dNBR_classified_palette = default_dNBR_classified_palette.copy()

            if accessibility == "Deuteranopia":
                dnbr_palette = ["#fffaa1", "#f4ef8e", "#9a5d67", "#573f73", "#372851", "#191135"]
                dNBR_classified_palette = ["#95a600", "#92ed3e", "#affac5", "#78ffb0", "#69d6c6", "#22459c", "#000e69"]
            elif accessibility == "Protanopia":
                dnbr_palette = ["#a6f697", "#7def75", "#2dcebb", "#1597ab", "#0c677e", "#002c47"]
                dNBR_classified_palette = ["#95a600", "#92ed3e", "#affac5", "#78ffb0", "#69d6c6", "#22459c", "#000e69"]
            elif accessibility == "Tritanopia":
                dnbr_palette = ["#cdffd7", "#a1fbb6", "#6cb5c6", "#3a77a5", "#205080", "#001752"]
                dNBR_classified_palette = ["#ed4700", "#ed8a00", "#e1fabe", "#99ff94", "#87bede", "#2e40cf", "#0600bc"]
            elif accessibility == "Achromatopsia":
                dnbr_palette = ["#407de0", "#2763da", "#394388", "#272c66", "#16194f", "#010034"]
                dNBR_classified_palette = ["#004f3d", "#338796", "#66a4f5", "#3683ff", "#3d50ca", "#421c7f", "#290058"]

        with c1:
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown(
                    '<div class="date-picker-container pre-fire-date">',
                    unsafe_allow_html=True
                )
                st.warning("Pre-Fire NBR Date Range 📅", icon="📅")
                pre_fire_dates = st.date_input(
                    "Select pre-fire date range",
                    value=(datetime(2023, 7, 5), datetime(2023, 7, 12)),
                    min_value=datetime(2015, 6, 23),  # Sentinel-2 start
                    max_value=datetime.now(),
                    help="Choose a date range before the wildfire to capture baseline imagery. A 7-day range is recommended.",
                    key="pre_fire_range"
                )
                st.markdown('</div>', unsafe_allow_html=True)
                st.info(
                    "Select a range capturing clear pre-fire imagery. Avoid periods with high cloud cover.",
                    icon="ℹ️"
                )

            with col2:
                st.markdown(
                    '<div class="date-picker-container post-fire-date">',
                    unsafe_allow_html=True
                )
                st.success("Post-Fire NBR Date Range 📅", icon="📅")
                post_fire_dates = st.date_input(
                    "Select post-fire date range",
                    value=(datetime(2023, 7, 20), datetime(2023, 7, 27)),
                    min_value=datetime(2015, 6, 23),
                    max_value=datetime.now(),
                    help="Choose a date range after the wildfire to assess burn severity. A 7-day range is recommended.",
                    key="post_fire_range"
                )
                st.markdown('</div>', unsafe_allow_html=True)
                st.info(
                    "Select a range capturing post-fire imagery to compare with pre-fire data.",
                    icon="ℹ️"
                )

            # Validate date ranges
            if isinstance(pre_fire_dates, tuple) and isinstance(post_fire_dates, tuple):
                pre_fire_start, pre_fire_end = pre_fire_dates
                post_fire_start, post_fire_end = post_fire_dates

                if pre_fire_start > pre_fire_end:
                    st.error("Pre-fire start date must be before end date.")
                    st.stop()
                if post_fire_start > post_fire_end:
                    st.error("Post-fire start date must be before end date.")
                    st.stop()
                if pre_fire_end >= post_fire_start:
                    st.error("Pre-fire date range must be before post-fire date range.")
                    st.stop()
                if (pre_fire_end - pre_fire_start).days > 30 or (post_fire_end - post_fire_start).days > 30:
                    st.warning("Date ranges longer than 30 days may slow down processing. Consider narrowing the range.")
                
                str_pre_fire_start = pre_fire_start.strftime('%Y-%m-%d')
                str_pre_fire_end = pre_fire_end.strftime('%Y-%m-%d')
                str_post_fire_start = post_fire_start.strftime('%Y-%m-%d')
                str_post_fire_end = post_fire_end.strftime('%Y-%m-%d')
            else:
                st.error("Please select valid date ranges for both pre-fire and post-fire periods.")
                st.stop()

        # Map generation
        with st.spinner("Generating map..."):
            latitude = centroid[1] if centroid else 36.60
            longitude = centroid[0] if centroid else 16.00
            m = folium.Map(location=[latitude, longitude], tiles=None, zoom_start=11 if centroid else 5, control_scale=True)

            b0 = folium.TileLayer('OpenStreetMap', name="Open Street Map", attr="OSM")
            b0.add_to(m)
            b1 = folium.TileLayer('cartodbdark_matter', name='Dark Basemap', attr='CartoDB')
            b1.add_to(m)

            pre_fire_collection = satCollection(str_pre_fire_start, str_pre_fire_end, cloud_pixel_percentage, geometry_aoi)
            post_fire_collection = satCollection(str_post_fire_start, str_post_fire_end, cloud_pixel_percentage, geometry_aoi)

            if pre_fire_collection is None or post_fire_collection is None:
                st.error("Cannot generate map due to missing satellite data. Adjust date ranges or cloud coverage.")
                st.stop()

            pre_fire = pre_fire_collection.median()
            post_fire = post_fire_collection.median()

            pre_fire_satImg = pre_fire
            post_fire_satImg = post_fire

            satImg_params = {
                'bands': ['B12', 'B11', 'B4'],
                'min': 0,
                'max': 1,
                'gamma': 1.1
            }

            def get_NDWI(image):
                return image.normalizedDifference(['B3', 'B11'])

            pre_fire_ndwi = get_NDWI(pre_fire)
            post_fire_ndwi = get_NDWI(post_fire)

            ndwi_params = {
                'min': -1,
                'max': 0,
                'palette': ndwi_palette
            }

            def get_NBR(image):
                return image.normalizedDifference(['B8', 'B12'])

            pre_fire_NBR = get_NBR(pre_fire_satImg)
            post_fire_NBR = get_NBR(post_fire_satImg)
            dNBR = pre_fire_NBR.subtract(post_fire_NBR)

            dNBR_params = {
                'min': -0.5,
                'max': 1.3,
                'palette': dnbr_palette
            }

            dNBR_classified = ee.Image(dNBR) \
                .where(dNBR.gte(-0.5).And(dNBR.lt(-0.251)), 1) \
                .where(dNBR.gte(-0.250).And(dNBR.lt(-0.101)), 2) \
                .where(dNBR.gte(-0.100).And(dNBR.lt(0.99)), 3) \
                .where(dNBR.gte(0.100).And(dNBR.lt(0.269)), 4) \
                .where(dNBR.gte(0.270).And(dNBR.lt(0.439)), 5) \
                .where(dNBR.gte(0.440).And(dNBR.lt(0.659)), 6) \
                .where(dNBR.gte(0.660).And(dNBR.lte(1.300)), 7)

            dNBR_classified_params = {
                'min': 1,
                'max': 7,
                'palette': dNBR_classified_palette
            }

            masked_pre_fire_ndwi = pre_fire_ndwi.updateMask(pre_fire_ndwi.gt(-0.12))
            binaryMask = pre_fire_ndwi.lt(-0.1)
            waterMask = binaryMask.selfMask()
            masked_dNBR_classified = dNBR_classified.updateMask(waterMask)

            dNBR_classified_burn = dNBR_classified.gte(4)
            dNBR_classified_burn = dNBR_classified_burn.updateMask(dNBR_classified_burn.neq(0))

            vectors = dNBR_classified_burn.addBands(dNBR_classified_burn).reduceToVectors(
                geometry=geometry_aoi,
                crs=dNBR_classified_burn.projection(),
                scale=10,
                geometryType='polygon',
                eightConnected=False,
                labelProperty='zone',
                reducer=ee.Reducer.mean(),
                bestEffort=True
            )
            burn_scar = ee.Image(0).updateMask(0).paint(vectors, '000000', 2)

            if pre_fire_start == post_fire_start:
                m.add_ee_layer(post_fire_satImg, satImg_params, 'Satellite Imagery')
            else:
                m.add_ee_layer(pre_fire_satImg, satImg_params, f'Pre-Fire Satellite Imagery: {str_pre_fire_start} to {str_pre_fire_end}')
                m.add_ee_layer(post_fire_satImg, satImg_params, f'Post-Fire Satellite Imagery: {str_post_fire_start} to {str_post_fire_end}')
                m.add_ee_layer(masked_pre_fire_ndwi, ndwi_params, f'NDWI: {str_pre_fire_start}')
                m.add_ee_layer(masked_dNBR_classified, dNBR_classified_params, 'Reclassified dNBR')
                m.add_ee_layer(burn_scar, {'palette': '#87043b'}, 'Burn Scar')

            folium.LayerControl(collapsed=True).add_to(m)

        submitted = c2.form_submit_button("Generate Map", type="primary")
        if submitted:
            st.write("Map form submitted successfully!")
            with c1:
                folium_static(m, width=800, height=600)
        else:
            with c1:
                folium_static(m, width=800, height=600)

    # Legend
    with st.container():
        st.subheader("Map Legend:")
        col3, col4, col5 = st.columns([1, 2, 1])
        with col3:
            ndwi_legend_html = f"""
                <div class="ndwilegend">
                    <h5>NDWI</h5>
                    <div style="display: flex; flex-direction: row; align-items: flex-start; gap: 1rem; width: 100%;">
                        <div style="width: 30px; height: 200px; background: linear-gradient({ndwi_palette[0]},{ndwi_palette[1]},{ndwi_palette[2]}); border-radius: 2px;"></div>
                        <div style="display: flex; flex-direction: column; justify-content: space-between; height: 200px;">
                            <span>-1</span>
                            <span style="align-self: flex-end;">1</span>
                        </div>
                    </div>
                </div>
            """
            st.markdown(ndwi_legend_html, unsafe_allow_html=True)

        with col4:
            reclassified_dNBR_legend_html = f"""
                <div class="reclassifieddNBR">
                    <h5>Reclassified Delta NBR</h5>
                    <ul style="list-style-type: none; padding: 0;">
                        <li style="margin: 0.2em 0; padding: 0;"><span style="background-color: {dNBR_classified_palette[0]}; opacity: 0.75; display: inline-block; width: 15px; height: 15px; border-radius: 50%; margin-right: 5px;"></span> Enhanced Regrowth (High)</li>
                        <li style="margin: 0.2em 0; padding: 0;"><span style="background-color: {dNBR_classified_palette[1]}; opacity: 0.75; display: inline-block; width: 15px; height: 15px; border-radius: 50%; margin-right: 5px;"></span> Enhanced Regrowth (Low)</li>
                        <li style="margin: 0.2em 0; padding: 0;"><span style="background-color: {dNBR_classified_palette[2]}; opacity: 0.75; display: inline-block; width: 15px; height: 15px; border-radius: 50%; margin-right: 5px;"></span> Unburned</li>
                        <li style="margin: 0.2em 0; padding: 0;"><span style="background-color: {dNBR_classified_palette[3]}; opacity: 0.75; display: inline-block; width: 15px; height: 15px; border-radius: 50%; margin-right: 5px;"></span> Low Severity Burns</li>
                        <li style="margin: 0.2em 0; padding: 0;"><span style="background-color: {dNBR_classified_palette[4]}; opacity: 0.75; display: inline-block; width: 15px; height: 15px; border-radius: 50%; margin-right: 5px;"></span> Moderate-Low Severity Burns</li>
                        <li style="margin: 0.2em 0; padding: 0;"><span style="background-color: {dNBR_classified_palette[5]}; opacity: 0.75; display: inline-block; width: 15px; height: 15px; border-radius: 50%; margin-right: 5px;"></span> Moderate-High Severity Burns</li>
                        <li style="margin: 0.2em 0; padding: 0;"><span style="background-color: {dNBR_classified_palette[6]}; opacity: 0.75; display: inline-block; width: 15px; height: 15px; border-radius: 50%; margin-right: 5px;"></span> High Severity Burns</li>
                    </ul>
                </div>
            """
            st.markdown(reclassified_dNBR_legend_html, unsafe_allow_html=True)

    # Analysis Report
    with st.form("report_form"):
        st.write("#### Analysis Report")
        submit_button = st.form_submit_button("Generate Report", type="primary")
        
        if submit_button:
            with st.spinner("Generating report..."):
                st.write("Report form submitted successfully!")
                geometry_area = geojson_area(geometry_aoi)

                dNBR_class_areas = []
                class_names = [
                    "Enhanced Regrowth (High)",
                    "Enhanced Regrowth (Low)",
                    "Unburned",
                    "Low Severity Burns",
                    "Moderate-Low Severity Burns",
                    "Moderate-High Severity Burns",
                    "High Severity Burns",
                ]
                for i in range(1, 8):
                    area = calculate_class_area(masked_dNBR_classified, geometry_aoi, i)
                    dNBR_class_areas.append(area / 1e6)

                st.write("#### Wildfire Burn Severity Analysis Report:")
                col1, col2 = st.columns([1, 1])
                col3, col4 = st.columns([1.5, 2])

                centroid_info = f"**ROI Location:** [:blue[{round(latitude, 4)}], :blue[{round(longitude, 4)}]]"
                area_of_interest = f"**Surface Area of Region of Interest: ~:blue[{geometry_area}] (Km²)**"
                initial_date_range = f"**Pre-Fire date range:** :blue-background[{str_pre_fire_start} to {str_pre_fire_end}]"
                updated_date_range = f"**Post-Fire date range:** :blue-background[{str_post_fire_start} to {str_post_fire_end}]"
                col1.success(centroid_info)
                col1.success(area_of_interest)
                col2.success(initial_date_range)
                col2.success(updated_date_range)

                for i, area in enumerate(dNBR_class_areas, start=1):
                    class_sq = f"**{class_names[i-1]}: ~** :green[{round(area, 4)}] **(Km²)**"
                    col3.info(class_sq)

                with col4:
                    DATA_PIE = [
                        {"id": class_names[i-1], "label": class_names[i-1], "value": round(area, 4), "color": dNBR_classified_palette[i-1]}
                        for i, area in enumerate(dNBR_class_areas, start=1)
                    ]
                    with elements("nivo_pie_chart"):
                        with mui.Box(sx={"height": 500}):
                            nivo.Pie(
                                data=DATA_PIE,
                                margin={"top": 20, "right": 100, "bottom": 150, "left": 100},
                                innerRadius=0.5,
                                padAngle=0.7,
                                cornerRadius=3,
                                activeOuterRadiusOffset=8,
                                borderWidth=1,
                                borderColor={"from": "color", "modifiers": [["darker", 0.8]]},
                                arcLinkLabelsSkipAngle=2,
                                arcLinkLabelsTextColor={"from": "color"},
                                arcLinkLabelsColor={"from": "color"},
                                colors={"datum": 'data.color'},
                                arcLinkLabel="value",
                                arcLinkLabelsThickness=2,
                                arcLinkLabelsDiagonalLength=10,
                                arcLinkLabelsStraightLength=10,
                                arcLinkLabelsTextOffset=4,
                                arcLabelsTextColor={"from": "color", "modifiers": [["darker", 4]]},
                                defs=[
                                    {
                                        "id": f"Class{i}",
                                        "type": "patternDots" if i > 4 else "patternLines" if i <= 2 else "patternSquares",
                                        "color": dNBR_classified_palette[i-1],
                                        "background": f"{dNBR_classified_palette[i-1]}bf",
                                        "rotation": 105 if i <= 2 else 0,
                                        "lineWidth": 3 if i <= 2 else 4,
                                        "spacing": 10 if i <= 2 else 3,
                                        "size": 4 if i > 2 else None,
                                        "padding": 3 if i > 2 else None,
                                        "stagger": True if i > 2 else False,
                                    } for i in range(1, 8)
                                ],
                                fill=[{"match": {"id": class_names[i-1]}, "id": f"Class{i}"} for i in range(1, 8)],
                                theme={
                                    "tooltip": {
                                        "container": {
                                            "background": "white",
                                            "fontSize": 14,
                                            "font-family": "sans-serif",
                                            "padding": 2,
                                            "border-radius": 4
                                        },
                                        "basic": {
                                            "whiteSpace": "pre",
                                            "display": "flex",
                                            "flex-direction": "row",
                                            "alignItems": "center",
                                            "justify-content": "space-around",
                                            "background": "#0e1117",
                                            "margin": 1,
                                            "padding": 5,
                                            "width": "fit-content",
                                            "height": "fit-content",
                                            "color": "white",
                                        },
                                    }
                                }
                            )

    # Precipitation Calculation
    def chirpsCollection(initialDate, endDate, _aoi):
        try:
            chirps = (
                ee.ImageCollection("UCSB-CHG/CHIRPS/DAILY")
                .filterDate(initialDate, endDate)
                .filterBounds(_aoi)
                .select("precipitation")
            )
            if chirps.size().getInfo() == 0:
                st.warning("No precipitation data available for the specified date range.")
                return None
            return chirps
        except Exception as e:
            st.error(f"Error fetching precipitation data: {str(e)}")
            return None

    def full_month_precipitation(initialDate, endDate, _aoi):
        try:
            initial_date = datetime.strptime(initialDate, "%Y-%m-%d")
            end_date = datetime.strptime(endDate, "%Y-%m-%d")
            start_of_month = initial_date.replace(day=1)
            _, end_of_month_day = calendar.monthrange(end_date.year, end_date.month)
            end_of_month = end_date.replace(day=end_of_month_day)

            if initial_date.month == end_date.month and initial_date.year == end_date.year:
                start_of_month = initial_date.replace(day=1)
                end_of_month = end_date.replace(day=end_of_month_day)

            raincol = chirpsCollection(start_of_month.strftime("%Y-%m-%d"), end_of_month.strftime("%Y-%m-%d"), _aoi)
            if raincol is None:
                return pd.DataFrame({"Date": [], "Precipitation": []})

            daily_precipitation = raincol.map(
                lambda img: ee.Feature(
                    _aoi,
                    {
                        "date": img.date().format("YYYY-MM-dd"),
                        "precipitation": img.reduceRegion(
                            reducer=ee.Reducer.mean(),
                            geometry=_aoi,
                            scale=30
                        ).get("precipitation"),
                    }
                )
            )
            daily_list = daily_precipitation.getInfo()["features"]
            dates = [entry["properties"]["date"] for entry in daily_list]
            values = [entry["properties"]["precipitation"] for entry in daily_list]
            rdf = pd.DataFrame({"Date": dates, "Precipitation": [round(value, 2) if value is not None else None for value in values]})
            return rdf
        except Exception as e:
            st.error(f"Error processing precipitation data: {str(e)}")
            return pd.DataFrame({"Date": [], "Precipitation": []})

    with st.container():
        col5, col6 = st.columns([1, 2])
        rdf = full_month_precipitation(str_pre_fire_start, str_post_fire_end, geometry_aoi)
        col5.subheader("Data table:")
        col5.dataframe(
            rdf,
            column_config={
                "Date": "Date",
                "Precipitation": st.column_config.ProgressColumn(
                    "Rainfall (mm)", format=" %f mm", min_value=0, max_value=100, width="medium", help='Precipitation (mm)'
                ),
            },
            hide_index=True, width=400, height=420
        )

        def precipitation_chart(rdf):
            if rdf.empty:
                st.warning("No precipitation data to display.")
                return None
            rdf["Date"] = pd.to_datetime(rdf["Date"])
            viz_chart = alt.Chart(rdf).mark_bar(color="#88c0d0").encode(
                x=alt.X("Date:T", axis=alt.Axis(title="Time (Days)", ticks=True, tickMinStep=1)),
                y=alt.Y("Precipitation:Q", axis=alt.Axis(title=None, ticks=True, tickMinStep=1)),
                tooltip=["Date:T", "Precipitation:Q"]
            ) + alt.Chart(rdf).mark_line(color="#004dc6", point=True, interpolate="monotone").encode(
                x="Date:T",
                y="Precipitation:Q"
            ).properties(
                title="Precipitation (mm)",
                height=500
            )
            return viz_chart

        viz_chart = precipitation_chart(rdf)
        if viz_chart:
            col6.subheader("Daily Precipitation")
            col6.altair_chart(viz_chart, use_container_width=True)

    # Temperature Calculation
    def temperatureCollection(initialDate, endDate, _aoi):
        try:
            temp_collection = (
                ee.ImageCollection("ECMWF/ERA5_LAND/HOURLY")
                .filterDate(initialDate, endDate)
                .filterBounds(_aoi)
                .select("temperature_2m")
            )
            if temp_collection.size().getInfo() == 0:
                st.warning("No temperature data available for the specified date range.")
                return None
            return temp_collection
        except Exception as e:
            st.error(f"Error fetching temperature data: {str(e)}")
            return None

    def full_month_temperature(initialDate, endDate, _aoi):
        try:
            initial_date = datetime.strptime(initialDate, "%Y-%m-%d")
            end_date = datetime.strptime(endDate, "%Y-%m-%d")
            start_of_month = initial_date.replace(day=1)
            _, end_of_month_day = calendar.monthrange(end_date.year, end_date.month)
            end_of_month = end_date.replace(day=end_of_month_day)

            if initial_date.month == end_date.month and initial_date.year == end_date.year:
                start_of_month = initial_date.replace(day=1)
                end_of_month = end_date.replace(day=end_of_month_day)

            tempcol = temperatureCollection(start_of_month.strftime("%Y-%m-%d"), end_of_month.strftime("%Y-%m-%d"), _aoi)
            if tempcol is None:
                return pd.DataFrame({"Date": [], "Temperature": []})

            daily_temperature = tempcol.map(
                lambda img: ee.Feature(
                    _aoi,
                    {
                        "date": img.date().format("YYYY-MM-dd"),
                        "temperature": img.reduceRegion(
                            reducer=ee.Reducer.mean(),
                            geometry=_aoi,
                            scale=1000
                        ).get("temperature_2m"),
                    }
                )
            )
            daily_temp_list = daily_temperature.getInfo()["features"]
            dates_t = [entry["properties"]["date"] for entry in daily_temp_list]
            values_t = [entry["properties"]["temperature"] for entry in daily_temp_list]
            scaled_values = [round(value - 273.15, 2) if value is not None else None for value in values_t]
            temp_df = pd.DataFrame({"Date": dates_t, "Temperature": scaled_values})
            temp_df = temp_df.groupby("Date", as_index=False).mean()
            return temp_df
        except Exception as e:
            st.error(f"Error processing temperature data: {str(e)}")
            return pd.DataFrame({"Date": [], "Temperature": []})

    with st.container():
        col5, col6 = st.columns([1, 2])
        temp_df = full_month_temperature(str_pre_fire_start, str_post_fire_end, geometry_aoi)
        col5.subheader("Temperature Data Table:")
        col5.dataframe(
            temp_df,
            column_config={
                "Date": "Date",
                "Temperature": st.column_config.NumberColumn(
                    "Temperature (°C)", format="%.2f °C", min_value=-50, max_value=50, width="medium", help="Temperature in Celsius"
                ),
            },
            hide_index=True, width=400, height=420
        )

        def temperature_chart(temp_df):
            if temp_df.empty:
                st.warning("No temperature data to display.")
                return None
            temp_df["Date"] = pd.to_datetime(temp_df["Date"])
            viz_chart = alt.Chart(temp_df).mark_bar(color="#e65780").encode(
                x=alt.X("Date:T", axis=alt.Axis(title="Time (Days)", ticks=True, tickMinStep=1)),
                y=alt.Y("Temperature:Q", axis=alt.Axis(title=None, ticks=True, tickMinStep=1)),
                tooltip=["Date:T", "Temperature:Q"]
            ) + alt.Chart(temp_df).mark_line(color="#e63946", point=True, interpolate="monotone").encode(
                x="Date:T",
                y="Temperature:Q"
            ).properties(
                title="Daily Temperature (°C)",
                height=500
            )
            return viz_chart

        temp_viz_chart = temperature_chart(temp_df)
        if temp_viz_chart:
            col6.subheader("Daily Temperature")
            col6.altair_chart(temp_viz_chart, use_container_width=True)

    # Miscellaneous Information
    with st.container():
        st.divider()
        st.write("#### Interpreting the Results")
        st.write("This app provides an accessible tool for both technical and non-technical users to explore burn severity and land surface changes.")
        st.write("When exploring the dNBR map, consider:")
        st.write("- Clouds, atmospheric conditions, and water bodies can affect the map's appearance.")
        st.write("- Satellite sensors may have limitations in distinguishing surface types.")
        st.write("- NBR/dNBR values may vary with vegetation and land cover changes.")
        st.write("- The map provides visual insights rather than precise representations.")

        st.write("#### Usage the Environmental Index: NBR / dNBR")
        st.write("The [Normalized Burn Ratio (NBR)](https://www.earthdatascience.org/courses/earth-analytics/multispectral-remote-sensing-modis/normalized-burn-index-dNBR/) emphasizes charred areas after a fire.")
        st.latex(r'\text{NBR} = \frac{\text{NIR} - \text{SWIR}}{\text{NIR} + \text{SWIR}}')
        st.write("dNBR is calculated as:")
        st.latex(r'\text{dNBR} = \text{NBR}_{pre-fire} - \text{NBR}_{post-fire}')
        st.write("NBR values range from **[-1 to 1]**, with higher values indicating higher severity burns.")

        st.write("#### Data")
        st.write("This app uses **Sentinel-2 Level-2A** atmospherically corrected Surface Reflectance images from the [Sentinel-2 satellite constellation](https://sentivista.copernicus.eu/).")

        st.write("##### Credit:")
        st.caption(
            """The app was developed by [Dr. Anil Kumar Singh](https://www.linkedin.com/in/anil-kumar-singh-phd-b192554a/) using [Streamlit](https://streamlit.io/), [Google Earth Engine](https://github.com/google/earthengine-api) Python API, and [Folium](https://github.com/python-visualization/folium). """,
            unsafe_allow_html=True
        )

if __name__ == "__main__":
    main()
