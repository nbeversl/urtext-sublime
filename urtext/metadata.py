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
import datetime
import time
from .utils import force_list
from .dynamic import UrtextDynamicDefinition
from .timestamp import UrtextTimestamp, default_date

timestamp_match = re.compile('<([^-/<\s][^=<]+?)>')
meta_entry = re.compile('\+?\*{0,2}\w+\:\:[^\n@};]+;?(?=>:})?')
node_title_regex = re.compile('^[^\n_]*?(?= _)', re.MULTILINE)
hash_meta = re.compile(r'(?:^|\s)#[A-Z,a-z].*?\b')
meta_separator = re.compile(r'\s-\s|$')

class NodeMetadata:

    def __init__(self, 
        node,
        project,
        node_id=None):

        self.node = node
        self.entries = []
        self.dynamic_entries = []
        self._last_accessed = 0
        self.project = project
   
    def access(self):
        self._last_accessed = time.time()

    def parse_contents(self, full_contents):

        parsed_contents = full_contents
        remaining_contents = full_contents

        for m in meta_entry.finditer(full_contents):

            keyname, contents = m.group().strip(';').split('::', 1)
            keyname = keyname.lower()
            value_list = meta_separator.split(contents)

            tag_self=False
            tag_children=False
            tag_descendants=False

            if keyname[0] not in ['+','*']:
                tag_self=True
            else:
                if keyname[0] == '+':
                    tag_self = True
                    keyname = keyname[1:]            
                if keyname[0] == '*' :
                    tag_children = True
                    keyname = keyname[1:] #cdr
                if keyname[0] == '*' :
                    tag_descendants = True
                    keyname = keyname[1:] #cdr

            for value in value_list:
                value = value.strip()
                entry = MetadataEntry(
                        keyname, 
                        value, 
                        recursive=tag_descendants,
                        position=m.start(), 
                        end_position=m.start() + len(m.group()))    
                if tag_children or tag_descendants:
                    self.dynamic_entries.append(entry)
                if tag_self and value not in self.get_values(keyname):
                    self.entries.append(entry)

            parsed_contents = parsed_contents.replace(m.group(),' '*len(m.group()), 1)
            remaining_contents = remaining_contents.replace(m.group(),'', 1 )

        # shorthand meta:
        for m in hash_meta.finditer(parsed_contents):
            value = m.group().replace('#','').strip()
            keyname = self.project.settings['hash_key']
            self.add_entry(
                keyname,
                value, 
                position=m.start(), 
                end_position=m.start()+len(m.group()))
            parsed_contents = parsed_contents.replace(m.group(),' '*len(m.group()), 1)
            remaining_contents = remaining_contents.replace(m.group(),'', 1 )

        # inline timestamps:
        for m in timestamp_match.finditer(parsed_contents):
            self.add_entry(
                'inline_timestamp',
                m.group(),
                position=m.start(),
                end_position=m.start() + len(m.group())
                )
            parsed_contents = parsed_contents.replace(m.group(),' '*len(m.group()), 1)
            remaining_contents = remaining_contents.replace(m.group(),'', 1 )
     
        # title
        s = node_title_regex.search(parsed_contents)
        if s:
           title = s.group(0).strip()
           self.add_entry(
                'title', 
                title,
                position=s.start(),
                end_position=s.end())
           parsed_contents = parsed_contents.replace(s.group(),' '*len(s.group()), 1)
           remaining_contents = remaining_contents.replace(s.group(),'', 1 )

        self.add_system_keys()
        return remaining_contents

    def convert_hash_keys(self):
        for entry in self.get_entries('#'):
            entry.set_keyname(self.project.settings['hash_key'])

    def add_entry(self, key, value, position=0, end_position=0, from_node=None, recursive=False):

        if value in self.get_values(key):
            return False
        e = MetadataEntry(
                    key, 
                    value,
                    position=position, 
                    from_node=from_node,
                    end_position=end_position,
                    recursive=recursive)
        if key == 'inline_timestamp' and not e.timestamps:
            return False
        self.entries.append(e)
        return True

    def add_system_keys(self):

        t = self.get_entries('inline_timestamp')
        if t:
            t = sorted(t, key=lambda i: i.timestamps[0].datetime) 
            self.entries.append(MetadataEntry('_oldest_timestamp', '<'+t[0].timestamps[0].string+'>'))
            self.entries.append(MetadataEntry('_newest_timestamp', '<'+t[-1].timestamps[0].string+'>'))

    def get_first_value(self, 
        keyname, 
        as_int=False,
        use_timestamp=False,
        return_type=False):

        if keyname == '_last_accessed':           
            return self._last_accessed

        entries = self.get_entries(keyname.lower())
        if not entries:
            if keyname == 'title':
                return self.node.title
            if return_type:
                if keyname in self.project.settings['use_timestamp']:
                    return default_date
                if keyname in self.project.settings['numerical_keys']:
                    return 999999
                return ''
            return None 

        if use_timestamp or keyname in self.project.settings['use_timestamp']:
            if entries[0].timestamps:
                return entries[0].timestamps[0].datetime
            if return_type:
                return default_date
            return None
                    
        if not entries[0].value:
            if return_type:
                return ''
            return None

        if as_int or keyname in self.project.settings['numerical_keys']:
            try:
                return int(entries[0].value)
            except:
                if return_type:
                    return 9999999
                return None

        return entries[0].value

    def get_values(self, 
        keyname,
        use_timestamp=False,
        lower=False):

        keyname = keyname.lower()
        values = []
        entries = self.get_entries(keyname)
       
        for e in entries:
            if use_timestamp:
                values.extend(e.timestamps)
            else:
                values.append(e.value)        

        if not values and use_timestamp:
            for e in entries:
                values.append(e.timestamps)            
        if lower:
            return strings_to_lower(values)
        return values
    
    def get_keys(self, exclude=[]):
        if self.entries:
            return list(set([e.keyname for e in self.entries if e.keyname not in exclude]))
        return []

    def get_entries(self, keyname):
        keynames = [keyname.lower()]
        return [e for e in self.entries if e.keyname in keynames]

    def get_matching_entries(self, keyname, value):
    
        entries = self.get_entries(keyname)
        matching_entries = []
        if entries:
            use_timestamp = True if isinstance(value, UrtextTimestamp) else False
            for e in entries:
                if not use_timestamp and value == e.value:
                    matching_entries.append(e)
                # TODO FIX
                # elif value.timestamps and e.contains_timestamp(value.timestamps[0]):
                #     matching_entries.append(e)
        return matching_entries

    def get_date(self, keyname):
        """
        Returns the timestamp of the FIRST matching metadata entry with the given key.
        """
        entries = self.get_entries(keyname)
        if entries and entries[0].timestamps:
            return entries[0].timestamps[0].datetime
        return default_date

      
    def clear_from_source(self, source_node_id):
        for entry in list(self.entries):
            if entry.from_node == source_node_id:
                self.entries.remove(entry)

    def log(self):
        for entry in self.entries:
            entry.log()

class MetadataEntry:  # container for a single metadata entry
    def __init__(self, 
        keyname, 
        contents, 
        as_int=False,
        position=None,
        recursive=False,
        end_position=None, 
        from_node=None):

        self.keyname = keyname.strip().lower() # string
        self.string_contents = contents
        self.value = ''
        self.recursive=recursive
        self.timestamps = []
        self.from_node = from_node
        self.position = position
        self.end_position = end_position
        self._parse_values(contents)
        
    def log(self):
        print('key: %s' % self.keyname)
        print(self.value)
        print('from_node: %s' % self.from_node)
        print('recursive: %s' % self.recursive)
        print(self.timestamps)

    def set_keyname(self, keyname):
        self.keyname = keyname
        
    def _parse_values(self, contents):

        for timestamp in timestamp_match.finditer(contents):
            dt_string = timestamp.group(0).strip()
            contents = contents.replace(dt_string, '').strip()
            t = UrtextTimestamp(dt_string[1:-1])
            if t.datetime:
                self.timestamps.append(t)        
        self.value = contents 
   
    def ints(self):
        parts = self.value.split[' ']
        ints = []
        for b in parts:
            try:
                ints.append(int(b))
            except:
                continue
        return ints

    def as_int(self):
        try:
            return int(self.value)
        except:
            return None 

""" Helpers """

def strings_to_lower(list):
    for i in range(len(list)):
        if isinstance(list[i], str):
            list[i] = list[i].lower()
    return list 



