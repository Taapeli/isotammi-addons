#
# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2021-2023 Kari Kujansuu
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
import functools

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
    from gramps.gen.db.txn import DbTxn
    from gramps.gen.dbstate import DbState
    from gramps.gen.lib import PrimaryObject
    from gramps.gen.lib import EventRef
except:
    TYPE_CHECKING = False

# -------------------------------------------------------------------------
#
# Gramps modules
#
# -------------------------------------------------------------------------
from gramps.gen.const import GRAMPS_LOCALE as glocale, CUSTOM_FILTERS
from gramps.gen.display.name import displayer as name_displayer
from gramps.gen.display.place import displayer as place_displayer
from gramps.gen.filters import FilterList
from gramps.gen.lib import Person
from gramps.gen.lib import Date
from gramps.gen.lib import Note

_ = glocale.translation.gettext

gender_map = {
    Person.MALE: "M",
    Person.FEMALE: "F",
}

from supertool_utils import makedate

class SupertoolException(RuntimeError):
    pass


def listproperty(orig):
    # type: (Any) -> Any
    @functools.wraps(orig)
    def f(*args):
        # type: (Any) -> Any
        return list(orig(*args))

    return property(f)


def gentolist(orig):
    # type: (Any) -> Any
    @functools.wraps(orig)
    def f(*args):
        # type: (Any) -> Any
        return list(orig(*args))

    return f


@functools.total_ordering
class Proxy:
    def __init__(self, db, handle, obj=None):
        # type: (DbGeneric, str, PrimaryObject) -> None
        self.db = db
        self.handle = handle

    def __eq__(self, other):
        # type: (Any, Any) -> bool
        return self.handle == other.handle

    def __repr__(self):
        # type: (Any) -> Any
        classname = self.__class__.__name__
        objname = classname.replace("Proxy", "")
        return "%s[%s]" % (objname, self.gramps_id)

    def __lt__(self, other):
        # type: (Any, object) -> bool
        return False


    @listproperty
    def tags(self):
        # type: (Any) -> Iterator[str]
        for tag_handle in self.obj.get_tag_list():
            tag = self.db.get_tag_from_handle(tag_handle)
            yield tag.name

    @gentolist
    def referrers(self, reftype):
        # type: (str) -> Iterator[Proxy]
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
        # type: (Any) -> Iterator
        for attr in self.obj.get_attribute_list():
            yield attr.type.xml_str(), attr.value


@functools.total_ordering
class NullProxy:
    def __getattr__(self, attrname):
        # type: (str) -> NullProxy
        return nullproxy

    def __getitem__(self, i):
        # type: (Any) -> NullProxy
        return nullproxy

    def __add__(self, other):
        # type: (object) -> NullProxy
        return nullproxy

    def __sub__(self, other):
        # type: (object) -> int
        return 0

    def __eq__(self, other):
        # type: (object) -> bool
        return False

    def __lt__(self, other):
        # type: (object) -> bool
        return False

    def __gt__(self, other):
        # type: (object) -> bool
        return False

    def __le__(self, other):
        # type: (object) -> bool
        return False

    def __ge__(self, other):
        # type: (object) -> bool
        return False

    def __ne__(self, other):
        # type: (object) -> bool
        return False

    def __repr__(self):
        # type: () -> str
        return ""

    def __bool__(self):
        # type: () -> bool
        return False

    def __call__(self, *args, **kwargs):
        # type: (Any, Any) -> NullProxy
        return nullproxy

    def __iter__(self):
        # type: (Any) -> Any
        return self

    def __next__(self):
        # type: (Any) -> Any
        raise StopIteration()


nullproxy = NullProxy()


@functools.total_ordering
class DateProxy:
    def __init__(self, dateobj):
        # type: (Date) -> None
        self.dateobj = dateobj
        self.obj = dateobj

    def __eq__(self, other):
        # type: (Any, Any) -> bool
        if isinstance(other, DateProxy):
            return self.dateobj == other.dateobj
        else:
            return False

    def __lt__(self, other):
        # type: (Any, Any) -> bool
        if isinstance(other, DateProxy):
            return self.dateobj < other.dateobj
        elif isinstance(other, int):
            return self.dateobj < makedate(other).obj
        else:
            return False

    def __add__(self, other):
        # type: (Any, Any) -> Any
        return DateProxy(self.dateobj + other)

    def __sub__(self, other):
        # type: (Any, DateProxy) -> Any
        if isinstance(other, DateProxy):
            return int(self.dateobj - other.dateobj)
        if isinstance(other, int):
            return DateProxy(self.dateobj - other)
        return nullproxy

    def __repr__(self):
        # type: () -> str
        return str(self.dateobj)


class CommonProxy(Proxy):
    def __init__(self, db, handle):
        # type: (DbGeneric, str) -> None
        Proxy.__init__(self, db, handle)

    @listproperty
    def citations(self):
        # type: (Any) -> Iterator
        for handle in self.obj.get_citation_list():
            yield CitationProxy(self.db, handle)

    @listproperty
    def notes(self):
        # type: (Any) -> Iterator
        for handle in self.obj.get_note_list():
            yield NoteProxy(self.db, handle)

class MediaListProxy:
    @listproperty
    def media_list(self):
        # type: (Any) -> Iterator
        for mediaref in self.obj.get_media_list():
            yield MediaProxy(self.db, mediaref.ref)

class NoteProxy(Proxy):
    namespace = "Note"
    _attrs = set() # type: Set[str]

    def __init__(self, db, handle, note=None):
        # type: (Any, DbGeneric, str, Note) -> None
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
        # type: (Any, DbGeneric, DbTxn) -> None
        db.commit_note(self.obj, trans)



class CitationProxy(Proxy, AttributeProxy, MediaListProxy):
    namespace = "Citation"
    _attrs = set() # type: Set[str]

    def __init__(self, db, handle, citation=None):
        # type: (Any, DbGeneric, str, PrimaryObject) -> None
        Proxy.__init__(self, db, handle)
        if citation:
            self.citation = citation
        else:
            self.citation = self.db.get_citation_from_handle(handle)
        self.obj = self.citation
        self.gramps_id = self.obj.gramps_id
        self.confidence = self.obj.confidence
        self.page = self.obj.page
        dateobj = self.citation.get_date_object()
        if dateobj.sortval:
            self.date = DateProxy(dateobj)
        else:
            self.date = nullproxy
        # self.source = SourceProxy(self.db, self.obj.source_handle)

    def _commit(self, db, trans):
        # type: (Any, Any, Any) -> Any
        db.commit_citation(self.obj, trans)


    @property
    def source(self):
        # type: () -> Union[SourceProxy, NullProxy]
        handle = self.obj.get_reference_handle()
        if not handle:
            return nullproxy
        return SourceProxy(self.db, handle)

    @listproperty
    def notes(self):
        # type: () -> Iterator[NoteProxy]
        for handle in self.obj.get_note_list():
            yield NoteProxy(self.db, handle)

    @property
    def note(self):
        # type: () -> str
        for noteobj in self.notes:
            text = noteobj.text
            return text
        return ""

    @listproperty
    def citators(self):
        # type: () -> Iterator[Union[PersonProxy, EventProxy]]
        for _, handle in self.db.find_backlink_handles(
            self.handle, include_classes=["Event"]
        ):
            yield EventProxy(self.db, handle)
        for _, handle in self.db.find_backlink_handles(
            self.handle, include_classes=["Person"]
        ):
            yield PersonProxy(self.db, handle)


class SourceProxy(Proxy, AttributeProxy, MediaListProxy):
    namespace = "Source"
    _attrs = set() # type: Set[str]

    def __init__(self, db, handle, source=None):
        # type: (DbGeneric, str, PrimaryObject) -> None
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
        # type: (DbGeneric, DbTxn) -> None
        db.commit_source(self.obj, trans)

    @listproperty
    def repositories(self):
        # type: () -> Iterator[RepositoryProxy]
        for reporef in self.source.get_reporef_list():
            yield RepositoryProxy(self.db, reporef.ref)

    @listproperty
    def citations(self):
        # type: () -> Iterator[CitationProxy]
        for _, handle in self.db.find_backlink_handles(
            self.handle, include_classes=["Citation"]
        ):
            yield CitationProxy(self.db, handle)

    @listproperty
    def notes(self):
        # type: () -> Iterator[NoteProxy]
        for handle in self.obj.get_note_list():
            yield NoteProxy(self.db, handle)


class RepositoryProxy(Proxy):
    namespace = "Repository"
    _attrs = set() # type: Set[str]

    def __init__(self, db, handle, repository=None):
        # type: (DbGeneric, str, PrimaryObject) -> None
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
        # type: (Any, Any, Any) -> Any
        db.commit_repository(self.obj, trans)

    @listproperty
    def sources(self):
        # type: () -> Iterator[SourceProxy]
        for _, handle in self.db.find_backlink_handles(
            self.handle, include_classes=["Source"]
        ):
            yield SourceProxy(self.db, handle)

    @listproperty
    def notes(self):
        # type: () -> Iterator[NoteProxy]
        for handle in self.obj.get_note_list():
            yield NoteProxy(self.db, handle)


class PlaceProxy(CommonProxy, MediaListProxy):
    namespace = "Place"
    _attrs = set() # type: Set[str]

    def __init__(self, db, place_handle, place=None):
        # type: (DbGeneric, str, PrimaryObject) -> None
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
        # type: (Any, Any, Any) -> Any
        db.commit_place(self.obj, trans)

    @property
    def name(self):
        # type: (Any) -> Any
        placename = self.place.get_name()
        if placename is None:
            return nullproxy
        return placename.get_value()

    @property
    def longname(self):
        # type: () -> str
        return place_displayer.display(self.db, self.place)

    @listproperty
    def altnames(self):
        # type: () -> Iterator[str]
        for pn in self.place.get_alternative_names():
            yield pn.get_value()

    @property
    def type(self):
        # type: () -> str
        placetype = self.place.get_type()
        # return str(placetype)
        return placetype.xml_str()

    @property
    def title(self):
        # type: () -> str
        return self.place.get_title()

    @listproperty
    def enclosed_by(self):
        # type: () -> Iterator[PlaceProxy]
        for placeref in self.place.get_placeref_list():
            yield PlaceProxy(self.db, placeref.ref)

    @listproperty
    def encloses(self):
        # type: () -> Iterator[PlaceProxy]
        for _, handle in self.db.find_backlink_handles(
            self.handle, include_classes=["Place"]
        ):
            yield PlaceProxy(self.db, handle)

    @property
    def events(self):
        # type: () -> Iterator[EventProxy]
        return self.referrers("Event")

class EventProxy(CommonProxy, AttributeProxy, MediaListProxy):
    namespace = "Event"
    _attrs = set() # type: Set[str]

    def __init__(self, db, event_handle, event=None, role=None):
        # type: (DbGeneric, str, PrimaryObject, str) -> None
        CommonProxy.__init__(self, db, event_handle)
        if event:
            self.event = event
        else:
            self.event = self.db.get_event_from_handle(event_handle)
        self.obj = self.event
        self.gramps_id = self.event.gramps_id
        self.type = self.event.get_type().xml_str()
        dateobj = self.event.get_date_object()
        if dateobj.sortval:
            self.date = DateProxy(dateobj) # type: Union[DateProxy, NullProxy]
        else:
            self.date = nullproxy
        self.description = self.event.description
        self.role = role

    def _commit(self, db, trans):
        # type: (Any, Any, Any) -> Any
        db.commit_event(self.obj, trans)


    @property
    def place(self):
        # type: () -> Union[PlaceProxy, NullProxy]
        handle = self.event.get_place_handle()
        if not handle:
            return nullproxy
        return PlaceProxy(self.db, handle)

    @property
    def placename(self):
        # type: () -> Union[str, NullProxy] # ???
        place_handle = self.event.get_place_handle()
        if not place_handle:
            return nullproxy
        place = self.db.get_place_from_handle(place_handle)
        return place_displayer.display_event(self.db, self.event)

    @listproperty
    def refs(self):
        # type: () -> Iterator[EventRef]
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
        # type: () -> Iterator[PersonProxy]
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
        # type: (Any, Any, Any, Any) -> Any
        person = db.get_person_from_handle(referrer_handle)
        eventref_list = person.get_event_ref_list()
        for eventref in eventref_list:
            if eventref.ref == event_handle:
                return eventref.role
        return "referred"


class PersonProxy(CommonProxy, AttributeProxy, MediaListProxy):
    namespace = "Person"
    _attrs = set() # type: Set[str]

    def __init__(self, db, person_handle, person=None):
        # type: (DbGeneric, str, PrimaryObject) -> None
        CommonProxy.__init__(self, db, person_handle)
        if person:
            self.person = person
        else:
            self.person = self.db.get_person_from_handle(person_handle)
        self.obj = self.person
        self.gramps_id = self.person.gramps_id

    def _commit(self, db, trans):
        # type: (Any, Any, Any) -> Any
        db.commit_person(self.obj, trans)

    @property
    def name(self):
        # type: () -> str
        return name_displayer.display(self.person)

    @property
    def names(self):
        # type: () -> List[str]
        return [
            n.get_name()
            for n in [self.person.get_primary_name()]
            + self.person.get_alternate_names()
        ]

    @property
    def nameobjs(self):
        # type: () -> List[Any]
        return [self.person.get_primary_name()] + self.person.get_alternate_names()

    @property
    def surname(self):
        # type: () -> str
        return self.person.get_primary_name().get_surname()

    @property
    def firstname(self):
        # type: () -> str
        return self.person.get_primary_name().get_first_name()

    @property
    def suffix(self):
        # type: () -> str
        return self.person.get_primary_name().get_suffix()

    @property
    def gender(self):
        # type: () -> str
        return gender_map.get(self.person.gender, "U")

    @property
    def birth(self):
        # type: () -> Union[EventProxy, NullProxy]
        eventref = self.person.get_birth_ref()
        if not eventref:
            return nullproxy
        return EventProxy(self.db, eventref.ref)

    @property
    def death(self):
        # type: () -> Union[EventProxy, NullProxy]
        eventref = self.person.get_death_ref()
        if not eventref:
            return nullproxy
        return EventProxy(self.db, eventref.ref)

    @listproperty
    def events(self):
        # type: () -> Iterator[EventProxy]
        for eventref in self.person.get_event_ref_list():
            yield EventProxy(self.db, eventref.ref, role=eventref.role)

    @listproperty
    def families(self):
        # type: () -> Iterator[FamilyProxy]
        for handle in self.person.get_family_handle_list():
            yield FamilyProxy(self.db, handle)

    @listproperty
    def children(self):
        # type: () -> Iterator[PersonProxy]
        for handle in self.person.get_family_handle_list():
            f = FamilyProxy(self.db, handle)
            for c in f.children:
                    yield c

    @listproperty
    def spouses(self):
        # type: () -> Iterator[PersonProxy]
        for handle in self.person.get_family_handle_list():
            f = FamilyProxy(self.db, handle)
            if f.father and f.father.handle != self.handle:
                if TYPE_CHECKING:
                    assert isinstance(f.father, PersonProxy)
                yield f.father
            if f.mother and f.mother.handle != self.handle:
                if TYPE_CHECKING:
                    assert isinstance(f.mother, PersonProxy)
                yield f.mother

    @listproperty
    def parent_families(self):
        # type: () -> Iterator[FamilyProxy]
        for handle in self.person.get_parent_family_handle_list():
            yield FamilyProxy(self.db, handle)

    @listproperty
    def parents(self):
        # type: () -> Iterator[PersonProxy]
        for handle in self.person.get_parent_family_handle_list():
            f = FamilyProxy(self.db, handle)
            father = f.father
            if father: 
                if TYPE_CHECKING:
                    assert isinstance(father, PersonProxy)
                yield father
            mother = f.mother
            if mother: 
                if TYPE_CHECKING:
                    assert isinstance(mother, PersonProxy)
                yield mother

    @property
    def mother(self):
        # type: () -> Union[PersonProxy, NullProxy]
        for handle in self.person.get_parent_family_handle_list():
            f = FamilyProxy(self.db, handle)
            return f.mother
        return nullproxy

    @property
    def father(self):
        # type: () -> Union[PersonProxy, NullProxy]
        for handle in self.person.get_parent_family_handle_list():
            f = FamilyProxy(self.db, handle)
            return f.father
        return nullproxy

    @listproperty
    def citations(self):
        # type: () -> Iterator[CitationProxy]
        for handle in self.obj.get_citation_list():
            yield CitationProxy(self.db, handle)


class FamilyProxy(CommonProxy, AttributeProxy, MediaListProxy):
    namespace = "Family"
    _attrs = set() # type: Set[str]

    def __init__(self, db, family_handle, family=None):
        # type: (DbGeneric, str, PrimaryObject) -> None
        CommonProxy.__init__(self, db, family_handle)
        if family:
            self.family = family
        else:
            self.family = self.db.get_family_from_handle(family_handle)
        self.obj = self.family
        self.gramps_id = self.family.gramps_id
        self.reltype = self.family.get_relationship().xml_str()

    def _commit(self, db, trans):
        # type: (Any, Any, Any) -> Any
        db.commit_family(self.obj, trans)

    @listproperty
    def events(self):
        # type: () -> Iterator[EventProxy]
        for eventref in self.family.get_event_ref_list():
            yield EventProxy(self.db, eventref.ref)

    @property
    def father(self):
        # type: () -> Union[PersonProxy, NullProxy]
        handle = self.family.get_father_handle()
        if handle is None:
            return nullproxy
        return PersonProxy(self.db, handle)

    @property
    def mother(self):
        # type: () -> Union[PersonProxy, NullProxy]
        handle = self.family.get_mother_handle()
        if handle is None:
            return nullproxy
        return PersonProxy(self.db, handle)

    @listproperty
    def children(self):
        # type: () -> Iterator[PersonProxy]
        for childref in self.family.get_child_ref_list():
            yield PersonProxy(self.db, childref.ref)


class MediaProxy(CommonProxy, AttributeProxy):
    namespace = "Media"
    _attrs = set() # type: Set[str]

    def __init__(self, db, media_handle, media=None):
        # type: (DbGeneric, str, PrimaryObject) -> None
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
        # type: (Any, Any, Any) -> Any
        db.commit_media(self.obj, trans)

class Filterfactory:
    filterdb = None

    def __init__(self, db):
        # type: (DbGeneric) -> None
        self.db = db

    def getfilter(self, namespace):
        # type: (str) -> Callable
        def filterfunc(filtername, namespace=namespace):
            # type: (str, str) -> Callable
            if 1 or not Filterfactory.filterdb:
                Filterfactory.filterdb = FilterList(CUSTOM_FILTERS)
                Filterfactory.filterdb.load()
            filter_dict = Filterfactory.filterdb.get_filters_dict(namespace)
            filt = filter_dict[filtername]
            return lambda obj: filt.match(obj.handle, self.db)

        return filterfunc

def get_attrs(proxyclass, p):
    # type: (Type, Proxy) -> None
    if proxyclass._attrs: return
    for name in dir(proxyclass) + list(p.__dict__.keys()):  # this contains the @property methods
        if not name.startswith("_"):
            proxyclass._attrs.add(name)

def execute(dbstate, obj, code, proxyclass, env, exectype):
    # type: (DbState, PrimaryObject, str, Any, Any, str) -> Tuple[Any, Dict]
    env["env"] = env
    env["code"] = code
    if obj:
        p = proxyclass(dbstate.db, obj.handle, obj)
        env["self"] = p
        env.obj = p # for Lazyenv
        get_attrs(proxyclass, p)
        env.attrs = proxyclass._attrs.copy()
    else:
        env.attrs = set()
    filterfactory = Filterfactory(dbstate.db)
    if proxyclass:
        env["filter"] = filterfactory.getfilter(proxyclass.namespace)

    if exectype == "exec":
        exec(code, env)
        res = None
    else:
        res = eval(code, env)
    return res, env


def execute_no_category(dbstate, obj, code, envvars, exectype="eval"):
    # type: (DbState, PrimaryObject, str, Dict, str) -> Tuple[Any, Dict]
    return execute(dbstate, None, code, None, envvars, exectype)


def execute_family(dbstate, obj, code, envvars, exectype="eval"):
    # type: (DbState, PrimaryObject, str, Dict, str) -> Tuple[Any, Dict]
    return execute(dbstate, obj, code, FamilyProxy, envvars, exectype)


def execute_person(dbstate, obj, code, envvars, exectype="eval"):
    # type: (DbState, PrimaryObject, str, Dict, str) -> Tuple[Any, Dict]
    return execute(dbstate, obj, code, PersonProxy, envvars, exectype)


def execute_place(dbstate, obj, code, envvars, exectype="eval"):
    # type: (DbState, PrimaryObject, str, Dict, str) -> Tuple[Any, Dict]
    return execute(dbstate, obj, code, PlaceProxy, envvars, exectype)


def execute_event(dbstate, obj, code, envvars, exectype="eval"):
    # type: (DbState, PrimaryObject, str, Dict, str) -> Tuple[Any, Dict]
    return execute(dbstate, obj, code, EventProxy, envvars, exectype)


def execute_media(dbstate, obj, code, envvars, exectype="eval"):
    # type: (DbState, PrimaryObject, str, Dict, str) -> Tuple[Any, Dict]
    return execute(dbstate, obj, code, MediaProxy, envvars, exectype)


def execute_note(dbstate, obj, code, envvars, exectype="eval"):
    # type: (DbState, PrimaryObject, str, Dict, str) -> Tuple[Any, Dict]
    return execute(dbstate, obj, code, NoteProxy, envvars, exectype)


def execute_citation(dbstate, obj, code, envvars, exectype="eval"):
    # type: (DbState, PrimaryObject, str, Dict, str) -> Tuple[Any, Dict]
    return execute(dbstate, obj, code, CitationProxy, envvars, exectype)


def execute_source(dbstate, obj, code, envvars, exectype="eval"):
    # type: (DbState, PrimaryObject, str, Dict, str) -> Tuple[Any, Dict]
    return execute(dbstate, obj, code, SourceProxy, envvars, exectype)


def execute_repository(dbstate, obj, code, envvars, exectype="eval"):
    # type: (DbState, PrimaryObject, str, Dict, str) -> Tuple[Any, Dict]
    return execute(dbstate, obj, code, RepositoryProxy, envvars, exectype)

