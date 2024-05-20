from .sublime_urtext import refresh_project_text_command
from .sublime_urtext import UrtextTextCommand

class UrtextHomeCommand(UrtextTextCommand):
    
    @refresh_project_text_command()
    def run(self):
        self._UrtextProjectList.current_project.open_home()

class NavigateBackwardCommand(UrtextTextCommand):

    @refresh_project_text_command()
    def run(self):
        self._UrtextProjectList.run_directive('NAVIGATION', 'reverse')

class NavigateForwardCommand(UrtextTextCommand):

    @refresh_project_text_command()
    def run(self):
        self._UrtextProjectList.run_directive('NAVIGATION', 'forward')