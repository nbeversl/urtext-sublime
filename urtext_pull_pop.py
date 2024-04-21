from .sublime_urtext import refresh_project_text_command
from .sublime_urtext import UrtextTextCommand

class PopNodeCommand(UrtextTextCommand):

    @refresh_project_text_command()
    def run(self):
        if self.view.file_name():
            r = self._UrtextProjectList.current_project.run_directive(
                'POP_NODE',
                self.view.file_name(),
                self.view.sel()[0].a + 1)

class PullNodeCommand(UrtextTextCommand):

    @refresh_project_text_command()
    def run(self):
        if self.view.file_name():
            file_pos = self.view.sel()[0].a
            col_pos = self.view.rowcol(file_pos)[1]
            self._UrtextProjectList.current_project.run_directive(
                'PULL_NODE',
                self.view.substr(self.view.line(self.view.sel()[0])),
                col_pos,
                self.view.file_name(),
                self.view.sel()[0].a)
