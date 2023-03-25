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

from pprint import pprint



# -------------------------------------------------------------------------
#
# Gramps modules
#
# -------------------------------------------------------------------------
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

def gentolist(orig):
    @functools.wraps(orig)
    def f(*args):
        return list(orig(*args))

    return f

def get_categories():
    return CATEGORIES


def get_category_info(db, category_name):
    # type: () -> None
    class Category:
        pass

    info = Category()

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
    # type (str) -> Tuple[str, List[Tuple(str,int,int)]]
    config.load()
    default_location = config.get("defaults.include_location")
    if not default_location:
        TOOL_DIR = "supertool"
        from gramps.gen.const import USER_HOME
        default_location = os.path.join(USER_HOME, TOOL_DIR)
    newlines = []
    files = []
    for line in code.splitlines(keepends=True):
        parts = line.split(maxsplit=1)
        if len(parts) > 0 and parts[0] == "@include":
            if len(parts) == 1:
                raise engine.SupertoolException("Include file name missing")
            fname = parts[1].strip()
            fullname = find_fullname(fname, scriptfile_location, default_location)
            startline = len(newlines)+1
            for line2 in open(fullname):
                newlines.append(line2)
            endline = len(newlines)
            files.append((fullname,startline,endline))
        else:
            newlines.append(line)
    return "".join(newlines), files

def compile_statements(statements, source):
    if statements.strip() == "": return None
    return compile(statements, source, 'exec')

def compile_expression(expression, source):
    if expression.strip() == "": return None
    return compile(expression.strip().replace("\n"," "), source, 'eval')



def getargs_dialog(**kwargs):
    # type: () -> bool
    """
    This code should really be in SuperTool.py because it contains user interface code...
    """
    
    from types import SimpleNamespace


    from gi.repository import Gtk
    from gramps.gen.const import GRAMPS_LOCALE as glocale, CUSTOM_FILTERS
    _ = glocale.translation.gettext

    config = configman.register_manager("supertool")
    config.load()
    
    dialog = Gtk.Dialog(
        title=_("Parameters"), parent=None, flags=Gtk.DialogFlags.MODAL
    )

    dialog.add_button(_("Ok"), Gtk.ResponseType.OK)
    dialog.add_button(_("Cancel"), Gtk.ResponseType.CANCEL)
    dialog.set_default_response(Gtk.ResponseType.OK)

    grid = Gtk.Grid()
    widgets = []
    for row, param in enumerate(kwargs.items()):
        param_name, title = param
        key = "default-params." + param_name
        config.register(key, "")
        value = config.get(key)

        lbl_title = Gtk.Label(title)
        lbl_title.set_halign(Gtk.Align.START)
        widget = Gtk.Entry() #self.get_widget(opttype)
        widget.set_text(value)
        grid.attach(lbl_title, 0, row, 1, 1)
        grid.attach(widget, 1, row, 1, 1)
        widgets.append((param_name, widget))

    dialog.vbox.pack_start(grid, False, False, 5)
    dialog.show_all()
    result = dialog.run()
    if result != Gtk.ResponseType.OK:
        dialog.destroy()
        raise RuntimeError("canceled")
        return False

    values = {}
    for param_name, widget in widgets:
        value = widget.get_text()
        values[param_name] = value
        key = "default-params." + param_name
        config.set(key, value)
    config.save()
    dialog.destroy()
    return SimpleNamespace(**values)


def uniq(items):
    return list(set(items))


def makedate(year, month=0, day=0, about=False):
    d = GrampsDate()
    d.set_yr_mon_day(year, month, day)
    if about:
        d.set_modifier(GrampsDate.MOD_ABOUT)
    return engine.DateProxy(d)


def today():
    return engine.DateProxy(Today())


def size(x):
    return len(list(x))


@gentolist
def old_flatten(lists):
    for sublist in lists:
        for item in sublist:
            yield item

from types import GeneratorType

@gentolist
def flatten(a):
    if type(a) in [list, GeneratorType]:
        for x in a:
            yield from flatten(x)
    else:
        yield a

def commit(db, trans, proxyobj): # not used, possible future use
    print("commit", trans, proxyobj.name)
    if trans is not None:
        proxyobj._commit(db, trans)




class DummyTxn:
    "Implements nested transactions"

    def __init__(self, trans):
        if trans is None:
            raise SupertoolException("Need a transaction (check 'Commit changes')")
        self.trans = trans

        class _Txn:
            def __init__(self, msg, db):
                pass

            def __enter__(self):
                return trans

            def __exit__(self, *args):
                return False

        self.txn = _Txn

class Lazyenv(dict):
    def __init__(self, **kwargs):
        dict.__init__(self, **kwargs)
        self.obj = None
        self.attrs = set()
    def __getitem__(self, attrname):
        if attrname in self:
            return dict.__getitem__(self, attrname)
        if attrname in self.attrs:
            value = getattr(self.obj, attrname) # nullproxy)
            return value
        raise KeyError
        #return dict.__getitem__(self, attrname)
        #return self.env[attrname]

        
def get_globals():
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
        getargs=getargs_dialog,
        null=engine.nullproxy,
    )

class Response:
    def __init__(self, rows):
        self.rows = rows


def supertool_execute( *, 
    category, 
    dbstate, 
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
        dirname = os.path.dirname(__file__)
        saved_path = sys.path[:]
        try:
            sys.path.append(dirname)
            import SuperTool
        finally:
            sys.path = saved_path

        if category not in CATEGORIES:
            raise RuntimeError("Invalid category: " + category)
        category_info = get_category_info(dbstate.db, category)
        
        if handles is None:
            if category_info.objclass:
                selected_handles = category_info.get_all_objects_func()
            else:
                selected_handles = []
        else:
            selected_handles = handles

        user = User()
        user.uistate = None
        
        query = SuperTool.Query()
        if initial_statements:
            query.initial_statements = initial_statements
        if statements:
            query.statements = statements
        if filter:
            query.filter = filter
        if expressions:
            query.expressions = expressions
        query.category = category
        query.scope = "all"
        query.unwind_lists = unwind_lists
        query.commit_changes = commit_changes
        query.summary_only = summary_only
        env = {
            "args": args, 
            #"category": category, 
            #"namespace": category_info.objclass
        }
        env = Lazyenv(**env)
        gramps_engine = SuperTool.GrampsEngine(
            dbstate,
            user,
            category_info,
            selected_handles,
            query,
            env=env,
            raw_values=True,
        )
        result = SuperTool.Result()
        rows = []
        if trans is not None:
            for values in gramps_engine.get_values(trans, result):
                rows.append(values[1:-1])
        else:
            with DbTxn("Generating values", dbstate.db) as trans:
                for values in gramps_engine.get_values(trans, result):
                    rows.append(values[1:-1])
        return Response(rows=rows)
    
