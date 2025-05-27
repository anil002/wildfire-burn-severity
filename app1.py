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
from typing import Union, Dict
import os

# Streamlit page configuration
st.set_page_config(
    page_title="Wildfire Burn Severity Analysis",
    page_icon="https://cdn-icons-png.flaticon.com/512/7204/7204183.png",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get help': "https://github.com/IndigoWizard/wildfire-burn-severity",
        'Report a bug': "https://github.com/IndigoWizard/wildfire-burn-severity/issues",
        'About': "Developed by IndigoWizard for environmental monitoring."
    }
)

# CSS Styling
st.markdown(
    """
    <style>
        /* Header */
        .st-emotion-cache-h4xjwg, .st-emotion-cache-12fmjuu {
            height: 1rem;
            background: none;
        }
        .st-emotion-cache-ropwps.egexzqm2 h1#wildfire-burn-severity-analysis {
            font-size: 1.75rem;
        }
        /* Main body */
        .stMain.st-emotion-cache-bm2z3a.eht7o1d1 {
            scroll-behavior: smooth;
        }
        .st-emotion-cache-t1wise.eht7o1d4 {
            padding: 0.2rem 2rem;
        }
        /* Sidebar */
        .stSidebar.st-emotion-cache-1wqrzgl.e1c29vlm0, .stSidebar.st-emotion-cache-vmpjyt.e1c29vlm0 {
            min-width: 280px;
            max-width: fit-content;
            background-color: rgb(38, 39, 48);
            color: #fafafa;
        }
        .st-emotion-cache-kgpedg {
            padding: 0;
        }
        .st-emotion-cache-1kyxreq.e115fcil2 {
            justify-content: center;
        }
        /* Socials */
        .st-emotion-cache-1espb9k p, .st-emotion-cache-1mw54nq p {
            display: flex;
            flex-direction: row;
            justify-content: start;
            gap: 0.8rem;
            padding-inline: 10px;
        }
        /* Upload Section */
        .st-emotion-cache-1gulkj5.e1blfcsg0 {
            background-color: rgb(215, 210, 225);
            color: rgb(40, 40, 55);
            display: flex;
            flex-direction: column;
            font-size: 14px;
        }
        .st-emotion-cache-19rxjzo.ef3psqc7 {
            width: 100%;
        }
        /* Legend */
        .ndwilegend, .reclassifieddNBR {
            transition: 0.2s ease-in-out;
            border-radius: 5px;
            box-shadow: 0 0 5px rgba(0, 0, 0, 0.2);
            background: rgba(0, 0, 0, 0.05);
        }
        .ndwilegend:hover, .reclassifieddNBR:hover {
            box-shadow: 0 0 5px rgba(0, 0, 0, 0.8);
            background: rgba(0, 0, 0, 0.12);
            cursor: pointer;
        }
    </style>
    """, unsafe_allow_html=True)

# Google Earth Engine Authentication
@st.cache_data(persist=True)
def ee_authenticate():
    """
    Authenticate with Google Earth Engine using a service account from Streamlit secrets
    or local CLI credentials.
    """
    try:
        try:
            if "json_key" in st.secrets:
                st.info("Authenticating with Google Earth Engine using service account...")
                json_creds = st.secrets["json_key"]
                # Handle AttrDict, dict, or JSON string
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
                return
        except FileNotFoundError:
            st.warning("No secrets.toml found. Attempting local CLI authentication...")

        # Fallback to CLI authentication
        st.info("Attempting authentication using Earth Engine CLI credentials...")
        ee.Initialize()
        st.success("Authenticated with Google Earth Engine using local CLI credentials.")
    except Exception as e:
        st.error(f"Failed to authenticate with Google Earth Engine: {str(e)}")
        st.markdown(
            "**Steps to resolve:**\n"
            "- **Local setup**: Create `.streamlit/secrets.toml` in your project directory (`D:\\wild_fire`) with the service account key, or run `earthengine authenticate` in your terminal.\n"
            "  Example `secrets.toml`:\n"
            "  ```toml\n"
            "  [json_key]\n"
            "  type = 'service_account'\n"
            "  project_id = 'ee-singhanil854'\n"
            "  private_key_id = 'de18479cbbd711eb8e54c3fb5468a3780ffdaf3b'\n"
            "  private_key = '''-----BEGIN PRIVATE KEY-----\\n...\\n-----END PRIVATE KEY-----'''\n"
            "  client_email = 'wildfire@ee-singhanil854.iam.gserviceaccount.com'\n"
            "  client_id = '113223099960707341487'\n"
            "  auth_uri = 'https://accounts.google.com/o/oauth2/auth'\n"
            "  token_uri = 'https://oauth2.googleapis.com/token'\n"
            "  auth_provider_x509_cert_url = 'https://www.googleapis.com/oauth2/v1/certs'\n"
            "  client_x509_cert_url = 'https://www.googleapis.com/robot/v1/metadata/x509/wildfire%40ee-singhanil854.iam.gserviceaccount.com'\n"
            "  universe_domain = 'googleapis.com'\n"
            "  ```\n"
            "- **Cloud deployment**: Ensure `[json_key]` is configured in Streamlit Cloud secrets.\n"
            "- Verify the service account has Earth Engine API permissions (`roles/earthengine.user`).\n"
            "- Check your internet connection and Google Cloud project settings."
        )
        raise

# Add Earth Engine layer to Folium map
def add_ee_layer(self, ee_image_object: ee.Image, vis_params: Dict, name: str):
    """Add a Google Earth Engine image layer to a Folium map."""
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

folium.Map.add_ee_layer = add_ee_layer

# Create and filter Sentinel-2 image collection
def satCollection(cloudRate: int, initialDate: str, updatedDate: str, aoi: ee.Geometry) -> ee.ImageCollection:
    """Create a filtered Sentinel-2 image collection for the given AOI and date range."""
    collection = ee.ImageCollection('COPERNICUS/S2_SR') \
        .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", cloudRate)) \
        .filterDate(initialDate, updatedDate) \
        .filterBounds(aoi)
    
    def clipCollection(image: ee.Image) -> ee.Image:
        return image.clip(aoi).divide(10000)
    
    return collection.map(clipCollection)

# Process uploaded GeoJSON files
last_uploaded_centroid = None
def upload_files_proc(upload_files: list) -> ee.Geometry:
    """Process uploaded GeoJSON files to create an AOI geometry."""
    global last_uploaded_centroid
    geometry_aoi_list = []
    
    if not upload_files:
        return ee.Geometry.Point([16.25, 36.65])
    
    for upload_file in upload_files:
        try:
            bytes_data = upload_file.read()
            geojson_data = json.loads(bytes_data)
            features = geojson_data.get('features', []) or [
                {'geometry': geo} for geo in geojson_data.get('geometries', [])
            ]
            for feature in features:
                if 'geometry' in feature and 'coordinates' in feature['geometry']:
                    coordinates = feature['geometry']['coordinates']
                    geometry = (
                        ee.Geometry.Polygon(coordinates)
                        if feature['geometry']['type'] == 'Polygon'
                        else ee.Geometry.MultiPolygon(coordinates)
                    )
                    geometry_aoi_list.append(geometry)
                    last_uploaded_centroid = geometry.centroid(maxError=1).getInfo()['coordinates']
        except Exception as e:
            st.warning(f"Error processing GeoJSON file '{upload_file.name}': {str(e)}")
    
    return ee.Geometry.MultiPolygon(geometry_aoi_list) if geometry_aoi_list else ee.Geometry.Point([16.25, 36.65])

# Process date inputs
def date_input_proc(input_date: datetime, time_range: int) -> tuple:
    """Convert date input to start and end date strings."""
    end_date = input_date
    start_date = input_date - timedelta(days=time_range)
    return start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')

# Calculate area for dNBR classes
def calculate_class_area(classified_image: ee.Image, geometry_aoi: ee.Geometry, class_value: int) -> float:
    """Calculate the area of a dNBR class in square kilometers."""
    class_pixel_area = classified_image.eq(class_value).multiply(ee.Image.pixelArea())
    class_area = class_pixel_area.reduceRegion(
        reducer=ee.Reducer.sum(),
        geometry=geometry_aoi,
        scale=10,
        maxPixels=1e12
    )
    area_value = class_area.getInfo()
    return area_value.get(list(area_value.keys())[0], 0)

# Calculate GeoJSON area
def geojson_area(aoi: ee.Geometry) -> float:
    """Calculate the area of the AOI in square kilometers."""
    aoi_area_sqm = aoi.area()
    return round(aoi_area_sqm.getInfo() / 1e6, 4)

# Main Streamlit app
def main():
    """Main function to run the Wildfire Burn Severity Analysis app."""
    ee_authenticate()

    # Sidebar
    with st.sidebar:
        st.logo("https://cdn-icons-png.flaticon.com/512/7204/7204183.png")
        st.image("https://cdn-icons-png.flaticon.com/512/7204/7204183.png", width=90)
        st.markdown("#### Wildfire Burn Severity Analysis")
        st.subheader("Navigation:")
        st.markdown(
            """
            - [Wildfire Map](#wildfire-burn-severity-analysis)
            - [Map Legend](#map-legend)
            - [Analysis Report](#analysis-report)
            - [Interpreting Results](#interpreting-the-results)
            - [Environmental Index](#usage-the-environmental-index-nbr-dnbr)
            - [Data](#data)
            - [Credit](#credit)
            """
        )
        st.subheader("Contact:")
        st.markdown(
            """
            [![LinkedIn](https://content.linkedin.com/content/dam/me/brand/en-us/brand-home/logos/In-Blue-Logo.png.original.png)](https://linkedin.com/in/ahmed-islem-mokhtari)
            [![GitHub](https://github.githubassets.com/favicons/favicon-dark.png)](https://github.com/IndigoWizard)
            """
        )
        st.caption("Star ⭐ the [project on GitHub](https://github.com/IndigoWizard/wildfire-burn-severity/)!")

    # Main content
    st.title("Wildfire Burn Severity Analysis")
    st.markdown("**Evaluate wildfire burn severity using Sentinel-2 imagery and NBR/dNBR indices.**")

    # User input form
    with st.form("input_form"):
        c1, c2 = st.columns([3, 1])
        with c2:
            st.info("Cloud Coverage 🌥️")
            cloud_pixel_percentage = st.slider(
                "Cloud pixel rate", min_value=5, max_value=100, step=5, value=75
            )
            st.info("Upload Area of Interest (GeoJSON):")
            upload_files = st.file_uploader(
                "Create a GeoJSON at [geojson.io](https://geojson.io/)",
                accept_multiple_files=True
            )
            geometry_aoi = upload_files_proc(upload_files)
            st.info("Color Palette")
            accessibility = st.selectbox(
                "Accessibility",
                ["Normal", "Deuteranopia", "Protanopia", "Tritanopia", "Achromatopsia"]
            )

        with c1:
            col1, col2 = st.columns(2)
            col1.warning("Pre-Fire NBR Date 📅")
            initial_date = col1.date_input("Initial date", datetime(2023, 7, 12))
            col2.success("Post-Fire NBR Date 📅")
            updated_date = col2.date_input("Updated date", datetime(2023, 7, 27))
            time_range = 7
            str_initial_start_date, str_initial_end_date = date_input_proc(initial_date, time_range)
            str_updated_start_date, str_updated_end_date = date_input_proc(updated_date, time_range)

        # Initialize Folium map
        global last_uploaded_centroid
        latitude, longitude = (
            (last_uploaded_centroid[1], last_uploaded_centroid[0])
            if last_uploaded_centroid
            else (36.60, 16.00)
        )
        m = folium.Map(
            location=[latitude, longitude],
            tiles=None,
            zoom_start=11 if last_uploaded_centroid else 5,
            control_scale=True
        )

        # Add basemaps
        folium.TileLayer('OpenStreetMap', name="Open Street Map", attr="OSM").add_to(m)
        folium.TileLayer('cartodbdark_matter', name='Dark Basemap', attr='CartoDB').add_to(m)

        # Process satellite imagery
        try:
            pre_fire_collection = satCollection(
                cloud_pixel_percentage, str_initial_start_date, str_initial_end_date, geometry_aoi
            )
            post_fire_collection = satCollection(
                cloud_pixel_percentage, str_updated_start_date, str_updated_end_date, geometry_aoi
            )
            pre_fire = pre_fire_collection.median()
            post_fire = post_fire_collection.median()

            # Calculate NDWI and NBR
            def get_NDWI(image: ee.Image) -> ee.Image:
                return image.normalizedDifference(['B3', 'B11'])

            def get_NBR(image: ee.Image) -> ee.Image:
                return image.normalizedDifference(['B8', 'B12'])

            pre_fire_ndwi = get_NDWI(pre_fire)
            pre_fire_NBR = get_NBR(pre_fire)
            post_fire_NBR = get_NBR(post_fire)
            dNBR = pre_fire_NBR.subtract(post_fire_NBR)

            # Define color palettes
            default_dnbr_palette = ["#ffffe5", "#f7fcb9", "#78c679", "#41ab5d", "#238443", "#005a32"]
            default_dNBR_classified_palette = [
                '#1c742c', '#2aae29', '#a1d574', '#f8ebb0', '#f7a769', '#e86c4e', '#902cd6'
            ]
            default_ndwi_palette = ["#caf0f8", "#00b4d8", "#023e8a"]
            ndwi_palette = default_ndwi_palette.copy()
            dnbr_palette = default_dnbr_palette.copy()
            dNBR_classified_palette = default_dNBR_classified_palette.copy()

            if accessibility == "Deuteranopia":
                dnbr_palette = ["#fffaa1", "#f4ef8e", "#9a5d67", "#573f73", "#372851", "#191135"]
                dNBR_classified_palette = [
                    "#95a600", "#92ed3e", "#affac5", "#78ffb0", "#69d6c6", "#22459c", "#000e69"
                ]
            elif accessibility == "Protanopia":
                dnbr_palette = ["#a6f697", "#7def75", "#2dcebb", "#1597ab", "#0c677e", "#002c47"]
                dNBR_classified_palette = [
                    "#95a600", "#92ed3e", "#affac5", "#78ffb0", "#69d6c6", "#22459c", "#000e69"
                ]
            elif accessibility == "Tritanopia":
                dnbr_palette = ["#cdffd7", "#a1fbb6", "#6cb5c6", "#3a77a5", "#205080", "#001752"]
                dNBR_classified_palette = [
                    "#ed4700", "#ed8a00", "#e1fabe", "#99ff94", "#87bede", "#2e40cf", "#0600bc"
                ]
            elif accessibility == "Achromatopsia":
                dnbr_palette = ["#407de0", "#2763da", "#394388", "#272c66", "#16194f", "#010034"]
                dNBR_classified_palette = [
                    "#004f3d", "#338796", "#66a4f5", "#3683ff", "#3d50ca", "#421c7f", "#290058"
                ]

            # Visualization parameters
            satImg_params = {'bands': ['B12', 'B11', 'B4'], 'min': 0, 'max': 1, 'gamma': 1.1}
            ndwi_params = {'min': -1, 'max': 0, 'palette': ndwi_palette}
            dNBR_params = {'min': -0.5, 'max': 1.3, 'palette': dnbr_palette}
            dNBR_classified_params = {'min': 1, 'max': 7, 'palette': dNBR_classified_palette}

            # Classify dNBR
            dNBR_classified = ee.Image(dNBR) \
                .where(dNBR.gte(-0.5).And(dNBR.lt(-0.251)), 1) \
                .where(dNBR.gte(-0.250).And(dNBR.lt(-0.101)), 2) \
                .where(dNBR.gte(-0.100).And(dNBR.lt(0.099)), 3) \
                .where(dNBR.gte(0.100).And(dNBR.lt(0.269)), 4) \
                .where(dNBR.gte(0.270).And(dNBR.lt(0.439)), 5) \
                .where(dNBR.gte(0.440).And(dNBR.lt(0.659)), 6) \
                .where(dNBR.gte(0.660).And(dNBR.lte(1.300)), 7)

            # Apply masks
            masked_pre_fire_ndwi = pre_fire_ndwi.updateMask(pre_fire_ndwi.gt(-0.12))
            binaryMask = pre_fire_ndwi.lt(-0.1)
            waterMask = binaryMask.selfMask()
            masked_dNBR_classified = dNBR_classified.updateMask(waterMask)

            # Generate burn scar
            dNBR_classified_burn = dNBR_classified.gte(4).updateMask(dNBR_classified.neq(0))
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

            # Add layers to map
            if initial_date == updated_date:
                m.add_ee_layer(post_fire, satImg_params, 'Satellite Imagery')
            else:
                m.add_ee_layer(pre_fire, satImg_params, f'Pre-Fire Imagery: {initial_date}')
                m.add_ee_layer(post_fire, satImg_params, f'Post-Fire Imagery: {updated_date}')
                m.add_ee_layer(masked_pre_fire_ndwi, ndwi_params, f'NDWI: {initial_date}')
                m.add_ee_layer(masked_dNBR_classified, dNBR_classified_params, 'Reclassified dNBR')
                m.add_ee_layer(burn_scar, {'palette': '#87043b'}, 'Burn Scar')

            folium.LayerControl(collapsed=True).add_to(m)
        except Exception as e:
            st.error(f"Error processing satellite imagery: {str(e)}")
            st.markdown(
                "- Ensure the date range and AOI are valid.\n"
                "- Check GEE authentication and API access."
            )
        except Exception as e:
            st.error(f"Error processing satellite imagery: {str(e)}")
            st.markdown(
                "- Ensure the date range and AOI are valid.\n"
                "- Check GEE authentication and API access."
            )

        # Form submission
        submitted = c2.form_submit_button("Generate Map")
        if submitted:
            with c1:
                folium_static(m)
        else:
            with c1:
                folium_static(m)

    # Map Legend
    st.subheader("Map Legend:")
    col3, col4, _ = st.columns([1, 2, 1])
    with col3:
        ndwi_legend_html = f"""
            <div class="ndwilegend">
                <h5>NDWI</h5>
                <div style="display: flex; flex-direction: row; align-items: flex-start; gap: 1rem;">
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
                    <li style="margin: 0.2em 0px;">
                        <span style="background-color: {dNBR_classified_palette[0]}; opacity: 0.75; display: inline-block; width: 15px; height: 15px; border-radius: 50%; margin-right: 5px;"></span>
                        Enhanced Regrowth (High)
                    </li>
                    <li style="margin: 0.2em 0px;">
                        <span style="background-color: {dNBR_classified_palette[1]}; opacity: 0.75; display: inline-block; width: 15px; height: 15px; border-radius: 50%; margin-right: 5px;"></span>
                        Enhanced Regrowth (Low)
                    </li>
                    <li style="margin: 0.2em 0px;">
                        <span style="background-color: {dNBR_classified_palette[2]}; opacity: 0.75; display: inline-block; width: 15px; height: 15px; border-radius: 50%; margin-right: 5px;"></span>
                        Unburned
                    </li>
                    <li style="margin: 0.2em 0px;">
                        <span style="background-color: {dNBR_classified_palette[3]}; opacity: 0.75; display: inline-block; width: 15px; height: 15px; border-radius: 50%; margin-right: 5px;"></span>
                        Low Severity Burns
                    </li>
                    <li style="margin: 0.2em 0px;">
                        <span style="background-color: {dNBR_classified_palette[4]}; opacity: 0.75; display: inline-block; width: 15px; height: 15px; border-radius: 50%; margin-right: 5px;"></span>
                        Moderate-Low Severity Burns
                    </li>
                    <li style="margin: 0.2em 0px;">
                        <span style="background-color: {dNBR_classified_palette[5]}; opacity: 0.75; display: inline-block; width: 15px; height: 15px; border-radius: 50%; margin-right: 5px;"></span>
                        Moderate-High Severity Burns
                    </li>
                    <li style="margin: 0.2em 0px;">
                        <span style="background-color: {dNBR_classified_palette[6]}; opacity: 0.75; display: inline-block; width: 15px; height: 15px; border-radius: 50%; margin-right: 5px;"></span>
                        High Severity Burns
                    </li>
                </ul>
            </div>
        """
        st.markdown(reclassified_dNBR_legend_html, unsafe_allow_html=True)

    # Analysis Report
    st.subheader("Analysis Report")
    with st.form("report_form"):
        try:
            geometry_area = geojson_area(geometry_aoi)
            dNBR_class_areas = [
                calculate_class_area(masked_dNBR_classified, geometry_aoi, i) / 1e6
                for i in range(1, 8)
            ]
            class_names = [
                "Enhanced Regrowth (High)", "Enhanced Regrowth (Low)", "Unburned",
                "Low Severity Burns", "Moderate-Low Severity Burns",
                "Moderate-High Severity Burns", "High Severity Burns"
            ]
        except NameError:
            dNBR_class_areas = [0] * 7
            class_names = [
                "Enhanced Regrowth (High)", "Enhanced Regrowth (Low)", "Unburned",
                "Low Severity Burns", "Moderate-Low Severity Burns",
                "Moderate-High Severity Burns", "High Severity Burns"
            ]
            geometry_area = 0

        report_form = st.form_submit_button("Generate Report", type="primary")
        if report_form:
            st.write("#### Wildfire Burn Severity Analysis Report:")
            col1, col2 = st.columns([1, 1])
            col1.success(f"**ROI Location:** [{round(latitude, 4)}, {round(longitude, 4)}]")
            col1.success(f"**Surface Area of ROI:** ~{geometry_area} Km²")
            col2.success(
                f"**Pre-Fire Date Range:** {str_initial_start_date} to {str_initial_end_date}"
            )
            col2.success(
                f"**Post-Fire Date Range:** {str_updated_start_date} to {str_updated_end_date}"
            )

            col3, col4 = st.columns([1.5, 2])
            for i, area in enumerate(dNBR_class_areas, start=1):
                col3.info(f"**{class_names[i-1]}:** ~{round(area, 4)} Km²")

            with col4:
                DATA_PIE = [
                    {
                        "id": class_names[i-1],
                        "label": class_names[i-1],
                        "value": round(area, 4),
                        "color": dNBR_classified_palette[i-1]
                    }
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
                            colors={"datum": "data.color"},
                            arcLinkLabel="value",
                            arcLinkLabelsThickness=2,
                            arcLabelsSkipAngle=10,
                            arcLinkLabelsDiagonalLength=10,
                            arcLinkLabelsStraightLength=10,
                            arcLinkLabelsTextOffset=4,
                            arcLabelsTextColor={"from": "color", "modifiers": [["darker", 4]]},
                            defs=[
                                {
                                    "id": name,
                                    "type": "patternDots" if i > 2 else "patternLines",
                                    "color": f"{dNBR_classified_palette[i-1]}",
                                    "background": f"{dNBR_classified_palette[i-1]}bf",
                                    "rotation": 105 if i < 2 else -15 if i == 2 else 0,
                                    "lineWidth": 3 if i == 1 else 2 if i == 2 else 0,
                                    "spacing": 10 if i <= 2 else 4,
                                    "size": 4 if i > 2 else None,
                                    "padding": 1 if i > 2 else None,
                                    "stagger": True if i > 2 else None
                                }
                                for i, name in enumerate(class_names)
                            ],
                            fill=[{"match": {"id": name}, "id": name} for name in class_names],
                            theme={
                                "tooltip": {
                                    "container": {
                                        "background": "white",
                                        "fontSize": 14,
                                        "padding": 2,
                                        "border-radius": 4
                                    },
                                    "basic": {
                                        "background": "#0e1117",
                                        "color": "white",
                                        "padding": 5
                                    }
                                }
                            }
                        )

        # Precipitation Data
        def chirpsCollection(initialDate: str, updatedDate: str, aoi: ee.Geometry) -> ee.ImageCollection:
            """Fetch CHIRPS precipitation data."""
            return ee.ImageCollection("UCSB-CHG/CHIRPS/DAILY") \
                .filterDate(initialDate, updatedDate) \
                .filterBounds(aoi) \
                .select("precipitation")

        def full_month_precipitation(initialDate: str, endDate: str, aoi: ee.Geometry) -> pd.DataFrame:
            """Calculate monthly precipitation data."""
            initial_date = pd.to_datetime(initialDate)
            end_date = pd.to_datetime(endDate)
            start_of_month = initial_date.replace(day=1)
            _, end_of_month_day = calendar.monthrange(end_date.year, end_date.month)
            end_of_month = end_date.replace(day=end_of_month_day)
            raincol = chirpsCollection(
                start_of_month.strftime("%Y-%m-%d"), end_of_month.strftime("%Y-%m-%d"), aoi
            )
            precip = raincol.map(
                lambda img: ee.Feature(None, {
                    'date': img.date().format('YYYY-MM-dd'),
                    'precipitation': img.reduceRegion(
                        reducer=ee.Reducer.mean(),
                        geometry=aoi,
                        scale=1000,
                        maxPixels=1e9
                    ).get('precipitation')
                })
            )
            feature_list = precip.getInfo()['features']
            df = pd.DataFrame([
                {
                    'Date': f['properties']['date'],
                    'Precipitation': f['properties']['precipitation']
                } for f in feature_list
            ])
            df['Date'] = pd.to_datetime(df['Date'])
            df['Precipitation'] = pd.to_numeric(df['Precipitation'], errors='coerce')
            return df

        col5, col6 = st.columns([1, 2])
        try:
            rdf = full_month_precipitation(str_initial_start_date, str_updated_end_date, geometry_aoi)
            col5.subheader("Precipitation Data:")
            col5.dataframe(
                rdf,
                column_config={
                    "Date": "Date",
                    "Precipitation": st.column_config.ProgressColumn(
                        "Rainfall (mm)", format="%f mm", min_value=0, max_value=100
                    )
                },
                hide_index=True,
                width=400,
                height=420
            )

            def precipitation_chart(rdf: pd.DataFrame) -> alt.Chart:
                """Create a precipitation chart."""
                rdf = rdf.copy()
                rdf["Date"] = pd.to_datetime(rdf["Date"])
                return alt.Chart(rdf).mark_bar(color="#88c0d0").encode(
                    x=alt.X("Date:T", axis=alt.Axis(title="Time (Days)")),
                    y=alt.Y("Precipitation:Q", axis=alt.Axis(title=None)),
                    tooltip=["Date:T", "Precipitation:Q"]
                ) + alt.Chart(rdf).mark_line(color="#004dc6", point=True).encode(
                    x="Date:T", y="Precipitation:Q"
                ).properties(title="Precipitation (mm)", height=500)

            col6.subheader("Daily Precipitation")
            col6.altair_chart(precipitation_chart(rdf), use_container_width=True)
        except Exception as e:
            col5.error(f"Error fetching precipitation data: {str(e)}")

        # Temperature Data
        def temperatureCollection(initialDate: str, updatedDate: str, aoi: ee.Geometry) -> ee.ImageCollection:
            """Fetch ERA5-Land temperature data."""
            return ee.ImageCollection("ECMWF/ERA5_LAND/HOURLY") \
                .filterDate(initialDate, updatedDate) \
                .filterBounds(aoi) \
                .select("temperature_2m")

        def full_month_temperature(initialDate: str, endDate: str, aoi: ee.Geometry) -> pd.DataFrame:
            """Calculate daily temperature data."""
            initial_date = pd.to_datetime(initialDate)
            end_date = pd.to_datetime(endDate)
            start_of_month = initial_date.replace(day=1)
            _, end_of_month_day = calendar.monthrange(end_date.year, end_date.month)
            end_of_month = end_date.replace(day=end_of_month_day)
            tempcol = temperatureCollection(
                start_of_month.strftime("%Y-%m-%d"), end_of_month.strftime("%Y-%m-%d"), aoi
            )
            temp = tempcol.map(
                lambda img: ee.Feature(None, {
                    'date': img.date().format('YYYY-MM-dd'),
                    'temperature': img.reduceRegion(
                        reducer=ee.Reducer.mean(),
                        geometry=aoi,
                        scale=1000,
                        maxPixels=1e9
                    ).get('temperature_2m')
                })
            )
            feature_list = temp.getInfo()['features']
            df = pd.DataFrame([
                {
                    'Date': f['properties']['date'],
                    'Temperature': f['properties']['temperature']
                } for f in feature_list
            ])
            df['Date'] = pd.to_datetime(df['Date'])
            df['Temperature'] = pd.to_numeric(df['Temperature'], errors='coerce') - 273.15
            return df

        col5, col6 = st.columns([1, 2])
        try:
            temp_df = full_month_temperature(str_initial_start_date, str_updated_end_date, geometry_aoi)
            col5.subheader("Temperature Data:")
            col5.dataframe(
                temp_df,
                column_config={
                    "Date": st.column_config.TextColumn("Date"),
                    "Temperature": st.column_config.NumberColumn(
                        "Temperature (°C)",
                        format="%f °C",
                        min_value=-50,
                        max_value=50
                    )
                },
                hide_index=True,
                width=400,
                height=420
            )

            def temperature_chart(temp_df: pd.DataFrame) -> alt.Chart:
                """Create a temperature chart."""
                temp_df = temp_df.copy()
                temp_df["Date"] = pd.to_datetime(temp_df["Date"])
                return alt.Chart(temp_df).mark_bar(color="#e65732").encode(
                    x=alt.X("Date:T", axis=alt.Axis(title="Time (Days)")),
                    y=alt.Y("Temperature:Q", axis=alt.Axis(title=None)),
                    tooltip=["Date:T", "Temperature:Q"]
                ) + alt.Chart(temp_df).mark_line(color="#004dc6", point=True).encode(
                    x="Date:T", y="Temperature:Q"
                ).properties(title="Temperature (°C)", height=500)

            col6.subheader("Daily Temperature")
            col6.altair_chart(temperature_chart(temp_df), use_container_width=True)
        except Exception as e:
            col5.error(f"Error fetching temperature data: {str(e)}")

    # Additional Information
    st.divider()
    st.subheader("Interpreting Results")
    st.markdown("""
    This app analyzes wildfire burn severity using NBR/dNBR indices. Considerations:
    - Clouds and water bodies may affect accuracy.
    - Satellite sensors have limitations in distinguishing terrain types.
    - NBR/dNBR values vary with vegetation and land cover.
    """)

    st.subheader("Environmental Index: NBR/dNBR")
    st.markdown("The [Normalized Burn Ratio (NBR)](https://www.earthdatascience.org/courses/earth-analytics/multispectral-remote-sensing-modis/normalized-burn-index-dNBR/) uses NIR and swIR:")
    st.latex(r'\text{NBR} = \frac{\text{NIR} - \text{SWIR}}{\text{NIR} + \text{SWIR}}')
    st.latex(r'\text{dNBR} = \text{NBR}_{pre-fire} - \text{NBR}_{post-fire}')

    st.subheader("Data")
    st.markdown("Uses **Sentinel-2 Level-2A** imagery for accurate reflectance.")

    st.subheader("Credits")
    st.markdown("Developed by [IndigoWizard](https://github.com/IndigoWizard). Icons by [Flaticon](https://www.flaticon.com/free-icons/wildfire-burned).")

if __name__ == "__main__":
    main()
