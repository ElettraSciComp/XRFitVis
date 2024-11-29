import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap, LogNorm
import matplotlib
import matplotlib.ticker as ticker

import numpy as np
from skimage import exposure


def cstretch(img, val1, val2):
    #img = np.nan_to_num(img, nan=0)
    #print('cstretch', val1, val2)
    if val1 == 0:
        img_rescale = img
    else:
        p2, p98 = np.percentile(img, (val1, val2))
        #img_rescale = exposure.rescale_intensity(img, in_range=(p2, p98), out_range=(img.min(), img.max()))
        img_rescale = exposure.rescale_intensity(img, (p2, p98))
        img_rescale = img_rescale *(p98-p2) + p2
    return img_rescale

def mouse_position_to_grid(mouse_x, mouse_y, num_plots, rows, cols):

    cell_width = 1.0 / cols
    cell_height = 1.0 / rows

    mouse_col = int(mouse_x / cell_width)
    mouse_row = int(mouse_y / cell_height)

    mouse_col = min(mouse_col, cols - 1)
    mouse_row = min(mouse_row, rows - 1)

    plot_index = mouse_row * cols + mouse_col

    return mouse_row, mouse_col, plot_index

    

def reg_temperature():
    import pandas as pd
    cmap_file = 'temperature_PYMCA.cmap'
    cmap_name = 'temperature as PyMCA'
    df = pd.read_csv(cmap_file,sep=' ')
    df.columns = ['R','G','B']
    n_lines = np.shape(df)[0]
    cmap_list = [[df['R'][idx_line],df['G'][idx_line],df['B'][idx_line]] for idx_line in range(n_lines)]

    cmap = LinearSegmentedColormap.from_list(cmap_name, cmap_list, N=n_lines+1)
    #matplotlib.cm.register_cmap(name=cmap_name, cmap=cmap)
    matplotlib.colormaps.register(cmap, name=cmap_name)

reg_temperature()

def fmt_normal(x, pos):
    a, b = '{:.1e}'.format(x).split('e')
    b = int(b)
    if b == 0:
        return r'${}$'.format(a)
    if a == "1.0":
        return r'$ 10^{{{}}}$'.format(b)

    return r'${} \times 10^{{{}}}$'.format(a, b)


def fmt_log(x, pos):
    b = '{:.1f}'.format(x)
    return r'$\times 10^{{{}}}$'.format(b)
