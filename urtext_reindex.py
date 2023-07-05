from .sublime_urtext import refresh_project_text_command
from .sublime_urtext import UrtextTextCommand
import sublime

class ReIndexFilesCommand(UrtextTextCommand):
    
    @refresh_project_text_command()
    def run(self):
        renamed_files = self._UrtextProjectList.current_project.extensions[
            'REINDEX'
            ].rename_all_files()
        if self._UrtextProjectList.current_project.is_async:
            renamed_files=renamed_files.result()
        if renamed_files:
            for view in self.view.window().views():
                if view.file_name() == None:
                    continue
                if view.file_name() in renamed_files:               
                    view.retarget(renamed_files[view.file_name()])

class RenameFileCommand(UrtextTextCommand):

    @refresh_project_text_command()
    def run(self):
        if self.view.file_name() and self._UrtextProjectList:
            self._UrtextProjectList.current_project.extensions[
                'RENAME_SINGLE_FILE'
                ].set_file_to_rename(self.view.file_name())
            self.view.run_command('save')         