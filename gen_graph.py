import fiona
import pandas as pd
import geopandas as gpd
from tqdm import tqdm
from gerrychain import Graph
from networkx import is_connected, connected_components

# Census tracts
# See `data/src/ACS_2018_5YR_TRACT_36_NEW_YORK.gdb/TRACT_METADATA_2018.txt`
tracts_file = 'data/src/ACS_2018_5YR_TRACT_36_NEW_YORK.gdb'
keep_layers = ['X02_RACE']
geo_layer = 'ACS_2018_5YR_TRACT_36_NEW_YORK'
ej_file = 'data/src/FPTZ_NY_3/Map_data.csv'
POP_COL = 'B02001e1' # depends on what layers we load, see the metadata file above

gdb_layers = fiona.listlayers(tracts_file)
available_tract_layers = [l for l in gdb_layers if l.startswith('X')]

def load_tracts():
    tracts = gpd.read_file(tracts_file, layer=geo_layer)
    for layer in tqdm(keep_layers, desc='Merging geodatabase tract layers'):
        other = gpd.read_file(tracts_file, layer=layer)
        other['GEOID'] = other['GEOID'].str[7:]
        tracts = tracts.merge(other.drop('geometry', axis=1), on='GEOID')
    tracts['population'] = tracts[POP_COL]

    ej_df = pd.read_csv(ej_file, dtype={'Tract_ID': str})
    ej_df['Wind_Class'] = pd.factorize(ej_df['Wind_Class'], sort=True)[0] # Convert letter classes to integers
    ej_df['Solar_Class'] = pd.factorize(ej_df['Solar_Class'], sort=True)[0]
    tracts = tracts.merge(ej_df, left_on='GEOID', right_on='Tract_ID')

    return tracts

units = load_tracts()

print('Layers:', available_tract_layers)
print('Using layers:', keep_layers)
print('Tracts:', len(units))

# Load/build the node graph (node=unit)
print('Generating graph from census tracts...')
graph = Graph.from_geodataframe(units)

def find_node_by_geoid(geoid):
    for node in graph:
        if graph.nodes[node]['GEOID'] == geoid:
            return node

# Check if any disconnected components (islands), need to connect them manually
# <https://gerrychain.readthedocs.io/en/latest/user/islands.html#strategy-2-connect-the-components-manually>
print('Fixing islands (if any)...')
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
