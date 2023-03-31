from .sublime_urtext import refresh_project_text_command, urtext_on_modified
from .sublime_urtext import UrtextTextCommand

class PopNodeCommand(UrtextTextCommand):

    @refresh_project_text_command()
    def run(self):
        self.view.run_command('save')
        urtext_on_modified(self.view)
        file_pos = self.view.sel()[0].a + 1
        r = self._UrtextProjectList.current_project.extensions[
            'POP_NODE'
            ].pop_node(
                self.view.substr(self.view.line(self.view.sel()[0])),
                self.view.file_name(),
                file_pos = file_pos,
                )

class PullNodeCommand(UrtextTextCommand):

    @refresh_project_text_command()
    def run(self):
        self.view.run_command('save')  # TODO insert notification
        urtext_on_modified(self.view)
        if self.view.file_name():
            file_pos = self.view.sel()[0].a
            file_to_close = self._UrtextProjectList.current_project.extensions[
                'PULL_NODE'
                ].pull_node(
                    self.view.substr(self.view.line(self.view.sel()[0])),
                    self.view.file_name(),
                    file_pos = file_pos,
                    )
            if file_to_close:
                if self._UrtextProjectList.current_project.is_async:
                    file_to_close=file_to_close.result()
                for view in self.window.views():
                    if view.file_name() == file_to_close:
                        view.set_scratch(True)
                        view.close()
                        return