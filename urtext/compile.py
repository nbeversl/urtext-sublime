
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

from .export import UrtextExport
from .node import UrtextNode
from. search import UrtextSearch
from .dynamic_output import DynamicOutput
import os
import re

"""
compile method for the UrtextProject class
"""
def _compile(self, first=[]):

    self.formulate_links_to()

    for dynamic_definition in self.dynamic_nodes:
        if dynamic_definition.target_id in self.nodes:
            self.nodes[dynamic_definition.target_id].dynamic = True

    compile_first = []

    if first:
        for file in first:
            compile_first = list(set([d for d in self.dynamic_nodes if d.target_id in self.files[file].nodes]))

        for dynamic_definition in compile_first:
            self._process_dynamic_def(dynamic_definition)

    for dynamic_definition in list([d for d in self.dynamic_nodes if d not in compile_first]): 
        self._process_dynamic_def(dynamic_definition)

    self.title_completions = [(self.nodes[n].title, ''.join(['| ',self.nodes[n].title,' >',self.nodes[n].id])) for n in list(self.nodes)]
        
def _process_dynamic_def(self, dynamic_definition):

    points = {}
    new_node_contents = []

    if dynamic_definition.target_id and dynamic_definition.target_id not in self.nodes:
        self._log_item('Dynamic node definition in >' + dynamic_definition.source_id +
                      ' points to nonexistent node >' + dynamic_definition.target_id)
        return

    # Determine included and excluded nodes
    included_projects = [self]
    if dynamic_definition.all_projects:
        included_projects.extend(self.other_projects)

    if dynamic_definition.include_all:
        included_nodes = set([node_id for node_id in self.nodes])

    else: 
        included_nodes = set([])
        if dynamic_definition.include_blank:
            included_nodes = set([node_id for node_id in self.nodes if self.nodes[node_id].blank])

        for project in included_projects:
            for group in dynamic_definition.include_groups:
                included_nodes = included_nodes.union(
                    _build_group_and(
                        project, 
                        group, 
                        include_dynamic=dynamic_definition.include_dynamic)
                    )

    excluded_nodes = set([])
    if dynamic_definition.exclude_blank:
        excluded_nodes = set([node_id for node_id in self.nodes if self.nodes[node_id].blank])

    for project in included_projects:
        for group in dynamic_definition.exclude_groups:
            excluded_nodes = excluded_nodes.union(
                _build_group_and(
                    project, 
                    group,
                    #include_dynamic=dynamic_definition.include_dynamic)
                    include_dynamic=True)
                )

    included_nodes -= excluded_nodes
    # Never include a dynamic node in itself.
    
    if dynamic_definition.target_id:
        included_nodes.discard(dynamic_definition.target_id)           

    if self.settings['log_id'] in self.nodes:
        included_nodes.discard(self.settings['log_id'])
    
    included_nodes = set([self.nodes[i] for i in included_nodes])
    
    # Sort
    if dynamic_definition.sort_keyname and dynamic_definition.use_timestamp:
        sort_order = lambda node: ( node.metadata.get_date(dynamic_definition.sort_keyname[0]), node.id)

    elif dynamic_definition.sort_keyname:
        sort_order = lambda node: ( self.get_first_value(node, dynamic_definition.sort_keyname[0]), node.id)            

    else:
        sort_order = lambda node: node.id

    included_nodes = sorted(
        included_nodes,
        key=sort_order,
        reverse=dynamic_definition.sort_reverse)

    # Apply limiting after sort
    if dynamic_definition.limit and dynamic_definition.output_type not in ['-collection', '-search']:
        included_nodes = included_nodes[0:dynamic_definition.limit]
    
    if dynamic_definition.output_type == '-collection':
        new_node_contents.append(self._collection(included_nodes, self, dynamic_definition))

    if dynamic_definition.output_type == '-search':
        for term in dynamic_definition.other_params:
            search = UrtextSearch(self, term, format_string=dynamic_definition.show)
            new_node_contents.extend(search.initiate_search())

    if dynamic_definition.output_type == '-list':
        
        for targeted_node in included_nodes:
            new_node_contents.append(
                self.show_tree_from(
                    targeted_node.id, 
                    dynamic_definition, 
                    exclude=list(excluded_nodes))
                )
    
    final_output = build_final_output(dynamic_definition, ''.join(new_node_contents)) 
    if dynamic_definition.target_id and dynamic_definition.target_id in self.h_content:
        if self.h_content[dynamic_definition.target_id] == hash(final_output):
            return

    if dynamic_definition.exports and dynamic_definition.exports[0] in self.dynamic_memo:
        if self.dynamic_memo[dynamic_definition.exports[0]]['contents'] == hash(final_output):
            return

    if dynamic_definition.exports:
        self.dynamic_memo[dynamic_definition.exports[0]] = {}
        self.dynamic_memo[dynamic_definition.exports[0]]['contents'] = hash(final_output)
    
    if dynamic_definition.target_id:

        changed_file = self._set_node_contents(dynamic_definition.target_id, final_output)                    
  
        self.nodes[dynamic_definition.target_id].dynamic = True

        # Dynamic nodes have blank title by default. Title can be set by header or title key.
        if not self.nodes[dynamic_definition.target_id].metadata.get_first_value('title') and not dynamic_definition.header:
            self.nodes[dynamic_definition.target_id].title = ''

        messages_file = self._populate_messages()
  
    if dynamic_definition.exports:

        for e in dynamic_definition.exports:

            exported = UrtextExport(self) 
            exported_content = ''
            for node in included_nodes:
                node_export, points = exported.export_from(
                     node.id,
                     kind=e.output_type,
                     exclude=list(excluded_nodes),
                     as_single_file=True, # TODO should be option 
                     #clean_whitespace=True,
                     preformat=e.preformat)
                
                exported_content += '\n'+node_export

            for n in e.to_nodes:
                
                if n in self.nodes:
                    
                    metadata_values = { 
                        'ID': [ n ],
                        'def' : [ '>'+dynamic_definition.source_id ] }

                    built_metadata = UrtextNode.build_metadata(
                        metadata_values, 
                        one_line = True)
                        #not dynamic_definition.multiline_meta)

                    changed_file = self._set_node_contents(n, exported_content + built_metadata)                       
                    self.nodes[n].export_points = points           
                    self.nodes[n].dynamic = True

            for f in e.to_files:
                with open(os.path.join(self.path, f), 'w',encoding='utf-8') as f:
                    f.write(exported_content)


def build_final_output(dynamic_definition, contents):

    metadata_values = {}
    if dynamic_definition.target_id:
        metadata_values['ID'] = dynamic_definition.target_id
        metadata_values['def'] = [ '>'+dynamic_definition.source_id ] 

    built_metadata = UrtextNode.build_metadata(
        metadata_values, 
        one_line = True )
        #one_line = not dynamic_definition.multiline_meta)

    footer = ''
    if dynamic_definition.footer:
        footer = bytes(dynamic_definition.footer, "utf-8").decode("unicode_escape") + '\n'

    header = ''
    if dynamic_definition.header:
        header = bytes(dynamic_definition.header, "utf-8").decode("unicode_escape")
        if header[-1] != '\n':
            header += '\n'

    final_contents = ''.join([
        ' ', ## TODO: Make leading space an option.
        header,
        contents,
        footer,
        built_metadata,
        ' '
        ])
    if dynamic_definition.spaces:
        final_contents = indent(final_contents, dynamic_definition.spaces)

    return final_contents

def _build_group_and(project, groups, include_dynamic=False):
    
    found_sets = []
    new_group = set([])
    for pair in groups:
        key, value, operator = pair[0], pair[1], pair[2]
        new_group = set(project.get_by_meta(key, value, operator))
        found_sets.append(new_group)

    for this_set in found_sets:
        new_group = new_group.intersection(this_set)

    if not include_dynamic:
        new_group = [f for f in new_group if f in project.nodes and not project.nodes[f].dynamic]

    return new_group

def indent(contents, spaces=4):
  
    content_lines = contents.split('\n')
    content_lines[0] = content_lines[0].strip()
    for index, line in enumerate(content_lines):
        if line.strip() != '':
            content_lines[index] = '\t' * spaces + line
    return '\n'+'\n'.join(content_lines)

compile_functions = [_compile,_process_dynamic_def ]
