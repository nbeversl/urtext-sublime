# Urtext

Urtext is a syntax and system for writing using plaintext. It is for prose writing, research, documentation, journaling, project organization, notetaking, and any other writing or information management that can be done in text form. This package is an implementation in Python and Sublime Text.

This is an alpha release.

## Issues

Pleae post issues at https://github.com/nbeversl/urtext-sublime/issues

## Installation

You can install this package through Package Control.

Press ⌘/Ctrl + ⇧ + P to open the command palette.

Type Install Package and press Enter. Then search for Urtext.

## Documentation

The documentation is included in the package in the form of an example Urtext project. You can read it in directly on Github in the [/documentation](https://github.com/nbeversl/urtext-sublime/tree/github-master/documentation) folder.

After installation in Sublime, it will function as an Urtext project, press ⌘/Ctrl + ⇧ + P to open the command palette. Type Urtext: Documentation and press Enter.

Excerpts of the documentation are included in this README.

## Project Information

### Ideas and Requirements

There are many tools available for writing and organizing. None of them was what I wanted, so I wrote this.

Urtext could be implemented in any text editor with built-in or supplemental scripting/automation, a web application, or pencil and paper along with human sorting and organizing routines. This version uses a Python implementation of Urtext, embedded into the Python scripting capability of Sublime Text 3 as a package. 

### Basic Requirements

The original requirements were stringent enough to eliminate every tool already available:

   - All in plain text. No proprietary file formats or information structure. Plaintext is fast, flexible, cross-platform, device-portable, and future-proof.

   - Usable across multiple platforms and devices.

   - Allow both organized and disorganized use. Structured but flexible, all-purpose syntax that allows freeform, fragmentary writing while permitting gradual aggregation of content with other content. No need to adapt to a preexisting interface or feature set. 

   - Be undistracted by interacting with the file system (dialogues for naming, saving, organizing of files).

   - Customizable and extensible metadata without relying on the file system.

   - Mobile use must not depend on live internet or cellular data; the content must wholly reside on, and sync among, every device that uses it.

   - Capable of hyperlinks, both within/among the files and to outside resources. Function as an all-purpose reference system that can link to anything.         

   - Pieces of content should be able to connect to one another in a tree-like as well as non-hierarchical fashion, such as wiki or flat database style. Files must be able to able to have multiple, not just single, tree-like or other relationships.

   - Extensible, hackable, customizable. This year's needs might not be next year's. One person's needs might not be another's.

   - Does not require years to master. (Looking at you Org Mode.)

   - Future-proof. No reliance on anything that may not exist in 5 or 100 years. 

### Additional Features

In addition to the requirements above, I wanted the following features found in various other text-oriented tools:

   - Syntax highlighting to delineate content from structure/syntax.

   - Fuzzy search within files. This is already implemented in most modern desktop editors and some mobile text editors, but I wanted the tool to have its own version of this that didn't rely on the editor features or environment.

   - Version control (using Git, for example). This possiblity is implicit in the commitment to plaintext but important enough to mention.
           
### Characteristics

As a result of the above, Urtext came out having the following characteristics:
   
   - It is offered as a syntax and a system, not as a particular implementation. 

   - It is open source.

   - It has two components:

      - Static plaintext files in a loosely specified syntax.
      
      - A service that organizes, and compiles the files. This can run either manually or continuously in "watchdog" mode. In this Sublime package, it runs in watchdog mode.

### About This Implementation

This package is an example implementation of Urtext using Sublime Text. It has two components:

   - An embedded pure Python module called "Urtext". It could be used in any Python environment and has no special relationship to Sublime Text. The Python module also has its own Github and can be used independently of the Sublime package. For instance, success has been found running it on iPhone using Pythonista.

   - A Sublime package that uses Sublime Text as a user interface for editing Urtext files. The package includes the Urtext module (above) as well as a syntax definition, two color schemes, commands, and key bindings for Sublime Text.    

   As a result of this combination, some features in this documentation are built into Urtext, while others are part of only the Sublime Text implementation. An effort has been made to indicate which features are which. 

## Versioning

[SemVer](http://semver.org/) for versioning.

## Author

https://github.com/nbeversl

## License

Urtext is licensed under the GNU 3.0 License.

## Acknowledgments

Hat tip to @c0fec0de for [anytree](https://github.com/c0fec0de/anytree).

