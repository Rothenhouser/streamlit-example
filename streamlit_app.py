from collections import namedtuple
import altair as alt
import math
import pandas as pd
import streamlit as st

"""
# Maximum temperatures


"""
import plotly.express as px

import re
import zipfile
from io import BytesIO

import bs4
import pandas as pd
import requests

DATA_DIR_URL = "https://opendata.dwd.de/climate_environment/CDC/observations_germany/climate/monthly/kl/historical/"
STATION_INFO = DATA_DIR_URL + "/KL_Monatswerte_Beschreibung_Stationen.txt"


def get_station_info():
    """
    Get station info from the station info file.

    Unfortunately, not all stations listed here have data files available.
    """
    return pd.read_fwf(
        STATION_INFO,
        encoding="windows-1252",
        colspecs="infer",
        infer_nrows=10,
        skiprows=[0, 1],
        # Can't parse the headers along with the rest because of the terrible formatting.
        header=None,
        names=[
            "Stations_id",
            "von_datum",
            "bis_datum",
            "Stationshoehe",
            "geoBreite",
            "geoLaenge",
            "Stationsname",
            "Bundesland",
        ],
    )


def _get_linked_file_urls(parent_url, ext=""):
    response = requests.get(parent_url)
    response.raise_for_status()
    soup = bs4.BeautifulSoup(response.text, "html.parser")
    return [
        parent_url + href
        for node in soup.find_all("a")
        if (href := node.get("href")).endswith(ext)
    ]


def _parse_data_urls_for_availability(data_urls):
    availability = {}
    for url in data_urls:
        m = re.search("KL_(\d*)_(\d*)_(\d*)_hist", url)
        stn_id, start, end = map(int, m.groups())
        if stn_id in availability:
            raise ValueError(f"Parsed more than one URL for {stn_id}")
        availability[stn_id] = {"start": start, "end": end, "url": url}
    return availability


def get_useful_stations_from_data_urls(latest_start=19800000, earliest_end=20200000):
    data_urls = _get_linked_file_urls(DATA_DIR_URL, "zip")
    availability_df = pd.DataFrame(
        _parse_data_urls_for_availability(data_urls)
    ).T.reset_index(names="station_id")
    useful_stations = availability_df[
        (availability_df["end"] >= earliest_end)
        & (availability_df["start"] <= latest_start)
    ]
    return useful_stations


def get_temperatures(zip_url):
    response = requests.get(zip_url)
    response.raise_for_status()
    with zipfile.ZipFile(BytesIO(response.content)) as myzip:
        [temperatures] = [n for n in myzip.namelist() if n.startswith("produkt")]
        with myzip.open(temperatures) as f:
            return pd.read_csv(
                f,
                sep=";",
                index_col="MESS_DATUM_BEGINN",
                usecols=["MESS_DATUM_BEGINN", "MX_TX"],
                parse_dates=["MESS_DATUM_BEGINN"],
            )


@st.cache_data()
def get_stations():
    return get_station_info()


# todo this is dumb
@st.cache_data()
def get_temps(url):
    return get_temperatures(url)


st.title("Development of max temperatures at German weather stations ")

data_load_state = st.text("Loading stations")

stations = get_stations()
st.write(stations)

useful_stations = get_useful_stations_from_data_urls()
st.write(
    f"Of {len(stations)} possible stations, only {len(useful_stations)} have current and long enough data."
)
st.write(useful_stations)

data_load_state.text("Loading stations... done")

useful_stations_merged = stations[
    stations["Stations_id"].isin(useful_stations["station_id"])
]

st.map(stations.rename(columns={"geoBreite": "latitude", "geoLaenge": "longitude"}))
st.map(
    useful_stations_merged.rename(
        columns={"geoBreite": "latitude", "geoLaenge": "longitude"}
    )
)

# todo multiselect, show name of station
# more challenging: select from map, colour map according to max temp rise
selected_station_id = st.selectbox("Choose a station ID", useful_stations["station_id"])


# todo clean data, -999 for missing value
temps = get_temps(
    useful_stations.query(f"station_id == {selected_station_id}")["url"].iloc[0]
)
annual_max = temps.resample("A").max()

st.plotly_chart(px.line(temps))
st.plotly_chart(px.line(annual_max))
