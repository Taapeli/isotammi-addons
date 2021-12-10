#
# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2020 Kari Kujansuu
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

# -------------------------------------------------------------------------
#
# Gramps modules
#
# -------------------------------------------------------------------------
from gramps.gen.const import GRAMPS_LOCALE as glocale, CUSTOM_FILTERS
from gramps.gen.display.name import displayer as name_displayer
from gramps.gen.display.place import displayer as place_displayer
from gramps.gen.utils.string import gender as gender_map

from gramps.gen.lib import Citation
from gramps.gen.lib import Date as GrampsDate
from gramps.gen.lib import Event
from gramps.gen.lib import EventType
from gramps.gen.lib import Family
from gramps.gen.lib import Media
from gramps.gen.lib import NameType
from gramps.gen.lib import Note
from gramps.gen.lib import Person
from gramps.gen.lib import Place
from gramps.gen.lib import PlaceType
from gramps.gen.lib import Repository
from gramps.gen.lib import Source

from gramps.gen.lib.date import Today
from gramps.gen.filters import FilterList

_ = glocale.translation.gettext

import supertool_utils

gender_map = {
    Person.MALE: "M",
    Person.FEMALE: "F",
}


class SupertoolException(RuntimeError):
    pass


def listproperty(orig):
    @functools.wraps(orig)
    def f(*args):
        return list(orig(*args))

    return property(f)


def gentolist(orig):
    @functools.wraps(orig)
    def f(*args):
        return list(orig(*args))

    return f


@functools.total_ordering
class Proxy:
    def __init__(self, db, handle):
        self.db = db
        self.handle = handle

    def __eq__(self, other):
        return self.handle == other.handle

    def __repr__(self):
        classname = self.__class__.__name__
        objname = classname.replace("Proxy", "")
        return "%s[%s]" % (objname, self.gramps_id)

    def __lt__(self, other):
        return False


    @listproperty
    def tags(self):
        for tag_handle in self.obj.get_tag_list():
            tag = self.db.get_tag_from_handle(tag_handle)
            yield tag.name

    @gentolist
    def referrers(self, reftype):
        for _, handle in self.db.find_backlink_handles(
            self.handle, include_classes=[reftype]
        ):
            if reftype == "Person":
                yield PersonProxy(self.db, handle)
            if reftype == "Family":
                yield FamilyProxy(self.db, handle)
            if reftype == "Event":
                yield EventProxy(self.db, handle)
            if reftype == "Place":
                yield PlaceProxy(self.db, handle)
            if reftype == "Source":
                yield SourceProxy(self.db, handle)
            if reftype == "Citation":
                yield CitationProxy(self.db, handle)
            if reftype == "Repository":
                yield RepositoryProxy(self.db, handle)
            if reftype == "Media":
                yield MediaProxy(self.db, handle)
            if reftype == "Note":
                yield NoteProxy(self.db, handle)

class AttributeProxy:
    @listproperty
    def attributes(self):
        for attr in self.obj.get_attribute_list():
            yield attr.type.xml_str(), attr.value


@functools.total_ordering
class NullProxy:
    def __getattr__(self, attrname):
        return NullProxy()

    def __getitem__(self, i):
        return NullProxy()

    def __add__(self, other):
        return NullProxy()

    def __sub__(self, other):
        return 0

    def __eq__(self, other):
        return False

    def __lt__(self, other):
        return False

    def __gt__(self, other):
        return False

    def __le__(self, other):
        return False

    def __ge__(self, other):
        return False

    def __ne__(self, other):
        return False
    
    def __repr__(self):
        return ""

    def __bool__(self):
        return False

    def __call__(self, *args, **kwargs):
        return NullProxy()

    def __iter__(self):
        return self

    def __next__(self):
        raise StopIteration()


nullproxy = NullProxy()


@functools.total_ordering
class DateProxy:
    def __init__(self, dateobj):
        self.dateobj = dateobj
        self.obj = dateobj

    def __eq__(self, other):
        if isinstance(other, DateProxy):
            return self.dateobj == other.dateobj
        else:
            return False

    def __lt__(self, other):
        if isinstance(other, DateProxy):
            return self.dateobj < other.dateobj
        elif isinstance(other, int):
            return self.dateobj < makedate(other).obj
        else:
            return False

    def __add__(self, other):
        return DateProxy(self.dateobj + other)

    def __sub__(self, other):
        if isinstance(other, DateProxy):
            return int(self.dateobj - other.dateobj)
        if isinstance(other, int):
            return DateProxy(self.dateobj - other)
        return NullProxy()

    def __repr__(self):
        return str(self.dateobj)


class CommonProxy(Proxy):
    def __init__(self, db, handle):
        Proxy.__init__(self, db, handle)

    @listproperty
    def citations(self):
        for handle in self.obj.get_citation_list():
            yield CitationProxy(self.db, handle)

    @listproperty
    def notes(self):
        for handle in self.obj.get_note_list():
            yield NoteProxy(self.db, handle)


class NoteProxy(Proxy):
    namespace = "Note"

    def __init__(self, db, handle, note=None):
        Proxy.__init__(self, db, handle)
        if note:
            self.note = note
        else:
            self.note = self.db.get_note_from_handle(handle)
        self.obj = self.note
        self.gramps_id = self.obj.gramps_id
        self.text = self.obj.get()
        self.type = self.obj.get_type().xml_str()

    def _commit(self, db, trans):
        db.commit_note(self.obj, trans)
        


class CitationProxy(Proxy, AttributeProxy):
    namespace = "Citation"

    def __init__(self, db, handle, citation=None):
        Proxy.__init__(self, db, handle)
        if citation:
            self.citation = citation
        else:
            self.citation = self.db.get_citation_from_handle(handle)
        self.obj = self.citation
        self.gramps_id = self.obj.gramps_id
        self.confidence = self.obj.confidence
        self.page = self.obj.page
        # self.source = SourceProxy(self.db, self.obj.source_handle)

    def _commit(self, db, trans):
        db.commit_citation(self.obj, trans)
        

    @property
    def source(self):
        handle = self.obj.get_reference_handle()
        if not handle:
            return NullProxy()
        return SourceProxy(self.db, handle)

    @listproperty
    def notes(self):
        for handle in self.obj.get_note_list():
            yield NoteProxy(self.db, handle)

    @property
    def note(self):
        for noteobj in self.notes:
            text = noteobj.text
            return text
        return ""

    @listproperty
    def citators(self):
        for _, handle in self.db.find_backlink_handles(
            self.handle, include_classes=["Event"]
        ):
            yield EventProxy(self.db, handle)
        for _, handle in self.db.find_backlink_handles(
            self.handle, include_classes=["Person"]
        ):
            yield PersonProxy(self.db, handle)


class SourceProxy(Proxy, AttributeProxy):
    namespace = "Source"

    def __init__(self, db, handle, source=None):
        Proxy.__init__(self, db, handle)
        if source:
            self.source = source
        else:
            self.source = self.db.get_source_from_handle(handle)
        self.obj = self.source
        self.gramps_id = self.obj.gramps_id
        self.title = self.obj.title
        self.author = self.obj.author
        self.abbrev = self.obj.abbrev
        self.pubinfo = self.obj.pubinfo

    def _commit(self, db, trans):
        db.commit_source(self.obj, trans)
        
    @listproperty
    def repositories(self):
        for reporef in self.source.get_reporef_list():
            yield RepositoryProxy(self.db, reporef.ref)

    @listproperty
    def citations(self):
        for _, handle in self.db.find_backlink_handles(
            self.handle, include_classes=["Citation"]
        ):
            yield CitationProxy(self.db, handle)

    @listproperty
    def notes(self):
        for handle in self.obj.get_note_list():
            yield NoteProxy(self.db, handle)


class RepositoryProxy(Proxy):
    namespace = "Repository"

    def __init__(self, db, handle, repository=None):
        Proxy.__init__(self, db, handle)
        if repository:
            self.repository = repository
        else:
            self.repository = self.db.get_repository_from_handle(handle)
        self.obj = self.repository
        self.gramps_id = self.obj.gramps_id
        self.name = self.obj.name
        self.type = self.obj.type.xml_str()

    def _commit(self, db, trans):
        db.commit_repository(self.obj, trans)
        
    @listproperty
    def sources(self):
        for _, handle in self.db.find_backlink_handles(
            self.handle, include_classes=["Source"]
        ):
            yield SourceProxy(self.db, handle)

    @listproperty
    def notes(self):
        for handle in self.obj.get_note_list():
            yield NoteProxy(self.db, handle)


class PlaceProxy(CommonProxy):
    namespace = "Place"

    def __init__(self, db, place_handle, place=None):
        CommonProxy.__init__(self, db, place_handle)
        if place:
            self.place = place
        else:
            self.place = self.db.get_place_from_handle(place_handle)
        self.obj = self.place
        self.gramps_id = self.obj.gramps_id
        self.code = self.obj.code
        self.lat = self.obj.lat
        self.long = self.obj.long

    def _commit(self, db, trans):
        db.commit_place(self.obj, trans)
        
    @property
    def name(self):
        placename = self.place.get_name()
        if placename is None:
            return NullProxy()
        return placename.get_value()

    @property
    def longname(self):
        return place_displayer.display(self.db, self.place)

    @property
    def type(self):
        placetype = self.place.get_type()
        # return str(placetype)
        return placetype.xml_str()

    @property
    def title(self):
        return self.place.get_title()

    @listproperty
    def enclosed_by(self):
        for placeref in self.place.get_placeref_list():
            yield PlaceProxy(self.db, placeref.ref)

    @listproperty
    def encloses(self):
        for _, handle in self.db.find_backlink_handles(
            self.handle, include_classes=["Place"]
        ):
            yield PlaceProxy(self.db, handle)

    @property
    def events(self):
        return self.referrers("Event")

class EventProxy(CommonProxy, AttributeProxy):
    namespace = "Event"

    def __init__(self, db, event_handle, event=None, role=None):
        CommonProxy.__init__(self, db, event_handle)
        if event:
            self.event = event
        else:
            self.event = self.db.get_event_from_handle(event_handle)
        self.obj = self.event
        self.gramps_id = self.event.gramps_id
        self.type = self.event.get_type().xml_str()
        self.date = DateProxy(self.event.get_date_object())
        self.description = self.event.description
        self.role = role

    def _commit(self, db, trans):
        db.commit_event(self.obj, trans)
        

    @property
    def place(self):
        handle = self.event.get_place_handle()
        if not handle:
            return NullProxy()
        return PlaceProxy(self.db, handle)

    @property
    def placename(self):
        place_handle = self.event.get_place_handle()
        if not place_handle:
            return NullProxy()
        place = self.db.get_place_from_handle(place_handle)
        return place_displayer.display_event(self.db, self.event)

    @listproperty
    def refs(self):
        for class_name, referrer_handle in self.db.find_backlink_handles(self.handle):
            if class_name == "Person":
                person = self.db.get_person_from_handle(referrer_handle)
                eventref_list = person.event_ref_list
            if class_name == "Family":
                family = self.db.get_family_from_handle(referrer_handle)
                eventref_list = family.event_ref_list
            for eventref in eventref_list:
                if eventref.ref == self.handle:
                    yield eventref

    @listproperty
    def participants(self):
        for class_name, referrer_handle in self.db.find_backlink_handles(
            self.handle, ["Person", "Family"]
        ):
            # role = self.get_role_of_eventref(self.db, referrer_handle, self.handle)
            if class_name == "Family":
                family = self.db.get_family_from_handle(referrer_handle)
                if family.father_handle:
                    yield PersonProxy(self.db, family.father_handle)
                if family.mother_handle:
                    yield PersonProxy(self.db, family.mother_handle)
            if class_name == "Person":
                # print(role,type(role),self.list[2],role != self.list[2])
                yield PersonProxy(self.db, referrer_handle)

    def get_role_of_eventref(self, db, referrer_handle, event_handle):
        person = db.get_person_from_handle(referrer_handle)
        eventref_list = person.get_event_ref_list()
        for eventref in eventref_list:
            if eventref.ref == event_handle:
                return eventref.role
        return "referred"


class PersonProxy(CommonProxy, AttributeProxy):
    namespace = "Person"

    def __init__(self, db, person_handle, person=None):
        CommonProxy.__init__(self, db, person_handle)
        if person:
            self.person = person
        else:
            self.person = self.db.get_person_from_handle(person_handle)
        self.obj = self.person
        self.gramps_id = self.person.gramps_id

    def _commit(self, db, trans):
        db.commit_person(self.obj, trans)
        
    @property
    def name(self):
        return name_displayer.display(self.person)

    @property
    def names(self):
        return [
            n.get_name()
            for n in [self.person.get_primary_name()]
            + self.person.get_alternate_names()
        ]

    @property
    def nameobjs(self):
        return [self.person.get_primary_name()] + self.person.get_alternate_names()

    @property
    def gender(self):
        return gender_map.get(self.person.gender, "U")

    @property
    def birth(self):
        eventref = self.person.get_birth_ref()
        if not eventref:
            return NullProxy()
        return EventProxy(self.db, eventref.ref)

    @property
    def death(self):
        eventref = self.person.get_death_ref()
        if not eventref:
            return NullProxy()
        return EventProxy(self.db, eventref.ref)

    @listproperty
    def events(self):
        for eventref in self.person.get_event_ref_list():
            yield EventProxy(self.db, eventref.ref, role=eventref.role)

    @listproperty
    def families(self):
        for handle in self.person.get_family_handle_list():
            yield FamilyProxy(self.db, handle)

    @listproperty
    def children(self):
        for handle in self.person.get_family_handle_list():
            f = FamilyProxy(self.db, handle)
            for c in f.children:
                    yield c

    @listproperty
    def spouses(self):
        for handle in self.person.get_family_handle_list():
            f = FamilyProxy(self.db, handle)
            if f.father and f.father.handle != self.handle:
                yield f.father
            if f.mother and f.mother.handle != self.handle:
                yield f.mother

    @listproperty
    def parent_families(self):
        for handle in self.person.get_parent_family_handle_list():
            yield FamilyProxy(self.db, handle)

    @listproperty
    def parents(self):
        for handle in self.person.get_parent_family_handle_list():
            f = FamilyProxy(self.db, handle)
            father = f.father
            if father: yield father
            mother = f.mother
            if mother: yield mother

    @property
    def mother(self):
        for handle in self.person.get_parent_family_handle_list():
            f = FamilyProxy(self.db, handle)
            return f.mother
        return NullProxy()

    @property
    def father(self):
        for handle in self.person.get_parent_family_handle_list():
            f = FamilyProxy(self.db, handle)
            return f.father
        return NullProxy()

    @listproperty
    def citations(self):
        for handle in self.obj.get_citation_list():
            yield CitationProxy(self.db, handle)


class FamilyProxy(CommonProxy, AttributeProxy):
    namespace = "Family"

    def __init__(self, db, family_handle, family=None):
        CommonProxy.__init__(self, db, family_handle)
        if family:
            self.family = family
        else:
            self.family = self.db.get_family_from_handle(family_handle)
        self.obj = self.family
        self.gramps_id = self.family.gramps_id
        self.reltype = self.family.get_relationship().xml_str()

    def _commit(self, db, trans):
        db.commit_family(self.obj, trans)

    @listproperty
    def events(self):
        for eventref in self.family.get_event_ref_list():
            yield EventProxy(self.db, eventref.ref)

    @property
    def father(self):
        handle = self.family.get_father_handle()
        if handle is None:
            return NullProxy()
        return PersonProxy(self.db, handle)

    @property
    def mother(self):
        handle = self.family.get_mother_handle()
        if handle is None:
            return NullProxy()
        return PersonProxy(self.db, handle)

    @listproperty
    def children(self):
        for childref in self.family.get_child_ref_list():
            yield PersonProxy(self.db, childref.ref)


class MediaProxy(CommonProxy, AttributeProxy):
    namespace = "Media"

    def __init__(self, db, media_handle, media=None):
        CommonProxy.__init__(self, db, media_handle)
        if media:
            self.media = media
        else:
            self.media = self.db.get_media_from_handle(media_handle)
        self.obj = self.media
        self.gramps_id = self.media.gramps_id
        self.path = self.media.path
        self.mime = self.media.mime
        self.desc = self.media.desc
        self.checksum = self.media.checksum
        self.date = DateProxy(self.media.date)

    def _commit(self, db, trans):
        db.commit_media(self.obj, trans)

def uniq(items):
    return list(set(items))


def makedate(year, month=0, day=0, about=False):
    d = GrampsDate()
    d.set_yr_mon_day(year, month, day)
    if about:
        d.set_modifier(GrampsDate.MOD_ABOUT)
    return DateProxy(d)


def today():
    return DateProxy(Today())


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


class Filterfactory:
    filterdb = None

    def __init__(self, db):
        self.db = db

    def getfilter(self, namespace):
        def filterfunc(filtername):
            if not Filterfactory.filterdb:
                Filterfactory.filterdb = FilterList(CUSTOM_FILTERS)
                Filterfactory.filterdb.load()
            filter_dict = Filterfactory.filterdb.get_filters_dict(namespace)
            filt = filter_dict[filtername]
            return lambda obj: filt.match(obj.handle, self.db)

        return filterfunc


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

def execute(dbstate, obj, code, proxyclass, env=None, exectype=None):
    global_env = dict(
        uniq=uniq,
        makedate=makedate,
        today=today,
        size=size,
        len=size,
        flatten=flatten,
        os=os,
        sys=sys,
        re=re,
        dbstate=dbstate,
        db=dbstate.db,
        collections=collections,
        defaultdict=collections.defaultdict,
        functools=functools,
        Person=Person,
        Family=Family,
        Place=Place,
        Event=Event,
        Repository=Repository,
        Source=Source,
        Citation=Citation,
        Note=Note,
        Date=GrampsDate,
        NameType=NameType,
        PlaceType=PlaceType,
        EventType=EventType,
        Media=Media,
        DummyTxn=DummyTxn,
        #commit=functools.partial(commit, dbstate.db, envvars["trans"]),
        getargs=supertool_utils.getargs_dialog,
    )
    env.update(global_env)
    env["env"] = env
    env["code"] = code
    if obj:
        p = proxyclass(dbstate.db, obj.handle, obj)
        env["self"] = p
        for name in dir(proxyclass) + list(
            p.__dict__.keys()
        ):  # this contains the @property methods
            if name.startswith("_"):
                continue
            # print(">>",name)
            value = getattr(p, name)
            env[name] = value
    filterfactory = Filterfactory(dbstate.db)
    if proxyclass:
        env["filter"] = filterfactory.getfilter(proxyclass.namespace)
    if exectype == "exec":
        res = exec(code, env)
    else:
        res = eval(code, env)
    return res, env


def execute_no_category(dbstate, obj, code, envvars=None, exectype=None):
    return execute(dbstate, None, code, None, envvars, exectype)


def execute_family(dbstate, obj, code, envvars=None, exectype=None):
    return execute(dbstate, obj, code, FamilyProxy, envvars, exectype)


def execute_person(dbstate, obj, code, envvars=None, exectype=None):
    return execute(dbstate, obj, code, PersonProxy, envvars, exectype)


def execute_place(dbstate, obj, code, envvars=None, exectype=None):
    return execute(dbstate, obj, code, PlaceProxy, envvars, exectype)


def execute_event(dbstate, obj, code, envvars=None, exectype=None):
    return execute(dbstate, obj, code, EventProxy, envvars, exectype)


def execute_media(dbstate, obj, code, envvars=None, exectype=None):
    return execute(dbstate, obj, code, MediaProxy, envvars, exectype)


def execute_note(dbstate, obj, code, envvars=None, exectype=None):
    return execute(dbstate, obj, code, NoteProxy, envvars, exectype)


def execute_citation(dbstate, obj, code, envvars=None, exectype=None):
    return execute(dbstate, obj, code, CitationProxy, envvars, exectype)


def execute_source(dbstate, obj, code, envvars=None, exectype=None):
    return execute(dbstate, obj, code, SourceProxy, envvars, exectype)


def execute_repository(dbstate, obj, code, envvars=None, exectype=None):
    return execute(dbstate, obj, code, RepositoryProxy, envvars, exectype)

