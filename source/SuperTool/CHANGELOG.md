## Changes in version 1.1.0 (2021-07-21)

### Menus
Most of the buttons in the old user interface have been removed. The commands are now available as menu choices.

The `Select font` button is replaced by the Settings/Preferences menu. Currently there are two settings, the font and the default directory/folder for the @include files.

### Transaction handling
Now all queries are done under a transaction even if they do not change the database. This avoids a certain error condition. Commit is still required if any changes are to be made - either by the `Commit changes` checkbox or explicitly calling the commit methods in the script. 

### Version
The version (v1.1.0) of the tool is displayed in the bottom right corner.

### Parameterized scripts
The scripts can be parameterized with the `getargs` function. Calling this function will ask the user for values of parameters and it returns an object with those values. 

### Function 'flatten' 
The `flatten` function is now properly implemented: it will work for arbitrarily deeply nested lists (previously only one level was supported).

### Script file format 
The script file format is slightly changed. 
- Scripts now work also if there is a line starting with a left bracket [.
- A version number is added

### Code refactorings
The file `supertool_categories.py` was renamed to `supertool_utils.py` and some functions were moved there.

### Other
* The `type` attribute for notes has been added.
* The user supplied Python code is pre-compiled for possible performance improvement.
* The CSV file does not contain the object handles by default anymore.


