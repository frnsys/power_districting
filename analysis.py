import data
import numpy as np
import init_districts
import matplotlib.pyplot as plt
from mpl_toolkits.axes_grid1 import make_axes_locatable
from matplotlib.colors import TwoSlopeNorm, ListedColormap

min_cand = 'Teachout'
maj_cand = 'Cuomo'

# Normalize so colormap center is at 0
def normalized_cmap(data, cmap):
    vmin, vmax, vcenter = data.min(), data.max(), 0
    if vmax <= 0: vmax = 1.
    if vmin >= 0: vmin = -1.
    norm = TwoSlopeNorm(vmin=vmin, vcenter=vcenter, vmax=vmax)
    cbar = plt.cm.ScalarMappable(norm=norm, cmap=cmap)
    return cbar, norm

def district_info(group):
    teachout_votes = group[min_cand].sum()
    cuomo_votes = group[maj_cand].sum()
    group['min_district_win'] = teachout_votes > cuomo_votes
    group['min_district_diff'] = teachout_votes - cuomo_votes
    return group

cmap = 'RdYlGn'
bin_cmap = ListedColormap(['#585858', '#008066'])
# legend_kwds={'orientation': 'horizontal'}
legend_kwds={'orientation': 'vertical', 'shrink': 0.3}

units = data.load_tracts(geom_only=False)
units['assignment'] = init_districts.state_assembly(units)
units['min_district_win'] = False
units['min_district_diff'] = 0
units = units.groupby('assignment').apply(district_info)
units['min_win'] = units[min_cand] > units[maj_cand]
units['min_diff'] = units[min_cand] - units[maj_cand]
units['min_diff_p'] = (units[min_cand] - units[maj_cand])/(units[min_cand] + units[maj_cand])
units['ej_class_min'] = units['EJ_Class'] >= 3

units['ej_class_min_diff'] = np.nan
units['ej_class_min_diff'].mask(units['EJ_Class'] >= 3, other=units[min_cand] - units[maj_cand], inplace=True)

assembly_districts = data.load_districts()
assembly_districts = assembly_districts.to_crs(units.crs)


def gen_plots(bounds, name):
    xmin, ymin, xmax, ymax = bounds
    df = units.cx[xmin:xmax, ymin:ymax]
    districts = assembly_districts.cx[xmin:xmax, ymin:ymax]

    fig, axes = plt.subplots(3, 3, figsize=(30, 30))
    fig.suptitle(name, fontsize=28)
    axes = axes.flatten()

    def plot(title, col, ax, cmap, center_cmap=False):
        kwargs ={}
        if center_cmap:
            cbar, norm = normalized_cmap(df[col], cmap)
            kwargs['norm'] = norm
        else:
            kwargs['legend_kwds'] = legend_kwds

        kwargs['missing_kwds'] = {
            "color": "lightgrey",
            # "hatch": "///",
            # "label": "Missing values",
        }

        ax.set_title(title)
        df.plot(column=col, ax=ax, cmap=cmap, legend=not center_cmap, **kwargs)
        districts.boundary.plot(ax=ax, edgecolor='black', linewidth=0.25)

        if center_cmap:
            fig.colorbar(cbar, ax=ax, **legend_kwds)

    plot('{} win'.format(min_cand), 'min_win', axes[0], bin_cmap)
    plot('{}-{} diff (absolute)'.format(min_cand, maj_cand), 'min_diff', axes[1], cmap, center_cmap=True)
    plot('{}-{} diff (percent)'.format(min_cand, maj_cand), 'min_diff_p', axes[2], cmap, center_cmap=True)

    plot('District {} win'.format(min_cand), 'min_district_win', axes[3], bin_cmap)
    plot('District {} diff (absolute)'.format(min_cand), 'min_district_diff', axes[4], cmap, center_cmap=True)
    plot('Population', 'population', axes[5], 'summer')

    plot('EJ Class', 'EJ_Class', axes[6], 'summer')
    plot('EJ Class minority', 'ej_class_min', axes[7], bin_cmap)
    plot('{} diff (absolute) in EJ Class minority'.format(min_cand), 'ej_class_min_diff', axes[8], cmap, center_cmap=True)

    plt.tight_layout()
    fig.savefig('data/gen/map_analysis__{}.png'.format(name), dpi=300)
    # plt.show()
    plt.close()


if __name__ == '__main__':
    xmin, ymin, xmax, ymax = units.total_bounds
    gen_plots((xmin, ymin, xmax, ymax), 'all')
    gen_plots((550000, ymin, xmax, 4.55e6), 'nyc')
    gen_plots((xmin, 4.65e6, 250000, 4.85e6), 'west')