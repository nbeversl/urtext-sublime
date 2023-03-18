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
if os.path.exists(os.path.join(os.path.dirname(os.path.realpath(__file__)), '../sublime.txt')):
    from Urtext.urtext.dynamic_output import DynamicOutput
    from Urtext.anytree import Node, PreOrderIter, RenderTree
    from Urtext.urtext.timestamp import UrtextTimestamp, default_date
    from Urtext.urtext.directive import UrtextDirective
else:
    from urtext.directive import UrtextDirective
    from urtext.dynamic_output import DynamicOutput
    from anytree import Node, PreOrderIter, RenderTree
    from urtext.timestamp import UrtextTimestamp, default_date
    from urtext.directive import UrtextDirective

class Collect (UrtextDirective):

    name = ["COLLECT"]
    phase = 300

    """ 
    generates a collection of context-aware metadata anchors in list or tree format """

    def dynamic_output(self, nodes):
       
        m_format = self.dynamic_definition.show

        keys = {}
        
        for entry in self.params:

            k, v, operator = entry
            if operator == '!=' and k in keys:
                keys[k].remove(v)
                continue

            if k =='*':
                for k in self.project.get_all_keys():
                    keys[k] = [v.lower()]
                
            else:
                keys[k] = [v.lower()]

        found_stuff = []

        for node in nodes:
           
            for k in keys:

                use_timestamp = k in self.project.settings['use_timestamp']

                for v in keys[k]:
                    
                    if v == '*':
                        entries = node.metadata.get_entries(k)
                    else:
                        entries = node.metadata.get_matching_entries(k, v)

                    for entry in entries:

                         found_item = {}

                         if v == '*':

                            if use_timestamp:
                                value = entry.timestamps[0].datetime
                            else:
                                value = entry.value

                         else:
                            if use_timestamp and entry.timestamps[0].datetime == v:
                                value =entry.timestamps[0].datetime
                            else:
                                value = entry.value

                         found_item['node_id'] = node.id
                         found_item['title'] = node.title
                         found_item['dt_string'] = entry.timestamps[0].unwrapped_string if entry.timestamps else ''

                         if use_timestamp:
                             found_item['value'] = entry.timestamps[0].unwrapped_string
                             found_item['sort_value'] = entry.timestamps[0].datetime
                       
                         else:
                             found_item['value'] = value
                             sort_value = value
                             if self.have_flags('-sort_numeric'):
                                 try:
                                    sort_value = float(value)
                                 except ValueError: 
                                    sort_value = 99999999
                             else:
                                sort_value = str(sort_value)
        
                             found_item['sort_value'] = sort_value

                         found_item['keyname'] = k
                         full_contents = node.content_only(preserve_length=True)
                        
                         context = []
                         length = 0
                         lines = full_contents.split('\n')
                         for line in lines:
                            length += len(line)
                            if entry.end_position < length:
                                break
                       
                         found_item['context'] = line.strip().replace('_',' ')

                         while '>>' in found_item['context']:
                            found_item['context'] = found_item['context'].replace('>>','>')

                         # this will be position in NODE, not FILE:
                         found_item['position'] = str(entry.position)                         
                         
                         found_stuff.append(found_item)
    
        if not found_stuff:
             return ''
        
        if '-tree' not in self.flags:

            collection = []
        
            sorted_stuff = sorted(found_stuff, 
             key=lambda x: ( x['sort_value'] ),
             reverse=self.have_flags('-sort_reverse'))

            for item in sorted_stuff:

                 next_content = DynamicOutput( m_format, self.project.settings)
                      
                 if next_content.needs_title:
                     next_content.title = item['title']

                 if next_content.needs_entry:
                    next_content.entry = item['keyname'] + ' :: ' +  str(item['value'])

                 if next_content.needs_key:
                    next_content.key = item['keyname']

                 if next_content.needs_values:
                    next_content.values = item['value']

                 if next_content.needs_link:            
                     next_content.link = '| '+item['node_id']+':'+item['position'] + '> '

                 if next_content.needs_date:
                     next_content.date = item['dt_string']

                 if next_content.needs_meta:
                      next_content.meta = self.project.nodes[item['node_id']].consolidate_metadata()

                 if next_content.needs_contents: 
                     contents = item['context']
                     while '\n\n' in contents:
                         contents = contents.replace('\n\n', '\n')
                     next_content.contents = contents

                 # for meta_key in next_content.needs_other_format_keys:
                 #     values = self.project.nodes[item['node_id']].metadata.get_values(meta_key) #, substitute_timestamp=True)
                 #     replacement = ''
                 #     if values:
                 #         replacement = ' - '.join(values)
                 #     next_content.other_format_keys[meta_key] = replacement

                 collection.extend([next_content.output()])

            return ''.join(collection)

        if '-tree' in self.flags:
            # TODO be able to pass an m_format for Dynamic Output here.

            contents = ''
            for k in sorted(keys.keys()):
                root = Node(k)
                if not contains_different_types(keys[k]):
                   keys[k] = sorted(keys[k], key=meta_value_sort_criteria)
                
                for v in keys[k]:
                    f = None
                    if isinstance(v, UrtextTimestamp):
                        t=Node(v.unwrapped_string)
                    else:
                        t = Node(v) 
                    for node in nodes:
                        for n in node.metadata.get_matching_entries(k,value):
                            f = Node(node.id + ' >' + node.id) #?
                            f.parent = t
                        if f:                        
                            t.parent = root
                for pre, _, node in RenderTree(root):
                    contents += "%s%s\n" % (pre, node.name)

            return contents

        return ''

def meta_value_sort_criteria(v):
    if isinstance(v,UrtextTimestamp):
        return v.datetime
    return v

def contains_different_types(list):
    if len(list) < 2:
        return False
    i = type(list[0])
    for y in list:
        if type(y) != i:
            return True
    return False