import streamlit as st
import pandas as pd
import folium
from streamlit_folium import folium_static
import json
import requests # URL에서 데이터를 가져오기 위해 필요합니다.

# --- Streamlit 페이지 설정 ---
st.set_page_config(layout="wide")

# --- 앱 제목 및 설명 ---
st.title("서울 지역별 범죄 발생 통계")
st.write("CSV 파일을 기반으로 서울 지역의 범죄 발생 건수를 시각화합니다.")
st.write("※ 데이터에 '서울'로 시작하는 지역 컬럼이 없거나, GeoJSON 파일 로드에 실패하면 지도가 표시되지 않을 수 있습니다.")

# --- CSV 파일 로드 ---
try:
    df = pd.read_csv("crime_statistics.csv")
    st.success("`crime_statistics.csv` 파일을 성공적으로 불러왔습니다.")
except FileNotFoundError:
    st.error("`crime_statistics.csv` 파일을 찾을 수 없습니다. 파일을 프로젝트 루트에 업로드했는지 확인해주세요.")
    st.stop() # 파일이 없으면 앱 실행 중단

# --- 서울 지역 데이터 컬럼 식별 ---
# CSV 파일의 컬럼명에 따라 '서울종로구', '서울중구' 등의 형태로 되어 있어야 합니다.
seoul_districts = [col for col in df.columns if col.startswith("서울")]

if not seoul_districts:
    st.warning("CSV 파일에 '서울'로 시작하는 지역 컬럼이 없습니다. 컬럼명을 확인해주세요.")
    st.stop() # 서울 지역 컬럼이 없으면 앱 실행 중단

# --- 사이드바 필터 옵션 ---
st.sidebar.header("필터 옵션")

# 범죄 대분류 선택
selected_crime_category = st.sidebar.selectbox(
    "범죄 대분류 선택",
    ["전체"] + df["범죄대분류"].unique().tolist()
)

# 선택된 범죄 대분류에 따라 데이터 필터링
if selected_crime_category != "전체":
    df_filtered = df[df["범죄대분류"] == selected_crime_category].copy()
else:
    df_filtered = df.copy()

# --- 서울 지역별 총 범죄 건수 계산 ---
crime_by_district = {}
for district in seoul_districts:
    # 예시: '서울종로구' -> '종로구' 로 변환하여 GeoJSON 'name' 속성과 매칭 시도
    # GeoJSON은 보통 '종로구'와 같이 구 이름만 가지고 있습니다.
    district_name_for_map = district.replace("서울", "")

    # 숫자로 변환할 수 없는 값은 0으로 처리 (NaN)
    crime_by_district[district_name_for_map] = pd.to_numeric(df_filtered[district], errors='coerce').sum()

# 데이터프레임으로 변환하여 표로 보여주기
crime_summary_df = pd.DataFrame(
    {"지역": list(crime_by_district.keys()), "총 범죄 건수": list(crime_by_district.values())}
)

st.subheader(f"{selected_crime_category} - 서울 지역별 총 범죄 건수")
st.dataframe(crime_summary_df.sort_values(by="총 범죄 건수", ascending=False))

# --- 서울 지도 시각화 (Folium) ---
# 서울 중심 좌표 (예시: 37.5665, 126.9780)
m = folium.Map(location=[37.5665, 126.9780], zoom_start=11)

# 서울 구별 경계 데이터 (GeoJSON URL에서 로드) 함수
@st.cache_data # Streamlit 캐싱을 사용하여 URL에서 데이터를 한 번만 가져오도록 합니다.
def load_seoul_geojson_from_url(url):
    try:
        response = requests.get(url)
        response.raise_for_status() # HTTP 오류가 발생하면 예외 발생 (예: 404 Not Found)
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"GeoJSON URL에서 데이터를 가져오는 데 실패했습니다. URL을 확인하거나 네트워크 연결을 점검해주세요: {e}")
        return None
    except json.JSONDecodeError:
        st.error("가져온 GeoJSON 파일의 형식이 올바르지 않습니다. Gist URL이 Raw 파일 링크인지 확인해주세요.")
        return None
    except Exception as e:
        st.error(f"GeoJSON 로드 중 예기치 않은 오류가 발생했습니다: {e}")
        return None

# !!! 중요: 여기에 Gist에서 복사한 Raw URL을 붙여넣으세요! !!!
# 예시: "https://gist.githubusercontent.com/사용자이름/고유ID/raw/해시/seoul_geojson.json"
GEOJSON_URL = "https://raw.githubusercontent.com/moondaon305/crime2/refs/heads/main/seoul_geojson.json" # <-- 이 부분을 반드시 수정해야 합니다.

seoul_geojson = load_seoul_geojson_from_url(GEOJSON_URL)

if seoul_geojson:
    try:
        # GeoJSON과 범죄 데이터를 병합하여 지도에 표시 (Choropleth 맵)
        # key_on 값: GeoJSON 파일 내부의 'properties' 객체 안에 있는 구 이름 속성 키입니다.
        # 대부분의 서울 GeoJSON 파일은 'name' 속성을 사용합니다.
        folium.Choropleth(
            geo_data=seoul_geojson,
            name="choropleth",
            data=crime_summary_df,
            columns=["지역", "총 범죄 건수"],
            key_on="feature.properties.name", # 이 속성 키가 GeoJSON 파일의 구 이름과 일치해야 합니다.
            fill_color="YlOrRd", # 색상 스케일 (노랑-주황-빨강)
            fill_opacity=0.7,    # 채우기 투명도
            line_opacity=0.2,    # 경계선 투명도
            legend_name="총 범죄 건수"
        ).add_to(m)

        # 지도 컨트롤 추가 (레이어 선택 등)
        folium.LayerControl().add_to(m)

        st.subheader("서울 지역별 범죄 발생 지도")
        # Streamlit에 Folium 지도 렌더링
        folium_static(m, width=900, height=600) # 지도의 너비와 높이를 조절할 수 있습니다.

    except Exception as e:
        st.error(f"지도 시각화 중 오류가 발생했습니다. 다음을 확인해주세요: {e}")
        st.info("1. `GEOJSON_URL` 변수에 입력된 Gist Raw URL이 올바른지.")
        st.info("2. Gist에 업로드한 GeoJSON 파일의 형식이 유효한지.")
        st.info("3. `key_on=\"feature.properties.name\"` 부분이 GeoJSON 파일의 실제 구 이름 속성 키와 일치하는지.")
        st.info("4. CSV 파일의 '서울종로구'와 같은 지역 컬럼 이름에서 '서울'을 제거한 이름('종로구')이 GeoJSON의 구 이름과 정확히 일치하는지.")
else:
    st.info("서울 구별 경계 GeoJSON 파일을 불러올 수 없어 지도를 표시할 수 없습니다.")
    st.info("`GEOJSON_URL`이 올바른지, 또는 네트워크 연결에 문제가 없는지 확인해주세요.")


st.markdown("---")
st.write("이 앱은 '범죄 발생 지역별 통계' 데이터를 기반으로 서울 지역의 범죄 현황을 보여줍니다.")
st.write("데이터 출처: 사용자 제공 CSV 파일")
