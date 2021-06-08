import pandas as pd

with open('data/src/2014StateLocalPrimaryElectionResults.txt', 'r') as f:
    d = f.read().split('\n')

candidates = d[1], d[2], d[3]
counties = {}
for i in range(4, len(d), 4):
    county_name = d[i]
    counties[county_name] = {}
    for j, cand in enumerate(candidates):
        counties[county_name][cand] = int(d[i + j + 1].replace(',', ''))
df = pd.DataFrame(counties).T
df.to_csv('data/gen/2014_state_primary.csv')