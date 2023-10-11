import plotly.express as px
import streamlit as st

from data import get_stations, get_temperatures

st.title("Development of max temperatures at German weather stations ")

data_load_state = st.text("Loading stations")
stations = get_stations()
data_load_state.text("Loading stations... done")

st.map(stations.rename(columns={"geoBreite": "latitude", "geoLaenge": "longitude"}))

# todo multiselect, show name of station
# more challenging: select from map, colour map according to max temp rise
selected_station_id = st.selectbox("Choose a station ID", stations["station_id"])


temps = get_temperatures(
    stations.query(f"station_id == {selected_station_id}")["url"].iloc[0]
)
annual_max = temps.resample("A").max()

st.plotly_chart(px.line(temps))
st.plotly_chart(px.line(annual_max))
