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
import logging

if os.path.exists(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'sublime.txt')):
    from Urtext.anytree import Node, PreOrderIter
    from .metadata import MetadataEntry
    from .metadata import NodeMetadata
    from Urtext.anytree.exporter import JsonExporter
    from .dynamic import UrtextDynamicDefinition
    from .utils import strip_backtick_escape
    import Urtext.urtext.syntax as syntax

else:
    from anytree import Node, PreOrderIter
    from urtext.metadata import MetadataEntry
    from urtext.metadata import NodeMetadata
    from anytree.exporter import JsonExporter
    from urtext.dynamic import UrtextDynamicDefinition
    from urtext.utils import strip_backtick_escape
    import urtext.syntax as syntax

class UrtextNode:

    urtext_metadata = NodeMetadata

    def __init__(self, 
        filename, 
        contents,
        project,
        root=False,
        compact=False):

        self.filename = os.path.basename(filename)
        self.project = project
        self.position = 0
        self.ranges = [[0, 0]]
        self.tree = None
        self.is_tree = False
        self.export_points = {}
        self.dynamic = False
        self.id = None
        self.links = []
        self.root_node = root
        self.compact = compact
        self.contains_project_settings = False
        self.parent_project = None
        self.dynamic_definitions = []
        self.target_nodes = []
        self.blank = False
        self.title = ''
        self.errors = False
        self.display_meta = ''
        self.parent = None
        self.first_line_title = False
        self.title_from_marker = False
    
        contents = self.parse_dynamic_definitions(contents, self.dynamic_definitions)
        contents = strip_dynamic_definitions(contents)
        contents = strip_wrappers(contents)
        contents = strip_errors(contents)
        contents = strip_embedded_syntaxes(contents)
        contents = strip_backtick_escape(contents)
            
        self.metadata = self.urtext_metadata(self, self.project)        
        contents = self.metadata.parse_contents(contents)
        if not contents:
            self.blank = True 
    
        self.title = self.set_title(contents)  
        self.content_only_text = contents
        if self.title == 'project_settings':
            self.contains_project_settings = True

        self.id = self.title
        self.tree_node = Node(self.id)
        for d in self.dynamic_definitions:
            d.source_id = self.id

        self.get_links(contents=contents)

    def start_position(self):
        return self.ranges[0][0]
    
    def get_date(self, date_keyword):
        return self.metadata.get_date(date_keyword)

    def contents(self, 
        preserve_length=False,
        strip_first_line_title=False,
        do_strip_embedded_syntaxes=True):
   
        file_contents = self.get_file_contents()
        node_contents = []
        for segment in self.ranges:
            this_range = file_contents[segment[0]:segment[1]]
            if this_range and this_range[0] in ['}','{']:
                this_range = this_range[1:]
            if this_range and this_range[-1] in ['}','{']:
                this_range = this_range[:-1]
            node_contents.append(this_range)
        node_contents = ''.join(node_contents)
        node_contents = strip_wrappers(node_contents)
        if do_strip_embedded_syntaxes:
            node_contents = strip_embedded_syntaxes(
                node_contents,
                preserve_length=preserve_length)
        if strip_first_line_title:
            node_contents = self.strip_first_line_title(node_contents)
        return node_contents

    def date(self):
        return self.metadata.get_date(self.project.settings['node_date_keyname'])

    def get_title(self):
        if not self.title:
            return '(untitled)'
        if self.project:
            return self.title

    def strip_inline_nodes(self, contents='', preserve_length=False):
        r = ' ' if preserve_length else ''
        if contents == '':
            contents = self.contents()
        
        stripped_contents = contents
        for inline_node in syntax.subnode_regexp.finditer(stripped_contents):
            stripped_contents = stripped_contents.replace(inline_node.group(), r * len(inline_node.group()))
        return stripped_contents

    def get_links(self, contents=None):
 
        if contents == None:
            contents = self.content_only()
        nodes = syntax.node_link_c.findall(contents)  # link RegEx
        for node in nodes:
            self.links.append(node[1].strip())

    def content_only(self, 
        contents=None, 
        preserve_length=False):
        return self.content_only_text


        if contents == None:
            contents = self.contents(preserve_length=preserve_length)
        return strip_contents(contents, preserve_length=preserve_length)

    def set_title(self, contents):

        """
        - title metadata key overrides any _ marker.
        - Then the first _ marker overrides any subsequent one.
            - If it is on the first line, we need to remember this for dynamic nodes.
        - it nothing else found, it is the first non-blank line
        """
        t = self.metadata.get_first_value('title')
        if t:
            return t

        first_non_blank_line = None
        contents_lines = contents.strip().split('\n')       
        for line in contents_lines:
            first_non_blank_line = line.strip()
            if first_non_blank_line:
                break

        title = syntax.node_title_c.search(contents)
        if title:
            title = title.group()
            self.title_from_marker = True
            if title in first_non_blank_line:
                self.first_line_title = True 
            title = title.strip('_').strip()         
        else:
            if first_non_blank_line:
                title = first_non_blank_line.strip()
                self.first_line_title = True
            else:
                title = '(untitled)'

        if len(title) > 255:
            title = title[:255]
        title = sanitize_escape(title)
        self.metadata.add_entry('title', title)
        return title
   
    def log(self):
        logging.info(self.id)
        logging.info(self.filename)
        logging.info(self.metadata.log())

    def consolidate_metadata(self, one_line=True, separator='::'):
        
        keynames = {}
        for entry in self.metadata.all_entries():
            if entry.keyname in [
                '_newest_timestamp',
                '_oldest_timestamp', 
                'inline_timestamp']:
                continue
            if entry.keyname not in keynames:
                keynames[entry.keyname] = []
            timestamps = ''
            if entry.timestamps:
                timestamps = ' '.join(['<'+t.string+'>' for t in entry.timestamps])
            if not entry.value:
                keynames[entry.keyname].append(timestamps)
            else:
                keynames[entry.keyname].append(str(entry.value)+' '+timestamps)

        return self.build_metadata(keynames, one_line=one_line, separator=separator)

    def rewrite_title(self, title_suffix):

        # check for metadata
        t = self.metadata.get_first_value('title')
        new_title = t + title_suffix

        file_contents = self.get_file_contents()
        
        if t:
            for r in self.ranges:
                tag = file_contents[r[0]:r[1]+1].find('title::'+t)
                if tag > -1:
                    print('FOUND TITLE TAG')
                    new_file_contents = file_contents[:r[0]+tag + len('title::'+t)]
                    new_file_contents += new_title
                    new_file_contents += file_contents[r[0]+tag + len('title::'+t):]
                    self.set_file_contents(new_file_contents)
                    self.project._adjust_ranges(
                        self.filename, 
                        r[0]+tag + len('title::'+t),
                        len(new_title) -len(t) * -1)
                    self.title = new_title
                    return
                else:
                    title_location = file_contents[r[0]:r[1]+1].find(t + ' _')
                    if title_location < 0:
                        title_location = file_contents[r[0]:r[1]+1].find(t)
                    if title_location < 0:
                        continue
                    print('FOUND TITLE AT', title_location)
                    new_title = new_title + ' _'
                    new_file_contents = file_contents[:r[0]+title_location + len(new_title)]
                    new_file_contents += new_title
                    new_file_contents += file_contents[r[0]+title_location + len(new_title):]
                    self.set_file_contents(new_file_contents)
                    self.project._adjust_ranges(
                        self.filename, 
                        r[0] + title_location + len(t),
                        len(new_title) - len(t) * -1)
                    self.title = new_title
                    return   

    @classmethod
    def build_metadata(self, 
        metadata, 
        one_line=None, 
        separator='::'
        ):

        if not metadata:
            return ''

        line_separator = '\n'
        if one_line:
            line_separator = '; '
        new_metadata = ''

        for keyname in metadata:
            new_metadata += keyname + separator
            if isinstance(metadata[keyname], list):
                new_metadata += ' - '.join(metadata[keyname])
            else:
                new_metadata += str(metadata[keyname])
            new_metadata += line_separator
        return new_metadata.strip()

    def set_content(self, contents, preserve_metadata=False, bypass_check=False):
        
        file_contents = self.get_file_contents()
        start_range = self.start_position()
        end_range = self.ranges[-1][1]
        new_file_contents = ''.join([
            file_contents[0:start_range],
            contents,
            file_contents[end_range:]]) 
        
        return self.set_file_contents(new_file_contents)

    def parse_dynamic_definitions(self, contents, dynamic_definitions): 
        for d in syntax.dynamic_def_c.finditer(contents):
            param_string = d.group(0)[2:-2]
            dynamic_definitions.append(UrtextDynamicDefinition(param_string, self.project, d.start()))
        return contents

    def strip_first_line_title(self, contents):
        if self.first_line_title:
            contents = contents.replace(self.title,'',1)
        if self.title_from_marker:
            contents = contents.replace(' _','',1)
        return contents


def strip_contents(contents, 
    preserve_length=False, 
    include_backtick=True,
    reformat_and_keep_embedded_syntaxes=False,
    ):
    contents = strip_embedded_syntaxes(contents, 
        preserve_length=preserve_length, 
        include_backtick=include_backtick,
        reformat_and_keep_contents=reformat_and_keep_embedded_syntaxes)
    contents = strip_metadata(contents=contents, preserve_length=preserve_length)
    contents = strip_dynamic_definitions(contents=contents, preserve_length=preserve_length)
    contents = contents.strip().strip('{').strip()
    return contents

def strip_wrappers(contents):
        wrappers = ['{','}']
        if contents and contents[0] in wrappers:
            contents = contents[1:]
        if contents and contents[-1] in wrappers:
            contents = contents[:-1]
        
        contents = contents.replace('{','')
        contents = contents.replace('}','')
        return contents

def strip_metadata(contents, preserve_length=False):

        r = ' ' if preserve_length else ''

        for e in syntax.metadata_replacements.finditer(contents):
            contents = contents.replace(e.group(), r*len(e.group()))       
        contents = contents.replace('• ',r*2)
        return contents.strip()

def strip_dynamic_definitions(contents, preserve_length=False):

        r = ' ' if preserve_length else ''
        if not contents:
            return contents
        stripped_contents = contents
      
        for dynamic_definition in syntax.dynamic_def_c.finditer(stripped_contents):
            stripped_contents = stripped_contents.replace(dynamic_definition.group(), r*len(dynamic_definition.group()))
        return stripped_contents.strip()

#TODO refactor
def strip_embedded_syntaxes(
    stripped_contents, 
    preserve_length=False, 
    reformat_and_keep_contents=False,
    include_backtick=True):

    r = ' ' if preserve_length else ''
    if include_backtick:
        stripped_contents = strip_backtick_escape(stripped_contents)
    for e in syntax.embedded_syntax_c.findall(stripped_contents):
        if reformat_and_keep_contents:
            unwrapped_contents = e
            for opening_wrapper in syntax.embedded_syntax_open_c.findall(unwrapped_contents):
                unwrapped_contents = unwrapped_contents.replace(opening_wrapper,'`',1)   
            for closing_wrapper in syntax.embedded_syntax_close_c.findall(unwrapped_contents):
                unwrapped_contents = unwrapped_contents.replace(closing_wrapper,'`',1)
            unwrapped_contents = unwrapped_contents.strip()
            unwrapped_contents = unwrapped_contents.split('\n')
            unwrapped_contents = [line.strip() for line in unwrapped_contents if line.strip() != '']
            unwrapped_contents = '\t\t\n'.join(unwrapped_contents)
            stripped_contents = stripped_contents.replace(e, unwrapped_contents)
        else:
            stripped_contents = stripped_contents.replace(e,r*len(e))

    return stripped_contents

def strip_errors(contents):
    return re.sub('<!!.*?!!>', '', contents, flags=re.DOTALL)

def sanitize_escape(string):
    if string.count('`') == 1:
        return string.replace('`','')
    return string
