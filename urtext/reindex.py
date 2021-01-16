import os
import datetime

""" 
Reindexing (renaming) Files 
"""
def reindex_files(self):
    """ 
    sorts all file-level nodes by their index, then passes
    the result to rename_file_nodes() to rename them.
    """

    # Calculate zero-padded digit length for the file prefix:
    prefix = 0
    
    # this should actually just be the first root node, not all root nodes.
    remaining_primary_root_nodes = list(self.root_nodes(primary=True))

    indexed_nodes = list(self.indexed_nodes())
    for node_id in indexed_nodes:
        if node_id in remaining_primary_root_nodes:
            self.nodes[node_id].prefix = prefix
            remaining_primary_root_nodes.remove(node_id)
            prefix += 1

    unindexed_root_nodes = [self.nodes[node_id] for node_id in remaining_primary_root_nodes]
    date_sorted_nodes = sorted(unindexed_root_nodes,
                               key=lambda r: r.date,
                               reverse=True)

    for node in date_sorted_nodes:
        node.prefix = prefix
        prefix += 1
    if self.is_async:
        return self.executor.submit(self._rename_file_nodes, list(self.files), reindex=True)
    return self._rename_file_nodes(list(self.files), reindex=True)

def rename_file_nodes(self, filename, reindex=False):
    if self.is_async:
        future = self.executor.submit(self._rename_file_nodes, filename, reindex=reindex)
        renamed_files = future.result()
        return renamed_files
    else:
        return self._rename_file_nodes(filename, reindex=reindex)

def _rename_file_nodes(self, filenames, reindex=False):
    """ Rename a file or list of files by metadata """
    
    if isinstance(filenames, str):
        filenames = [filenames]

    used_names = []
    existing_files = os.listdir()

    indexed_nodes = list(self.indexed_nodes())
    filename_template = self.settings['filenames']
    renamed_files = {}
    date_template = None

    for i in range(0, len(filename_template)):
        if 'DATE' in filename_template[i]:
            date_template = filename_template[i].replace('DATE', '').strip()
            filename_template[i] = 'DATE'

    for filename in filenames:

        old_filename = os.path.basename(filename)
        if old_filename not in self.files:
            return []

        if not self.files[old_filename].root_nodes:
            self._log_item('DEBUGGING (reindex.py): No root nodes in '+old_filename)
            continue

        ## Name each file from the first root_node
        root_node_id = self.files[old_filename].root_nodes[0]
        root_node = self.nodes[root_node_id]

        # start with the filename template, replace each element
        new_filename = ' - '.join(filename_template)
        if root_node.title:
            new_filename = new_filename.replace('TITLE', root_node.title)
        else:
            new_filename = new_filename.replace('TITLE', '(untitled)')
        
        if root_node_id not in indexed_nodes and date_template != None:
            new_filename = new_filename.replace(
                'DATE', 
                datetime.datetime.strftime(root_node.date, date_template))
        else:
            new_filename = new_filename.replace('DATE', '')
        
        if reindex == True:
            padded_prefix = '{number:0{width}d}'.format(
                width=self._prefix_length(), number=int(root_node.prefix))
            new_filename = new_filename.replace('PREFIX', padded_prefix)
        else:
            old_prefix = old_filename.split('-')[0].strip()
            new_filename = new_filename.replace('PREFIX', old_prefix)
        new_filename = new_filename.replace('/', '-')
        new_filename = new_filename.replace('.', ' ')
        new_filename = new_filename.replace('’', "'")
        new_filename = new_filename.replace(':', "-")
        new_filename = new_filename.strip('-').strip();
        new_filename += '.txt'

        if new_filename in used_names:
            new_filename = new_filename.replace('.txt',' - '+root_node.id+'.txt')
        # renamed_files retains full file paths
        renamed_files[os.path.join(self.path, old_filename)] = os.path.join(self.path, new_filename)
        used_names.append(new_filename)

        # add history files
        old_history_file = old_filename.replace('.txt','.pkl')
        if os.path.exists(os.path.join(self.path, 'history', old_history_file)  ):
            new_history_file = new_filename.replace('.txt','.pkl')
            renamed_files[os.path.join(self.path, 'history', old_history_file)] = os.path.join(self.path, 'history', new_history_file)
            

    for filename in renamed_files:
        old_filename = filename
        new_filename = renamed_files[old_filename]

        self._log_item('renaming ' + old_filename + ' to ' + new_filename)

        os.rename(old_filename, new_filename)

        if old_filename[-4:].lower() == '.txt': # skip history files
            self._handle_renamed(old_filename, new_filename)

    """
    Returns a list of renamed files with full paths
    """    
    return renamed_files

reindex_functions = [ rename_file_nodes, _rename_file_nodes, reindex_files ]
