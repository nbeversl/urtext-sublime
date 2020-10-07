# Urtext package for Sublime Text

Urtext is a syntax and system for writing using plaintext. It is for prose writing, research, documentation, journaling, project organization, notetaking, and any other writing or information management that can be done in text form. 

Urtext does not have a user interface and requires implementation using a text editor or other wrapper. This package is an implementation for desktop (PC/Mac/Linux) using Sublime Text.

## Installation

1. Download Sublime Text. (https://www.sublimetext.com/).

2. Install the Urtext package for Sublime Text. To do this with package control, Press ⌘/Ctrl + ⇧ + P to open the command palette. Type Install Package and press Enter. Then search for Urtext. To install manually, clone or download `https://github.com/nbeversl/urtext_sublime`. Place it in your Packages folder (Sublime Text 3/Packages) 

3. The package will install several dependencies into Sublime Text. There is currently one dependency that must be installed manually: From https://pypi.org/project/anytree, download the Source package (https://files.pythonhosted.org/packages/d8/45/de59861abc8cb66e9e95c02b214be4d52900aa92ce34241a957dcf1d569d/anytree-2.8.0.tar.gz). Unzip this package and copy the `anytree` subfolder (important: not the entire unzipped folder) directly into your `Sublime Text 3/Lib/python3.3` folder.

Once the Sublime package is installed, it will look for any files with the .txt extension in open folders and attempt to compile them into a project. To open an existing Urtext project, open the folder, a file in the folder, or a Sublime project that includes the folder, and any feature described in this documentation will work.

## Documentation

The documentation of Urtext is itself an Urtext project at https://github.com/nbeversl/urtext-docs. You can read it in directly on Github or download it as a navigable project. It will automatically be read as an Urtext project when opened. Clone/download the documentation repository, open its folder in Sublime Text. Pres Ctrl-Shift-H to view the home page with the table of contents. 

## Issues

Please post issues at https://github.com/nbeversl/urtext-sublime/issues

## Versioning

[SemVer](http://semver.org/) for versioning.

## Contributors

https://github.com/nbeversl
https://github.com/PhilipvonMaltzahn

## License

Urtext is licensed under the GNU 3.0 License.

## Acknowledgments

Hat tip to @c0fec0de for [anytree](https://github.com/c0fec0de/anytree).

