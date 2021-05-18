import data
import maup
import json
from maup.indexed_geometries import IndexedGeometries
from tqdm import tqdm
from functools import partial
from collections import defaultdict
from gerrychain.proposals import recom
from gerrychain.accept import always_accept
from gerrychain.updaters import Tally, cut_edges
from gerrychain import Graph, Partition, MarkovChain, constraints, tree
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
    print('Assigning census tracts to districts...')
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

def mean_ej_class(partition):
    return _pop_weighted_mean(partition, 'EJ_Class')

def ej_classes(partition):
    data = {}
    for part in partition.parts:
        counts = defaultdict(int)
        nodes = [partition.graph.nodes[n] for n in partition.parts[part]]
        for n in nodes:
            counts[n['EJ_Class']] += n['population']
        data[part] = counts
    return data

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

# Plot initial districts
initial_partition.plot(units, figsize=(10, 10), cmap='RdYlBu_r')
plt.axis('off')
# plt.show()
plt.savefig('data/gen/init_map.png')
plt.close()


# District proposal method: ReCom
# For more on ReCom see <https://mggg.org/VA-report.pdf>
#   At each step, we (uniformly) randomly select a pair of adjacent districts and
#   merge all of their blocks in to a single unit. Then, we generate a spanning tree
#   for the blocks of the merged unit with the Kruskal/Karger algorithm. Finally,
#   we cut an edge of the tree at random, checking that this separates the region
#   into two new districts that are population balanced.
# pop_percent_margin:
#   This should be something like 0.01 but the initial districting fails to meet this criteria
#   unless it's a higher value like 0.25
pop_percent_margin = TARGET_POP_MARGIN if INIT_DISTRICT == 'generate' else 0.25
ideal_population = sum(initial_partition['population'].values()) / len(initial_partition)
proposal = partial(recom,
                   pop_col='population',
                   pop_target=ideal_population,
                   epsilon=pop_percent_margin,
                   node_repeats=2)

# Compactness: bound the number of cut edges at 2 times the number of cut edges in the initial plan
compactness_bound = constraints.UpperBound(
    lambda p: len(p['cut_edges']),
    2*len(initial_partition['cut_edges'])
)

# Population
pop_constraint = constraints.within_percent_of_ideal_population(initial_partition, pop_percent_margin)

chain = MarkovChain(
    proposal=proposal,

    # Constraints: a list of predicates that return
    # whether or not a map is valid
    # Built-in constraints: <https://gerrychain.readthedocs.io/en/latest/api.html#module-gerrychain.constraints>
    constraints=[
        # compactness_bound,
        # pop_constraint,
        # constraints.contiguous # Initial districts aren't contiguous, so this fails if using real districts
    ],

    # Whether or not to accept a valid proposed map.
    # `always_accept` always accepts valid proposals
    accept=always_accept,

    # Initial state
    initial_state=initial_partition,

    # Number of valid maps to step through
    total_steps=100
)


desiderata = {
    'All are crossover districts': lambda p: all(partition['ej_class_crossover_district'].values())
}

# Iterate over the proposals
print('Generating maps...')
import os
import imageio
from glob import glob
for f in glob('data/gen/maps/*.png'):
    os.remove(f)

images = []
for i, partition in enumerate(chain.with_progress_bar()):
    for label, d in desiderata.items():
        print(label, ':', d(partition))
    partition.plot(units, figsize=(10, 10), cmap='RdYlBu_r')
    plt.axis('off')
    path = 'data/gen/maps/{}.png'.format(i)
    plt.savefig(path)
    plt.close()
    images.append(imageio.imread(path))
imageio.mimsave('data/gen/maps.gif', images)
    # print(sorted(partition["SEN12"].percents("Dem")))

import ipdb; ipdb.set_trace()