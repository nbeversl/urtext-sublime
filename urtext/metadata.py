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
import pytz

default_date = pytz.timezone('UTC').localize(datetime.datetime(1970,1,1))
timestamp_match = re.compile('(?:<)([^-/<\s][^=<]*?)(?:>)')
inline_meta = re.compile('\*{0,2}\w+\:\:[^\n};]+;?(?=>:})?')

class NodeMetadata:

    def __init__(self, node, full_contents, settings=None):

        self.node = node
        self._entries, self.dynamic_entries = parse_contents(
            full_contents,
            node,
            settings=settings)
        self._sort()       
        self._last_accessed = 0
        
    def _sort(self):
        """ from extant entries, populate a dict by key"""
        
        self.entries = {}
        for e in self._entries:
            self.entries.setdefault(e.keyname, [])
            if e not in self.entries[e.keyname]:
               self.entries[e.keyname].append(e)

        node_id = self.get_first_value('id')
        if node_id:
            self._entries = sorted(self._entries, key = lambda entry: entry.position)
            for i in range(len(self._entries)):
                self._entries[i].index = i
                self._entries[i].node = node_id

    def get_links_to(self): 
        return sorted(
            [r for r in self.node.project.links_to[node_id] if not self.node.project.nodes[r].dynamic],
            key = lambda n: n.index )

    def get_links_from(self):
        return sorted(
            [r for r in self.node.project.links_from[node_id] if not self.node.project.nodes[r].dynamic],
            key = lambda n: n.index )
        

    def get_first_value(self, keyname):
        if keyname == '_last_accessed':
            return self.node.last_accessed

        entries = self.entries.get(keyname)
        if not entries or not entries[0].values:
            return ''
        return entries[0].values[0]

    
        

    def get_values(self, 
        keyname,
        # use_timestamp=False, # use timestamp as value (FUTURE)
        substitute_timestamp=False  # substitutes the timestamp as a string if no value
        ):

        """ returns a list of values for the given key """
        values = []
        entries = self.entries.get(keyname)
        if not entries:
            return values
        for e in entries:
            values.extend(e.values)
            
        if not values and substitute_timestamp:
            for e in entries:
                if e.dt_stamp != default_date:
                    values.append(e.dt_string)            
        return values
  
    def get_entries(self, 
        keyname, 
        value=None):

        keyname = keyname.lower()
        if keyname in self.entries:
            return self.entries[keyname]
        return []

    def get_matching_entries(self, 
        keyname, 
        value,
        use_timestamp=False):

        entries = self.get_entries(keyname)
        matching_entries = []
        for e in entries:
            if not use_timestamp:
                if value in e.values:
                    matching_entries.append(e)
            else:
                if value == e.dt_stamp:
                    matching_entries.append(e)

        return matching_entries

    def get_date(self, keyname):
        """
        Returns the timestamp of the FIRST matching metadata entry with the given key.
        Requires the project be parsed (dt_stamp set from dt_string)
        """
        entries = self.get_entries(keyname)
        if entries:
            return entries[0].dt_stamp

        return default_date # ?

    # Set
    
    def add_meta_entry(self, 
        key, 
        values,
        from_node=None,
        position=0):

        new_entry = MetadataEntry(key, values, None, from_node=from_node, position=position)
        self._entries.append(new_entry)
        self._sort()

    def clear_from_source(self, source_node_id):
        for entry in list(self._entries):
            if entry.from_node == source_node_id:
                self._entries.remove(entry)
        self._sort()

    # Debug

    def log(self):
        for entry in self._entries:
            entry.log()

class MetadataEntry:  # container for a single metadata entry
    def __init__(self, 
        keyname, 
        value, 
        dt_string,
        children=False,
        recursive=False,
        position=None,
        end_position=None, 
        from_node=None):

        self.keyname = keyname.strip().lower() # string
        self.values = value         # always a list
        self.dt_string = dt_string
        self.dt_stamp = default_date # default or set by project        
        self.from_node = from_node
        self.position = position
        self.end_position = end_position
        self.children = children
        self.recursive = recursive

    def log(self):
        print('key: %s' % self.keyname)
        print('value: %s' % self.values)
        print('datetimestring: %s' % self.dt_string)
        print('datetimestamp: %s' % self.dt_stamp)
        print('from_node: %s' % self.from_node)
        print('children: %s' % self.children)
        print('recursive: %s' % self.recursive)

def parse_contents(full_contents, node, settings=None):

    project = node.project

    parsed_contents = full_contents

    # parse inline metadata:
    entries = []
    dynamic_entries = []
    for m in inline_meta.finditer(full_contents):

        key, value = m.group().strip(';').split('::', 1)

        """
        For lines containing a timestamp
        """
        timestamp = timestamp_match.search(value)
        dt_string = ''
        if timestamp:
            dt_string = timestamp.group(1).strip()
            value = value.replace(timestamp.group(0), '').strip()

        values = []
        value_list = value.split('|')

        for value in value_list:

            if key not in settings['case_sensitive']:
                value = value.lower()
            value = value.strip()
            if key in settings['numerical_keys']:
                try:
                    value = int(value)
                except ValueError:
                    value = -1
            if value:
                values.append(value)

        recursive = False
        children = False
        if key[0] == '*' :
            children = True
            key = key[1:]
            if key[0] == '*' :
                recursive = True
                key = key[1:]

        end_position = m.start() + len(m.group())
        
        entry = MetadataEntry(
                key, 
                values, 
                dt_string, 
                children=children,
                recursive=recursive,       
                position=m.start(), 
                end_position=end_position)    

        if children or recursive:
            dynamic_entries.append(entry)

        else:
            entries.append(entry)

        parsed_contents = parsed_contents.replace(m.group(),'X'*len(m.group()))

    # parse inline timestamps:
    
    for m in timestamp_match.finditer(parsed_contents):
        stamp = m.group()
        position = m.start()
        end_position = position + len(m.group())
        entries.append(
            MetadataEntry(
                'inline-timestamp', 
                '', 
                stamp[1:-1],     
                position=position, 
                end_position=end_position)
                )    

    return entries, dynamic_entries
