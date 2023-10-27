import re
import os

class PopNode:

    name=['POP_NODE']

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

        if not self.project.event_listeners_should_continue:
            return

        if source_filename not in self.project.files:
            print(source_filename, 'not in project')
            return

        self.project.event_listeners_should_continue = False
        self.project.run_editor_method('save_file', source_filename)
        self.project._on_modified(source_filename, bypass=True)

        popped_node_id = self.project.get_node_id_from_position(
            source_filename,
            file_pos)
 
        if not popped_node_id:
            print('No node ID or duplicate Node ID')
            self.project.event_listeners_should_continue = True
            return
        
        if popped_node_id not in self.project.nodes:
            print(popped_node_id, 'not in project')
            self.project.event_listeners_should_continue = True
            return

        if self.project.nodes[popped_node_id].root_node:
            print(popped_node_id+ ' is already a root node.')
            self.project.event_listeners_should_continue = True
            return
    
        start = self.project.nodes[popped_node_id].start_position
        end = self.project.nodes[popped_node_id].end_position
        source_file_contents = self.project.files[source_filename]._get_contents()
        popped_node_contents = source_file_contents[start:end].strip()
        parent_id = self.project.nodes[popped_node_id].parent.id
        
        if self.project.settings['breadcrumb_key']:
            popped_node_contents += ''.join([
                '\n',
                self.project.settings['breadcrumb_key'],
                self.syntax.metadata_assignment_operator,
                self.syntax.link_opening_wrapper,
                self.project.nodes[parent_id].id,
                self.syntax.link_closing_wrapper,
                ' ',
                self.project.timestamp().wrapped_string]);

        remaining_node_contents = ''.join([
            source_file_contents[:start - 1],
            self.syntax.link_opening_wrapper,
            popped_node_id,
            self.syntax.pointer_closing_wrapper,
            '\n' if self.project.nodes[popped_node_id].compact else '',
            source_file_contents[end + 1:]
            ])
        self.project.files[source_filename]._set_contents(remaining_node_contents)
        self.project._parse_file(source_filename)

        new_file_name = os.path.join(
            self.project.entry_path, 
            popped_node_id+'.urtext')
        with open(new_file_name, 'w',encoding='utf-8') as f:
            f.write(popped_node_contents)
        self.project._parse_file(new_file_name)
        self.project._on_modified(source_filename, bypass=True)
        self.project.event_listeners_should_continue = True
  
class PullNode:

    name=['PULL_NODE']

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

        if not self.project.event_listeners_should_continue:
            return

        self.project.event_listeners_should_continue = False
        self.project.run_editor_method('save_current')
        self.project.event_listeners_should_continue = True
        self.project._on_modified(destination_filename)
        self.project.event_listeners_should_continue = False

        link = self.project.parse_link(
            string,
            file_pos=file_pos)

        if not link or link['kind'] != 'NODE': 
            self.project.event_listeners_should_continue = True
            return

        source_id = link['node_id']
        if source_id not in self.project.nodes: 
            self.project.event_listeners_should_continue = True
            return
        
        destination_node = self.project.get_node_id_from_position(
            destination_filename, 
            file_pos)

        if not destination_node:
            print('No destination node found here')
            self.project.event_listeners_should_continue = True
            return

        if self.project.nodes[destination_node].dynamic:
            print('Not pulling content into a dynamic node')
            self.project.event_listeners_should_continue = True
            return

        source_filename = self.project.nodes[source_id].filename
        for ancestor in self.project.nodes[destination_node].tree_node.ancestors:
            if ancestor.name == source_id:
                print('Cannot pull a node into its own child or descendant.')
                self.project.event_listeners_should_continue = True
                return

        self.project._on_modified(source_filename, bypass=True)
        start = self.project.nodes[source_id].start_position
        end = self.project.nodes[source_id].end_position

        source_file_contents = self.project.files[source_filename]._get_contents()

        if not self.project.nodes[source_id].root_node:
            updated_source_file_contents = ''.join([
                source_file_contents[0:end],
                source_file_contents[end:len(source_file_contents)]
                ])
            self.project.files[source_filename]._set_contents(
                updated_source_file_contents)
            self.project._on_modified(source_filename, bypass=True)
        else:
            self.project._delete_file(source_filename)
            self.project.run_editor_method('close_file', source_filename)

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
        self.project._on_modified(destination_filename, bypass=True)
        self.project.event_listeners_should_continue = True

urtext_extensions = [PullNode, PopNode]
        