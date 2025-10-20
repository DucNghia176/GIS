import streamlit as st
import streamlit.components.v1 as components
from streamlit_folium import st_folium
import geopandas as gpd
import osmnx as ox
import folium
from shapely.geometry import Point
from streamlit_js_eval import get_geolocation
import matplotlib.pyplot as plt

st.set_page_config(page_title="Phân tích tiếp cận y tế Hà Nội", layout="wide")
st.title("🗺️ Phân tích tiếp cận cơ sở y tế ở Hà Nội")

# ======================
# 1️⃣ Tải dữ liệu
# ======================
@st.cache_data
def load_data():
    hanoi_gdf = ox.geocode_to_gdf("Hanoi, Vietnam")

    # Lấy dữ liệu cơ sở y tế
    tags = {"amenity": ["hospital", "clinic", "doctors"]}
    health_facilities_gdf = ox.features_from_place("Hanoi, Vietnam", tags)

    # Xử lý dữ liệu hình học
    health_facilities_gdf = health_facilities_gdf.to_crs(epsg=3405)
    health_facilities_gdf["geometry"] = health_facilities_gdf["geometry"].centroid
    health_facilities_gdf = health_facilities_gdf.to_crs(epsg=4326)
    health_facilities_gdf['name'] = health_facilities_gdf['name'].fillna("Không rõ")
    health_facilities_gdf['amenity'] = health_facilities_gdf['amenity'].fillna("Không rõ")

    return hanoi_gdf, health_facilities_gdf

with st.spinner("Đang tải dữ liệu địa lý (lần đầu có thể mất vài phút)..."):
    hanoi, health_facilities = load_data()

# ======================
# 2️⃣ Hiển thị bản đồ cơ sở y tế
# ======================
m = folium.Map(location=[21.0285, 105.8542], zoom_start=11, tiles="CartoDB positron")
folium.GeoJson(hanoi.geometry.iloc[0], name="Hà Nội").add_to(m)

for _, row in health_facilities.iterrows():
    folium.CircleMarker(
        location=[row.geometry.y, row.geometry.x],
        radius=4,
        color="magenta",
        fill=True,
        fill_opacity=0.7,
        popup=f"{row['name']} ({row['amenity']})"
    ).add_to(m)

# # ======================
# # 3️⃣ Chọn vị trí người dùng
# # ======================

# # 🔹 Thêm đoạn JavaScript lấy GPS (bổ sung mới)
# st.subheader("📍 Chọn vị trí của bạn")

# components.html("""
# <script>
# navigator.geolocation.getCurrentPosition(
#     (pos) => {
#         const coords = pos.coords;
#         const lat = coords.latitude;
#         const lon = coords.longitude;
#         // Gửi kết quả lên Streamlit qua postMessage
#         window.parent.postMessage({lat: lat, lon: lon}, "*");
#     },
#     (err) => {
#         window.parent.postMessage({error: err.message}, "*");
#     }
# );
# </script>
# """, height=0)

# clicked_coords = None

# location = get_geolocation()

# if location:
#     lat = location['coords']['latitude']
#     lon = location['coords']['longitude']
#     clicked_coords = (lat, lon)
#     st.success(f"Vị trí GPS: ({lat:.5f}, {lon:.5f})")
# else:
#     st.info("Chưa có vị trí GPS — vui lòng cấp quyền hoặc chọn trên bản đồ.")

# if not clicked_coords:
#     st.write("👉 Hoặc click trực tiếp trên bản đồ bên dưới:")
#     st_map = st_folium(m, width=900, height=600)
#     if st_map and st_map.get("last_clicked"):
#         lat = st_map["last_clicked"]["lat"]
#         lon = st_map["last_clicked"]["lng"]
#         clicked_coords = (lat, lon)

# ======================
# 3️⃣ Chọn vị trí người dùng
# ======================
st.subheader("📍 Chọn vị trí của bạn")

# Dùng session_state để lưu toạ độ tránh bị reset
if "clicked_coords" not in st.session_state:
    st.session_state.clicked_coords = None

# Tuỳ chọn lấy GPS hoặc chọn trên bản đồ
option = st.radio(
    "Chọn cách xác định vị trí:",
    ("Lấy từ GPS", "Chọn thủ công trên bản đồ")
)

if option == "Lấy từ GPS":
    st.write("👉 Nhấn nút bên dưới để lấy vị trí GPS:")
    location = get_geolocation()
    if st.button("📡 Lấy vị trí hiện tại"):
        if location:
            lat = location['coords']['latitude']
            lon = location['coords']['longitude']
            st.session_state.clicked_coords = (lat, lon)
            st.success(f"Vị trí GPS: ({lat:.5f}, {lon:.5f})")
        else:
            st.warning("Không thể lấy vị trí — vui lòng cấp quyền truy cập vị trí cho trình duyệt.")
elif option == "Chọn thủ công trên bản đồ":
    st.info("👉 Click trực tiếp trên bản đồ để chọn vị trí:")
    st_map = st_folium(m, width=900, height=600)
    if st_map and st_map.get("last_clicked"):
        lat = st_map["last_clicked"]["lat"]
        lon = st_map["last_clicked"]["lng"]
        st.session_state.clicked_coords = (lat, lon)
        st.success(f"Vị trí thủ công: ({lat:.5f}, {lon:.5f})")
        
if st.button("🗑️ Xoá vị trí GPS đã lưu"):
    st.session_state.clicked_coords = None
    st.info("Đã xoá vị trí, vui lòng lấy lại GPS mới.")
# Lấy ra toạ độ hiện tại từ session_state
clicked_coords = st.session_state.clicked_coords

# ======================
# 4️⃣ Phân tích kết quả
# ======================
if clicked_coords:
    lat, lon = clicked_coords
    st.success(f"Vị trí đã chọn: ({lat:.5f}, {lon:.5f})")

    # Chuyển sang CRS mét để tính khoảng cách
    health_facilities_utm = health_facilities.to_crs(epsg=3405)
    clicked_point_gdf = gpd.GeoDataFrame(geometry=[Point(lon, lat)], crs="EPSG:4326").to_crs(epsg=3405)

    # Tính khoảng cách
    health_facilities_utm["distance_m"] = health_facilities_utm.distance(clicked_point_gdf.iloc[0].geometry)

    # 4.1. Lấy 3 cơ sở gần nhất
    nearest = health_facilities_utm.nsmallest(3, "distance_m").to_crs(epsg=4326)
    st.subheader("🏥 3 cơ sở y tế gần nhất:")
    for _, row in nearest.iterrows():
        st.write(f"- **{row['name']}** — {row['distance_m']:.0f} m — ({row['amenity']})")

    # 4.2. Thêm buffer (vùng ảnh hưởng 3 km)
    buffer_radius = 3000  # 3km
    buffer_area = clicked_point_gdf.buffer(buffer_radius)
    facilities_in_buffer = health_facilities_utm[health_facilities_utm.intersects(buffer_area.iloc[0])]
    count_in_buffer = len(facilities_in_buffer)

    st.subheader("📊 Phân tích vùng ảnh hưởng 3 km")
    st.write(f"- Số cơ sở y tế trong bán kính **3 km**: **{count_in_buffer}**")

    # 4.3. Vẽ bản đồ kết quả (tất cả cơ sở y tế)
    m2 = folium.Map(location=[lat, lon], zoom_start=12, tiles="CartoDB positron")

    # Vẽ buffer 3km
    folium.Circle(
        location=[lat, lon],
        radius=buffer_radius,
        color='blue',
        fill=True,
        fill_opacity=0.1,
        popup='Phạm vi 3 km'
    ).add_to(m2)

    # Marker người dùng
    folium.Marker(
        [lat, lon],
        popup="Vị trí của bạn",
        icon=folium.Icon(color="blue", icon="user", prefix="fa")
    ).add_to(m2)

    # Định nghĩa màu theo loại cơ sở
    color_map = {
        "hospital": "red",
        "clinic": "green",
        "doctors": "orange",
        "Không rõ": "gray"
    }

    # Vẽ tất cả các cơ sở y tế với màu tương ứng
    for _, row in health_facilities.iterrows():
        color = color_map.get(row["amenity"], "gray")
        folium.CircleMarker(
            location=[row.geometry.y, row.geometry.x],
            radius=5,
            color=color,
            fill=True,
            fill_opacity=0.7,
            popup=f"{row['name']} ({row['amenity']})"
        ).add_to(m2)

    # Vẽ 3 cơ sở gần nhất (nổi bật)
    for _, row in nearest.iterrows():
        folium.CircleMarker(
            location=[row.geometry.y, row.geometry.x],
            radius=9,
            color="darkred",
            fill=True,
            fill_opacity=0.9,
            popup=f"🏥 {row['name']} — {row['distance_m']:.0f} m"
        ).add_to(m2)

    # Thêm chú thích màu (legend)
    legend_html = """
    <div style="position: fixed; 
                bottom: 40px; left: 40px; width: 210px; height: 130px; 
                background-color: white; z-index:9999; font-size:14px;
                border:2px solid grey; border-radius:10px; padding:10px;">
        <b>🩺 Chú thích màu</b><br>
        <i style="color:red;">●</i> Bệnh viện<br>
        <i style="color:green;">●</i> Phòng khám<br>
        <i style="color:orange;">●</i> Bác sĩ<br>
        <i style="color:gray;">●</i> Khác<br>
        <i style="color:darkred;">●</i> Cơ sở gần nhất
    </div>
    """
    m2.get_root().html.add_child(folium.Element(legend_html))

    st.write("🗺️ **Bản đồ kết quả (toàn Hà Nội):**")
    st_folium(m2, width=900, height=600)

    # 4.4. Thống kê loại hình trong bán kính 3 km (đặt sau bản đồ)
    if count_in_buffer > 0:
        amenity_counts = facilities_in_buffer['amenity'].value_counts()
        fig, ax = plt.subplots()
        amenity_counts.plot(kind='bar', ax=ax, color=['red', 'green', 'orange', 'gray'])
        ax.set_title("Phân bố loại hình cơ sở y tế trong bán kính 3 km")
        ax.set_ylabel("Số lượng")
        st.pyplot(fig)
    else:
        st.info("Không có cơ sở y tế nào trong phạm vi 3 km.")
