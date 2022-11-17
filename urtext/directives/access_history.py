import os
import re
if os.path.exists(os.path.join(os.path.dirname(os.path.realpath(__file__)), '../sublime.txt')):
    from Urtext.urtext.directive import UrtextDirectiveWithKeysFlags
    from Urtext.urtext.syntax import title_regex
else:
    from urtext.directive import UrtextDirectiveWithKeysFlags
    from urtext.syntax import title_regex
# This class should be abstracted as an accumulator (prepend/append)

class AccessHistory(UrtextDirectiveWithKeysFlags):

    name = ["ACCESS_HISTORY"]
    phase = 700

    def on_node_visited(self, node_id):
        self.dynamic_definition.process_output(max_phase=200)
        if node_id in self.dynamic_definition.included_nodes:
            if self.dynamic_definition.target_id in self.project.nodes:
                contents = self.project.nodes[self.dynamic_definition.target_id].contents()
                title = self.get_existing_title(contents)
                contents = contents.strip(title)
                contents = ''.join([ 
                        title,
                        '\n',
                        self.project.timestamp(), 
                        ' | ', 
                        self.project.nodes[node_id].get_title(), 
                        ' >\n', 
                        contents
                    ])
                access_history_file = self.project.get_file_name(self.dynamic_definition.target_id)
                self.project._parse_file(access_history_file)
                self.project._set_node_contents(self.dynamic_definition.target_id, contents)

    def get_existing_title(self, contents):
        title = re.search(title_regex, contents)
        if title:
            return title.group().strip() + ' _'
        return ''

    def dynamic_output(self, input_contents):
        return False # do not change existing output.



