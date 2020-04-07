"""fff        
This is an attempt to enhance the "Deep Connections" gramplet to find even more connections.
Author: kari.kujansuu@gmail.com, 2019


"""


#------------------------------------------------------------------------
#
# Python modules
#
#------------------------------------------------------------------------
from collections import defaultdict
import json
import os
from pprint import pprint

#------------------------------------------------------------------------
#
# GRAMPS modules
#
#------------------------------------------------------------------------
from gramps.gen.display.name import displayer as name_displayer

from gramps.gen.const import GRAMPS_LOCALE as glocale
try:
    _trans = glocale.get_addon_translator(__file__)
except ValueError:
    _trans = glocale.translation
_ = _trans.gettext

import utils

nodecolor       = "#eeeeee"

# these need to match the colors in index.html:
startnode_color = "#ffffaa"
endnode_color   = "#aaffff"
bgcolor         = "lightsteelblue"

DEBUG = False
class DBData:
    def __init__(self):
        self.xref = defaultdict(list)  # (handle_type,handle) -> [Link(assoc_type, handle_type, handle, [role]), ]
        self.names = {} # personhandle -> (name,years)
        self.family_names = {} # family_handle -> name
        self.events = {} # eventhandle -> (type, gramps_id, description)
    
class Link:
    def __init__(self, assoc_type, from_node, to_node, reverse=False, sortkey=0):  
        # assoc_type = 'family', 'parent_family', 'assoc', <event-role>
        # from_node/to_node = (node_type, handle), eg. ('Person', '22d9be333eee272e9e166b2572215')
        
        self.assoc_type = assoc_type
        self.from_node = from_node
        self.to_node = to_node
        self.reverse = reverse
        if assoc_type[0] == "<": assoc_type = assoc_type[1:]
        if assoc_type == "parent_family": 
            self.sortkey = 1
        elif assoc_type == "family": 
            self.sortkey = 2
        else:
            self.sortkey = 3
            
    def __hash__(self):
        return hash((self.assoc_type,self.from_node,self.to_node,self.reverse))

    def __eq__(self, other):
        return (self.assoc_type,self.from_node,self.to_node,self.reverse) == (other.assoc_type,other.from_node,other.to_node,other.reverse)
        
    def __repr__(self):
        return "Link({self.assoc_type},{self.to_node})".format(self=self)
        
    def copy(self):
        return Link(self.assoc_type, self.from_node, self.to_node, self.reverse)

    @staticmethod            
    def default(obj):
         #if isinstance(obj, Link):
         if hasattr(obj, "assoc_type"):
             return obj.__dict__
         # Let the base class default method raise the TypeError
         return json.JSONEncoder.default(self, obj)

    @staticmethod            
    def object_hook(objdict):        
        if "assoc_type" in objdict:
            if "counter" in objdict: del objdict["counter"]
            link =  Link(**objdict)
            #link.__dict__ = objdict
            return link
        return objdict

def add_notelinks(dbstate, dbdata, key, person):
    for note_handle in person.get_note_list():
        note = dbstate.db.get_note_from_handle(note_handle)
        links = note.get_links()
        for link in links:
            #print(link)
            # esim. ('gramps', 'Person', 'handle', 'e6b5be02dfb30ff524c96f5d7d1')
            if link[0] == "gramps": # and link[1] == "Person":
                if link[2] == "handle":
                    object_type = link[1]
                    linkhandle = link[3]
                    dbdata.xref[key].append(Link("note",key,(object_type,linkhandle)))

def load_dbdata(dbstate):
    dbdata = DBData()
    dbdata.dbname = dbstate.db.get_dbname()
    "Returns a structure containing the relevant parts of the database (family tree)"
    for person_handle in dbstate.db.get_person_handles():
        person = dbstate.db.get_person_from_handle(person_handle)
        name = name_displayer.display(person)
        years = utils.get_years( dbstate, person )
        dbdata.names[person_handle] = (name,years)
        assoc_list = person.get_person_ref_list()
        key = ('Person',person_handle)
        for family_handle in person.get_family_handle_list():
            dbdata.xref[key].append(Link("family", key, ('Family', family_handle)))
        for family_handle in person.get_parent_family_handle_list():
            dbdata.xref[key].append(Link("parent_family", key, ('Family', family_handle)))
        for eventref in person.get_event_ref_list():
            event_handle = eventref.ref
            event = dbstate.db.get_event_from_handle(event_handle)
            role = str(eventref.role)
            try:
                role = role.encode("utf-8").decode("iso8859-1")  # role seems to have an invalid encoding, trying to fix
            except:
                pass
            if True or event.get_type() == "Kaste":
                dbdata.xref[key].append(Link(role, key, ('Event', event_handle) ))
        for assoc in assoc_list:
            assoc_handle = assoc.get_reference_handle()
            dbdata.xref[key].append(Link("assoc: " + assoc.rel, key, ('Person', assoc_handle)))
        add_notelinks(dbstate, dbdata, key, person)

    for family_handle in dbstate.db.get_family_handles():
        family = dbstate.db.get_family_from_handle(family_handle)
        name = get_family_name(dbstate, family)
        dbdata.family_names[family_handle] = name
        key = ('Family',family_handle)
        for eventref in family.get_event_ref_list():
            event_handle = eventref.ref
            role = str(eventref.role)
            try:
                role = role.encode("utf-8").decode("iso8859-1")  # role seems to have an invalid encoding, trying to fix
            except:
                pass
            dbdata.xref[key].append(Link(role, key, ('Event', event_handle) ))
        add_notelinks(dbstate, dbdata, key, family)

    for event_handle in dbstate.db.get_event_handles():
        event = dbstate.db.get_event_from_handle(event_handle)
        dbdata.events[event_handle] = ( event.get_type(), event.gramps_id, event.get_description() )
        key = ('Event',event_handle)
        add_notelinks(dbstate, dbdata, key, event)

    # generate reverse links
    dbdata2 = DBData()
    for links in list(dbdata.xref.values())[:]:
        for link in links[:]:
            if link.assoc_type[0] == "<": continue
            dbdata.xref[link.to_node].append(Link("<"+link.assoc_type, link.to_node, link.from_node, reverse=True))
    for key,links in dbdata.xref.items():
        dbdata.xref[key] = sorted(links, key=lambda link: link.sortkey )            
    print("loaded new dbdata")
    return dbdata
    

def get_family_name(dbstate, family):
    father_handle = family.get_father_handle()
    mother_handle = family.get_mother_handle()
    if father_handle:
        father = dbstate.db.get_person_from_handle(father_handle)
    else:
        father = None
    if mother_handle:
        mother = dbstate.db.get_person_from_handle(mother_handle)
    else:
        mother = None

    if father and mother:
        return name_displayer.display(father) + " and " + name_displayer.display(mother)
    if father:
        return name_displayer.display(father)
    if mother:
        return name_displayer.display(mother)
    return family.gramps_id


def generate_graph(dbdata, paths, start_handle, end_handle):
    lines = []
    def emit(s):
        lines.append(s)

    emit("digraph Path")
    emit("{")
    emit('  graph [shape=box,style=filled,bgcolor="lightsteelblue"];'.format(bgcolor=bgcolor))
    emit('  node [shape=box,style="rounded,filled",fillcolor="{fillcolor}"];'.format(fillcolor=nodecolor))
    emitted_lines = set()
    emitted_nodes = set()
    for path in paths:
        prevnode = None
        for link in path:
            handle_type, handle = link.to_node
            nodename = handle
            color = "black"
            attrs = 'shape=box,style=rounded'
            if handle_type == 'Person' and nodename not in emitted_nodes:
                pname, years = dbdata.names[handle]
                label = pname + "\n" + years
                if handle == start_handle:
                    emit('    {nodename} [label="{label}",fillcolor="{color}"];'.format(nodename=nodename,label=label,color=startnode_color))
                elif handle == end_handle:
                    emit('    {nodename} [label="{label}",fillcolor="{color}"];'.format(nodename=nodename,label=label,color=endnode_color))
                else:
                    emit('    {nodename} [label="{label}"];'.format(nodename=nodename,label=label))
            if handle_type == 'Family' and nodename not in emitted_nodes:
                family_name = dbdata.family_names[handle]
                emit('    {nodename} [label="{family_name}",{attrs}];'.format(**locals()))
            if handle_type == 'Event' and nodename not in emitted_nodes:
                type, gramps_id, description = dbdata.events[handle]
                name = "{} Event {} ({})".format(type, gramps_id, description)
                emit('    {nodename} [label="{name}"];'.format(**locals()))
            emitted_nodes.add(nodename);
            if prevnode:
                color = "black"
                role = link.assoc_type
                if role[0] == "<":
                    role = role[1:]
                    reverse = True
                else:
                    reverse = False
                if role in ("vanhempi","lapsi","sisarus"): color = "red"
                if role in ("puoliso"): color = "blue"
                if role in ("kummi","Kummi"): color = "yellow"
                attrs = 'color={color},fontcolor={color}'.format(**locals())
                #if 0 and link.reverse:
                #if link.assoc_type[0] == "<":
                if reverse:
                    role = link.assoc_type[1:]
                    line = '    {nodename} -> {prevnode} [label="{role}",{attrs}];'.format(**locals())
                else:
                    line = '    {prevnode} -> {nodename} [label="{link.assoc_type}",{attrs}];'.format(**locals())
                if line not in emitted_lines:
                    emit(line)
                    emitted_lines.add(line)
            prevnode = nodename
    emit("}")
    return lines

def fix_paths(paths):
    paths = [fix_path(path) for path in paths]
    paths = list(set(tuple(path) for path in paths))
    pprint(paths)
    return paths

def fix_path(path):
    newpath = []
    while path:
        link = path[0]
        if len(path) < 2:
            path = path[1:]
        elif path[1].to_node != link.from_node: 
            link = link.copy()
            link2 = path[1]
            key = (link.assoc_type, link2.assoc_type)
            if key == ("parent_family","<family"):
                link.assoc_type = "vanhempi"
                link.to_node = link2.to_node
                path = path[2:]
            elif key == ("family","<parent_family"):
                link.assoc_type = "lapsi"
                link.to_node = link2.to_node
                path = path[2:]
            elif key == ("family","<family"):
                link.assoc_type = "puoliso"
                link.to_node = link2.to_node
                path = path[2:]
            elif key == ("parent_family","<parent_family"):
                link.assoc_type = "sisarus"
                link.to_node = link2.to_node
                path = path[2:]
            elif link.assoc_type == "Kummi" and link2.assoc_type == "<Päähenkilö":
                link.assoc_type = "<kummi"
                link.to_node = link2.to_node
                link.reverse = True
                path = path[2:]
            elif link.assoc_type == "Kummi":
                link.assoc_type = "<kummi"
                path = path[1:]
            elif link.assoc_type == "<Kummi":
                link.assoc_type = "kummi"
                path = path[1:]
            elif link.assoc_type == "Päähenkilö" and link2.assoc_type == "<Kummi":
                link.assoc_type = "kummi"
                link.to_node = link2.to_node
                path = path[2:]
            else:
                path = path[1:]
        if link.to_node == link.from_node: continue
        newpath.append(link)
    return newpath

class VeryDeepConnections:
    """
    Finds deep connections between two people.
    Uses a breadth-first search algorithm.
    In addition to biological relationships also supports connections via
    - events
    - notes
    - associations

    Events: two people are connected through an event if both are participants in the same event. 
    Events can also attached to families.

    Notes can have links to people or families.

    People can be linked to other people through associations.

    All such links can be traversed in both directions when searching for the connection.
    The method "get_relatives" is a generator that yields one object at a time along the with the current path
    from the start person to the object. The objects can be people, families or events. Each relation in the
    path can contain a role. So the generated path can be like

    (person1) -[parent]-> (family) -[child]-> (person2) -[witness]-> (baptism event) -[primary]-> (person3)

    So from the searching algorithm perspective the nodes can be people, families or events.
    """
    def __init__(self, server, dbdata, use_relatives, use_events, use_notes, use_associations, use_places):
        self.server = server
        self.dbdata = dbdata
        self.use_relatives = use_relatives
        self.use_events = use_events
        self.use_notes = use_notes
        self.use_associations = use_associations
        self.use_places = use_places
        self.cache = None

    def get_relatives(self, object_type, handle, path):
        """
        Gets all of the relations of handle.
        """
        return self.dbdata.xref[(object_type,handle)]

    def contains(self, path, new_handle):
        for link in path:
            if link.to_node[1] == new_handle:
                return True
        return False

    def getname(self,current_type, current_handle):
        if current_type == 'Person':
            return self.dbdata.names[current_handle]
        if current_type == 'Family':
            return self.dbdata.family_names[current_handle]
        if current_type == 'Event':
            return self.dbdata.events[current_handle]
        return "??? " + current_type + ": " + current_handle
        
    def generate_paths(self, person1handle, person2handle, maxpaths, throttle):
        c  = VeryDeepConnections( self.server, self.dbdata, 
            use_relatives=True, use_events=False, use_notes=False, use_associations=False, use_places=False)
        #yield from c.generate_paths1(person1handle, person2handle, maxpaths, throttle)
        if self.use_events:        
            c  = VeryDeepConnections( self.server, self.dbdata, 
                use_relatives=True, use_events=True, use_notes=False, use_associations=False, use_places=False)
            yield from c.generate_paths1(person1handle, person2handle, maxpaths, throttle)
        if self.use_notes:        
            c  = VeryDeepConnections( self.server, self.dbdata, 
                use_relatives=True, use_events=self.use_events, use_notes=True, use_associations=False, use_places=False)
            yield from c.generate_paths1(person1handle, person2handle, maxpaths, throttle)
        if self.use_associations:        
            c  = VeryDeepConnections( self.server, self.dbdata, 
                use_relatives=True, use_events=self.use_events, use_notes=self.use_notes, use_associations=True, use_places=False)
            yield from c.generate_paths1(person1handle, person2handle, maxpaths, throttle)

    def generate_paths1(self, person1handle, person2handle, maxpaths, throttle):
        total_relations_found = 0
        #print("generate_paths", person1handle, person2handle)
        #throttle = False

        visited = set()
        link = Link("self", (None,None), ('Person', person1handle))
        link.counter = 0
        queue = [[link]]
        counter1 = 0
        counter2 = 0
        import time
        #time.sleep(10)
        while queue and self.server.running:
            counter1 += 1
            #if counter1 > 500000: break
            if DEBUG:
                print("queue:")
                pprint(self.queue)
            current_path = queue.pop(0)
            lastlink = current_path[-1]
            (current_type, current_handle) = lastlink.to_node
            if DEBUG and counter1 < 200:
                print(counter1,"got",self.getname(current_type, current_handle),lastlink.counter)
            if current_handle == person2handle:
                total_relations_found += 1
                #print("---> yield",counter1, current_path)
                yield current_path
                if total_relations_found >= maxpaths:
                    break                   
            if current_type == 'Person' and current_handle in visited:
            #if current_handle in visited:
                if DEBUG and counter1 < 200:
                    print("- skipped: ", counter1, self.getname(current_type, current_handle))
                continue
            visited.add(current_handle)
            #if len(current_path) > 24: continue
            for link in self.dbdata.xref[(current_type,current_handle)]:
                counter2 += 1
                if DEBUG: 
                    print(">> path:", link )
                if not self.use_events and link.from_node[0] == 'Event': continue
                if not self.use_events and link.to_node[0] == 'Event': continue
                if not self.use_notes and link.assoc_type in ("note","<note"): continue
                if (not self.use_associations and (
                    link.assoc_type.startswith("assoc:") or
                    link.assoc_type.startswith("<assoc:"))
                ):
                    continue

                if DEBUG and counter1 < 200:
                    print("- link: ", counter1, self.getname(*link.to_node))
                if self.contains( current_path, link.to_node[1]): 
                    if DEBUG and counter1 < 200:
                        print("- skipped2: ", counter1, self.getname(*link.to_node))
                    continue

                if link.to_node[1] != current_handle and link.to_node[1] != link.from_node[1]:
                    link.counter = counter1
                    queue.append( current_path + [link] )
                    #queue.sort(key=lambda links: links[0].sortkey)
                    
                    
        
