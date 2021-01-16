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
import json
from .metadata import NodeMetadata
from .dynamic import UrtextDynamicDefinition

from anytree.exporter import JsonExporter

import re
import datetime
import logging
import pytz
from anytree import Node, PreOrderIter

dynamic_definition_regex = re.compile('(?:\[\[)([^\]]*?)(?:\]\])', re.DOTALL)
subnode_regexp = re.compile(r'(?<!\\){(?!.*(?<!\\){)(?:(?!}).)*}', re.DOTALL)
dynamic_def_regexp = re.compile(r'\[\[[^\]]*?\]\]', re.DOTALL)
default_date = pytz.timezone('UTC').localize(datetime.datetime(1970,2,1))
node_link_regex = r'>{1,2}[0-9,a-z]{3}\b'
timestamp_match = re.compile('(?:<)([^-/<\s`][^=<]*?)(?:>)', flags=re.DOTALL)
inline_meta = re.compile('\*{0,2}\w+\:\:([^\n};]+;?(?=>:})?)?', flags=re.DOTALL)
embedded_syntax = re.compile('%%-[^E][A-Z-]*.*?%%-END-[A-Z-]*', flags=re.DOTALL)

class UrtextNode:
    """ Urtext Node object"""
    def __init__(self, 
        filename, 
        contents,
        settings=None,
        root=False, 
        compact=False):

        self.filename = os.path.basename(filename)
        self.project_path = os.path.dirname(filename)
        self.project = None
        self.position = 0
        self.ranges = [[0, 0]]
        self.tree = None
        self.is_tree = False
        self.export_points = {}
        self.dynamic = False
        self.id = None
        self.links_from = []
        self.root_node = root
        self.tz = pytz.timezone('UTC')
        self.date = default_date # default, modified by the project
        self.prefix = None
        self.project_settings = False
        self.dynamic_definitions = {}
        self.compact = compact
        self.index = 10
        self.parent_project = None
        self.last_accessed = 0
        self.trailing_node_id = False
        self.dynamic_definitions = []
        self.blank = False
        self.title = None
        self.hashed_contents = hash(contents)

        stripped_contents = self.strip_dynamic_definitions(contents)
        self.metadata = NodeMetadata(self, stripped_contents, settings=settings)

        stripped_contents = self.strip_metadata(contents=stripped_contents)
        stripped_contents = self.strip_embedded_syntaxes(contents=stripped_contents)
        
        if stripped_contents.strip() == '':
            self.blank = True
            
        self.title = self.set_title(stripped_contents)
       
        if self.metadata.get_first_value('id'):
            node_id = self.metadata.get_first_value('id')
            node_id = node_id.lower().strip()
            if re.match(r'^[a-z0-9]{3}$', node_id):
                self.id = node_id
        else:
            contents = self.strip_wrappers(contents)
            r = re.match('\s[a-z0-9]{3}', contents[-4:])
            if r:
                self.id = contents[-3:]
                self.trailing_node_id = True
                self.metadata.add_meta_entry('id',[self.id],position=len(contents)-3)

        title_value = self.metadata.get_first_value('title')
        if title_value and title_value == 'project_settings':
            self.project_settings = True

        self.parent = None
        self.index = self.assign_as_int(
                self.metadata.get_first_value('index'),
                self.index)

        # create tree node
        self.reset_node()

        # parse dynamic definitions
        for possible_def in ['[['+section for section in contents.split('[[') ]:
            match = re.match(dynamic_definition_regex, possible_def)        
            if match:
                match = match.group(0).strip('[[').strip(']]')
                dynamic_definition = UrtextDynamicDefinition(match)
                dynamic_definition.source_id = self.id
                self.dynamic_definitions.append(dynamic_definition)

        # parse back and forward links
        self.get_links(contents=self.strip_metadata(contents=stripped_contents))
    

    def default_sort(self):
        r = str(self.date.timestamp()) + self.title
        return r

    def start_position(self):
        return self.ranges[0][0]

    def reset_node(self):
        self.tree_node = Node(self.id)
    
    def get_date(self, format_string=''):
        return self.date.strftime(format_string)

    def contents(self):
   
        with open(os.path.join(self.project_path, self.filename),
                  'r',
                  encoding='utf-8') as theFile:
            file_contents = theFile.read()
        node_contents = []
        for segment in self.ranges:
            this_range = file_contents[segment[0]:segment[1]]
            if this_range and this_range[0] in ['}','{']:
                this_range = this_range[1:]
            if this_range and this_range[-1] in ['}','{']:
                this_range = this_range[:-1]
            node_contents.append(this_range)
        node_contents = ''.join(node_contents)
        node_contents = self.strip_wrappers(node_contents)
        node_contents = self.strip_embedded_syntaxes(contents=node_contents)
        return node_contents

    def strip_wrappers(self, contents, outside_only=False):
        if contents and contents[0] in ['}','{']:
            contents = contents[1:]
        if contents and contents[-1] in ['}','{']:
            contents = contents[:-1]
        if not outside_only:
            contents = contents.replace('{','')
            contents = contents.replace('}','')
        if self.compact: # don't include the compact marker
             contents = contents.lstrip().replace('^','',1)        
        return contents

    @classmethod
    def strip_metadata(self, contents=''):
        if contents == '':
            return contents

        stripped_contents = inline_meta.sub('', contents )
        stripped_contents = timestamp_match.sub('',  stripped_contents)

        # TODO: integrate this with checking for self.trailing_node_id
        if re.match('\s[a-z0-9]{3}', stripped_contents[-4:]):
            stripped_contents = stripped_contents[:-3]

        return stripped_contents

    @classmethod
    def strip_embedded_syntaxes(self, contents=None):
        if contents == None:
            #contents = self.contents
            contents = self.contents()
        stripped_contents = contents

        for e in embedded_syntax.findall(stripped_contents):
            stripped_contents = stripped_contents.replace(e,'')
        return stripped_contents

    @classmethod
    def strip_inline_nodes(self, contents=''):
        if contents == '':
            #contents = self.contents
            contents = self.contents()
        
        stripped_contents = contents
        while subnode_regexp.search(stripped_contents):
            for inline_node in subnode_regexp.findall(stripped_contents):
                stripped_contents = stripped_contents.replace(inline_node, '')
        return stripped_contents

    @classmethod
    def strip_dynamic_definitions(self, contents=''):
        if not contents:
            return contents
             
        stripped_contents = contents
        while dynamic_def_regexp.search(stripped_contents):
            for dynamic_definition in dynamic_def_regexp.findall(
                    stripped_contents):
                stripped_contents = stripped_contents.replace(
                    dynamic_definition, '')
        return stripped_contents

    def content_only(self, contents=None):
        if contents == None:
            #contents = self.contents
            contents = self.contents()
        contents = self.strip_metadata(contents=contents)
        contents = self.strip_dynamic_definitions(contents=contents)
        contents = self.strip_embedded_syntaxes(contents=contents)
        if self.trailing_node_id:
            contents = contents[:-3]
        return contents
    
    def get_links(self, contents=None):
        if contents == None:
            contents = self.contents_only()
        nodes = re.findall(node_link_regex, contents)  # link RegEx
        for node in nodes:
            self.links_from.append(node[-3:])

    @classmethod
    def strip_contents(self, contents):
        contents = self.strip_metadata(contents=contents)
        contents = self.strip_dynamic_definitions(contents=contents)
        return contents

    def set_index(self, new_index):
        self.index = new_index

    def set_title(self, contents):

        title_value = self.metadata.get_first_value('title')
        if title_value: 
            return title_value
        #
        # otherwise, title is the first non white-space line
        #
        stripped_contents_lines = self.strip_metadata(contents=contents).strip().split('\n')
        index = 0
        last_line = len(stripped_contents_lines) - 1
        while stripped_contents_lines[index].strip() in ['','%']:
            if index == last_line:
                return '(untitled)'
            index += 1

        first_line = stripped_contents_lines[index][:100].replace('{','').replace('}', '')
        first_line = re.sub('>{1,2}[0-9,-z]{3}', '', first_line, re.DOTALL)
    
        first_line = first_line.replace('┌──','')
        first_line = first_line.replace('|','') # pipe character cannot be in node names
       
        # make conditional?
        if '^' in first_line:
            first_line = re.sub(r'^[\s]*\^','',first_line)           # compact node opening wrapper
        return first_line.strip().strip('\n').strip()

    def get_ID(self):
        if len(self.metadata.get_first_value('ID')): 
            return self.metadata.get_first_value('ID')
        return self.id

    def log(self):
        logging.info(self.id)
        logging.info(self.index)
        logging.info(self.filename)
        logging.info(self.metadata.log())

    def consolidate_metadata(self, one_line=True, separator='::'):
        
        keynames = {}
        for entry in self.metadata._entries:
            if entry.keyname not in keynames:
                keynames[entry.keyname] = []
            timestamp = ''
            if entry.dt_string:
                timestamp = '<'+entry.dt_string+'>'
            if not entry.values:
                keynames[entry.keyname].append(timestamp)
            for value in entry.values:
                keynames[entry.keyname].append(str(value)+timestamp)

        return self.build_metadata(keynames, one_line=one_line, separator=separator)

    @classmethod
    def build_metadata(self, 
        metadata, 
        one_line=False, 
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
                new_metadata += ' | '.join(metadata[keyname])
            else:
                new_metadata += metadata[keyname]
            new_metadata += line_separator

        return new_metadata.strip()

    def get_all_meta_keynames(self):
        return self.metadata._entries.keys()

    def get_region(self, region):
        region = self.ranges[region]
        with open(os.path.join(self.project_path, self.filename),
                  'r',
                  encoding='utf-8') as theFile:
            file_contents = theFile.read()
        region_contents = file_contents[region[0]: region[1]]
        return region_contents

    def set_region(self, region, contents):
        with open(os.path.join(self.project_path, self.filename),
                  'r',
                  encoding='utf-8') as theFile:
            file_contents = theFile.read()

        region = self.ranges[region]
        new_contents = file_contents[:region[0]] + contents +  file_contents[region[1]:]
        if new_contents == file_contents:
            return None
        with open(os.path.join(self.project_path, self.filename),
                  'w',
                  encoding='utf-8') as theFile:
            theFile.write(new_contents)

    def set_content(self, contents, preserve_metadata=False, bypass_check=False):

        with open(os.path.join(self.project_path, self.filename),
                  'r',
                  encoding='utf-8') as theFile:
            file_contents = theFile.read()
            
        # if preserve_metadata:
        #     contents += self.consolidate_metadata()

        start_range = self.ranges[0][0]
        end_range = self.ranges[-1][1]

        new_file_contents = ''.join([
            file_contents[0:start_range],
            contents,
            file_contents[end_range:]]) 
        
        with open(os.path.join(self.project_path, self.filename),
                  'w',
                  encoding='utf-8') as theFile:
            theFile.write(new_file_contents)

        return True

    def assign_as_int(self, value, default):
        try:
            number = int(value)
            return number
        except ValueError:
            return default

