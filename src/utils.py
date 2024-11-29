import os
from os.path import commonpath, normpath
import subprocess
import re

import numpy as np
import h5py
import csv
# Function to load data from a CSV file
def load_from_csv(filename):
    try:
        with open(filename, mode='r') as file:
            reader = csv.reader(file)
            # Skip the header
            next(reader)
            # Read the data into a list
            data_list = [row[0] for row in reader]
        return data_list
    except Exception as e:
        print(f"Error reading CSV: {e}")
        return []



def remove_common_path(paths):
    try:
        common_path = os.path.commonpath(paths) + '/'
        #common_path = os.path.normpath(common_path)
        return [p.replace(common_path, '') for p in paths]
    except:
        return paths



def load_images_from_hdf(path, loadthis):
    imgstack = []
    okdsets = []
    with h5py.File(path, 'r') as f:
        for cc in loadthis:
            try:
                if len(f[cc].shape) == 2 and f[cc].shape[-2] > 5 and f[cc].shape[-1] > 5:
                    imgstack.append(f[cc][()])
                    okdsets.append(cc)
                    #print('rawload', cc, f[cc].shape)
            except:
                pass
    return imgstack, okdsets


def execute_h5dump(filename):
    command = f"h5dump -n {filename}"
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    return result.stdout



def extract_dataset_paths(output):
    lines = output.split('\n')
    dsetnames = [re.search(r'\s*dataset\s*(.*)', line).group(1).strip()[1:] for line in lines if line.strip().startswith("dataset")]
    return dsetnames



def find_2d_dataset_paths(filename):
    output = execute_h5dump(filename)
    paths_to_2d_datasets = extract_dataset_paths(output)
    print('loading data')
    imgstack, filtereddsets = load_images_from_hdf(filename, paths_to_2d_datasets)

    print(filtereddsets)
    print('end loading')
    outdict = {}
    with h5py.File(filename, 'r') as f:

        if 1:
            if f.attrs['creator'] == 'pymca':
                print('pymca')
                for ff, ccimg in zip(filtereddsets, imgstack):
                    if 'results/parameters'in ff and '_errors' not in ff: # if f.attrs['creator'] == 'pymca':
                        outdict[ff.split('results/parameters/')[-1].replace("_"," ")] = np.nan_to_num(ccimg, nan=np.nanmin(ccimg), posinf=np.nanmax(ccimg), neginf=np.nanmin(ccimg))
            else:
                print('not pymca')
                #outdict = {ff:ccimg for ff, ccimg in zip(remove_common_path(filtereddsets), imgstack) if 'results/parameters'in ff and '_errors' not in ff}
                outdict = {ff:ccimg for ff, ccimg in zip(remove_common_path(filtereddsets), imgstack) if '_errors' not in ff} # era questo
                #outdict = {ff:np.nan_to_num(ccimg, nan=np.nanmin(ccimg), posinf=np.nanmax(ccimg), neginf=np.nanmin(ccimg)) for ff, ccimg in zip(filtereddsets, imgstack) if '_errors' not in ff}
        #except:
        #    pass

        if 0:
            #outdict = {ff:ccimg for ff, ccimg in zip(remove_common_path(filtereddsets), imgstack) if 'results/parameters'in ff and '_errors' not in ff}
            outdict = {ff:np.nan_to_num(ccimg, nan=np.nanmin(ccimg), posinf=np.nanmax(ccimg), neginf=np.nanmin(ccimg)) for ff, ccimg in zip(filtereddsets, imgstack) if '_errors' not in ff} ## interesting

        try:
            pymca = f.attrs['creator'] == 'pymca'
        except:
            pymca = False

    print(len(outdict.keys()), 'filtered dataset available of', len(filtereddsets))
    return outdict, pymca


def create_tree_structure(paths):
    tree_structure = []

    for path in paths:
        path_components = path.split('/')
        current_level = tree_structure
        parent_path = ''

        for component in path_components:
            parent_path = f"{parent_path}/{component}" if parent_path else component

            matching_nodes = [node for node in current_level if node['id'] == parent_path]

            if matching_nodes:
                current_node = matching_nodes[0]
            else:
                current_node = {'id': parent_path, 'children': [], 'path': parent_path}
                current_level.append(current_node)

            current_level = current_node['children']

    return tree_structure


