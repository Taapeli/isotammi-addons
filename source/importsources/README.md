# Import Sources

The tool "Import Sources" is a specialized tool that can load sources into Gramps from a CSV format file. From each line of the file, the tool creates a new source and optionally attaches it to a repository. The CSV file can also contain one or more attributes for the source.

The tool is installed in Tools > Isotammi tools.

The tool is given a .csv file as input, with the following column headings: 
* Title
* Author
* Abbrev
* Pubinfo
* Repository
* Attributetype
* Attributevalue

The headings are not case-sensitive. The order of the columns does not matter and you do not need to use all of them. Other columns are ignored.

If the title column contains a value then a new source is created and given a running id numbering (S0001, S0002, etc.). IDs already in 
the database are skipped.

The contents of the columns Title, Author, Abbrev and Pubinfo are stored as such in the source.

The Repository column has a special treatment:

Repository can be empty, in which case the source is not connected to any repository.

If the column has an id in square brackets (of the form [Rxxxx]), then the source is connected to the corresponding repository, if it already exists in the database. If there is no such repository, then a new repository will be created named “[Rxxxx]” and the source will be attached to it.

If there is another value in the column, then it is interpreted as the name of the repository, in which case a new repository is created with this name and the source is attached to it. However, if the same name is used multiple times, the tool only creates one repository. If the name is already used by an existing repository, the tool cannot connect the new name to it but this can be fixed later by merging the repositories in question.

You can attach multiple repositories and attribute values to one source. 
This is done by adding new rows below the row for the source. Those rows should only contain repository and/or attribute information. 

The CSV file should use the UTF-8 encoding and comma as the column delimiter.

Here is an example of a CSV file:

1|Title              | Author |Abbrev |Pubinfo|Repository |Attributetype |Attributevalue |
-|------------------ |--------|-------|-------|-----------|--------------|---------------|
2|The New York Times |        |NYT    |       |Newspapers |City          |New York       |
3|                   |        |       |       |           |Founded       |1851           |
4|The Washington Post|        |WP     |       |Newspapers |City          |Washington     |
5|                   |        |       |       |R0123      |              |               |



