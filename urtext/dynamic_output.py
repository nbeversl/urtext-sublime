
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
    import Urtext.urtext.syntax as syntax
    from Urtext.urtext.node import UrtextNode
else:
    import urtext.syntax as syntax
    from urtext.node import UrtextNode

class DynamicOutput():

    def __init__(self, 
        format_string, 
        project_settings):

        self.title = ''
        self.date = ''
        self.link = ''
        self.pointer = ''
        self.meta = ''
        self.entry = ''
        self.key = ''
        self.contents = ''
        self.other_format_keys = {}
        self.project_settings = project_settings
        self.needs_contents = False
        self.needs_other_format_keys = []        
        self.format_string = format_string

        #TODO : randomize -- must not be any regex operators.
        self.shah = '%&&&&888'
        self.values = []
        self.item_format = self._tokenize_format()

        self._build_needs_list()

    def _tokenize_format(self):

        item_format = self.format_string
        item_format = bytes(item_format, "utf-8").decode("unicode_escape")
        
        # tokenize all $ format keys
        format_keys = syntax.format_key_c.findall(item_format)
        for token in format_keys:
            item_format = item_format.replace(token, self.shah + token)
            self.values.append(token)

        return item_format

    def _build_needs_list(self):

        defined_list = [
            'title',
            '_link',
            '_pointer',
            '_date',
            '_meta',
            '_contents',
            '_entry',
        ]

        contents_syntax = re.compile(
            self.shah+'\$_contents'+'(:\d*)?', 
            re.DOTALL)      
        contents_match = re.search(
            contents_syntax, 
            self.item_format)
        if contents_match:
            self.needs_contents = True
        all_format_keys = re.findall(
            self.shah+'\$[\.A-Za-z0-9_-]*', 
            self.item_format, 
            re.DOTALL)

        for match in all_format_keys:
            meta_key = match.strip(self.shah+'$') 
            if meta_key not in defined_list:
                self.needs_other_format_keys.append(meta_key)

    def output(self):
        
        self.item_format = self.item_format.replace(
            self.shah + '$title', 
            self.title)
        self.item_format = self.item_format.replace(
            self.shah + '$_link', 
            self.link)
        self.item_format = self.item_format.replace(
            self.shah + '$_pointer', 
            self.pointer)
        self.item_format = self.item_format.replace(
            self.shah + '$_date', 
            self.date)
        self.item_format = self.item_format.replace(
            self.shah + '$_meta', 
            self.meta)
        self.item_format = self.item_format.replace(
            self.shah + '$_entry', 
            self.entry)

        contents_syntax = re.compile(
            self.shah+'\$_contents'+'(:\d*)?', 
            re.DOTALL)      
        contents_match = re.search(contents_syntax, self.item_format)

        if contents_match:
            contents = self.contents
            if self.project_settings['contents_strip_outer_whitespace']:
                contents = contents.strip()
            if self.project_settings['contents_strip_internal_whitespace']:
                contents =  strip_internal_whitespace(contents)
            #TODO check whether this is ever reached:
            while '>>' in contents:
                contents = contents.replace('>>','(>)>')
            suffix = ''
            if contents_match.group(1):
                suffix = contents_match.group(1)                        
                length_str = contents_match.group(1)[1:] # strip :
                length = int(length_str)
                if len(contents) > length:
                    contents = contents[0:length] + ' (...)'
            self.item_format = self.item_format.replace(
                ''.join([
                        self.shah,
                        '$_contents',
                        suffix
                    ]),
                ''.join([ contents, '\n']))
                    
        # all other meta keys
        for meta_key in self.other_format_keys:
            token = self.shah + '$' + meta_key
            value = ''.join(self.other_format_keys[meta_key])
            self.item_format = self.item_format.replace(token, value)

        return self.item_format

def strip_internal_whitespace(contents):
    contents = '\n'.join([l.strip() for l in contents.split('\n')])
    while '\n\n\n' in contents:
        contents = contents.replace('\n\n\n','\n\n')
    return contents
