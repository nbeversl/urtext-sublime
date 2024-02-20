from .sublime_urtext import refresh_project_text_command
from .sublime_urtext import UrtextTextCommand

class PopNodeCommand(UrtextTextCommand):

    @refresh_project_text_command()
    def run(self):
        if self._UrtextProjectList.can_use_extension('POP_NODE'):
            if self.view.file_name():
                r = self._UrtextProjectList.current_project.extensions[
                    'POP_NODE'
                    ].pop_node_from_editor(
                        self.view.substr(self.view.line(self.view.sel()[0])),
                        self.view.file_name(),
                        self.view.sel()[0].a + 1)

class PullNodeCommand(UrtextTextCommand):

    @refresh_project_text_command()
    def run(self):
        if self._UrtextProjectList.can_use_extension('PULL_NODE'):
            if self.view.file_name():
                self._UrtextProjectList.current_project.extensions[
                    'PULL_NODE'
                    ].pull_node(
                        self.view.substr(self.view.line(self.view.sel()[0])),
                        self.view.file_name(),
                        self.view.sel()[0].a)
