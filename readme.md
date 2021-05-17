## Notes

TODO document:

- EJ data source
- Add additional constraints: crossover districts, EJ data
- Incorporate energy infrastructure as a constraint?

## Usage

1. Run `gen_graph.py` to generate the district graph data.
    - Whenever you want to include different data in the initial graph, update `keep_layers` in that file, and re-run.
    - This produces `gen/graph.json`
2. Run `gen_districts.py` to generate districting proposals.

## Data

- `data/src/ny_legislative_boundaries`
    - NYS Legislative Boundaries (includes US Congressional, State Senate and State Assembly Districts in New York State); Revised: February 2021
    - <https://gis.ny.gov/gisdata/inventories/details.cfm?DSID=1360>
- `data/src/ACS_2018_5YR_TRACT_36_NEW_YORK.gdb`
    - Census tract geometries and demographic/economic data (2018, ACS 5 year estimates)
    - <https://www.census.gov/geographies/mapping-files/time-series/geo/tiger-data.html>
    - <https://www2.census.gov/geo/tiger/TIGER_DP/2018ACS/ACS_2018_5YR_TRACT_36.gdb.zip>
    - Metadata: <https://www2.census.gov/geo/tiger/TIGER_DP/2018ACS/Metadata/TRACT_METADATA_2018.txt>
