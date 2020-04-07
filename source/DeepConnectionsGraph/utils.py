import os

def get_year(dbstate, ref):
    y = ""
    if ref:
        event = dbstate.db.get_event_from_handle(ref.ref)
        date_object = event.get_date_object()
        if date_object:
            y = date_object.get_year()
            if not y: y = ""
    return str(y)
    
def get_years(dbstate, person):
    birthref = person.get_birth_ref()
    by = get_year(dbstate, birthref)
    deathref = person.get_death_ref()
    dy = get_year(dbstate, deathref)
    if by and dy:
        years = by + "-" + dy
    elif by:
        years = by
    elif dy:
        years = "-" + dy
    else:
        years = ""
    return years


def removefile(fname):
    try:
        os.remove(fname)
    except:
        pass
        

