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
    from .dynamic import UrtextDynamicDefinition
    from .timestamp import UrtextTimestamp, default_date
    import Urtext.urtext.syntax as syntax
else:
    from urtext.dynamic import UrtextDynamicDefinition
    from urtext.timestamp import UrtextTimestamp, default_date
    import urtext.syntax as syntax

class NodeMetadata:

    def __init__(self, 
        node,
        project,
        node_id=None):

        self.node = node
        self.entries_dict = {}
        self.dynamic_entries = []
        self.project = project
   
    def parse_contents(self, full_contents):

        parsed_contents = full_contents
        remaining_contents = full_contents

        for m in syntax.metadata_entry_c.finditer(full_contents):
            keyname, contents = m.group().strip(syntax.metadata_end_marker).split(syntax.metadata_assigner, 1)                 
            value_list = syntax.metadata_separator_pattern_c.split(contents)
            
            tag_self=False
            tag_children=False
            tag_descendants=False

            if not syntax.metadata_tag_self_c.match(keyname[0]) and not syntax.metadata_tag_desc_c.match(keyname[0]):
                tag_self=True
            else:
                if syntax.metadata_tag_self_c.match(keyname[0]):
                    tag_self = True
                    keyname = keyname[1:]
                if syntax.metadata_tag_desc_c.match(keyname[0]):
                    tag_children = True
                    keyname = keyname[1:]
                if syntax.metadata_tag_desc_c.match(keyname[0]):
                    tag_descendants = True
                    keyname = keyname[1:]

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
                    self.add_entry(
                        keyname, 
                        value,
                        position=m.start(),
                        end_position=m.start() + len(m.group()))

            parsed_contents = parsed_contents.replace(m.group(),' '*len(m.group()), 1)
            remaining_contents = remaining_contents.replace(m.group(),'', 1 )

        for m in syntax.hash_meta_c.finditer(parsed_contents):
            value = syntax.hash_key_c.sub('',m.group()).strip()
            keyname = self.project.settings['hash_key']
            self.add_entry(
                keyname,
                value, 
                position=m.start(), 
                end_position=m.start() + len(m.group()))
            parsed_contents = parsed_contents.replace(m.group(),' '*len(m.group()), 1)
            remaining_contents = remaining_contents.replace(m.group(),'', 1 )

        # inline timestamps:
        for m in syntax.timestamp_c.finditer(parsed_contents):
            self.add_entry(
                'inline_timestamp',
                m.group(),
                position=m.start(),
                end_position=m.start() + len(m.group()))
            remaining_contents = remaining_contents.replace(m.group(),' ', 1 )

        self.add_system_keys()
        return remaining_contents

    def add_entry(self, 
        key, 
        value,
        is_node=False,
        position=0, 
        end_position=0, 
        from_node=None, 
        recursive=False):

        key = key.lower()
        if value in self.get_values(key):
            return False

        e = MetadataEntry(
            key, 
            value,
            is_node=is_node,
            position=position, 
            from_node=from_node,
            end_position=end_position,
            recursive=recursive)
        if key == 'inline_timestamp' and not e.timestamps:
            return False
        self.entries_dict.setdefault(key, [])
        if e.is_node:
            self.entries_dict[key] = [e]
        else:
            self.entries_dict[key].append(e)

    def add_system_keys(self):
        t = self.get_entries('inline_timestamp')
        if t:
            t = sorted(t, key=lambda i: i.timestamps[0].datetime) 
            self.add_entry('_oldest_timestamp', t[0].timestamps[0].wrapped_string)
            self.add_entry('_newest_timestamp', t[-1].timestamps[0].wrapped_string)

    def get_first_value(self, 
        keyname, 
        as_int=False,
        use_timestamp=False,
        return_type=False):

        if keyname in self.entries_dict:
            entries = self.entries_dict[keyname.lower()]

        else:
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
                    
        if len(entries) and not entries[0].value:
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

        return entries[0].value if len(entries) else []

    def get_values(self, 
        keyname,
        use_timestamp=False,
        lower=False):

        values = []
        keyname = keyname.lower()
        entries = self.get_entries(keyname)

        if use_timestamp:
            values = [e.timestamps for e in entries]
        else:
            values = [e.value for e in entries]        
        if lower:
            return [v.lower() if isinstance(v, str) else v for v in values]
        return values
    
    def get_keys(self, exclude=[]):
        return [k for k in self.entries_dict.keys() if k not in exclude]

    def get_entries(self, keyname):
        keyname = keyname.lower()
        return self.entries_dict[keyname] if keyname in self.entries_dict else []
    
    def all_entries(self):
        all_entries = []
        for k in self.entries_dict:
            all_entries.extend(self.entries_dict[k])
        return all_entries

    def get_matching_entries(self, keyname, value):
        keyname = keyname.lower() 
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
        keyname = keyname.lower()
        entries = self.get_entries(keyname)
        if entries and entries[0].timestamps:
            return entries[0].timestamps[0].datetime
        return default_date
      
    def clear_from_source(self, source_node_id):
        for k in self.entries_dict:
            for entry in self.entries_dict[k]:
                if entry.from_node == source_node_id:
                    self.entries_dict[k].remove(entry)
    
    def convert_hash_keys(self):
        if '#' in self.entries_dict:
            for entry in self.get_entries('#'):
                entry.keyname = self.project.settings['hash_key']
            self.entries_dict.setdefault(self.project.settings['hash_key'], [])                
            self.entries_dict[self.project.settings['hash_key']].extend(self.entries_dict['#'])
            del self.entries_dict['#']

    def get_oldest_timestamp(self):

        if self.get_entries('_oldest_timestamp'):
            return self.get_entries('_oldest_timestamp')[0].timestamps[0]
        all_timestamps = []
        for entry in self.all_entries():
            all_timestamps.extend(entry.timestamps)
        all_timestamps = sorted(all_timestamps, reverse=True, key=lambda ts: ts.datetime)
        if all_timestamps:
            return all_timestamps[0]

    def convert_node_links(self):
        for entry in self.all_entries():
            if not entry.is_node:
                m = syntax.node_link_or_pointer_c.search(entry.value)
                if m:
                    node_id = m.group(2)
                    if node_id in self.project.nodes:
                        entry.value = self.project.nodes[node_id]
                        entry.is_node = True
                        # timestamp, if any, will remain

    def log(self):
        for entry in self.all_entries():
            entry.log()

class MetadataEntry:  # container for a single metadata entry
    def __init__(self, 
        keyname, 
        contents, 
        is_node=False,
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
        self.is_node = is_node
        if is_node:
            self.value = contents
        else:
            self._parse_values(contents)
        
    def log(self):
        print('key: %s' % self.keyname)
        print(self.value)
        print('from_node: %s' % self.from_node)
        print('recursive: %s' % self.recursive)
        print(self.timestamps)
        print('is node', self.is_node)
        print('-------------------------')
        
    def _parse_values(self, contents):
        for ts in syntax.timestamp_c.finditer(contents):
            dt_string = ts.group(0).strip()
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

    def value_as_string(self):
        if self.is_node:
            return ''.join([
                syntax.link_opening_wrapper,
                self.value.title,
                syntax.link_closing_wrapper ])
        return self.value