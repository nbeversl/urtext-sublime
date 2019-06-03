Sublime-Urtext Documentation 

Updated: <Thu., May. 30, 2019, 02:49 PM>
Version: 0.6

You can always open this help document by choosing "Urtext: Help" from the command pallette.

{{
Sublime Urtext Documentation >01k
├── Example Tree >001
├── What Sublime-Urtext Is >003
│   ├── Urtext is a syntax I invented for writing and organizing in plaintext. >004
│   └── Ideas and Requirements Behind Urtext >008
│       ├── Basic Project Requirements: >005
│       ├── Additional Features: >006
│       └── Characteristics >007
├── Using this document >009
├── Setup >00c
│   ├── Empty Project >00a
│   └── Importing existing files >00b
├── Basics >00d
├── Inline Nodes >00i
│   ├── example inline node text >00e
│   └── Node Trees >00h
│       ├── From a selected node >00f
│       └── From the root >00g
├── Timestamps >00j
│   └── Timeline View: >00k
├── Links: >00l
│   ├── Linking to other nodes >002
│   │   └── Sublime Text tools to help with linking >00m
│   └── Linking to outside resources >00q
│       ├── Web >00o
│       └── Files >00p
├── File and Node Organization: >00r
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
title: Example Tree
kind: dynamic
defined in: >01b
 --/ }}


{{ Add:
  That Urtext syntax has to be selected for syntax highlighting to work.

 /-- ID:002 --/ }}
                                                                                                                        
 
{{  What Sublime-Urtext Is                                                                       /--ID:003--/
    {{ 
    Urtext is a syntax I invented for writing and organizing in plaintext.      /--ID:004; tag:definition--/}}
    Sublime is a modern, programmable text editor. 

    This is an implementation of Urtext in Sublime Text 3. I call it Sublime-Urtext. 

{{  Ideas and Requirements Behind Urtext

    Urtext is a system and a syntax for writing and structuring files in plaintext. There are many tools available for writing and organizing. None of them was what I wanted, so I wrote this.

    The Urtext idea could be implemented using any text editor with built-in or supplemental scripting/automation, a web application, or pencil and paper along with human sorting and organizing routines. This example version uses a Python implementation of Urtext as a module, embedded into the Python scripting capability of Sublime Text 3 as a Sublime package. 

    {{  Basic Project Requirements:

        The original requirements were stringent enough to eliminate every tool already available:

            All in plain text. No proprietary file formats or structure. Usable across multiple platforms and devices.

            Allow both organized and disorganized use. Structured but flexible, all-purpose syntax that allows freeform writing without adapting to a preexisting interface or feature set. Permit gradual aggregation of content with other content.

            Be undistracted by interacting with the file system (naming, saving, organizing of files).  

            Customizable metadata, without relying on the file system.

            Content at least partially editable and organizable from mobile devices.        

            Be capable of hyperlinks, both within/among the files and to outside resources. Function as an all-purpose reference system that can link to anything.         

            Pieces of content should be able to connect to one another in a tree-like as well as non-hierarchical way, such as wiki or flat database style. Files must be able to able to have multiple, not just single, tree-like or other relationships.
            
            Extensible and customizable. This year's needs might not be next year's.

            Does not require years to master. (Looking at you Org Mode.)

            Future-proof. No reliance on anything that may no longer exist in 5 or 100 years.    /--ID:005--/}}

    {{  Additional Features:

            In addition to the requirements above, I wanted the following features found in various other text-oriented tools:

            Basic syntax highlighting, if only to delineate content from structure/syntax.

            Fuzzy search within files. This is already implemented in most modern desktop editors and some mobile text editors, but I wanted the tool to have its own version of this that didn't rely on the editor environment.   

            Version control (using Git, for example). This possiblity is implicit in the commitment to plaintext but important enough to mention.
                                                                                               /--ID:006--/}}

    {{  Characteristics

        As a result of the above, Urtext came out having the following characteristics:
       
            It has two components:

                I. Static plaintext files in a loosely specified syntax.

                II. A compiler that reads, organizes, and compiles the files in real time.

            Like any data format (such as JSON, XML, etc.), the compiling could be done in any language, given the right rules. This particular implementation uses Python, embedded into a Sublime plugin to provide more Sublime-specific editing tools, also using Python, which is Sublime's scripting language.

            The compiler runs continuously in "watchdog" mode. (The latter was inspired by the ``npm run watch`` tool for React development.)

            No need to interact directly with a file system dialog or manually organize files. 

            No subfolder organization scheme. All files are kept in a single folder. Organization of files, file groups, and file relationships is entirely done within the system. This makes it easy to sync and use across devices and platforms where file and folder paths may not always resolve uniformly, and it avoids broken file paths from moved/renamed/reorganized files.

            Filenaming is automatic using a 14-digit derivation of creation time, which also ensures every filename is unique. Further manual naming is possible, provided the 14 digit string is retained in the filename.
           
                                                                                        /-- ID:007 --/ }}
                                                                                             /--ID:008--/}} 
                                                                                                                      }}

{{  Using this document

    This file is an Urtext node with several sub-nodes. It can be used in Sublime Text to try out the features described.

    To enable syntax and node depth highlighting that makes everything easier, select the Sixteen (for light) or Monokai (for dark) color schemes in Preferences -> Color Scheme ... See >01g for more on syntax highlighting. (Press Shift-Control-/ (Shift-Control-forward-slash) to jump to a 14-digit link like.)
                                                                                               /--ID:009--/}}

{{  Setup

    Once the package is installed, it will look for any .txt files in open folders and attempt to compile them. To open a folder as an Urtext project in Sublime, just open the folder or a project that includes the folder.

    {{  Empty Project

        The package will use any existing open folder as a project. You don't need to explicitly set a Sublime Project, but if you intend to do more than one thing at a time in Sublime, it's more convenient to use one; you can then use Select Project -> Quick Switch Project (Ctrl-Cmd-P) to switch among them. 
    
     /-- ID:00a --/ }}
    
     {{ Importing existing files

        To use existing plaintext files, the filenames need to contain a 14-digit Node ID. Sublime Urtext will add this automatically from on the file's creation/modification date and time by selecting "Urtext : Import Project" from the Sublime Command palette. Note that the renaming will occur without a confirmation dialog.

      /-- ID:00b --/ }}


    For syntax and node depth highlighting that makes using Urtext easier, this package adds customizations to two of Sublime's default color schemes. Use the "Sixteen" color scheme for light or "Monokai" for dark. (Select the scheme using Preferences -> Color Scheme ...) See >01g for more on syntax highlighting. 
                                                                                               /--ID:00c--/}}

{{  Basics                                                                                       /--ID:00d--/

    Text is kept in nodes. A node can be a single file but a single file can also contain multiple nodes. Think of a node as a blank piece of paper. Nodes can be of any length. 

    To create a new empty file press Control-Shift-; (Control-Shift-semicolon). There is no need to make a filename or interact with a file system dialog. The new node has whitespace on top and metadata tag with a node ID. By default, the first non-whitespace line is read as the node title. Write a title and anything else into the node. Save it with Super-S.

    Once you have multiple nodes, press Super-E or select "Urtext: Show All Nodes" from the Sublime command palette (Shift-Super-P) to browse them. Nodes are sorted by their time of creation, with the most recent first. They can also be sorted by index (see below). Find a node by typing part of its title. Open a node by selecting it and pressing return. }}

 {{  Inline Nodes                                                                 
     
     Nodes can be nested inside other nodes, whether the parent node is a file or another inline node. The syntax for inline nodes is to wrap the content in double curly braces, like this: {{ example inline node text /-- ID:00e --/ }}. To create an empty inline node, press Shift-Ctrl-{ (Shift - Control - left curly brace). To wrap existing content into an inline node, first select the content and use the same keypress. Inside the double curly braces is a new node with an auto-generated ID. Note that syntactically, the curly braces are part of the enclosed node, not the enclosing node. File-level nodes have and require no curly-braces.
 
     Using inline nodes requires attention to syntax : every opening doubly squiggly bracket must be closed in the same file and requires an ID metadata tag between the opening an closing brackets and not nested in another node.
 
     Inline nodes have their own identity in both content and metadata for all purposes within Urtext. Inline nodes can be nested arbitrarily deep.

     When syntax highlighting is used (>01g), inline nodes will have subtle background shading that shows nesting up to five layers deep. More levels can be added by altering the file sublime_urtext.sublime-syntax.
 
     {{ Node Trees
 
         Once nodes are nested, you can view a tree of their hierarchy in two ways:         

         {{ From a selected node

            Position the cursor in the node you want to see as root (outermost) and select "Urtext: Show Tree From Current Node" from the Sublime Command Palette. This will add a new split view to the left side of the current view in Sublime, containing a tree with the selected node as root. 
                                                                                            /-- ID:00f --/ }}

         {{  From the root

             Position the cursor anywhere in the node/file and select "Urtext: Show Tree From Root". This will do the same as above, but the tree will include everything back to the node's root. If the tree extends upward beyond the current file, that will also be included.
                                                                                            /-- ID:00g --/ }}
         
        Note that each branch of the resulting file tree contains a 14-digit Node ID that works like a link. You can navigate the links on the tree as normal using Shift-Control-/ .

        File trees are displayed in Sublime's "scratch" views, meaning they will never report as being dirty (unsaved). They are intended for one-time/temporary use and will not update when a node/file changes. To make permanent and dynamically updated trees, see 79810911080130.

        CREDIT: The tree display uses the module anytree (https://pypi.org/project/anytree/.)
                                                                                              /--ID:00h--/ }}
                                                                                                /-- ID:00i --/ }}

{{  Timestamps                                                                                   /--ID:00j--/

    One of the most important features for organizing and tracking writing is timestamps. Urtext utilizes human-readable Timestamps in the format: <Thu., Feb. 07, 2019, 05:57 PM>. In Sublime Urtext, insert a timestamp for the current date and time ("now") anywhere by pressing Control-T.

    Timestamps can be part of Metadata (see below) but can also be inserted anywhere else. Urtext utilizes a "loose" parsing of inline timestamps, meaning they can be placed anywhere and will be recognized and parsed by a timeline view.

    {{  Timeline View:                                                                           /--ID:00k--/

        Urtext will parse node timestamp along with inline timestamps into a detailed overview of the project timeline. Press Ctrl-Shift-T or select Urtext: Show Timeline in the Sublime command palette. Each node or inline timestamp is shown in chronological order with nearby text. As everywhere in a project, node IDs shown are links that can be opened using Ctrl-/.  }}    }}

{{  Links:                                                                                     

    {{  Linking to other nodes 

        To write a link, using the "greater than" angular bracket (>) followed by a node ID. Press Shift-Ctrl-/ on a line containing a link to open the node with the linked ID. If the linked node is inline, Sublime will jump to and center its starting point. Note that Urtext reads node regions on every save, so cursor location may be imprecise if the file has been altered since the last save.

        Linking does not require a filename, only a Node ID. Any other information around the Node ID (such as the rest of the filename, or arbitrary text), will be ignored. See 79810913063619 for more information on file naming and Node IDs.

        {{  Sublime Text tools to help with linking    
            Two Sublime Command Palette commands can make linking quick and easy:
         
            Urtext : Link To ...
                Links from the currently viewed node to another node which you can select in the selection panel. When you select a node in the quick panel, a link to that node will be inserted at the cursor.
     
            Urtext: Link From ...
                Links TO the current node FROM another node. When you select this command, a link to the current node will be copied to the clipboard. You can then paste the reference into the node you open in the quick panel.
                                                                                            /-- ID:00m --/ }} 
                                                                               /-- ID: 0y2 --/             }}

    {{ Linking to outside resources

        {{ Web

            HTTP links are recognized automatically and will open in the default browser.
            Example: http://fantutti.com                                                    /-- ID:00o --/ }}

        {{ Files
            TODO  <Fri., May. 03, 2019, 02:24 PM>
                                                                                        /-- ID:00p --/ }}
                                                                                            /-- ID:00q --/ }}
                                                                                                      /-- ID:00l --/                   }}

{{ File and Node Organization:                                                                 /-- ID:00r --/
    
    Urtext does not depend on organization of files at the filesystem level. All files are kept in a single project folder. Instead, you can link file-level nodes together in several ways:

    {{ Tree-like: Extending node trees beyond the file level
      
       Nested inline nodes have an inherent hierarchy that Urtext can represent as a tree, as described above in 79810913063730. You can extend this tree either higher or lower beyond individual file level, mimicking file-system organization. To do so, add the metadata tag `parent`, following by a target Node ID. This will link the tagged node to the targeted node in a child-parent relationship. (See >00x for more information on metadata.) The resulting tree relationship(s) will be understood and displayed accordingly by Urtext (see 79810822060133). 

       The advantages here are many, including:
            - The tree represents the hierachy of actual content, rather than the files containing the content.
            - The tree permits nesting both within and beyond the individual file level.
            - The tree can be displayed from any arbitrary starting point, whether or not its branches are within or beyond a particular file level.

       Note that a "tree" here is a strict hierarchical structure that resolves to a single root. Therefore, {{  nodes can only have one parent (at a time), although multiple nodes may share the same parent. See 79810728091838. /-- ID:00s --/ }} The intended use for this feature is to link separate individual files into trees. Using it in other ways, such as adding a `parent` tag to a inline node that already has a parent, will override this and, while possible, may have confusing results. Instead, see "Virtual Trees" below (79810728091838).
                                                                                            /-- ID:00t --/ }}

    {{  Acyclic or Wiki/Web-like

        Elaborate writing, notetaking, and reference systems are possible by linking nodes together in tangled and intricate ways that a tree will not accomodate. To do so, immediately precede a link to a node (see >00l) by the right angle bracket, such as: 79810728091838. 

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
                [[ ID:001
                    tree:01k
                    metadata:title:Example Tree
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
    ctrl+t                  Insert timestamp
    ctrl+shift+]            New dynamic node definition
    ctrl+shift+t            Timeline view
    ctrl+shift+-            Align selected lines to the right (120 character width)
                                                                                           /-- ID:01j --/ }}

 
                                                                                                                    /--
                                                                                                                ID:01k
                                                                                                           tags: urtext
                                                                                    title: Sublime Urtext Documentation
                                                                                                                    --/
                                                                                  