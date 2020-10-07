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
import itertools
import platform
import json
import os
import random
import time
import pickle
from time import strftime
import concurrent.futures
import diff_match_patch as dmp_module
from dateutil.parser import *
from pytz import timezone

from .file import UrtextFile
from .interlinks import Interlinks
from .node import UrtextNode 
from .compile import compile_functions
from .trees import trees_functions
from .meta_handling import metadata_functions
from .reindex import reindex_functions
from .search import search_functions
from .collection import collection_functions
from .dynamic import UrtextDynamicDefinition

node_pointer_regex = r'>>[0-9,a-z]{3}\b'
node_link_regex = r'>[0-9,a-z]{3}\b'
title_marker_regex = r'\|.*?\s>{1,2}[0-9,a-z]{3}\b'
node_id_regex = r'\b[0-9,a-z]{3}\b'

functions = trees_functions
functions.extend(compile_functions)
functions.extend(metadata_functions)
functions.extend(reindex_functions)
functions.extend(search_functions)
functions.extend(collection_functions)


def add_functions_as_methods(functions):
    def decorator(Class):
        for function in functions:
            setattr(Class, function.__name__, function)
        return Class
    return decorator

@add_functions_as_methods(functions)
class UrtextProject:
    """ Urtext project object """

    def __init__(self,
                 path,
                 rename=False,
                 recursive=False,
                 import_project=False,
                 init_project=False,
                 watchdog=False):
        
        self.is_async = True 
        #self.is_async = False # development only
        self.path = path
        self.nodes = {}
        self.h_content = {}
        self.files = {}
        self.keynames = {}
        self.navigation = []  # Stores, in order, the path of navigation
        self.nav_index = -1  # pointer to the CURRENT position in the navigation list
        self.to_import = []
        self.settings_initialized = False
        self.dynamic_nodes = []  # { target : definition, etc.}
        self.dynamic_memo = {}
        self.watchdog = watchdog
        # dict of nodes tagged recursively from parent/ancestors
        self.dynamic_meta = { } # { source_id :  { 'entries' : [] , 'targets' : [] } }
        self.quick_loaded = False
        self.compiled = False
        self.links_to = {}
        self.links_from = {}
        self.loaded = False
        self.other_projects = [] # propagates from UrtextProjectList, permits "awareness" of list context
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        self.access_history = {}
        self.messages = {}
        self.title_completions = []
        self.settings = {  # defaults
            'home': None,
            'timestamp_format':'%a., %b. %d, %Y, %I:%M %p', 
            'use_timestamp': ['timestamp','inline-timestamp'],
            'filenames': ['PREFIX', 'DATE %m-%d-%Y', 'TITLE'],
            'console_log': True,
            'google_auth_token' : 'token.json',
            'google_calendar_id' : None,
            'timezone' : ['UTC'],
            'always_oneline_meta' : False,
            'format_string': '$title\n-\n',
            'strict':False,
            'node_date_keyname' : '',
            'log_id': '',
            'numerical_keys': ['_index' ,'index'],
            'preload': [],
            'atomic_rename' : False,
            'case_sensitive': [
                'title',
                'notes',
                'comments',
                'project_title',
                'timezone',
                'timestamp_format',
                'filenames',
                'weblink',
                'timestamp',]
        }
        self.default_timezone = timezone('UTC')
        self.title = self.path # default

        self.quick_load(import_project=import_project)
        if self.is_async:
            self.executor.submit(self._initialize_project,
                import_project=import_project, 
                init_project=init_project)
        else:
            self._initialize_project(
                 import_project=import_project, 
                 init_project=init_project)

        if not os.path.exists(os.path.join(self.path, "history")):
            os.mkdir(os.path.join(self.path, "history"))

        if watchdog:
            self._initialize_watchdog()        

    def quick_load(self, import_project=False):

        self.retrieve()
        
        if self.ql and 'last_accessed' in self.ql:
            for file in [t for t in self.ql['last_accessed'] if t in os.listdir(self.path)]:
                self._parse_file(file)
        self.quick_loaded = True
        
    def retrieve(self):
        if os.path.exists(os.path.join(self.path,'_store.json')):
            with open(os.path.join(self.path, '_store.json'), 'r') as f:
                self.ql = json.loads(f.read())
                self.settings=self.ql['project_settings']
                self.title = self.ql['title']
        else:
            self.ql = { 'last_accessed': [], 'title': '', 'path': self.path}

    def store(self):
        if self.compiled:
            self.ql['title'] = self.title
            self.ql['project_settings'] = self.settings       
            with open(os.path.join(self.path,'_store.json'), "w", encoding='utf-8') as f:
                f.write(json.dumps(self.ql))

    def _initialize_project(self, 
        import_project=False, 
        init_project=False):

        for file in [f for f in os.listdir(self.path) if f not in self.ql['last_accessed']]:
            self._parse_file(file, import_project=import_project)

        if import_project:
            for file in self.to_import:
                self.import_file(file)
        
        self.default_timezone = timezone(self.settings['timezone'][0])
        if self.nodes == {}:
            if init_project == True:
                self._log_item('Initalizing a new Urtext project in ' + self.path)
                self.new_file_node()
            else:
                raise NoProject('No Urtext nodes in this folder.')

        elif init_project:
            print('Urtext project already exists here.')
            return None            
        
        # must be done once manually on project init
        # TODO refactor
        for node_id in self.nodes:
            self._parse_meta_dates(node_id)
            for e in self.nodes[node_id].metadata.dynamic_entries:                
                self._add_sub_tags( node_id, node_id, e)

        self._get_access_history()        
        self._compile()
        self.compiled = True

    def _node_id_generator(self):
        chars = [
            '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', 'a', 'b', 'c',
            'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p',
            'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z'
        ]
        return itertools.product(chars, repeat=3)

    def formulate_links_to(self):       
        for node_id in self.links_from:
            self.update_links_in(node_id)

    def update_links_in(self, node_id):
        for link_from in self.links_from[node_id]:
            if link_from not in self.links_to:
                self.links_to[link_from] = []
            if node_id not in self.links_to[link_from]:
                self.links_to[link_from].append(node_id) 

    def remove_links_in(self, node_id):

        for destination in self.links_to:
            self.links_to[destination] = [ r for r in self.links_to[destination] if r != node_id ]

    def _assign_node_parent_title(self):
        """
        Only has to be called once on project init
        """

        for node_id in self.nodes:
            self.nodes[node_id].parent_project = self.title


    def _file_changed(self, filename, strict=False):
        
        old_hash = None
        if filename in self.files:
            already_in_project = True
            old_hash = self.files[filename].hash

        """
        Parse the file
        """
        new_file = UrtextFile(
            os.path.join(self.path, filename), 
            settings=self.settings,
            previous_hash=old_hash,
            strict=strict
            )
        
        if new_file.changed == False:
            return False

        return new_file

    def _parse_file(self, 
            filename, 
            import_project=False):
        """
        Parses a single file into the project.
        Returns None if successful, or a list of duplicate nodes found
        if duplicate nodes were found.
        FUTURE: return value should be sanitized Currently returns None, False or list.
        """
        filename = os.path.basename(filename)
        if self._filter_filenames(filename) == None:
            return
        
        already_in_project = False

        new_file = self._file_changed(filename)
        if not new_file:
            return None

        self.messages[filename] = []
        if new_file.messages:
            self.messages[filename] = new_file.messages 
        
        if not new_file.is_parseable:
            if already_in_project:
                self._log_item('Unable to re-parse >f'+filename+ ', dropping it from the project.')
                return False
            self.to_import.append(filename)
            return

        self._remove_file(filename)
        """
        Check the file for duplicate nodes
        """
        duplicate_nodes = self._check_file_for_duplicates(new_file)
        if duplicate_nodes:
            return duplicate_nodes
 
        """
        re-add the filename and all its nodes to the project
        """
        self.files[new_file.basename] = new_file  

        for node_id in new_file.nodes:
            self._add_node(new_file.nodes[node_id])
        
        self._set_tree_elements(new_file.basename)
        
        for node_id in new_file.nodes:
            self._rebuild_node_meta(node_id)

        """
        If this is not the initial load of the project, parse the timestamps in the file
        and rebuild sub-tags
        """        
        if self.compiled:
            for node_id in new_file.nodes:
                self._parse_meta_dates(node_id)
                for e in self.nodes[node_id].metadata.dynamic_entries:                
                    self._add_sub_tags( node_id, node_id, e)
     
        """ returns None if successful """
        return None

    def _check_file_for_duplicates(self, file_obj):
        duplicate_nodes = {}
        for node_id in file_obj.nodes:
            duplicate_filename = self._is_duplicate_id(node_id, file_obj.filename)
            if duplicate_filename:
                duplicate_nodes[node_id] = duplicate_filename

        if duplicate_nodes:
            basename = os.path.basename(file_obj.filename)
            self.messages[basename].append('Duplicate node ID(s) found')

            messages = []
            for node_id in duplicate_nodes:
                messages.append(''.join([
                    'node ID >',
                    node_id,
                    ' exists in f>',
                    duplicate_nodes[node_id]]) )

            file_obj.write_errors( self.settings, messages=messages)
            return duplicate_nodes

        return False

    def _rewrite_titles(self, filename):
        
        original_contents = self._full_file_contents(filename=filename)
        new_contents = original_contents
        offset = 0        
        for match in re.finditer(title_marker_regex, new_contents):
            start = match.start() + offset
            end = match.end() + offset
            location_node_id = self.get_node_id_from_position(filename, start)
            if not location_node_id:
                continue
            if not self.nodes[location_node_id].dynamic:          
                match_contents = new_contents[start:end]
                node_id = match_contents[-3:]
                if node_id in self.nodes:
                    title = self.nodes[node_id].title
                else:
                    title = ' ? '
                bracket = '>'
                if re.search(node_pointer_regex, match_contents):
                    bracket += '>'
                replaced_contents = ''.join([new_contents[:start],
                    '| ', title, ' ', bracket, node_id,
                    new_contents[end:]
                    ])
                offset += len(replaced_contents) - len(new_contents)
                new_contents = replaced_contents
        if new_contents != original_contents:
            return new_contents 
        return False

    def _target_id_defined(self, check_id):
        for definition in self.dynamic_nodes:
            if definition.target_id and definition.target_id == check_id:
                return definition.source_id
        return

    def _target_file_defined(self, file):
        for definition in self.dynamic_nodes:
            for e in  definition.exports:
                for f in e.to_files:
                    if f == file:
                        return definition.source_id
        return

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

                    self.messages[new_node.filename].append(message)
                    self._log_item(message)
                else:
                    self.dynamic_nodes.append(definition)

            if definition.exports:
                for e in definition.exports:
                    for f in e.to_files:
                        defined = self._target_file_defined(f)
                        if defined and defined != new_node.id:
                            message = ''.join([ 
                                          'File >f' , f ,
                                          ' has duplicate definition in >' , new_node.id ,
                                          '. Keeping the definition in >' , defined , '.'
                                          ])
                            self.message[new_node.filename].append(message)
                            self._log_item(message)
                        else:
                            self.dynamic_nodes.append(definition)

        if len(new_node.metadata.get_first_value('ID')) > 1:
            message = ''.join([ 
                    'Multiple ID tags in >' , new_node.id ,': ',
                    ', '.join(new_node.metadata.get_first_value('ID')),' - using the first one found.'])
            if new_node.filename not in self.messages: #why?
                self.messages[new_node.filename] = []
            self.messages[new_node.filename].append(message)
            self._log_item(message)

        new_node.parent_project = self.title
        if new_node.id in self.access_history:
            new_node.last_accessed = self.access_history[new_node.id]

        self.h_content[new_node.id] = new_node.hashed_contents
        new_node.project = self
        # TODO : it's not necessary to keep a copy of this
        # inside the node. do it at the project level only. 
        self.links_from[new_node.id] = new_node.links_from
        self.nodes[new_node.id] = new_node
        self.update_links_in(new_node.id)

        if new_node.project_settings:
            self._get_settings_from(new_node)

    def _parse_meta_dates(self, node_id):
        """ Parses dates (requires that timestamp_format already be set) """
        for entry in self.nodes[node_id].metadata._entries:

            if entry.dt_string:                    
                dt_stamp = self._date_from_timestamp(entry.dt_string)
                if dt_stamp:
                    entry.dt_stamp = dt_stamp 
                    if entry.keyname.lower() == self.settings['node_date_keyname'].lower():
                        self.nodes[node_id].date = dt_stamp

    def _date_from_timestamp(self, datestamp_string):
        dt_stamp = None
        try:
            d = parse(datestamp_string)
            if d.tzinfo == None:
                 d = self.default_timezone.localize(d) 
            return d
        except:
            pass

        return None

    def export_from_root_node(self, root_node_id):
        export = UrtextExport(self)
        contents = export.export_from(
            root_node_id, 
            kind='plaintext',
            as_single_file=True)
        return contents[0]
    

    def get_source_node(self, filename, position):
        if filename not in self.files:
            return None, None
        exported_node_id = self.get_node_id_from_position(filename, position)
        points = self.nodes[exported_node_id].export_points
        if not points:
            return None, None
        node_start_point = self.nodes[exported_node_id].ranges[0][0]

        indexes = sorted(points)
        for index in range(0, len(indexes)):
            if position >= indexes[index] and position < indexes[index+1]:
                node, target_position = self.nodes[exported_node_id].export_points[indexes[index]]
                offset = position - indexes[index]
                return node, target_position+offset

    def _set_node_contents(self, node_id, contents):
        """ project-aware alias for the Node set_content() method """

        self._parse_file(self.nodes[node_id].filename)
        if node_id not in self.nodes:
            print('NODE LOST')
            print(contents)
        self.nodes[node_id].set_content(contents, preserve_metadata=True)
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

    def _full_file_contents(self, filename='', node_id=''):
        if node_id:
            filename = self.nodes[node_id].filename
        if not filename:
            return
        with open(os.path.join(self.path, filename), 'r', encoding='utf-8') as theFile:
            file_contents = theFile.read()
            theFile.close()
        return file_contents

    def _set_file_contents(self, filename, contents):
        with open(os.path.join(self.path, filename), 'w', encoding='utf-8') as theFile:
            theFile.write(contents)

    def import_file(self, filename):

        with open(
                os.path.join(self.path, filename),
                'r',
                encoding='utf-8',
        ) as theFile:
            full_file_contents = theFile.read()
            theFile.close()

        date = creation_date(os.path.join(self.path, filename))
        now = datetime.datetime.now()
        contents = '\n\n'
        contents += "id::" + self.next_index() + '\n'
        if self.settings['node_date_keyname']:
            contents += self.settings['node_date_keyname']+'::' + self.timestamp(date) + '\n'
        contents += 'imported::' + self.timestamp(now) + '\n'

        full_file_contents += contents

        self._set_file_contents(filename,full_file_contents)

        return self._parse_file(filename)

    def get_node_relationships(self, 
        node_id, 
        omit=[]):

        return Interlinks(self, 
            node_id, 
            omit=omit).render_tree()

    def _list_messages(self):
        pass
        output = []
        for filename in self.messages:
            if self.messages[filename]:
                output.append('f>./'+filename)
                output.extend(self.messages[filename])
        return '\n'.join(output)

    def _populate_messages(self):
        if self.settings['log_id'] and self.settings['log_id'] in self.nodes:
            output = self._list_messages()
            output += '\n'+UrtextNode.build_metadata(
                {   'id':self.settings['log_id'],
                    'title':'Log',
                    'timestamp' : self.timestamp(datetime.datetime.now())
                })
            self.messages = {}
            changed = self._set_node_contents(self.settings['log_id'], output)     
            if changed:
                return self.nodes[self.settings['log_id']].filename
    """
    Removing and renaming files
    """
    def _remove_file(self, filename):
       
        if filename in self.files:
            
            for node_id in self.files[filename].nodes: 
                # remove this node's dynamic definitions
                for index, definition in enumerate(self.dynamic_nodes):
                    if definition.source_id == node_id:
                        del self.dynamic_nodes[index]
                
                self.nodes[node_id].tree_node.parent = None
                self.nodes[node_id].tree_node = None
                self._remove_sub_tags(node_id)                
                del self.links_from[node_id]
                self.remove_links_in(node_id)
                del self.nodes[node_id]
                del self.h_content[node_id]

            for a in self.files[filename].alias_nodes:
                a.parent = None
                a.children = []

            del self.files[filename]

    def delete_file(self, filename):
        """
        Deletes a file, removes it from the project,
        and returns a future of modified files.
        """
        filename = os.path.basename(filename)
        if filename in self.files:
            node_ids = list(self.files[filename].nodes)
            for node_id in node_ids:
                while node_id in self.navigation:
                    index = self.navigation.index(node_id)
                    del self.navigation[index]
                    if self.nav_index > index: # >= ?
                        self.nav_index -= 1            
            self.remove_file(filename)
            os.remove(os.path.join(self.path, filename))
            return node_ids
        return []
    
    def _handle_renamed(self, old_filename, new_filename):
        new_filename = os.path.basename(new_filename)
        old_filename = os.path.basename(old_filename)
        self.files[new_filename] = self.files[old_filename]
        for node_id in self.files[new_filename].nodes:
            self.nodes[node_id].filename = new_filename
            self.nodes[node_id].full_path = os.path.join(
                self.path, new_filename)
        if new_filename != old_filename:
            del self.files[old_filename]

    """ 
    Methods for filtering files to skip 
    """
    def _filter_filenames(self, filename):
        """ Filters out files to skip altogether """
        """ Omit system files """
        if filename[0] == '.':
            return None
        if not filename.endswith('.txt'):
            # FUTURE:
            # save and check these in an optional list of other extensions 
            # set from project_settings 
            return None
            
        return filename
    
    def new_file_node(self, 
        date=None, 
        metadata = {}, 
        node_id=None,
        one_line=None
        ):
        
        if date == None:
            date = datetime.datetime.now()

        if one_line == None:
            one_line = self.settings['always_oneline_meta']

        if not node_id:
            node_id = self.next_index()   
        metadata['id'] = node_id
        if self.settings['node_date_keyname']:
            metadata[self.settings['node_date_keyname']] = self.timestamp(date)
        metadata['from'] = platform.node()
        metadata_block = UrtextNode.build_metadata(metadata, one_line=one_line)
        contents = '\n\n\n' +metadata_block
        filename = node_id + '.txt'

        self._set_file_contents( filename, contents )  
        self._parse_file(filename)
        return { 
                'filename':filename, 
                'id':node_id
                }
 
    def add_inline_node(self, 
            date=None, 
            contents='',
            metadata={},
            one_line=None,
            trailing_id=False,
            include_timestamp=False):
              
        if one_line == None:
            one_line = self.settings['always_oneline_meta']
            
        node_id = self.next_index()

        if not trailing_id:
            metadata['id']=node_id
        
        if include_timestamp:

            if date == None:
                date = datetime.datetime.now()
 
            if 'node_date_keyname' in self.settings:
                metadata[self.settings['node_date_keyname']] = self.timestamp(date)
 
        new_node_contents = ''.join([
            '{ ', 
            contents,
            '  ',
            UrtextNode.build_metadata(metadata, one_line=one_line),
            ' '])
        if trailing_id:
            new_node_contents += node_id   
        new_node_contents += "}"
        return (new_node_contents, node_id)

    # def insert_interlinks(self, node_id, one_line=True):
    #     new_node = self.add_inline_node()
    #     insertion = new_node[0]
    #     new_node_id = new_node[1]
    #     dynamic_def =   '[[ id('+ new_node_id +'); '
    #     dynamic_def +=  'interlinks:'+node_id
    #     dynamic_def += ' ]]'

    #     return '\n'.join([insertion, dynamic_def])

    def add_compact_node(self, 
            date=None, 
            contents='', 
            metadata={},
        ):
        if date == None:
            date = datetime.datetime.now()
        metadata['id']=self.next_index()
        if self.settings['node_date_keyname']:
            metadata[self.settings['node_date_keyname']] = self.timestamp(date)
        metadata_block = UrtextNode.build_metadata(metadata, one_line=True)
        return '^  '+contents + ' ' + metadata_block

    def _prefix_length(self):
        """ Determines the prefix length for indexing files (requires an already-compiled project) """

        prefix_length = 0
        num_files = len(self.files)
        while num_files > 1:
            prefix_length += 1
            num_files /= 10
        return prefix_length

    """
    Project Navigation
    """

    def nav_advance(self):
        if not self.navigation:
            return None
        
        # return if the index is already at the end
        if self.nav_index == len(self.navigation) - 1:
            self._log_item('project index is at the end.')
            return None
        
        self.nav_index += 1
       
        return self.navigation[self.nav_index]


    def nav_new(self, node_id):

        # don't re-remember consecutive duplicate links
        if -1 < self.nav_index < len(self.navigation) and node_id == self.navigation[self.nav_index]:
            return

        if node_id in self.nodes and self.nodes[node_id].filename not in self.ql['last_accessed']:
            self.ql.setdefault('last_accessed',[])
            self.ql['last_accessed'].insert(0, self.nodes[node_id].filename)
            self.ql['last_accessed'] = self.ql['last_accessed'][:20]
            self.store()
            
        # add the newly opened file as the new "HEAD"
        self.nav_index += 1
        del self.navigation[self.nav_index:]
        self.navigation.append(node_id)
        self.executor.submit(self._push_access_history, node_id)
         
    def nav_reverse(self):
        if not self.navigation:
            return None

        if self.nav_index == 0:
            self._log_item('project index is already at the beginning.')
            return None

        self.nav_index -= 1
        last_node = self.navigation[self.nav_index]
        
        return last_node

    def nav_current(self):

        if self.navigation and self.nav_index > -1:
            return self.navigation[self.nav_index]
        alternative = self.get_home()
        if not alternative:
            alternative = self.random_node()
        return alternative

    """ 
    Cataloguing Nodes
    """

    def unindexed_nodes(self):
        """ 
        returns an array of node IDs of unindexed nodes, 
        in reverse order (most recent) by date 
        """

        unindexed_nodes = []
        for node_id in list(self.nodes):   
            if not self.nodes[node_id].metadata.get_first_value('index'):
                unindexed_nodes.append(node_id)
                
        sorted_unindexed_nodes = sorted(
            unindexed_nodes,
            key=lambda node_id: self.nodes[node_id].date,
            reverse=True)
        return sorted_unindexed_nodes

    def indexed_nodes(self):
        """ returns an array of node IDs of indexed nodes, in indexed order """

        indexed_nodes_list = []
        for node_id in list(self.nodes):
            index = self.nodes[node_id].metadata.get_first_value('index')
            if index:
                indexed_nodes_list.append([
                    node_id,
                    index
                ])
        sorted_indexed_nodes = sorted(indexed_nodes_list, key=lambda item: item[1])
        for index, node in enumerate(sorted_indexed_nodes):
            sorted_indexed_nodes[index] = node[0] 
        return sorted_indexed_nodes

    def all_nodes(self):
        all_nodes = self.indexed_nodes()
        all_nodes.extend(self.unindexed_nodes())
        return all_nodes

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
                    self._log_item('DEBUGGING (project.py): No root nodes in f>'+filename)
                else:
                    root_nodes.append(self.files[filename].root_nodes[0])
        return root_nodes
          
    def get_node_id_from_position(self, filename, position):

        filename = os.path.basename(filename)
        if filename in self.files:
            for node_id in self.files[filename].nodes:
                for r in self.files[filename].nodes[node_id].ranges:
                    if position in range(r[0],r[1]):
                        return node_id
        return None

    def get_links_to(self, to_id):
        """
        Returns the list of all nodes linking to the passed id
        """
        if to_id in self.links_to:
            return [i for i in self.links_to[to_id] if i in self.nodes]
        return []

    def get_links_from(self, from_id):
        """
        Returns the list of all nodes linking to the passed id
        """
        if from_id in self.links_from:
            return [i for i in self.links_from[from_id] if i in self.nodes]
        return []

    def get_link(self, string, position=0):
        """ 
        Given a line of text passed from an editor, 
        opens a web link, file, or returns a node,
        in that order. Returns a tuple of type and success/failure or node ID
        """
    
        link = None
    
        # start after cursor    
        link = self.find_link(string[position:])

        # then work backwards along the whole line
        if not link[0]:
            h = position
            while h > -1:
                link = self.find_link(string[h:])
                if link[0]:
                    break
                h -= 1

        
        if not link[0]:
            self._log_item('No node ID, web link, or file found on this line.')
            return None

        if link[0] == 'NODE' and link[1] not in self.nodes:
            self._log_item('Node ' + link[1] + ' is not in the project')
            return None

        return link

    def find_link(self, string):

        node_link_regex = re.compile('(\|?.*?[^f]>{1,2})(\w{3})(\:\d{1,10})?')
        editor_file_link_regex = re.compile('(f>{1,2})([^;]+)')
        url_scheme = re.compile('http[s]?:\/\/(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\), ]|(?:%[0-9a-fA-F][0-9a-fA-F]))+')

        kind = ''
        result = None
        link = ''
        position = 0
        result = re.search(node_link_regex, string)        
        link_location = None
        if result:
            kind = 'NODE'
            link_location = result.span()
            link = result.group(2) # node id
            if len(result.groups()) > 2:
                position = result.group(3) 
                if position:
                    position = int(position[1:])
                else:
                    position = 0
        else:
            result = re.search(editor_file_link_regex, string)            
            if result:
                kind='EDITOR_LINK'
                link = os.path.join(self.path, result.group(2))
            else:
                result = re.search(url_scheme, string)                
                if result:
                    kind ='HTTP'
                    link = result.group()

        
        return (kind, link, position, link_location)
             
    def build_collection(self):
        """ Returns a collection of context-aware metadata anchors """ 
        s = UrtextDynamicDefinition('')
        return self._collection([self.nodes[j] for j in self.nodes], s)

    def _is_duplicate_id(self, node_id, filename):
        """ private method to check if a node id is already in the project """
        if node_id in self.nodes:
            return self.nodes[node_id].filename
        return False

    def _log_item(self, item):
        if self.settings['console_log']:
            print(item)
        
    def timestamp(self, date):
        """ Given a datetime object, returns a timestamp in the format set in project_settings, or the default """

        if date.tzinfo == None:
            date = self.default_timezone.localize(date)    

        timestamp_format = '<' + self.settings['timestamp_format'] + '>'
        return date.strftime(timestamp_format)

    def get_log_node(self):
        return self.settings['log_id']

    def _get_settings_from(self, node):
        single_values = [
            'format_string',
            'home',
            'project_title',
            'google_auth_token',
            'google_calendar_id',
            'node_date_keyname',
            'log_id',
            'timestamp_format'
        ]
        single_boolean_values = [
            'always_oneline_meta',
            'preformat',
            'console_log',
            'atomic_rename',
        ]

        for entry in node.metadata._entries:
            key = entry.keyname
            values = entry.values
           
            if key == 'project_title':
                # this one sets a project object property, not the settings dict
                self.title = values[0]
                continue

            if key == 'numerical_keys':
                self.settings['numerical_keys'].extend(values)
                continue

            if key == 'filenames':
                #always a list
                self.settings['filenames'] = values
                continue

            if key in single_boolean_values:
                self.settings[key] = True if values[0].lower() == 'true' else False
                continue

            if key in single_values:
                self.settings[key] = values[0]
                continue

            if key not in self.settings:
                self.settings[key] = []                                

            self.settings[key].extend(values)

        self.default_timezone = timezone(self.settings['timezone'][0])

    def get_home(self):
        return self.settings['home']

    def next_index(self):
        index = random.choice(list(self._node_id_generator()))
        while ''.join(index) in self.nodes:
            index = random.choice(list(self._node_id_generator()))
        return ''.join(index)

    def pop_node(self, position=None, filename=None, node_id=None):
        """
        Pops a node asyncronously, making sure that if the file was saved and on_modified
        was called in the same calling function, this completes before evaluating
        the node_id from the position.

        Returns a future containing a list of modified files as the result.
        """
        #return self.executor.submit(self._pop_node, position=position, filename=filename, node_id=node_id)        
        return self._pop_node( position=position, filename=filename, node_id=node_id)

    def _pop_node(self, position=None, filename=None, node_id=None):
 
        if not node_id:
            node_id = self.get_node_id_from_position(filename, position)
 
        if not node_id:
            print('No node ID or duplicate Node ID')
            return None

        if self.nodes[node_id].root_node:
            print(node_id+ ' is already a root node.')
            return None

        start = self.nodes[node_id].ranges[0][0]
        end = self.nodes[node_id].ranges[-1][1]
        file_contents = self._full_file_contents(node_id=node_id)
        
        popped_node_id = node_id

        filename = self.nodes[node_id].filename

        popped_node_contents = file_contents[start:end].strip()

        # special case:
        # for popped nodes with trailing IDs, manually repopulate the node ID at file level.
        if self.nodes[node_id].trailing_node_id:
            popped_node_contents = popped_node_contents[:-3]
            popped_node_contents += 'id::'+node_id+'; '

        remaining_node_contents = ''.join([
            file_contents[0:start - 2],
            '\n| ',
            self.nodes[popped_node_id].title,
             ' >>',
            popped_node_id,
            '\n',
            file_contents[end + 2:]])
       
        with open (os.path.join(self.path, filename), 'w', encoding='utf-8') as f:
            f.write(remaining_node_contents)
        self._parse_file(filename) 

        # new file
        with open(os.path.join(self.path, popped_node_id+'.txt'), 'w',encoding='utf-8') as f:
            f.write(popped_node_contents)
        self._parse_file(popped_node_id+'.txt') 
        self._compile()  

    def pull_node(self, string, current_file, current_position):
        """ File must be saved in the editor first for this to work """
        if self.is_async:
            return self.executor.submit(self._pull_node, string, current_file, current_position) 
        else:
            self._pull_node(string, current_file, current_position)
    
    def _pull_node(self, string, current_file, current_position):

        link = self.get_link(string)
        
        if not link or link[0] != 'NODE': 
            return None
        
        node_id = link[1]
        if node_id not in self.nodes: 
            return None

        current_node = self.get_node_id_from_position(current_file, current_position)
        if not current_node:
            return None

        start = self.nodes[node_id].ranges[0][0]
        end = self.nodes[node_id].ranges[-1][1]
        
        contents =self._full_file_contents(filename=self.nodes[node_id].filename)
        replaced_file_contents = ''.join([contents[0:start],contents[end:len(contents)]])
        if self.nodes[node_id].root_node:
            self.delete_file(self.nodes[node_id].filename)  
        else:
            self._set_file_contents(self.nodes[node_id].filename, replaced_file_contents)
            self._parse_file(self.nodes[node_id].filename)
        pulled_contents = contents[start:end]
        full_current_contents = self._full_file_contents(current_file)

        # here we need to know the exact location of the returned link within the file
        span = link[3]
        replacement = string[span[0]:span[1]]
        wrapped_contents = ''.join(['{',pulled_contents,'}'])
        replacement_contents = full_current_contents.replace(replacement, wrapped_contents)
        self._set_file_contents(current_file, replacement_contents)
        self._parse_file(current_file)
        
        return self._compile()  

    def titles(self):
        title_list = {}
        for node_id in self.nodes:
            title_list[self.nodes[node_id].title] = (self.title, node_id)
        return title_list

    def complete_meta_value(self, fragment):
        fragment = fragment.lower().strip()
        length = len(fragment)

        for keyname in self.keynames:
            for value in keyname:
                if fragment == value[:length].lower():
                    return (keyname, value)
        return u''        

    def get_all_meta_pairs(self):
        pairs = []
        ignore = [ 'id' ]
        for k in self.keynames: 
            if k in ignore:
                continue
            for value in list(self.keynames[k]):
                meta_string = ''.join([k, '::', str(value) ])            
                pairs.append(meta_string)
        return list(set(pairs))

    def random_node(self):
        if self.nodes:
            node_id = random.choice(list(self.nodes))
            return node_id
    
    def replace_links(self, original_id, new_id='', new_project=''):
        if not new_id and not new_project:
            return None
        replacement = '>'+original_id
        if new_id:
            replacement = '>'+new_id
        if new_project:
            replacement = '{"'+new_project+'"}'+replacement
        patterns_to_replace = [
            r'\|.*?\s>{1,2}',   # replace title markers before anything else
            r'[^\}]>>',         # then node pointers
            r'[^\}]>' ]         # finally node links

        for filename in list(self.files):
            contents = self._full_file_contents(filename)
            new_contents = contents
            for pattern in patterns_to_replace:
                links = re.findall(pattern + original_id, new_contents)
                for link in links:
                    new_contents = new_contents.replace(link, replacement, 1)
            if contents != new_contents:
                self._set_file_contents(filename, new_contents)
                if self.is_async:
                    self.executor.submit(self._file_update, filename)
                else:
                    self._file_update(filename)
                    
    ## file modification 

    def on_modified(self, filename):
        """ 
        Main method to keep the project updated. 
        Should be called whenever file or directory content changes
        Returns a FULL PATH to the new filename if the filename changes by atomic rename
        """
        do_not_update = ['history','files']
        
        filename = os.path.basename(filename)
        if filename in do_not_update or '.git' in filename:
            return (True, '')
        self._log_item('MODIFIED f>' + filename +' - Updating the project object')
        if self.is_async:
            return self.executor.submit(self._file_update, filename)
        return self._file_update(filename)
    
    def _file_update(self, filename):
        
        rewritten_contents = self._rewrite_titles(filename)
        if rewritten_contents:
            self._set_file_contents(filename, rewritten_contents)
        self._parse_file(filename)
        full_filename = None
        # if self.settings['atomic_rename']:
        #     renamed = self._rename_file_nodes(filename)
        #     if os.path.join(self.path, filename) in renamed:
        #         full_filename = renamed[os.path.join(self.path, filename)]
        self._compile()
        """ returns filename with full path"""
        return full_filename

    def _check_for_new_files(self):
        filelist = os.listdir(self.path)
        new_files = []
        for file in filelist:
            if self._filter_filenames(file) == None:
                continue
            if os.path.basename(file) not in self.files:
                duplicate_node_ids = self._parse_file(file)
                if not duplicate_node_ids:
                    new_files.append(os.path.basename(file))
        for filename in list(self.files):
            if filename not in filelist:
                self._log_item(filename+' no longer seen in project path. Dropping it from the project.')
                self.remove_file(filename)
        return new_files

    def add_file(self, filename):
        """ 
        parse syncronously so we can raise an exception
        if moving files between projects.
        """
        any_duplicate_ids = self._parse_file(filename)
        
        if any_duplicate_ids:
            self._log_item('File moved but not added to destination project. Duplicate Nodes IDs shoudld be printed above.')
            raise DuplicateIDs()
        else:
            if self.is_async:
                return self.executor.submit(self._compile)
            else:
                self._compile()


    def remove_file(self, filename):
        if self.is_async:
            self.executor.submit(self._remove_file, os.path.basename(filename))
            return self.executor.submit(self._compile)
        else:
            self._remove_file(os.path.basename(filename))
            self._compile()
    
    def get_file_name(self, node_id, absolute=False):
        filename = None
        if node_id in self.nodes:
            filename = self.nodes[node_id].filename
        else:
            return None
        if absolute:
            filename = os.path.join(self.path, filename)
        return filename

    """
    File History
    """
    def snapshot_diff(self, filename, contents):
        dmp = dmp_module.diff_match_patch()
        filename = os.path.basename(filename)
        if filename not in self.files:
            return None
        now = int(time.time())
        history_file = filename.replace('.txt','.pkl')
        file_history = self.get_history(filename)
        if not file_history:
            file_history = {}
            file_history[now] = contents
            with open( os.path.join(self.path, 'history', history_file), "wb") as f:
                pickle.dump(file_history, f )
            return
        else:

            latest_history = self.apply_patches(file_history)
            if contents != latest_history:
                file_history[now] = dmp.patch_make(latest_history, contents)
                with open( os.path.join(self.path, 'history', history_file), "wb") as f:
                    pickle.dump(file_history, f )

    def apply_patches(self, history, distance_back=0):
        dmp = dmp_module.diff_match_patch()
        timestamps = sorted(history.keys())
        original = history[timestamps[0]]
        for index in range(1,len(timestamps)-distance_back):
            next_patch = history[timestamps[index]]
            original = dmp.patch_apply(next_patch, original)[0]

        return original

    def get_version(self, filename, distance_back=0):
        history = self.get_history(filename)
        version = self.apply_patches(history, distance_back)
       
        return version

    def get_history(self, filename):
        filename = os.path.basename(filename)
        history_file = os.path.join(self.path, 'history', filename.replace('.txt','.pkl'))
        if os.path.exists(history_file):
            with open(history_file, "rb") as f:
                file_history = pickle.load(f)
            return file_history
        return None

    def most_recent_history(self, history):
        times = sorted(history.keys())
        return times[-1]

    """
    Access History
    """

    def _get_access_history(self):

        accessed_file = os.path.join(self.path, "history", "URTEXT_accessed.json")
        if os.path.exists(accessed_file):
            with open(accessed_file,"r") as f:
                try:
                    contents = f.read()
                    if contents:
                        try:
                            access_history = json.loads(contents)
                            self.access_history = convert_dict_values_to_int(access_history)
                        except:
                            print('Could not parse access history for '+accessed_file)
                            print(contents)
                except EOFError as error:
                    print(error)
         
        self._propagate_access_history()    

    def _propagate_access_history(self):

        for node_id, access_time in self.access_history.items():
            if node_id in self.nodes:
                self.nodes[node_id].last_accessed = access_time

    def _save_access_history(self):

        accessed_file = os.path.join(self.path, "history", "URTEXT_accessed.json")

        with open(accessed_file,"w") as f:
            f.write(json.dumps(self.access_history))
    
    def _push_access_history(self, node_id, duplicate=False):
        if node_id not in self.nodes: return
        access_time = int(time.time()) # UNIX timestamp
        self.nodes[node_id].last_accessed = access_time
        self.access_history[node_id] = access_time
        self._save_access_history()

    def get_first_value(self, node, keyname):
        value = node.metadata.get_first_value(keyname)
        if keyname in self.settings['numerical_keys']:
            try:
                value = float(value)
            except ValueError:
                return 0
        return value

    def get_by_meta(self, key, values, operator):
        
        if isinstance(values,str):
            values = [values]

        results = []

        if key == '_contents' and operator == '?': # `=` not currently implemented
            for node_id in self.nodes:
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
                if v in self.links_to:
                    results.extend(self.links_to[v])
            return results

        if key == '_links_from':
            for v in values:
                if v in self.links_from:
                    results.extend(self.links_from[v])
            return results

        results = set([])

        for value in values:
            if value in ['*']:
                results = results.union(set(n for n in self.nodes if self.nodes[n].metadata.get_values(key))) 
                continue
            
            if isinstance(value, str) and key not in self.settings['case_sensitive']:
                value = value.lower() # all comparisons case insensitive

            if key in self.settings['numerical_keys']:
                try:
                    value = float(value)
                except ValueError:
                    value = 99999999
                    continue
           
            results = results.union(set(n for n in self.nodes if value in self.nodes[n].metadata.get_values(key)))

        return results

    """
    Export
    """
    def is_in_export(self, filename, position):

        node_id = self.get_node_id_from_position(filename, position)
        if not node_id:
            return False
        for export_range in self.nodes[node_id].export_points:
            if position in range(export_range[0],export_range[1]):
                # returns tuple (id, starting_position)
                return self.nodes[node_id].export_points[export_range]
        return False

    def get_file_and_position(self, node_id):
        if node_id in self.nodes:
            filename = self.get_file_name(node_id, absolute=True)
            position = self.nodes[node_id].start_position()
            return filename, position
        return None, None

    """
    FUTURE : Calendar
    """
    def export_to_ics(self):
        c = Calendar()
        for node_id in self.nodes:
            e = Event()
            urtext_node = self.nodes[node_id]
            e.name = urtext_node.title
            e.begin = urtext_node.date.isoformat()
            c.add(e)
        with open('my.ics', 'w') as f:
            f.write(c)

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

def convert_dict_values_to_int(old_dict):
    new_dict = {}
    for key, value in old_dict.items():
        new_dict[key] = int(value)
    return new_dict

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
