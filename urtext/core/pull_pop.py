import os

class PopNode:

    name=['POP_NODE']

    def pop_node_from_editor(self,
        source_filename, 
        file_pos,
        from_project=None):

        return self.project.execute(
            self._pop_node_from_editor,
            source_filename, 
            file_pos,
            from_project=from_project)

    def _pop_node_from_editor(self,
        source_filename, 
        file_pos,
        from_project=None):

        if not self.project.compiled:
            return self.project.handle_info_message(
                'Project not yet compiled.')

        if source_filename not in self.project.files:
            return self.project.handle_info_message(
                '%s not in project' % source_filename)

        self.project.run_editor_method('save_file', source_filename)
        self.project._parse_file(source_filename)

        popped_node_id = self.project.get_node_id_from_position(source_filename, file_pos) 
        if not popped_node_id:
            return self.project.handle_info_message(
                'No node ID or duplicate Node ID')        
        if popped_node_id not in self.project.nodes:
            return self.project.handle_info_message(
                '%s not in project' % popped_node_id)

        if self.project.nodes[popped_node_id].root_node:
            return self.project.handle_info_message(
                '%s is already a root node.' % popped_node_id)

        self._pop_node(popped_node_id, from_project=from_project)

    def _pop_node(self,
        popped_node_id,
        rewrite_buffer=True,
        from_project=None,
        leave_link=False,
        leave_pointer=True,
        include_project=False):
        
        source_filename = self.project.nodes[popped_node_id].filename
        self.project.run_editor_method('save_file', source_filename)
        start = self.project.nodes[popped_node_id].start_position
        end = self.project.nodes[popped_node_id].end_position
        source_file_contents = self.project.files[source_filename]._get_contents()
        popped_node_contents = source_file_contents[start:end].strip()
        pre_offset = 2 if self.project.nodes[popped_node_id].compact else 1
        post_offset = 0 if self.project.nodes[popped_node_id].compact else 1
        parent_id = self.project.nodes[popped_node_id].parent.id
        popped_node_is_compact = self.project.nodes[popped_node_id].compact
        
        if self.project.settings['breadcrumb_key']:
            if from_project:
                popped_node_contents += ''.join([
                '\n',
                self.project.settings['breadcrumb_key'],
                self.syntax.metadata_assignment_operator,
                self.project.nodes[popped_node_id].link(include_project=True),
                ' ',
                self.project.timestamp().wrapped_string]);
            else:
                popped_node_contents += ''.join([
                    '\n',
                    self.project.settings['breadcrumb_key'],
                    self.syntax.metadata_assignment_operator,
                    self.project.nodes[popped_node_id].parent.link(),
                    ' ',
                    self.project.timestamp().wrapped_string]);

        self.project._drop_file(source_filename) #important

        new_file_node = self.project.new_file_node(
            contents=popped_node_contents,
            open_file=False)

        insertion = ''
        if leave_pointer:
            insertion = new_file_node['root_node'].pointer()
        elif leave_link:
            # is it easier to leave a link to another project here than go back and rewrite them
            # from MOVE_TO_PROJECT?
            insertion = new_file_node['root_node'].link() #include_project=include_project
        remaining_node_contents = ''.join([
            source_file_contents[:start - pre_offset],
            insertion,
            '\n' if popped_node_is_compact else '',
            source_file_contents[end + post_offset:]
            ])
        if os.path.exists(source_filename):
            os.remove(source_filename)
        with open(source_filename, 'w', encoding='utf-8') as f:
            f.write(remaining_node_contents)
        if rewrite_buffer:
            self.project.run_editor_method(
                'set_buffer',
                source_filename,
                remaining_node_contents)
        self.project._parse_file(source_filename)
        return new_file_node['filename']
 
class PullNode:

    name=['PULL_NODE']

    def pull_node(self, 
        string, 
        col_pos,
        destination_filename, 
        file_pos):

        return self.project.execute(
            self._pull_node,
            string, 
            col_pos,
            destination_filename, 
            file_pos)

    def _pull_node(self, 
        string,
        col_pos,
        destination_filename, 
        file_pos):

        if not self.project.compiled:
            return self.project.handle_info_message(
                'Project not yet compiled.')

        link = self.project.project_list.utils.get_link_from_position_in_string(string, col_pos)

        if not link or link.node_id not in self.project.nodes:
            return self.project.handle_info_message(
                'link is not a node')

        source_node = self.project.nodes[link.node_id]
        if source_node.id not in self.project.nodes: 
            return
        
        destination_node = self.project.get_node_id_from_position(
            destination_filename, 
            file_pos)

        if not destination_node:
            return self.project.handle_info_message(
                'No destination node found here')

        if self.project.nodes[destination_node].dynamic:
            return self.project.handle_info_message(
                'Not pulling content into a dynamic node')

        source_filename = self.project.nodes[source_node.id].filename
        for ancestor in self.project.nodes[destination_node].tree_node.ancestors:
            if ancestor.name == source_node.id:
                return self.project.handle_info_message(
                    'Cannot pull a node into its own child or descendant.')
        self.project._parse_file(source_filename)

        start = self.project.nodes[source_node.id].start_position
        end = self.project.nodes[source_node.id].end_position

        source_file_contents = self.project.files[source_filename]._get_contents()

        delete = False
        if not self.project.nodes[source_node.id].root_node:
            updated_source_file_contents = ''.join([
                source_file_contents[0:end],
                source_file_contents[end:len(source_file_contents)]
                ])
            self.project.files[source_filename]._set_buffer_contents(
                updated_source_file_contents)
            self.project.files[source_filename].write_contents_to_file()

        else:
            self.project._delete_file(source_filename)

        pulled_contents = source_file_contents[start:end]
        destination_file_contents = self.project.files[destination_filename]._get_contents()

        wrapped_contents = ''.join([
            self.syntax.node_opening_wrapper,
            ' ',
            pulled_contents,
            ' ',
            self.syntax.node_closing_wrapper])
        
        destination_file_contents = destination_file_contents.replace(
            link.matching_string,
            wrapped_contents)

        self.project.files[destination_filename]._set_buffer_contents(destination_file_contents)
        self.project.files[destination_filename].write_contents_to_file()
        self.project.run_editor_method(
            'set_buffer',
            destination_filename,
            destination_file_contents)
        self.project._parse_file(destination_filename)

urtext_extensions = [PullNode, PopNode]
        