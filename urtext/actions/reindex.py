import os
import concurrent.futures
if os.path.exists(os.path.join(os.path.dirname(os.path.realpath(__file__)), '../sublime.txt')):
    from Urtext.urtext.action import UrtextAction
else:
    from urtext.action import UrtextAction

class ReindexFiles(UrtextAction):
    """ 
    sorts all file-level nodes by their index, then passes
    the result to rename_file_nodes() to rename them.
    """    
    name=['REINDEX']
    
    def execute(self, 
        param_string, 
        filename=None,
        file_pos=0,
        col_pos=0, 
        node_id=None):

        files = self.project.all_files() 
        return self.rename_file_nodes(files, reindex=True)
     
    def rename_file_nodes(self, filenames, reindex=False, keep_prefix=False):
        """ Rename a file or list of files by metadata """

        if isinstance(filenames, str):
            filenames = [filenames]
       
        used_names = []
        existing_files = os.listdir(self.project.path)
        renamed_files = {}
        date_template = self.project.settings['filename_datestamp_format']
        prefix = 0
        prefix_length = len(str(len(self.project.files)))
        for filename in filenames:
            old_filename = os.path.basename(filename)
            if old_filename not in self.project.files:
                return {}

            if not self.project.files[old_filename].root_nodes:
                print('No root nodes in '+old_filename)
                continue

            ## Name each file from the first root_node
            root_node_id = self.project.files[old_filename].root_nodes[0]
            root_node = self.project.nodes[root_node_id]
            filename_template = list(self.project.settings['filenames'])
            if keep_prefix and 'PREFIX' in filename_template:
                filename_template.pop(filename_template.index('PREFIX')) 
                try:
                    existing_prefix = int(old_filename.split('-')[0])
                    existing_prefix = old_filename.split('-')[0].strip()
                except:
                    existing_prefix = ''
            
            for i in range(0,len(filename_template)):

                if filename_template[i] == 'PREFIX' and reindex == True:
                    padded_prefix = '{number:0{width}d}'.format(
                        width = prefix_length, 
                        number = prefix)
                    filename_template[i] = padded_prefix
                
                elif filename_template[i].lower() == 'title':
                    filename_length = int(self.project.settings['filename_title_length'])
                    if filename_length > 255:
                        filename_length = 255
                    title = root_node.get_title()
                    filename_template[i] = title[:filename_length]
                
                elif filename_template[i].lower() in self.project.settings['use_timestamp']:
                    timestamp = root_node.metadata.get_first_value(filename_template[i], use_timestamp=True)
                    if timestamp:
                        filename_template[i] = timestamp.strftime(date_template)
                    else:
                        filename_template[i] = ''                
                else:
                    filename_template[i] = ' '.join([str(s) for s in root_node.metadata.get_values(filename_template[i])])

            if filename_template in [ [], [''] ]:
                return print('New filename(s) could not be made. Check project_settings')

            if keep_prefix and 'PREFIX' in filename_template:
                filename_template.insert(0, str(existing_prefix))
            filename_template = [p.strip() for p in filename_template if p.strip()]
            new_filename = ' - '.join(filename_template)      
            new_filename = new_filename.replace('’', "'")
            new_filename = new_filename.strip().strip('-').strip();
            new_filename = strip_illegal_characters(new_filename)
            new_filename = new_filename[:250]
            new_filename += '.txt'

            if new_filename in used_names:
                new_filename = new_filename.replace('.txt',' - '+root_node.id+'.txt')

            # renamed_files retains full file paths
            renamed_files[os.path.join(self.project.path, old_filename)] = os.path.join(self.project.path, new_filename)
            used_names.append(new_filename)

            # add history files
            old_history_file = old_filename.replace('.txt','.diff')
            if os.path.exists(os.path.join(self.project.path, 'history', old_history_file) ):
                new_history_file = new_filename.replace('.txt','.diff')
                #renamed_files[os.path.join(self.project.path, 'history', old_history_file)] = os.path.join(self.project.path, 'history', new_history_file)

            prefix += 1
            
        for filename in renamed_files:
            old_filename = filename
            new_filename = renamed_files[old_filename]
            os.rename(old_filename, new_filename)
            self.project._handle_renamed(old_filename, new_filename)

        return renamed_files

class RenameSingleFile(ReindexFiles):

    name=['RENAME_SINGLE_FILE']

    def execute(self, 
        param_string, 
        filename=None,
        file_pos=0,
        col_pos=0, 
        node_id=None):

        return self.rename_file_nodes(filename, reindex=True, keep_prefix=True) 

def strip_illegal_characters(filename):
    for c in ['<', '>', ':', '"', '/', '\\', '|', '?','*']:
        filename = filename.replace(c,' ')
    return filename