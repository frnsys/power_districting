import os
import data
import maup
import json
from glob import glob
from tqdm import tqdm
from collections import defaultdict
from gerrychain.updaters import Tally, cut_edges
from gerrychain import Graph, Partition, constraints, tree
from maup.indexed_geometries import IndexedGeometries
from search import hill_climbing
import matplotlib.pyplot as plt

# Ignore maup warnings
import warnings; warnings.filterwarnings('ignore', 'GeoSeries.isna', UserWarning)

# INIT_DISTRICT = 'generate'
INIT_DISTRICT = 'service_territories'
# INIT_DISTRICT = 'assembly_districts'
N_DISTRICTS = 20
TARGET_POP_MARGIN = 0.02
EJ_CUTOFF = 3

# Geometry for plotting
units = data.load_tracts(geom_only=True)

# Load generated graph
graph = Graph.from_json('data/gen/graph.json')

# Generate initial districts
# (if not using real districts)
if INIT_DISTRICT == 'generate':
    print('Generating districts...')
    total_pop = sum(graph.nodes[n]['population'] for n in graph.nodes)
    ideal_pop = total_pop/N_DISTRICTS
    init = tree.recursive_tree_part(
            graph,
            parts=range(N_DISTRICTS),
            pop_target=ideal_pop,
            pop_col='population',
            epsilon=TARGET_POP_MARGIN,
            node_repeats=2)
    for n in graph.nodes:
        node = graph.nodes[n]
        node['DISTRICT'] = init[n]
    n_districts = len(set(init.values()))

elif INIT_DISTRICT == 'assembly_districts':
    # Assign tracts to districts
    print('Assigning census tracts to assembly districts...')
    districts = data.load_districts()
    units.to_crs(districts.crs, inplace=True)
    assignment = maup.assign(units, districts)
    assert assignment.isna().sum() == 0 # Assert all units were successfully assigned
    for n in graph.nodes:
        graph.nodes[n]['DISTRICT'] = assignment[n]
    n_districts = len(set(assignment.values))

elif INIT_DISTRICT == 'service_territories':
    # Problem with this one is it's not contiguous and
    # there are many overlapping service territories
    print('Assigning census tracts to service territories...')
    try:
        assignment = json.load(open('data/gen/initial/service_territories.json'))
        assignment = {int(k): v for k, v in assignment.items()}
    except FileNotFoundError:
        service_territories = data.load_service_territories()
        units.to_crs(service_territories.crs, inplace=True)
        geoms = IndexedGeometries(service_territories)
        assignment = {}
        for i, unit in tqdm(units.iterrows(), total=len(units)):
            candidates = []
            for j, intersection in geoms.intersections(unit.geometry).items():
                terr = service_territories.loc[j]
                candidates.append((j, intersection.area, terr.geometry.area))

            if len(candidates) == 1:
                assignment[i] = candidates[0][0]
            elif len(candidates) > 1:
                # If multiple candidates, pick the one with the most overlap and smallest service territory
                assignment[i] = sorted(candidates, key=lambda c: (-c[1], c[2]))[0][0]
            else:
                # If no candidates, pick the closest, smallest service territory
                for j, terr in geoms.query(unit.geometry).items():
                    candidates.append((j, unit.geometry.distance(terr), terr.area))
                assignment[i] = sorted(candidates, key=lambda c: (c[1], c[2]))[0][0]
        with open('data/gen/initial/service_territories.json', 'w') as f:
            json.dump(assignment, f)

    for n in graph.nodes:
        graph.nodes[n]['DISTRICT'] = assignment[n]
    n_districts = len(set(assignment.values()))


# Updaters
def _pop_weighted_mean(partition, key):
    data = {}
    for part in partition.parts:
        total_pop = partition['population'][part]
        nodes = [partition.graph.nodes[n] for n in partition.parts[part]]
        vals = [n[key] * n['population'] for n in nodes]
        data[part] = sum(vals)/total_pop
    return data

# Calculate population-weighted mean EJ class
def mean_ej_class(partition):
    return _pop_weighted_mean(partition, 'EJ_Class')

# Count population for each EJ class
def ej_classes(partition):
    data = {}
    for part in partition.parts:
        counts = defaultdict(int)
        nodes = [partition.graph.nodes[n] for n in partition.parts[part]]
        for n in nodes:
            counts[n['EJ_Class']] += n['population']
        data[part] = counts
    return data

# Count percent of "minority" EJ class population
def ej_class_minority_percent(partition):
    data = {}
    for part, counts in partition['ej_classes'].items():
        data[part] = sum(count for ej_class, count in counts.items() if ej_class >= EJ_CUTOFF)/sum(counts.values())
    return data

# A crossover district is one in which,
# when voting with the majority,
# the minority population can vote in their candidate of choice,
# even if they have <50% of the population.
def ej_class_crossover_district(partition):
    data = {}
    for part in partition.parts:
        dem_win = partition['votes_dem'][part] > partition['votes_gop'][part]
        minority_pref = {'dem': 0, 'gop': 0}
        nodes = [partition.graph.nodes[n] for n in partition.parts[part]]
        for n in nodes:
            if n['EJ_Class'] >= EJ_CUTOFF:
                minority_pref['dem'] += n['votes_dem']
                minority_pref['gop'] += n['votes_gop']

        dem_win_minority = minority_pref['dem'] > minority_pref['gop']
        data[part] = dem_win == dem_win_minority
    return data

# A majority-minority district is one where
# the minority makes up >50% of the population
def ej_class_majority_minority(partition):
    return {part: p > 0.5 for part, p in partition['ej_class_minority_percent'].items()}

def count_power_plants(partition):
    data = {}
    for part in partition.parts:
        count = 0
        nodes = [partition.graph.nodes[n] for n in partition.parts[part]]
        for n in nodes:
            count += len(n['power_plants'])
        data[part] = count
    return data

# Prepare initial partition
initial_partition = Partition(
    graph,
    assignment='DISTRICT',

    # Calculate for each generated district map
    updaters={
        # Identifies boundary nodes
        'cut_edges': cut_edges,

        # Calculate district populations
        'population': Tally('population', alias='population'),

        'votes_dem': Tally('votes_dem', alias='votes_dem'),
        'votes_gop': Tally('votes_gop', alias='votes_gop'),

        'mean_ej_class': mean_ej_class,
        'ej_classes': ej_classes,
        'ej_class_minority_percent': ej_class_minority_percent,
        'ej_class_majority_minority': ej_class_majority_minority,
        'ej_class_crossover_district': ej_class_crossover_district,

        'power_plants': count_power_plants,
    }
)


ideal_population = sum(initial_partition['population'].values()) / len(initial_partition)

# Compactness: bound the number of cut edges at 2 times the number of cut edges in the initial plan
compactness_bound = constraints.UpperBound(
    lambda p: len(p['cut_edges']),
    2*len(initial_partition['cut_edges'])
)

# Population
pop_constraint = constraints.within_percent_of_ideal_population(initial_partition, TARGET_POP_MARGIN)

def succ_func(partition):
    # Based on `propose_random_flip`
    if len(partition['cut_edges']) == 0:
        return []

    succs = []
    for edge in partition['cut_edges']:
        for index in [0, 1]:
            flipped_node, other_node = edge[index], edge[1 - index]
            flip = {flipped_node: partition.assignment[other_node]}
            p = partition.flip(flip)
            succs.append((p, score_func(p))) # TODO score_func is very slow
    succs.sort(key=lambda x: x[1], reverse=True)
    return [v for (v, _) in succs]

def goal_func(partition):
    p_crossover_districts = sum(1 for d in partition['ej_class_crossover_district'].values() if d)/n_districts
    return p_crossover_districts > 0.9

def score_func(partition):
    p_crossover_districts = sum(1 for d in partition['ej_class_crossover_district'].values() if d)/n_districts
    return p_crossover_districts

def hash_func(partition):
    return hash(frozenset(partition.assignment.items()))


print('Searching for a districting plan that satisfies criteria...')
best_partition = hill_climbing(
        initial_partition,
        succ_func,
        goal_func,
        max_depth=1000,
        hash_func=hash_func)


# Plot maps
print('Generating maps...')
for f in glob('data/gen/maps/*.png'):
    os.remove(f)

initial_partition.plot(units, figsize=(10, 10), cmap='RdYlBu_r')
plt.axis('off')
plt.savefig('data/gen/maps/_init.png')
plt.close()

for i, partition in enumerate([best_partition]):
    print('% crossover districts:', sum(1 for d in partition['ej_class_crossover_district'].values() if d)/n_districts)
    print('% majority-minority:', sum(1 for d in partition['ej_class_majority_minority'].values() if d)/n_districts)
    partition.plot(units, figsize=(10, 10), cmap='RdYlBu_r')
    plt.axis('off')
    path = 'data/gen/maps/{}.png'.format(i)
    plt.savefig(path)
    plt.close()