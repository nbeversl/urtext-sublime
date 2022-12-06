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
import platform
import os
import random
import time
from time import strftime
import concurrent.futures
import inspect

if os.path.exists(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'sublime.txt')):
    from ..anytree import Node, PreOrderIter, RenderTree
    from .file import UrtextFile, UrtextBuffer
    from .node import UrtextNode
    from .compile import compile_functions
    from .meta_handling import metadata_functions
    from .dynamic import UrtextDynamicDefinition
    from .timestamp import date_from_timestamp, default_date, UrtextTimestamp
    from .directive import UrtextDirective
    from .action import UrtextAction
    from .extension import UrtextExtension
    import Urtext.urtext.syntax as syntax
    from Urtext.urtext.project_settings import *
    import Urtext.urtext.directives     
    import Urtext.urtext.actions
    import Urtext.urtext.extensions
else:
    from anytree import Node, PreOrderIter, RenderTree
    from urtext.file import UrtextFile, UrtextBuffer
    from urtext.node import UrtextNode
    from urtext.compile import compile_functions
    from urtext.meta_handling import metadata_functions
    from urtext.dynamic import UrtextDynamicDefinition
    from urtext.timestamp import date_from_timestamp, default_date, UrtextTimestamp
    from urtext.directive import UrtextDirective
    from urtext.action import UrtextAction
    from urtext.extension import UrtextExtension
    from urtext.templates.templates import templates
    import urtext.syntax as syntax
    from urtext.project_settings import *
    import urtext.directives     
    import urtext.actions
    import urtext.extensions

functions = compile_functions
functions.extend(metadata_functions)

def all_subclasses(cls):
    return set(cls.__subclasses__()).union(
        [s for c in cls.__subclasses__() for s in all_subclasses(c)])

all_extensions = all_subclasses(UrtextExtension)
all_directives = all_subclasses(UrtextDirective)
all_actions = all_subclasses(UrtextAction)

def add_functions_as_methods(functions):
    def decorator(Class):
        for function in functions:
            setattr(Class, function.__name__, function)
        return Class
    return decorator

@add_functions_as_methods(functions)
class UrtextProject:
    """ Urtext project object """

    urtext_file = UrtextFile
    urtext_node = UrtextNode

    def __init__(self,
                 path,
                 file_extensions=['.txt'],
                 rename=False,
                 new_project=False,
                 run_async=True):
        
        self.is_async = run_async 
        #self.is_async = False # development
        self.time = time.time()
        self.last_compile_time = 0
        self.path = path
        self.settings = default_project_settings()
        self.nodes = {}
        self.files = {}
        self.exports = {}
        self.messages = {}
        self.navigation = []  # Stores, in order, the path of navigation
        self.nav_index = -1  # pointer to the CURRENT position in the navigation list
        self.dynamic_definitions = []
        self.dynamic_metadata_entries = []
        self.extensions = {}
        self.actions = {}
        self.duplicate_ids = {}
        self.directives = {}
        self.compiled = False
        self.project_list = None # becomes UrtextProjectList, permits "awareness" of list context
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=50)
        self.file_extensions = file_extensions
        self.title = self.path # default
        self.excluded_files = []
        self.error_files = []
        self.execute(self._initialize_project, new_project=new_project)
    
    def _initialize_project(self, 
        new_project=False):

        for c in all_extensions:
            for n in c.name:
                self.extensions[n] = c(self)

        for c in all_actions:
            for n in c.name:
                self.actions[n] = c

        for c in all_directives:
            for n in c.name:
                self.directives[n] = c

        for file in self._get_included_files():
            self._parse_file(file)

        if self.nodes == {}:
            if new_project:
                for filename in templates:
                    with open(os.path.join(self.path, filename ), 'w', encoding='utf-8') as f:
                        f.write(templates[filename]) 
                    self._parse_file(os.path.basename(filename))
            else:
                raise NoProject('No Urtext nodes in this folder.')

        elif new_project:
            print('Urtext project already exists here.')
            return None

        for node_id in self.nodes:
            self.nodes[node_id].metadata.convert_hash_keys()       
        
        self._compile()
        self.compiled = True
        self.last_compile_time = time.time() - self.time
        self.time = time.time()
        print('"'+self.title+'" compiled from '+self.path )
    
    def get_file_position(self, node_id, position): 
        if node_id in self.nodes:
            node_length = 0
            offset_position = position
            for r in self.nodes[node_id].ranges:
                range_length = r[1] - r[0]
                node_length += range_length
                if position < node_length:
                    break
                offset_position -= range_length
            file_position = r[0] + offset_position
            return file_position
        return None

    def _parse_file(self, filename):
    
        filename = os.path.basename(filename)

        if self._filter_filenames(filename) == None:
            return self._add_to_excluded_files(filename)

        new_file = self.urtext_file(os.path.join(self.path, filename), self)
        self.messages[new_file.filename] = new_file.messages
        if new_file.errors:
            self._add_to_error_files(filename)
            return -1
 
        old_node_ids = []
        if filename in self.files:
            old_node_ids = self.files[filename].get_ordered_nodes()

        self._remove_file(filename)
 
        file_should_be_dropped, should_re_parse = self._check_file_for_duplicates(new_file)
        
        if file_should_be_dropped:
            self._add_to_error_files(filename)
            return file_should_be_dropped
        
        if should_re_parse:
            return self._parse_file(filename)

        if new_file.filename in self.error_files:
            self.error_files.remove(new_file.filename)

        if old_node_ids: # (if the file was already in the project)
            new_node_ids = new_file.get_ordered_nodes()

            added_ids = []
            for node_id in new_node_ids:
                if node_id not in old_node_ids:
                    added_ids.append(node_id)

            removed_ids = []
            for node_id in old_node_ids:
                if node_id not in new_node_ids:
                    removed_ids.append(node_id)

            changed_ids = {}
            
            if len(old_node_ids) == len(new_node_ids):
                for index in range(0, len(old_node_ids)): # existing links are all we care about
                    if old_node_ids[index] == new_node_ids[index]:
                        # the id stayed the same
                        continue
                    else:
                        if new_node_ids[index] in old_node_ids:
                            # proably only the order changed.
                            # don't have to do anything
                            continue
                        else:
                            # check each new id for similarity to the old one
                            if len(added_ids) == 1:
                                # only one node id changed. simple.
                                changed_ids[old_node_ids[index]] = added_ids[0]
                            else:
                                # try to map old to new. This is the hard part
                                pass
            self._rewrite_changed_links(changed_ids)

        self.files[new_file.basename] = new_file  
        for node_id in new_file.nodes:
            self._add_node(new_file.nodes[node_id])
    
        for ext in self.extensions:
             self.extensions[ext].on_file_modified(filename)

        for node_id in new_file.nodes:
            for dd in new_file.nodes[node_id].dynamic_definitions:
                dd.source_id = node_id
                self.dynamic_definitions.append(dd)

            for entry in new_file.nodes[node_id].metadata.dynamic_entries:
                entry.from_node = node_id
                self._add_sub_tags(entry)
                self.dynamic_metadata_entries.append(entry)

    def _add_all_sub_tags(self):
        for entry in self.dynamic_metadata_entries:
            self._add_sub_tags(entry)
        
    def _rewrite_changed_links(self, changed_ids):

        old_ids = list(changed_ids.keys())
        files = list(self.files)
        for file in files:
            if file in self.files:
                for node_id in self.files[file].nodes:
                    changed_links = {}

                    if node_id == '(untitled)' or node_id not in self.nodes:
                        continue

                    for link in self.nodes[node_id].links:
                        for old_id in old_ids:
                            if old_id.startswith(link):
                                changed_links[link] = changed_ids[old_id]
                if changed_links:
                    contents = self.files[file]._get_file_contents()
                    replaced_contents = contents
                    for node_id in list(changed_ids.keys()):
                        if '| ' + node_id + ' >' in contents:
                             replaced_contents = replaced_contents.replace(
                                '| '+ node_id + ' >', 
                                '| '+ changed_ids[node_id] + ' >')
                    if replaced_contents != contents:
                        self.files[file]._set_file_contents(replaced_contents)
                        self._parse_file(file)

    def _check_file_for_duplicates(self, file_obj):

        duplicate_nodes = {}
        for node_id in file_obj.nodes:
            duplicate_filename = self._is_duplicate_id(node_id, file_obj.filename)
            if duplicate_filename:
                duplicate_nodes[node_id] = duplicate_filename

        file_should_be_dropped = False
        should_re_parse = False

        if duplicate_nodes:
            basename = os.path.basename(file_obj.filename)
            messages = []
            
            for n in duplicate_nodes:
                if n == '(untitled)':
                    if self.settings['allow_untitled_nodes'] == False:
                        messages.append('untitled node in f>'+duplicate_nodes[n]+'\n')
                        self._log_item(basename, 'Untitled node: '+ duplicate_nodes[n])
                else:
                    messages.append('>'+n + ' exists in f>'+duplicate_nodes[n]+'\n')
                    self._log_item(basename, 'Duplicate node ID(s) found: '+ ', '.join(duplicate_nodes))
                    file_should_be_dropped = True
            
        return file_should_be_dropped, should_re_parse

    def _target_id_defined(self, check_id):
        for nid in list(self.nodes):
            if nid in self.nodes and check_id in [t.target_id for t in self.nodes[nid].dynamic_definitions]:
                return nid

    def _target_file_defined(self, file):
        for nid in list(self.nodes):
            for e in self.nodes[nid].dynamic_definitions:
                for r in e.exports:
                    if file in r.to_files:
                        return nid

    """
    Parsing helpers
    """
    def _add_node(self, new_node):
        """ Adds a node to the project object """

        for definition in new_node.dynamic_definitions:
            
            if definition.target_id:
                defined = self._target_id_defined(definition.target_id)
                
                if defined and defined != new_node.id:

                    message = ''.join([ 'Node >', definition.target_id,
                                ' has duplicate definition in >' , new_node.id ,
                                  '. Keeping the definition in >',
                                  defined, '.'
                                  ])
                    self._log_item(new_node.filename, message)

                    definition = None
                       
        if len(new_node.metadata.get_values('ID')) > 1:
            message = ''.join([ 
                    'Multiple ID tags in >' , new_node.id ,': ',
                    ', '.join(new_node.metadata.get_first_value('ID')),' - using the first one found.'])
            self._log_item(new_node.filename, message)

        new_node.parent_project = self.title
        new_node.project = self
        self.nodes[new_node.id] = new_node

        if new_node.contains_project_settings:
            self._get_settings_from(new_node)            
        
    def get_source_node(self, filename, position):
        if filename not in self.files:
            return None, None
        exported_node_id = self.get_node_id_from_position(filename, position)
        points = self.nodes[exported_node_id].export_points
        if not points:
            return None, None
        node_start_point = self.nodes[exported_node_id].start_position()

        indexes = sorted(points)
        for index in range(0, len(indexes)):
            if position >= indexes[index] and position < indexes[index+1]:
                node, target_position = self.nodes[exported_node_id].export_points[indexes[index]]
                offset = position - indexes[index]
                return node, target_position+offset

    def _set_node_contents(self, node_id, contents, parse=True):
        """ 
        project-aware alias for the Node set_content() method 
        returns filename if contents has changed.
        """
        if parse and self._parse_file(self.nodes[node_id].filename) == -1:
            return
        if node_id in self.nodes:
             if self.nodes[node_id].set_content(contents, preserve_metadata=True):
                self._parse_file(self.nodes[node_id].filename)
                if node_id in self.nodes:
                    return self.nodes[node_id].filename
        return False

    def _adjust_ranges(self, filename, from_position, amount):
        """ 
        adjust the ranges of all nodes in the given file 
        a given amount, from a given position
        """
        for node_id in self.files[os.path.basename(filename)].nodes:
            number_ranges = len(self.nodes[node_id].ranges)
            for index in range(number_ranges):
                this_range = self.nodes[node_id].ranges[index]
                if from_position >= this_range[0]:
                    self.nodes[node_id].ranges[index][0] -= amount
                    self.nodes[node_id].ranges[index][1] -= amount

    """
    Removing and renaming files
    """
    def _remove_file(self, filename):
       
        if filename in self.files:
            for dd in self.dynamic_defs():
                for op in dd.operations:
                    op.on_file_removed(filename)

            for node_id in self.files[filename].nodes:    
                if node_id not in self.nodes:
                    continue
                self._remove_sub_tags(node_id)

                del self.nodes[node_id]
                self.remove_dynamic_defs(node_id)
                self.remove_dynamic_metadata_entries(node_id)
            del self.files[filename]

        if filename in self.messages:
            del self.messages[filename]

    def delete_file(self, filename, open_files=[]):
        return self.execute(self._delete_file, filename, open_files=open_files)

    def _delete_file(self, filename, open_files=[]):
        """
        Deletes a file, removes it from the project,
        and returns a future of modified files.
        """
        filename = os.path.basename(filename)
        if filename in self.files:
            for node_id in list(self.files[filename].nodes):
                while node_id in self.navigation:
                    index = self.navigation.index(node_id)
                    del self.navigation[index]
                    if self.nav_index >= index:
                        self.nav_index -= 1            
            self._remove_file(filename)
            os.remove(os.path.join(self.path, filename))
        if filename in self.error_files:
            os.remove(os.path.join(self.path, filename))
        if filename in self.messages:
            del self.messages[filename]
        if open_files:
            return self.on_modified(open_files)
        return []
    
    def _handle_renamed(self, old_filename, new_filename):
        new_filename = os.path.basename(new_filename)
        old_filename = os.path.basename(old_filename)
        if new_filename != old_filename:
            self.files[new_filename] = self.files[old_filename]
            for node_id in self.files[new_filename].nodes:
                self.nodes[node_id].filename = new_filename
                self.files[new_filename].filename = os.path.join(self.path, new_filename)
                self.nodes[node_id].full_path = os.path.join(self.path, new_filename)
            del self.files[old_filename]
            for ext in self.extensions:
                self.extensions[ext].on_file_renamed(old_filename, new_filename)
    
    """ 
    filtering files to skip 
    """
    def _filter_filenames(self, filename):
        if filename in ['history','files','.git']:
            return None            
        if filename in self.settings['exclude_files']:
            return None
        return filename
    
    def new_file_node(self, 
        date=None, 
        contents=None,
        metadata = {}, 
        one_line=None):

        contents_format = None
        if contents == None:
            contents_format = bytes(self.settings['new_file_node_format'], "utf-8").decode("unicode_escape")

        filename = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        contents, title, cursor_pos = self._new_node(
            date=date,
            contents=contents,
            contents_format=contents_format,
            metadata=metadata,
            include_timestamp=self.settings['file_node_timestamp'])
        
        filename = filename + '.txt'
        with open(os.path.join(self.path, filename), "w") as f:
            f.write(contents)  
        self._parse_file(filename)

        return { 
                'filename' : filename, 
                'id' : title,
                'cursor_pos' : cursor_pos
                }

    def new_inline_node(self, 
        date=None, 
        metadata = {}, 
        contents='',
        one_line=None,
        ):

        contents_format = None
        contents, cursor_pos = self._new_node(
            date=date,
            contents=contents,
            contents_format=contents_format,
            metadata=metadata)

        return {
            'contents' : ''.join(['{', contents, '}']),
            'cursor_pos' : cursor_pos
        }
    
    def _new_node(self, 
            date=None, 
            contents='',
            title='',
            contents_format=None,
            metadata=None,
            one_line=None,
            include_timestamp=False):

        cursor_pos = 0

        duplication_index = 2
        if title != '':
            while test_title in self.nodes:
                test_title = title + ' (' + str(duplication_index) + ')'
                duplication_index += 1

            title = test_title
            title += '\n'

        if contents_format:
            new_node_contents = contents_format.replace('$timestamp', self.timestamp(datetime.datetime.now()) )
            new_node_contents = new_node_contents.replace('$device_keyname', platform.node() )

            if '$cursor' in new_node_contents:
                new_node_contents = new_node_contents.split('$cursor')
                cursor_pos = len(new_node_contents[0])
                new_node_contents = title + ''.join(new_node_contents)
        else:
            if one_line == None:
                one_line = self.settings['always_oneline_meta']
            
            if not metadata:
                metadata = {}

            if  self.settings['device_keyname']:
                metadata[self.settings['device_keyname']] = platform.node()

            new_node_contents = contents

            if include_timestamp:
                if date == None:
                    date = datetime.datetime.now() 
                if self.settings['keyless_timestamp'] == True:
                    new_node_contents += self.timestamp(date) + ' '
                elif self.settings['node_date_keyname']:
                    metadata[self.settings['node_date_keyname']] = self.timestamp(date)

            new_node_contents += self.urtext_node.build_metadata(metadata, one_line=one_line)

        return new_node_contents, title, cursor_pos

    def add_compact_node(self,  
            contents='', 
            metadata={}):
            metadata_block = self.urtext_node.build_metadata(metadata, one_line=True)
            if metadata_block:
                metadata_block = ' ' + metadata_block
            return '• ' + contents.strip() + metadata_block

    def dynamic_defs(self, target=None, source=None):
        if target:
            return [dd for dd in self.dynamic_definitions if dd.target_id == target]
        return self.dynamic_definitions

    def remove_dynamic_defs(self, node_id):
        for dd in list(self.dynamic_definitions):
            if dd.source_id == node_id:
                self.dynamic_definitions.remove(dd)

    def remove_dynamic_metadata_entries(self, node_id):
        for entry in list(self.dynamic_metadata_entries):
            if entry.from_node == node_id:
                self.dynamic_metadata_entries.remove(entry)

    """
    Project Navigation
    """

    def nav_advance(self):
        if not self.navigation:
            return None
        
        # return if the index is already at the end
        if self.nav_index == len(self.navigation) - 1:
            print('project index is at the end.')
            return None
        
        self.nav_index += 1
        next_node = self.navigation[self.nav_index]
        self.visit_node(next_node)
        return next_node

    def nav_new(self, node_id):
        """
        Should be called from the wrapper on focus of any new file or
        node_id and before calling on_modified() or visit_file()
        """
        if node_id in self.nodes:
            # don't re-remember consecutive duplicate links
            if -1 < self.nav_index < len(self.navigation) and node_id == self.navigation[self.nav_index]:
                return     
            # add the newly opened file as the new "HEAD"
            self.nav_index += 1
            del self.navigation[self.nav_index:]
            self.navigation.append(node_id)
            self.visit_node(node_id)
               
    def nav_reverse(self):
        if not self.navigation:
            return None

        if self.nav_index == 0:
            print('project index is already at the beginning.')
            return None

        self.nav_index -= 1
        last_node = self.navigation[self.nav_index]
        self.visit_node(last_node)
        return last_node

    def nav_current(self):
        if self.navigation and self.nav_index > -1:
            return self.navigation[self.nav_index]
        alternative = self.get_home()
        if not alternative:
            alternative = self.random_node()
        return alternative

    def all_nodes(self):

        def sort(nid, return_type=False):
            return self.nodes[nid].metadata.get_first_value(
                k, 
                use_timestamp=use_timestamp,
                return_type=return_type)

        remaining_nodes = list(self.nodes)
        sorted_nodes = []
        for k in self.settings['node_browser_sort']:
            use_timestamp= k in self.settings['use_timestamp']
            as_int = k in self.settings['numerical_keys']
            k = k.lower()

            node_group = [r for r in remaining_nodes if r in self.nodes and self.nodes[r].metadata.get_first_value(k)]
            for r in node_group:
                if use_timestamp:
                    self.nodes[r].display_meta = self.timestamp(self.nodes[r].metadata.get_first_value(k, use_timestamp=use_timestamp))
                else:
                    self.nodes[r].display_meta = str(self.nodes[r].metadata.get_first_value(k))
            node_group = sorted(node_group, key=lambda nid: sort(nid, return_type=True), reverse=k in self.settings['use_timestamp'] )
            sorted_nodes.extend(node_group)
            remaining_nodes = list(set(remaining_nodes) - set(node_group))
        sorted_nodes.extend(remaining_nodes)
        return sorted_nodes

    def all_files(self):
        files=list(self.files)
        prefix = 0
        sorted_files = []
        for k in self.settings['file_index_sort']:
            k = k.lower()
            use_timestamp= True if k in self.settings['use_timestamp'] else False
            file_group = [f for f in files if self.files[f].root_nodes and self.nodes[self.files[f].root_nodes[0]].metadata.get_first_value(k, use_timestamp=use_timestamp)]
            file_group = sorted(file_group, 
                key=lambda f:  self.nodes[self.files[f].root_nodes[0]].metadata.get_first_value(k, use_timestamp=use_timestamp),
                reverse=use_timestamp)
            sorted_files.extend(file_group)
            files = list(set(files) - set(sorted_files))
        sorted_files.extend(files)
        return sorted_files

    def root_nodes(self, primary=False):
        """
        Returns the IDs of all the root (file level) nodes
        """
        root_nodes = []        
        for filename in self.files:
            if not primary:
                root_nodes.extend(self.files[filename].root_nodes)
            else:
                if not self.files[filename].root_nodes:
                    self._log_item(filename, 'No root nodes in f>'+filename)
                else:
                    root_nodes.append(self.files[filename].root_nodes[0])
        return root_nodes

    def get_node_id_from_position(self, filename, position):
        filename = os.path.basename(filename)
        if filename in self.files:
            for node_id in self.files[filename].nodes:
                for r in self.files[filename].nodes[node_id].ranges:                   
                    if position in range(r[0],r[1]+1): # +1 in case the cursor is in the last position of the node.
                        return node_id
        return None

    def get_node_id_from_position_in_buffer(self, buffer, position):
        buffer_file = UrtextBuffer(buffer, self)
        for node_id in buffer_file.nodes:
            for r in buffer_file.nodes[node_id].ranges:
                if position  >= r[0] and position < r[1]:
                    return node_id
        return None


    def get_links_to(self, to_id):
        return [i for i in self.nodes if to_id in self.nodes[i].links]
       
    def get_links_from(self, from_id):
        if from_id in self.nodes:
            return self.nodes[from_id].links
        return []

    def get_link(self, 
        string, 
        filename, 
        col_pos=0,
        file_pos=0):
        """ 
        Given a line of text passed from an editor, 
        opens a web link, file, or returns a node,
        in that order. Returns a tuple of type and success/failure or node ID
        """
        link = self.find_link(
            string, 
            filename, 
            col_pos=col_pos,
            file_pos=file_pos)

        if not link:
            return
                
        if not link['kind']:
            if not self.compiled:
               return print('Project is still compiling')
            return print('No node ID, web link, or file found on this line.')

        if link['kind'] == 'NODE' and link['link'] not in self.nodes:
            if not self.compiled:
               return print('Project is still compiling')
            return print('Node ' + link['link'] + ' is not in the project')

        return link

    def find_link(self, 
        string,
        filename, 
        col_pos=0,
        file_pos=0):
      
        kind = ''
        link = ''
        dest_position = None
        link_match = None
        link_location = None
        filename = os.path.basename(filename)

        result = syntax.action_c.search(string)
        if result:
            action = result.group(1)
            for name in self.actions:
                if name == action:
                    r = self.actions[name](self)
                    return r.execute(
                        result.group(2),
                        filename,
                        action_span=result.span(),
                        col_pos=col_pos,
                        file_pos=file_pos)

        link = syntax.node_link_or_pointer_c.search(string)
        if link:
            full_match = link.group().strip()
            link = link.group(2).strip()
            if link in self.nodes:
                result = link
            else:
                for node_id in self.nodes:
                    if node_id.startswith(link):
                        result = node_id
                        break
        node_id = ''
        if result:
            kind = 'NODE'
            node_id = result
            link_location = file_pos + len(result)
            link = result # node id
            dest_position = self.get_file_position(link, 0)
        else:
            result = syntax.editor_file_link_c.search(string)            
            if result:
                full_match = result.group().strip()
                link = os.path.join(self.path, result.group(2)).strip()
                kind = 'EDITOR_LINK'              
                if os.path.splitext(link)[1][1:] in self.settings['open_with_system']:
                    kind = 'SYSTEM'              
            else:
                result = syntax.url_c.search(string)                
                if result:
                    kind ='HTTP'
                    link = result.group().strip()
                    full_match = link
        if result:
            return {
                'kind' : kind, 
                'link' : link, 
                'full_match' : full_match,
                'node_id' : node_id,
                'file_pos': file_pos, 
                'link_location' : link_location, 
                'dest_position' : dest_position 
                }

    def _is_duplicate_id(self, node_id, filename):
        """ private method to check if a node id is already in the project """
        if node_id in self.nodes:
            return self.nodes[node_id].filename
        return False

    def _log_item(self, filename, message):
        if filename: 
            self.messages.setdefault(filename, [])
            self.messages[filename].append(message)
        if self.settings['console_log']: print(str(filename)+' : '+ message)
        
    def timestamp(self, date=None):
        """ 
        Returns a timestamp in the format set in project_settings, or the default 
        """
        if date == None:
            date = datetime.datetime.now()
        if date.tzinfo == None:
            date = date.replace(tzinfo=datetime.timezone.utc)    
        timestamp_format = '<' + self.settings['timestamp_format'] + '>'
        return date.strftime(timestamp_format)

    def _get_settings_from(self, node):
      
        replacements = {}
        for entry in node.metadata.all_entries():
   
            if entry.keyname in replace_settings:
                replacements.setdefault(entry.keyname, [])
                replacements[entry.keyname].append(entry.value)
                continue

            if entry.keyname == 'project_title':
                # sets a project object property, not the settings dict
                self.title = entry.value
                continue

            if entry.keyname == 'numerical_keys':
                self.settings['numerical_keys'].append(entry.value)
                continue

            if entry.keyname in single_values_settings:
                if entry.keyname in integers_settings:
                    try:
                        self.settings[entry.keyname] = int(entry.value)
                    except:
                        print(entry.value + ' not an integer')
                else:
                    self.settings[entry.keyname] = entry.value
                continue

            if entry.keyname in single_boolean_values_settings:
                self.settings[entry.keyname] = True if entry.value.lower() in ['true','yes'] else False
                continue            

            if entry.keyname not in self.settings:
                self.settings[str(entry.keyname)] = []

            self.settings[str(entry.keyname)].append(entry.value)
            self.settings[str(entry.keyname)] = list(set(self.settings[entry.keyname]))

        for k in replacements.keys():
            if k in single_values_settings:
                self.settings[k] = replacements[k][0]
            else:
                self.settings[k] = replacements[k]

    def run_action(self, action, string, filename, col_pos=0, file_pos=0):
        instance = self.actions[action](self)
        if not filename:
            return None
        return self.execute(instance.execute,            
            string, 
            filename=filename, 
            col_pos=col_pos,
            file_pos=file_pos)
            
    def get_home(self):
        return self.settings['home']

    def get_all_meta_pairs(self):
        pairs = []
        for n in list(self.nodes):
            for k in self.nodes[n].metadata.get_keys():
               values = self.nodes[n].metadata.get_values(k)
               if k == '#':
                    k = self.settings['hash_key']
               for v in values:
                    pairs.append(''.join([k, '::', str(v) ])  )

        return list(set(pairs))

    def random_node(self):
        if self.nodes:
            node_id = random.choice(list(self.nodes))
            return node_id
        return None
    
    def replace_links(self, original_id, new_id='', new_project=''):
        if not new_id and not new_project:
            return None
        replacement = '>'+original_id
        if new_id:
            replacement = '>'+new_id
        if new_project:
            replacement = '=>"'+new_project+'"'+replacement
        
        #TODO factor regexes out into syntax.py
        patterns_to_replace = [
            r'\|.*?\s>{1,2}',   # replace title markers before anything else
            r'[^\}]>>',         # then node pointers
            r'[^\}]>' ]         # finally node links

        for filename in list(self.files):
            contents = self.files[filename]._get_file_contents()
            new_contents = contents
            for pattern in patterns_to_replace:
                links = re.findall(pattern + original_id, new_contents)
                for link in links:
                    new_contents = new_contents.replace(link, replacement, 1)
            if contents != new_contents:
                self.files[filename]._set_file_contents(new_contents, compare=False)
                return self.execute(self._file_update, filename)

    def on_modified(self, filenames):
        """
        Call whenever a file is known to have changed contents
        """        
        if not isinstance(filenames, list):
            filenames = [filenames]
        filenames = [f for f in filenames if f not in self.excluded_files]

        return self.execute(self._file_update, filenames)
    
    def _file_update(self, filenames):
        
        if self.compiled:
            modified_files = []
            for f in filenames:
                if f not in self.files:
                    continue
                self._parse_file(f)
                modified_file = self._compile_file(f)
                if modified_file:
                    modified_files.append(modified_file)
            self._sync_file_list()
            return modified_files

    def visit_node(self, node_id):
        return self.execute(self._visit_node, node_id)

    def _visit_node(self, node_id):
        for ext in self.extensions:
            self.extensions[ext].on_node_visited(node_id)
        for dd in self.dynamic_defs():
            for op in dd.operations:
                op.on_node_visited(node_id)

    def visit_file(self, filename):
        return self.execute(self._visit_file, filename)

    def _visit_file(self, filename):
        """
        Call whenever a file requires dynamic updating
        """        
        filename = os.path.basename(filename)
        if filename in self.exports:
            self._process_dynamic_def(self.exports[filename])        
        if filename in self.files and self.compiled:
            return self._compile_file(filename)

    def _sync_file_list(self):
        included_files = self._get_included_files()
        current_files = list(self.files)
        for file in [f for f in included_files if f not in current_files]:
            self._parse_file(file)
        for file in [f for f in list(self.files) if f not in included_files]: # now list of dropped files
            self._log_item(file, file+' no longer seen in project path. Dropping it from the project.')
            self.remove_file(file)

    def _get_included_files(self):
        basenames = self._get_basenames()
        return [f for f in basenames if self._include_file(f)]

    def _get_basenames(self):
        all_files = os.listdir(self.path)
        return [os.path.basename(f) for f in all_files]

    def _include_file(self, filename):
        if filename in self.excluded_files:
            return False 
        if os.path.splitext(filename)[1] not in self.file_extensions:
            return False
        return True
    
    def _add_to_excluded_files(self, filename):
        if filename not in self.excluded_files:
            self.excluded_files.append(filename)    
    
    def _add_to_error_files(self, filename):
        if filename not in self.error_files:
            self.error_files.append(filename)    

    def add_file(self, filename):
        """ 
        parse syncronously so we can raise an exception
        if moving files between projects.
        """
        any_duplicate_ids = self._parse_file(filename)
        
        if any_duplicate_ids:
            self._log_item(filename, 'File moved but not added to destination project. Duplicate Nodes IDs shoudld be printed above.')
            raise DuplicateIDs()
        return self.execute(self._compile)

    def remove_file(self, filename):
        self.execute(self._remove_file, os.path.basename(filename))
    
    def get_file_name(self, node_id, absolute=False):
        filename = None
        if node_id in self.nodes:
            filename = self.nodes[node_id].filename
        else:
            return None
        if absolute:
            filename = os.path.join(self.path, filename)
        return filename

    def title_completions(self):
        return [(self.nodes[n].get_title(), ''.join(['| ',self.nodes[n].get_title(),' >',self.nodes[n].id])) for n in list(self.nodes)]

    def get_first_value(self, node, keyname):
        value = node.metadata.get_first_value(keyname)
        if keyname in self.settings['numerical_keys']:
            try:
                value = float(value)
            except ValueError:
                return 0
        return value

    def get_all_keys(self):
        keys = []
        exclude = self.settings['exclude_from_star']
        exclude.extend(self.settings.keys())
        for nid in list(self.nodes):
            keys.extend(self.nodes[nid].metadata.get_keys(exclude=exclude)
            )
        return list(set(keys))

    def get_all_values_for_key(self, key, lower=False):
        values = []
        for nid in self.nodes:
            values.extend(self.nodes[nid].metadata.get_values(key))
        if lower:
            return list(set([v.lower() for v in values]))
        return list(set(values))

    def get_dynamic_definition(self, target_id):
        for dd in self.dynamic_definitions:
            if dd.target_id == target_id:
                position = self.get_file_position(dd.source_id, dd.location)
                return { 
                    'id' : dd.source_id,
                    'location' : position}


    def get_by_meta(self, key, values, operator):
        
        if isinstance(values,str):
            values = [values]
        results = []

        if operator in ['before','after']:
            
            compare_date = date_from_timestamp(values[0][1:-1])
            
            if compare_date:
                if operator == 'before':
                    results = [n for n in self.nodes if default_date != self.nodes[n].metadata.get_date(key) < compare_date]
                if operator == 'after':
                    results = [n for n in self.nodes if self.nodes[n].metadata.get_date(key) > compare_date != default_date ]

                return set(results)

            return set([])

        if key == '_contents' and operator == '?': # `=` not currently implemented
            for node_id in list(self.nodes):
                if self.nodes[node_id].dynamic:
                    continue
                matches = []
                contents = self.nodes[node_id].content_only()
                lower_contents = contents.lower()           

                for v in values:
                    if v.lower() in lower_contents:
                        results.append(node_id)

            return results

        if key == '_links_to':
            for v in values:
                results.extend(self.get_links_to(v))
            return results

        if key == '_links_from':
            for v in values:
                results.extend(self.get_links_from(v))
            return results

        results = set([])
        
        if key == '*':
            keys = self.get_all_keys()
        
        else:
            keys = [key]

        for k in keys:
            for value in values:

                if value in ['*']:
                    results = results.union(set(n for n in list(self.nodes) if self.nodes[n].metadata.get_values(k))) 
                    continue

                use_timestamp = False
                if isinstance(value, UrtextTimestamp):
                    use_timestamp = True

                if k in self.settings['numerical_keys']:
                    try:
                        value = float(value)
                    except ValueError:
                        value = 99999999
                
                if k in self.settings['case_sensitive']:
                    results = results.union(set(
                        n for n in list(self.nodes) if value in self.nodes[n].metadata.get_values(
                            k, use_timestamp=use_timestamp)))
                else:
                    if isinstance(value, str):
                        value=value.lower()
                    results = results.union(set(
                        n for n in list(self.nodes) if n in self.nodes and value in self.nodes[n].metadata.get_values(
                            k, 
                            use_timestamp=use_timestamp, 
                            lower=True)))
        
        return results

    def get_file_and_position(self, node_id):
        if node_id in self.nodes:
            filename = self.get_file_name(node_id, absolute=True)
            position = self.nodes[node_id].start_position()
            return filename, position
        return None, None

    def execute(self, function, *args, **kwargs):
        if self.is_async:
            future = self.executor.submit(function, *args, **kwargs)
            return future
        else:    
            return function(*args, **kwargs)

                
class NoProject(Exception):
    """ no Urtext nodes are in the folder """
    pass

class DuplicateIDs(Exception):
    """ duplicate IDS """
    def __init__(self):
        pass

""" 
Helpers 
"""

def match_compact_node(selection):
    return True if syntax.compact_node_c.match(selection) else False
        
def creation_date(path_to_file):
    """
    Try to get the date that a file was created, falling back to when it was
    last modified if that isn't possible.
    See http://stackoverflow.com/a/39501288/1709587 for explanation.
    """
    if platform.system() == 'Windows':
        return datetime.datetime.fromtimestamp(os.path.getctime(path_to_file))
    else:
        stat = os.stat(path_to_file)
        try:
            return datetime.datetime.fromtimestamp(stat.st_birthtime)
        except AttributeError:
            # We're probably on Linux. No easy way to get creation dates here,
            # so we'll settle for when its content was last modified.
            return datetime.datetime.fromtimestamp(stat.st_mtime)
