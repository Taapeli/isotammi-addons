from gramps.version import major_version, VERSION_TUPLE


if VERSION_TUPLE < (5, 2, 0):
    additional_args = {}
else:
    additional_args = {"audience": EXPERT}

register(GRAMPLET,
         id="DeepConnectionsGraph",
         name=_("Deep Connections Graph"),
         description = _("DeepConnectionsGraph; a Dashboard Server Gramplet"),
         status=STABLE, 
         fname="DeepConnectionsGraph.py",
         height=230,
         expand=True,
         gramplet = 'DeepConnectionsGraph',
         gramplet_title=_("Deep Connections Graph"),
         detached_width = 510,
         detached_height = 480,
         version = '1.2.8',
         gramps_target_version = major_version,
         help_url="Addon:Isotammi_addons#Deep_Connections_Graph",
         navtypes=["Dashboard"],
         **additional_args,
         )


