
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

import re
format_key_regex = re.compile('\$_?[A-Za-z0-9_-]+', re.DOTALL)

class DynamicOutput():

    def __init__(self, format_string):

        self.title = ''
        self.date = ''
        self.link = ''
        self.meta = ''
        self.entry = ''
        self.key = ''
        self.contents = ''
        self.last_accessed = ''
        self.other_format_keys = {}

        self.needs_title = False
        self.needs_meta = False
        self.needs_link = False
        self.needs_date = False
        self.needs_contents = False
        self.needs_entry = False
        self.needs_other_format_keys = []
        self.needs_last_accessed = False
        
        self.needs_key = False
        self.needs_values = False

        self.format_string = format_string
        self.shah = '%&&&&888' #FUTURE : possibly randomize -- must not be any regex operators.
        self.values = []
        self.item_format = self._tokenize_format();

        self._build_needs_list()

    def _tokenize_format(self):

        item_format = self.format_string
        item_format = bytes(item_format, "utf-8").decode("unicode_escape")
                    
        # tokenize all $ format keys
        format_keys = re.findall(format_key_regex, item_format)
        for token in format_keys:
            item_format = item_format.replace(token, self.shah + token)
            self.values.append(token)

        return item_format

    def _build_needs_list(self):

        defined_list = [
            'title',
            'link',
            'date',
            'meta',
            'contents',
            'entry' # for metadata collection
            '_last_accessed',
        ]

        if self.shah + '$title' in self.item_format:
            self.needs_title = True
        if self.shah + '$link' in self.item_format:
            self.needs_link = True
        if self.shah + '$date' in self.item_format:
            self.needs_date = True
        if self.shah + '$meta' in self.item_format:
            self.needs_meta = True
        if self.shah + '$entry' in self.item_format:
            self.needs_entry = True
        if self.shah + '$key' in self.item_format:
            self.needs_key = True
        if self.shah + '$values' in self.item_format:
            self.needs_values = True
        if self.shah + '$_last_accessed' in self.item_format:
            self.needs_last_accessed = True

        contents_syntax = re.compile(self.shah+'\$contents'+'(:\d*)?', re.DOTALL)      
        contents_match = re.search(contents_syntax, self.item_format)
        if contents_match:
            self.needs_contents = True

        all_format_keys = re.findall( self.shah+'\$[A-Za-z0-9_-]+', self.item_format, re.DOTALL)                   
        for match in all_format_keys:
            meta_key = match.strip(self.shah+'$') 
            if meta_key not in defined_list:
                self.needs_other_format_keys.append(meta_key)

    def output(self):
      
        self.item_format = self.item_format.replace(self.shah + '$title', self.title)
        self.item_format = self.item_format.replace(self.shah + '$link', self.link)
        self.item_format = self.item_format.replace(self.shah + '$date', self.date)
        self.item_format = self.item_format.replace(self.shah + '$meta', self.meta)
        self.item_format = self.item_format.replace(self.shah + '$entry', self.entry)
        self.item_format = self.item_format.replace(self.shah + '$key', self.key)
        self.item_format = self.item_format.replace(self.shah + '$values', str(self.values))
        self.item_format = self.item_format.replace(self.shah + '$_last_accessed', str(self.last_accessed))

        contents_syntax = re.compile(self.shah+'\$contents'+'(:\d*)?', re.DOTALL)      
        contents_match = re.search(contents_syntax, self.item_format)

        if contents_match:
            contents = self.contents
            while '>>' in contents:
                contents = contents.replace('>>','(>)>')
            suffix = ''
            if contents_match.group(1):
                suffix = contents_match.group(1)                        
                length_str = contents_match.group(1)[1:] # strip :
                length = int(length_str)
                if len(contents) > length:
                    contents = contents[0:length] + ' (...)'
            self.item_format = self.item_format.replace(self.shah + '$contents' + suffix, contents + '\n')
                    
        # all other meta keys
        for meta_key in self.other_format_keys:
            token = self.shah+'$'+meta_key
            value = ''.join(self.other_format_keys[meta_key])
            self.item_format = self.item_format.replace(token, value );    

        return self.item_format