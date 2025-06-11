import streamlit as st
import pandas as pd
import folium
from streamlit_folium import folium_static

st.set_page_config(layout="wide")

st.title("서울 지역별 범죄 발생 통계")
st.write("CSV 파일을 기반으로 서울 지역의 범죄 발생 건수를 시각화합니다.")

# CSV 파일 로드
try:
    df = pd.read_csv("crime_statistics.csv")
    st.success("`crime_statistics.csv` 파일을 성공적으로 불러왔습니다.")
except FileNotFoundError:
    st.error("`crime_statistics.csv` 파일을 찾을 수 없습니다. 파일을 프로젝트 루트에 업로드했는지 확인해주세요.")
    st.stop()

# 서울 지역 데이터 필터링 (예시: 서울 종로구, 서울 중구 등)
# 실제 CSV 파일의 컬럼명에 따라 조정해야 합니다.
seoul_districts = [col for col in df.columns if col.startswith("서울")]

if not seoul_districts:
    st.warning("CSV 파일에 '서울'로 시작하는 지역 컬럼이 없습니다. 컬럼명을 확인해주세요.")
    st.stop()

# 범죄 대분류 선택 (사이드바)
st.sidebar.header("필터 옵션")
selected_crime_category = st.sidebar.selectbox(
    "범죄 대분류 선택",
    ["전체"] + df["범죄대분류"].unique().tolist()
)

# 선택된 범죄 대분류에 따라 데이터 필터링
if selected_crime_category != "전체":
    df_filtered = df[df["범죄대분류"] == selected_crime_category].copy()
else:
    df_filtered = df.copy()

# 서울 지역별 총 범죄 건수 계산
# 각 범죄 대분류, 중분류에 대해 지역별 데이터를 합산합니다.
# 이 예시에서는 각 지역 컬럼의 숫자를 합산합니다.
# 실제 데이터의 특성에 따라 '범죄중분류'를 고려하여 더 세밀한 합산 로직이 필요할 수 있습니다.
crime_by_district = {}
for district in seoul_districts:
    # 숫자가 아닌 값은 0으로 처리 (예: 공백이나 문자열)
    crime_by_district[district] = pd.to_numeric(df_filtered[district], errors='coerce').sum()

# 데이터프레임으로 변환
crime_summary_df = pd.DataFrame(
    {"지역": list(crime_by_district.keys()), "총 범죄 건수": list(crime_by_district.values())}
)

st.subheader(f"{selected_crime_category} - 서울 지역별 총 범죄 건수")
st.dataframe(crime_summary_df.sort_values(by="총 범죄 건수", ascending=False))

# 서울 지도 시각화 (Folium)
# 서울 중심 좌표 (예시: 37.5665, 126.9780)
m = folium.Map(location=[37.5665, 126.9780], zoom_start=11)

# 서울 구별 경계 데이터 (GeoJSON 파일 필요)
# 이 부분은 별도의 GeoJSON 파일이 필요합니다.
# 예를 들어, 서울시 구별 행정구역 경계 GeoJSON 파일을 다운로드하여 사용해야 합니다.
# (예: https://raw.githubusercontent.com/southkorea/seoul-maps/master/korea_administrative_boundaries_v1.geojson)
# 여기서는 예시로 설명하며, 실제 사용 시 해당 파일을 다운로드하여 프로젝트에 포함해야 합니다.

# 예시: GeoJSON 파일 로드 및 지도에 범죄 건수 표시 (가상의 경계 데이터 및 병합)
try:
    # 실제 GeoJSON 파일 경로로 변경해주세요.
    # st.cache_data를 사용하여 GeoJSON 파일 로드를 캐싱하면 성능 향상에 도움이 됩니다.
    @st.cache_data
    def load_seoul_geojson():
        # 여기에 서울 구별 GeoJSON 파일의 URL 또는 로컬 경로를 넣어주세요.
        # 예: 서울시 구별 GeoJSON 파일 다운로드 후 프로젝트에 포함
        # return json.load(open("seoul_geojson.geojson", "r", encoding="utf-8"))
        return None # 실제 GeoJSON 경로로 대체 필요

    seoul_geojson = load_seoul_geojson()

    if seoul_geojson:
        # GeoJSON과 범죄 데이터를 병합하여 지도에 표시
        folium.Choropleth(
            geo_data=seoul_geojson,
            name="choropleth",
            data=crime_summary_df,
            columns=["지역", "총 범죄 건수"],
            key_on="feature.properties.name", # GeoJSON 파일의 구 이름 속성 (예: 'name' 또는 'SIG_ENG_NM')
            fill_color="YlOrRd",
            fill_opacity=0.7,
            line_opacity=0.2,
            legend_name="총 범죄 건수"
        ).add_to(m)

        folium.LayerControl().add_to(m)
        st.subheader("서울 지역별 범죄 발생 지도")
        folium_static(m)
    else:
        st.info("서울 구별 경계 GeoJSON 파일이 없거나 로드할 수 없어 지도를 표시할 수 없습니다. GeoJSON 파일을 준비해주세요.")
        # GeoJSON 파일이 없는 경우, 마커로 각 구의 중심에 범죄 건수를 표시하는 것도 고려해볼 수 있습니다.
        # 이 예시에서는 생략합니다.

except Exception as e:
    st.error(f"지도 시각화 중 오류가 발생했습니다: {e}")
    st.info("서울 구별 경계 GeoJSON 파일 경로와 속성 키(`key_on`)가 올바른지 확인해주세요.")


st.markdown("---")
st.write("이 앱은 '범죄 발생 지역별 통계' 데이터를 기반으로 서울 지역의 범죄 현황을 보여줍니다.")
