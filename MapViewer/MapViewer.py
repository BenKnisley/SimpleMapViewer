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


class MainWindow(Gtk.Window):
    """ The main application window """
    def __init__(self):
        """ Defines window properties, & adds child widgets. """
        ## Initialize parents: Gtk.Window & Gtk.GObject
        Gtk.Window.__init__(self)
        GObject.GObject.__init__(self)

        ## Set properties
        self.set_title("GeoSpatial Data Viewer")
        self.resize(1700, 900)
        self.set_border_width(0)

        ## Setup MapCanvas Widget
        self.map = MapCanvasGTK.MapCanvas()
        self.map.add_tool( MapCanvasGTK.UITool() )

        ## Enable and setup drag and drop
        self.connect('drag_data_received', self.on_drag_data_received)
        self.drag_dest_set( Gtk.DestDefaults.MOTION | Gtk.DestDefaults.HIGHLIGHT | Gtk.DestDefaults.DROP, [Gtk.TargetEntry.new("text/uri-list", 0, 80)], Gdk.DragAction.COPY)


        ## Create Overlay and put map canvas in it
        self.overlay = Gtk.Overlay()
        self.overlay.add(self.map)

        ''' Over widget add
        over_widget = Gtk.Button("Press Me")
        over_widget.set_valign(Gtk.Align.START)
        over_widget.set_halign(Gtk.Align.START)
        over_widget.set_margin_top(30)
        over_widget.set_margin_left(30)
        #self.overlay.add_overlay(over_widget)
        '''
    
        ## Create main window layout, and add layout to window
        self.layout = Gtk.VBox()
        self.add(self.layout)

        ## Add overlay with map in it to layout
        self.layout.pack_start(self.overlay, True, True, 0)





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
    
    ## Add title layer
    #app.window.map.add_layer( TileLayer("https://a.tile.openstreetmap.org/{z}/{x}/{y}.png", blocking=False) )
    #app.window.map.add_layer( RasterLayer("/home/ben/Downloads/LC08_L1TP_019033_20200607_20200625_01_T1/LC08_L1TP_019033_20200607_20200625_01_T1.tif", True))
    #app.window.map.add_layer( TileLayer("https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}", blocking=False) )
    ## Set to random color


    ## Run Applications
    app.run()

## If file run directly, call main functions
if __name__ == "__main__":
    ## Enable mutithreading
    GObject.threads_init()
    main()

