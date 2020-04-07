import json
import os
from pprint import pprint
import subprocess
import time

from gramps.gen.display.name import displayer as name_displayer

map = {}

# these global variables are injected into this module:
# - request
# - dbdata
# - basedir
# - server

import connections
import importlib
importlib.reload(connections)

import utils

def app(path):
    def g(f):
        #print("new path:",path)
        map[path] = f
        return f
    return g

class Response:
    def __init__(self,data=None,content_type=None,status=200):
        self.status = status
        self.data = data
        self.content_type = content_type
        
@app("/")
def index():
    dirname, fname = os.path.split(__file__)
    index_fname = os.path.join(dirname,"index.html")
    return open(index_fname).read()

@app("/get_dbname")
def get_dbname():
    return json.dumps({"dbname":dbdata.dbname})

@app("/list_persons")
def list_persons():
    rsp = []
    t1 = time.time()
    for person_handle,(name,years) in dbdata.names.items():
        name = "{name} {years}".format(name=name,years=years)
        rsp.append(dict(
            gramps_id="person.gramps_id",
            name=name,
            handle=person_handle,
        ))
    t2 = time.time()
    #print("Elapsed:",t2-t1)
    return json.dumps(rsp)

@app("/get_person")
def get_person():
    person_handle = request.args['handle'][0]
    include = request.args.get('include',[])
    person = dbstate.db.get_person_from_handle(person_handle)
    rsp = dict(
        handle=person.handle,
        name=name_displayer.display(person)
    )
    if "notes" in include:
        notes = []
        for notehandle in person.get_note_list():
            note = dbstate.db.get_note_from_handle(notehandle)
            text = note.get()
            notes.append(dict(handle=note.handle,text=text))
        rsp["notes"] = notes
    if "families" in include:
        handles = person.get_family_handle_list()
        rsp["families"] = handles
        handles = person.get_parent_family_handle_list()
        rsp["parent_families"] = handles
    if "events" in include:
        handles = [eventref.ref for eventref in person.get_event_ref_list()]
        rsp["events"] = handles
    return json.dumps(rsp)

@app("/get_family")
def get_family():
    family_handle = request.args['handle'][0]
    include = request.args.get('include',[])
    family = dbstate.db.get_family_from_handle(family_handle)
    rsp = dict(
        handle=family.handle,
        father=family.get_father_handle(),
        mother=family.get_mother_handle(),
        children=[childref.ref for childref in family.get_child_ref_list()],
    )
    return json.dumps(rsp)

@app("/get_connections") # ?handle1=...&handle2=...&use_relatives=true&...
def get_connections():
    def bool(s):
        return s == "true"
        
    #os.chdir( os.path.dirname(os.path.abspath(__file__)) )
    #handle1,handle2 = request.qs.split("/")
    handle1 = request.args["handle1"][0]
    handle2 = request.args["handle2"][0]
    use_relatives = bool(request.args["use_relatives"][0])
    use_events = bool(request.args["use_events"][0])
    use_notes = bool(request.args["use_notes"][0])
    use_associations = bool(request.args["use_associations"][0])
    use_places = bool(request.args["use_places"][0])
    maxpaths = int(request.args["max"][0])
    throttle = bool(request.args["throttle"][0])
    c = connections.VeryDeepConnections(server, dbdata, use_relatives, use_events, use_notes, use_associations, use_places)
    paths = list(c.generate_paths(handle1, handle2, maxpaths, throttle))
    paths = connections.fix_paths(paths)
    rsp = {
        "paths":paths, 
        "shortest_path":min((len(path) for path in paths), default=1)-1,
        "longest_path":max((len(path) for path in paths), default=1)-1,
        "refresh_needed": server.refresh_needed,
    }
    return json.dumps(rsp, default=connections.Link.default)
    
@app("/get_dot")  # ?paths=<paths>
def get_dot():
    import time
    #time.sleep(10)
    paths = json.loads(request.args["paths"][0], object_hook=connections.Link.object_hook)
    handle1 = request.args["handle1"][0]
    handle2 = request.args["handle2"][0]
    lines = connections.generate_graph(dbdata, paths, handle1, handle2)
    dotsrc = "\n".join(lines)
    return dotsrc

@app("/get_image")  # ?paths=<paths>
def get_image():
    import time
    #time.sleep(10)
    paths = json.loads(request.args["paths"][0], object_hook=connections.Link.object_hook)
    handle1 = request.args["handle1"][0]
    handle2 = request.args["handle2"][0]
    lines = connections.generate_graph(dbdata, paths, handle1, handle2)
    lines = [line+"\n" for line in lines]
    #print(lines)
    use_tempfiles = True
    if use_tempfiles:
        utils.removefile("temp.dot")
        utils.removefile("temp.png")
        open("temp.dot","w").writelines(lines)
        # -Goverlap=true -Gsplines=true
        p = subprocess.Popen("dot  -Gcenter=true -T png temp.dot -o temp.png", shell=True)
        p.wait()
        stdout_data = open("temp.png","rb").read()
        #utils.removefile("temp.dot")
        #utils.removefile("temp.png")
    else:
        p = subprocess.Popen("dot -Goverlap=scale -T png", shell=True, 
            stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        (stdout_data,stderr_data) = p.communicate("\n".join(lines).encode("utf-8"))
    return Response(stdout_data,"image/png") 
    
    
@app("/get_svg")  # ?paths=<paths>
def get_svg():
    import time
    #time.sleep(10)
    paths = json.loads(request.args["paths"][0], object_hook=connections.Link.object_hook)
    handle1 = request.args["handle1"][0]
    handle2 = request.args["handle2"][0]
    lines = connections.generate_graph(dbdata, paths, handle1, handle2)
    lines = [line+"\n" for line in lines]
    #print(lines)
    use_tempfiles = True
    if use_tempfiles:
        utils.removefile("temp.dot")
        utils.removefile("temp.png")
        open("temp.dot","w").writelines(lines)
        # -Goverlap=true -Gsplines=true
        p = subprocess.Popen("dot  -Gcenter=true -T svg temp.dot -o temp.svg", shell=True)
        p.wait()
        #stdout_data = open("temp.svg","r", encoding="iso8859-1").read()
        stdout_data = open("temp.svg","r").read()
        i = stdout_data.find("<svg")
        stdout_data = stdout_data[i:].encode("utf-8")
        #utils.removefile("temp.dot")
        #utils.removefile("temp.png")
    else:
        p = subprocess.Popen("dot -Goverlap=scale -T svg", shell=True, 
            stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        (stdout_data,stderr_data) = p.communicate("\n".join(lines).encode("utf-8"))
    return Response(stdout_data,"text/svg") 
    

