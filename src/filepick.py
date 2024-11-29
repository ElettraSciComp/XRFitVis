import os
import string
import platform
from pathlib import Path
from typing import Optional, List


from nicegui import ui
from nicegui.events import ValueChangeEventArguments, GenericEventArguments

class FilePicker(ui.dialog):

    def __init__(self, directory: str, *,
                 upper_limit: Optional[str] = None,
                 show_hidden_files: bool = False,
                 allowed_extensions: Optional[List[str]] = None,) -> None:
        """
        https://github.com/zauberzeug/nicegui/tree/main/examples/local_file_picker

        Parameters
        ----------

        directory : str
            Starting directory.
        upper_limit : str
            Stopping directory (None: no limit).
        show_hidden_files : bool
            Whether to show hidden files.
        allowed_extensions : list of str
            Only show files with given extension. E.g. ['hdf', 'h5', 'nxs']

        Returns
        -------
            file path.
        """
        super().__init__()
        self.show_hidden_files = show_hidden_files
        self.allowed_extensions = allowed_extensions
        self.drives_toggle = None
        self.path = Path(directory).expanduser()
        if upper_limit is None:
            self.upper_limit = None
        else:
            self.upper_limit = Path(
                directory if upper_limit is ... else upper_limit).expanduser()
        with self, ui.card():
            self.add_drives_toggle()
            self.grid = ui.aggrid(
                {'columnDefs': [{'field': 'name', 'headerName': 'File'}],
                 'rowSelection': 'single'}, html_columns=[0]).classes(
                'w-96').on('cellDoubleClicked', self.handle_double_click)
            with ui.row().classes('w-full justify-end'):
                ui.button('Cancel', on_click=self.close).props('outline')
                ui.button('Ok', on_click=self.handle_ok)
        self.update_grid()

    def check_extension(self, filename: str) -> bool:
        """Check if the filename has an allowed extension."""
        if self.allowed_extensions is None:
            return True
        else:
            return filename.split('.')[-1].lower() in self.allowed_extensions
            

    def add_drives_toggle(self):
        """Give a list of available drivers in a WinOS computer"""
        if platform.system() == 'Windows':
            drives = ['%s:\\' % d for d in string.ascii_uppercase if
                      os.path.exists('%s:' % d)]
            self.path = Path(drives[0]).expanduser()
            self.drives_toggle = ui.toggle(drives, value=drives[0],
                                           on_change=self.__update_drive)

    def __update_drive(self):
        if self.drives_toggle:
            self.path = Path(self.drives_toggle.value).expanduser()
            self.update_grid()

    def update_grid(self) -> None:
        paths = list(self.path.glob('*'))
        if not self.show_hidden_files:
            paths = [p for p in paths if not p.name.startswith('.')]
        if self.allowed_extensions:
            paths = [p for p in paths if
                     p.is_dir() or self.check_extension(p.name)]
                     
        paths.sort(key=lambda p: p.name.lower())
        paths.sort(key=lambda p: not p.is_dir())
        
        self.grid.options['rowData'] = [
            {'name': f'📁 <strong>{p.name}</strong>' if p.is_dir() else p.name,
             'path': str(p), } for p in paths]
        if (self.upper_limit is None
                and self.path != self.path.parent
                or self.upper_limit is not None
                and self.path != self.upper_limit):
            self.grid.options['rowData'].insert(0, {
                'name': '📁 <strong>..</strong>',
                'path': str(self.path.parent), })
        self.grid.update()

    def handle_double_click(self, e: GenericEventArguments) -> None:
        self.path = Path(e.args['data']['path'])
        if self.path.is_dir():
            self.update_grid()
        else:
            if self.path:
                self.submit(str(self.path))
            else:
                return

    async def handle_ok(self):
        try:
            rows = await ui.run_javascript(
                f'getElement({self.grid.id}).gridOptions.api.getSelectedRows()')
            if rows:
                fpath = [r['path'] for r in rows]
                if fpath:
                    self.submit(fpath[0])
                else:
                    ui.notify("No file path found in the selected rows")
                    return
            else:
                ui.notify("No rows selected.")
                return
        except Exception as e:
            ui.notify(f"An error occurred: {e}")
            return
