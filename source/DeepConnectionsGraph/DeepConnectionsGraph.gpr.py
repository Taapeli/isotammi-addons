from gramps.version import major_version

register(GRAMPLET,
         id="DeepConnectionsGraph",
         name=_("Deep Connections Graph"),
         description = _("DeepConnectionsGraph Gramplet "),
         status=STABLE, 
         fname="DeepConnectionsGraph.py",
         height=230,
         expand=True,
         gramplet = 'DeepConnectionsGraph',
         gramplet_title=_("Deep Connections Graph"),
         detached_width = 510,
         detached_height = 480,
         version = '1.0.0',
         gramps_target_version = major_version,
         help_url="",
         navtypes=["Dashboard"],
         )


