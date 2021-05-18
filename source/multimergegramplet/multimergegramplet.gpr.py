from gramps.version import major_version

register(GRAMPLET,
         id="Multimergegramplet Gramplet",
         name=_("Multimerge Gramplet"),
         description = _("Gramplet "),
         status=STABLE, 
         fname="multimergegramplet.py",
         height=230,
         expand=True,
         gramplet = 'MultiMergeGramplet',
         gramplet_title=_("MultiMergeGramplet"),
         detached_width = 510,
         detached_height = 480,
         version = '1.0.5',
         gramps_target_version = major_version,
         help_url="MultiMergeGramplet",
         navtypes=["Person","Family","Place","Source","Repository","Note"],
         )


