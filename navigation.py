from .sublime_urtext import refresh_project_text_command, open_urtext_node
from .sublime_urtext import UrtextTextCommand

class UrtextHomeCommand(UrtextTextCommand):
    
    @refresh_project_text_command()
    def run(self):
        home = self._UrtextProjectList.current_project.get_home()
        if home:
            self._UrtextProjectList.nav_new(home)
            open_urtext_node(self.view, home)

class NavigateBackwardCommand(UrtextTextCommand):

    @refresh_project_text_command()
    def run(self):
        last_node = self._UrtextProjectList.nav_reverse()
        if last_node:
            open_urtext_node(self.view, last_node)

class NavigateForwardCommand(UrtextTextCommand):

    @refresh_project_text_command()
    def run(self):
        next_node = self._UrtextProjectList.nav_advance()
        if next_node:
            open_urtext_node(self.view, next_node)