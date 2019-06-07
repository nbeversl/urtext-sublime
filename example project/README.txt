Sublime-Urtext Documentation 

Updated: <Tue., Jun. 04, 2019, 04:55 PM> /-- Timestamp: <Tue., Jun. 04, 2019, 05:32 PM> --/
Version: 0.6

You can always open this help document by choosing "Urtext: Help" from the command pallette.

{{
Sublime Urtext Documentation >01k
├── Table of Contents >01a
├── TODOs Add: >002
├── Using this document >009
├── Setup >003
│   ├── Empty Project >00a
│   └── Importing existing files >00b
├── File-Level Nodes >00d
├── Inline Nodes >004
│   ├── example inline node text >00e
│   ├── NOTE: File-level nodes do not use curly-braces. >001
│   └── Node Trees >00h
│       ├── From a selected node >00f
│       └── From the root >00g
├── Timestamps >005
│   └── Timeline View: >00k
├── Links: >006
│   ├── Linking to other nodes >0y2
│   │   └── Sublime Text tools to help with linking >00m
│   └── Linking to outside resources >00q
│       ├── Web >00o
│       └── Files >00p
├── project_settings Node >000
├── File and Node Organization >00r
│   ├── Tree-like: Extending node trees beyond the file level >00t
│   │   └── nodes can only have one parent (at a time), although multiple nodes may share the same parent. See 7 >00s
│   ├── Acyclic or Wiki/Web-like >00v
│   │   └── Viewing >00u
│   └── Traverse Mode >00w
├── Metadata: >00x
│   ├── Reserved words >011
│   │   ├── Title (This tag overrides the default title) >00y
│   │   ├── index >00z
│   │   └── parent >010
│   └── Finding nodes by Metadata: >012
├── Dynamic Nodes >01c
│   ├── Example Source Node 1 >014
│   ├── Example Source Node 2 >015
│   ├── Example Source Node 3 >016
│   ├── Example Source Node 4 >017
│   ├── Example Dynamic Node Title >019
│   └── Node Definition for the Table of Contents >01b
├── Filenames >01d
├── Node IDs: >01e
├── Linking to URLS and to Files Outside the Project: >01f
├── Syntax Highlighting and Readability >01g
├── Formatting and Conventions >01h
├── Architecture : Extension and Customization >01i
└── Reference: Key Bindings >01j
/-- ID: 01a
title: Table of Contents
index: 00
kind: dynamic
defined in: >01b
 --/ }}

insert todos >>002

{{  Using this document

    This file is an Urtext file with several inline nodes. It can be used in Sublime Text to try out the features described.

    To enable syntax and node depth highlighting that makes everything easier, select the Sixteen (for light) or Monokai (for dark) color schemes in Preferences -> Color Scheme ... See >01g for more on syntax highlighting. (Press Shift-Control-/ (Shift-Control-forward-slash) to jump to a link.)
                                                                                          /--ID:009--/}}

Setup >>003

{{  File-Level Nodes                                                                                  /--ID:00d--/

    Text is kept in nodes. Nodes can be of any length. Think of a node as a blank piece of paper or a blank area of the paper. 

    A file-level node is a node that may or may not contain other nodes and is identifiable as a single file. A node can be a file but a file can also contain multiple nodes. In this system, it's clearer and more useful to think of text entities as nodes than as files.

    To create a new empty file-level node press Control-Shift-; (Control-Shift-semicolon). The file gets created and uniquely named automatically. The new node has whitespace on top and metadata tag with a node ID. By default, the first non-whitespace line is the node's title. Write a title and anything else into the node. Save it with Super-S as usual.

    Once you have multiple nodes, press Control-Shift-E or select "Urtext: Node Browser" from the Sublime command palette (Shift-Super-P) to browse them. In the Node Browser, nodes are sorted by their time of creation, with most recent first. They can also be sorted by index (see >00z). Find a node by typing part of its title. Open a node by selecting it and pressing return. }}

Inline Nodes >>004

Timeline >>005

Links >>006

{{  project_settings Node
        


                /-- ID:000 --/ }}


{{ File and Node Organization                                                                 /-- ID:00r --/
    
    Urtext does not depend on organization of files at the filesystem level. Instead, you can link file-level nodes together in several ways:

    {{ Tree-like: Extending node trees beyond the file level
      
       Nested inline nodes have an inherent hierarchy that Urtext can represent as a tree, as described above (>00i). You can extend this tree either higher or lower beyond individual file level, mimicking file-system organization. Add the metadata tag `parent`, following by a target Node ID. This will link the tagged node to the targeted node in a child-parent relationship. (See >00x for more information on metadata.) The resulting tree relationship(s) will be understood and displayed accordingly by Urtext (see 79810822060133). 

       The advantages here are many, including:
            - The tree represents the hierachy of actual content, rather than the files containing the content.
            - The tree permits nesting both within and beyond file level.
            - The tree can be displayed from any arbitrary starting point, whether or not its branches are within or beyond a particular file.

       Note that a "tree" here is a strict hierarchical structure that resolves to a single root. Therefore, {{nodes can only have one parent (at a time), although multiple nodes may share the same parent. See 79810728091838. /-- ID:00s --/ }} The intended use for this feature is to link separate individual files into trees. Using it in other ways, such as adding a `parent` tag to a inline node that already has a parent, will override this and, while possible, may have confusing results. Instead, see "Virtual Trees" below (79810728091838).
                                                                                            /-- ID:00t --/ }}

    {{  Acyclic or Wiki/Web-like

        Elaborate writing, notetaking, and reference systems are possible by linking nodes together in tangled and intricate ways a tree will not accomodate. To do so, immediately precede a link to a node (see >00l) by the right angle bracket, such as: >>00u. 

        {{  Viewing
        
            While Urtext cannot draw acyclic graphs in plaintext, it can represent these acyclic relationships from the perspective of any one node. Positioning the cursor in the desired node and and selecting "Urtext : Show Linked Relationships..." from the Sublime command palette will open a split view similar to that in 79810822060133. The currently selected node will be displayed as root; all nodes linking into this nodes, and recursively into those nodes, will be displayed above the root; all files linked from this node, and recursively from those nodes, will be displayed below. Circular references are represented up to one iteration.

            Like trees (79810728103313), these diagrams are displayed as Sublime "scratch" views, meaning they will never report as being dirty (unsaved). They are intended for one-time/temporary use and will not update when a node/file changes. To make permanent and dynamically updated diagrams, see 79810911080130.
                                                                                            /-- ID:00u --/ }}
                                                                                             /-- ID:00v --/ }}                                                                  
    {{ Traverse Mode:                                                    /-- ID:00w; title: Traverse Mode --/

        Once you have a node view, you can navigate it like a file tree by turning on Traverse mode (Ctrl-R). Traverse mode will open a second Sublime pane. As you navigate the nodeview in the left pane with the cursor or mouse, the selected node shows on the right pane. Use Sublime's Focus Group navigation keys, or the mouse, to switch between left and right panes.
        
        The status bar at the bottom of the Sublime window indicates whether Traverse is on or off. Note that if Traverse mode is off, you can also open a link manually (Shift-Ctrl-/) as normal. 
        
        TODO fix Traverse Mode

        }}
                                                                                                                      }}
    
{{  Metadata:                                                                                  /-- ID:00x --/

    Metadata tags can be placed anywhere inside the double curly braces of the node they reference. Metadata tags open with a forward-slash followed by two dashes and close with two dashes followed by a forward slash. The syntax is:
        
        <optional key> : <optional value with optional timestamp> 

    Examples:

        /-- Purpose: work-related <Tue., Mar. 05, 2019, 03:25 PM> --/
        /-- kind: gift_list --/

    You can also string several entries together on one line, separated by semicolons:

        /-- note: example note ; tag: groceries --/

    Other than three reserved words (see below), metadata can be have aribitrary names and values, with open-ended length. Keys and values of metadata tags are indexed automatically and are searchable within the Urtext project. 

    Note that: 

        -   A colon separates the metadata key from the value 
        -   All three values are optional; any content preceding a colon (if one is present) is interpreted as a key; content following the (first) colon is interpreted as a value.
        -   A timestamp anywhere in the value will be indexed as the timestamp for the whole entry. If you put more than one timestamp in an entry, only the first one is read.
        -   Indexing of metadata keys and values is not case-sensitive.

    {{ Reserved words
                                                       
        There are three reserved metadata names:
   
           {{   title
           
                If for some reason you want to override the automatic title and assign a title manually, add a title tag to the metadata block:
           
                   /-- title: Title (This tag overrides the default title)  --/
                                                                                            /-- ID:00y --/ }}
   
           {{   index
           
                You can optionally add a two-digit sort index (00-99) to a node, such as:
   
                   /-- index: 03 --/    
   
                Index tags will sort the files in the node browser (Super-E). Any indexed nodes will before (above) the others, with lowest number appearing first. Remember unindexed notes display in order of creation, newest first. You can give the same index number to multiple nodes; in this case they sort with the most recent node first, within each index.
   
                See Filenames for another way to use for indexes.                            /-- ID:00z --/ }}
   
          {{    parent

                As described in 79810728101527, you add give a node a parent to incorporate it into a node tree beyond the file level, or for other purposes. Example:

                    /-- parent: 00z  --/
                This tag redundantly sets the parent of the present node to 79810728072553, which it already is; however, change the node ID in the tag and look at the table of contents tree to try out unusual results.
          
                                                                                      /-- ID:010 --/ }}                             
                                                                                            /-- ID:011 --/ }}

    {{  Finding nodes by Metadata:                                                            /-- ID:012 --/

        To browse nodes using their metadata, use the "Find By Meta" command in Command Palette. Select the tag name and then "<all>" or a tag value. A nodeview matching the selection will be written into a new buffer. }}

                                                                         /-- ID:056 --/                   }}

{{ Dynamic Nodes
    
    Dynamic nodes compile and update content from other nodes in real time. Dynamic node definitions are enclosed in double square brackets and can be inserted into any node arbitrarily. Press Ctrl-Shift-] to insert a dynamic node definition.

    The definition has the following keys:
        
        - IDDD: (required) : This will be auto-populated by Sublime when using the shortcut above; however you can also replace it with the ID of another node. For example, if you want the contents to replace an existing node, copy and paste that node's ID. If you want it to populate new inline node, create that node and then copy/paste its ID. Otherwise, a new file will be created with the specified ID.

        - include:metadata:<tag name>:<tag values> (optional) : Include nodes with this metadata key and value. Keys and values are chained together and separated by the colon (:) as shown above. To include multiple key/value pairs, write multiple lines.

        - exclude:metadata:<tag name>:<tag values> (optional) : Exclude nodes with this metadata key and value. Keys and values are strung together and separated by the colon (:) as shown above. To exclude multiple key/value pairs, write multiple lines. Excluding will always supersede including, no matter the order listed in the definition. 

        - sort:index:<index> (optional) : How to sort the nodes in the dynamically populated node. Currently, this can be only be 'index'. The index is a zero-padded number between 00 and 99 that determines sort order.

        - metadata:<tag name>:<value> (optional) : Metadata to add to the dynamically populated node. This can be any metadata, including the reserved title, index and parent keys.

        - tree: <root id> : Populates the node with a tree with the provided node ID as root.

        Dynamic nodes will always automatically include the metadata key 'defined in' which will point to the node containing its definition.

    Example:

        Here are four inline nodes with example tags and indexes.

            {{ Example Source Node 1
                    Some text here.
                 /-- ID:014; tag: example_node; index:02 --/ }}

            {{ Example Source Node 2
                 /-- ID:015; tag: example_node; index:05 --/ }}
            
            {{ Example Source Node 3
                 /-- ID:016; tag: example_node; index:01 --/ }}
            
            {{ Example Source Node 4
                 /-- ID:017; tag: example_node; index:05  --/ }}


        Here is an example dynamic node definition targeting node ID >018

            [[ ID:019
                include:metadata:tag:example_node
                exclude:metadata:tag:exclude_this
                sort:index
                show:title
                metadata:title:Example Dynamic Node Title
            ]] >018

        Here is the node defined by the definition above. Changing the dynamic definition and/or the contents or metadata of the source nodes will update the dynamic node. Saving is necessary to trigger the update.

{{  Example Source Node 3  >016
Example Source Node 1  >014
Example Source Node 2  >015
Example Source Node 4  >017
/-- ID: 019
title: Example Dynamic Node Title
kind: dynamic
defined in: >01c
 --/ }}

        {{ Node Definition for the Table of Contents

            Here is another example dynamic definition, which creates the tree at the top of this file:
                [[ ID:01a
                    tree:01k
                    metadata:title:Table of Contents
                    metadata:index:00
                 ]]  

            Changing the titles or nesting of sections in this document will dynamically update the tree.
                                                                                           /--ID:01b--/}}
                                                                                               /--ID:01c--/}}


{{ Filenames                                                                                 /--ID:01d--/

    You can use any naming convention you want to make filenames easy for purposes such as browsing files via the file system, reading and editing nodes using mobile apps, etc.

    Urtext can also rename files automatically in a few convenient formats based on their title and/or index. Renaming by index is useful, for instance, if you want to see nodes appear in a file system, mobile app, or other file browser in the same order they appear within Sublime Urtext.

    To rename a file, select "Rename File from Meta" from the command palette (Command-P). This will rename the file in one of the following schema:

    If an index is present:

        <index> <title>.txt

    If no index is present:

        <node id> <title>.txt

    This system preserves automatic numerical sorting within the filesystem, such that the most recent un-indexed nodes appear first. If you want to use another system, such as putting the title first, you can do so.
                                                                                                                      }}
{{ Node IDs:                                                                                     /--ID:01e--/

    Nodes have 14-digit ID numbers. The 14 digits are an inverse representation of the year, month, day, hour, minute and second they were created. The operating system's file-created or file-modified metadata is avoided because it can be too easily and involuntarily overwritten under ordinary file system operations such as copying and moving files or folders. Creation date is inverted in filenames to force files sorting with the most recent node first. It's useful in mobile applications that have limited or inconvenient filelist sorting and viewing capabilities. 
    
  }}
  
{{ Linking to URLS and to Files Outside the Project:

    Ctrl-/ works to open a link anywhere in an Urtext project. The syntax for making a link is:

        <any text> -> <link to anything> | <any other text>

    Command palette. HTTP (internet) URLs are recognized and open in the default browser, such as www.google.com  | You can link to assets (img, pdf, etc.) within the Urtext project using the native folder separators for your operating system. 

                                                                                               /--ID:01f--/}}

{{  Syntax Highlighting and Readability

        Sublime Urtext offers some basic syntax highlighting by extending the Sixteen and Monokai color scheme in Sublime. It also has a syntax definition .YML file that can be used to add syntax highlighting in other color schemes.

                                                                                               /--ID:01g--/}}

{{ Formatting and Conventions

      to be added


                                                                                            /-- ID:01h --/ }}

{{ Architecture : Extension and Customization

    Some features described in this document are specific to this Sublime Text implementation, (though they could be reproduced in any scriptable text editor), but most are features of Urtext itself. Where there is question, you can find out fairly be inspecting the code. Anything that is 
    [ TO BE COMPLETED ]

 /-- ID:01i --/ }}

{{ Reference: Key Bindings

    The 'Super' key is Command on Mac, Windows key on Windows.

    ctrl+shift+;            New Node
    ctrl+shift+e            Node Browser 
    ctrl+shift+r            Toggle Traverse Mode
    ctrl+shift+s.           Auto rename file from node metadata
    ctrl+shift+/            Open node (from an ID on the same line) 
    ctrl+shift+super+;      New inline node
    ctrl+shift+[            New inline node from selection
    ctrl+Et                  Insert timestamp
    ctrl+shift+]            New dynamic node definition
    ctrl+shift+t            Timeline view
    ctrl+shift+-            Align selected lines to the right (120 character width)
                                                                                           /-- ID:01j --/ }}

 
                                                                                                                    /--
                                                                                                                ID:01k
                                                                                                           tags: urtext
                                                                                    title: Sublime Urtext Documentation
                                                                                                                    --/
                                                                                  