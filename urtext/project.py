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

if os.path.exists(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'sublime.txt')):
    from ..anytree import Node, PreOrderIter, RenderTree
    from .file import UrtextFile, UrtextBuffer
    from .node import UrtextNode
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

def all_subclasses(cls):
    return set(cls.__subclasses__()).union(
        [s for c in cls.__subclasses__() for s in all_subclasses(c)])

class UrtextProject:

    urtext_file = UrtextFile
    urtext_node = UrtextNode

    def __init__(self, entry_point, add_project):

        self.settings = default_project_settings()
        self._add_project = add_project # ProjectList method
        self.entry_point = entry_point
        self.entry_path = None
        self.settings['project_title'] = self.entry_point # default
        self.is_async = True
        self.is_async = False # development
        self.time = time.time()
        self.last_compile_time = 0
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
        self.directives = {}
        self.duplicate_ids = {}
        self.compiled = False
        self.project_list = None
        self.excluded_files = []
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=50)        
        self.execute(self._initialize_project)
    
    def _initialize_project(self):

        self._collect_extensions_directives_actions()

        num_file_extensions = len(self.settings['file_extensions'])
        num_paths = len(self.settings['paths'])

        # parse the entry point
        if os.path.isdir(self.entry_point):
            self.entry_path = self.entry_point
            self.settings['paths'].append({
                'path' : self.entry_point,
                'recurse' : False
                })
            for file in self._get_included_files():
                self._parse_file(file)
        else:
            self.entry_path = os.dirname(self.entry_point)
            self._parse_file(self.entry_point)

        # check what additional folders are included
        # and what paths within that folder are included
        while len(self.settings['paths']) > num_paths or len(self.settings['file_extensions']) > num_file_extensions:
            num_paths = len(self.settings['paths'])
            num_file_extensions = len(self.settings['file_extensions'])
            for file in self._get_included_files():
                if file not in self.files:
                    self._parse_file(file)

        # or if additional projects have been added
        
        # also actions, directions, or extensions have been added within the project.

        for node_id in self.nodes:
            self.nodes[node_id].metadata.convert_hash_keys()
            self.nodes[node_id].metadata.convert_node_links()
            


        
        self._compile()

        # if len(self.extensions) > num_extensions or len(self.actions) > num_actions or len(self.directives) > num_directives:
        #     self._compile()
        self.compiled = True
        self.last_compile_time = time.time() - self.time
        self.time = time.time()
        print('"'+self.settings['project_title']+'" compiled')
    
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
    
        if self._filter_filenames(filename) == None:
            return self._add_to_excluded_files(filename)

        old_node_ids = []
        if filename in self.files:
            old_node_ids = self.files[filename].get_ordered_nodes()
        self._drop_file(filename)
        
        new_file = self.urtext_file(filename, self)
        self.messages[new_file.filename] = new_file.messages

        file_should_be_dropped, should_re_parse = self._check_file_for_duplicates(new_file)
        
        if should_re_parse:
            return self._parse_file(filename)

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
            if self.compiled:
                self._rewrite_changed_links(changed_ids)

        self.files[new_file.filename] = new_file  
        for node_id in new_file.nodes:
            self._add_node(new_file.nodes[node_id])
        
        for node_title in new_file.nodes:
            if new_file.nodes[node_title].parent:
                new_file.nodes[node_title].parent.children.append(new_file.nodes[node_title])

        for entry in new_file.meta_to_node:
            keyname = entry.group(1)
            source_node = self.get_node_id_from_position(filename, entry.span()[0])
            target_node = self.get_node_id_from_position(filename, entry.span()[1])
            self.nodes[source_node].metadata.add_entry(
                keyname, 
                self.nodes[target_node],
                is_node=True)

        for ext in self.extensions:
             self.extensions[ext].on_file_modified(filename)

        for node_id in new_file.nodes:            
            node = self.nodes[node_id]
            if node.title == 'project_settings':
                self._get_settings_from(node)     

            for dd in node.dynamic_definitions:
                dd.source_id = node.id
                self.dynamic_definitions.append(dd)

            for entry in node.metadata.dynamic_entries:
                entry.from_node = node.id
                self._add_sub_tags(entry)
                self.dynamic_metadata_entries.append(entry) 

    def _collect_extensions_directives_actions(self):

        changed = False
        all_extensions = all_subclasses(UrtextExtension)
        all_directives = all_subclasses(UrtextDirective)
        all_actions = all_subclasses(UrtextAction)

        if len(all_extensions) != len(self.extensions):
            changed = True

        if len(all_directives) != len(self.directives):
            changed = True

        if len(all_actions) != len (self.actions):
            changed = True

        for c in all_extensions:
            for n in c.name:
                self.extensions[n] = c(self)

        for c in all_actions:
            for n in c.name:
                self.actions[n] = c

        for c in all_directives:
            for n in c.name:
                self.directives[n] = c

        return changed 

    def _add_all_sub_tags(self):
        for entry in self.dynamic_metadata_entries:
            self._add_sub_tags(entry)
        
    def _rewrite_changed_links(self, changed_ids):

        old_ids = list(changed_ids.keys())
        nodes = list(self.nodes)
        for node_id in nodes:
            changed_links = {}

            for link in self.nodes[node_id].links:
                for old_id in old_ids:
                    if old_id.startswith(link):
                        changed_links[link] = changed_ids[old_id]
            if changed_links:
                filename = self.nodes[node_id].filename
                contents = self.files[filename]._get_file_contents()
                replaced_contents = contents
                for node_id in list(changed_ids.keys()):
                    if '| ' + node_id + ' >' in contents:
                         replaced_contents = replaced_contents.replace(
                            '| '+ node_id + ' >', 
                            '| '+ changed_ids[node_id] + ' >')
                if replaced_contents != contents:
                    self.files[filename]._set_file_contents(replaced_contents)
                    self._parse_file(filename)

    def _check_file_for_duplicates(self, file_obj):

        duplicate_nodes = {}
        for node_id in file_obj.nodes:
            if self._is_duplicate_id(node_id, file_obj.filename):
                resolved_id = file_obj.nodes[node_id].resolve_duplicate_id()
                if resolved_id:
                    file_obj.nodes[node_id].apply_title(resolved_id)
                    for index in file_obj.parsed_items:
                        if file_obj.parsed_items[index] == node_id:
                            file_obj.parsed_items[index] = resolved_id
                else:
                    duplicate_nodes[node_id] = file_obj.filename
        
        file_should_be_dropped = False
        should_re_parse = False

        if duplicate_nodes:
            messages = []
            
            self._log_item(file_obj.filename, 
                'Duplicate node ID(s) found: ' + ''.join([
                    ''.join(['\n\t',
                                syntax.link_opening_wrapper, 
                                n,
                                syntax.link_closing_wrapper,
                                ' (also in) ',
                                syntax.file_link_opening_wrapper,
                                self.nodes[n].filename,
                                syntax.file_link_closing_wrapper,
                            ]) for n in duplicate_nodes]))
            file_should_be_dropped = True
            
        return file_should_be_dropped, should_re_parse

    def _target_id_defined(self, check_id):
        """ """
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

                    message = ''.join(['Dynamic node ', 
                                syntax.link_opening_wrapper,
                                definition.target_id,
                                syntax.link_closing_wrapper,
                                ' has duplicate definition in', 
                                syntax.link_opening_wrapper,
                                new_node.id,
                                syntax.link_closing_wrapper,
                                '; Keeping the definition in ',
                                syntax.link_opening_wrapper,
                                defined,
                                syntax.link_closing_wrapper])

                    self._log_item(new_node.filename, message)

        new_node.project = self
        self.nodes[new_node.id] = new_node  
        if self.compiled:
            new_node.metadata.convert_node_links()     
        
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
        for node_id in self.files[filename].nodes:
            number_ranges = len(self.nodes[node_id].ranges)
            for index in range(number_ranges):
                this_range = self.nodes[node_id].ranges[index]
                if from_position >= this_range[0]:
                    self.nodes[node_id].ranges[index][0] -= amount
                    self.nodes[node_id].ranges[index][1] -= amount

    """
    Removing and renaming files
    """
    def _drop_file(self, filename):

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
        if filename in self.files:
            for node_id in list(self.files[filename].nodes):
                while node_id in self.navigation:
                    index = self.navigation.index(node_id)
                    del self.navigation[index]
                    if self.nav_index >= index:
                        self.nav_index -= 1            
            self._drop_file(filename)
            os.remove(filename)
        if filename in self.messages:
            del self.messages[filename]
        if open_files:
            return self.on_modified(open_files)
        return []
    
    def _handle_renamed(self, old_filename, new_filename):
        if new_filename != old_filename:
            self.files[new_filename] = self.files[old_filename]
            for node_id in self.files[new_filename].nodes:
                self.nodes[node_id].filename = new_filename
                self.files[new_filename].filename = new_filename
                self.nodes[node_id].full_path = new_filename
            del self.files[old_filename]
            for ext in self.extensions:
                self.extensions[ext].on_file_renamed(old_filename, new_filename)
    
    """ 
    filtering files to skip 
    """
    def _filter_filenames(self, filename):
        if filename in ['urtext_files','.git']:
            return None            
        if filename in self.settings['exclude_files']:
            return None
        return filename
    
    def new_file_node(self, 
        date=None,
        path=None,
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
        
        filename = filename + '.urtext'
        if path:
            filename = os.path.join(path, filename)
        with open(filename, "w") as f:
            f.write(contents)  
        self._parse_file(filename)

        #TODO refactor so that UrtextFile rememebrs these as UrtextNodes, not titles
        title = self.files[filename].root_node

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

        if contents_format:
            new_node_contents = contents_format.replace('$timestamp', '<' + self.timestamp(datetime.datetime.now()).string + '>')
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
                    self.nodes[r].display_meta = self.timestamp(
                        self.nodes[r].metadata.get_first_value(
                            k, 
                            use_timestamp=use_timestamp),
                        as_string=True)
                else:
                    self.nodes[r].display_meta = str(self.nodes[r].metadata.get_first_value(k))
            node_group = sorted(node_group, key=lambda nid: sort(nid, return_type=True), reverse=k in self.settings['use_timestamp'] )
            sorted_nodes.extend(node_group)
            remaining_nodes = list(set(remaining_nodes) - set(node_group))
        sorted_nodes.extend(remaining_nodes)
        return sorted_nodes

    def all_files(self):
        self._sync_file_list()
        files=list(self.files)
        prefix = 0
        sorted_files = []
        for k in self.settings['file_index_sort']:
            k = k.lower()
            use_timestamp= True if k in self.settings['use_timestamp'] else False
            file_group = [f for f in files if self.files[f].root_node and self.nodes[self.files[f].root_node].metadata.get_first_value(k, use_timestamp=use_timestamp)]
            file_group = sorted(file_group, 
                key=lambda f:  self.nodes[self.files[f].root_node].metadata.get_first_value(k, use_timestamp=use_timestamp),
                reverse=use_timestamp)
            sorted_files.extend(file_group)
            files = list(set(files) - set(sorted_files))
        sorted_files.extend(files)
        return sorted_files

    def get_node_id_from_position(self, filename, position):
        if filename in self.files:
            for node_id in self.files[filename].nodes:
                for r in self.files[filename].nodes[node_id].ranges:                   
                    if position in range(r[0],r[1]+1): # +1 in case the cursor is in the last position of the node.
                        return node_id
        return None

    def get_node_id_from_position_in_buffer(self, contents, position):
        buffer = UrtextBuffer(self)
        buffer.lex_and_parse(contents)
        for node_id in buffer.nodes:
            for r in buffer.nodes[node_id].ranges:
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
                link = result.group(2).strip()
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
    def get_node_contents(self, node_id):
        if node_id in self.nodes:
            return self.nodes[node_id].contents()
            
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
        
    def timestamp(self, date=None, as_string=False):
        """ 
        Returns a timestamp in the format set in project_settings, or the default 
        """
        if date == None:
            date = datetime.datetime.now()
        if date.tzinfo == None:
            date = date.replace(tzinfo=datetime.timezone.utc)
        if as_string:
            return ''.join([
                syntax.timestamp_opening_wrapper,
                date.strftime(self.settings['timestamp_format']),
                syntax.timestamp_closing_wrapper,
                ])

        return UrtextTimestamp(date.strftime(self.settings['timestamp_format']))

    def _get_settings_from(self, node):
      
        replacements = {}
        for entry in node.metadata.all_entries():
   
            if entry.keyname in replace_settings:
                replacements.setdefault(entry.keyname, [])
                replacements[entry.keyname].append(entry.value)
                continue

            if entry.keyname == 'numerical_keys':
                self.settings['numerical_keys'].append(entry.value)
                continue

            if entry.keyname == 'file_extensions':
                value = entry.value
                if value[0] != '.':
                    value = '.' + value
                self.settings['file_extensions'] = ['.urtext'].append(value)
                continue

            if entry.keyname == 'paths':
                if entry.is_node:
                    for n in entry.value.children:
                        path = n.metadata.get_first_value('path')
                        recurse = n.metadata.get_first_value('recurse')
                        if path and path not in [entry['path'] for entry in self.settings['paths']]:
                            self.settings['paths'].append({
                                'path' : path,
                                'recurse': True if recurse.lower() in ['yes', 'true'] else False
                                })
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
                    pairs.append(''.join([k, syntax.metadata_assignment_operator, str(v) ])  )

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

        return self.execute(self._file_update, filenames)
    
    def _file_update(self, filenames):
        if self.compiled:
            modified_files = []
            for f in filenames:
                any_duplicate_ids = self._parse_file(f)
                if not any_duplicate_ids:
                    modified_file = self._compile_file(f)
                    if modified_file:
                        modified_files.append(modified_file)
            self._sync_file_list()
            return modified_files

    def visit_node(self, node_id):
        return self.execute(self._visit_node, node_id)

    def _visit_node(self, node_id):
        for ext in list(self.extensions):
            self.extensions[ext].on_node_visited(node_id)
        for dd in list(self.dynamic_definitions):
            for op in dd.operations:
                op.on_node_visited(node_id)

    def visit_file(self, filename):
        return self.execute(self._visit_file, filename)

    def _visit_file(self, filename):
        """
        Call whenever a file requires dynamic updating
        """        
        if filename in self.files and self.compiled:
            return self._compile_file(filename)

    def _sync_file_list(self):
        included_files = self._get_included_files()
        current_files = list(self.files)
        for file in [f for f in included_files if f not in current_files]:
            self._parse_file(file)
        for file in [f for f in list(self.files) if f not in included_files]: # now list of dropped files
            self._log_item(file, file+' no longer seen in project path. Dropping it from the project.')
            self._drop_file(file)

    def _get_included_files(self):
        files = []
        for path in self.settings['paths']:
            files.extend([os.path.join(path['path'], f) for f in os.listdir(path['path'])])
        return [f for f in files if self._include_file(f)]

    def _include_file(self, filename):
        if filename in self.excluded_files:
            return False
        if os.path.splitext(filename)[1] not in self.settings['file_extensions']:
            return False
        return True
    
    def _add_to_excluded_files(self, filename):
        if filename not in self.excluded_files:
            self.excluded_files.append(filename)    
    
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

    def drop_file(self, filename):
        self.execute(self._drop_file, filename)
    
    def get_file_name(self, node_id):
        filename = None
        if node_id in self.nodes:
            filename = self.nodes[node_id].filename
        else:
            return None
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
        entries = []
        for nid in self.nodes:
            entries.extend(self.nodes[nid].metadata.get_entries(key))
        values = [e.value_as_string() for e in entries]
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
                    results = results.union(
                        set(n for n in list(self.nodes) if n in self.nodes 
                            and self.nodes[n].metadata.get_values(k))
                        ) 
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
            filename = self.get_file_name(node_id)
            position = self.nodes[node_id].start_position()
            return filename, position
        return None, None

    def execute(self, function, *args, **kwargs):
        if self.is_async:
            future = self.executor.submit(function, *args, **kwargs)
            return future
        else:    
            return function(*args, **kwargs)

    """ Project Compile """

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
            #TODO Refactor
            for dd in self.dynamic_definitions:
                if dd.target_file and dd.source_id == node_id:
                    output = self._process_dynamic_def(dd)
                    if output:
                        if self._write_dynamic_def_output(dd, output):
                            modified = filename                        
        return modified

    def _process_dynamic_def(self, dynamic_definition):
                
        if dynamic_definition.target_id == None and not dynamic_definition.target_file: 
            self._log_item(None, ''.join([
                    'Dynamic definition in ',
                    syntax.link_opening_wrapper,
                    dynamic_definition.source_id,
                    syntax.link_closing_wrapper,
                    ' has no target']))
            return

        if dynamic_definition.target_id and dynamic_definition.target_id not in self.nodes:
            return self._log_item(None, ''.join([
                        'Dynamic node definition in',
                        syntax.link_opening_wrapper,
                        dynamic_definition.source_id,
                        syntax.link_closing_wrapper,
                        ' points to nonexistent node ',
                        syntax.link_opening_wrapper,
                        dynamic_definition.target_id,
                        syntax.link_closing_wrapper]))

        output = dynamic_definition.process_output()    
        
        if not dynamic_definition.returns_text and not dynamic_definition.target_file:
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
            filename = os.path.join(self.entry_point, dynamic_definition.target_file)
            self.exports[dynamic_definition.target_file] = dynamic_definition
            with open(filename, 'w', encoding='utf-8' ) as f:
                f.write(final_output)
            changed_file = dynamic_definition.target_file

            #TODO -- If the file is an export, need to make sure it is remembered
            # when parsed so duplicate titles can be avoided

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

    """ Metadata Handling """

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
            wrapped_timestamp = ''.join([
                syntax.timestamp_opening_wrapper,
                timestamp.string,
                syntax.timestamp_closing_wrapper
                ])
            metadata = { self.settings['tag_other'][0] : self.settings['tag_other'][1] + ' ' + wrapped_timestamp}
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
        if source_tree_node.name.replace('ALIA$','') not in self.nodes:
            return

        for child in self.nodes[source_tree_node.name.replace('ALIA$','')].tree_node.children:
            
            uid = source_tree_node.name + child.name
            if uid in visited_nodes:
                continue
            node_to_tag = child.name.replace('ALIA$','')
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

class DuplicateIDs(Exception):
    """ duplicate IDS """
    def __init__(self):
        pass

""" 
Helpers 
"""

def match_compact_node(selection):
    return True if syntax.compact_node_c.match(selection) else False

def indent(contents, spaces=4):
  
    content_lines = contents.split('\n')
    content_lines[0] = content_lines[0].strip()
    for index, line in enumerate(content_lines):
        if line.strip() != '':
            content_lines[index] = '\t' * spaces + line
    return '\n'+'\n'.join(content_lines)