import networkx as nx
import geopandas as gpd
import matplotlib.pyplot as plt
from collections import defaultdict
from gerrychain import Graph
from tqdm import tqdm

# Parameters
# ==============================

# How many districts to generate
N_DISTRICTS = 25

# How far seed tracts must be apart, at minimum
MIN_SEED_DISTANCE = 10

# Tracts with EJ >= EJ_MINORITY_CUTOFF
# are considered "minority"
EJ_MINORITY_CUTOFF = 3

# The minority vote wins if
# CROSSOVER_PERCENT of majority voters crossover
CROSSOVER_PERCENT = 0.2

# Load generated graph
graph = Graph.from_json('data/gen/graph.json')

TractId = int
District = tuple[TractId, list[TractId]]

tracts_file = 'data/src/ACS_2018_5YR_TRACT_36_NEW_YORK.gdb'
geo_layer = 'ACS_2018_5YR_TRACT_36_NEW_YORK'
tracts_geo = gpd.read_file(tracts_file, layer=geo_layer)
tracts_geo.set_index('GEOID', inplace=True)
tracts_geo['Label'] = 'Unassigned'

color_mapping = {
    'Unassigned': '#eeeeee',
    'Seed': '#ff0000',
}
district_colors = [
    '#5E4FA2',
    '#54AEAD',
    '#BFE5A0',
    '#FFFFBD',
    '#FDBF6F',
    '#E85C47',
    '#9D0041'
]
for i in range(N_DISTRICTS):
    idx = i % len(district_colors)
    color_mapping['District {}'.format(i)] = district_colors[idx]

distances = defaultdict(dict)

def get_distance(source, target) -> int:
    dist = distances.get(source, {}).get(target)
    if dist is None:
        path = nx.shortest_path(graph, source=source, target=target)
        dist = len(path)
        distances[source][target] = dist
        distances[target][source] = dist
    return dist

def select_seeds():
    pbar = tqdm(total=N_DISTRICTS, desc='Finding seeds')
    node_ids = list(graph.nodes)

    # Sort by EJ class, high to low
    node_ids.sort(key=lambda id: -graph.nodes[id]['EJ_Class'])

    seeds = [node_ids.pop(0)]
    pbar.update(1)

    while len(seeds) < N_DISTRICTS and node_ids:
        node_id = node_ids.pop(0)
        dists = [get_distance(seed, node_id) for seed in seeds]
        if all(dist >= MIN_SEED_DISTANCE for dist in dists):
            seeds.append(node_id)
            pbar.update(1)

    return seeds

def is_minority(tract) -> bool:
    return tract['EJ_Class'] >= EJ_MINORITY_CUTOFF

def vote_fn(tract_id: TractId) -> tuple[float, float]:
    """Return the minority and majority candidate votes
    for a given tract. The naive version of this assumes
    all minority voters vote for the minority candidate and
    all majority voters vote for the majority candidate.
    We then incorporate the desired crossover amount to give
    a majority for the minority candidate.
    Ideally you would use real election data to
    reflect actual voting patterns, but we were unable to
    find adequately detailed data.
    """
    tract = graph.nodes[tract_id]
    pop = tract['population']
    if is_minority(tract):
        maj_vote = 0
        min_vote = pop
    else:
        maj_vote = (1-CROSSOVER_PERCENT) * pop
        min_vote = CROSSOVER_PERCENT * pop
    return min_vote, maj_vote

def get_candidates(district: District, unclaimed: set[TractId]) -> list[TractId]:
    """Get candidate tracts for a district.
    These tracts are adjacent to the existing district
    that are closest to the seed tract (to ensure compactness)."""
    seed, tract_ids = district
    neighbors = set()
    for tract_id in tract_ids:
        for neighb in graph.neighbors(tract_id):
            if neighb not in tract_ids and neighb in unclaimed:
                neighbors.add(neighb)

    dists = []
    for neighb in neighbors:
        dist = get_distance(seed, neighb)
        dists.append(dist)

    return [neighb for dist, neighb
            in zip(dists, neighbors)
            if dist >= min(dists)]

def district_votes(district: District) -> tuple[float, float]:
    _, tract_ids = district
    min_votes, maj_votes = 0, 0
    for tract_id in tract_ids:
        min_vote, maj_vote = vote_fn(tract_id)
        min_votes += min_vote
        maj_votes += maj_vote
    return min_votes, maj_votes

def district_pop(district: District) -> tuple[float, float]:
    _, tract_ids = district
    min_pop, maj_pop = 0, 0
    for tract_id in tract_ids:
        tract = graph.nodes[tract_id]
        pop = tract['population']
        if is_minority(tract):
            min_pop += pop
        else:
            maj_pop += pop
    return min_pop, maj_pop

def score_district(district: District) -> float:
    """Score a district based on the desired
    crossover amount"""
    min_votes, maj_votes = district_votes(district)

    # Ideal is that min_votes == maj_votes,
    # i.e. with the specified majority crossover
    # minority and majority voters are on equal footing
    diff = abs(min_votes - maj_votes) + 1 # To prevent 0 division
    return 1/diff

def greedy_search(seeds):
    districts = [(seed, [seed]) for seed in seeds]
    saturated = set()
    unclaimed = set(node_id for node_id in list(graph.nodes) if node_id not in seeds)
    pbar = tqdm(total=len(unclaimed), desc='Forming districts')
    while unclaimed:
        for district in districts:
            seed, tract_ids = district
            if seed in saturated: continue
            cands = get_candidates(district, unclaimed)
            if not cands: # Can happen if the district is surrounded on all sides
                saturated.add(seed)
                continue
            best_cand = max(cands, key=lambda cand: score_district((seed, tract_ids + [cand])))
            tract_ids.append(best_cand)
            unclaimed.remove(best_cand)
            pbar.update(1)
    return districts

if __name__ == '__main__':
    print('Parameters:')
    print('  {} districts'.format(N_DISTRICTS))
    print('  Seeded at least {} tracts apart'.format(MIN_SEED_DISTANCE))
    print('  Tracts with EJ class >= {} considered "minority"'.format(EJ_MINORITY_CUTOFF))
    print('  Crossover {}% of majority votes to minority side'.format(CROSSOVER_PERCENT*100))

    seeds = select_seeds()
    for seed in seeds:
        tract = graph.nodes[seed]
        tracts_geo.loc[tract['GEOID'], 'Label'] = 'Seed'
    assert len(seeds) == N_DISTRICTS

    districts = greedy_search(seeds)
    print('                      AbsDiff PctDiff  PctMin')
    for i, district in enumerate(districts):
        min_votes, maj_votes = district_votes(district)
        diff = min_votes - maj_votes
        lead = '✅MIN' if diff >= 0 else '❌MAJ'
        min_pop, maj_pop = district_pop(district)
        p_min_pop = min_pop/(min_pop+maj_pop)
        print('District {:2}: {} {:10,} {:6.1f}% {:6.1f}% {}'.format(
            i, lead,
            abs(round(diff)),
            abs(round(diff))/(min_pop+maj_pop) * 100,
            p_min_pop * 100,
            'X-OVER' if p_min_pop < 0.5 and diff >= 0 else '',
        ))

    for i, (_, tract_ids) in enumerate(districts):
        for tract_id in tract_ids[1:]: # First id is seed
            tract = graph.nodes[tract_id]
            tracts_geo.loc[tract['GEOID'], 'Label'] = 'District {}'.format(i)

    tracts_geo.plot(color=tracts_geo['Label'].map(color_mapping))
    plt.savefig('districts.png', dpi=300)
    plt.show()
    plt.close()