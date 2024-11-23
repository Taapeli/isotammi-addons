Dates
-----
Author: kari.kujansuu@gmail.com

Gramplet to fix invalid Event date formats (formats that Gramps cannot parse) via selectable Search and Replace. That Gramplet can only be added to the Events category.

Rationale:
Some genealogical tools use formats that are non-standard or ambiguous. This gramplet allows transforming imported Event dates into formats that Gramps can understand. The transforms are applied to the selected rows in the Events category view. 

The "Events with an invalid date" custom filter rule (https://github.com/Taapeli/isotammi-addons/tree/master/source/_hasvaliddate) can be used to limit rows to those with non-conformant dates.

The gramplet only affects dates that are in text-only format. If Gramps has already interpreted the date incorrectly and stored a formally correct date then this gramplet cannot fix it.

The gramplet has several predefined corrections. For each event/date the grampled tries this fixes in order until one matches. Note the the period in these patterns actually represents any of the following: period (.), comma (,), hyphen (-) or slash (/).

Before the predefined fixes there is the possibility to replace text strings so that the result matches a valid date or matches one of the predefined formats. With the regular expression feature you can do more flexible corrections.

Documentation published to:
https://www.gramps-project.org/wiki/index.php/Addon:Isotammi_addons#Dates
