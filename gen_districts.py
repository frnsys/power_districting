import data
import cProfile
import numpy as np
import init_districts
from plot import plot_partition
from collections import defaultdict
from gerrychain.updaters import Tally, cut_edges
from gerrychain import Graph, Partition, constraints
from search import hill_climbing

# EJ scores >= are considered "minority"
# for the purpose of scoring a districting plan
EJ_CUTOFF = 3
MIN_CANDIDATE = 'Teachout'
MAJ_CANDIDATE = 'Cuomo'
CROSSOVER_MIN_MINORITY_PERCENT = 0.25

# Geometry for plotting
units = data.load_tracts(geom_only=True)

# Load generated graph
graph = Graph.from_json('data/gen/graph.json')

# Create initial district assignment
# assignment = init_districts.service_territories(units)
assignment = init_districts.state_assembly(units)
for n in graph.nodes:
    graph.nodes[n]['DISTRICT'] = assignment[n]
n_districts = len(set(assignment))
print('Districts:', n_districts)

# Updaters
def _pop_weighted_mean(partition, key):
    data = {}
    for part in partition.parts:
        total_pop = partition['population'][part]
        nodes = [partition.graph.nodes[n] for n in partition.parts[part]]
        vals = [n[key] * n['population'] for n in nodes]
        data[part] = sum(vals)/total_pop
    return data

def _mean(partition, key):
    data = {}
    for part in partition.parts:
        nodes = [partition.graph.nodes[n] for n in partition.parts[part]]
        vals = [n[key] for n in nodes]
        data[part] = sum(vals)/len(vals)
    return data

# Calculate population-weighted mean EJ class
def mean_ej_class(partition):
    return _pop_weighted_mean(partition, 'EJ_Class')

def mean_wind_class(partition):
    return _mean(partition, 'Wind_Class')

def mean_solar_class(partition):
    return _mean(partition, 'Solar_Class')

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

def ej_class_crossover_district(partition):
    is_crossover = {}
    # min_percent = partition['ej_class_minority_percent']
    for part in partition.parts:
        # if min_percent[part] < CROSSOVER_MIN_MINORITY_PERCENT:
        #     is_crossover[part] = False
        #     continue
        nodes = [partition.graph.nodes[n] for n in partition.parts[part]]
        min_cand_total, maj_cand_total = district_votes(nodes)
        is_crossover[part] = min_cand_total > maj_cand_total
    return is_crossover


def district_votes(nodes):
    minority_votes = {'min_cand': 0, 'maj_cand': 0}
    majority_votes = {'min_cand': 0, 'maj_cand': 0}
    for n in nodes:
        if n['EJ_Class'] >= EJ_CUTOFF:
            minority_votes['min_cand'] += n[MIN_CANDIDATE]
            minority_votes['maj_cand'] += n[MAJ_CANDIDATE]
        else:
            majority_votes['min_cand'] += n[MIN_CANDIDATE]
            majority_votes['maj_cand'] += n[MAJ_CANDIDATE]

    min_cand_total = minority_votes['min_cand'] + majority_votes['min_cand']
    maj_cand_total = minority_votes['maj_cand'] + majority_votes['maj_cand']
    return min_cand_total, maj_cand_total


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

        'votes_min': Tally(MIN_CANDIDATE, alias='votes_min'),
        'votes_maj': Tally(MAJ_CANDIDATE, alias='votes_maj'),

        'mean_ej_class': mean_ej_class,
        'ej_classes': ej_classes,
        'ej_class_minority_percent': ej_class_minority_percent,
        'ej_class_majority_minority': ej_class_majority_minority,
        'ej_class_crossover_district': ej_class_crossover_district,

        'mean_wind_class': mean_wind_class,
        'mean_solar_class': mean_solar_class,
        'power_plants': count_power_plants,
    }
)

# Compactness: bound the number of cut edges at 2 times the number of cut edges in the initial plan
compactness_bound = constraints.UpperBound(
    lambda p: len(p['cut_edges']),
    2*len(initial_partition['cut_edges'])
)

def succ_func(partition):
    # Based on `propose_random_flip`
    if len(partition['cut_edges']) == 0:
        return []

    succs = []
    all_district_votes = {part_id: district_votes([partition.graph.nodes[n] for n in node_ids]) for part_id, node_ids in partition.parts.items()}
    for edge in partition['cut_edges']:
        for index in [0, 1]:
            flipped_node_idx, other_node_idx = edge[index], edge[1 - index]
            flipped_node = partition.graph.nodes[flipped_node_idx]
            prev_assignment = flipped_node['DISTRICT']
            next_assignment = partition.assignment[other_node_idx]

            # Recalculate
            # crossover_count = sum(is_crossover_districts.values())
            scores = []
            for part_id in partition.parts.keys():
                if part_id == prev_assignment:
                    nodes = [partition.graph.nodes[n] for n in set(partition.parts[prev_assignment]) - {flipped_node_idx}]
                    min_vote, maj_vote = district_votes(nodes)
                elif part_id == next_assignment:
                    nodes = [partition.graph.nodes[n] for n in set(partition.parts[next_assignment]).union({flipped_node_idx})]
                    min_vote, maj_vote = district_votes(nodes)
                else:
                    min_vote, maj_vote = all_district_votes[part_id]
                scores.append(_score(min_vote, maj_vote))
            score = np.mean(scores)
            # prev_district = [partition.graph.nodes[n] for n in set(partition.parts[prev_assignment]) - {flipped_node_idx}]
            # prev_is_now_crossover = is_crossover_district(prev_district)
            # next_district = [partition.graph.nodes[n] for n in set(partition.parts[next_assignment]).union({flipped_node_idx})]
            # next_is_now_crossover = is_crossover_district(next_district)
            # if is_crossover_districts[prev_assignment] != prev_is_now_crossover:
            #     crossover_count += 1 if prev_is_now_crossover else -1
            # if is_crossover_districts[next_assignment] != next_is_now_crossover:
            #     crossover_count += 1 if next_is_now_crossover else -1
            # score = crossover_count/n_districts

            flip = {flipped_node_idx: next_assignment}
            p = partition.flip(flip)
            succs.append((p, score))
    # succs.sort(key=lambda x: x[1], reverse=True) # sorted in hill climber
    return succs

def goal_func(partition):
    p_crossover_districts = sum(1 for d in partition['ej_class_crossover_district'].values() if d)/n_districts
    return p_crossover_districts > 0.9

def _score(min_vote, maj_vote):
    return min(min_vote/(min_vote+maj_vote), 0.5)

def score_func(partition):
    all_district_votes = {part_id: district_votes([partition.graph.nodes[n] for n in node_ids]) for part_id, node_ids in partition.parts.items()}
    # score = sum(_score(min_vote, maj_vote) for min_vote, maj_vote in all_district_votes.values())
    score = np.mean([_score(min_vote, maj_vote) for min_vote, maj_vote in all_district_votes.values()])
    return score

def hash_func(partition):
    return hash(frozenset(partition.assignment.items()))

ref = data.load_districts()
# ref = data.load_service_territories(geom_only=False)
def summarize(partition, partition_name):
    print(partition_name)
    lines = []
    for id, nodes in initial_partition.parts.items():
        # name = ref.loc[id]['NAME'] # service territories
        name = 'District {}'.format(ref.loc[id]['DISTRICT']) # state assembly districts
        lines.append(name)
        lines.append('  Tracts: %s' % len(nodes))
        lines.append('  Population: %s' % initial_partition['population'][id])
        lines.append('  Mean EJ Class: %s' % initial_partition['mean_ej_class'][id])
        lines.append('  EJ Class Minority Percent: %s' % initial_partition['ej_class_minority_percent'][id])
        # lines.append('  EJ Class Crossover District: %s' % initial_partition['ej_class_crossover_district'][id])
        lines.append('  Mean Wind Class: %s' % initial_partition['mean_wind_class'][id])
        lines.append('  Mean Solar Class: %s' % initial_partition['mean_solar_class'][id])
        lines.append('  Power Plants: %s' % initial_partition['power_plants'][id])
    with open('data/gen/{}_districts_summary.txt'.format(partition_name), 'w') as f:
        f.write('\n'.join(lines))
    for line in lines: print(line)

print('Plotting initial partitions...')
plot_partition(units, initial_partition, 'initial')
summarize(initial_partition, 'initial')

print('Searching for a districting plan that satisfies criteria...')
best_partition = hill_climbing(
        initial_partition,
        succ_func,
        goal_func,
        score_func,
        max_depth=1000,
        hash_func=hash_func)

import ipdb; ipdb.set_trace()

# Plot maps
print('Generating maps...')
plot_partition(units, best_partition, 'best')
summarize(best_partition, 'best')

import ipdb; ipdb.set_trace()

# print('% crossover districts:', sum(1 for d in partition['ej_class_crossover_district'].values() if d)/n_districts)
# print('% majority-minority:', sum(1 for d in partition['ej_class_majority_minority'].values() if d)/n_districts)