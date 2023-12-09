import sublime
import sublime_plugin

from .sublime_urtext import refresh_project_text_command

class DebugCommand(sublime_plugin.TextCommand):

    @refresh_project_text_command()
    def run(self):
        node_id = self._UrtextProjectList.current_project.get_node_id_from_position(
            self.view.file_name(), 
            self.view.sel()[0].a)

        if not node_id:
            print('No Node found here')
            return
        print('UNTITLED:')
        print(self._UrtextProjectList.current_project.nodes[node_id].untitled)
        print('DYNAMIC:')
        print(self._UrtextProjectList.current_project.nodes[node_id].dynamic)
        print('NODE ID')
        print(node_id)
        print('LINKS')
        print(self._UrtextProjectList.current_project.nodes[node_id].links)
        print('METADATA')
        self._UrtextProjectList.current_project.nodes[node_id].metadata.log()
        print('Ranges')
        print(self._UrtextProjectList.current_project.nodes[node_id].ranges)
        print('Root')
        print(self._UrtextProjectList.current_project.nodes[node_id].root_node)
        print('Compact')
        print(self._UrtextProjectList.current_project.nodes[node_id].compact)
        print('EXPORTS')
        print(self._UrtextProjectList.current_project.nodes[node_id].export_points)
        print('NODE PARENT')
        print(self._UrtextProjectList.current_project.nodes[node_id].parent)
        print('TREE PARENT')
        print(self._UrtextProjectList.current_project.nodes[node_id].tree_node.parent)
        print('TREE CHILDREN')
        print(self._UrtextProjectList.current_project.nodes[node_id].tree_node.children)
        print('First line title')
        print(self._UrtextProjectList.current_project.nodes[node_id].first_line_title)
        print('------------------------')

class NoAsync(sublime_plugin.TextCommand):

    @refresh_project_text_command()
    def run(self):
        self._UrtextProjectList.current_project.is_async = False