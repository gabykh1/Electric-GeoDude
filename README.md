<!-- Banner -->
<p align="center">
  <img src="banner.jpg" alt="Electric GeoDude Banner" width="100%">
</p>

<!-- Logo -->
<p align="center">
  <img src="logo.png" alt="GeoDude Logo" width="500">
</p>

Electric GeoDude is a private Streamlit web app designed to search through a geo-tagged database of leaked information.

Users can search by:
- Coordinates (with radius)
- Address
- Name
- ID

And instantly receive results displayed on an interactive map, without needing any SQL knowledge.

⚠️ **Note:** Because the app uses leaked data, it is **not publicly deployed** and is shown here **for demonstration and educational purposes only**, to showcase the technology, not the content.

### 🎥 Demo: App in Action

[Click here to watch the demo video](https://github.com/user-attachments/assets/33066b38-85f8-4157-b39a-b6dfefd4e582)

---

## 🔍 How It Works Behind the Scenes

The app uses a custom-built SQLite database created from **scraped leaked data**, enhanced with **Google Maps API geocoding** to add accurate latitude and longitude for each record. The result is a powerful and flexible database you can query by name, address, coordinates, or ID.

---

### ⚡️ Loading the Data

```python
@st.cache_data
def load_data(query, params=()):
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df
![image](https://github.com/user-attachments/assets/e79feac7-8f54-4aff-98cf-93929c3439d2)

This function loads data from the SQLite database and caches it using @st.cache_data, so repeated queries are fast.
It uses parameterized queries for security — protecting against SQL injection.

--- Example of function
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
![image](https://github.com/user-attachments/assets/b0eb42eb-a32f-4d78-b42b-357a455ab415)
This function is built to be flexible and forgiving:

Users can enter just a first name, just a city, or any combination.

The query dynamically builds itself based on which inputs are provided.

This is achieved by starting the SQL with WHERE 1=1 - then adding conditions only when needed.

This allows the function to work with at least one input instead of requiring all fields.

--- Example of function
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
![image](https://github.com/user-attachments/assets/f6467c52-fb0b-4e17-9c45-861a19cbeecd)
This function lets users input a pair of coordinates and a search radius.
Here's how it works:

1. Converts the coordinates into a GeoPandas point in metric CRS

2. Builds a circular buffer around the point using gdf.geometry.buffer(buffer_distance)

3. Extracts a bounding box to pre-filter results with a fast SQL query:
WHERE lat BETWEEN ? AND ? AND lon BETWEEN ? AND ?
This makes the query much faster.

Then it filters the results precisely by checking which points fall inside the buffer polygon.




