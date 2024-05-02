from .sublime_urtext import refresh_project_text_command
from .sublime_urtext import UrtextTextCommand
import sublime

class ReIndexFilesCommand(UrtextTextCommand):
    
    @refresh_project_text_command()
    def run(self):
        renamed_files = self._UrtextProjectList.current_project.run_directive('REINDEX')
        if renamed_files:
            for view in self.view.window().views():
                if view.file_name() in renamed_files:               
                    view.retarget(renamed_files[view.file_name()])

class RenameFileCommand(UrtextTextCommand):

    @refresh_project_text_command()
    def run(self):
        if self.view.file_name() and self._UrtextProjectList:
            self.view.run_command('save')
            self._UrtextProjectList.current_project.run_directive(
                'RENAME_SINGLE_FILE',
                self.view.file_name()),
