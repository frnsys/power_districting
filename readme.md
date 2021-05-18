## Usage

1. Run `gen_graph.py` to generate the district graph data.
    - Whenever you want to include different data in the initial graph, update `keep_layers` in that file, and re-run.
    - This produces `gen/graph.json`
2. Run `gen_districts.py` to generate districting proposals.

## Data

- `data/src/ny_legislative_boundaries`
    - NYS Legislative Boundaries (includes US Congressional, State Senate and State Assembly Districts in New York State)
    - url: <https://gis.ny.gov/gisdata/inventories/details.cfm?DSID=1360>
    - updated: February 2021
    - accessed: 5/17/2021
- `data/src/ACS_2018_5YR_TRACT_36_NEW_YORK.gdb`
    - Census tract geometries and demographic/economic data (2018, ACS 5 year estimates)
    - url: <https://www.census.gov/geographies/mapping-files/time-series/geo/tiger-data.html>
    - url: <https://www2.census.gov/geo/tiger/TIGER_DP/2018ACS/ACS_2018_5YR_TRACT_36.gdb.zip>
    - Metadata: <https://www2.census.gov/geo/tiger/TIGER_DP/2018ACS/Metadata/TRACT_METADATA_2018.txt>
    - accessed: 5/17/2021
- `data/src/2020_US_County_Level_Presidential_Results.csv`
    - url: <https://github.com/tonmcg/US_County_Level_Election_Results_08-20/blob/master/2020_US_County_Level_Presidential_Results.csv>
    - accessed: 5/18/2021
- `data/src/counties`
    - url: <https://www2.census.gov/geo/tiger/TIGER2020/COUNTY/>
    - accessed: 5/18/2021
- `data/src/electric_retail_service_territories`
    - url: <https://hifld-geoplatform.opendata.arcgis.com/datasets/c4fd0b01c2544a2f83440dab292f0980_0>
    - updated: 6/23/2020
    - accessed: 2/23/2021
    - source: Homeland Infrastructure Foundation Level Database, Oak Ridge National Laboratory (ORNL), Los Alamos National Laboratory (LANL), Idaho National Laboratory (INL), National Geospatial-Intelligence Agency (NGA) Homeland Security Infrastructure Program (HSIP) Team
- `data/src/infra/electric_substations`
    - url: <https://hifld-geoplatform.opendata.arcgis.com/datasets/electric-substations>
    - updated: 6/23/2020
    - accessed: 2/23/2021
    - source: Homeland Infrastructure Foundation Level Database, Oak Ridge National Laboratory (ORNL), Los Alamos National Laboratory (LANL), Idaho National Laboratory (INL), National Geospatial-Intelligence Agency (NGA) Homeland Security Infrastructure Program (HSIP) Team
- `data/src/infra/power_plants`
    - url: <https://hifld-geoplatform.opendata.arcgis.com/datasets/power-plants>
    - updated: 6/24/2020
    - accessed: 2/23/2021
    - source: Homeland Infrastructure Foundation Level Database, Oak Ridge National Laboratory (ORNL), Los Alamos National Laboratory (LANL), Idaho National Laboratory (INL), National Geospatial-Intelligence Agency (NGA) Homeland Security Infrastructure Program (HSIP) Team
- `data/src/electric_holding_company_areas`
    - url: <https://hifld-geoplatform.opendata.arcgis.com/datasets/electric-holding-company-areas>
    - updated: 6/24/2020
    - accessed: 2/23/2021
    - source: Homeland Infrastructure Foundation Level Database, Oak Ridge National Laboratory (ORNL), Los Alamos National Laboratory (LANL), Idaho National Laboratory (INL), National Geospatial-Intelligence Agency (NGA) Homeland Security Infrastructure Program (HSIP) Team

- Election/voting data:
    - <https://www.dailykos.com/stories/2013/07/09/1220127/-Daily-Kos-Elections-2012-election-results-by-congressional-and-legislative-districts>
    - <https://electionlab.mit.edu/data>
    - <https://libguides.princeton.edu/elections>
