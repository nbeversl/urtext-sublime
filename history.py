
import sublime
import sublime_plugin
from sublime_plugin import EventListener
import time
import datetime
import os
from .sublime_urtext import refresh_project_text_command, refresh_project_event_listener, UrtextTextCommand

is_browsing_history = False

class TakeSnapshot(EventListener):

    def __init__(self):
        self.last_time = time.time()

    @refresh_project_event_listener
    def on_modified(self, view):
        self.take_snapshot(view)

    @refresh_project_event_listener
    def on_post_save_async(self, view):
        self.take_snapshot(view)

    def take_snapshot(self, view):
        global is_browsing_history
        if is_browsing_history:
            return
        now = time.time()
        if now - self.last_time < self._UrtextProjectList.current_project.settings['history_interval']:
            return None
        self.last_time = now 
        take_snapshot(view, self._UrtextProjectList.current_project)


def take_snapshot(view, project):
    if view and view.file_name():
        project.run_action('HISTORY_SNAPSHOT',
            view.substr(sublime.Region(0, view.size())),
            os.path.basename(view.file_name())
            )

def get_contents(view):
    if view != None: 
        return view.substr(sublime.Region(0, view.size()))
    return None

class BrowseHistoryCommand(UrtextTextCommand):

    @refresh_project_text_command()
    def run(self):
        
        if self.view.file_name():

            global is_browsing_history
            is_browsing_history = True
            
            take_snapshot(self.view, self._UrtextProjectList.current_project)

            self.current_file = os.path.basename(self.view.file_name())
            new_history = self._UrtextProjectList.current_project.run_action(
                'HISTORY_GET_HISTORY',
                '',
                self.current_file)
            
            if self._UrtextProjectList.current_project.is_async:
                new_history = new_history.result()
                
            if not new_history:
                return None
            
            ts_format =  self._UrtextProjectList.current_project.settings['timestamp_format']
            string_timestamps = [datetime.datetime.fromtimestamp(int(i)).strftime(ts_format) for i in sorted(new_history.keys(),reverse=True)]

            self.view.window().show_quick_panel(
                string_timestamps,
                self.done,
                on_highlight=self.show_state,
                )

    def done(self, index):
        global is_browsing_history
        is_browsing_history=False

    def show_state(self, index):
        state = self._UrtextProjectList.current_project.run_action(
            'APPLY_HISTORY_PATCHES',
            str(index),
            os.path.basename(self.view.file_name()))

        if self._UrtextProjectList.current_project.is_async:
            state = state.result()

        self.view.run_command("select_all")
        self.view.run_command("right_delete")
        for line in state.split('\n'):
            self.view.run_command("append", {"characters": line+ "\n" })
    