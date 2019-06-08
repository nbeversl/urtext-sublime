Table of Contents
Sublime-Urtext Documentation

Updated: <Tue., Jun. 04, 2019, 04:55 PM> /-- Timestamp: <Tue., Jun. 04, 2019, 05:32 PM> --/
Version: 0.6

{{  Using this document

    You can always open this help document from Sublime by choosing "Urtext: Help" from the command pallette.

    To go to a link in the table of contents, press ctrl-shift-/ from any line. (See Links >00j for more information).
    To return to this table of contents, press ctrl-shift-h.

    This file is an Urtext file with several inline nodes. It can be used in Sublime Text to try out the features described.

    To enable syntax and node depth highlighting that makes everything easier, select the Sixteen (for light) or Monokai (for dark) color schemes in Preferences -> Color Scheme ... See >01g for more on syntax highlighting. (Press Shift-Control-/ (Shift-Control-forward-slash) to jump to a link.)
                                                                                          /--ID:009--/}}

{{
Sublime Urtext Documentation >01k
├── Using this document >009
├── Table of Contents >01a
├── TODOs Add: >002
├── Setup >003
│   ├── Empty Project >00a
│   └── Importing existing files >00b
├── File-Level Nodes >01j
├── Inline Nodes >004
│   ├── example inline node text >00e
│   ├── NOTE: File-level nodes do not use curly-braces. >001
│   └── Node Trees >00h
│       ├── From a selected node >00f
│       └── From the root >00g
├── Node Metadata >00x
│   ├── Reserved words >011
│   │   ├── title (This tag overrides the default title) >00y
│   │   └── index >00z
│   └── Finding nodes by Metadata: >012
├── Basic Requirements: >005
├── Links: >00j
│   ├── Linking to other nodes >0y2
│   │   └── Sublime Text tools to help with linking >00m
│   └── Linking to outside resources >00q
│       ├── Web >00o
│       ├── Files >00p
│       └── Linking to URLS and to Files Outside the Project: >01f
├── File and Node Organization >00r
│   ├── Tree-like: Extending node trees beyond the file level >00t
│   │   └── nodes can only have one parent (at a time), although multiple nodes may share the same parent. See 7 >00s
│   ├── Acyclic or Wiki/Web-like >00v
│   │   └── Viewing >00u
│   └── Traverse Mode >00w
├── Dynamic Nodes >01c
│   ├── Example Source Node 2 >015
│   ├── Example Source Node 3 >016
│   ├── Example Source Node 4 >017
│   ├── Example Dynamic Node Title >019
│   └── Node Definition for the Table of Contents >01b
├── Filenames >01d
├── Node IDs: >01e
├── Syntax Highlighting and Readability >01g
├── Formatting and Conventions >01h
├── Architecture : Extension and Customization >01i
└── Reference: Key Bindings >018
/-- ID: 01a
title: Table of Contents
index: 00
kind: dynamic
defined in: >01b
 --/ }}

    insert todos >>002 
    Setup >>003
    File Level Nodes >>01j
    Inline Nodes >>004
    Metadata >>00x
    Timeline >>005
    Links >>00j
    File and Node Organization >>00r
    Dynamic Nodes >>01c
    
   
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

{{ Node IDs:                                                                                     

   The operating system's file-created or file-modified metadata is avoided because it can be too easily and involuntarily overwritten under ordinary file system operations such as copying and moving files or folders. 
    
          /--ID:01e--/      }}
  

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

    Key Bindings >>018
 
                                                                                                                    /--
                                                                                                                ID:01k
                                                                                                           tags: urtext
                                                                                    title: Sublime Urtext Documentation
                                                                                                                    --/
                                                                                  