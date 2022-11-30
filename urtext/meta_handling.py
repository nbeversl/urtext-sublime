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

"""
Metadata
"""
import os

if os.path.exists(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'sublime.txt')):
    from .node import UrtextNode
    from .metadata import MetadataEntry
    from .syntax import metadata_entry
else:
    from urtext.node import UrtextNode
    from urtext.metadata import MetadataEntry
    from urtext.syntax import metadata_entry

def tag_other_node(self, node_id, open_files=[], metadata={}):
    return self.execute(
        self._tag_other_node, 
        node_id, 
        metadata=metadata, 
        open_files=open_files)
        
def _tag_other_node(self, node_id, metadata={}, open_files=[]):
    """adds a metadata tag to a node programmatically"""

    if metadata == {}:
        if len(self.settings['tag_other']) < 2:
            return None
        timestamp = self.timestamp()
        metadata = { self.settings['tag_other'][0] : self.settings['tag_other'][1] + ' ' + timestamp}
    
    territory = self.nodes[node_id].ranges
    metadata_contents = UrtextNode.build_metadata(metadata)

    filename = self.nodes[node_id].filename

    full_file_contents = self.files[filename]._get_file_contents()
    tag_position = territory[-1][1]

    separator = '\n'
    if self.nodes[node_id].compact:
        separator = ' '

    new_contents = ''.join([
        full_file_contents[:tag_position],
        separator,
        metadata_contents,
        separator,
        full_file_contents[tag_position:]])
    self.files[filename]._set_file_contents(new_contents)
    s = self.on_modified(filename)
    return s

def consolidate_metadata(self, node_id, one_line=False):

    if node_id not in self.nodes:
        print('Node ID '+node_id+' not in project.')
        return None

    consolidated_metadata = self.nodes[node_id].consolidate_metadata(
        one_line=one_line)

    filename = self.nodes[node_id].filename
    file_contents = self.files[filename]._get_file_contents()
    length = len(file_contents)
    ranges = self.nodes[node_id].ranges

    for single_range in ranges:

        for section in metadata_entry.finditer(file_contents[single_range[0]:single_range[1]]):
            start = section.start() + single_range[0]
            end = start + len(section.group())
            first_splice = file_contents[:start]
            second_splice = file_contents[end:]
            file_contents = first_splice
            file_contents += second_splice
            self._adjust_ranges(filename, start, len(section.group()))

    new_file_contents = file_contents[0:ranges[-1][1]]
    new_file_contents += '\n'+consolidated_metadata
    new_file_contents += file_contents[ranges[-1][1]:]
    self.files[filename]._set_file_contents(new_file_contents)
    self._parse_file(filename)

            
def _add_sub_tags(self, 
    entry,
    next_node=None,
    visited_nodes=None):

    
    if visited_nodes == None:
        visited_nodes = []
    if next_node:
        source_tree_node = next_node
    else:
        source_tree_node = self.nodes[entry.from_node].tree_node
    if source_tree_node.name.replace('ALIAS','') not in self.nodes:
        return

    for child in self.nodes[source_tree_node.name.replace('ALIAS','')].tree_node.children:
        
        uid = source_tree_node.name + child.name
        if uid in visited_nodes:
            continue
        node_to_tag = child.name.replace('ALIAS','')
        if node_to_tag not in self.nodes:
            visited_nodes.append(uid)
            continue
        if uid not in visited_nodes and not self.nodes[node_to_tag].dynamic:
            self.nodes[node_to_tag].metadata.add_entry(
                entry.keyname, 
                entry.value, 
                from_node=entry.from_node, 
                recursive=entry.recursive)
            if node_to_tag not in self.nodes[entry.from_node].target_nodes:
                self.nodes[entry.from_node].target_nodes.append(node_to_tag)
        
        visited_nodes.append(uid)        
        
        if entry.recursive:
            self._add_sub_tags(
                entry,
                next_node=self.nodes[node_to_tag].tree_node, 
                visited_nodes=visited_nodes)

def _remove_sub_tags(self, source_id):
    for target_id in self.nodes[source_id].target_nodes:
         if target_id in self.nodes:
             self.nodes[target_id].metadata.clear_from_source(source_id)       

def _reassign_sub_tags(self, target_id):
 
    for source_id in self.nodes:
        if target_id in self.nodes[source_id].target_nodes:
            for e in self.nodes[source_id].metadata.dynamic_entries:               
                self._add_sub_tags( self.nodes[source_id].tree_node, self.nodes[target_id].tree_node, e)    

metadata_functions = [ 
    _add_sub_tags,  
    _reassign_sub_tags, 
    _tag_other_node, 
    _remove_sub_tags, 
    consolidate_metadata, 
    tag_other_node]
