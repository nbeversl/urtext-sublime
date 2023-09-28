import re

class PopNode:

    name=['POP_NODE']

    def pop_node(self,
        param_string, 
        filename, 
        file_pos=None,  
        node_id=None):

        return self.project.execute(
            self._pop_node,
            param_string, 
            filename, 
            file_pos=file_pos,  
            node_id=node_id)

    def _pop_node(self,
        param_string, 
        filename, 
        file_pos=None,  
        node_id=None):
 
        if not node_id:
            node_id = self.project.get_node_id_from_position(
                filename, 
                file_pos)
 
        if not node_id:
            print('No node ID or duplicate Node ID')
            return None
        
        if self.project.nodes[node_id].root_node:
            print(node_id+ ' is already a root node.')
            return None

        self.project._parse_file(filename)
        start = self.project.nodes[node_id].start_position()
        end = self.project.nodes[node_id].end_position()
        filename = self.project.nodes[node_id].filename
        file_contents = self.project.files[filename]._get_file_contents()
        popped_node_id = node_id
        popped_node_contents = file_contents[start:end+1].strip()
        parent_id = self.project.nodes[node_id].parent.id
        
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
            file_contents[:start - 1],
            '\n',
            self.syntax.link_opening_wrapper,
            popped_node_id,
            self.syntax.pointer_closing_wrapper,
            file_contents[end + 1:]
            ])
       
        with open(os.path.join(self.project.entry_path, filename), 'w', encoding='utf-8') as f:
            f.write(remaining_node_contents)
        self.project._parse_file(filename) 

        new_file_name = os.path.join(self.project.entry_path, popped_node_id+'.urtext')
        with open(new_file_name, 'w',encoding='utf-8') as f:
            f.write(popped_node_contents)
        self.project._parse_file(new_file_name) 
        return filename

class PullNode:

    name=['PULL_NODE']

    def pull_node(self, 
        string, 
        destination_filename, 
        file_pos=0,
        col_pos=0):

        return self.project.execute(
            self._pull_node,
            string, 
            destination_filename, 
            file_pos=file_pos,
            col_pos=col_pos)

    def _pull_node(self, 
        string, 
        destination_filename, 
        file_pos=0,
        col_pos=0):
        
        replacement_contents = None

        link = self.project.parse_link(
            string,
            file_pos=file_pos,
            col_pos=col_pos)
        
        if not link or link['kind'] != 'NODE': 
            return None
        
        source_id = link['link']
        
        if source_id not in self.project.nodes: 
            return None

        #  make sure we are in a node in an Urtext file.
        self.project._parse_file(destination_filename)
        destination_node = self.project.get_node_id_from_position(destination_filename, file_pos)
        if not destination_node:
            return None
        if self.project.nodes[destination_node].dynamic:
            print('Not pulling content into a dynamic node')
            return None

        source_filename = self.project.nodes[source_id].filename
        for ancestor in self.project.nodes[destination_node].tree_node.ancestors:
            if ancestor.name == source_id:
                print('Cannot pull a node into its own child or descendant.')
                return None
                        
        self.project._parse_file(source_filename)
        start = self.project.nodes[source_id].start_position()
        end = self.project.nodes[source_id].ranges[-1][1]
        
        source_file_contents = self.project.files[source_filename]._get_file_contents()

        updated_source_file_contents = ''.join([
            source_file_contents[0:start-1],
            source_file_contents[end+1:len(source_file_contents)]])

        root = False
        if not self.project.nodes[source_id].root_node:
            self.project.files[source_filename]._set_file_contents(
                updated_source_file_contents)
            self.project._parse_file(source_filename)
        else:
            self.project._delete_file(source_filename)
            root = True
        
        pulled_contents = source_file_contents[start:end]
        destination_file_contents = self.project.files[destination_filename]._get_file_contents()
    
        wrapped_contents = ''.join([
            self.syntax.node_opening_wrapper,
            ' ',
            pulled_contents,
            ' ',
            self.syntax.node_closing_wrapper])

        for m in re.finditer(re.escape(link['full_match']), destination_file_contents):
                
            replacement_contents = ''.join([
                destination_file_contents[:m.start()],
                wrapped_contents,
                destination_file_contents[m.end():]]
                )

        if replacement_contents:
            self.project.files[destination_filename]._set_file_contents(replacement_contents)
            self.project._parse_file(destination_filename)

        if root == True: return source_filename
        return None

urtext_extensions = [PullNode, PopNode]
        