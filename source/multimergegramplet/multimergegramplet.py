#
# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2015-2016 Nick Hall
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, 
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#
#
# PlaceTool
# ---------
# Author: kari.kujansuu@gmail.com
# 9 Jun 2019
#
# Gramplet to change properties of multiple places at the same time. See README.
 
import json
import pprint
import re
import traceback

from gi.repository import Gtk, Gdk, GObject

from gramps.gen.plug import Gramplet
from gramps.gui.plug import tool
from gramps.gui.utils import ProgressMeter
from gramps.gen.db import DbTxn
from gramps.gen.lib import Place, PlaceRef, PlaceName, PlaceType, Note, Tag
from gramps.gen.display.name import displayer as name_displayer

from gramps.gen.merge import MergePersonQuery
from gramps.gen.merge import MergeFamilyQuery
from gramps.gen.merge import MergePlaceQuery
from gramps.gen.merge import MergeSourceQuery
from gramps.gen.merge import MergeRepositoryQuery
from gramps.gen.merge import MergeNoteQuery

from gramps.gui.dialog import OkDialog, ErrorDialog

from gramps.gen.const import GRAMPS_LOCALE as glocale
try:
    _trans = glocale.get_addon_translator(__file__)
except ValueError:
    _trans = glocale.translation
_ = _trans.gettext

class MultiMergeGramplet(Gramplet):

    def init(self):
        self.root = self.__create_gui()
        self.gui.get_container_widget().remove(self.gui.textview)
        self.gui.get_container_widget().add_with_viewport(self.root)
        self.selected_handle = None
        self.set_tooltip(_("Merge multiple objects"))

    def db_changed(self):
        self.__clear(None)
        

    def __clear(self, obj):
        self.selected_handle = None        
    
    def __create_gui(self):
        vbox = Gtk.VBox(orientation=Gtk.Orientation.VERTICAL)
        vbox.set_spacing(4)

        label = Gtk.Label(_("This gramplet allows merging multiple objects"))
        label.set_margin_top(29)
        vbox.pack_start(label, False, True, 0)

        but_apply = Gtk.Button(label=_('Merge selected objects'))
        but_apply.set_border_width(29)
        but_apply.connect("clicked", self.__apply)
        vbox.pack_start(but_apply, False, True, 0)

        vbox.show_all()
        return vbox

    def cb_set_primary(self, obj, value):
        self.primary_handle = value

    def cb_set_option(self, obj, value):
        self.option = value
        
    def person_name(self, person_handle):
        if not person_handle: return ""
        person = self.dbstate.db.get_person_from_handle(person_handle)
        return name_displayer.display(person)

        
    def get_person_title(self, obj):
        return "{gramps_id}: {name}".format(gramps_id=obj.get_gramps_id(), name=name_displayer.display(obj))

    def get_family_title(self, obj):
        husb = self.person_name(obj.get_father_handle())
        wife = self.person_name(obj.get_mother_handle())
        return "{gramps_id}: {husb}, {wife}".format(gramps_id=obj.get_gramps_id(), husb=husb, wife=wife )   

    def get_place_title(self, obj):
        return "{gramps_id}: {name}".format(gramps_id=obj.get_gramps_id(), name=obj.get_name().get_value())

    def get_source_title(self, obj):
        return "{gramps_id}: {name}".format(gramps_id=obj.get_gramps_id(), name=obj.get_title())

    def get_repository_title(self, obj):
        return "{gramps_id}: {name}".format(gramps_id=obj.get_gramps_id(), name=obj.get_name())

    def get_note_title(self, obj):
        return "{gramps_id}: {text}".format(gramps_id=obj.get_gramps_id(), text=obj.get()[0:20].replace("\n"," "))

    def compute_possible_handles(self, selected_handles):
        has_hather_handle = False
        has_mother_handle = False
        for i,handle in enumerate(selected_handles):
            obj = self.dbstate.db.get_family_from_handle(handle)
            father_handle = obj.get_father_handle()
            if father_handle: has_hather_handle = True
            mother_handle = obj.get_mother_handle()
            if mother_handle: has_mother_handle = True

        new_handles = []
        for i,handle in enumerate(selected_handles):
            obj = self.dbstate.db.get_family_from_handle(handle)
            father_handle = obj.get_father_handle()
            mother_handle = obj.get_mother_handle()
            if ((not father_handle and has_hather_handle) or
                (not mother_handle and has_mother_handle)): 
                    continue
            new_handles.append(handle)

        return new_handles

    def __apply(self,obj):
        category = self.uistate.viewmanager.active_page.get_category()
        print("category=",category)
        if category == 'People':
            mergeclass = MergePersonQuery
            objclass = 'Person'
            getfunc = self.dbstate.db.get_person_from_handle
            titlefunc = self.get_person_title
            dbstate = self.dbstate.db  # MergePersonQuery has a different argument than the others
        if category == 'Families':
            mergeclass = MergeFamilyQuery
            objclass = 'Family'
            getfunc = self.dbstate.db.get_family_from_handle
            titlefunc = self.get_family_title
            dbstate = self.dbstate.db  # MergeFamilyQuery has a different argument than the rest
        if category == 'Places':
            mergeclass = MergePlaceQuery
            objclass = 'Place'
            getfunc = self.dbstate.db.get_place_from_handle
            titlefunc = self.get_place_title
            dbstate = self.dbstate
        if category == 'Sources':
            mergeclass = MergeSourceQuery
            objclass = 'Source'
            getfunc = self.dbstate.db.get_source_from_handle
            titlefunc = self.get_source_title
            dbstate = self.dbstate
        if category == 'Repositories':
            mergeclass = MergeRepositoryQuery
            objclass = 'Repository'
            getfunc = self.dbstate.db.get_repository_from_handle
            titlefunc = self.get_repository_title
            dbstate = self.dbstate
        if category == 'Notes':
            mergeclass = MergeNoteQuery
            objclass = 'Note'
            getfunc = self.dbstate.db.get_note_from_handle
            titlefunc = self.get_note_title
            dbstate = self.dbstate
        
        # from /gramps 5.1/gramps/gui/merge/mergeplace.py
        selected_handles = self.uistate.viewmanager.active_page.selected_handles()

        if len(selected_handles) < 2:
            ErrorDialog(_("Error"),
                     _("Select at least two rows"),
                     parent=self.uistate.window)
            return

        if category == 'Families':
            possible_handles = self.compute_possible_handles(selected_handles)
        else:
            possible_handles = selected_handles

        #print("selected_handles =",  selected_handles )
        #print("possible_handles =",  possible_handles )
        
        if len(possible_handles) == 0:
            ErrorDialog(_("Error"),
                     _("Impossible to merge"),
                     parent=self.uistate.window)
            return
        
        if len(possible_handles) == 1:
            self.primary_handle = possible_handles[0]
        else: # ask the user
            dialog = Gtk.Dialog(title=_("Select primary object"), parent=None,
                                flags=Gtk.DialogFlags.MODAL)
            lbl1 = Gtk.Label(_("Select primary object"))
            dialog.vbox.pack_start(lbl1, False, False, 5)
            self.primary_handle = None
            group = None
            for handle in possible_handles:
                obj = getfunc(handle)
                title = titlefunc(obj)
                group = Gtk.RadioButton.new_with_label_from_widget(group, title)
                group.connect("toggled", self.cb_set_primary, handle)
                dialog.vbox.pack_start(group, False, True, 0)
                # first one is the default:
                if self.primary_handle is None:
                    group.set_active(True) 
                    self.primary_handle = handle
            if category == 'Notes':
                box2 = Gtk.VBox()
                box2.set_margin_left(20)
                #box2.pack_start(Gtk.VSeparator(), False, True, 0)
                group = None
                self.option = 1
                group = Gtk.RadioButton.new_with_label_from_widget(group, _("Use text from primary note only"))
                group.connect("toggled", self.cb_set_option, 1)
                group.set_active(True) 
                box2.pack_start(group, False, True, 0)
                group = Gtk.RadioButton.new_with_label_from_widget(group, _("Combine text from all notes"))
                group.connect("toggled", self.cb_set_option, 2)
                box2.pack_start(group, False, True, 0)
                dialog.vbox.pack_start(box2, False, True, 10)
                        
            dialog.add_button("Ok", Gtk.ResponseType.OK)
            dialog.add_button("Cancel", Gtk.ResponseType.CANCEL)
            dialog.set_default_response(Gtk.ResponseType.OK)
            dialog.show_all()
            result = dialog.run()
            dialog.destroy()
            if result != Gtk.ResponseType.OK: return
                
        phoenix = None
        for handle in selected_handles:
            if handle == self.primary_handle: continue # don't merge with self
            phoenix = getfunc(self.primary_handle)  # must retrieve a fresh copy
            titanic = getfunc(handle)
            query = mergeclass(dbstate, phoenix, titanic)
            if category == 'Notes':
                if self.option == 2:
                    phoenix.set( phoenix.get() + "\n\n" + titanic.get())
            query.execute()
        if phoenix:
            self.uistate.set_active(phoenix.get_handle(), objclass)  # put cursor on the combined object


