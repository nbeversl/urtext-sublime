import sublime
import sublime_plugin

from .sublime_urtext import refresh_project_text_command

class DebugCommand(sublime_plugin.TextCommand):
    @refresh_project_text_command
    def run(self):
        filename = self.view.file_name()
        position = self.view.sel()[0].a
        node_id = self._UrtextProjectList.current_project.get_node_id_from_position(filename, position)
        self._UrtextProjectList.current_project.nodes[node_id].metadata.log()
        print(self._UrtextProjectList.current_project.nodes[node_id].ranges)
        print(self._UrtextProjectList.current_project.nodes[node_id].root_node)
        print(self._UrtextProjectList.current_project.nodes[node_id].compact)
        print(self._UrtextProjectList.current_project.nodes[node_id].export_points)
        self._UrtextProjectList.current_project.nodes[node_id].metadata.log()