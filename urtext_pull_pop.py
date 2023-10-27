from .sublime_urtext import refresh_project_text_command
from .sublime_urtext import UrtextTextCommand
import sublime

class PopNodeCommand(UrtextTextCommand):

    @refresh_project_text_command()
    def run(self):
        if self.view.file_name():
            file_pos = self.view.sel()[0].a + 1
            r = self._UrtextProjectList.current_project.extensions[
                'POP_NODE'
                ].pop_node(
                    self.view.substr(self.view.line(self.view.sel()[0])),
                    self.view.file_name(),
                    file_pos)

class PullNodeCommand(UrtextTextCommand):

    @refresh_project_text_command()
    def run(self):
        if self.view.file_name():
            file_pos = self.view.sel()[0].a
            self._UrtextProjectList.current_project.extensions[
                'PULL_NODE'
                ].pull_node(
                    self.view.substr(self.view.line(self.view.sel()[0])),
                    self.view.file_name(),
                    file_pos)
