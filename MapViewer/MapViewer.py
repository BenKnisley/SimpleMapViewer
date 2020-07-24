#!/usr/bin/env python3
"""
Project: MapViewer
Title: Main Executable
Author: Ben Knisley [benknisley@gmail.com]
Date: 8 December, 2019
Function: UI entry point for user
"""
## Import standard library modules
import os, sys
from random import randint
from urllib.parse import urlparse, unquote

from threading import Thread

## Import PyGTK Modules
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, Gio, GObject

## Import VectorLayer & MapCanvas
from PyMapKit import VectorLayer, RasterLayer, TileLayer

import MapCanvasGTK


class MapViewerApplication(Gtk.Application):
    """ The root GTK object for the application. Opens MainWindow. """
    def __init__(self):
        """ Opens MainWindow and connects signals & slots. """
        ## Set ID and flags, initialize Gtk Application parent.
        app_id="apps.test.MapViewer.id" + str(randint(1,1000))
        flags=Gio.ApplicationFlags.FLAGS_NONE
        Gtk.Application.__init__(self, application_id=app_id, flags=flags)

        ## Initialize self object.
        self.window = MainWindow()

        ## Connect self activate signal, with self on_activate slot
        self.connect("activate", self._on_activate)

    def _on_activate(self, caller):
        self.window.show_all()
        self.add_window(self.window)


class LayerView(Gtk.TreeView):
    def __init__(self, parent_map):
        ## Init as a TreeView obj
        Gtk.TreeView.__init__(self)
        self.parent_map = parent_map

        ## Make item selected on single click
        self.set_activate_on_single_click(True)

        ## Setup a ListStore as a data model
        self.store = Gtk.ListStore(object, str) ## MapLayer, layer name
        self.set_model(self.store)

        ## Setup a single column as a model
        rendererText = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("                                   Map Layers                                   ", rendererText, text=1)
        self.append_column(column)

        ## Connect selection changes with selection_changed_slot
        selection_watcher = self.get_selection()
        selection_watcher.connect("changed", self.selection_changed_slot)


    #def selection_changed_slot(self, treeview, index, view_column):
    def selection_changed_slot(self, caller):
        """
        Updated active layer index when called
        """
        ## Get model and treepath of selected row
        selection_watcher = self.get_selection()
        model, treepath = selection_watcher.get_selected_rows()

        ## Get layer from model and treepath
        layer = model[treepath][0]

        ## Get Index of layer in map layer list
        layer_index = self.parent_map._layer_list.index(layer)

        ## Set active layer index to selected layer index
        self.parent_map.active_layer_index = layer_index

        
        
        
        #tree_row = treeview.get_model()[index]
        #self.parent_map.active_layer_index = self.parent_map._layer_list.index(tree_row[1])
        #view_column


    def layer_added_slot(self, caller, layer):
        """
        Adds a given MapLayer to the layer list
        """
        ## Add layer name and layer to model
        self.store.append([layer, layer.name])

        ## Set selection new layer
        index = len(self.store) - 1
        path = Gtk.TreePath.new_from_indices([index])
        self.set_cursor_on_cell(path, None, None, False)





class MainWindow(Gtk.Window):
    """ The main application window """
    def __init__(self):
        """ Defines window properties, & adds child widgets. """
        ## Initialize parents: Gtk.Window & Gtk.GObject
        Gtk.Window.__init__(self)
        GObject.GObject.__init__(self)

        ## Set window properties
        self.set_title("GeoSpatial Data Viewer")
        self.resize(1700, 900)
        self.set_border_width(0)

        ## Enable and setup drag and drop for window
        self.connect('drag_data_received', self.on_drag_data_received)
        self.drag_dest_set( Gtk.DestDefaults.MOTION | Gtk.DestDefaults.HIGHLIGHT | Gtk.DestDefaults.DROP, [Gtk.TargetEntry.new("text/uri-list", 0, 80)], Gdk.DragAction.COPY)
        

        ## Setup MapCanvas Widget
        self.map = MapCanvasGTK.MapCanvas()
        self.map.add_tool( MapCanvasGTK.UITool() )

        ## Setup LayerView Widget
        layer_view = LayerView(self.map)

        self.map.connect('layer-added', layer_view.layer_added_slot)






        #####################
        ###    Layout     ###
        #####################

        ## Create main window layout, and add layout to window(self)
        self.layout = Gtk.VBox()
        self.add(self.layout)

        ## Setup top toolbar widget, and add to main layout
        self.toolbar = Gtk.Toolbar()
        newbtn = Gtk.ToolButton(Gtk.STOCK_NEW)

        def x(*args): self.map.add_tool(MapCanvasGTK.SelectTool())
        newbtn.connect('clicked', x)
        
        sep = Gtk.SeparatorToolItem()
        self.toolbar.insert(newbtn, 0)
        self.toolbar.insert(sep, 1)
        self.layout.pack_start(self.toolbar, False, False, 0)


        ## Setup side be side panes, add to main layout
        side_by_side = Gtk.HBox()
        self.layout.pack_start(side_by_side, True, True, 0)

        ## Setup Sidebar layout, add to side by side
        self.sidebar = Gtk.VBox()
        side_by_side.pack_start(self.sidebar, False, False, 3)

        ## Add layerView to sidebar
        self.sidebar.pack_start(layer_view, True, True, 0)

        ## Create a vbox to hold map_overlay, and map statusbar. Add to side_by_side
        map_area = Gtk.VBox()
        side_by_side.pack_start(map_area, True, True, 0)

        ## Create overlay layout and put map canvas in it
        self.map_overlay = Gtk.Overlay()
        self.map_overlay.add(self.map)

        ## Put Map Overlay into map_area
        map_area.pack_start(self.map_overlay, True, True, 0)

        ## Setup statusbar, add to map area
        self.statusbar = Gtk.HBox()
        self.statusbar.pack_start(Gtk.Label("Helo"), False, False, 10)
        map_area.pack_start(self.statusbar, False, False, 0)


        ## Add overlay with map in it to layout












    def add_from_path(self, path):
        """ """
        file_extension = path.split(".")[-1]

        ## If Vector data, create a New Vector Layer
        if file_extension in ('shp', 'geojson'): 
            print("Adding Vector Layer")
            layer = VectorLayer(path)
            color_list = ['salmon', 'goldenrod', 'firebrick', 'steelblue', 'aquamarine', 'seagreen', 'powderblue', 'cornflowerblue', 'crimson', 'darkgoldenrod', 'chocolate', 'darkmagenta', 'darkolivegreen', 'darkturquoise', 'deeppink']
            rand_color = color_list[randint(0, len(color_list)-1)]
            for f in layer: f.set_color(rand_color)
            layer.set_opacity(0.5)
        
        elif file_extension in ('geotiff'):
            print("Adding Raster Layer")
            layer = RasterLayer(path, True)


        '''
        This code lets me add a new layer without GUI locking up
        '''
        def add_fn(layer):
            self.map.add_layer(layer)
            layer.focus()
        
        def thread_killer(t):
            if t.is_alive() == False:
                t.join()
                self.map.call_redraw(self)
            else:
                GObject.idle_add(thread_killer, t)

        thread = Thread(target = add_fn, args = (layer, ))
        thread.start()
        GObject.idle_add(thread_killer, thread)

        #GObject.idle_add(add_fn, layer)

    def on_drag_data_received(self, caller, context, x, y, selection, target_type, timestamp):
        """ Drag and drop received slot """
        ## Clean selection url string
        selection_data = selection.get_data().decode("utf-8")
        selection_data = selection_data.strip('\r\n\x00')
        selection_data = selection_data.replace('file"//', '')
        selection_data = selection_data.split('\r\n')
        
        ## Add all shp files in selection_data
        for url in selection_data:
            path = unquote(urlparse(url).path)
            self.add_from_path(path)
            self.map.call_redraw(self)



def main():
    """ Main function exists to allow for multiple entry points (namely setup.py's console_scripts)"""
    ## Create MapViewerApplication instance
    app = MapViewerApplication()

    ## If command line args given
    if len(sys.argv) > 1:
        for arg in list(sys.argv[1:]):
            ## Assume all args are a shapefile path (for now)
            app.window.add_from_path(arg)
    
    ## Run Applications
    app.run()

## If file run directly, call main functions
if __name__ == "__main__":
    ## Enable mutithreading
    GObject.threads_init()
    main()

