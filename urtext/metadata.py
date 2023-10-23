import os

if os.path.exists(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'sublime.txt')):
    from .timestamp import UrtextTimestamp, default_date
    import Urtext.urtext.syntax as syntax
    from .metadata_entry import MetadataEntry
    from .metadata_value import MetadataValue
else:
    from urtext.timestamp import UrtextTimestamp, default_date
    import urtext.syntax as syntax
    from urtext.metadata_entry import MetadataEntry
    from urtext.metadata_value import MetadataValue

SINGLE_VALUES = [
    '_oldest_timestamp',
    '_newest_timestamp',
    ]

class NodeMetadata:

    def __init__(self, 
        node,
        project):

        self.node = node
        self.entries_dict = {}
        self.project = project
   
    def parse_contents(self, full_contents):
        parsed_contents = full_contents
        remaining_contents = full_contents

        for m in syntax.metadata_entry_c.finditer(full_contents):
            keyname, contents = m.group().strip(
                syntax.metadata_end_marker).split(
                    syntax.metadata_assigner, 
                    1)
            value_list = syntax.metadata_separator_pattern_c.split(contents)
            
            tag_self=False
            tag_children=False
            tag_descendants=False
            if not syntax.metadata_tag_self_c.match(keyname[0]) and ( 
                not syntax.metadata_tag_desc_c.match(keyname[0])):
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

            value_list = [v.strip() for v in value_list]

            self.add_entry(
                keyname,
                [MetadataValue(v) for v in value_list],
                self.node,
                tag_self=tag_self,
                tag_children=tag_children,
                tag_descendants=tag_descendants,
                start_position=m.start(),
                end_position=m.start() + len(m.group().strip()))

            parsed_contents = parsed_contents.replace(
                m.group(),
                ' '*len(m.group()), 
                1)
            remaining_contents = remaining_contents.replace(
                m.group(),
                '', 
                1)

        for m in syntax.hash_meta_c.finditer(parsed_contents):
            value = syntax.hash_key_c.sub('',m.group()).strip()
            keyname = self.project.settings['hash_key']
            self.add_entry(
                keyname,
                [MetadataValue(value)], 
                self.node,
                start_position=m.start(), 
                end_position=m.start() + len(m.group()))
            parsed_contents = parsed_contents.replace(
                m.group(),
                ' '*len(m.group()),
                1)
            remaining_contents = remaining_contents.replace(
                m.group(),
                '',
                1)

        # inline timestamps:
        for m in syntax.timestamp_c.finditer(parsed_contents):
            self.add_entry(
                'inline_timestamp',
                [MetadataValue(m.group())],
                self.node,
                start_position=m.start(),
                end_position=m.start() + len(m.group()))
            parsed_contents = parsed_contents.replace(
                m.group(),
                ' '*len(m.group()),
                1)
            remaining_contents = remaining_contents.replace(
                m.group(),
                '',
                1)

        self.add_system_keys()
        return remaining_contents, parsed_contents

    def add_entry(self, 
        key,
        values,
        node,
        is_node=False,
        start_position=0,
        end_position=0,
        tag_self=True,
        from_node=None,
        tag_children=False,
        tag_descendants=False):

        key = key.lower().strip()

        e = MetadataEntry(
            key, 
            values,
            node,
            is_node=is_node,
            start_position=start_position, 
            end_position=end_position,
            from_node=from_node,
            tag_self=tag_self,
            tag_children=tag_children,
            tag_descendants=tag_descendants)

        # error catch in case the user tries to manually add one:
        # if key == 'inline_timestamp' and not e.timestamps:
        #     return False
        self.entries_dict.setdefault(key, [])
        
        if e.is_node:
            # node values must be unique for the key
            self.entries_dict[key] = [e]
        else:
            self.entries_dict[key].append(e)

    def get_keys(self, exclude=[]):
        return [k for k in self.entries_dict.keys() if k not in exclude]

    def get_entries(self, keyname, use_timestamp=True):
        keyname = keyname.lower()
        if keyname not in self.entries_dict:
            return []
        entries = [e for e in self.entries_dict[keyname] if e.tag_self]

        if use_timestamp and keyname in self.project.settings['use_timestamp']:
            timestamps = []
            for e in entries:
                timestamps.extend(e.get_timestamps())
            return timestamps
        return entries

    def entries(self):
        all_entries = []
        for k in self.entries_dict:
            all_entries.extend(self.entries_dict[k])
        return all_entries

    def add_system_keys(self):
        inline_timestamps = self.get_entries('inline_timestamp')
        if inline_timestamps:
            inline_timestamps = sorted(
                inline_timestamps,
                key=lambda t: t.datetime
                )
            self.add_entry(
                '_oldest_timestamp', 
                [MetadataValue(inline_timestamps[0].wrapped_string)],
                self.node,
                start_position=inline_timestamps[0].start_position,
                end_position=inline_timestamps[-1].end_position)
            self.add_entry(
                '_newest_timestamp',
                [MetadataValue(inline_timestamps[-1].wrapped_string)],
                self.node,
                start_position=inline_timestamps[-1].start_position,
                end_position=inline_timestamps[-1].end_position)

    def get_first_value(self, 
        keyname, 
        use_timestamp=False):
        
        keyname = keyname.lower()
        if keyname not in self.entries_dict:
            return None
        entries = self.entries_dict[keyname]

        if use_timestamp or keyname in self.project.settings['use_timestamp']:
            if keyname in SINGLE_VALUES:
                return self.entries_dict[keyname][0].meta_values[0].timestamp
            if entries[0].meta_values[0].timestamp:
                return entries[0].meta_values[0].timestamp
            return default_date

        #TODO update: when would this happen?
        if len(entries) and not entries[0].meta_values:
            return None

        return self._as_num_if_num(
            keyname,
            entries[0].meta_values[0].text)

    def get_values(self, 
        keyname,
        use_timestamp=False,
        lower=False,
        convert_nodes_to_links=False):

        values = []
        entries = self.get_entries(keyname)

        for e in entries:
            if e.is_node:
                if convert_nodes_to_links:
                    values.append(''.join([
                        syntax.link_opening_wrapper,
                        value.id,
                        syntax.link_closing_wrapper])) 
                continue
            for v in e.meta_values:
                if use_timestamp and v.timestamp:
                    values.append(v.timestamp)
                    continue
                if v.text:
                    if lower:
                        v.text = v.text.lower()
                    values.append(self._as_num_if_num(
                        keyname,
                        v))
        
        return list(set(values))

    def _as_num_if_num(self, keyname, value):
        if keyname in self.project.settings['numerical_keys']:
            try:
                return float(value)
            except:
                return None
        return value

    def get_matching_entries(self, keyname, value):
        entries = self.get_entries(keyname)
        matching_entries = []
        if entries:
            for e in entries:
                if isinstance(value, UrtextTimestamp):
                    meta_values = [v.timestamp for v in e.meta_values]
                else:
                    meta_values = [v.text for v in e.meta_values]
                for v in meta_values:
                    if v == value:
                        matching_entries.append(e)
            return matching_entries

    def get_date(self, keyname):
        """
        Returns the timestamp of the FIRST matching metadata entry with the given key.
        #TODO possibly remove
        """
        timestamp = self.get_first_value(keyname, use_timestamp=True)
        if timestamp:
            return timestamp.datetime
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

    def get_oldest_timestamp(self, use_timestamp=True):
        oldest_timestamp = self.get_first_value('_oldest_timestamp')
        if oldest_timestamp:
            return oldest_timestamp
        return None
        # all_timestamps = []
        # for entry in self.entries():
        #     all_timestamps.extend(entry.timestamps)
        # all_timestamps = sorted(all_timestamps, reverse=True, key=lambda ts: ts.datetime)
        # if all_timestamps:
        #     return all_timestamps[0]

    def convert_node_links(self):
        for entry in self.entries():
            if not entry.is_node:
                for value in entry.meta_values:
                    if not value.text:
                        continue
                    m = syntax.node_link_or_pointer_c.search(value.text)
                    if m:
                        node_id = m.group(2)
                        if node_id in self.project.nodes:
                            entry.value = self.project.nodes[node_id]
                            entry.is_node = True
                            # timestamp, if any, will remain

    def log(self):
        for entry in self.entries():
            entry.log()
