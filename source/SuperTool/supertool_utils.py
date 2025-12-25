# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2021-2023       Kari Kujansuu
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

# -------------------------------------------------------------------------
#
# Standard Python modules
#
# -------------------------------------------------------------------------
import collections
import functools
import os
import re
import sys
import textwrap

from pprint import pprint
from types import SimpleNamespace
from builtins import str

try:
    from typing import TYPE_CHECKING
    from typing import Any
    from typing import Callable
    from typing import Dict
    from typing import Generator
    from typing import Iterator
    from typing import List
    from typing import Optional
    from typing import Set
    from typing import Tuple
    from typing import Type
    from typing import Union
    from gramps.gen.user import User
    from gramps.gen.db import DbGeneric
    #from gramps.gen.lib import PrimaryObject
except:
    TYPE_CHECKING = False

from gi.repository import Gtk

# -------------------------------------------------------------------------
#
# Gramps modules
#
# -------------------------------------------------------------------------
from gramps.gen.db import DbGeneric

from gramps.gen.lib import PrimaryObject

from gramps.gen.lib import Address
from gramps.gen.lib import Attribute
from gramps.gen.lib import AttributeType
from gramps.gen.lib import ChildRef
from gramps.gen.lib import ChildRefType
from gramps.gen.lib import Citation
from gramps.gen.lib import Date as GrampsDate
from gramps.gen.lib import DateError
from gramps.gen.lib import Event
from gramps.gen.lib import EventRef
from gramps.gen.lib import EventRoleType
from gramps.gen.lib import EventType
from gramps.gen.lib import Family
from gramps.gen.lib import FamilyRelType
#from gramps.gen.lib import GenderStats
from gramps.gen.lib import GrampsType
from gramps.gen.lib import LdsOrd
from gramps.gen.lib import Location
from gramps.gen.lib import MarkerType
from gramps.gen.lib import Media
from gramps.gen.lib import MediaRef
from gramps.gen.lib import Name
from gramps.gen.lib import NameOriginType
from gramps.gen.lib import NameType
from gramps.gen.lib import Note
from gramps.gen.lib import NoteType
from gramps.gen.lib import Person
from gramps.gen.lib import PersonRef
from gramps.gen.lib import Place
from gramps.gen.lib import PlaceName
from gramps.gen.lib import PlaceRef
from gramps.gen.lib import PlaceType
#from gramps.gen.lib import PrimaryObject
from gramps.gen.lib import RepoRef
from gramps.gen.lib import Repository
from gramps.gen.lib import RepositoryType
#from gramps.gen.lib import Researcher
#from gramps.gen.lib import SecondaryObject
from gramps.gen.lib import Source
from gramps.gen.lib import SourceMediaType
from gramps.gen.lib import Span
from gramps.gen.lib import SrcAttribute
from gramps.gen.lib import SrcAttributeType
from gramps.gen.lib import StyledText
from gramps.gen.lib import StyledTextTag
from gramps.gen.lib import StyledTextTagType
from gramps.gen.lib import Surname
from gramps.gen.lib import Tag
from gramps.gen.lib import Url
from gramps.gen.lib import UrlType

try:
    from gramps.gui.editors import EditCitation
    from gramps.gui.editors import EditEvent
    from gramps.gui.editors import EditFamily
    from gramps.gui.editors import EditMedia
    from gramps.gui.editors import EditNote
    from gramps.gui.editors import EditPerson
    from gramps.gui.editors import EditPlace
    from gramps.gui.editors import EditRepository
    from gramps.gui.editors import EditSource
except:
    pass # command line mode, no GUI

from gramps.gen.config import config as configman
from gramps.gen.db import DbTxn
from gramps.gen.lib.date import Today
from gramps.gen.user import User

from gramps.gui.dialog import OkDialog
from gramps.gui.selectors.selectperson import SelectPerson

# -------------------------------------------------------------------------
#
# Local modules
#
# -------------------------------------------------------------------------
import supertool_engine as engine
import supertool_genfilter as genfilter


config = configman.register_manager("supertool")
config.register("defaults.include_location","")

CATEGORIES = [
    "People",
    "Families",
    "Events",
    "Places",
    "Citations",
    "Sources",
    "Repositories",
    "Media",
    "Notes",
]

namespace_to_category = {
    'Person': 'People',
    'Family': 'Families',
    'Event': 'Events',
    'Place': 'Places',
    'Citation': 'Citations',
    'Source': 'Sources',
    'Repository': 'Repositories',
    'Media': 'Media',
    'Note': 'Notes',
}

category_to_namespace = {cat:ns for ns,cat in namespace_to_category.items()}

def gentolist(orig):
    # type: (Callable) -> Callable

    @functools.wraps(orig)
    def f(*args):
        # type: (List[Any]) -> List[Any]
        return list(orig(*args))

    return f

def get_categories():
    # type: () -> List[str]
    return CATEGORIES


class Context:
    if TYPE_CHECKING:
        category_name: str
        get_all_objects_func: Callable
        getfunc: Callable
        commitfunc: Callable
        execute_func: Callable
        editfunc: Callable
        objcls: Type[PrimaryObject]
        objclass: Optional[str]
        #namespace: Optional[str]
        filterrule: Type[genfilter.GenericFilterRule]
        proxyclass: Type[engine.Proxy]

def get_context_from_namespace(db, namespace):
    # type: (DbGeneric ,str) -> Context
    return get_context(db, namespace_to_category[namespace])

def get_context(db, category_name):
    # type: (DbGeneric ,str) -> Context

    info = Context()

    info.category_name = category_name
    info.objclass = None
    info.execute_func = engine.execute_no_category
    if category_name == "People":
        info.get_all_objects_func = db.get_person_handles
        info.getfunc = db.get_person_from_handle
        info.commitfunc = db.commit_person
        info.execute_func = engine.execute_person
        info.editfunc = EditPerson
        info.objcls = Person
        info.objclass = "Person"
        info.filterrule = genfilter.GenericFilterRule_Person
        info.proxyclass = engine.PersonProxy
    if category_name == "Families":
        info.get_all_objects_func = db.get_family_handles
        info.getfunc = db.get_family_from_handle
        info.commitfunc = db.commit_family
        info.execute_func = engine.execute_family
        info.editfunc = EditFamily
        info.objcls = Family
        info.objclass = "Family"
        info.filterrule = genfilter.GenericFilterRule_Family
        info.proxyclass = engine.FamilyProxy
    if category_name == "Places":
        info.get_all_objects_func = db.get_place_handles
        info.getfunc = db.get_place_from_handle
        info.commitfunc = db.commit_place
        info.execute_func = engine.execute_place
        info.editfunc = EditPlace
        info.objcls = Place
        info.objclass = "Place"
        info.filterrule = genfilter.GenericFilterRule_Place
        info.proxyclass = engine.PlaceProxy
    if category_name == "Events":
        info.get_all_objects_func = db.get_event_handles
        info.getfunc = db.get_event_from_handle
        info.commitfunc = db.commit_event
        info.execute_func = engine.execute_event
        info.editfunc = EditEvent
        info.objcls = Event
        info.objclass = "Event"
        info.filterrule = genfilter.GenericFilterRule_Event
        info.proxyclass = engine.EventProxy
    if category_name == "Citations":
        info.get_all_objects_func = db.get_citation_handles
        info.getfunc = db.get_citation_from_handle
        info.commitfunc = db.commit_citation
        info.execute_func = engine.execute_citation
        info.editfunc = EditCitation
        info.objcls = Citation
        info.objclass = "Citation"
        info.filterrule = genfilter.GenericFilterRule_Citation
        info.proxyclass = engine.CitationProxy
    if category_name == "Sources":
        info.get_all_objects_func = db.get_source_handles
        info.getfunc = db.get_source_from_handle
        info.commitfunc = db.commit_source
        info.execute_func = engine.execute_source
        info.editfunc = EditSource
        info.objcls = Source
        info.objclass = "Source"
        info.filterrule = genfilter.GenericFilterRule_Source
        info.proxyclass = engine.SourceProxy
    if category_name == "Repositories":
        info.get_all_objects_func = db.get_repository_handles
        info.getfunc = db.get_repository_from_handle
        info.commitfunc = db.commit_repository
        info.execute_func = engine.execute_repository
        info.editfunc = EditRepository
        info.objcls = Repository
        info.objclass = "Repository"
        info.filterrule = genfilter.GenericFilterRule_Repository
        info.proxyclass = engine.RepositoryProxy
    if category_name == "Notes":
        info.get_all_objects_func = db.get_note_handles
        info.getfunc = db.get_note_from_handle
        info.commitfunc = db.commit_note
        info.execute_func = engine.execute_note
        info.editfunc = EditNote
        info.objcls = Note
        info.objclass = "Note"
        info.filterrule = genfilter.GenericFilterRule_Note
        info.proxyclass = engine.NoteProxy
    if category_name == "Media":
        info.get_all_objects_func = db.get_media_handles
        info.getfunc = db.get_media_from_handle
        info.commitfunc = db.commit_media
        info.execute_func = engine.execute_media
        info.editfunc = EditMedia
        info.objcls = Media
        info.objclass = "Media"
        info.filterrule = genfilter.GenericFilterRule_Media
        info.proxyclass = engine.MediaProxy
    return info

def find_fullname(fname, scriptfile_location, default_location):
    # type: (str, Optional[str], str) -> str
    mydir = os.path.split(__file__)[0]
    fullnames = []
    locations = []
    if scriptfile_location:
        locations.append(scriptfile_location)
    locations.append(default_location)
    locations.append(mydir)
    for dirname in locations:
        fullname = os.path.join(dirname, fname)
        fullname = os.path.abspath(fullname)
        if fullname not in fullnames:
            fullnames.append(fullname)
        if os.path.exists(fullname):
            return fullname
    fullname = os.path.abspath(fname)
    if fullname not in fullnames:
        fullnames.append(fullname)
    if os.path.exists(fullname):
        return fullname

    msg = "Include file '{}' not found; looked at\n".format(fname)
    msg += "\n".join(["- " + name for name in fullnames])
    raise engine.SupertoolException(msg)


def process_includes(code, scriptfile_location=None):
    # type: (str, str) -> Tuple[str, List[Tuple[str,int,int]]]

    def readfile(filename):
        # type: (str) -> List[str]
        try:
            return open(filename, 'rt', encoding='utf-8').readlines()
        except UnicodeError:
            # include files should be in utf-8 but if that fails then try the default encoding
            return open(filename, 'rt').readlines()

    config.load()
    default_location = config.get("defaults.include_location")
    if not default_location:
        TOOL_DIR = "supertool"
        from gramps.gen.const import USER_HOME
        default_location = os.path.join(USER_HOME, TOOL_DIR)
    newlines = [] # type: List[str]
    files = []  # type: List[Tuple[str,int,int]]
    for line in code.splitlines(keepends=True):
        parts = line.split(maxsplit=1)
        if len(parts) > 0 and parts[0] == "@include":
            if len(parts) == 1:
                raise engine.SupertoolException("Include file name missing")
            fname = parts[1].strip()
            fullname = find_fullname(fname, scriptfile_location, default_location)
            startline = len(newlines)+1
            for line2 in readfile(fullname):
                newlines.append(line2)
            endline = len(newlines)
            files.append((fullname,startline,endline))
        else:
            newlines.append(line)
    return "".join(newlines), files

def compile_statements(statements, source):
    # type: (str, str) -> Any
    if statements.strip() == "": return None
    return compile(statements, source, 'exec')

def compile_expression(expression, source):
    # type: (str, str) -> Any
    if expression.strip() == "": return None
    return compile(expression.strip().replace("\n"," "), source, 'eval')


def getargs_dialog(dbstate, uistate, from_genfilter, **kwargs):
    # type: (Dict[str, Union[str, Tuple[str,str,str]]]) -> Any
    from types import SimpleNamespace

    from gi.repository import Gtk, Gdk
    from gramps.gen.const import GRAMPS_LOCALE as glocale
    _ = glocale.translation.gettext

    from supertool_engine import SupertoolException

    def select_person(param):
        sel = SelectPerson(dbstate, uistate, [], "Select Person")
        result = sel.run()
        if result:
            p = getproxy(dbstate.db, result)
            param.value = p
            param.entry.set_text(p.gramps_id)
            param.lbl.set_label(p.name)

    def keypress(param, event):
        if event.keyval in (Gdk.KEY_Return, Gdk.KEY_KP_Enter):
            p = dbstate.db.get_person_from_gramps_id(param.entry.get_text())
            if p:
                value = getproxy(dbstate.db, p)
                param.lbl.set_label(value.name)
                param.value = value
            else:
                param.lbl.set_label("")
                param.value = None

    config = configman.register_manager("supertool")
    config.load()
    
    dialog = Gtk.Dialog(
        title=_("Parameters"), parent=None, flags=Gtk.DialogFlags.MODAL
    )

    dialog.add_button(_("Ok"), Gtk.ResponseType.OK)
    dialog.add_button(_("Cancel"), Gtk.ResponseType.CANCEL)
    dialog.set_default_response(Gtk.ResponseType.OK)

    grid = Gtk.Grid()
    grid.set_row_spacing(10)
    grid.set_column_spacing(10)

    initvalue = None

    class Param: pass
    params = []
    
    for row, (param_name, val) in enumerate(kwargs.items()):
        key = "default-params." + param_name
        config.register(key, "")
        value = config.get(key)
        
        param = Param()        
        if type(val) not in (str, tuple):
            raise SupertoolException(f"getargs: param must be a string or a tuple: {val}")
        if type(val) == str:
            title = val
            widget = Gtk.Entry()
            widget.set_text(value)
            paramtype = str
        if type(val) == tuple:
            title, paramtype, initvalue = val # type: ignore
            if type(title) != str:
                raise SupertoolException(f"getargs: invalid title - must be a string: {title}")
            param.initvalue = initvalue
            if paramtype not in (
                    bool, list, 'person', 'file',
                ):
                raise SupertoolException(f"getargs: invalid param type - use one of: bool, list, 'person': {paramtype}")
            if paramtype == bool:
                widget = Gtk.CheckButton()
                if value == "":
                    value = initvalue
                elif value == 'True':
                    value = True
                else:
                    value = False
                widget.set_active(value)
            if paramtype == list:
                try:
                    initvalue = list(initvalue)  # type: ignore # ensure this is a real list
                except:
                    raise SupertoolException(f"getargs: invalid value '{initvalue}' - must be a list")
                widget = Gtk.ComboBoxText()
                widget.set_entry_text_column(0)
                widget.append_text("")
                for index, v in enumerate(initvalue):
                    widget.append_text(str(v))
                    if str(v) == value:
                        print(widget)
                        widget.set_active(index+1)                
            if paramtype == 'person':
                widget = Gtk.HBox()
                widget.set_spacing(10)
                entry = Gtk.Entry() #self.get_widget(opttype)
                lbl = Gtk.Label()
                button = Gtk.Button("Select")
                widget.pack_start(entry, False, False, 0)
                widget.pack_start(button, False, False, 0)
                widget.pack_end(lbl, False, False, 0)

                param.entry = entry
                param.lbl = lbl
                param.value = None
                if not value and initvalue:
                    value = initvalue
                if value:
                    p = dbstate.db.get_person_from_gramps_id(value)
                    if p:
                        entry.set_text(value)
                        param.value = getproxy(dbstate.db, p)
                        lbl.set_label(param.value.name)

                entry.connect("key-press-event",lambda _widget, event,
                              param=param: keypress(param, event))
                button.connect("clicked", lambda _, param=param: select_person(param))
            if paramtype == 'file':
                print('file')
                widget = Gtk.HBox()
                widget.set_spacing(10)
                entry = Gtk.Entry() #self.get_widget(opttype)
                entry.set_text(value)
                lbl = Gtk.Label()
                button = Gtk.Button("Select")
                widget.pack_start(entry, False, False, 0)
                widget.pack_start(button, False, False, 0)
                widget.pack_end(lbl, False, False, 0)

                param.entry = entry
                param.lbl = lbl
                param.value = None

                extension = initvalue

                button.connect("clicked", lambda _, param=param: select_file(param, extension))

        param.name = param_name
        param.paramtype = paramtype
        param.widget = widget
        params.append(param)
                
        lbl_title = Gtk.Label(title)
        lbl_title.set_halign(Gtk.Align.START)
        grid.attach(lbl_title, 0, row, 1, 1)
        grid.attach(widget, 1, row, 1, 1)

    dialog.vbox.pack_start(grid, False, False, 5)
    if uistate: dialog.set_transient_for(uistate.window)
    dialog.set_urgency_hint(True)
    dialog.show_all()
    try:
        result = dialog.run()
        if result != Gtk.ResponseType.OK:
            if from_genfilter:
                OkDialog("Warning", "Canceling the dialog will cause a Gramps exception. This is expected. Please ignore the next message.")
            raise engine.SupertoolException("canceled")
    
        values = {}
        for param in params:
            if param.paramtype == str:
                value = param.widget.get_text()
            if param.paramtype == bool:
                value = param.widget.get_active()
            if param.paramtype == list:
                index = param.widget.get_active()
                if index <= 0:  # 0 or -1
                    value = ""    # none selected
                else:
                    value = param.initvalue[index-1] # type: ignore
                print(index, value)
            configvalue = value
            if param.paramtype == 'person':
                value = param.value
                if value is None:
                    gid = param.entry.get_text()
                    if gid:
                        p = dbstate.db.get_person_from_gramps_id(gid)
                        if p:
                            value = getproxy(dbstate.db, p)
                configvalue = value.gramps_id if value else ""
            if param.paramtype == 'file':
                value = param.value
                if value is None:
                    value = param.entry.get_text()
                configvalue = value if value else ""
            values[param.name] = value
            key = "default-params." + param.name
            config.set(key, str(configvalue))
        config.save()
        return SimpleNamespace(**values)
    finally:
        dialog.destroy()


class FileChooserDialog(Gtk.FileChooserDialog):
    def __init__(self, extension):
        # type: (DisplayState) -> None
        from gramps.gen.const import GRAMPS_LOCALE as glocale
        _ = glocale.translation.gettext
        Gtk.FileChooserDialog.__init__(
            self,
            title="Select a file",
#            transient_for=uistate.window,
            action=Gtk.FileChooserAction.OPEN,
        )

        self.add_buttons(
            _("_Cancel"), Gtk.ResponseType.CANCEL, _("Select"), Gtk.ResponseType.OK
        )

        if extension:
            if not extension.startswith("."):
                extension = "." + extension
            filefilter = Gtk.FileFilter()
            filefilter.set_name(f"{extension} files")
            filefilter.add_pattern("*"+extension)
            self.add_filter(filefilter)

        filter_all = Gtk.FileFilter()
        filter_all.set_name("All files")
        filter_all.add_pattern("*.*")
        self.add_filter(filter_all)

def select_file(param, extension):
    # type: (Gtk.Widget) -> None
    choose_file_dialog = FileChooserDialog(extension) #self.uistate)

    while True:
        response = choose_file_dialog.run()
        if response == Gtk.ResponseType.CANCEL:
            break
        elif response == Gtk.ResponseType.DELETE_EVENT:
            break
        elif response == Gtk.ResponseType.OK:
            filename = choose_file_dialog.get_filename()
            param.entry.set_text(filename)
            param.value = filename
            break

    choose_file_dialog.destroy()


def uniq(items):
    # type: (List[Any]) -> List[Any]
    return list(set(items))


def makedate(year, month=0, day=0, about=False):
    # type: (int, int, int, bool) -> engine.DateProxy
    d = GrampsDate()
    d.set_yr_mon_day(year, month, day)
    if about:
        d.set_modifier(GrampsDate.MOD_ABOUT)
    return engine.DateProxy(d)


def today():
    # type: () -> engine.DateProxy
    return engine.DateProxy(Today())


def size(x):
    # type: (Any) -> int
    return len(list(x))


@gentolist
def old_flatten(lists):
    # type: (List[Any]) -> Iterator[Any]
    for sublist in lists:
        for item in sublist:
            yield item

from types import GeneratorType

@gentolist
def flatten(a):
    # type: (List[Any]) -> Iterator[Any]
    if type(a) in [list, GeneratorType]:
        for x in a:
            yield from flatten(x)
    else:
        yield a

# def commit(db, trans, proxyobj): # not used, possible future use
#     # type: (DbGeneric, DbTxn, engine.Proxy) -> None
#     print("commit", trans, proxyobj.name)
#     if trans is not None:
#         proxyobj._commit(db, trans)



class DummyTxn:
    "Implements nested transactions"

    def __init__(self, trans):
        # type: (DbTxn) -> None
        if trans is None:
            raise engine.SupertoolException("Need a transaction (check 'Commit changes')")
        self.trans = trans

        class _Txn:
            def __init__(self, msg, db):
                # type: (str, DbGeneric) -> None
                pass

            def __enter__(self):
                # type: () -> DbTxn
                return trans

            def __exit__(self, *args):
                # type: (List[Any]) -> Any
                return False

        self.txn = _Txn

class Lazyenv(dict):
    def __init__(self, **kwargs):
        # type: (Any) -> None
        dict.__init__(self, **kwargs)
        self.obj = None
        self.attrs = set() # type: Set[str]
    def __getitem__(self, attrname):
        # type: (str) -> Any
        if attrname in self:
            return dict.__getitem__(self, attrname)
        if attrname in self.attrs:
            value = getattr(self.obj, attrname) # nullproxy)
            return value
        raise KeyError
        #return dict.__getitem__(self, attrname)
        #return self.env[attrname]

        
def get_globals():
    # type: () -> Lazyenv
    return Lazyenv(
        uniq=uniq,
        makedate=makedate,
        today=today,
        size=size,
        len=size,
        flatten=flatten,
        os=os,
        sys=sys,
        re=re,
        collections=collections,
        defaultdict=collections.defaultdict,
        functools=functools,
        pprint=pprint,

        Address=Address,
        Attribute=Attribute,
        AttributeType=AttributeType,
        ChildRef=ChildRef,
        ChildRefType=ChildRefType,
        Citation=Citation,
        Date=GrampsDate,
        DateError=DateError,
        Event=Event,
        EventRef=EventRef,
        EventRoleType=EventRoleType,
        EventType=EventType,
        Family=Family,
        FamilyRelType=FamilyRelType,
#        GenderStats=GenderStats,
        GrampsType=GrampsType,
        LdsOrd=LdsOrd,
        Location=Location,
        MarkerType=MarkerType,
        Media=Media,
        MediaRef=MediaRef,
        Name=Name,
        NameOriginType=NameOriginType,
        NameType=NameType,
        Note=Note,
        NoteType=NoteType,
        Person=Person,
        PersonRef=PersonRef,
        Place=Place,
        PlaceName=PlaceName,
        PlaceRef=PlaceRef,
        PlaceType=PlaceType,
#        PrimaryObject=PrimaryObject,
        RepoRef=RepoRef,
        Repository=Repository,
        RepositoryType=RepositoryType,
#        Researcher=Researcher,
#        SecondaryObject=SecondaryObject,
        Source=Source,
        SourceMediaType=SourceMediaType,
        Span=Span,
        SrcAttribute=SrcAttribute,
        SrcAttributeType=SrcAttributeType,
        StyledText=StyledText,
        StyledTextTag=StyledTextTag,
        StyledTextTagType=StyledTextTagType,
        Surname=Surname,
        Tag=Tag,
        Url=Url,
        UrlType=UrlType,
        
        DummyTxn=DummyTxn,
        #commit=functools.partial(commit, dbstate.db, envvars["trans"]),
        null=engine.nullproxy,
    )

class Response:
    def __init__(self, rows, query, result):
        # type: (List[List[Any]], Any, Any) -> None
        # xtype: (List[List[Any]], Query, Result) -> None
        self.rows = rows
        self.query = query
        self.result = result


import SuperTool

def supertool_execute( *, 
    category, 
    dbstate=None, 
    db=None, 
    trans=None,
    handles=None, 
    initial_statements=None, 
    statements=None, 
    filter=None, 
    expressions=None, 
    summary_only=False, 
    unwind_lists=False, 
    commit_changes=False, 
    args=""):
        # type: (str,Any,Any,Any,List[str],str,str,str,str,bool,bool,bool,str) -> Any
        query = SuperTool.Query()
        if initial_statements:
            query.initial_statements = textwrap.dedent(initial_statements)
        if statements:
            query.statements = textwrap.dedent(statements)
        if filter:
            query.filter = filter
        if expressions:
            query.expressions = expressions
        query.category = category
        query.scope = "all"
        query.unwind_lists = unwind_lists
        query.commit_changes = commit_changes
        query.summary_only = summary_only
        return supertool_execute_query(query=query, dbstate=dbstate, db=db, trans=trans, handles=handles, args=args) 

def supertool_execute_script(*, script, dbstate=None, db=None, trans=None, handles=None, args=""): 
        # type: (str,Any,Any,Any,List[str],str) -> Any
        scriptfile = SuperTool.ScriptFile()
        query = scriptfile.load(script)
        return supertool_execute_query(query=query, dbstate=dbstate, db=db, trans=trans, handles=handles, args=args) 

def supertool_execute_query(*, query, dbstate=None, db=None, trans=None, handles=None, args=""): 
        # type: (SuperTool.Query,Any,Any,Any,List[str],str) -> Any
        env = {
            "args": args, 
        }

        if dbstate is None and db is None:
            raise RuntimeError("supertool_execute: dbstate and db cannot both be omitted")
        if dbstate is not None and db is not None:
            raise RuntimeError("supertool_execute: dbstate and db cannot both be supplied")
        if dbstate is None:
            dbstate =  SimpleNamespace(db=db)
            
        if query.category not in CATEGORIES:
            raise RuntimeError("Invalid category: " + query.category)
        context = get_context(dbstate.db, query.category)
        
        if handles is None:
            if context.objclass:
                selected_handles = context.get_all_objects_func()
            else:
                selected_handles = []
        else:
            selected_handles = handles

        user = User()
        user.uistate = None
        
        env = Lazyenv(**env)
        gramps_engine = SuperTool.GrampsEngine(
            dbstate,
            user,
            context,
            selected_handles,
            query,
            env=env,
            raw_values=True,
        )
        result = SuperTool.Result()
        rows = []
        if trans is not None:
            for values in gramps_engine.get_values(trans, result):
                rows.append(values[1:-2])
        else:
            with DbTxn("Generating values", dbstate.db) as trans:
                for values in gramps_engine.get_values(trans, result):
                    rows.append(values[1:-2])
        return Response(rows=rows, query=query, result=result)
    


def getproxy(db, obj):
    # type: (DbGeneric, PrimaryObject) -> engine.Proxy
    if isinstance(obj, Person): return engine.PersonProxy(db, obj.handle)
    if isinstance(obj, Family): return engine.FamilyProxy(db, obj.handle)
    if isinstance(obj, Event): return engine.EventProxy(db, obj.handle)
    if isinstance(obj, Place): return engine.PlaceProxy(db, obj.handle)
    if isinstance(obj, Citation): return engine.CitationProxy(db, obj.handle)
    if isinstance(obj, Source): return engine.SourceProxy(db, obj.handle)
    if isinstance(obj, Repository): return engine.RepositoryProxy(db, obj.handle)
    if isinstance(obj, Media): return engine.MediaProxy(db, obj.handle)
    if isinstance(obj, Note): return engine.NoteProxy(db, obj.handle)
    raise engine.SupertoolException("Unknown object type: " + str(type(obj)))

    