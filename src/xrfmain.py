import datetime as dt
old_printf = print
def print(*msg): # print also on file
    message = []
    for m in msg:
        message.append(str(m))
    message = ' '.join(message)
    # append to the log file
    with open('/tmp/xrfvis.log','a') as log:
        log.write(f'{dt.datetime.now()} | {message}\n')
    old_printf(message)

import os
import time
import tempfile
import asyncio

import numpy as np
import tifffile as tf

from nicegui import ui, app, events, Client

import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

import xml.etree.ElementTree as ET

from filepick import FilePicker
from plotutils import reg_temperature, fmt_normal, fmt_log, mouse_position_to_grid, cstretch
from utils import find_2d_dataset_paths, sort_img_entropy, create_tree_structure, remove_common_path

import requests
import urllib

import pickle
from copy import deepcopy
import ast

FONT_STYLE = "font-size: 200%; font-weight: bold"
INPUT_EXT = ["hdf", "nxs", "h5", "hdf5"]
CMAP_LIST = ["temperature as PyMCA", "gray", "inferno", "afmhot", "viridis", "magma", "jet"]

VERSION="28112024"

class_members_exports = list(set(['colorbarspacing', 'colorbarfraction', 'denoisemethod', 'tree_data_dict', 'choosed_dataset_raw', 'choosed_dataset_short', 'datadict', 'choosed_colormap', 'logchecked', 'fliplrall', 'flipudall', 'plotticks', 'readytosave', 'num_images', 'rows', 'cols', 'pymca', 'labelsize', 'caliblabelsize', 'minrow', 'mincol', 'maxrow', 'maxcol', 'colorbarticksnum', 'horizcolorbar', 'wspace', 'hspace', 'minmaxtable']))


from skimage.restoration import denoise_tv_chambolle, denoise_bilateral, denoise_wavelet, estimate_sigma, denoise_nl_means, denoise_tv_bregman

class TheGui:

    def __init__(self, email=None, investigationlist=[], limitpathlow='/tmp/', currinvestigation=None):
        self.path = None
        self.choosed_dataset_raw, self.choosed_dataset_short = [], [] #enabled_dataset()
        self.mainplot = None
        self.datadict = {}
        self.dataloaded = False
        self.choosed_colormap = 'temperature as PyMCA'
        self.logchecked = False
        self.denoisemethod = "Not Enabled"
        self.fliplrall, self.flipudall = False, False
        self.plotticks = False
        self.treesel_gui, self.treecontainer_gui, self.tree_display_gui = None, None, None
        self.tree_data_dict = []
        self.readytosave = False

        self.pickle_file_path = None

        self.num_images, self.rows, self.cols = 0,0,0
        self.pymca = False
        self.labelsize, self.caliblabelsize = 20, 20
        self.minrow, self.mincol = 0,0
        self.maxrow, self.maxcol = 1,1
        self.email = email
        self.investigationlist = investigationlist
        self.limitpathlow = limitpathlow
        self.enable_remotefile = self.limitpathlow != '/tmp/'
        print('CURRENTINVESTIGATION', currinvestigation)
        self.currinvestigation = currinvestigation
        self.enable_localfile = not self.enable_remotefile
        #print(self.limitpathlow, self.enable_remotefile)
        self.colorbarticksnum = 5
        self.horizcolorbar = False
        #self.subplotpad = .3
        self.wspace, self.hspace = .3, .3
        self.minmaxtable = []
        self.autoscalestrategy = "Min/Max"
        self.colorbarfraction = 0.046 *1000.
        self.colorbarspacing = 0.02 * 1000
        self.gain = 1.0
        self.aspectratio = 1.0
        print(f"init done User:{self.email} User investigations:{self.investigationlist} CurrentPath: {self.limitpathlow}")


    async def handle_upload(self, e: events.UploadEventArguments):
        content = e.content.read()
        tempdir = tempfile.TemporaryDirectory(dir='/tmp/')
        outname = f"{tempdir.name}/{e.name}"

        print('start writing')
        with open(outname, 'wb') as f:
            f.write(content)
        self.path = outname
        print('done writing')
        await self.load_data()
        print('cleanup tmpdir')
        tempdir.cleanup()


    async def checkwhatenabled(self, e):
        self.choosed_dataset_short = e.value
        #print(self.choosed_dataset_short)
        self.num_images = len(self.choosed_dataset_short)
        if self.num_images > 0:
            self.cols = int(np.ceil(np.sqrt(self.num_images)))
            self.rows = int(np.ceil(self.num_images / self.cols))
        await self.update_graph()

        print(f"checkwhatenabled: {self.treesel_gui.__dict__}")


    async def pick_file_demo(self) -> None:
        """To pick a file when click the button 'Select file' """
        self.path = await FilePicker(directory="../sample_data/", upper_limit="../sample_data/", allowed_extensions=INPUT_EXT)
        await self.load_data()


    async def load_data(self):
        self.datadict, self.pymca = find_2d_dataset_paths(self.path)
        #print(self.pymca)
        if self.pymca:
            allk = list(self.datadict.keys())

            scatterdata = 0.0
            for kk in allk:
                if 'Scatter '.lower() in kk.lower():
                    scatterdata = self.datadict.pop(kk) + scatterdata
                    #removethis = kk.split('/')[-1]
                    #print(removethis)
            if not isinstance(scatterdata, float):
                self.datadict['Scattering'] = scatterdata

        kk = list(self.datadict.keys())[0]
        self.maxrow, self.maxcol = self.datadict[kk].shape ## TO BE FIXED FOR EACH IMAGE, now common
        self.rowend_gui.max, self.colend_gui.max = self.maxrow, self.maxcol

        await self.update_available_hdfdatasets()
        if len(self.datadict.keys()) > 0:
            ui.notify(f"Loaded {os.path.basename(self.path)}", close_button="OK", type='positive')
        else:
            ui.notify(f"No 2D Maps in {os.path.basename(self.path)}", close_button="OK", type='negative')
        self.titlelabel.set_content(f'Filename: <b>{os.path.basename(self.path)}</b>')
        #self.plot_options = {}
        self.treecontainer_gui.open()



    async def update_available_hdfdatasets(self):
        # set the available dataset in the ui select
        self.dataloaded = True
        self.tree_data_dict = create_tree_structure(list(self.datadict.keys()))
        print(f"update_available_hdfdatasets: {self.tree_data_dict=}")
        self.updatetree()
        self.choosed_dataset_short = []
        await self.logchanged()


    async def savefig(self):
        with self.main_plot:
            tempdir = tempfile.TemporaryDirectory(dir='/tmp/')
            outname = f"{tempdir.name}/plot_{os.path.basename(self.path).split('.')[0]}.png"
            plt.savefig(outname, dpi=600,  bbox_inches='tight', pad_inches=0)
            ui.download(outname)
            await asyncio.sleep(1)
            tempdir.cleanup()
        ui.notify(f'Saved {os.path.basename(outname)}', close_button="OK", type='positive')


    async def exportrawmaps(self):
        with self.main_plot:
            print('preparing file')
            titles = remove_common_path(self.choosed_dataset_short) if self.num_images > 1 else [os.path.basename(self.choosed_dataset_short[0])]
            alltitles_tmp, tmp_data_export = [], []
            for ii, (tt,kk) in enumerate(zip(titles, self.choosed_dataset_short)):
                alltitles_tmp.append(tt)
                tmp_data_export.append(self.datadict[kk])
            tmp_data_export = np.asarray(tmp_data_export).astype(np.float32)
            tempdir = tempfile.TemporaryDirectory(dir='/tmp/')
            outname = f"{tempdir.name}/plot_{os.path.basename(self.path).split('.')[0]}.tiff"
            tf.imwrite(outname,  tmp_data_export, metadata={"axes": "CYX", "Labels": [f"{tt}" for tt in alltitles_tmp]}, imagej=True)

            ui.download(outname)
            await asyncio.sleep(1)
            tempdir.cleanup()
        ui.notify(f'Saved {os.path.basename(outname)}', close_button="OK", type='positive')


    # on change self.sel_dataset_gui
    async def update_graph(self):
        t0 = time.time()
        if self.dataloaded:
            if self.num_images > 0:
                self.readytosave = True
                titles = remove_common_path(self.choosed_dataset_short) if self.num_images > 1 else [os.path.basename(self.choosed_dataset_short[0])]

                with self.main_plot:
                    plt.clf(); plt.gcf().set_figwidth(4*self.cols); plt.gcf().set_figheight(4*self.rows)

                    for ii, (tt,kk) in enumerate(zip(titles, self.choosed_dataset_short)):
                        plt.subplot(self.rows,self.cols,ii+1)

                        origcrop = self.datadict[kk][int(self.minrow):int(self.maxrow), int(self.mincol):int(self.maxcol)]
                        tmpimg = origcrop.copy() * self.gain

                        tmpimg = np.fliplr(tmpimg) if self.fliplrall else tmpimg
                        tmpimg = np.flipud(tmpimg) if self.flipudall else tmpimg

                        name_indices = {entry['name']: idx for idx, entry in enumerate(self.minmaxtable)}
                        ccidx = name_indices.get(tt)
                        #ccidx = name_indices.get(self.choosed_dataset_short[ii]) ## interesting
                        cmin, cmax = self.minmaxtable[ccidx]['min']*self.gain, self.minmaxtable[ccidx]['max']*self.gain

                        if self.logchecked: tmpimg = np.log10(tmpimg+1)

                        match self.denoisemethod:
                            case "Not Enabled":
                                print(self.denoisemethod)
                                pass
                            case "denoise_tv_chambolle":
                                print('denoise_tv_chambolle')
                                tmpimg = denoise_tv_chambolle(tmpimg, weight=5.)
                            case "denoise_wavelet":
                                print("denoise_wavelet")
                                tmpimg = denoise_wavelet(tmpimg, rescale_sigma=True,  wavelet='bior4.4', mode='soft')
                            case "denoise_bilateral":
                                print('denoise_bilateral')
                                tmpimg = denoise_bilateral(tmpimg, mode='symmetric', sigma_spatial=.5)
                            case "denoise_nl_means":
                                print('denoise_nl_means')
                                tmpimg = denoise_nl_means(tmpimg, patch_size=3)
                            case "denoise_tv_bregman":
                                print('denoise_tv_bregman')
                                tmpimg = denoise_tv_bregman(tmpimg, weight=.1, isotropic=False)
                            case _:
                                print(self.denoisemethod)
                                print('degfault')
                                pass

                        plt.imshow(tmpimg,  cmap=self.choosed_colormap, interpolation='nearest', aspect=self.aspectratio, vmin=cmin, vmax=cmax)
                        cbar = plt.colorbar(format=ticker.FuncFormatter(fmt_log) if self.logchecked else ticker.FuncFormatter(fmt_normal), fraction=self.colorbarfraction/1000, location='bottom' if self.horizcolorbar else 'right', pad=self.colorbarspacing/1000.)

                        # Calculate tick positions
                        tick_positions = np.linspace(cmin, cmax, int(self.colorbarticksnum))
                        cbar.set_ticks(tick_positions)
                        cbar.ax.tick_params(labelsize=self.caliblabelsize)

                        plt.title(tt, fontsize=self.labelsize)

                        if not self.plotticks: plt.xticks([]); plt.yticks([]) #plt.axis('off')
                    plt.tight_layout(h_pad=self.hspace, w_pad=self.wspace, pad=0.0)

            else:
                self.readytosave = False # disable the save button
                with self.main_plot:
                    plt.clf()
            self.main_plot.update()

        t1 = time.time()
        print(f'Rendering in {t1-t0} s')



    async def logchanged(self):
        self.minmaxtable[:] = []
        elnames = list(self.datadict.keys())
        print(f"logchanged: {elnames=}")
        print(f"logchanged: {self.logchecked=}")
        for ii,tt in enumerate(elnames):
            tmpimg = np.log10(self.datadict[tt]+1) if self.logchecked else self.datadict[tt]
            p2, p98 = np.percentile(tmpimg, (1, 99)) if self.autoscalestrategy == 'Std' else [tmpimg.min(), tmpimg.max()]
            self.minmaxtable.append({"id":ii, "name":tt, "min":p2, "max":p98})

        self.tablegui.update()
        await self.update_graph()


    def updatetree(self):
        self.treecontainer_gui.remove(self.tree_display_gui)
        with self.treecontainer_gui:
            self.tree_display_gui = ui.card().classes('w-full')
            with self.tree_display_gui:
                #ui.label('Datasets:')
                self.treesel_gui = ui.tree(self.tree_data_dict, label_key='id', tick_strategy='leaf', on_tick=lambda e: self.checkwhatenabled(e))



    def initgui(self):
        # ui.add_head_html('''<link rel="stylesheet" type="text/css" href="./style/general.css">''')
        ui.add_css('''main .nicegui-content{
                        padding-top: 0px;
                        padding-bottom: 0px;
                    }

                    main .q-uploader{
                        width:100%
                    }

                   @media (min-width: 1200px) {
                   
                   }

                   ''')
        with ui.row().style("width:100%;heigth:100%;flex-wrap: nowrap;gap: 0px;"): # main container
            with ui.column().classes('col-4 col-lg-3 col-xxl-2').style("heigth:100%;").style("height: 100vh;padding-right:1rem;overflow:auto;display:block"):
                with ui.card().classes('w-full').style("margin-top:1rem;"): # logo and title
                    with ui.row():
                        with ui.column():
                            ui.image('https://avatars.githubusercontent.com/u/15228664?v=4').classes('w-24')
                            ui.label(f"v{VERSION}")
                        with ui.column():
                            ui.label('XRFitVis Pro').style("color: #3874c8; " + FONT_STYLE)

                            self.titlelabel = ui.html('').style("color: #000000")
                            self.titlelabel.bind_visibility_from(self, "dataloaded")
                    with ui.tabs()as tabs: #.classes('w-full') as tabs: # file loader
                        two = ui.tab('Local File')#.classes('w-full')
                        one = ui.tab('Remote File')#.classes('w-full')
                        three = ui.tab('Demo Files')#.classes('w-full')
                        one.set_visibility(self.enable_remotefile)
                    with ui.tab_panels(tabs, value=two).classes("w-full").style('align-items: center;') as tabpanels:
                        self.remotefiletab = ui.tab_panel(one).style('align-items: center;')
                        self.localfiletab = ui.tab_panel(two).style('align-items: center;')
                        self.demofiletab = ui.tab_panel(three).style('align-items: center;')
                        self.remotefiletab.bind_visibility_from(self,  "enable_remotefile")

                        with self.remotefiletab:
                            if self.currinvestigation is not None:
                                ui.html(f'Browse for a remote HDF5 file in investigation:  <b>{self.currinvestigation} </b>').style("color: #000000")
                            self.pickfilebutton_gui = ui.button('Pick Remote File', on_click=self.pick_file_demo).classes('w-full')

                        with self.demofiletab:
                            ui.html(f'Browse for a remote HDF5 file in investigation:  <b> DEMO </b>').style("color: #000000")
                            self.pickfilebutton_gui_demo = ui.button('Pick DEMO File', on_click=self.pick_file_demo).classes('w-full')

                        self.tabpanels = tabpanels
                        with self.localfiletab:
                            ui.label('Choose a local .h5 file (press "+" or drag and drop in the bottom area)')
                            ui.upload(on_upload=self.handle_upload, auto_upload=True, on_rejected=lambda: ui.notify('Invalid file', type='negative'), max_file_size=100_000_000_000).props('accept=.h5')

                # tree view
                # with ui.scroll_area().style("height:100%"):
                with ui.column():
                    self.treecontainer_gui = ui.expansion('Maps', icon='image').classes('w-full') #ui.column().classes('w-full')
                    self.treecontainer_gui.bind_visibility_from(self, "dataloaded")
                    with self.treecontainer_gui:
                        self.tree_display_gui = ui.card().classes("w-full")
                        self.tree_display_gui.bind_visibility_from(self, "dataloaded")
                        with self.tree_display_gui:
                            self.treesel_gui = ui.tree([], label_key='id', tick_strategy='leaf', on_tick=lambda e: self.checkwhatenabled(e))
                            self.treesel_gui.bind_visibility_from(self, "dataloaded")

                    with ui.expansion('Project file', icon='work').classes('w-full').classes('h-full'):
                        with ui.card().classes("w-full"):
                            ui.label('Import configuration (drag and drop)')
                            ui.upload(on_upload=self.handle_upload_project, auto_upload=True, on_rejected=lambda: ui.notify('Invalid file', type='negative'), max_file_size=100_000_000).props('accept=.xrfitvis2proj')
                            self.saveconf_gui = ui.button('Export Configuration', on_click=self.export_project)
                            self.saveconf_gui.bind_visibility_from(self, "readytosave")

                    # expand options
                    expand_options_gui = ui.expansion('Settings', icon='settings').classes('w-full').classes('h-full')
                    expand_options_gui.bind_visibility_from(self, "dataloaded")
                    with expand_options_gui.classes('w-full'):
                    
                        self.aspectratio_gui = ui.number(label='Pixel Aspect Ratio', value=1.0, format='%.3f',on_change=self.update_graph)
                        self.aspectratio_gui.bind_value(self, "aspectratio")

                        ui.label('Crop settings:')#.classes('w-full')
                        with ui.element('div').classes('w-full').style("width:100%; display:flex; gap:1rem"):
                            #ui.label('Rows').classes('w-1/3')
                            self.rowstart_gui = ui.number(label='Start row', value=0, format='%d',on_change=self.update_graph, min=0, step=1)
                            self.rowend_gui = ui.number(label='Stop row', value=1, format='%d',on_change=self.update_graph, min=1, step=1)
                        with ui.element('div').classes('w-full').style("width:100%; display:flex; gap:1rem"):
                            #ui.label('Columns').classes('w-1/3')
                            self.colstart_gui = ui.number(label='Start column', value=0, format='%d',on_change=self.update_graph, min=0, step=1)
                            self.colend_gui = ui.number(label='Stop column', value=1, format='%d',on_change=self.update_graph, min=1, step=1)

                        self.rowstart_gui.bind_value(self, "minrow")
                        self.colstart_gui.bind_value(self, "mincol")

                        self.rowend_gui.bind_value(self, "maxrow")
                        self.colend_gui.bind_value(self, "maxcol")

                        with ui.element('div').classes('w-full').style("width:100%; display:flex; gap:1rem"):
                            self.subpad_gui_h = ui.number(label='Vertical spacing', value=0.04167, format='%.3f',on_change=self.update_graph)
                            self.subpad_gui_h.bind_value(self, "hspace")
                            self.subpad_gui_h.bind_visibility_from(self, "dataloaded")

                            self.subpad_gui_w = ui.number(label='Horizontal spacing', value=0.04167, format='%.3f',on_change=self.update_graph)
                            self.subpad_gui_w.bind_value(self, "wspace")
                            self.subpad_gui_w.bind_visibility_from(self, "dataloaded")


                        self.cmapsel_gui = ui.select(CMAP_LIST, value="temperature as PyMCA", on_change=self.update_graph, label='Colormap:').style('width:100%')
                        self.cmapsel_gui.bind_value(self, "choosed_colormap")
                        self.cmapsel_gui.bind_visibility_from(self, "dataloaded")


                        self.denoisemethod_gui = ui.select(["Not Enabled", 'denoise_tv_chambolle','denoise_wavelet', 'denoise_bilateral', 'denoise_nl_means', 'denoise_tv_bregman'], value="Not Enabled", on_change=self.update_graph, label="Denoise method").style('width:100%')
                        self.denoisemethod_gui.bind_value(self, 'denoisemethod')

                        with ui.column():
                            ui.label('Default autoscale strategy:')
                            with ui.row():
                                self.default_autoscale_gui = ui.toggle(["Min/Max", "Std"], value="Min/Max", on_change=self.logchanged)
                                self.default_autoscale_gui.bind_value(self, 'autoscalestrategy')
                                self.logcheckbox_gui = ui.switch('Log10', on_change=self.logchanged)
                                self.logcheckbox_gui.bind_visibility_from(self, "dataloaded")
                                self.logcheckbox_gui.bind_value(self, "logchecked")
                                
                                self.gain_gui = ui.number(label='Gain', value=15, format='%.6f',on_change=self.update_graph)
                                self.gain_gui.bind_value(self, "gain")


                        self.logticks_gui = ui.switch('Ticks', on_change=self.update_graph)
                        self.logticks_gui.bind_visibility_from(self, "dataloaded")
                        self.logticks_gui.bind_value(self, "plotticks")

                        self.labelsize_gui = ui.number(label='Map name size', value=20, format='%.1f',on_change=self.update_graph)
                        self.labelsize_gui.bind_value(self, "labelsize")
                        self.labelsize_gui.bind_visibility_from(self, "dataloaded")

                        with ui.row():
                            self.caliblabelsize_gui = ui.number(label='Colorbar size', value=0.046 *1000., format='%.1f',on_change=self.update_graph)
                            self.caliblabelsize_gui.bind_value(self, "colorbarfraction")
                            self.caliblabelsize_gui.bind_visibility_from(self, "dataloaded")

                            self.caliblabelsize_gui = ui.number(label='Colorbar spacing', value=0.02, format='%.3f',on_change=self.update_graph)
                            self.caliblabelsize_gui.bind_value(self, "colorbarspacing")
                            self.caliblabelsize_gui.bind_visibility_from(self, "dataloaded")

                            self.caliblabelsize_gui = ui.number(label='Colorbar label size', value=15, format='%.1f',on_change=self.update_graph)
                            self.caliblabelsize_gui.bind_value(self, "caliblabelsize")
                            self.caliblabelsize_gui.bind_visibility_from(self, "dataloaded")

                        with ui.row():
                            self.colorbarticks_gui = ui.number(label='Colorbar Ticks', value=5, format='%d',on_change=self.update_graph, min=1, step=1)
                            self.colorbarticks_gui.bind_value(self, "colorbarticksnum")

                            self.colorbar_horiz_gui = ui.switch('Horizontal colorbar', on_change=self.update_graph)
                            self.colorbar_horiz_gui.bind_visibility_from(self, "dataloaded")
                            self.colorbar_horiz_gui.bind_value(self, "horizcolorbar")

                        with ui.row():
                            self.fliplr_gui = ui.switch('All Flip horizontal', on_change=self.update_graph)
                            self.fliplr_gui.bind_visibility_from(self, "dataloaded")
                            self.fliplr_gui.bind_value(self, "fliplrall")

                            self.flipud_gui = ui.switch('All Flip vertical', on_change=self.update_graph)
                            self.flipud_gui.bind_visibility_from(self, "dataloaded")
                            self.flipud_gui.bind_value(self, "flipudall")

                ui.label('Export:').bind_visibility_from(self, 'readytosave')
                with ui.row().classes('w-full').style("margin-bottom:1rem;"):
                    self.savegraph_gui = ui.button('Export Figure', on_click=self.savefig)
                    self.savegraph_gui.bind_visibility_from(self, "readytosave")

                    self.savemaps_gui = ui.button('Export Multipage TIFF RAW maps', on_click=self.exportrawmaps)
                    self.savemaps_gui.bind_visibility_from(self, "readytosave")

            # main plot
            with ui.column().classes('col-8 col-lg-9 col-xxl-10').style("height: 100%;"):
                with ui.scroll_area().style("height:100vh").style("justify-content: center;display: flex;"):
                    with ui.row().classes().style("width:100%;justify-content: center;display: flex;"):
                        self.main_plot = ui.pyplot(close=False).style("image-rendering: pixelated !important;")#.on('mousedown', lambda e: self.elaborate_pos(e)) #  figsize=(12, 4) #figsize=(16,16),dpi=40
                        self.main_plot.set_visibility(True)
                    ui.label('Custom colorbar limit values:').bind_visibility_from(self, "dataloaded")
                    self.tablegui =  ui.aggrid(
                                    {
                                        "columnDefs": [
                                            {"field": "name", "editable": True, "sortable": True},
                                            {"field": "min", "editable": True},
                                            {"field": "max", "editable": True},
                                            {"field": "id"}
                                        ],
                                        "rowData": self.minmaxtable,
                                        "rowSelection": "multiple",
                                        "stopEditingWhenCellsLoseFocus": True,
                                    }
                                ).on("cellValueChanged", self.update_data_from_table_change).classes("no-wrap")#.classes('w-full')
                    self.tablegui.bind_visibility_from(self, "dataloaded")



    async def update_data_from_table_change(self, e):
        #ui.notify(f"Update with {e.args['data'] }")
        uprow = e.args["data"]
        self.minmaxtable[:] = [row | uprow if row["id"] == uprow["id"] else row for row in self.minmaxtable]
        await self.update_graph()


    async def export_project(self):

        try:
            deep_copied_members = {name: deepcopy(getattr(self, name)) for name in class_members_exports}
            deep_copied_members["external_ticked_items"] = self.treesel_gui._props['ticked']

            tempdir = tempfile.TemporaryDirectory(dir='/tmp/')
            pickle_filename = f"{tempdir.name}/exportproj_{os.path.basename(self.path).split('.')[0]}.xrfitvis2proj"

            with open(pickle_filename, "wb") as pickle_file:
                pickle.dump(deep_copied_members, pickle_file)

            ui.download(pickle_filename)
            await asyncio.sleep(1)
            tempdir.cleanup()
            ui.notify(f'Saved {os.path.basename(pickle_filename)}', close_button="OK", type='positive')

        except Exception as e:
            print(e)
            ui.notify(f'Problems saving the configuration', close_button="OK", type='negative')


    async def handle_upload_project(self, e: events.UploadEventArguments):
        content = e.content.read()
        tempdir = tempfile.TemporaryDirectory(dir='/tmp/')
        outname = f"{tempdir.name}/{e.name}"

        with open(outname, 'wb') as f:
            f.write(content)
        self.pickle_file_path = outname
        await self.load_projectfile()
        tempdir.cleanup()


    async def load_projectfile(self):
        try:
            with open(self.pickle_file_path, "rb") as pickle_file:
                loaded_class_members = pickle.load(pickle_file)

            for name, value in loaded_class_members.items():
                if name == "minmaxtable":
                    self.minmaxtable[:] = value
                elif name == 'external_ticked_items':
                     tmpchk = value
                else:
                    setattr(self, name, value)

            self.dataloaded = True
            self.readytosave = True
            self.path = self.pickle_file_path

            self.tablegui.update()
            self.updatetree()
            self.treesel_gui._props['ticked'] = tmpchk
            await self.update_graph()
            self.treecontainer_gui.open()

            ui.notify(f'Loaded {os.path.basename(self.pickle_file_path)}', close_button="OK", type='positive')

            with self.tree_display_gui:
                print(self.treesel_gui.__dict__)

        except Exception as e:
            print(f"error loading project: {e}")
            ui.notify(f'Problems loading the configuration', close_button="OK", type='negative')
           
            
if __name__ in {"__main__", "__mp_main__"}:

    @ui.page('/{command}', title='XRFitVis')
    async def h5page(client: Client, command: str, datapath: str = None, beamline: str = None, investigation: str = None):
        await client.connected()
        await asyncio.sleep(0.1)
        print(f"URL info: {Client=}, {command=}, {datapath=}, {beamline=}, {investigation=}")
        if command == 'load':
            mygui = TheGui()
            mygui.initgui()
        

    @ui.page('/test/', title='XRFitVis_test')
    async def page(client: Client): 
        ui.label('Test')
        ui.label(f'{client}')
       
            

    ui.run(port=8228, host="0.0.0.0", reconnect_timeout=25, show=False)
    


