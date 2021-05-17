from functools import partial
from gerrychain.proposals import recom
from gerrychain.accept import always_accept
from gerrychain import Graph, Partition, MarkovChain, constraints
from gerrychain.updaters import Tally, cut_edges
# import matplotlib.pyplot as plt

POP_COL = 'B01001e1'

graph = Graph.from_json('data/gen/graph.json')
initial_partition = Partition(
        graph,
        assignment='DISTRICT',

        # Calculate for each generated district map
        updaters={
            # Identifies boundary nodes
            "cut_edges": cut_edges,

            # Calculate district populations
            'population': Tally(POP_COL, alias='population'),
        }
)

# Plot initial districts
# initial_partition.plot(units, figsize=(10, 10), cmap="tab20")
# plt.axis('off')
# plt.show()

# District proposal method: ReCom
# For more on ReCom see <https://mggg.org/VA-report.pdf>
#   At each step, we (uniformly) randomly select a pair of adjacent districts and
#   merge all of their blocks in to a single unit. Then, we generate a spanning tree
#   for the blocks of the merged unit with the Kruskal/Karger algorithm. Finally,
#   we cut an edge of the tree at random, checking that this separates the region
#   into two new districts that are population balanced.
ideal_population = sum(initial_partition['population'].values()) / len(initial_partition)
proposal = partial(recom,
                   pop_col=POP_COL,
                   pop_target=ideal_population,
                   epsilon=0.02,
                   node_repeats=2)

# Compactness: bound the number of cut edges at 2 times the number of cut edges in the initial plan
compactness_bound = constraints.UpperBound(
    lambda p: len(p['cut_edges']),
    2*len(initial_partition['cut_edges'])
)

# Population
# This should be something like 0.01 but the initial districting fails to meet this criteria
# unless it's a higher value like 0.25
pop_constraint = constraints.within_percent_of_ideal_population(initial_partition, 0.25)

chain = MarkovChain(
    proposal=proposal,

    # Constraints: a list of predicates that return
    # whether or not a map is valid
    constraints=[
        compactness_bound,
        pop_constraint
    ],

    # Whether or not to accept a valid proposed map.
    # `always_accept` always accepts valid proposals
    accept=always_accept,

    # Initial state
    initial_state=initial_partition,

    # Number of valid maps to step through
    total_steps=1000
)

# Iterate over the proposals
for partition in chain:
    import ipdb; ipdb.set_trace()
    pass
    # print(sorted(partition["SEN12"].percents("Dem")))

import ipdb; ipdb.set_trace()