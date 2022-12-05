# -*- coding: utf-8 -*-
"""
This file is part of Urtext.

Urtext is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Urtext is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Urtext.  If not, see <https://www.gnu.org/licenses/>.

"""
import os

if os.path.exists(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'sublime.txt')):
    from .buffer import UrtextBuffer
else:
    from urtext.buffer import UrtextBuffer

class UrtextFile(UrtextBuffer):
   
    def __init__(self, filename, project):
        self.basename = os.path.basename(filename)
        self.nodes = {}
        self.root_nodes = []
        self.alias_nodes = []           
        self.parsed_items = {}
        self.messages = []    
        self.filename = filename    
        self.errors = False
        self.project = project
        self.file_contents = self._read_file_contents()
        self.contents = self._get_file_contents()        
        self.filename = os.path.join(project.path, os.path.basename(filename))
        self.could_import = False        
        self.clear_errors(self.contents)
        symbols = self.lex(self.contents)
        self.parse(self.contents, symbols)
        self.write_errors(project.settings)

    def _get_file_contents(self):
        return self.file_contents

    def _read_file_contents(self):
        
        """ returns the file contents, filtering out Unicode Errors, directories, other errors """
        try:
            with open(self.filename, 'r', encoding='utf-8',) as theFile:
                full_file_contents = theFile.read()
        except IsADirectoryError:
            return None
        except UnicodeDecodeError:
            self.log_error('UnicodeDecode Error: f>' + self.filename, 0)
            return None
        return full_file_contents

    def _insert_contents(self, inserted_contents, position):
        self._set_file_contents(''.join([
            self.file_contents[:position],
            inserted_contents,
            self.file_contents[position:],
            ]))

    def _replace_contents(self, inserted_contents, range):
        self._set_file_contents(''.join([
            self.file_contents[:range[0]],
            inserted_contents,
            self.file_contents[range[1]:],
            ]))

    def _set_file_contents(self, new_contents, compare=True): 

        new_contents = "\n".join(new_contents.splitlines())
        if compare:
            existing_contents = self._get_file_contents()
            if existing_contents == new_contents:
                return False
        with open(self.filename, 'w', encoding='utf-8') as theFile:
            theFile.write(new_contents)
        self.file_contents = new_contents
        return True

