# Urtext package for Sublime Text

Urtext is a syntax and system for writing using plaintext. It is for prose writing, research, documentation, journaling, project organization, notetaking, and any other writing or information management that can be done in text form.

For desktop use (PC/Mac/Linux) Urtext is currently implemented in Sublime Text.

## Issues

Pleae post issues at https://github.com/nbeversl/urtext-sublime/issues

## Installation

1. Download Sublime Text. (https://www.sublimetext.com/).

2. Download Urtext and all its dependencies from the monorepo at `https://github.com/nbeversl/urtext_deps`. You can either download this repository as a .ZIP file and unzip it, or if you want to maintain version control, use `git clone --recurse-submodules https://github.com/nbeversl/urtext_deps`. Put the contents of the cloned/unzipped folder (important: not the folder itself) directly into your `Sublime Text 3/Lib/python3.3` folder.

3. Install the Sublime Urtext package. To do this with package control, Press ⌘/Ctrl + ⇧ + P to open the command palette. Type Install Package and press Enter. Then search for Urtext. To install manually, clone or download `https://github.com/nbeversl/urtext_sublime`. Place it in your Packages folder (Sublime Text 3/Packages) 

4. Clone/download this documentation repository and open its folder in Sublime. It will automatically be read as an Urtext project.

Once the Sublime package is installed, it will look for any files with the .txt extension in open folders and attempt to compile them into a project. To open an existing Urtext project, open the folder, a file in the folder, or a Sublime project that includes the folder, and any feature described in this documentation will work.

## Documentation

The documentation of Urtext is itself an Urtext project at https://github.com/nbeversl/urtext-docs. You can read it in directly on Github or download it as a navigable project.

## Versioning

[SemVer](http://semver.org/) for versioning.

## Contributors

https://github.com/nbeversl
https://github.com/PhilipvonMaltzahn

## License

Urtext is licensed under the GNU 3.0 License.

## Acknowledgments

Hat tip to @c0fec0de for [anytree](https://github.com/c0fec0de/anytree).

