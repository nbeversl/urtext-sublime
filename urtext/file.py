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
import re

if os.path.exists(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'sublime.txt')):
    from .buffer import UrtextBuffer
    import Urtext.urtext.syntax as syntax 
else:
    from urtext.buffer import UrtextBuffer
    import urtext.syntax as syntax

class UrtextFile(UrtextBuffer):
   
    def __init__(self, filename, project):
        super().__init__(project)
        self.filename = filename
        self.file_contents = self._read_file_contents()
        if self.file_contents:
            self.contents = self._get_file_contents()                
            self.lex_and_parse(self.contents)
            self.write_messages(project.settings)
            for node in self.nodes:
                node.filename = filename
                node.file = self

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
            self.log_error(''.join([
                'UnicodeDecode Error: ',
                syntax.file_link_opening_wrapper,
                self.filename,
                syntax.file_link_closing_wrapper]), 0)
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

    def write_messages(self, settings, messages=None):
        if not messages and not self.messages:
            return False
        if messages:
            self.messages = messages

        contents = self._get_file_contents()

        messages = ''.join([ 
            syntax.urtext_message_opening_wrapper,
            '\n',
            '\n'.join(self.messages),
            '\n',
            syntax.urtext_message_closing_wrapper,
            '\n',
            ])

        message_length = len(messages)
        
        for n in re.finditer('position \d{1,10}', messages):
            old_n = int(n.group().strip('position '))
            new_n = old_n + message_length
            messages = messages.replace(str(old_n), str(new_n))
             
        new_contents = ''.join([
            messages,
            contents,
            ])

        self._set_file_contents(new_contents, compare=False)
        self.nodes = []
        self.root_node = None
        self.lex_and_parse(new_contents)