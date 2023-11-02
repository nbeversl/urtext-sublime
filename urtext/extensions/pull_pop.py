import re
import os

class PopNode:

    name=['POP_NODE']

    def __init__(self, project):
        super().__init__(project)
        self.running = False

    def pop_node(self,
        param_string, 
        source_filename, 
        file_pos):

        return self.project.execute(
            self._pop_node,
            param_string, 
            source_filename, 
            file_pos)

    def _pop_node(self,
        param_string, 
        source_filename, 
        file_pos):

        if not self.project.compiled:
            print('Project not yet compiled.')
            return        

        if source_filename not in self.project.files:
            print(source_filename, 'not in project')
            return

        self.project.run_editor_method('save_file', source_filename)

        popped_node_id = self.project.get_node_id_from_position(
            source_filename,
            file_pos)
 
        if not popped_node_id:
            print('No node ID or duplicate Node ID')
            return
        
        if popped_node_id not in self.project.nodes:
            print(popped_node_id, 'not in project')
            return

        if self.project.nodes[popped_node_id].root_node:
            print(popped_node_id+ ' is already a root node.')
            return
    
        start = self.project.nodes[popped_node_id].start_position
        end = self.project.nodes[popped_node_id].end_position
        source_file_contents = self.project.files[source_filename]._get_contents()
        popped_node_contents = source_file_contents[start:end].strip()
        
        if self.project.settings['breadcrumb_key']:
            parent_id = self.project.nodes[popped_node_id].parent.id
            popped_node_contents += ''.join([
                '\n',
                self.project.settings['breadcrumb_key'],
                self.syntax.metadata_assignment_operator,
                self.syntax.link_opening_wrapper,
                self.project.nodes[parent_id].id,
                self.syntax.link_closing_wrapper,
                ' ',
                self.project.timestamp().wrapped_string]);

        self.project._drop_file(source_filename) #important

        new_file_node = self.project.new_file_node(contents=popped_node_contents)

        remaining_node_contents = ''.join([
            source_file_contents[:start - 1],
            self.syntax.link_opening_wrapper,
            new_file_node['id'],
            self.syntax.pointer_closing_wrapper,
            '\n' if self.project.nodes[new_file_node['id']].compact else '',
            source_file_contents[end + 1:]
            ])

        with open(source_filename, 'w', encoding='utf-8') as f:
            f.write(remaining_node_contents)
        self.project.run_editor_method(
            'set_buffer',
            source_filename,
            remaining_node_contents)
        self.project._parse_file(source_filename)
 
class PullNode:

    name=['PULL_NODE']

    def __init__(self, project):
        super().__init__(project)
        self.running = False

    def pull_node(self, 
        string, 
        destination_filename, 
        file_pos):

        return self.project.execute(
            self._pull_node,
            string, 
            destination_filename, 
            file_pos)

    def _pull_node(self, 
        string, 
        destination_filename, 
        file_pos):

        if not self.project.compiled:
            print('Project not yet compiled.')
            return        

        link = self.project.parse_link(
            string,
            file_pos=file_pos)

        if not link or link['kind'] != 'NODE':
            print('link is not a node')
            return

        source_id = link['node_id']
        if source_id not in self.project.nodes: 
            return
        
        destination_node = self.project.get_node_id_from_position(
            destination_filename, 
            file_pos)

        if not destination_node:
            print('No destination node found here')
            return

        if self.project.nodes[destination_node].dynamic:
            print('Not pulling content into a dynamic node')
            return

        source_filename = self.project.nodes[source_id].filename
        for ancestor in self.project.nodes[destination_node].tree_node.ancestors:
            if ancestor.name == source_id:
                print('Cannot pull a node into its own child or descendant.')
                return
        self.project._parse_file(source_filename)

        start = self.project.nodes[source_id].start_position
        end = self.project.nodes[source_id].end_position

        source_file_contents = self.project.files[source_filename]._get_contents()

        delete = False
        if not self.project.nodes[source_id].root_node:
            updated_source_file_contents = ''.join([
                source_file_contents[0:end],
                source_file_contents[end:len(source_file_contents)]
                ])
            self.project.files[source_filename]._set_contents(
                updated_source_file_contents)
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
            link['full_match'],
            wrapped_contents)

        self.project.files[destination_filename]._set_contents(destination_file_contents)

        self.project.run_editor_method(
            'set_buffer',
            destination_filename,
            destination_file_contents)
        self.project._parse_file(destination_filename)

urtext_extensions = [PullNode, PopNode]
        