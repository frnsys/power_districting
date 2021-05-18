import fiona
import pandas as pd
import geopandas as gpd
from tqdm import tqdm
from util import distribute_values
from maup.indexed_geometries import IndexedGeometries

# Census tracts
# See `data/src/ACS_2018_5YR_TRACT_36_NEW_YORK.gdb/TRACT_METADATA_2018.txt`
units_file = 'data/src/ACS_2018_5YR_TRACT_36_NEW_YORK.gdb'
geo_layer = 'ACS_2018_5YR_TRACT_36_NEW_YORK'
keep_layers = ['X02_RACE']
POP_COL = 'B02001e1' # depends on what layers we load, see the metadata file above

# Other data
ej_file = 'data/src/FPTZ_NY_3/Map_data.csv'
service_territories_file = 'data/src/electric_retail_service_territories/Retail_Service_Territories.shp'
holding_companies_file = 'data/src/electric_holding_company_areas/Holding_Company_Areas.shp'
substations_file = 'data/src/infra/electric_substations/Substations.shp'
power_plants_file = 'data/src/infra/power_plants/Power_Plants.shp'

# Election data
election_file = 'data/src/2020_US_County_Level_Presidential_Results.csv'
counties_shapefile = 'data/src/counties/tl_2020_us_county.shp'

# Existing districts
districts_file = 'data/src/ny_legislative_boundaries/NYS-Assembly-Districts.shp'


def _find_matching_features(units, path):
    df = gpd.read_file(path)
    df = df[df['STATE'] == 'NY']
    df.to_crs(units.crs, inplace=True)
    geoms = IndexedGeometries(df)
    feats = []
    for _, unit in units.iterrows():
        feats.append(list(geoms.query(unit.geometry).index))
    return feats


def load_tracts(geom_only=False):
    units = gpd.read_file(units_file, layer=geo_layer)

    if not geom_only:
        for layer in tqdm(keep_layers, desc='Merging geodatabase tract layers'):
            other = gpd.read_file(units_file, layer=layer)
            other['GEOID'] = other['GEOID'].str[7:]
            units = units.merge(other.drop('geometry', axis=1), on='GEOID')
        units['population'] = units[POP_COL]

        # Disaggregate county-level election data into tracts
        # Not at all perfect, just an estimate. Best we can do
        election_df = pd.read_csv(election_file, dtype={'county_fips': str})
        election_df = election_df[election_df['state_name'] == 'New York']
        counties_df = gpd.read_file(counties_shapefile)
        counties_df['county_fips'] = counties_df['STATEFP'] + counties_df['COUNTYFP']
        counties = counties_df.merge(election_df, on='county_fips')
        units = distribute_values(counties, ['votes_gop', 'votes_dem'], units, distribute_type='fractional', distribute_on='population', distribute_round=True)

        # Infrastructure
        units['substations'] = _find_matching_features(units, substations_file)
        units['power_plants'] = _find_matching_features(units, power_plants_file)


    ej_df = pd.read_csv(ej_file, dtype={'Tract_ID': str})
    units = units.merge(ej_df, left_on='GEOID', right_on='Tract_ID')

    return units

def available_tract_layers():
    gdb_layers = fiona.listlayers(units_file)
    return [l for l in gdb_layers if l.startswith('X')]

def load_districts():
    return gpd.read_file(districts_file)

def load_service_territories():
    df = gpd.read_file(service_territories_file)
    return df[df['STATE'] == 'NY'][['geometry']]

def load_holding_companies():
    df = gpd.read_file(holding_companies_file)
    return df[df['STATE'] == 'NY'][['geometry']]
