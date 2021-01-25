"""
Esimerkki

python3 select.py "gedcom oma.ged _name,BIRT.DATE"

"""
import sys
import struct
import time
import calendar
from collections import defaultdict
import traceback
import pprint

from datatypes import *
import util
import attr
from gramps.gen.display.name import displayer as name_displayer

from gramps.gen.lib import EventType
from gramps.gen.lib import Person
from gramps.gen.lib import Place
from gramps.gen.lib import Date as GrampsDate

from select_parser import Array
import select_parser

yield_nulls = True

attrs = [
    # ("__name__",DT_STRING,8),
    # ("name",DT_STRING,40),
    ("name.type", DT_STRING, 10),
    ("birt.date", DT_GEDCOMDATE, 10),
    ("birt.plac", DT_STRING, 30),
    ("deat.date", DT_GEDCOMDATE, 10),
    ("deat.plac", DT_STRING, 30),
    ("sex", DT_STRING, 1),
    ("occu", DT_STRING, 30),
    ("note", DT_STRING, 30),
]

variables = """
xref = __name__
tag = __tag__
"""
xref = __name__

attrtypes = dict((name, type) for (name, type, width) in attrs)

dynamic_attrs = True


def getvalue1(db, obj, name):
    if obj is None:
        return None
    if name == "father":
        handle = obj.get_father_handle()
        if not handle:
            return None
        obj = db.get_person_from_handle(handle)
    elif name == "mother":
        handle = obj.get_mother_handle()
        if not handle:
            return None
        obj = db.get_person_from_handle(handle)
    elif name == "birth":
        eventref = obj.get_birth_ref()
        if not eventref:
            return None
        obj = db.get_event_from_handle(eventref.ref)
    elif name == "death":
        eventref = obj.get_death_ref()
        if not eventref:
            return None
        obj = db.get_event_from_handle(eventref.ref)
    elif name == "type":
        obj = obj.get_type()
        if not obj:
            return None
    elif name == "date":
        obj = obj.get_date_object()
        if not obj:
            return None
    elif name == "place":
        handle = obj.get_place_handle()
        if not handle:
            return None
        place = db.get_place_from_handle(handle)
        if not place:
            return None
        obj = place
    elif name == "name":
        if isinstance(obj, Person):
            obj = name_displayer.display(obj)
        elif isinstance(obj, Place):
            obj = obj.get_name().get_value()
        elif isinstance(obj, EventType):
            obj = str(obj)
        else:
            obj = str(obj)
    elif name == "children":
        children = []
        for childref in obj.get_child_ref_list():
            child = db.get_person_from_handle(childref.ref)
            if child is not None:
                children.append(child)
        obj = Array(children)
    elif name == "events":
        events = []
        for eventref in obj.get_event_ref_list():
            if not eventref:
                return None
            event = db.get_event_from_handle(eventref.ref)
            events.append(event)
        obj = Array(events)
    elif name == "families":
        if not isinstance(obj, Person):
            raise
        families = []
        for handle in obj.get_family_handle_list():
            family = db.get_family_from_handle(handle)
            families.append(family)
        obj = Array(families)
    elif name == "parent_families":
        if not isinstance(obj, Person):
            raise
        families = []
        for handle in obj.get_parent_family_handle_list():
            family = db.get_family_from_handle(handle)
            families.append(family)
        obj = Array(families)
    else:
        raise RuntimeError("unknown attribute: {}".format(name))
        xxx

    return obj


def getvalue1b(db, obj, attr, attrvalues):
    if attr in attrvalues:
        return attrvalues[attr]
    names = attr.split(".", maxsplit=1)
    obj = getvalue1(db, obj, names[0])
    if len(names) > 1:
        obj = getvalue(db, obj, names[1], attrvalues)
    return obj


def getvalue(db, obj, attr, attrvalues):
    if isinstance(obj, Array):
        values = []
        for o in obj.items:
            v = getvalue(db, o, attr, attrvalues)
            if v is not None:
                values.append(v)
        return Array(values)
    else:
        v = getvalue1b(db, obj, attr, attrvalues)
        if isinstance(v, GrampsDate):
            y, m, d = v.get_ymd()
            timestring = "{}-{}-{}".format(y, m, d)
            v = select_parser.Date(timestring, 0)
            v = v.value
        return v


def find(db, obj, attrlist, attrvalues=None):
    if attrvalues is None:
        attrvalues = {}
    for attr in attrlist:
        value = getvalue(db, obj, attr, attrvalues)
        yield value
