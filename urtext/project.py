import re
import datetime
import platform
import os
import random
import time
import concurrent.futures
import threading
from urtext.file import UrtextFile, UrtextBuffer
from urtext.node import UrtextNode
from urtext.timestamp import date_from_timestamp, default_date, UrtextTimestamp
from urtext.directive import UrtextDirective
import urtext.syntax as syntax
import urtext.utils as utils
from urtext.exec import Exec


class UrtextProject:
    urtext_file = UrtextFile
    urtext_node = UrtextNode
    urtext_buffer = UrtextBuffer

    def __init__(self,
                 entry_point,
                 project_list=None,
                 editor_methods=None,
                 new_file_node_created=False):

        if editor_methods is None:
            editor_methods = {}
        self.project_list = project_list
        self.entry_point = entry_point
        self.entry_path = None
        self.project_title = self.entry_point  # default
        self.editor_methods = editor_methods
        self.is_async = None
        self.time = time.time()
        self.last_compile_time = 0
        self.nodes = {}
        self.project_settings_nodes = []
        self.files = {}
        self.paths = []
        self.messages = {}
        self.dynamic_definitions = {}
        self.virtual_outputs = {}
        self.dynamic_metadata_entries = []
        self.directives = {}
        self.project_instance_directives = {}
        self.initialized = False
        self.compiled = False
        self.executor = None
        self.excluded_files = []
        self.home_requested = False
        self.running_on_modified = None
        self.new_file_node_created = new_file_node_created

    def get_setting(self, setting, _from_project_list=False):

        values = []
        is_text = True
        if 'project_settings' in self.nodes:
            values = self.nodes['project_settings'].metadata.get_values(setting)
        if not values and not _from_project_list:
            return self.project_list.get_setting(setting, self)
        if values and values[0].is_node:
            return values
        if setting in ['boolean_settings', 'single_values_settings', 'numerical_settings']:
            return [v.text for v in values]
        if setting in self.get_setting('boolean_settings', _from_project_list=_from_project_list):
            values = [v.true() for v in values]
            is_text = False
        elif setting in self.get_setting('numerical_settings', _from_project_list=_from_project_list):
            values = [v.num() for v in values]
            is_text = False
        single_values_settings = self.get_setting('single_values_settings', _from_project_list=_from_project_list)
        if values and not is_text:
            if setting in single_values_settings:
                return values[0]
        if setting in single_values_settings:
            return values[0].text
        return [v.text for v in values]

    def get_settings_keys(self):
        keys = []
        for n in self.project_settings_nodes:
            keys.extend(n.metadata.get_keys())
        return keys

    def get_propagated_settings(self, _from_project_list=False):
        propagated_settings = self.get_setting('propagate_settings', _from_project_list=_from_project_list)
        if '_all' in propagated_settings:
            return self.get_settings_keys()
        return propagated_settings

    def initialize(self, callback=None):
        self.add_directive(Exec)
        for directive in self.project_list.directives.values():
            self.add_directive(directive)
        for directive in self.project_list.project_instance_directives.values():
            self.add_directive(directive)

        num_file_extensions = len(self.get_setting('file_extensions'))
        if os.path.exists(self.entry_point):
            if os.path.isdir(self.entry_point) and (
                    self._approve_new_path(self.entry_point)):
                self.entry_path = self.entry_point
            elif self._include_file(self.entry_point):
                self._parse_file(self.entry_point)
                if self._approve_new_path(os.path.dirname(self.entry_point)):
                    self.entry_path = os.path.dirname(self.entry_point)
            if self.entry_path:
                self.paths.append(self.entry_path)
            for file in self._get_included_files():
                self._parse_file(file)
        else:
            self.handle_error_message('Project path does not exist: %s' % self.entry_point)
            return False

        for p in self.get_settings_paths():
            if p not in self.paths:
                if not self._approve_new_path(p):
                    print(p, 'NOT ADDED (debugging)')
                else:
                    self.paths.append(p)
                    for file in self._get_included_files():
                        if file not in self.files:
                            self._parse_file(file)
                                
        num_paths = len(self.get_settings_paths())
        while len(self.get_settings_paths()) > num_paths or (
                len(self.get_setting('file_extensions')) > num_file_extensions):
            num_paths = len(self.get_settings_paths())
            num_file_extensions = len(self.get_setting('file_extensions'))
            for p in self.get_settings_paths():
                if p not in self.paths and self._approve_new_path(p):
                    self.paths.append(p)
                    for file in self._get_included_files():
                        if file not in self.files:
                            self._parse_file(file)

        if len(self.nodes) == 0 and not self.new_file_node_created:
            return False

        for node in self.nodes.values():
            node.metadata.convert_hash_keys()
            node.metadata.convert_node_links()
        self._add_all_sub_tags()
        self._mark_dynamic_nodes()
        self.run_hook('after_project_initialized')

        other_entry_points = self.get_setting('other_entry_points')
        if other_entry_points:
            for path_link in other_entry_points:
                self.project_list._add_project(utils.get_path_from_link(path_link))
        self.initialized = True
        callback(self)

    def _approve_new_path(self, path):
        if path in self.project_list.get_all_paths():
            self.log_item('system', "%s is already in another project." % path)
            return False
        return True

    def _parse_file(self, filename, try_buffer=False, passed_contents=None):
        if self._filter_filenames(filename) is None:
            self._add_to_excluded_files(filename)
            return False

        buffer = None
        if self.compiled and not passed_contents and try_buffer:
            buffer_contents = self.run_editor_method(
                'get_buffer',
                filename)
            if buffer_contents:
                buffer = self._make_buffer(filename, buffer_contents)
        elif passed_contents:
            buffer = self._make_buffer(filename, passed_contents)
        else:
            buffer = self.urtext_file(filename, self)
        return self._parse_buffer(buffer)

    def _parse_buffer(self, buffer):

        existing_buffer_ids = []
        if buffer.filename in self.files:
            existing_buffer_ids = [n.id for n in self.files[buffer.filename].get_ordered_nodes()]

        self.drop_buffer(buffer)

        self._check_buffer_for_duplicates(buffer)
        if not buffer.root_node:
            buffer.write_buffer_messages()
            self.log_item(buffer.filename, '%s has no root node, dropping' % buffer.filename)
            return False

        self.messages[buffer.filename] = buffer.messages
        if buffer.has_errors:
            buffer.write_buffer_messages()
            self._check_buffer_for_duplicates(buffer)
        changed_ids = {}
        if existing_buffer_ids:
            new_node_ids = [n.id for n in buffer.get_ordered_nodes()]
            if len(existing_buffer_ids) == len(new_node_ids):
                for index in range(0, len(existing_buffer_ids)):  # existing links are all we care about
                    if existing_buffer_ids[index] == new_node_ids[index]:
                        continue  # id stayed the same
                    else:
                        if new_node_ids[index] in existing_buffer_ids:
                            # proably only the order changed.
                            # don't have to do anything
                            continue
                        else:
                            # check each new id for similarity to the old one
                            changed_ids[existing_buffer_ids[index]] = new_node_ids[index]
                            # else:
                            # TODO try to map old to new.
        for node in buffer.nodes:
            if node.id == '(untitled)':
                print('(DEBUGGING) - should not happen, untitled node', buffer.filename)

        for node in buffer.nodes:
            self._add_node(node)

        self.files[buffer.filename] = buffer
        self.run_hook('on_buffer_added', buffer)

        for entry in buffer.meta_to_node:
            keyname = entry.group(1)
            source_node = self.get_node_id_from_position(
                buffer.filename,
                entry.span()[0])
            target_node = self.get_node_id_from_position(
                buffer.filename,
                entry.span()[1] + 1)
            if source_node and target_node:
                self.nodes[source_node].metadata.add_entry(
                    keyname,
                    [self.nodes[target_node]],
                    self.nodes[source_node],
                    start_position=self.nodes[target_node].start_position,
                    end_position=self.nodes[target_node].end_position,
                    is_node=True)
                self.nodes[target_node].is_meta = True
                self.nodes[target_node].meta_key = keyname
        for node in buffer.nodes:
            for dd in node.dynamic_definitions:
                dd.source_node = node
                self._add_dynamic_definition(dd)

            for entry in node.metadata.entries():
                entry.from_node = node
                if entry.tag_children:
                    self._add_sub_tags(entry)
                    self.dynamic_metadata_entries.append(entry)

        if self.compiled and changed_ids:
            for old_node_id in changed_ids:
                self.run_hook('on_node_id_changed',
                            old_node_id, # old id
                            changed_ids[old_node_id], # new id
                            ) 
            self._rewrite_changed_links(changed_ids)
        self._mark_dynamic_nodes()
        return buffer

    def _verify_links_globally(self):
        links = self.get_all_links()
        for filename in links:
            self._reverify_links(filename)

    def _reverify_links(self, filename):
        if filename in self.files:
            contents = self.files[filename]._get_contents()
            for node in [n for n in self.files[filename].nodes if not n.dynamic]:
                rewrites = {}
                for link in node.links:
                    if link.is_file or not link.node_id or link.project_name:
                        continue
                    node_id = link.node_id
                    suffix = ' >>' if link.is_pointer else ' >'
                    if node_id not in self.nodes:
                        title_only = node_id.split(syntax.resolution_identifier)[0]
                        if title_only not in self.nodes and link.node_id not in rewrites:
                            rewrites[link] = ''.join([
                                syntax.missing_link_opening_wrapper,
                                title_only,
                                suffix])
                    elif link.is_missing and link not in rewrites:  # node marked missing but is there
                        rewrites[link] = ''.join([
                            syntax.link_opening_wrapper,
                            link.node_id,
                            suffix])
                if rewrites:
                    for old_link in rewrites:
                        contents = contents.replace(old_link.matching_string, rewrites[old_link])
            return contents

    def _add_all_sub_tags(self):
        for entry in self.dynamic_metadata_entries:
            self._add_sub_tags(entry)

    def _rewrite_changed_links(self, changed_ids):
        for old_id in list(changed_ids.keys()):
            new_id = changed_ids[old_id]
            if new_id in self.nodes:
                for project_node in [n for n in self.nodes.values() if not n.dynamic]:
                    if project_node.id not in self.nodes:
                        continue
                    links_to_change = {}
                    for link in project_node.links:
                        node_id = link.node_id
                        if node_id == old_id:
                            links_to_change[node_id] = new_id
                    if links_to_change:
                        contents = self.files[project_node.filename]._get_contents()
                        for node_id in list(links_to_change.keys()):
                            replaced_contents = contents
                            node_id_regex = re.escape(node_id)
                            replaced_contents = re.sub(''.join([
                                    syntax.node_link_opening_wrapper_match,
                                    node_id_regex,
                                    syntax.link_closing_wrapper
                                    ]),
                                utils.make_node_link(links_to_change[node_id]), replaced_contents)
                            self.files[project_node.filename].set_buffer_contents(replaced_contents)

    def _check_buffer_for_duplicates(self, buffer):
        messages = []
        changed_ids = {}
        allocated_ids = []

        for node in list([n for n in buffer.nodes if n.title == '(untitled)']):
            resolution = node.resolve_id(allocated_ids=allocated_ids)
            if not resolution['resolved_id']:
                message = {
                    'top_message': ''.join([
                                'Dropping (untitled) ID at position ',
                                str(node.start_position),
                                '. ',
                                resolution['reason'],
                                ' ',
                            ]),
                    'position_message': 'Dropped (untitled, cannot resolve)',
                    'position' : node.start_position
                    }
                self.log_item(buffer.filename, message)
                messages.append(message)
                buffer.nodes.remove(node)
                del node
                continue
            else:
                node.id = resolution['resolved_id']
                changed_ids[node.id] = resolution['resolved_id']
                allocated_ids.append(node.id)

        # resolve duplicate titles within file/buffer
        new_file_node_ids = [file_node.id for file_node in buffer.nodes]
        nodes_to_resolve = [n for n in buffer.nodes if new_file_node_ids.count(n.id) > 1]
        allocated_ids.extend([file_node.id for file_node in buffer.nodes])
        for n in nodes_to_resolve:
            resolution = n.resolve_id(allocated_ids=allocated_ids)
            if not resolution['resolved_id'] or n.id in changed_ids:
                message = {
                    'top_message' :''.join([
                                'Dropping duplicate node title "',
                                n.title,
                                '"',
                                ' at position ',
                                str(n.start_position),
                                '; duplicated in the same file.'
                            ]),
                    'position_message': 'Dropped (duplicate title in file)',
                    'position': n.start_position
                    }

                self.log_item(buffer.filename, message)
                messages.append(message)
                buffer.nodes.remove(n)
                del n
                continue
            changed_ids[n.id] = resolution['resolved_id']
            n.id = resolution['resolved_id']

        # resolve duplicate titles in project
        new_file_node_ids = [file_node.id for file_node in buffer.nodes]
        allocated_ids = [n for n in self.nodes if n not in new_file_node_ids]
        for node in buffer.get_ordered_nodes():
            duplicate_titled_node = self._find_duplicate_title(node)
            if duplicate_titled_node:
                resolution = node.resolve_id(
                    allocated_ids=allocated_ids)
                if not resolution['resolved_id']:
                    message = {
                        'top_message' : ''.join([
                                'Dropping duplicate node ID "',
                                node.id,
                                '"',
                                ' already exists in file ',
                                syntax.file_link_opening_wrapper,
                                duplicate_titled_node.filename,
                                syntax.link_closing_wrapper,
                            ]),
                        'position_message': 'Dropped (node ID already exists in file)',
                        'position': node.id.start_position,
                    }
                    buffer.nodes.remove(node)
                    del node
                    self.log_item(buffer.filename, message)
                    messages.append(message)
                    continue
                changed_ids[node.id] = resolution['resolved_id']
                node.id = resolution['resolved_id']

        if messages:
            buffer.messages = messages
            buffer.has_errors = True

        return changed_ids

    def _add_dynamic_definition(self, definition):
        for target_id in definition.target_ids:
            if target_id in self.dynamic_definitions:
                pass
                # self._reject_definition(target_id, definition)
            else:
                self.dynamic_definitions[target_id] = definition

        for target in definition.targets:
            if target in self.nodes:  # allow not using link syntax
                if target in self.dynamic_definitions:
                    self._reject_definition(target, definition)
                else:
                    self.dynamic_definitions[target] = definition
                    continue
            virtual_target = syntax.virtual_target_match_c.match(target)
            if virtual_target:
                target = virtual_target.group()
                if target == "@self":
                    if definition.source_node.id in self.dynamic_definitions:
                        self._reject_definition(definition.source_node.id, definition)
                    else:
                        self.dynamic_definitions[definition.source_node.id] = definition
                else:
                    self.virtual_outputs.setdefault(target, [])
                    self.virtual_outputs[target].append(definition)

    def _reject_definition(self, target_id, definition):
        message = ''.join([
            '\nDynamic node ',
            utils.make_node_link(target_id),
            '\nalready has a definition in ',
            self.dynamic_definitions[target_id].source_node.link(),
            '\n in file ',
            syntax.file_link_opening_wrapper,
            self.dynamic_definitions[target_id].source_node.filename,
            syntax.link_closing_wrapper,
            '\nskipping the definition in ',
            definition.source_node.link(),
        ])
        self.log_item(
            self.nodes[definition.source_node.id].filename,
            message)

    def _add_node(self, new_node):
        new_node.project = self
        self.nodes[new_node.id] = new_node
        if self.compiled:
            new_node.metadata.convert_node_links()
        if new_node.title == 'project_settings':
            self.project_settings_nodes.append(new_node)
        self.run_hook('on_node_added', new_node)

    def get_source_node(self, filename, position):  # future
        if filename not in self.files:
            return None, None
        exported_node_id = self.get_node_id_from_position(filename, position)
        points = self.nodes[exported_node_id].export_points
        if not points:
            return None, None

        indexes = sorted(points)
        for index in range(0, len(indexes)):
            if indexes[index] <= position < indexes[index + 1]:
                node, target_position = self.nodes[exported_node_id].export_points[indexes[index]]
                offset = position - indexes[index]
                return node, target_position + offset

    def _set_node_contents(self, node_id, contents, preserve_title=False):
        """ 
        project-aware alias for the Node _set_contents() method 
        parses the file before and after;
        returns filename if contents changed.
        """
        if node_id in self.nodes:
            self._parse_buffer(self.nodes[node_id].file)
            if node_id in self.nodes:
                if self.nodes[node_id]._set_contents(
                        contents,
                        preserve_title=preserve_title):
                    if node_id in self.nodes:
                        return self.nodes[node_id].filename
        return False

    def _mark_dynamic_nodes(self):
        for target in self.dynamic_definitions:
            if target in self.nodes:
                self.nodes[target].dynamic = True

    """
    Removing and renaming files
    """

    def drop_file(self, filename):
        if filename in self.files:
            self.drop_buffer(self.files[filename])

    def drop_buffer(self, buffer):
        self.run_hook('on_buffer_dropped', buffer.filename)
        for node in list(buffer.nodes):
            self._drop_node(node)
        if buffer.filename in self.files:
            del self.files[buffer.filename]
        if buffer.filename in self.messages:
            self.messages[buffer.filename] = []

    def _drop_node(self, node):
        if node.id in self.nodes:  # might not be if it's an incompletely parsed buffer
            self._remove_sub_tags(node.id)
            self._remove_dynamic_defs(node.id)
            self._remove_dynamic_metadata_entries(node.id)
            if node in self.project_settings_nodes:
                self.project_settings_nodes.remove(node)
            del self.nodes[node.id]

    def delete_file(self, filename):
        """
        Deletes a file, removes it from the project,
        """
        self.run_editor_method('close_file', filename)
        self.drop_file(filename)
        os.remove(filename)
        if filename in self.messages:
            del self.messages[filename]
        self.run_hook('on_file_deleted', filename)

    def _handle_renamed(self, old_filename, new_filename):
        if new_filename != old_filename:
            self.files[new_filename] = self.files[old_filename]
            for node in self.files[new_filename].nodes:
                self.nodes[node.id].filename = new_filename
                self.files[new_filename].filename = new_filename
            del self.files[old_filename]
            self.run_hook(
                'on_file_renamed',
                old_filename,
                new_filename)

    def _filter_filenames(self, filename):
        if filename in ['urtext_files', '.git']:
            return None
        if filename in self.get_setting('exclude_files'):
            return None
        return filename

    def new_file_node(self,
                      path=None,
                      contents=None,
                      metadata=None,
                      open_file=True):

        contents_format = None
        if contents is None:
            contents_format = bytes(
                self.get_setting('new_file_node_format'),
                "utf-8"
            ).decode("unicode_escape")
        if metadata is None:
            metadata = {}
        filename = datetime.datetime.now().strftime('%Y-%m-%d %H-%M-%S')

        new_node_contents, node_id, cursor_pos = self._new_node(
            contents=contents,
            contents_format=contents_format,
            metadata=metadata)

        filename += '.urtext'
        if path:
            filename = os.path.join(path, filename)
        else:
            filename = os.path.join(self.entry_path, filename)

        if os.path.isfile(filename):
            suffix = 2
            resolved_filename = filename
            while os.path.isfile(resolved_filename):
                resolved_filename = filename.replace('.urtext', ' (dup name %s).urtext' % str(suffix))
                suffix += 1
            filename = resolved_filename

        utils.write_file_contents(filename, new_node_contents)
        new_file = self.urtext_file(filename, self)

        self._check_buffer_for_duplicates(new_file)
        if new_file.has_errors and 'timestamp or parent title exists in another node' in new_file.messages[0]:
            if contents is None:
                new_node_contents, node_id, cursor_pos = self._new_node(
                    contents=contents,
                    add_seconds_to_timestamp=True,
                    contents_format=contents_format,
                    metadata=metadata)
            utils.write_file_contents(filename, new_node_contents)
            new_file = self.urtext_file(filename, self)
            self._check_buffer_for_duplicates(new_file)

        self._parse_file(filename)

        if filename in self.files:
            # TODO possibly should be sent in a thread:
            self.run_hook('on_new_file_node',
                          self.files[filename].root_node.id)

            if open_file:
                self.open_node(self.files[filename].root_node.id,
                               position=cursor_pos)

            return {
                'filename': filename,
                'root_node': self.files[filename].root_node,
                'id': self.files[filename].root_node.id,
                'cursor_pos': cursor_pos
            }

    def new_inline_node(self,
                        metadata=None,
                        contents=''):

        if metadata is None:
            metadata = {}
        contents_format = None
        new_node_contents, title, cursor_pos = self._new_node(
            contents=contents,
            contents_format=contents_format,
            metadata=metadata)

        return {
            'contents': ''.join(['{', new_node_contents, '}']),
            'cursor_pos': cursor_pos
        }

    def _new_node(self,
                  contents=None,
                  title='',
                  contents_format=None,
                  add_seconds_to_timestamp=False,
                  metadata=None,
                  one_line=None):

        cursor_pos = 0
        if contents is None:
            contents = ''

        if contents_format:
            new_node_contents = contents_format.replace(
                '$timestamp',
                self.timestamp(add_seconds=add_seconds_to_timestamp).wrapped_string)
            new_node_contents = new_node_contents.replace(
                '$device_keyname',
                platform.node())
            if '$cursor' in new_node_contents:
                new_node_contents = new_node_contents.split('$cursor')
                cursor_pos = len(new_node_contents[0]) - 1
                new_node_contents = title + ''.join(new_node_contents)
                if cursor_pos < len(new_node_contents) - 1:
                    new_node_contents += ' '
        else:
            if one_line is None:
                one_line = self.get_setting('always_oneline_meta')

            if not metadata:
                metadata = {}

            if self.get_setting('device_keyname'):
                metadata[self.get_setting('device_keyname')] = platform.node()

            new_node_contents = contents
            new_node_contents += self.urtext_node.build_metadata(metadata, one_line=one_line)

        return new_node_contents, title, cursor_pos

    def add_compact_node(self,
                         contents='',
                         metadata=None):
        if metadata is None:
            metadata = {}
        metadata_block = self.urtext_node.build_metadata(metadata, one_line=True)
        if metadata_block:
            metadata_block = ' ' + metadata_block
        return '• ' + contents.strip() + metadata_block

    def __get_dynamic_defs(self,
                           target_node=None,
                           source_node=None,
                           flags=None,
                           has_not_run=False):

        defs = []
        if target_node and target_node.id in self.dynamic_definitions:
            defs.append(self.dynamic_definitions[target_node.id])
        if source_node:
            for dd in self.dynamic_definitions.values():
                if dd.source_node.id == source_node.id:
                    defs.append(dd)
        for target in self.virtual_outputs:
            for dd in self.virtual_outputs[target]:
                if source_node and dd.source_node.id == source_node.id:
                    defs.append(dd)
                elif not source_node:
                    defs.append(dd)
        if flags:
            if not isinstance(flags, list):
                flags = [flags]
            for f in flags:
                for dd in self.dynamic_definitions.values():
                    if dd.have_flags(f) and dd not in defs:
                        defs.append(dd)
        if has_not_run:
            for dd in self.dynamic_definitions.values():
                if not dd.ran:
                    defs.append(dd)
        return defs

    def _remove_dynamic_defs(self, node_id):
        for target in list(self.dynamic_definitions):
            if self.dynamic_definitions[target].source_node.id == node_id:
                del self.dynamic_definitions[target]
        for target in self.virtual_outputs:
            for dd in self.virtual_outputs[target]:
                if dd.source_node.id == node_id:
                    self.virtual_outputs[target].remove(dd)

    def _remove_dynamic_metadata_entries(self, node_id):
        for entry in list(self.dynamic_metadata_entries):
            if entry.from_node == self.nodes[node_id]:
                self.dynamic_metadata_entries.remove(entry)

    def open_node(self, node_id, position=None):
        if node_id not in self.nodes:
            if self.compiled:
                message = node_id + ' not in current project'
            else:
                message = 'Project is still compiling'
            self.handle_info_message(message)
            return False

        node_range = (
            self.nodes[node_id].ranges[0][0],
            self.nodes[node_id].ranges[-1][1])

        if position is None:
            position = self.nodes[node_id].start_position

        self.run_editor_method(
            'open_file_to_position',
            self.nodes[node_id].filename,
            position,
            node_range=node_range
        )
        return self.visit_node(node_id)

    def open_home(self):
        if not self.get_home():
            if not self.compiled:
                if not self.home_requested:
                    self.handle_info_message('Project is compiling. Home will be shown when found.')
                    self.home_requested = True
                timer = threading.Timer(.5, self.open_home)
                timer.start()
                return timer
            else:
                self.home_requested = False
                self.handle_info_message(
                    'No home node for this project')
                return False
        self.home_requested = False
        self.open_node(self.get_setting('home'))
        return True

    def handle_info_message(self, message):
        print(message)
        self.run_editor_method('popup', message)

    def handle_error_message(self, message):
        print(message)
        self.run_editor_method('error_message', message)

    def sort_for_node_browser(self, nodes=None, as_nodes=False):
        if not nodes:
            nodes = list(self.nodes.values())
        return self._sort_nodes(
            nodes,
            self.get_setting('node_browser_sort'),
            as_nodes=as_nodes)

    def sort_for_meta_browser(self, nodes, as_nodes=False):
        meta_browser_key = self.get_setting('meta_browser_key')
        if meta_browser_key:
            nodes = [n for n in nodes if n.metadata.get_first_value(meta_browser_key)]
            return self._sort_nodes(
                nodes,
                [meta_browser_key],
                as_nodes=as_nodes)
        return self._sort_nodes(
            nodes,
            self.get_setting('meta_browser_sort'),
            as_nodes=as_nodes)

    def _sort_nodes(self, nodes, keys, as_nodes=False):
        remaining_nodes = nodes
        sorted_nodes = []
        for k in keys:
            use_timestamp = k in self.get_setting('use_timestamp')
            node_group = [r for r in remaining_nodes if r.metadata.get_first_value(k) is not None]
            remaining_nodes = [r for r in remaining_nodes if r not in node_group]
            if node_group:
                if use_timestamp:
                    node_group = sorted(
                        node_group,
                        key=lambda node: node.metadata.get_first_value(k).timestamp if node.metadata.get_first_value(
                            k) else None,
                        reverse=True)
                else:
                    node_group = sorted(
                        node_group,
                        key=lambda n: n.metadata.get_first_value(k))
                for node in node_group:
                    detail_key = self.get_setting('node_browser_detail')
                    if not detail_key:
                        detail_key = k
                    detail = node.metadata.get_first_value(detail_key)
                    if detail:
                        if detail_key in self.get_setting('use_timestamp'):
                            detail = detail.timestamp.wrapped_string
                        else:
                            detail = detail.text
                    else:
                        detail = ''
                    node.display_detail = detail
                sorted_nodes.extend(node_group)
        sorted_nodes.extend([r for r in remaining_nodes if r not in sorted_nodes])
        if not as_nodes:
            return [n.id for n in sorted_nodes]
        return sorted_nodes

    def get_node_id_from_position(self, filename, position):
        if filename in self.files:
            return self.files[filename].get_node_id_from_position(position)

    def get_links_to(self, to_id, as_nodes=False, include_dynamic=True):
        links_to = [n for n in self.nodes.values() if to_id in n.links_ids()]
        if not include_dynamic:
            links_to = [n for n in links_to if not n.dynamic]
        if not as_nodes:
            return [n.id for n in links_to]
        return links_to

    def get_links_from(self, from_id, as_nodes=False, include_dynamic=True):
        if from_id in self.nodes:
            links = self.nodes[from_id].links_ids()
            links_from = [l for l in links if l in self.nodes]
            if not include_dynamic:
                links_from = [link for link in links_from if not self.nodes[link].dynamic]
            if as_nodes:
                return [self.nodes[n] for n in links_from]
            return links_from
        return []

    def get_all_links(self):
        links = {}
        for node in self.nodes.values():
            links[node.filename] = links.get(node.filename, [])
            links[node.filename].extend(node.links)
        return links

    def handle_link(self, link):

        if link.is_node and link.node_id in self.nodes:
            if link.is_action:
                for dd in self.__get_dynamic_defs(source_node=self.nodes[link.node_id]):
                    if dd.source_node.id == link.node_id:
                        output = dd.process(flags=['-link_clicked'])
                        if output not in [False, None]:
                            for target in dd.targets:
                                target_output = dd.preserve_title_if_present(target) + output
                                self._direct_output(target_output, target, dd)
            else:
                return self.open_node(
                    link.node_id,
                    position=self.nodes[link.node_id].start_position + link.dest_node_position)

        elif link.is_node:
            return self.project_list.handle_link_using_all_projects(link)
           
        return link

    def _is_duplicate_id(self, node_id):
        return node_id in self.nodes

    def _find_duplicate_title(self, node):
        for n in list(self.nodes):
            if n.title == node.title:
                return node

    def log_item(self, filename, message):
        self.messages.setdefault(filename, [])
        if message not in self.messages[filename]:
            self.messages[filename].append(message)
        if self.get_setting('console_log'):
            print(str(filename) + ' : ' + message)

    def timestamp(self, date=None, as_string=False, add_seconds=False):
        """ 
        Returns a timestamp in the format set in project_settings, or the default 
        """
        if date is None:
            date = datetime.datetime.now(
                datetime.timezone.utc
            ).astimezone()
        ts_format = self.get_setting('timestamp_format')
        if add_seconds:
            if '%' in ts_format and '%S' not in ts_format:
                ts_format = ts_format.replace('%M', '%M:%S')
        if as_string:
            return ''.join([
                syntax.timestamp_opening_wrapper,
                date.strftime(ts_format),
                syntax.timestamp_closing_wrapper,
            ])

        return UrtextTimestamp(
            date.strftime(ts_format))

    def get_home(self):
        home_node_id = self.get_setting('home')
        if home_node_id in self.nodes:
            return home_node_id

    def get_all_meta_pairs(self):
        pairs = []
        for n in self.nodes.values():
            for k in n.metadata.get_keys().keys():
                values = n.metadata.get_values(k)
                assigner = syntax.metadata_assignment_operator
                if k == self.get_setting('hash_key'):
                    k = '#'
                    assigner = ''
                for v in values:
                    if v.is_node:
                        pairs.append(utils.make_node_link(v.id))
                    else:
                        pairs.append(''.join([
                            k,
                            assigner,
                            v.text,  # num would need to be converted to text anyway
                        ]))

        return list(set(pairs))

    def random_node(self):
        if self.nodes:
            node_id = random.choice(list(self.nodes))
            self.open_node(node_id)
        return None

    def on_modified(self, filename, flags=[]):
        if self.compiled and filename in self._get_included_files():
            if self.running_on_modified == filename:
                print('(debugging) already visiting', filename)
                return
            self.running_on_modified = filename
            file_obj = self._parse_file(filename)
            if file_obj:
                self._compile_file(
                    filename,
                    flags=['-file_update'].extend(flags))
                file_obj.set_buffer_contents(self._reverify_links(filename))
                file_obj.write_file_contents(file_obj.contents, run_hook=True)
                self._sync_file_list()
                if filename in self.files:
                    self.run_hook('after_on_file_modified', filename)
        self.running_on_modified = None

    def visit_node(self, node_id):
        if self.compiled:
            filename = self.nodes[node_id].filename
            self.run_hook('on_node_visited', node_id)
            self.visit_file(filename)
            self.run_editor_method('status_message',
                                   ''.join([
                                       self.title(),
                                       ' (compiled)']))

    def visit_file(self, filename):
        if filename in self.files and self.compiled:
            self.on_modified(filename, flags=['-file_visited'])

    def _sync_file_list(self):
        included_files = self._get_included_files()
        for filename in included_files:
            if filename not in self.files:
                self._parse_file(filename)
        for filename in [f for f in list(self.files) if f not in included_files]:
            self.log_item(
                filename,
                filename + ' no longer seen in project path. Dropping it from the project.')
            self.drop_file(filename)

    def _get_included_files(self):
        files = []
        for pathname in self.paths:
            files.extend([os.path.join(pathname, f) for f in os.listdir(pathname)])
        return [f for f in files if self._include_file(f)]

    def get_settings_paths(self):
        paths = []
        if self.entry_path is not None:
            paths.append(self.entry_path)
        if os.path.isdir(self.entry_point):
            paths.append(self.entry_point)

        for node in self.get_setting('paths'):
            for n in node.children:
                pathname = n.metadata.get_first_value('path')
                if pathname:
                    path = utils.get_path_from_link(pathname.text)
                    if os.path.exists(path):
                        paths.append(path)
                        recurse_subfolders = n.metadata.get_first_value('recurse_subfolders')
                        if recurse_subfolders:                        
                            if path:
                                for dirpath, dirnames, filenames in os.walk(path):
                                    if '/.git' in dirpath or '/_diff' in dirpath:
                                        continue
                                    paths.append(dirpath)
                    else:
                        print("NOT PATH FOR", pathname.text)
        return paths

    def _include_file(self, filename):
        if filename in self.excluded_files:
            return False
        file_extensions = self.get_setting('file_extensions')
        if '.urtext' not in file_extensions or 'urtext' not in file_extensions:
            file_extensions.append('.urtext')  # for bootstrapping
        if os.path.splitext(filename)[1] not in file_extensions:
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
        self._parse_file(filename)
        self._compile_file(filename)

    def get_file_name(self, node_id):
        if node_id in self.nodes:
            filename = self.nodes[node_id].filename
        else:
            return None
        return filename

    def title_completions(self):
        return [
            (self.nodes[n].id,
             ''.join(utils.make_node_link(self.nodes[n].id)))
            for n in list(self.nodes)]

    def get_keys_with_frequency(self):
        key_occurrences = {}
        exclude = self.get_setting('exclude_from_star')
        exclude.extend(self.get_settings_keys())
        for node in list(self.nodes.values()):
            node_keys = node.metadata.get_keys(exclude=exclude)
            for key in node_keys:
                key_occurrences[key] = key_occurrences.get(key, 0)
                key_occurrences[key] += node_keys[key]

        return key_occurrences

    def get_all_keys(self):
        key_occurrences = self.get_keys_with_frequency()
        unique_keys = key_occurrences.keys()

        if self.get_setting('meta_browser_sort_keys_by') == 'frequency':
            return sorted(
                unique_keys,
                key=lambda key: key_occurrences[key],
                reverse=True)
        else:
            return sorted(unique_keys)

    def get_all_values_for_key_with_frequency(self, key):

        values = {}
        for node in self.nodes.values():
            values_occurrences = node.metadata.get_values_with_frequency(key)
            for v in values_occurrences:
                values[v.text] = values.get(v.text, 0)
                values[v.text] += values_occurrences[v]

        return values

    def get_all_values_for_key(self,
                               key,
                               substitute_timestamp=True):

        """
        Return tuple of (value.text, value.timestamp)
        """
        values_occurrences = self.get_all_values_for_key_with_frequency(key)
        values = values_occurrences.keys()
        if self.get_setting('meta_browser_sort_values_by') == 'frequency':
            return sorted(
                values,
                key=lambda value: values_occurrences[value],
                reverse=True)

        return sorted(values)

    def go_to_dynamic_definition(self, target_id):
        if target_id in self.dynamic_definitions:
            dd = self.dynamic_definitions[target_id]
            self.run_editor_method(
                'open_file_to_position',
                self.nodes[dd.source_node.id].filename,
                self.nodes[dd.source_node.id].get_file_position(dd.position))
            return self.visit_node(dd.source_node.id)
        self.handle_info_message(
            'No dynamic definition for "%s"' % target_id
        )

    def get_by_meta(self,
                    key,
                    values,
                    operator,
                    as_nodes=False):

        if not isinstance(values, list):
            values = [values]
        results = set()

        if operator in ['before', 'after']:
            compare_date = date_from_timestamp(values[0][1:-1])

            if compare_date:
                if operator == 'before':
                    results = [n for n in self.nodes.values() if
                               default_date != n.metadata.get_date(key) < compare_date]
                if operator == 'after':
                    results = [n for n in self.nodes.values() if
                               n.metadata.get_date(key) > compare_date != default_date]

        if key == '_contents' and operator == '?':
            for node in list(self.nodes.values()):
                if node.dynamic:
                    continue
                contents = node.stripped_contents
                lower_contents = contents.lower()

                for v in values:
                    if v.lower() in lower_contents:
                        results.add(node.id)

        elif key == '_links_to':
            for v in values:
                results.update(self.get_links_to(v))

        elif key == '_links_from':
            for v in values:
                results.update(self.get_links_from(v))
        else:
            if key == '*':
                keys = self.get_all_keys()
            else:
                keys = [key]
            for k in keys:
                for value in values:
                    if value == '*':
                        results.update([n for n in self.nodes if
                                        self.nodes[n].metadata.get_values(
                                            k,
                                            convert_nodes_to_links=True)])
                        continue

                    if k in self.get_setting('numerical_keys'):
                        try:
                            value = float(value)
                        except ValueError:
                            value = float('inf')

                    use_timestamp = False
                    if isinstance(value, UrtextTimestamp):
                        use_timestamp = True

                    if k in self.get_setting('case_sensitive'):
                        results.update([
                            n for n in self.nodes if
                            value in [
                                v.text for v in self.nodes[n].metadata.get_values(k) if v.text]])
                    else:
                        if isinstance(value, str):
                            value = value.lower()
                        for n in self.nodes.values():
                            found_values = n.metadata.get_values(k)
                            if use_timestamp:
                                if value in [v.timestamp for v in found_values]:
                                    results.update([n.id])
                            else:
                                if value in [v.text_lower for v in found_values]:
                                    results.update([n.id])

        results = list(results)
        if as_nodes:
            return [self.nodes[n] for n in results]
        return results

    def get_file_and_position(self, node_id):
        if node_id in self.nodes:
            filename = self.get_file_name(node_id)
            position = self.nodes[node_id].start_position
            return filename, position
        return None, None

    def run_hook(self, hook_name, *args):
        for dd in self.dynamic_definitions.values():
            hook = getattr(dd, hook_name, None)
            if hook and callable(hook):
                hook(*args)
        for directive in self.project_instance_directives.values():
            hook = getattr(directive, hook_name, None)
            if hook and callable(hook):
                hook(*args)
        self.project_list.run_hook(hook_name, *args)

    """ Project Compile """

    def _compile(self):
        self.handle_info_message('Compiling Urtext project from %s' % self.entry_point)
        num_directives = len(list(self.directives.values()))
        num_project_directives = len(list(self.project_instance_directives.values()))
        for dd in list(self.dynamic_definitions.values()):
            directives = self.__run_def(dd)
        while len(self.directives.values()) > num_directives: # directives can add directives
            return self._compile()
        self._add_all_sub_tags()
        self._verify_links_globally()
        self.compiled = True
        self.last_compile_time = time.time() - self.time
        self.time = time.time()
        self.handle_info_message('"%s" compiled' % self.title())

    def _compile_file(self, filename, flags=None):
        if flags is None:
            flags = {}

        for node in self.files[filename].nodes:
            for dd in self.__get_dynamic_defs(target_node=node, source_node=node):
                self.__run_def(dd)

    def __run_def(self, dd, flags=None):
        output = dd.process(flags=flags)
        if output not in [False, None]:
            for target in dd.targets + dd.target_ids:
                targeted_output = dd.post_process(
                    target,
                    output)
                self._direct_output(
                    targeted_output,
                    target,
                    dd)
                if target in self.nodes:
                    self.nodes[target].dynamic = True

    def _direct_output(self, output, target, dd):
        node_link = syntax.node_link_or_pointer_c.match(target)
        if node_link:
            node_id = utils.get_id_from_link(node_link.group())
        else:
            node_id = target
        if node_id in self.nodes:
            if self._set_node_contents(node_id, output):
                return node_id
            return False

        target_file = syntax.file_link_c.match(target)
        if target_file:
            filename = utils.get_id_from_link(target_file)
            filename = os.path.join(self.entry_point, filename)
            utils.write_file_contents(filename, output)
            return filename
        virtual_target = syntax.virtual_target_match_c.match(target)
        if virtual_target:
            virtual_target = virtual_target.group()
            if virtual_target == '@self':
                if self._set_node_contents(dd.source_node.id, output):
                    return dd.source_node.id
            if virtual_target == '@clipboard':
                return self.run_editor_method('set_clipboard', output)
            if virtual_target == '@next_line':
                return self.run_editor_method('insert_at_next_line', output)
            if virtual_target == '@log':
                return self.log_item(
                    self.nodes[dd.source_node.id].filename,
                    output)
            if virtual_target == '@console':
                return self.run_editor_method('write_to_console', output)
            if virtual_target == '@popup':
                return self.run_editor_method('popup', output)
        if target in self.nodes:  # fallback
            self._set_node_contents(target, output)
            return target

    """ Metadata Handling """

    def _add_sub_tags(self,
                      entry,
                      next_node=None,
                      visited_nodes=None):

        if visited_nodes is None:
            visited_nodes = []
        source_node_id = entry.from_node.id
        if next_node:
            source_node_id = next_node

        if source_node_id not in self.nodes:
            return

        for child in self.nodes[source_node_id].children:

            uid = source_node_id + child.id
            if uid in visited_nodes:
                continue
            node_to_tag = child.id
            if node_to_tag not in self.nodes:
                visited_nodes.append(uid)
                continue

            if uid not in visited_nodes and not self.nodes[node_to_tag].dynamic:
                self.nodes[node_to_tag].metadata.add_entry(
                    entry.keyname,
                    entry.meta_values,
                    self.nodes[node_to_tag],
                    tag_self=True,
                    from_node=entry.from_node,
                    tag_descendants=entry.tag_descendants)
                self.nodes[node_to_tag].metadata.convert_hash_keys()
                if node_to_tag not in entry.from_node.target_nodes:
                    entry.from_node.target_nodes.append(node_to_tag)

            visited_nodes.append(uid)

            if entry.tag_descendants:
                self._add_sub_tags(
                    entry,
                    next_node=node_to_tag,
                    visited_nodes=visited_nodes)
        self.run_hook(
            'on_sub_tags_added',
            source_node_id,
            entry)

    def _remove_sub_tags(self, source_id):
        source_node = self.nodes[source_id]
        for target_id in source_node.target_nodes:
            if target_id in self.nodes:
                self.nodes[target_id].metadata.clear_from_source(source_node)

    def title(self):
        title_setting = self.get_setting('project_title')
        if title_setting:
            return title_setting
        return self.entry_point

    def on_project_activated(self):
        if self.get_setting('on_project_activated'):
            for action in self.get_setting('on_project_activated'):
                if action == 'open_home':
                    if self.open_home():
                        return

    def has_folder(self, folder):
        included_paths = self.get_settings_paths()
        if os.path.isdir(self.entry_point):
            included_paths.append(self.entry_point)
        return included_paths

    def _make_buffer(self, filename, buffer_contents):
        new_file = UrtextBuffer(self, filename, buffer_contents)
        new_file.filename = filename
        for node in new_file.nodes:
            node.filename = filename
        return new_file

    """ Editor Methods """

    def editor_insert_timestamp(self):
        self.run_editor_method('insert_text', self.timestamp(as_string=True))

    def editor_copy_link_to_node(self,
                                 position,
                                 filename,
                                 include_project=False):

        self._parse_file(filename, try_buffer=True)

        node_id = None
        for node in self.files[filename].nodes:
            for r in node.ranges:
                if position in range(r[0], r[1] + 1):  # +1 in case the cursor is in the last position of the node.
                    node_id = node.id
                    break
        if node_id:
            link = self.project_list.build_contextual_link(
                node_id,
                include_project=include_project)
            if link:
                self.run_editor_method('set_clipboard', link)
        else:
            self.handle_info_message('No Node found here')

    def run_editor_method(self, method_name, *args, **kwargs):
        if method_name in self.editor_methods:
            return self.editor_methods[method_name](*args, **kwargs)
        print('No editor method available for "%s"' % method_name)
        return False

    def add_directive(self, directive):
        propagated_directives = self.get_setting('propagate_directives')
        propagate_all_directives = '_all' in propagated_directives

        class Directive(directive, UrtextDirective):
            pass

        if Directive.project_instance:
            global_directive = Directive(self)
            global_directive.on_added()
            self.project_instance_directives[Directive.name[0]] = (Directive(self))
            if Directive.name in propagated_directives or propagate_all_directives:
                self.project_list.add_directive(directive)
        else:
            for n in directive.name:
                self.directives[n] = directive
            self.project_list.add_directive(directive)
        return self.directives

    def get_directive(self, directive_name):
        directive_class = None
        if directive_name in self.directives:
            directive_class = self.directives[directive_name]
        elif directive_name in self.project_list.directives:
            directive_class = self.project_list.directives[directive_name]
        if not directive_class:
            return None

        class Directive(directive_class, UrtextDirective):
            pass

        return Directive

    def run_directive(self, directive_name, *args, **kwargs):
        directive = self.get_directive(directive_name)
        if not directive:
            self.handle_info_message('Directive %s is not available' % directive_name)
            return None
        op = directive(self)
        return op.run(*args, **kwargs)
