templates = {

'new_file_node.txt' : """
New File Node _   

This is a file node. 

Make new bracket nodes with `Ctrl-Shift-{` (Ctrl-Shift-leftSquigglyBracket)

Example:  

  { Example text 
  
   @232} 

 @sdw
""",


'new_project_home.txt' : """
Home Node _ @8mw

Welcome to Urtext. This is a new, blank Urtext project.

This is the "home" node; to get here from anywhere in the project, press Ctrl-Shift-H
For full documentation, see https://github.com/nbeversl/urtext-docs,

To follow the links below, use `ctrl+shift+/` or `ctrl-shift-MouseClick` (from cursor/pointer position)


To view project settings, visit | project_settings >2bl

NOTE: Add Created date



{  Making New Nodes _

    `ctrl+shift+;` Create New File Node

    `ctrl+shift+{`  New Bracket Node; Will wrap any existing contents if selected.

    `ctrl+shift+]`  New Bracket Node with Dynamic Definition 

    `ctrl+shift+1` Insert Single-Line Bracket Node

    `ctrl+shift+^` Bullet Node 

    `ctrl+shift+f` Random node  @5pd}

{  Project Navigation _
    
    `ctrl+shift+h`  Home Node

    `ctrl+shift+e`  Browse Nodes in Current Project (Dropdown)

    `ctrl+shift+*`  Browse Nodes in All Projects (Dropdown)

    `ctrl+shift+<`  Nav Backward (like a browser)

    `ctrl+shift+/` or `ctrl-shift-MouseClick` Open Link (from cursor/pointer position)

    `ctrl+shift+r` Toggle Traverse Mode

    `ctrl+shift+>` Nav Forward (like a browser)   

    (Command Palette) "Urtext: Metadata Browser" : Browse Project by Metadata

    @off}


{ Content _

    `ctrl+shift+t` Insert Timestamp

    `ctrl+shift+i`  Add Node ID (rarely needed)  @rsj}


{ File Management _
    
    `ctrl+shift+s`  Rename File  

    (Command Palette) "Urtext: Move File to Other Project" : Moves the file to another (chosen) project.

    (Command Palette) "Urtext: Reindex All Files" : Renames all files with an optional index prefix.

    (Command Palette) "Urtext: Delete This Node" : Deletes the current file node.

    @dbr}


{ Global _

    `ctrl+shift+o` List All Projects @08d}


{ Links _

        
    `ctrl+shift+c` Copy a Link to This Node (in cursor position) 

    `ctrl+shift+super+c` Copy a Link to This Node (in cursor position), Include Project Title

    `ctrl+shift+'` Insert Link To New New

    `ctrl+shift+left-arrow` Browse Nodes that Link to This Node

    `ctrl+shift+right-arrow` Browse Nodes This Node Links To

    `ctrl+shift+l` Link From Here To Node (select from Dropdown) 

    (Command Palette) "Urtext: Link to ..." (same as `ctrl+shift+l`)

@pv8}

{ Other Features _
    
    `ctrl+shift+x` Rake Keywords (Entire Project) 

    `ctrl+shift+space`  Rake Free Associate (Show Nodes with Similar Keywords, based on cursor position) 

    `ctrl+shift+super+right`  Pop Node 

    `ctrl+shift+super+left`  Pull Node 

    `ctrl+shift+0`  Add Metadata to Linked Node From This Node 

    (Command Palette) "Urtext: Consolidate Metadata" : Consolidates all metadata in the node to a single block.


    @rym}


{ Utility Commands _


    (Command Palette) "Urtext: New Project" : Creates a new Urtext project in a chosen folder.

    (Command Palette) "Urtext: Reload Project" : Reloads the current project.


@m45}


<Tue., Oct. 05, 2021, 02:12 PM>
""",


'project_settings.txt' : """

This is the `project_settings` node. In the metadata you can specify settings for the project.

always_oneline_meta::False
When creating a new node, sets whether the metadata will appear on one line separated by semicolon,or on separate lines.

breadcrumb_key::
When popping nodes, optionally adds a breadcrumb showing which node the popped node was popped from, 
and the timestamp.

console_log::True
(True or False): Sets whether Urtext will log updates, errors, messages to Sublime's Python console.
(Press Control-tilde(~)  to open the console)

contents_strip_internal_whitespace::True
When including contents in dynamic nodes, determines whether internal multiline whitespace gets stripped from the dynamic output.

contents_strip_outer_whitespace::True
When including contents in dynamic nodes, determines whether leading or trailing whitespace gets stripped from the dynamic output.

exclude_files::
Sets filenames in the project folder to be excluded from the project, if any.

exclude_from_star::title - _newest_timestamp - _oldest_timestamp - _breadcrumb - def
When marking metadata using the * and ** syntax, these keys will get omitted, if present.

import::False
If set to true, all new text files added to the project folder get imported automatically on the fly by adding an Urtext Node ID.

index::100; (Sets the index of this node, not part of project settings.)

inline_node_timestamp::True 
Specifies whether a new bracket node gets a timestamp.

filenames::PREFIX - index - title - _oldest_timestamp
Specifies format for filenames when using Reindex Files

file_node_timestamp::True

filename_datestamp_format::%m-%d-%Y
Specifies how dates will be formatted in filenames when using 

filename_title_length::100
Sets a maximum title length (in characters) when using Reindex Files

file_index_sort::index - _oldest_timestamp
When using Reindex Files with an prefix, specifies the order in which the files should be prefixed. For more information see "Reindex Files" in the Urtext Reference.

hash_key::keyword
The keyname to use for the hash mark metadata shortcut.

history_interval::10
Sets the interval (in seconds) at which history snapshots should be taken of your views. Increase the interval to have smaller .diff files in your /history folder. Decrease it to have more granular edit history.

home::8mw
Identifies the home node for the project, connected to the "Home" key
Press Ctrl-Shift-H to go to the Home node of this documentation, whose ID is 013

keyless_timestamp::True

open_with_system::pdf 
File extensions to always open using the default system application.

new_file_line_pos::2

new_file_node_format::$timestamp $id $cursor
Spcifies the default format for new file nodes. The following values can be string together in any way:
  $timestamp
  $id (required)
  $device_keyname
  $cursor - where to position the cursor

node_browser_sort::_oldest_timestamp
Specifies the key order by which nodes will sort in the Node Browser dropdown

node_date_keyname::timestamp
When creating a new node, if the node gets a timestamp key, this sets the keyname.

numerical_keys::_index - index
Sets keys that should always be interpreted numerically for sorting and processing in dynamic output.

project_title::New Urtext Project
Provides a title for the entire project

tag_other::
Accepts two values which will be interpreted as key/value.
When quick-tagging a node from another (see "Quick Tagging" in the Urtext Reference), this metadata entry will be the 
one added.

timestamp_format::%a., %b. %d, %Y, %I:%M %p
Set the format of the timestamp when using Timestamps.
This accepts a Python `strftime` directive. For possible format strings, see https://strftime.org/

timezone::US/Eastern
Specifices a timezone to which the timestamp keys should be localized, or, if including a timezone in the `timestamp_format`, what timezone to include.

title::project_settings
Reserved key; Sets the title of the node, overrides other ways of setting it.  It is used to specificy this node as the project settings node.

use_timestamp::updated - timestamp - inline_timestamp - _oldest_timestamp - _newest_timestamp
Specifies keys for which the timestamp component should be used instead of the text value.

case_sensitive::title - notes - comments - project_title - timezone - timestamp_format - filenames - weblink - timestamp
Specifies which keys' contents should be parsed case-sensitive.
 
@2bl
"""
}

