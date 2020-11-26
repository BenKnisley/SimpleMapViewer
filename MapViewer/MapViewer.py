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

## Make GTK thread aware
GObject.threads_init()

## Import MapCanvas Widget
import MapCanvasGTK

## Import layers from VectorLayer
from PyMapKit import VectorLayer, RasterLayer, TileLayer
from PyMapKit import vector

from .LayerViewWidget import LayerView



##############################
## Tool Classes
##############################

class SelectTool(GObject.GObject): 
    __gsignals__ = {
    "features-selected": (GObject.SIGNAL_RUN_FIRST, GObject.TYPE_NONE, (object,)),
    "selection-cleared": (GObject.SIGNAL_RUN_FIRST, GObject.TYPE_NONE, ()),
    }
    def __init__(self):
        GObject.GObject.__init__(self)
        self.parent = None
        self.connection_list = []
        self.select_box_active = False
        self.selected = []

        self.selected_style = vector.FeatureStyle()
        self.selected_style.set_color('yellow', 0.25)
        self.selected_style.set_outline_color('red')


        #self.signal_new("map-features-selected", self, GObject.SIGNAL_RUN_FIRST, None, (object,))

    def activate(self, parent):
        ## Set parent object
        self.parent = parent
        ## Setup connection, keeping the reference to each in connection_list
        self.connection_list.append( self.parent.connect("double-click", self.select_at_click) )
        self.connection_list.append( self.parent.connect("middle-click", self.deselect_click) )
        self.connection_list.append( self.parent.connect("middle-drag-start", self.select_box_start) )
        self.connection_list.append( self.parent.connect("middle-drag-update", self.select_box_update) )
        self.connection_list.append( self.parent.connect("middle-drag-end", self.select_box_end) )

    def deactivate(self):
        ## Reset tool vars
        self.select_box_active = False
        self.selected = []
        ## Disconnect all connection
        for connect_id in self.connection_list:
            self.parent.disconnect(connect_id)
        
        ## Clear Connection list
        self.connection_list = []

        ## Remove parent
        self.parent = None

    def select_at_click(self, caller, x, y):
        """ """
        self.deselect_all(self)

        ## Get current active layer
        layer = self.parent.get_layer( self.parent.active_layer_index )
        if isinstance(layer, VectorLayer):
            ## Get proj coords of click
            proj_x, proj_y = self.parent.pix2proj(x, self.parent.height - y)

            ## Get features at point
            selected_features = layer.point_select(proj_x, proj_y)

            ## Add all selected features to selected_features list
            for feature in selected_features:
                if feature not in self.selected:
                    self.selected.append(feature)

        ## Emit selected_features 
        self.emit("features-selected", self.selected)

        ## Redraw widget with selected features highlighted
        self.parent.call_redraw(self)
    
    def select_box_start(self, caller, x, y):
        self.select_box_active = True
        self.select_box_start_coord = (x, y)
        self.select_box_size = (0, 0)

    def select_box_update(self, caller, x, y):
        if self.select_box_active:
            self.select_box_size = self.select_box_size[0] + x, self.select_box_size[1] + y
            self.parent.call_redraw(self)

    def select_box_end(self, caller, x, y):
        ## Set box active to false to stop drawing rectangle
        self.select_box_active = False

        ## Get current active layer, only proceed of VectorLayer
        layer = self.parent.get_layer( self.parent.active_layer_index )
        if isinstance(layer, VectorLayer):
            ## Get proj coords of start of drag
            x0, y0 = self.select_box_start_coord
            
            ## Get proj coords of 
            proj_x1, proj_y1 = self.parent.pix2proj(x0, self.parent.height - y0)
            proj_x2, proj_y2 = self.parent.pix2proj(x, self.parent.height - y)

            ## Get Min and max of projection coords
            min_x = min(proj_x1, proj_x2)
            min_y = min(proj_y1, proj_y2)
            max_x = max(proj_x1, proj_x2)
            max_y = max(proj_y1, proj_y2)

            ## Get features within selection area
            selected_features = layer.box_select(min_x, min_y, max_x, max_y)

            ## Add all selected features to selected_features list
            for feature in selected_features:
                if feature not in self.selected:
                    self.selected.append(feature)

        ## Emit feature selected signal
        self.emit("features-selected", self.selected)

        ## Redraw widget with selected features highlighted
        self.parent.call_redraw(self)

    def deselect_click(self, caller, x, y):
        self.deselect_all(caller)

    def deselect_all(self, caller):
        self.selected = []
        self.parent.call_redraw(self)
        self.emit("selection-cleared")

    def draw(self, cr):
        """ """
        if self.select_box_active:
            cr.rectangle(*self.select_box_start_coord, *self.select_box_size)
            cr.set_source_rgba(0, 1, 1, 0.25)
            cr.fill_preserve()

            cr.set_source_rgba(0, 1, 1, 1)
            cr.set_line_width(3)
            cr.stroke()

        for f in self.selected:
            x_values, y_values = f.parent.parent.proj2pix(*f.geometry.get_points())

            if f.geometry.geometry_type == 'point':
                self.parent.renderer.draw_point(cr, f.geometry.structure, x_values, y_values, self.selected_style)
            elif f.geometry.geometry_type == 'line':
                self.parent.renderer.draw_line(cr, f.geometry.structure, x_values, y_values, self.selected_style)
            else: #f.geometry_type == 'polygon':
                self.parent.renderer.draw_polygon(cr, f.geometry.structure, x_values, y_values, self.selected_style)


class IdentifyTool(GObject.GObject):
    __gsignals__ = {
        "features-selected": (GObject.SIGNAL_RUN_FIRST, GObject.TYPE_NONE, (object,)),
        "selection-cleared": (GObject.SIGNAL_RUN_FIRST, GObject.TYPE_NONE, ()),
    }
    
    def __init__(self, window):
        GObject.GObject.__init__(self)
        self.parent = None
        self.connection_list = []
        self.select_box_active = False
        self.selected = []

        self.selected_style = vector.FeatureStyle()
        self.selected_style.set_color('yellow', 0.25)
        self.selected_style.set_outline_color('red')

        self.window = window

        self.display = IdentifyDisplay()
        
        self.connect("features-selected", self.ping)
        self.connect("selection-cleared", self.ping2)
    
    def activate(self, parent_map):
        ## Set parent object
        self.parent = parent_map

        ## Setup connection, keeping the reference to each in connection_list
        self.connection_list.append( self.parent.connect("double-click", self.select_at_click) )
        self.connection_list.append( self.parent.connect("middle-click", self.deselect_click) )
        self.connection_list.append( self.parent.connect("middle-drag-start", self.select_box_start) )
        self.connection_list.append( self.parent.connect("middle-drag-update", self.select_box_update) )
        self.connection_list.append( self.parent.connect("middle-drag-end", self.select_box_end) )

        ##
        self.window.sidebar.pack_start(self.display, True, True, 0)
        self.window.sidebar.show_all()

    def deactivate(self):
        ## Reset tool vars
        self.select_box_active = False
        self.selected = []

        ## Disconnect all connection
        for connect_id in self.connection_list:
            self.parent.disconnect(connect_id)
        
        ## Clear Connection list
        self.connection_list = []

        ## Remove parent
        self.parent = None

        self.display.clear_display()
        self.window.sidebar.remove(self.display)
        self.window.sidebar.show_all()
    
    
    def select_at_click(self, caller, x, y):
        """ """
        self.deselect_all(self)

        ## Get current active layer
        layer = self.parent.get_layer( self.parent.active_layer_index )
        if isinstance(layer, VectorLayer):
            ## Get proj coords of click
            proj_x, proj_y = self.parent.pix2proj(x, self.parent.height - y)

            ## Get features at point
            selected_features = layer.point_select(proj_x, proj_y)

            ## Add all selected features to selected_features list
            for feature in selected_features:
                if feature not in self.selected:
                    self.selected.append(feature)

        ## Emit selected_features 
        self.emit("features-selected", self.selected)

        ## Redraw widget with selected features highlighted
        self.parent.call_redraw(self)
    
    def select_box_start(self, caller, x, y):
        self.select_box_active = True
        self.select_box_start_coord = (x, y)
        self.select_box_size = (0, 0)

    def select_box_update(self, caller, x, y):
        if self.select_box_active:
            self.select_box_size = self.select_box_size[0] + x, self.select_box_size[1] + y
            self.parent.call_redraw(self)

    def select_box_end(self, caller, x, y):
        ## Set box active to false to stop drawing rectangle
        self.select_box_active = False

        ## Get current active layer, only proceed of VectorLayer
        layer = self.parent.get_layer( self.parent.active_layer_index )
        if isinstance(layer, VectorLayer):
            ## Get proj coords of start of drag
            x0, y0 = self.select_box_start_coord
            
            ## Get proj coords of 
            proj_x1, proj_y1 = self.parent.pix2proj(x0, self.parent.height - y0)
            proj_x2, proj_y2 = self.parent.pix2proj(x, self.parent.height - y)

            ## Get Min and max of projection coords
            min_x = min(proj_x1, proj_x2)
            min_y = min(proj_y1, proj_y2)
            max_x = max(proj_x1, proj_x2)
            max_y = max(proj_y1, proj_y2)

            ## Get features within selection area
            selected_features = layer.box_select(min_x, min_y, max_x, max_y)

            ## Add all selected features to selected_features list
            for feature in selected_features:
                if feature not in self.selected:
                    self.selected.append(feature)

        ## Emit feature selected signal
        self.emit("features-selected", self.selected)

        ## Redraw widget with selected features highlighted
        self.parent.call_redraw(self)

    def deselect_click(self, caller, x, y):
        self.deselect_all(caller)

    def deselect_all(self, caller):
        self.selected = []
        self.parent.call_redraw(self)
        self.emit("selection-cleared")

    def draw(self, cr):
        """ """
        if self.select_box_active:
            cr.rectangle(*self.select_box_start_coord, *self.select_box_size)
            cr.set_source_rgba(0, 1, 1, 0.25)
            cr.fill_preserve()

            cr.set_source_rgba(0, 1, 1, 1)
            cr.set_line_width(3)
            cr.stroke()

        for f in self.selected:
            x_values, y_values = f.parent.parent.proj2pix(*f.geometry.get_points())

            if f.geometry.geometry_type == 'point':
                self.parent.renderer.draw_point(cr, f.geometry.structure, x_values, y_values, self.selected_style)
            elif f.geometry.geometry_type == 'line':
                self.parent.renderer.draw_line(cr, f.geometry.structure, x_values, y_values, self.selected_style)
            else: #f.geometry_type == 'polygon':
                self.parent.renderer.draw_polygon(cr, f.geometry.structure, x_values, y_values, self.selected_style)


    def ping(self, caller, features):
        self.display.list_features(features)
    
    def ping2(self, caller):
        self.display.clear_display()

class IdentifyDisplay(Gtk.Frame):
    def __init__(self):
        Gtk.Frame.__init__(self, label="Selected Features")

        self.subwidgets = []
        self.layout = Gtk.VBox()
        
        sw = Gtk.ScrolledWindow()
        sw.add_with_viewport(self.layout)
        self.add(sw)
    
    def clear_display(self):
            ## Clean out old before adding new
        for widget in self.subwidgets:
            self.layout.remove(widget)
        self.subwidgets = []
    
    def list_features(self, features):
        ## Clean out old before adding new
        for widget in self.subwidgets:
            self.layout.remove(widget)
        self.subwidgets = []

        for feature in features:
            for fieldname in feature.attributes.keys():
                string = f"{fieldname}: {feature[fieldname]}"
                label = Gtk.Label(string)
                self.subwidgets.append(label)
                self.layout.pack_start(label, False, False, 0)

            label = Gtk.Label("........................")
            self.subwidgets.append(label)
            self.layout.pack_start(label, False, False, 0)

            self.layout.show_all()


class TileLayerTool(GObject.GObject):
    __gsignals__ = {
    #"features-selected": (GObject.SIGNAL_RUN_FIRST, GObject.TYPE_NONE, (object,)),
    #"selection-cleared": (GObject.SIGNAL_RUN_FIRST, GObject.TYPE_NONE, ()),
    }
    def __init__(self):
        GObject.GObject.__init__(self)
        self.parent = None
        self.connection_list = []

        self.tile_layer = self.tile_layer = TileLayer('https://a.tile.openstreetmap.org/{z}/{x}/{y}.png', False)
        
        #self.signal_new("map-features-selected", self, GObject.SIGNAL_RUN_FIRST, None, (object,))

    def activate(self, parent):
        ## Set parent object
        self.parent = parent

        self.parent.add_layer(self.tile_layer)

        ## Setup connection, keeping the reference to each in connection_list
        #self.connection_list.append( self.parent.connect("double-click", self.select_at_click) )

    def deactivate(self):
        ## Reset tool vars
        self.selected = []
        ## Disconnect all connection
        for connect_id in self.connection_list:
            self.parent.disconnect(connect_id)
        
        ## Clear Connection list
        self.connection_list = []

        ## 
        self.parent.remove_layer(self.tile_layer)

        ## Remove parent
        self.parent = None
    
    def draw(self, cr):
        self.parent.call_redraw(self)



class MeasureTool(GObject.GObject):
    __gsignals__ = {}
    def __init__(self):
        GObject.GObject.__init__(self)
        self.parent = None
        self.connection_list = []


        self.p1 = None
        self.p2 = None
        self.measuring_active = False
        #self.selected = []

        self.point_style = vector.FeatureStyle()
        self.point_style.set_color('white', 0.5)
        self.point_style.set_outline_color('red')
        self.point_style.weight = 10

        self.line_style = vector.FeatureStyle()
        self.line_style.set_color('yellow')
        #self.line_style.set_outline_color('red')



        #self.signal_new("map-features-selected", self, GObject.SIGNAL_RUN_FIRST, None, (object,))

    def activate(self, parent):
        ## Set parent object
        self.parent = parent
        ## Setup connection, keeping the reference to each in connection_list
        self.connection_list.append( self.parent.connect("left-click", self.add_click) )
        self.connection_list.append( self.parent.connect("middle-click", self.clear_clicks) )
        self.parent.call_redraw(self)

    def deactivate(self):
        ## Reset tool vars
        self.select_box_active = False
        self.selected = []
        ## Disconnect all connection
        for connect_id in self.connection_list:
            self.parent.disconnect(connect_id)
        
        ## Clear Connection list
        self.connection_list = []

        self.p1 = None
        self.p2 = None

        self.parent.call_redraw(self)

        ## Remove parent
        self.parent = None
    
    def add_click(self, caller, pix_x, pix_y):
        if self.p1:
            #pix_x = self.parent.width - pix_x
            pix_y = self.parent.height - pix_y
            self.p2 = self.parent.pix2geo(pix_x, pix_y)
            
            deg2m = 110570
            x1 = self.p1[0] * deg2m
            y1 = self.p1[1] * deg2m
            x2 = self.p2[0] * deg2m
            y2 = self.p2[1] * deg2m

            d = (((x1-x2)**2)+((y1-y2)**2))**0.5

            print(d) #!! THIS IS NOT CORRECT!!

        else:
            #pix_x = self.parent.width - pix_x
            pix_y = self.parent.height - pix_y
            self.p1 = self.parent.pix2geo(pix_x, pix_y)

        self.parent.call_redraw(self)

    def clear_clicks(self, caller, *args):
        self.p1 = None
        self.p2 = None
        self.parent.call_redraw(self)
    
    def draw(self, cr):
        print('drawing')
        if self.p1:
            ## Draw first click point
            pix1_x, pix1_y = self.parent.geo2pix(*self.p1)
            self.parent.renderer.draw_point(cr, [1], [pix1_x], [pix1_y], self.point_style)
        
        if self.p2:
            ## Draw second click point
            pix2_x, pix2_y = self.parent.geo2pix(*self.p2)
            self.parent.renderer.draw_point(cr, [1], [pix2_x], [pix2_y], self.point_style)

            ## Draw line between points
            pixs_x = [pix1_x, pix2_x]
            pixs_y = [pix1_y, pix2_y]
            self.parent.renderer.draw_line(cr, [2], pixs_x, pixs_y, self.line_style)




##############################
## Structure classes
##############################

class ToolBar(Gtk.Toolbar):
    def __init__(self, window, parent_map):
        Gtk.Toolbar.__init__(self)

        self.window = window
        self.map = parent_map


        ## Setup select tool & toolbar button
        self.select_tool = SelectTool()
        self.select_tool_button = Gtk.ToggleToolButton()
        self.select_tool_button.set_icon_name('tool-pointer')
        self.select_tool_button.set_tooltip_text("Select Tool")
        self.select_tool_button.connect('toggled', self.select_tool_button_toggled)
        self.insert(self.select_tool_button, 0)

        #sep = Gtk.SeparatorToolItem()
        #self.insert(sep, 1)

        ## Setup identify tool & toolbar button
        self.id_tool = IdentifyTool(self.window)
        self.id_tool_button = Gtk.ToggleToolButton()
        self.id_tool_button.set_icon_name('search')
        self.id_tool_button.set_tooltip_text("Select Tool")
        self.id_tool_button.connect('toggled', self.id_tool_button_toggled)
        self.insert(self.id_tool_button, 1)
        
        ## Setup tile layer tool & button
        self.tile_map_tool = TileLayerTool()
        self.map_tool_button = Gtk.ToggleToolButton()
        self.map_tool_button.set_icon_name('maps')
        self.map_tool_button.set_tooltip_text("Toggle OpenStreetMaps Layer")
        self.map_tool_button.connect('toggled', self.map_tool_button_toggled)
        self.insert(self.map_tool_button, 2)

        ## Setup measure  tool & button
        self.measure_tool = MeasureTool()
        self.measure_tool_button = Gtk.ToggleToolButton()
        self.measure_tool_button.set_icon_name('screenruler')
        self.measure_tool_button.set_tooltip_text("Measure distance")
        self.measure_tool_button.connect('toggled', self.measure_tool_button_toggled)
        self.insert(self.measure_tool_button, 3)


    def select_tool_button_toggled(self, caller):
        if self.select_tool_button.get_active():
            self.map.add_tool(self.select_tool)
        else:
            self.select_tool.deselect_all(self)
            self.map.remove_tool(self.select_tool)
    
    def id_tool_button_toggled(self, caller):
        if self.id_tool_button.get_active():
            self.map.add_tool(self.id_tool)
        else:
            self.id_tool.deselect_all(self)
            self.map.remove_tool(self.id_tool)

    def map_tool_button_toggled(self, caller):
        if self.map_tool_button.get_active():
            self.map.add_tool(self.tile_map_tool)
        else:
            self.map.remove_tool(self.tile_map_tool)

    def measure_tool_button_toggled(self, caller):
        if self.measure_tool_button.get_active():
            self.map.add_tool(self.measure_tool)
        else:
            self.map.remove_tool(self.measure_tool)


class StatusBar(Gtk.HBox):
    def __init__(self, window, parent_map):
        Gtk.HBox.__init__(self)
        self.map = parent_map

        ## Add a location label
        self.pack_start(Gtk.Label("Location:"), False, False, 0)
        
        ## Setup & add location tracker
        self.location_tracker = Gtk.Entry()
        self.location_tracker.set_text("0, 0")
        self.pack_start(self.location_tracker, False, False, 10)
        
        ## Setup signals
        self.location_tracker.connect('activate', self.loc_label_input_slot)
        self.map.connect('location-changed', self.location_changed_slot)
        

        projection = self.map._projection
        p2 = projection.srs
        projection = projection.crs.to_epsg()
        projection = f"Projection: EPSG:{str(projection)}"
        #@
        self.projection_status_label = Gtk.Label(projection)
        self.projection_status_label.set_tooltip_text(p2)
        self.pack_start(self.projection_status_label, False, False, 10)

    def loc_label_input_slot(self, caller, *args):
        location_string = self.location_tracker.get_text()
        self.map.grab_focus()
        lat, lon = location_string.split(',')
        lat = lat.strip(','); lon = lon.strip(',')
        lat = float(lat); lon = float(lon)
        self.map.set_location(lat, lon)
        self.map.call_rerender(self)
    
    def location_changed_slot(self, caller, geox, geoy, projx, projy):
        self.location_tracker.set_text(f"{round(geoy, 4)}, {round(geox, 4)}")

class MainWindow(Gtk.Window):
    """ The main application window """
    def __init__(self):
        """ Defines window properties, & adds child widgets. """
        ## Initialize parents: Gtk.Window & Gtk.GObject
        Gtk.Window.__init__(self)
        GObject.GObject.__init__(self)

        ## Set window properties
        self.set_title("MapViewer")
        self.resize(1700, 900)
        self.set_border_width(0)

        ## Enable and setup drag and drop for window
        self.connect('drag_data_received', self.on_drag_data_received)
        self.drag_dest_set( Gtk.DestDefaults.MOTION | Gtk.DestDefaults.HIGHLIGHT | Gtk.DestDefaults.DROP, [Gtk.TargetEntry.new("text/uri-list", 0, 80)], Gdk.DragAction.COPY)
        
        ## Setup MapCanvas Widget
        self.map = MapCanvasGTK.MapCanvas()

        ## Setup LayerView Widget
        layer_view = LayerView(self.map)

        ## Connect map signals
        self.map.connect('layer-added', layer_view.layer_added_slot)
        self.map.connect('layer-removed', layer_view.layer_removed_slot)

        #####################
        ###    Layout     ###
        #####################

        ## Create main window layout, and add layout to window(self)
        self.layout = Gtk.VBox()
        self.add(self.layout)

        ## Setup top toolbar widget, and add to main layout
        self.toolbar = ToolBar(self, self.map)
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

        ''' Over widget add
        over_widget = Gtk.Button("Press Me")
        over_widget.set_valign(Gtk.Align.START)
        over_widget.set_halign(Gtk.Align.START)
        over_widget.set_margin_top(30)
        over_widget.set_margin_left(30)
        self.map_overlay.add_overlay(over_widget)
        #'''
    
        ## Put Map Overlay into map_area
        map_area.pack_start(self.map_overlay, True, True, 0)

        self.statusbar = StatusBar(self, self.map)
        map_area.pack_start(self.statusbar, False, False, 0)


    def add_from_path(self, path):
        """ """
        file_extension = path.split(".")[-1]

        ## If Vector data, create a New Vector Layer
        if file_extension in ('shp', 'geojson'): 
            layer = VectorLayer.from_path(path)
            color_list = ['salmon', 'goldenrod', 'firebrick', 'steelblue', 'aquamarine', 'seagreen', 'powderblue', 'cornflowerblue', 'crimson', 'darkgoldenrod', 'chocolate', 'darkmagenta', 'darkolivegreen', 'darkturquoise', 'deeppink']
            rand_color = color_list[randint(0, len(color_list)-1)]
            for f in layer: f.set_color(rand_color)
            #layer.set_opacity(0.5)
        
        elif file_extension in ('geotiff'):
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


##############################
## ././. classes
##############################

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
    main()

