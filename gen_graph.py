import data
from gerrychain import Graph
from networkx import is_connected, connected_components
import matplotlib.pyplot as plt

units = data.load_tracts()
print('Layers:', data.available_tract_layers())
print('Using layers:', data.keep_layers)
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
