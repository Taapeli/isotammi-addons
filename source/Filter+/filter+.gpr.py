from gramps.version import major_version, VERSION_TUPLE

objs = """
Person
Family
Event
Place
Citation
Source
Repository
Media
Note
"""

if VERSION_TUPLE < (5, 2, 0):
    additional_args = {}
else:
    additional_args = {"help_url": "https://github.com/Taapeli/isotammi-addons/tree/master/source/Filter+"}
    
for obj in objs.splitlines():
    obj = obj.strip()
    if obj == "": continue
    register(GRAMPLET,
             id=obj + "-Filter+",
             name=_(obj + " Filter+"),
             description = _("Gramplet providing a filter (enhanced)"),
             version="1.0.1",
             gramps_target_version=major_version,
             status = STABLE,
             fname="filter+.py",
             height=200,
             gramplet = obj + 'FilterPlus',
             gramplet_title=_("Filter+"),
             navtypes=[obj],
            **additional_args,
     )

register(RULE,
  id    = 'HasEventBase+',
  name  = _("HasEventBase+"),
  description = _("HasEventBase+ - used by Filter+"),
  version = '1.0.1',
  authors = ["Kari Kujansuu"],
  authors_email = ["kari.kujansuu@gmail.com"],
  gramps_target_version = major_version,
  status = STABLE,
  fname = "filter+.py",
  ruleclass = 'HasEventBasePlus',  # rule class name
  namespace = 'Event',  # one of the primary object classes
)

register(RULE,
  id    = 'HasSourceBase+',
  name  = _("HasSourceBase+"),
  description = _("HasSourceBase+ - used by Filter+"),
  version = '1.0.1',
  authors = ["Kari Kujansuu"],
  authors_email = ["kari.kujansuu@gmail.com"],
  gramps_target_version = major_version,
  status = STABLE,
  fname = "filter+.py",
  ruleclass = 'HasSourceBasePlus',  # rule class name
  namespace = 'Source',  # one of the primary object classes
)

