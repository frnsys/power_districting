import maup
import fiona
import geopandas
import pandas as pd
from tqdm import tqdm
from gerrychain import Graph
from networkx import is_connected, connected_components
import matplotlib.pyplot as plt

# Census tracts
units_file = 'data/src/ACS_2018_5YR_TRACT_36_NEW_YORK.gdb'
districts_file = 'data/src/ny_legislative_boundaries/NYS-Assembly-Districts.shp'
keep_layers = ['X01_AGE_AND_SEX']

# Load tract data
# See `data/src/ACS_2018_5YR_TRACT_36_NEW_YORK.gdb/TRACT_METADATA_2018.txt`
gdb_layers = fiona.listlayers(units_file)
geo_layer = 'ACS_2018_5YR_TRACT_36_NEW_YORK'
gdb_layers = [l for l in gdb_layers if l.startswith('X')]
print('Layers:', gdb_layers)
print('Using layers:', keep_layers)

units = geopandas.read_file(units_file, layer=geo_layer)
print('Tracts:', len(units))
for layer in tqdm(keep_layers, desc='Merging geodatabase tract layers'):
    other = geopandas.read_file(units_file, layer=layer)
    other['GEOID'] = other['GEOID'].str[7:]
    units = units.merge(other.drop('geometry', axis=1), on='GEOID')
ej_df = pd.read_csv('data/src/FPTZ_NY_3/Map_data.csv', dtype={'Tract_ID': str})
units = units.merge(ej_df, left_on='GEOID', right_on='Tract_ID')
print('Tracts after merging EJ data:', len(units))

# Assign tracts to districts
print('Assigning census tracts to districts...')
districts = geopandas.read_file(districts_file)
units.to_crs(districts.crs, inplace=True)
assignment = maup.assign(units, districts)
assert assignment.isna().sum() == 0 # Assert all units were successfully assigned
units["DISTRICT"] = assignment

# Load/build the node graph (node=unit)
print('Generating graph from census tracts...')
graph = Graph.from_geodataframe(units)

def find_node_by_geoid(geoid):
    for node in graph:
        if graph.nodes[node]['GEOID'] == geoid:
            return node

# Check if any disconnected components (islands), need to connect them manually
# <https://gerrychain.readthedocs.io/en/latest/user/islands.html#strategy-2-connect-the-components-manually>
if graph.islands:
    components = list(connected_components(graph))
    biggest_component_size = max(len(c) for c in components)
    problem_components = [c for c in components if len(c) < biggest_component_size]
    problem_nodes = [node for component in problem_components for node in component]

    # Use this to plot out the map, to locate the problem areas (they will be yellow)
    # For NY, the problem feature is Liberty Island and Ellis Island (they're combined into a single feature)
    problem_geoids = [graph.nodes[node]['GEOID'] for node in problem_nodes]
    # is_a_problem = df['GEOID'].isin(problem_geoids)
    # df = units.to_crs({'init': 'epsg:26986'})
    # df.plot(column=is_a_problem, figsize=(10, 10))
    # plt.axis('off')
    # plt.show()

    # Manually connect them to Governor's Island
    # Look up GEOIDs here (property here is "FIPS"):
    # <https://hub.arcgis.com/datasets/esri::usa-tracts?geometry=-74.066%2C40.685%2C-74.011%2C40.696>
    to_node = find_node_by_geoid('36061000500')
    from_node = find_node_by_geoid(problem_geoids[0])
    graph.add_edge(from_node, to_node)

# Assert that all islands connected
assert is_connected(graph)

print('Saving graph...')
graph.to_json('data/gen/graph.json')
