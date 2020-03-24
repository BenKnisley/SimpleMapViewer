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

## Import PyGTK Modules
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, Gio, GObject

## Import VectorLayer & MapCanvas
from MapEngine import VectorLayer
from MapCanvas import MapCanvas


class MapViewerApplication(Gtk.Application):
    """ The root GTK object for the application. Opens MainWindow. """
    def __init__(self):
        """ Opens MainWindow and connects signals & slots. """
        ## Set ID and flags, initialize Gtk Application parent.
        app_id="apps.test.MapViewer"
        flags=Gio.ApplicationFlags.FLAGS_NONE
        Gtk.Application.__init__(self, application_id=app_id, flags=flags)

        ## Initialize self object.
        self.window = MainWindow()

        ## Connect self activate signal, with self on_activate slot
        self.connect("activate", self._on_activate)

    def _on_activate(self, caller):
        self.window.show_all()
        self.add_window(self.window)


class MainWindow(Gtk.Window):
    """ The main application window, hosts the MapView widget """
    def __init__(self):
        """ Defines window properties, & adds child widgets. """
        ## Initialize parents: Gtk.Window & Gtk.GObject
        Gtk.Window.__init__(self)
        GObject.GObject.__init__(self)

        ## Set own window properties
        self.resize(1700, 900)
        self.set_title("Map Viewer")
        self.set_border_width(3)

        ## Create widgets
        self.map = MapCanvas()

        #self.map.set_projection("EPSG:4326")
        self.map.set_projection("EPSG:3857")
        #self.map.set_projection("EPSG:32023")
        #self.map.set_projection("+proj=aea +lat_1=29.5 +lat_2=45.5 +lat_0=37.5 +lon_0=-96 +x_0=0 +y_0=0 +datum=NAD83 +units=m +no_defs")

        self.map.set_location((-83.0, 40.0))
        self.map.set_scale(40000)
        self.map.set_background_color('black')

        ## Enable and setup drag and drop
        self.connect('drag_data_received', self.on_drag_data_received)
        self.drag_dest_set( Gtk.DestDefaults.MOTION | Gtk.DestDefaults.HIGHLIGHT | Gtk.DestDefaults.DROP, [Gtk.TargetEntry.new("text/uri-list", 0, 80)], Gdk.DragAction.COPY)

        ## Create layout, add MapView, and add layout to window
        self.layout = Gtk.VBox()
        self.layout.pack_start(self.map, True, True, 0)
        self.add(self.layout)
    

    def add_shapefile(self, path):
        """ Adds a layer from a file (Rename to add_from_path) """
        self.map.add_layer(VectorLayer.from_shapefile(path))


    def on_drag_data_received(self, caller, context, x, y, selection, target_type, timestamp):
        """ Drag and drop received slot """
        ## Clean selection url string
        selection_data = selection.get_data().decode("utf-8")
        selection_data = selection_data.strip('\r\n\x00')
        selection_data = selection_data.split('\r\n')

        ## Add all shp files in selection_data
        for url in selection_data:
            path = url[7:] ## Strip file://
            if path[-3:] == 'shp' and os.path.isfile(path):
                ## Add shapefile to map
                 self.add_shapefile(path)



def main():
    """ Main function exists to allow for multiple entry points (namely setup.py's console_scripts)"""
    ## Create MapViewerApplication instance
    app = MapViewerApplication()

    ## If command line args given
    if len(sys.argv) > 1:
        for arg in list(sys.argv[1:]):
            ## Assume all args are a shapefile path (for now)
            app.window.add_shapefile(arg)

    ## Run Applications
    app.run()

## If file run directly, call main functions
if __name__ == "__main__":
    main()

