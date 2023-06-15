from .sublime_urtext import refresh_project_text_command
from .sublime_urtext import UrtextTextCommand
import sublime

class PopNodeCommand(UrtextTextCommand):

    @refresh_project_text_command()
    def run(self):
        if self.view.file_name():
            self.view.run_command('save', {"async" : True})        

            def pop_node(view):
                if not view.is_dirty():
                    file_pos = self.view.sel()[0].a + 1
                    r = self._UrtextProjectList.current_project.extensions[
                        'POP_NODE'
                        ].pop_node(
                            self.view.substr(self.view.line(self.view.sel()[0])),
                            self.view.file_name(),
                            file_pos = file_pos,
                            )
                else: sublime.set_timeout(lambda: pop_node(self.view), 50) 

            pop_node(self.view)

class PullNodeCommand(UrtextTextCommand):

    @refresh_project_text_command()
    def run(self):

        if self.view.file_name():
            self.view.run_command('save', {"async" : True})

            def pull_node(view):
                if not view.is_dirty():
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
                        for v in self.window.views():
                            if v.file_name() == file_to_close:
                                v.set_scratch(True)
                                v.close()
                                return

                else: sublime.set_timeout(lambda: pull_node(self.view), 50) 

            pull_node(self.view)
