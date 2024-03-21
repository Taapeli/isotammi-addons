from gramps.version import major_version, VERSION_TUPLE


if VERSION_TUPLE < (5, 2, 0):
    additional_args = {}
else:
    additional_args = {"audience": EXPERT}

register(GRAMPLET,
         id="Multimergegramplet Gramplet",
         name=_("Multimerge Gramplet"),
         description = _("Multimerge Gramplet"),
         status=STABLE, 
         fname="multimergegramplet.py",
         authors = ['Kari Kujansuu', 'Nick Hall'],
         authors_email = ['kari.kujansuu@gmail.com', 'nick-h@gramps-project.org'],
         height=230,
         expand=True,
         gramplet = 'MultiMergeGramplet',
         gramplet_title=_("MultiMergeGramplet"),
         detached_width = 510,
         detached_height = 480,
         version = '1.2.2',
         gramps_target_version = major_version,
         help_url="http://github.com/Taapeli/isotammi-addons/tree/master/source/multimergegramplet/README.md",
         navtypes=["Person","Family","Place","Source","Repository","Note","Event",
                   "Citation","Media"],
         **additional_args,
         )
