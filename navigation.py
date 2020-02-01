
import sublime
import sublime_plugin

from .sublime_urtext import UrtextTextCommand, refresh_project_text_command, show_panel, open_urtext_node

class UrtextHomeCommand(UrtextTextCommand):
    
    @refresh_project_text_command
    def run(self):
        node_id = self._UrtextProjectList.current_project.get_home()
        self._UrtextProjectList.current_project.nav_new(node_id)
        open_urtext_node(self.view, node_id, 0)

class NavigateBackwardCommand(UrtextTextCommand):

    @refresh_project_text_command
    def run(self):
        last_node = self._UrtextProjectList.current_project.nav_reverse()
        if last_node:
            position = self._UrtextProjectList.current_project.nodes[last_node].ranges[0][0]
            open_urtext_node(self.view, last_node, position)

class NavigateForwardCommand(UrtextTextCommand):

    @refresh_project_text_command
    def run(self):
        next_node = self._UrtextProjectList.current_project.nav_advance()
        if next_node:
            position = self._UrtextProjectList.current_project.nodes[next_node].ranges[0][0]
            open_urtext_node(self.view, next_node, position)

class OpenUrtextLinkCommand(UrtextTextCommand):

    @refresh_project_text_command
    def run(self):
        position = self.view.sel()[0].a
        column = self.view.rowcol(position)[1]
        full_line = self.view.substr(self.view.line(self.view.sel()[0]))
        link = self._UrtextProjectList.get_link(full_line, position=column)

        if link == None:    
            return
        if link[0] == 'HTTP':
            if not webbrowser.get().open(link[1]):
                sublime.error_message(
                    'Could not open tab using your "web_browser_path" setting: {}'
                    .format(browser_path))
            return
        if link[0] == 'NODE':
            self._UrtextProjectList.current_project.nav_new(link[1])
            open_urtext_node(self.view, link[1], link[2])
