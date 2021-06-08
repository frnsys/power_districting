import os
from glob import glob
import colorcet as cc
import geopandas as gpd
from matplotlib.colors import ListedColormap
import matplotlib.pyplot as plt

cmap = ListedColormap(cc.glasbey_light)

def plot_partition(units, partition, name):
    ax = partition.plot(units, figsize=(20, 20), cmap=cmap)
    assignment = partition.assignment.to_series()
    df = gpd.GeoDataFrame(
        {'assignment': assignment}, geometry=units.geometry
    )
    districts = df.dissolve(by='assignment')
    districts['coords'] = [c[0] for c in districts.geometry.apply(lambda x: x.representative_point().coords[:])]
    for assignment, row in districts.iterrows():
        plt.annotate(
                s=assignment, xy=row['coords'],
                horizontalalignment='center', fontsize=2)
    plt.axis('off')
    path = 'data/gen/maps/{}.png'.format(name)
    plt.savefig(path, dpi=300)
    plt.close()
