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
    from .node import UrtextNode
    from .utils import force_list
else:
    from urtext.node import UrtextNode
    from urtext.utils import force_list

def _compile(self):
    
    self._add_all_sub_tags()
    for dynamic_definition in self.dynamic_defs():
        if dynamic_definition.target_id in self.nodes:
            self.nodes[dynamic_definition.target_id].dynamic = True

    for dynamic_definition in self.dynamic_defs(): 
        self._process_dynamic_def(dynamic_definition)

    self._add_all_sub_tags()

def _compile_file(self, filename):
    modified = False
    for node_id in self.files[filename].nodes:
        for dd in self.dynamic_defs(target=node_id):
            output = self._process_dynamic_def(dd)
            if output: # omit 700 phase
                if self._write_dynamic_def_output(dd, output):
                    modified = filename
    return modified

def _process_dynamic_def(self, dynamic_definition):
            
    if dynamic_definition.target_id == None: 
        # (export temporarily disabled)
        print('Found NoneType target in '+dynamic_definition.source_id)
        return

    if dynamic_definition.target_id == None and not dynamic_definition.target_file:
        return
        
    if dynamic_definition.target_id not in self.nodes:
        return self._log_item(None, 'Dynamic node definition in >' + dynamic_definition.source_id +
                      ' points to nonexistent node >' + dynamic_definition.target_id)
        
    output = dynamic_definition.process_output()    
    if not dynamic_definition.returns_text:
        return

    return self._build_final_output(dynamic_definition, output) 

def _write_dynamic_def_output(self, dynamic_definition, final_output):

    changed_file = None    
    if dynamic_definition.target_id and dynamic_definition.target_id in self.nodes:
        changed_file = self._set_node_contents(dynamic_definition.target_id, final_output) 
        if changed_file:
            self.nodes[dynamic_definition.target_id].dynamic = True

            # Dynamic nodes have blank title by default. Title can be set by header or title key.
            if not self.nodes[dynamic_definition.target_id].metadata.get_first_value('title'):
                self.nodes[dynamic_definition.target_id].title = ''
    
    if dynamic_definition.target_file:
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
        dynamic_definition.preserve_title_if_present(),
        contents,
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

compile_functions = [
    _compile, 
    _build_final_output, 
    _process_dynamic_def, 
    _write_dynamic_def_output,
    _compile_file ]
