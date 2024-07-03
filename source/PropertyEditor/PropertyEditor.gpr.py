from gramps.version import major_version, VERSION_TUPLE


if VERSION_TUPLE < (5, 2, 0):
    additional_args = {}
else:
    additional_args = {"audience": EXPERT}

register(GRAMPLET,
         id = "PropertyEditor",
         name = _("PropertyEditor"),
         description = _("Gramplet to edit attributes of multiple objects"),
         status = STABLE,
         version = '1.1.4',
         gramps_target_version = major_version,
         fname = "PropertyEditor.py",
         gramplet = 'PropertyEditor',
         height = 375,
         detached_width = 510,
         detached_height = 480,
         expand = True,
         gramplet_title = _("PropertyEditor"),
         help_url="PropertyEditor Gramplet",
         include_in_listing = True,
         **additional_args,
        )
