
import sublime
import sublime_plugin
from sublime_plugin import EventListener
import time
import datetime
import os
from .sublime_urtext import refresh_project_event_listener, UrtextTextCommand, size_to_groups

is_browsing_history = False

class TakeSnapshot(EventListener):

    def __init__(self):
        self.last_time = time.time()

    @refresh_project_event_listener
    def on_modified(self, view):
        global is_browsing_history
        if is_browsing_history:
            return
        now = time.time()
        if now - self.last_time < 10:
            return None
        self.last_time = now 

        take_snapshot(view, self._UrtextProjectList.current_project)

def take_snapshot(view, project):
    if not view:
        return
    contents = get_contents(view)
    if not view.file_name():
        return
    filename = os.path.basename(view.file_name())
    project.run_action('HISTORY_SNAPSHOT',
        view.substr(sublime.Region(0, view.size())),
        view.file_name()
        )



def get_contents(view):
    if view != None:
        contents = view.substr(sublime.Region(0, view.size()))
        return contents
    return None


class ToggleHistoryTraverse(UrtextTextCommand):
    """ Toggles history traversing on/off """

    @refresh_project_event_listener
    def run(self, view):
        global is_browsing_history
        window = self.view.window()
        history_view = None
        for view in window.views():
            if view.name() == 'urtext_history': 
                history_view = view

        if history_view:
            history_group = window.get_view_index(history_view)[0]
            history_view.close()
            file_view = window.active_view_in_group(history_group-1)
            window.focus_group(history_group-1)
            window.focus_view(file_view)
            groups = window.num_groups()                
            groups -= 1
            if groups == 0:
                groups = 1
            window.focus_group(groups-1) 
            if file_view:
                size_to_groups(groups, file_view)
            is_browsing_history = False  
            return
    
        is_browsing_history = True

        # take a snapshot now so we don't mess up what's there, in case it isn't saved:
        take_snapshot(self.view, self._UrtextProjectList.current_project)

        groups = self.view.window().num_groups()
        size_to_groups(groups + 1, self.view)

        window = self.view.window()
        history_group = window.active_group() + 1
        window.focus_group(history_group)
        history_view = window.new_file()
        history_view.set_scratch(True)
        history_view.set_name('urtext_history')
        history_view.set_status('urtext_history', 'History: On')
        history_view.run_command("insert_snippet", {"contents": ''}) # this just triggers on_modified()

class TraverseHistoryView(EventListener):

    def __init__(self):
        self.current_file = None
        self.history = None
        self.string_timestamps = None
        self.rewriting = False
 
    @refresh_project_event_listener
    def on_selection_modified(self, view):

        if view.name() != 'urtext_history':
            return None
        if self.rewriting:
            return

        history_view = view

        # 1-indexed number of current groups ("group" = window division)
        self.groups = history_view.window().num_groups()        

        # 0-indexed number of the group with the history view
        # history group is always made to be the view this was called from.
        self.history_group = history_view.window().active_group() 

        # 0-indexed number of the group with the content 
        # (may not yet exist)
        self.content_group = self.history_group -1

        # TAB of the content (left) view. ("sheet" = tab)        
        self.content_tab = history_view.window().active_sheet_in_group(self.content_group)

        # View of the file in the content tab 
        self.file_view = self.content_tab.view()

        filename = self.file_view.file_name()

        if self.current_file != filename:
            self.current_file = filename

      
        new_history = self._UrtextProjectList.current_project.run_action(
            'HISTORY_GET_HISTORY',
            '',
            self.current_file).result()
        
        if not new_history:
            return None
      
        ts_format =  self._UrtextProjectList.current_project.settings['timestamp_format']
        string_timestamps = [datetime.datetime.fromtimestamp(int(i)).strftime(ts_format) for i in sorted(new_history.keys(),reverse=True)]

        if string_timestamps != self.string_timestamps or not get_contents(history_view).strip():
            self.string_timestamps = string_timestamps
            self.history = new_history
            self.rewriting = True
            history_view.set_read_only(False)
            history_view.run_command("select_all")
            history_view.run_command("right_delete")
            history_view.run_command("insert_snippet", {"contents": 'HISTORY for '+ os.path.basename(filename)+'\n'})        
            for line in self.string_timestamps:
                history_view.run_command("insert_snippet", {"contents": line+'\n'})
            self.rewriting = False
            history_view.set_read_only(True)
            history_view.sel().clear()
            history_view.sel().add(sublime.Region(0,0))
            history_view.set_viewport_position((0,0))
            return
        

        line = view.substr(history_view.line(history_view.sel()[0]))
        if line in self.string_timestamps:           
            index = self.string_timestamps.index(line) 
            self.rewriting = True
            self.show_state(index)
            self.rewriting = False

    def show_state(self, index):

        state = self._UrtextProjectList.current_project.run_action(
            'APPLY_HISTORY_PATCHES',
            str(index),
            self.file_view.file_name()).result()
        self.file_view.run_command("select_all")
        self.file_view.run_command("right_delete")
        for line in state.split('\n'):
            self.file_view.run_command("append", {"characters": line+ "\n" })