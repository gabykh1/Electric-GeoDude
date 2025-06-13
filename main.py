import streamlit as st
import sqlite3
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
import folium
from folium.plugins import MarkerCluster
# from streamlit_folium import folium_static
from streamlit_folium import st_folium
import os
import sys

# DB_PATH = 'geodude.db' -- test

if getattr(sys, 'frozen', False):
    BASE_DIR = sys._MEIPASS  # for .exe
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # for .py

DATA_DIR = os.path.join(BASE_DIR, 'data')
DB_PATH = os.path.join(DATA_DIR, 'geodude.db')
MAIN_IMAGE = os.path.join(DATA_DIR, 'Electric GeoDude_HD_2.png')
LOGO_IMAGE = os.path.join(DATA_DIR, 'Electric GeoDude Logo_on black.png')

@st.cache_data
def load_data(query, params=()):
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df


def query_by_id(id_input):
    query = "SELECT * FROM elector WHERE id = ?"
    return load_data(query, (id_input,))


def query_by_person(first_name=None, last_name=None, city=None):
    query = "SELECT * FROM elector WHERE 1=1"
    params = []
    if first_name:
        query += " AND first_name = ?"
        params.append(first_name)
    if last_name:
        query += " AND last_name = ?"
        params.append(last_name)
    if city:
        query += " AND city LIKE ?"
        params.append(f"%{city.strip()}%")
    query += " LIMIT 100"
    return load_data(query, tuple(params))


def query_by_adress(street_name=None, city=None):
    query = "SELECT * FROM elector WHERE 1=1"
    params = []
    if street_name:
        query += " AND street_name LIKE ?"
        params.append(f"%{street_name.strip()}%")
    if city:
        query += " AND city LIKE ?"
        params.append(f"%{city.strip()}%")
    query += " LIMIT 100"
    return load_data(query, tuple(params))


def parse_coordinates(coord_text):
    try:
        lat, lon = map(float, coord_text.replace(',', ' ').split())
        return lat, lon
    except ValueError:
        raise ValueError("Invalid coordinate format! Use 'lat lon' or 'lat, lon'.")


def query_by_coordinates(coord_text, buffer_distance=30):
    lat, lon = parse_coordinates(coord_text)
    point = Point(lon, lat)
    gdf = gpd.GeoDataFrame(geometry=[point], crs="EPSG:4326").to_crs("EPSG:3857")
    buffer_gdf = gpd.GeoDataFrame(geometry=gdf.geometry.buffer(buffer_distance), crs="EPSG:3857").to_crs("EPSG:4326")
    min_x, min_y, max_x, max_y = buffer_gdf.total_bounds
    query = "SELECT * FROM elector WHERE lat BETWEEN ? AND ? AND lon BETWEEN ? AND ?"
    bounding_box_results = load_data(query, (min_y, max_y, min_x, max_x))
    if not bounding_box_results.empty:
        points_gdf = gpd.GeoDataFrame(
            bounding_box_results,
            geometry=gpd.points_from_xy(bounding_box_results.lon, bounding_box_results.lat),
            crs="EPSG:4326"
        )
        points_within_polygon = points_gdf[points_gdf.geometry.within(buffer_gdf.geometry.iloc[0])]
        points_within_polygon = points_within_polygon.head(1000)
    else:
        points_within_polygon = pd.DataFrame()
    return buffer_gdf, bounding_box_results, points_within_polygon

st.set_page_config(layout="centered", page_title="GeoDude", page_icon="🗺️")

st.markdown("""
    <style>
    /* Hide the hamburger menu (top-right) */
    #MainMenu {
        visibility: hidden;
    }

    /* Hide Streamlit footer */
    footer {
        visibility: hidden;
    }

    /* Optional: Hide "Made with Streamlit" header on public apps */
    header {
        visibility: hidden;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown("""
    <style>
    body {
        background-color: #111;  /* Dark background */
    }

    /* Make the form background fully yellow */
    .yellow-form {
        background-color: #D7AA57;  
        padding: 20px;
        border-radius: 15px;
        box-shadow: 0px 4px 10px rgba(255, 204, 0, 0.4);
        width: 90%;
        max-width: 700px;
        margin: auto;
    }

    /* Style for the form submit button */
    div[data-testid="stForm"] button {
        background-color: #D7AA57 !important;
        color: black !important;
        font-weight: bold !important;
        padding: 10px 20px !important;
        border: none !important;
        font-size: 16px !important;
        border-radius: 10px !important;
        text-align: center !important;
        display: block !important;
        margin: auto !important;
        transition: 0.3s;
    }
    div[data-testid="stForm"] button:hover {
        background-color: #D7AA57 !important;
    }
    </style>
""", unsafe_allow_html=True)

# Logo and title
# st.image("geodude.jpg", width=100)
st.image(MAIN_IMAGE)
st.markdown("<h1 style='text-align: center; color: white;'> Electric <span style='color:#D7AA57;'>GeoDude</span></h1>",
            unsafe_allow_html=True)
st.markdown(
    "<h3 style='text-align: center; color: white;'> Rock-Solid Accuracy, <span style='color:#D7AA57;'>Lightning-Fast Results!</span> </h3>",
    unsafe_allow_html=True)

# Sidebar
st.sidebar.image(LOGO_IMAGE)

# Main page
option = st.selectbox('Choose option', ['location', 'id', 'name'])

if option == 'location':
    choice = st.radio("Select input type:", ["Coordinates", "Address"], horizontal=True)

result_df = None
# starting main form
with st.form("query_form"):
    if option == 'location':
        st.markdown("<h2 style='text-align: center;'>location + radius</h2>", unsafe_allow_html=True)
        if choice == 'Coordinates':
            Coordination_input = st.text_input("Enter location (latitude, longitude):",
                                               placeholder="E.g.: 31.12345, 34.12345")
            radius = st.slider('What is the radius?', 1, 100, 15)
        else:  # address
            col1, col2 = st.columns(2)
            address_city_input = col1.text_input("Enter city:", placeholder="E.g.: הרצליה")
            address_street_input = col2.text_input("Enter street:", placeholder="E.g.: אריה שנקר 3")

    elif option == 'name':
        st.markdown("<h2 style='text-align: center;'>Provide at least one input</h2>", unsafe_allow_html=True)

        col1, col2, col3 = st.columns(3)
        first_name = col1.text_input('Name please', placeholder="E.g: אסף")
        last_name = col2.text_input('What about the last name', placeholder="E.g: לוץ")
        city = col3.text_input('You can also provide the city', placeholder="E.g: הרצליה")

    else:  # id
        st.markdown("<h2 style='text-align: center;'>ID</h2>", unsafe_allow_html=True)
        id_input = st.number_input('provide id', step=1, format="%d", placeholder=329999999, value=None)



    submit = st.form_submit_button("2,3 SHAGER!")

    if submit:
        st.success("Query submitted successfully! 🎉")

        result_df = None
        zoom_location = [32.1602, 34.8097]  # Default location

        # Run the appropriate query based on user input
        if option == "id":
            if not id_input:
                st.error("⚠ Please enter an ID before submitting!")
            else:
                result_df = query_by_id(id_input)

        elif option == "name":
            if not first_name and not last_name:
                st.error("⚠ Please provide at least a first or last name!")
            else:
                result_df = query_by_person(first_name, last_name, city)
                result_df = query_by_person(first_name, last_name, city)

        elif option == "location":
            if choice == "Coordinates":
                if not Coordination_input:
                    st.error("⚠ Please enter valid coordinates!")
                else:
                    buffer_gdf, bounding_box_results, points_within_polygon = query_by_coordinates(Coordination_input,
                                                                                                   radius)
                    result_df = points_within_polygon
                    zoom_location = parse_coordinates(Coordination_input)  # Set zoom to input location
            else:
                if not address_city_input and not address_street_input:
                    st.error("⚠ Please provide at least a city or street name!")
                else:
                    result_df = query_by_adress(address_street_input, address_city_input)

        # Handle case where no data is found
        if result_df is None or result_df.empty:
            st.warning("⚠ No data found! Try different inputs.")
        else:
            # Set zoom location to the first result if available
            if option != "location" or choice != "Coordinates":
                zoom_location = [result_df.iloc[0]["lat"], result_df.iloc[0]["lon"]]

            # Create a single map centered at the queried location
            m = folium.Map(location=zoom_location, zoom_start=16)

            # Add buffer polygon if applicable
            if option == "location" and choice == "Coordinates":
                folium.GeoJson(
                    buffer_gdf,
                    style_function=lambda x: {
                        "fillColor": "yellow",
                        "color": "black",
                        "weight": 2,
                        "fillOpacity": 0.3,
                    },
                    name="Search Radius"
                ).add_to(m)

            # Use a dictionary to group points with the same lat/lon
            grouped_points = {}
            for _, row in result_df.iterrows():
                lat_lon = (row["lat"], row["lon"])
                if lat_lon not in grouped_points:
                    grouped_points[lat_lon] = []
                grouped_points[lat_lon].append(row)

            # Add a MarkerCluster for overlapping points
            marker_cluster = MarkerCluster().add_to(m)

            # Loop through grouped points and create popups
            for (lat, lon), rows in grouped_points.items():
                display_rows = rows[:15]
                if len(rows) > 1:
                    popup_content = f"<b>Multiple Entries at this Location:</b> (showing {len(display_rows)} of {len(rows)})<br><table border='1' style='width:100%;'>"
                    popup_content += "<tr><th>Name</th><th>ID</th><th>Phone</th><th>Street</th><th>City</th></tr>"
                    for row in display_rows:
                        popup_content += f"""
                            <tr>
                                <td>{row['first_name']} {row['last_name']}</td>
                                <td>{row['id']}</td>
                                <td>{row['phone']}</td>
                                <td>{row['street_name']}</td>
                                <td>{row['city']}</td>
                            </tr>
                        """
                    popup_content += "</table>"
                    if len(rows) > 15:
                        popup_content += "<br><i>Only first 15 records shown</i>"
                else:
                    row = rows[0]
                    popup_content = f"""
                        <b>Name:</b> {row['first_name']} {row['last_name']}<br>
                        <b>ID:</b> {row['id']}<br>
                        <b>Phone:</b> {row['phone']}<br>
                        <b>Street:</b> {row['street_name']}<br>
                        <b>City:</b> {row['city']}<br>
                        <b>Coordinates:</b> {row['lat']}, {row['lon']}
                    """

                folium.Marker(
                    location=[lat, lon],
                    popup=folium.Popup(popup_content, max_width=400),
                    tooltip=f"Click for Details ({len(rows)} entries)",
                    icon=folium.Icon(color="blue", icon="info-sign"),
                ).add_to(marker_cluster)

            # Display the final map
            # folium_static(m)
            st_folium(m, width=700, height=800)
            # Store relevant data for full map rendering
            st.session_state["zoom_location"] = zoom_location
            st.session_state["grouped_points"] = grouped_points
            st.session_state["buffer_gdf"] = buffer_gdf if "buffer_gdf" in locals() else None
            st.session_state["use_buffer"] = option == "location" and choice == "Coordinates"

if result_df is not None and not result_df.empty:
    st.markdown("---")
    st.markdown("### Download your results:")

    csv_string = result_df.drop(columns=["geometry"], errors="ignore").to_csv(index=False, encoding='utf-8-sig')

    csv_bytes = csv_string.encode('utf-8-sig')

    st.download_button(
        label="📥 Download results as CSV",
        data=csv_bytes,
        file_name='query_results.csv',
        mime='text/csv',
    )


#########################
# test
st.sidebar.header(":mailbox: What do you think of the app? Send me mail :)")
contact_form = """
<form action="https://formsubmit.co/Adrian.Taboulet@gmail.com" method="POST">
    <input type="hidden" name="_captcha" value="false">
    <input type="text" name="name" placeholder="YOUR name" required>
    <textarea name="message" placeholder="Your msg here"></textarea>
    <button type="submit">Send</button>
</form>
"""
st.sidebar.markdown(contact_form, unsafe_allow_html=True)

# Apply CSS only to the sidebar
st.markdown("""
<style>
/* Target only elements in the sidebar */
.stSidebar input[type=text], .stSidebar select, .stSidebar textarea {
  width: 100%; /* Full width */
  padding: 12px; /* Some padding */
  border: 1px solid #D7AA57; /* Gray border */
  border-radius: 4px; /* Rounded borders */
  box-sizing: border-box; /* Make sure that padding and width stays in place */
  margin-top: 6px; /* Add a top margin */
  margin-bottom: 16px; /* Bottom margin */
  resize: vertical /* Allow the user to vertically resize the textarea (not horizontally) */
}

/* Style the submit button with a specific background color etc */
.stSidebar input[type=submit] {
  background-color: #D7AA57;
  color: gold;
  padding: 12px 20px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

/* When moving the mouse over the submit button, add a darker green color */
.stSidebar input[type=submit]:hover {
  background-color: #D7AA57;
}
</style>
""", unsafe_allow_html=True)
