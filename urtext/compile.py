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
    from .node import UrtextNode
else:
    from urtext.node import UrtextNode

def _compile(self):
    
    for dynamic_definition in self.dynamic_defs():
        if dynamic_definition.target_id in self.nodes:
            self.nodes[dynamic_definition.target_id].dynamic = True

    for dynamic_definition in self.dynamic_defs(): 
        self._process_dynamic_def(dynamic_definition)

def _compile_file(self, filename): 
    modified = False
    filename = os.path.basename(filename)
    if filename in self.files:
        for node_id in self.files[filename].nodes:
            for dd in self.dynamic_defs(target=node_id):
                if self._process_dynamic_def(dd) and not modified:
                    modified = filename
    else:
        print('DEBUGGING: '+filename +' not found in project')
    return modified

def _process_dynamic_def(self, dynamic_definition):

    # points = {} # Future
    new_node_contents = []
    if not dynamic_definition.target_id and not dynamic_definition.target_file:
        return
        
    if dynamic_definition.target_id and dynamic_definition.target_id not in self.nodes:
        return self._log_item(None, 'Dynamic node definition in >' + dynamic_definition.source_id +
                      ' points to nonexistent node >' + dynamic_definition.target_id)

    output = dynamic_definition.process_output()    

    #TODO this should not be necessary, but:
    if not isinstance(output, str):
        return

    final_output = self._build_final_output(dynamic_definition, output) 

    if dynamic_definition.target_id and dynamic_definition.target_id in self.nodes:
        changed_file = self._set_node_contents(dynamic_definition.target_id, final_output)  
        if changed_file:
            self.nodes[dynamic_definition.target_id].dynamic = True
        
            # Dynamic nodes have blank title by default. Title can be set by header or title key.
            if not self.nodes[dynamic_definition.target_id].metadata.get_first_value('title'):
                self.nodes[dynamic_definition.target_id].title = ''
    if dynamic_definition.target_file:
        final_output = strip_source_information(final_output)
        self.exports[dynamic_definition.target_file] = dynamic_definition
        with open(os.path.join(self.path, dynamic_definition.target_file), 'w', encoding='utf-8' ) as f:
            f.write(final_output)
        changed_file = dynamic_definition.target_file

    return changed_file


def _build_final_output(self, dynamic_definition, contents):

    metadata_values = {}
    
    built_metadata = UrtextNode.build_metadata(
        metadata_values, 
        one_line = not dynamic_definition.multiline_meta)

    final_contents = ''.join([
        ' ', ## TODO: Make leading space an option.
        contents,
        '((>'+dynamic_definition.source_id +':'+str(dynamic_definition.location),
        ')) ',
        built_metadata,
        ])
    if dynamic_definition.spaces:
        final_contents = indent(final_contents, dynamic_definition.spaces)

    return final_contents

def indent(contents, spaces=4):
  
    content_lines = contents.split('\n')
    content_lines[0] = content_lines[0].strip()
    for index, line in enumerate(content_lines):
        if line.strip() != '':
            content_lines[index] = '\t' * spaces + line
    return '\n'+'\n'.join(content_lines)

def strip_source_information(string):
    source_info = re.compile(r'\(\(>[0-9,a-z]{3}\:\d+\)\)')
    for s in source_info.findall(string):
        string = string.replace(s,'')
    return string

compile_functions = [_compile, _build_final_output, _process_dynamic_def, _compile_file ]
