#
# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2015-2016 Nick Hall
# Copyright (C) 2019-2021 Kari Kujansuu
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
# MultimergeGramplet
# ------------------
# Author: kari.kujansuu@gmail.com
# Gramplet to merge multiple objects at the same time. See README.


import json
import pprint
import re
import traceback

from collections import defaultdict
from contextlib import contextmanager
from types import SimpleNamespace

from gi.repository import Gtk, Gdk, GObject

from gramps.gen.plug import Gramplet
from gramps.gui.plug import tool
from gramps.gui.utils import ProgressMeter
from gramps.gen.db import DbTxn
from gramps.gen.lib import Place, PlaceRef, PlaceName, PlaceType, Note, Tag
from gramps.gen.display.name import displayer as name_displayer
from gramps.gen.display.place import displayer as place_displayer

from gramps.gen.merge import MergePersonQuery
from gramps.gen.merge import MergeFamilyQuery
from gramps.gen.merge import MergeEventQuery
from gramps.gen.merge import MergeCitationQuery
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


class DummyTxn:
    "Implements nested transactions"

    def __init__(self, trans):
        if trans is None:
            raise RuntimeError(_("Need a transaction"))
        self.trans = trans

        class _Txn:
            def __init__(self, msg, db):
                pass

            def __enter__(self):
                return trans

            def __exit__(self, *args):
                return False

        self.txn = _Txn

@contextmanager
def nested_txn(title, db, mergemodule):
    with DbTxn(title, db) as trans:
        saved_dbtxn = mergemodule.DbTxn
        mergemodule.DbTxn = DummyTxn(trans).txn
        try:
            yield trans
        finally:
            mergemodule.DbTxn = saved_dbtxn


class Options:
    pass

def build_context(dbstate, category):
        
    def person_name(person_handle, db):
        if not person_handle:
            return ""
        person = db.get_person_from_handle(person_handle)
        return name_displayer.display(person)

    def get_person_title(obj):
        return "{gramps_id}: {name}".format(
            gramps_id=obj.get_gramps_id(), name=name_displayer.display(obj)
        )

    def get_family_title(obj):
        husb = person_name(obj.get_father_handle(), db=dbstate)
        wife = person_name(obj.get_mother_handle(), db=dbstate)
        return "{gramps_id}: {husb}, {wife}".format(
            gramps_id=obj.get_gramps_id(), husb=husb, wife=wife
        )

    def get_place_title(obj):
        return "{gramps_id}: {name}".format(
            gramps_id=obj.get_gramps_id(), 
                #name=obj.get_name().get_value()
                name=place_displayer.display(dbstate.db, obj)
        )

    def get_citation_title(obj):
        return "{gramps_id}: {name}".format(
            gramps_id=obj.get_gramps_id(), name=obj.get_page()
        )

    def get_event_title(obj):
        return "{gramps_id}: {type}".format(
            gramps_id=obj.get_gramps_id(), type=obj.get_type()
        )

    def get_source_title(obj):
        return "{gramps_id}: {name}".format(
            gramps_id=obj.get_gramps_id(), name=obj.get_title()
        )

    def get_repository_title(obj):
        return "{gramps_id}: {name}".format(
            gramps_id=obj.get_gramps_id(), name=obj.get_name()
        )

    def get_media_title(obj):
        return "{gramps_id}: {name}".format(
            gramps_id=obj.get_gramps_id(), name=obj.get_description()
        )

    def get_note_title(obj):
        return "{gramps_id}: {text}".format(
            gramps_id=obj.get_gramps_id(), text=obj.get()[0:20].replace("\n", " ")
        )

        
    gethandlesfunc = None
    if category == "People":
        import gramps.gen.merge.mergepersonquery as mergemodule
        mergeclass = mergemodule.MergePersonQuery
        objclass = "Person"
        getfunc = dbstate.db.get_person_from_handle
        titlefunc = get_person_title
        dbstate = (
            dbstate.db
        )  # MergePersonQuery has a different argument than the others

    if category == "Families":
        import gramps.gen.merge.mergefamilyquery as mergemodule
        mergeclass = mergemodule.MergeFamilyQuery
        objclass = "Family"
        getfunc = dbstate.db.get_family_from_handle
        titlefunc = get_family_title
        dbstate = (
            dbstate.db
        )  # MergeFamilyQuery has a different argument than the rest

    if category == "Places":
        import gramps.gen.merge.mergeplacequery as mergemodule
        mergeclass = mergemodule.MergePlaceQuery
        objclass = "Place"
        gethandlesfunc = dbstate.db.get_place_handles
        getfunc = dbstate.db.get_place_from_handle
        titlefunc = get_place_title

    if category == "Events":
        import gramps.gen.merge.mergeeventquery as mergemodule
        mergeclass = mergemodule.MergeEventQuery
        objclass = "Event"
        getfunc = dbstate.db.get_event_from_handle
        titlefunc = get_event_title

    if category == "Citations":
        import gramps.gen.merge.mergecitationquery as mergemodule
        mergeclass = mergemodule.MergeCitationQuery
        objclass = "Citation"
        getfunc = dbstate.db.get_citation_from_handle
        titlefunc = get_citation_title

    if category == "Sources":
        import gramps.gen.merge.mergesourcequery as mergemodule
        mergeclass = mergemodule.MergeSourceQuery
        objclass = "Source"
        gethandlesfunc = dbstate.db.get_source_handles
        getfunc = dbstate.db.get_source_from_handle
        titlefunc = get_source_title

    if category == "Repositories":
        import gramps.gen.merge.mergerepositoryquery as mergemodule
        mergeclass = mergemodule.MergeRepositoryQuery
        objclass = "Repository"
        gethandlesfunc = dbstate.db.get_repository_handles
        getfunc = dbstate.db.get_repository_from_handle
        titlefunc = get_repository_title

    if category == "Media":
        import gramps.gen.merge.mergemediaquery as mergemodule
        mergeclass = mergemodule.MergeMediaQuery
        objclass = "Media"
        getfunc = dbstate.db.get_media_from_handle
        titlefunc = get_media_title

    if category == "Notes":
        import gramps.gen.merge.mergenotequery as mergemodule
        mergeclass = mergemodule.MergeNoteQuery
        objclass = "Note"
        getfunc = dbstate.db.get_note_from_handle
        titlefunc = get_note_title

    return SimpleNamespace(
        mergemodule = mergemodule,
        mergeclass = mergeclass,
        objclass = objclass,
        gethandlesfunc = gethandlesfunc,
        getfunc = getfunc,
        titlefunc = titlefunc,
        dbstate = dbstate,
        )


class MultiMergeGramplet(Gramplet):
    def init(self):
        self.category = self.gui.view.category
        self.root = self.__create_gui()
        self.gui.get_container_widget().remove(self.gui.textview)
        self.gui.get_container_widget().add_with_viewport(self.root)
        self.selected_handle = None
        self.note_option = None
        self.set_tooltip(_("Merge multiple objects"))
        self.options = Options()

    def db_changed(self):
        self.__clear(None)

    def __clear(self, obj):
        self.selected_handle = None

    def __create_gui(self):
        vbox = Gtk.VBox(orientation=Gtk.Orientation.VERTICAL)
        vbox.set_spacing(4)

        label = Gtk.Label(_("Merges multiple objects with one click"))
        label.set_margin_top(20)
        vbox.pack_start(label, False, True, 0)

        but_apply = Gtk.Button(label=_("Merge selected objects"))
        but_apply.set_border_width(12)
        but_apply.connect("clicked", self.__apply)
        vbox.pack_start(but_apply, False, True, 0)

        if self.category in ["Places", "Sources", "Repositories"]:
            nb = Gtk.Notebook()
            nb.append_page(vbox,Gtk.Label(_("Merge selected")))
            
            vbox = Gtk.VBox(orientation=Gtk.Orientation.VERTICAL)

            label = Gtk.Label(label=_("Automatically merges objects with the same name/title"))
            label.set_margin_top(20)
            vbox.pack_start(label, False, True, 0)

            but_apply = Gtk.Button(label=_("Automerge"))
            but_apply.set_border_width(12)
            but_apply.connect("clicked", self.automerge)
            vbox.pack_start(but_apply, False, True, 0)


            grid = Gtk.Grid()
            grid.set_margin_left(10)
            self.but_selected_places = Gtk.RadioButton.new_with_label_from_widget(None, _("Selected objects"))
            self.but_all_places = Gtk.RadioButton.new_with_label_from_widget(self.but_selected_places, _("All objects"))
            grid.attach(self.but_selected_places, 0, 0, 1, 1)
            grid.attach(self.but_all_places, 0, 1, 1, 1)

            if self.category == "Places":
                self.but_same_titles = Gtk.RadioButton.new_with_label_from_widget(None, _("With same titles"))
                self.but_same_names = Gtk.RadioButton.new_with_label_from_widget(self.but_same_titles, _("With same names"))
                self.but_type_match = Gtk.CheckButton(_("Types must match"))
                self.but_type_match.set_active(True) 
                self.but_type_match.set_tooltip_text(_("If checked then places are merged only if they both have the same type")) 
                grid.attach(self.but_same_titles, 1, 0, 1, 1)
                grid.attach(self.but_same_names , 1, 1, 1, 1)
                grid.attach(self.but_type_match , 1, 2, 1, 1)

            if self.category == "Sources":
                self.but_author_match = Gtk.CheckButton(_("Authors must match"))
                self.but_author_match.set_active(True) 
                self.but_author_match.set_tooltip_text(_("If checked then sources are merged only if they have both the same title and same author")) 
                grid.attach(self.but_author_match, 1, 0, 1, 1)
                
            vbox.pack_start(grid, False, True, 0)
            self.page = vbox
            self.output_window = None
            self.label_msg = Gtk.Label("")
            self.label_msg.set_margin_top(10)
            self.label_msg.set_halign(Gtk.Align.START)
            vbox.pack_start(self.label_msg, False, True, 0)

            nb.append_page(vbox, Gtk.Label(_("Automerge")))
            nb.show_all()
            return nb

        vbox.show_all()
        return vbox

    def cb_set_primary(self, obj, value):
        self.primary_handle = value

    def cb_set_option(self, obj, value):
        self.options.note_option = value

    def compute_possible_handles(self, selected_handles):
        has_father_handle = False
        has_mother_handle = False
        for i, handle in enumerate(selected_handles):
            obj = self.dbstate.db.get_family_from_handle(handle)
            father_handle = obj.get_father_handle()
            if father_handle:
                has_father_handle = True
            mother_handle = obj.get_mother_handle()
            if mother_handle:
                has_mother_handle = True

        new_handles = []
        for i, handle in enumerate(selected_handles):
            obj = self.dbstate.db.get_family_from_handle(handle)
            father_handle = obj.get_father_handle()
            mother_handle = obj.get_mother_handle()
            if (not father_handle and has_father_handle) or (
                not mother_handle and has_mother_handle
            ):
                continue
            new_handles.append(handle)

        return new_handles

        
    def __apply(self, _widget):
        # from /gramps 5.1/gramps/gui/merge/mergeplace.py
        context = build_context(self.dbstate, self.category)
        selected_handles = self.uistate.viewmanager.active_page.selected_handles()

        if len(selected_handles) < 2:
            ErrorDialog(
                _("Error"), _("Select at least two rows"), parent=self.uistate.window
            )
            return

        if self.category == "Families":
            possible_handles = self.compute_possible_handles(selected_handles)
        else:
            possible_handles = selected_handles

        # print("selected_handles =",  selected_handles )
        # print("possible_handles =",  possible_handles )

        if len(possible_handles) == 0:
            ErrorDialog(
                _("Error"), _("Impossible to merge"), parent=self.uistate.window
            )
            return

        if len(possible_handles) == 1:
            self.primary_handle = possible_handles[0]
        else:  # ask the user
            dialog = Gtk.Dialog(
                title=_("Select primary object"),
                parent=None,
                flags=Gtk.DialogFlags.MODAL,
            )
            lbl1 = Gtk.Label(_("Select primary object"))
            dialog.vbox.pack_start(lbl1, False, False, 5)
            self.primary_handle = None
            group = None
            for handle in possible_handles:
                obj = context.getfunc(handle)
                title = context.titlefunc(obj)
                group = Gtk.RadioButton.new_with_label_from_widget(group, title)
                group.connect("toggled", self.cb_set_primary, handle)
                dialog.vbox.pack_start(group, False, True, 0)
                # first one is the default:
                if self.primary_handle is None:
                    group.set_active(True)
                    self.primary_handle = handle
            if self.category == "Notes":
                box2 = Gtk.VBox()
                box2.set_margin_left(20)
                # box2.pack_start(Gtk.VSeparator(), False, True, 0)
                group = None
                self.options.note_option = 1
                group = Gtk.RadioButton.new_with_label_from_widget(
                    group, _("Use text from primary note only")
                )
                group.connect("toggled", self.cb_set_option, 1)
                group.set_active(True)
                box2.pack_start(group, False, True, 0)
                group = Gtk.RadioButton.new_with_label_from_widget(
                    group, _("Combine text from all notes")
                )
                group.connect("toggled", self.cb_set_option, 2)
                box2.pack_start(group, False, True, 0)
                dialog.vbox.pack_start(box2, False, True, 10)

            dialog.add_button("Ok", Gtk.ResponseType.OK)
            dialog.add_button("Cancel", Gtk.ResponseType.CANCEL)
            dialog.set_default_response(Gtk.ResponseType.OK)
            dialog.show_all()
            result = dialog.run()
            dialog.destroy()
            if result != Gtk.ResponseType.OK:
                return

        engine = MultiMergeEngine(context, self.dbstate, self.category, selected_handles, self.options)
        title = _("Merging {} {}").format(len(selected_handles), self.category)
        with nested_txn(title, self.dbstate.db, context.mergemodule) as trans:
            phoenix = None
            for handle in selected_handles:
                if handle == self.primary_handle:
                    continue  # don't merge with self
                phoenix = context.getfunc(self.primary_handle)  # must retrieve a fresh copy
                titanic = context.getfunc(handle)
                engine.domerge(context, phoenix, titanic)
        if phoenix:
            self.uistate.set_active(
                phoenix.get_handle(), context.objclass
            )  # put cursor on the combined object

    def display_results(self, merged):
        if self.output_window: self.output_window.destroy()
        self.output_window = Gtk.ScrolledWindow()
        self.output_window.set_min_content_height(300)

        box = Gtk.VBox()
        box.set_margin_left(10)
        box.set_margin_top(15)
            
        self.label_msg.set_label(_("Merged {} {}:").format(len(merged), self.category.lower()))
        for name in sorted(merged):
            if type(name) == tuple:
                if name[1]:
                    label = name[0] + " [" + name[1] + "]"
                else:
                    label = name[0]
            else:
                label = name
            hdr = Gtk.Expander(label=label)
            hdr.set_resize_toplevel(True)
            msg = "\n".join(sorted(merged[name]))
            label2 = Gtk.Label(msg)
            label2.set_halign(Gtk.Align.START)
            label2.set_margin_left(20)
            hdr.add(label2)
            box.pack_start(hdr, False, True, 0)
        
        self.output_window.add(box)
        self.page.pack_start(self.output_window, False, True, 0)
        self.page.show_all()
        
    def automerge(self, _widget):
        context = build_context(self.dbstate, self.category)
        if self.but_selected_places.get_active():
            handles = self.uistate.viewmanager.active_page.selected_handles()
        else:
            handles = context.gethandlesfunc()
        self.options.note_option = self.note_option
        if self.category == "Places":
            self.options.same_names = self.but_same_names.get_active()
            self.options.same_types = self.but_type_match.get_active() 
        if self.category == "Sources":
            self.options.same_authors=self.but_author_match.get_active()
            
        engine = MultiMergeEngine(context, self.dbstate, self.category, handles, self.options)
        merged = engine.automerge()
        self.display_results(merged)
        
class MultiMergeEngine:
    def __init__(self, context, dbstate, category, handles, options):
        self.dbstate = dbstate
        self.context = context
        self.category = category
        self.handles = handles
        self.options = options

    def automerge(self):
        context = self.context
        objs = {}
        merged = {} 
        title = _("Auto merging {}").format(self.category)
        with nested_txn(title, self.dbstate.db, context.mergemodule) as trans:
            for handle in self.handles:
                obj = context.getfunc(handle)
                obj_title = context.titlefunc(obj) 
                objkey = self.get_objkey(context, obj)
                if objkey in objs:
                    basehandle = objs[objkey]
                    p = context.getfunc(basehandle)
                    if objkey not in merged:
                        merged[objkey] = [context.titlefunc(p)]
                    merged[objkey].append(obj_title)
                    self.domerge(context, p, obj)
                else:
                    objs[objkey] = handle
        return merged
            
    def domerge(self, context, phoenix, titanic):
        query = context.mergeclass(context.dbstate, phoenix, titanic)
        if self.category == "Notes":
            if self.options.note_option == 2:
                phoenix.append("\n\n")
                phoenix.append(titanic.get_styledtext())
        query.execute()

    def get_objkey(self, context, obj):
        if self.category == "Places":
            if self.options.same_names:
                placename = obj.get_name().get_value()
            else:
                placename = place_displayer.display(self.dbstate.db, obj)
            if self.options.same_types:
                return (placename, obj.get_type().xml_str())
            else:
                return placename
        if self.category == "Sources":
            stitle = obj.get_title()
            if self.options.same_authors:
                return (stitle, obj.get_author())
            else:
                return stitle
        if self.category == "Repositories":
            return obj.get_name()
        raise RuntimeError("Unsupported category: " + self.category)
        
        
