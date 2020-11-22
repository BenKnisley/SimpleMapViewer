"""
Author: Ben Knisley [benknisley@gmail.com]
Date: 21 November, 2020
"""
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, Gio, GObject

## Make GTK thread aware
GObject.threads_init()



class ContextMenu(Gtk.Menu):
    def __init__(self, parent_layerview):
        Gtk.Menu.__init__(self)
        self.parent = parent_layerview
        self.map = self.parent.parent_map

        ## Hold selected layer to make availabl to all methods
        self.selected_layer = None

        ##
        self.item_print_about = Gtk.MenuItem("About")
        self.append(self.item_print_about)
        self.item_print_about.connect("activate", self.about_slot)
        
        ##
        self.item_focus = Gtk.MenuItem("Focus on Layer")
        self.append(self.item_focus)
        self.item_focus.connect("activate", self.slot_focus)

        ##
        self.item_delete = Gtk.MenuItem("Delete Layer")
        self.append(self.item_delete)
        self.item_delete.connect("activate", self.slot_delete)

        ##
        self.show_all()
    

    def popup(self, selected_layer, click_event):
        super().popup(None, None, None, None, 3, click_event.time)
        self.selected_layer = selected_layer
    
    def about_slot(self, caller):
        ## Setup a delete confirmation window
        box = Gtk.MessageDialog(transient_for=self.get_toplevel(), title=self.selected_layer.name, text=str(self.selected_layer))
        #box.get_content_area().add(Gtk.Label("Are you sure you want to delete the layer?"))
        box.add_buttons(Gtk.STOCK_OK, True)
        box.show_all()

        box.run()
        box.destroy()
    
    def slot_delete(self, caller):
        ## Setup a delete confirmation window
        box = Gtk.MessageDialog(transient_for=self.get_toplevel(), title="Remove Layer", text="Are you sure you remove this layer?")
        #box.get_content_area().add(Gtk.Label("Are you sure you want to delete the layer?"))
        box.add_buttons(Gtk.STOCK_YES, True, Gtk.STOCK_NO, False)
        box.show_all()

        ## Get response
        delete_response = box.run()
        box.destroy()

        ## If 
        if delete_response:
            self.map.remove_layer(self.selected_layer)

    def slot_focus(self, caller):
        self.selected_layer.focus()
        self.map.call_rerender(self)

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

        self.set_reorderable(True)

        ## Setup a single column as a model
        rendererText = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("                                   Map Layers                                   ", rendererText, text=1)
        self.append_column(column)

        ## Connect selection changes with selection_changed_slot
        selection_watcher = self.get_selection()
        selection_watcher.connect("changed", self.selection_changed_slot)
        #self.store.connect("row-inserted", self.ping1)
        self.store.connect("row-deleted", self.push_model_to_layer_list)

        self.connect('button-press-event' , self.mouse_click_slot)

        ###########
        ## Set up right click menu
        self.context_menu = ContextMenu(self)


    def push_model_to_layer_list(self, treemodel, path):
        """ Sets current order of items to maps layer list """
        ## 
        for i, iter in enumerate(treemodel):
            l = len(self.parent_map._layer_list) - 1
            self.parent_map._layer_list[l - i] = iter[0]

        self.parent_map.call_rerender(self)
        self.parent_map.call_redraw(self)
    
        #for layer in self.parent_map._layer_list:

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
        self.store.prepend([layer, layer.name])

        ## Set selection new layer
        index = 0# len(self.store) - 1
        path = Gtk.TreePath.new_from_indices([index])
        self.set_cursor_on_cell(path, None, None, False)

    def layer_removed_slot(self, caller, layer):
        """
        Removes a given MapLayer to the layer list
        """
        #!! THIS IS A HACK AND I SHOULD FIND A BETTER WAY
        for r in self.store:
            if r[0] == layer:
                self.store.remove(r.iter)

    def mouse_click_slot(self, caller, event):
        ## If right click, & on layer; then popup context menu
        if event.button == 3:
            x = int(event.x); y = int(event.y)
            at_click = self.get_path_at_pos(x, y)
            if at_click:
                path = at_click[0]
                clicked_layer = self.store[path][0]
                self.context_menu.popup(clicked_layer, event)


         

