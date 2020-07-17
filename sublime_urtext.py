"""
This file is part of Urtext for Sublime Text.

Urtext is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Urtext is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Urtext.  If not, see <https://www.gnu.org/licenses/>.

"""
import sublime
import sublime_plugin
import os
import re
import datetime
import time
import concurrent.futures
import subprocess
import webbrowser
from urtext.metadata import NodeMetadata
from urtext.project_list import ProjectList
from urtext.project import node_id_regex
from sublime_plugin import EventListener

_SublimeUrtextWindows = {}
_UrtextProjectList = None
urtext_initiated = False
quick_panel_waiting = False
quick_panel_active  = False
quick_panel_id = 0
is_browsing_history = False

class UrtextTextCommand(sublime_plugin.TextCommand):

    def __init__(self, view):
        self.view = view
        self.window = view.window()

def refresh_project_text_command(import_project=False):
    """ 
    Determine which project we are in based on the Sublime window.
    Used as a decorator in every command class.
    """    
    def middle(function):

        def wrapper(*args, **kwargs):

            global urtext_initiated
            urtext_initiated = True

            
            view = args[0].view
            edit = args[1]

            _UrtextProjectList = initialize_project_list(view)
            if not _UrtextProjectList:
                return None

            window = sublime.active_window()
            if not window:
                print('NO WINDOW')
                print(function) # debugging
                return

            view = window.active_view()
            window_id = window.id()

            # get the current project first from the view
            if view.file_name():
                current_path = os.path.dirname(view.file_name())
                _UrtextProjectList.set_current_project(current_path)
                if import_project :
                    _UrtextProjectList.import_project(current_path)
            
            # then try the window
            elif window_id in _SublimeUrtextWindows:
                current_path = _SublimeUrtextWindows[window_id]
                _UrtextProjectList.set_current_project(current_path)
                if import_project :
                    _UrtextProjectList.import_project(current_path)

            # otherwise assign the current window to the current project
            elif _UrtextProjectList.current_project:
                _SublimeUrtextWindows[window_id] = _UrtextProjectList.current_project.path
                
            # If there is a current project, return it
            if _UrtextProjectList.current_project:
                args[0].edit = edit
                args[0]._UrtextProjectList = _UrtextProjectList
                view.set_status('urtext_project', 'Urtext Project: '+_UrtextProjectList.current_project.title)
                return function(args[0])

            elif import_project:
                current_paths = window.folders()
                for path in current_paths:
                    _UrtextProjectList.import_project(path)

            return None

        return wrapper

    return middle

def refresh_project_event_listener(function):

    def wrapper(*args):
        view = args[1]
        
        _UrtextProjectList = initialize_project_list(view)
        if not _UrtextProjectList:
            return None

        window = sublime.active_window()
        if not window:
            print('NO WINDOW')
            return
        
        view = window.active_view()
        window_id = window.id()

        if view and view.file_name():
            current_path = os.path.dirname(view.file_name())
            _UrtextProjectList.set_current_project(current_path)
            args[0]._UrtextProjectList = _UrtextProjectList
            return function(args[0], view)

        if window_id in _SublimeUrtextWindows:
            current_path = _SublimeUrtextWindows[window_id]
            _UrtextProjectList.set_current_project(current_path)
            args[0]._UrtextProjectList = _UrtextProjectList
            return function(args[0], view)

        if _UrtextProjectList.current_project:
            _SublimeUrtextWindows[window_id] = _UrtextProjectList.current_project.path
            args[0]._UrtextProjectList = _UrtextProjectList

            return function(args[0], view)
        return None

    return wrapper


def initialize_project_list(view, init_project=False, reload_projects=False):

    global _UrtextProjectList

    if reload_projects:
        _UrtextProjectList = None        

    if _UrtextProjectList == None:
        current_path = get_path(view)
        if not current_path:
            return None
        _UrtextProjectList = ProjectList(current_path, watchdog=True)
        
    return _UrtextProjectList

def get_path(view):
    """ 
    given a view or None, establishes the current active path,
    either from the view or from the current active window.
    """

    current_path = None
    if view and view.file_name():
        return os.path.dirname(view.file_name())
    window = sublime.active_window()
    if not window:
        print('No active window')
        return None
    window_variables = window.extract_variables()
    if 'folder' in window_variables:
        return window.extract_variables()['folder']
    return None
      
class ListProjectsCommand(UrtextTextCommand):
    
    @refresh_project_text_command()
    def run(self):
        show_panel(
            self.view.window(), 
            self._UrtextProjectList.project_titles(), 
            self.set_window_project)

    def set_window_project(self, title):
        self._UrtextProjectList.set_current_project(title)
        self.view.set_status('urtext_project', 'Urtext Project: '+_UrtextProjectList.current_project.title)
        _SublimeUrtextWindows[self.view.window().id()] = self._UrtextProjectList.current_project.path
        node_id = self._UrtextProjectList.nav_current()
        self._UrtextProjectList.nav_new(node_id)
        open_urtext_node(self.view, node_id)


class MoveFileToAnotherProjectCommand(UrtextTextCommand):
    
    @refresh_project_text_command()
    def run(self):
        show_panel(
            self.window,
            self._UrtextProjectList.project_titles(), 
            self.move_file)

    def move_file(self, new_project_title):
                
        replace_links = sublime.yes_no_cancel_dialog(
            'Do you want to also rewrite links to nodes in this file as links to the new project?')
        replace_links = True if replace_links == sublime.DIALOG_YES else False
        filename = self.view.file_name()

        success = self._UrtextProjectList.move_file(
            filename, 
            new_project_title,
            replace_links=replace_links)

        self.view.window().run_command('close_file')

        last_node = _UrtextProjectList.nav_reverse()
        if last_node:
            open_urtext_node(self.view, last_node)

        # temporary.
        if not success:
            sublime.message_dialog('File was moved but error occured. Check the console.')
        else:
            sublime.message_dialog('File was moved')


class UrtextSaveListener(EventListener):

    def __init__(self):
        
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)

    def on_query_completions(self, view, prefix, locations):

        if not _UrtextProjectList.current_project:
            return

        current_path = os.path.dirname(view.file_name())
      
        if _UrtextProjectList.get_project(current_path):
        
            completions = []
            
            for pair in list(_UrtextProjectList.get_all_meta_pairs()):
                completions.append([pair, '/-- '+pair+' --/'])

            return completions

    # @refresh_project_event_listener
    # def on_post_save(self, view):
        
    #     if not view.file_name():
    #         return

    #     future = self._UrtextProjectList.on_modified(view.file_name())

    #     #always take a snapshot manually on save
    #     take_snapshot(view, self._UrtextProjectList.current_project)

    #     if future: 
    #         self.executor.submit(refresh_open_file, future, view)

class KeepPosition(EventListener):

    @refresh_project_event_listener
    def on_modified(self, view):
        if not view:
            return

        position = view.sel()
        def restore_position(view, position):
            if not view.is_loading():
                view.show(position)
            else:
                sublime.set_timeout(lambda: restore_position(view, position), 10)

        restore_position(view, position)


class UrtextHomeCommand(UrtextTextCommand):
    
    @refresh_project_text_command()
    def run(self):
        node_id = _UrtextProjectList.current_project.get_home()
        _UrtextProjectList.nav_new(node_id)
        open_urtext_node(self.view, node_id)

class NavigateBackwardCommand(UrtextTextCommand):

    @refresh_project_text_command()
    def run(self):
        last_node = _UrtextProjectList.nav_reverse()
        if last_node:
            open_urtext_node(self.view, last_node)

class NavigateForwardCommand(UrtextTextCommand):

    @refresh_project_text_command()
    def run(self):
        next_node = _UrtextProjectList.nav_advance()
        if next_node:
            open_urtext_node(self.view, next_node)

class OpenUrtextLinkCommand(UrtextTextCommand):

    @refresh_project_text_command()
    def run(self):
        position = self.view.sel()[0].a
        column = self.view.rowcol(position)[1]
        full_line = self.view.substr(self.view.line(self.view.sel()[0]))
        link = _UrtextProjectList.get_link_and_set_project(full_line, position=column)

        if link == None:   
            print('NO LINK') 
            return

        kind = link[0]
        if kind == 'EDITOR_LINK':
            file_view = self.view.window().open_file(link[1])

        if kind == 'NODE':
            _UrtextProjectList.nav_new(link[1])
            open_urtext_node(self.view, link[1])

        if kind == 'HTTP':
            success = webbrowser.get().open(link[1])
            if not success:
                self.log('Could not open tab using your "web_browser_path" setting')       

        if kind == 'FILE':
            open_external_file(link[1])

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


class JumpToSource(EventListener):

    @refresh_project_event_listener
    def on_modified(self, view):
        """
        problematic -- this doesn't work if the view is dirty.

        TODO: revise
        For now, making available only if few is not dirty. However this should
        still be usable in many cases.
        """
        if not view:
            return
        position = view.sel()[0].a
        filename = view.file_name()
        if filename:
            destination_node = _UrtextProjectList.is_in_export(filename, position)
            if destination_node:
                view.window().run_command('undo') # undo the manual change made to the view
                open_urtext_node(view, destination_node[0])
                center_node(view, destination_node[1])

def take_snapshot(view, project):
    contents = get_contents(view)
    if view.file_name():
        filename = os.path.basename(view.file_name())
        project.snapshot_diff(filename, contents)

class ToggleHistoryTraverse(UrtextTextCommand):
    """ Toggles history traversing on/off """

    @refresh_project_text_command()
    def run(self):
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

        new_history = _UrtextProjectList.current_project.get_history(self.current_file)

        if not new_history:
            return None

        ts_format = '%a., %b. %d, %Y, %I:%M:%S %p'
        string_timestamps = [datetime.datetime.fromtimestamp(i).strftime(ts_format) for i in sorted(new_history.keys(),reverse=True)]

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
            self.show_state(index)

    def show_state(self, index):
        state = _UrtextProjectList.current_project.apply_patches(self.history, distance_back=index)
        self.file_view.run_command("select_all")
        self.file_view.run_command("right_delete")
        for line in state.split('\n'):
            self.file_view.run_command("append", {"characters": line+ "\n" })

class NodeBrowserCommand(UrtextTextCommand):
    
    @refresh_project_text_command()
    def run(self):
        self.menu = NodeBrowserMenu(
            self._UrtextProjectList, 
            project=self._UrtextProjectList.current_project
            )

        show_panel(
            self.view.window(), 
            self.menu.display_menu, 
            self.open_the_file)

    def open_the_file(self, selected_option):        
        selected_item = self.menu.get_selection_from_index(selected_option)
        self._UrtextProjectList.set_current_project(selected_item.project_title)
        self._UrtextProjectList.nav_new(selected_item.node_id)   
        open_urtext_node(self.view, selected_item.node_id)


class BacklinksBrowser(NodeBrowserCommand):

    @refresh_project_text_command()
    def run(self):

        self.menu = NodeBrowserMenu(
            self._UrtextProjectList, 
            project=self._UrtextProjectList.current_project,
            nodes=self._UrtextProjectList.current_project.get_links_to(get_node_id(self.view))
            )
        show_panel(
            self.view.window(), 
            self.menu.display_menu, 
            self.open_the_file)


class AllProjectsNodeBrowser(NodeBrowserCommand):
    
    @refresh_project_text_command()
    def run(self):
        self.menu = NodeBrowserMenu(
            self._UrtextProjectList, 
            project=None
            )
        show_panel(
            self.view.window(), 
            self.menu.display_menu, 
            self.open_the_file)

class FullTextSearchCommand(UrtextTextCommand):

    @refresh_project_text_command()
    def run(self):
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=10)
        self.view.window().show_input_panel(
            'search terms',
            '',
            self.show_results,
            None,
            None
            )
    
    def show_results(self, string):
        search_results = self._UrtextProjectList.current_project.search_term(string)
        search_results.initiate_search()
        self.results_view = self.window.new_file()
        self.results_view.set_scratch(True)
        self.results_view.set_syntax_file('sublime_urtext.sublime-syntax')

        while self.results_view.is_loading():
            time.sleep(0.1)

        self.executor.submit(self.do_search, search_results)

    def do_search(self, search_results):

        t = []
        while not search_results.complete:
            r = len(t)
            t = search_results.result            
            if len(t) > r:
                for item in t[r:]:
                    self.results_view.run_command("append", {"characters": item+'\n'})

        final_results = search_results.result            
        if t != final_results:
            final_results = final_results[len(t):]
            for item in final_results:
                self.results_view.run_command("append", {"characters": item +'\n'})

def size_to_groups(groups, view):
    panel_size = 1 / groups
    cols = [0]
    cells = [[0, 0, 1, 1]]
    for index in range(1, groups):
        cols.append(cols[index - 1] + panel_size)
        cells.append([index, 0, index + 1, 1])
    cols.append(1)
    view.window().set_layout({"cols": cols, "rows": [0, 1], "cells": cells})

class TagNodeCommand(UrtextTextCommand):  #under construction
    
    @refresh_project_text_command()
    def run(self):
        self.keynames = [value for value in self._UrtextProjectList.current_project.keynames]
        self.view.window().show_quick_panel(self.keynames, self.list_values)

    def list_values(self, index):
        if index == -1:
            return
        self.selected_tag = self.keynames[index]
        self.values = [
            value for value in self._UrtextProjectList.current_project.keynames[self.selected_tag]
        ]
        self.view.window().show_quick_panel(self.values, self.insert_tag)

    def insert_tag(self, index):
        if index == -1:
            return
        self.selected_value = self.values[index]
        timestamp = self.timestamp(datetime.datetime.now())
        tag = '/-- ' + self.selected_tag + ': ' + self.selected_value + ' ' + timestamp + ' --/'
        self.view.run_command("insert_snippet", {"contents": tag})

    def locate_from_in_node(self, index):  # useful in the future.
        selected_tag = self.values[index]
        max_size = self.view.size()
        region = self.view.sel()[0]
        subnode_regexp = re.compile(r'{{(?!.*{{)(?:(?!}}).)*}}', re.DOTALL)
        selection = self.view.substr(region)
        while not subnode_regexp.search(selection):
            a = region.a
            b = region.b
            if selection[:2] != '{{':
                a -= 1
            if selection[-2:] != '}}':
                b += 1
            region = sublime.Region(a, b)
            if a == 0 or b == max_size:  # entire file
                break
            selection = self.view.substr(region)

        metadata = urtext.metadata.NodeMetadata(selection[2:-2])
        # this all successfully identifies which node the cursor is in.
        # from here this should probably be done in the metadata class, not here.
        # get the metadata string out, probably using regex
        # find a place where the tag is

        if selected_tag not in metadata.get_meta_value(self.selected_tag):
            print('ADD IT')  # DEBUGGING

class ShowTreeFromNode(UrtextTextCommand):
    
    @refresh_project_text_command()
    def run(self):

        def render_tree(view, tree_render):
            if not view.is_loading():
                view.run_command("insert_snippet", {"contents": tree_render})
            else:
                sublime.set_timeout(lambda: render_tree(view, tree_render), 10)

        tree_render = self._UrtextProjectList.current_project.show_tree_from(get_node_id(self.view))
        tree_view = target_tree_view(self.view)
        tree_view.erase(self.edit, sublime.Region(0, tree_view.size()))
        render_tree(tree_view, tree_render)

class ShowTreeFromRootCommand(UrtextTextCommand):
    
    @refresh_project_text_command()
    def run(self):

        def render_tree(view, tree_render):
            if not view.is_loading():
                view.run_command("insert_snippet", {"contents": tree_render})
            else:
                sublime.set_timeout(lambda: render_tree(view, tree_render), 10)

        tree_render = self._UrtextProjectList.current_project.show_tree_from(
            get_node_id(self.view), from_root_of=True)
        tree_view = target_tree_view(self.view)
        tree_view.erase(self.edit, sublime.Region(0, tree_view.size()))
        render_tree(tree_view, tree_render)

def target_tree_view(view):

    filename = view.file_name()
    if filename == None:
        return

    def locate_view(view, name):
        all_views = view.window().views()
        for view in all_views:
            if view.name() == name:
                return view
        return None

    tree_name = filename + 'TREE'  # Make a name for the view
    tree_view = locate_view(view, tree_name)
    if tree_view == None:
        tree_view = view.window().new_file()
        tree_view.set_name(filename + 'TREE')
        tree_view.set_scratch(True)

    # copied from traverse. Should refactor
    groups = view.window().num_groups()  
    
    active_group = view.window().active_group()  # 0-indexed
    if active_group == 0 or view.window().get_view_index(
            tree_view)[0] != active_group - 1:
        if groups > 1 and view.window().active_view_in_group(
                active_group - 1).file_name() == None:
            view.window().set_view_index(tree_view, active_group - 1, 0)
        else:
            groups += 1
            panel_size = 1 / groups
            cols = [0]
            cells = [[0, 0, 1, 1]]
            for index in range(1, groups):
                cols.append(cols[index - 1] + panel_size)
                cells.append([index, 0, index + 1, 1])
            cols.append(1)
            view.window().set_layout({
                "cols": cols,
                "rows": [0, 1],
                "cells": cells
            })
            view.settings().set("word_wrap", False)

            sheets = tree_view.window().sheets_in_group(active_group)
            index = 0
            for sheet in sheets:
                tree_view.window().set_sheet_index(
                    sheet,
                    groups - 1,  # 0-indexed from 1-indexed value
                    index)
                index += 1
            view.window().set_view_index(tree_view, active_group, 0)
            view.window().focus_group(active_group)
    return tree_view

class InsertInterlinksCommand(UrtextTextCommand):
    
    @refresh_project_text_command()
    def run(self):
        insertion =  self._UrtextProjectList.current_project.insert_interlinks(get_node_id(self.view))
        self.view.run_command("insert_snippet",
                          {"contents": insertion}) 

class InsertNodeCommand(sublime_plugin.TextCommand):
    """ inline only, does not make a new file """
    @refresh_project_text_command()
    def run(self):
        add_inline_node(self.view)

class InsertNodeSingleLineCommand(sublime_plugin.TextCommand):
    """ inline only, does not make a new file """
    @refresh_project_text_command()
    def run(self):
        add_inline_node(self.view, trailing_id=True, include_timestamp=False)    


def add_inline_node(view, 
    include_timestamp=True, 
    trailing_id=False,
    locate_inside=True):

    region = view.sel()[0]
    selection = view.substr(region)
    new_node = _UrtextProjectList.current_project.add_inline_node(
        metadata={},
        contents=selection,
        trailing_id=trailing_id,
        include_timestamp=include_timestamp)
    new_node_contents = new_node[0]
    view.run_command("insert_snippet",
                          {"contents": new_node_contents})  # (whitespace)
    if locate_inside:
        view.sel().clear()
        new_cursor_position = sublime.Region(region.a + 3, region.a + 3 ) 
        view.sel().add(new_cursor_position) 
    return new_node[1] # id


class RenameFileCommand(UrtextTextCommand):

    @refresh_project_text_command()
    def run(self):
        old_filename = self.view.file_name()
        new_filenames = self._UrtextProjectList.current_project.rename_file_nodes(old_filename)
        self.view.retarget(
            os.path.join(self._UrtextProjectList.current_project.path,
                         new_filenames[old_filename]))

class NodeBrowserMenu:
    """ custom class to store more information on menu items than is displayed """

    def __init__(self, 
        project_list, 
        project=None, 
        nodes=[]):

        self.full_menu = make_node_menu(
            project_list,
            project=project,
            nodes=nodes)

        self.display_menu = sort_menu(self.full_menu)

    def get_selection_from_index(self, selected_option):
        index = self.display_menu.index(selected_option)
        return self.full_menu[index]

class NodeInfo():

    def __init__(self, node_id, project_list, project=None):    
        if not project:
            project = project_list.current_project
        self.title =project.nodes[node_id].title
        if self.title.strip() == '':
            self.title = '(no title)'
        self.date =project.nodes[node_id].date
        self.filename = project.nodes[node_id].filename
        self.position = project.nodes[node_id].ranges[0][0]
        self.title = project.nodes[node_id].title
        self.node_id = project.nodes[node_id].id
        self.project_title = project.title

def make_node_menu(
    project_list, 
    project=None, 
    nodes=[]):

    menu = []

    projects = project_list.projects

    if project:
        projects = [project]

    if nodes:
        for node_id in nodes:
            menu.append(
                  NodeInfo(
                    node_id, 
                    project_list))
        return menu
    
    for single_project in projects:
        for node_id in single_project.all_nodes():
            menu.append(
                NodeInfo(
                    node_id, 
                    project_list, 
                    project=single_project))
 
    return menu

def sort_menu(menu):
    display_menu = []
    for item in menu:  # there is probably a better way to copy this list.
        item.position = str(item.position)
        new_item = [
            item.title,
            item.project_title + ' - ' + item.date.strftime('<%a., %b. %d, %Y, %I:%M %p>'),            
        ]
        display_menu.append(new_item)
    return display_menu

def show_panel(window, menu, main_callback):
    """ shows a quick panel with an option to cancel if -1 """
    def private_callback(index):
        if index == -1:
            return
        # otherwise return the main callback with the index of the selected item
        main_callback(menu[index])
    window.show_quick_panel(menu, private_callback)

class LinkToNodeCommand(UrtextTextCommand):

    @refresh_project_text_command()
    def run(self):
        self.menu = NodeBrowserMenu(self._UrtextProjectList, project=None)
        show_panel(self.view.window(), self.menu.display_menu, self.link_to_the_node)

    def link_to_the_node(self, selected_option):
        if not self.window:
            return
        view = self.window.active_view()
        selected_option = self.menu.get_selection_from_index(selected_option)
        link = self._UrtextProjectList.build_contextual_link(
            selected_option.node_id,
            project_title=selected_option.project_title)    
        view.run_command("insert", {"characters": link})

class CopyLinkToHereCommand(UrtextTextCommand):
    """
    Copy a link to the node containing the cursor to the clipboard.
    Does not include project title.
    """
    @refresh_project_text_command()
    def run(self):
        link = self.get_link(get_node_id(self.window.active_view()))
        sublime.set_clipboard(link)        
        self.view.show_popup(link + '\ncopied to the clipboard', 
            max_width=1800, 
            max_height=1000 
                # max_height does not work correctly. 
                # workaround for now using max_width
                # FUTURE: Could also hard wrap.
                # https://github.com/sublimehq/sublime_text/issues/2854
                # https://github.com/SublimeLinter/SublimeLinter/pull/1609
                # https://github.com/SublimeLinter/SublimeLinter/issues/1601
            )

    def get_link(self, node_id):
        return self._UrtextProjectList.build_contextual_link(node_id)       

class CopyLinkToHereWithProjectCommand(CopyLinkToHereCommand):
    """
    Copy a link to the node containing the cursor to the clipboard.
    Does not include project title.
    """
    def get_link(self, node_id):
        return self._UrtextProjectList.build_contextual_link(
            node_id, 
            include_project=True)

def get_contents(view):
    if view != None:
        contents = view.substr(sublime.Region(0, view.size()))
        return contents
    return None

class ShowAllNodesCommand(UrtextTextCommand):

    @refresh_project_text_command()
    def run(self):
        new_view = self.view.window().new_file()
        output = self._UrtextProjectList.current_project.list_nodes()
        new_view.run_command("insert", {"characters": output})

class NewNodeCommand(UrtextTextCommand):

    @refresh_project_text_command()
    def run(self):
        path = self._UrtextProjectList.current_project.path
        new_node = self._UrtextProjectList.current_project.new_file_node()
        self._UrtextProjectList.nav_new(new_node['id'])        
        new_view = self.view.window().open_file(os.path.join(path, new_node['filename']))

class NewNodeWithLinkCommand(UrtextTextCommand):

    @refresh_project_text_command()
    def run(self):
        path = self._UrtextProjectList.current_project.path
        new_node = self._UrtextProjectList.current_project.new_file_node()
        new_node_id = new_node['id']
        self.view.run_command("insert", {"characters":' >' + new_node_id})
        self.view.run_command("save")
        self._UrtextProjectList.nav_new(new_node_id)
        new_view = self.view.window().open_file(os.path.join(path, new_node['filename']))

class NewProjectCommand(UrtextTextCommand):

    def run(self, view):
        global _UrtextProjectList        
        current_path = get_path(self.view)
        new_view = self.window.new_file()
        new_view.set_scratch(True)
        _UrtextProjectList.init_new_project(current_path)
        new_view.close()
        
class DeleteThisNodeCommand(UrtextTextCommand):

    @refresh_project_text_command()
    def run(self):
        file_name = os.path.basename(self.view.file_name())
        if self.view.is_dirty():
            self.view.set_scratch(True)
        self.view.window().run_command('close_file')
        self._UrtextProjectList.delete_file(file_name) 

class InsertTimestampCommand(UrtextTextCommand):

    @refresh_project_text_command()
    def run(self):
        datestamp = self._UrtextProjectList.current_project.timestamp(datetime.datetime.now())
        for s in self.view.sel():
            if s.empty():
                self.view.insert(self.edit, s.a, datestamp)
            else:
                self.view.replace(self.edit, s, datestamp)

class ConsolidateMetadataCommand(UrtextTextCommand):

    @refresh_project_text_command()
    def run(self):
        self.view.run_command('save')  # TODO insert notification
        node_id = get_node_id(self.view)
        if node_id:
            self._UrtextProjectList.current_project.consolidate_metadata(node_id, one_line=True)
            return True    
        print('No Urtext node or no Urtext node with ID found here.')
        return False

class InsertDynamicNodeDefinitionCommand(UrtextTextCommand):

    @refresh_project_text_command()
    def run(self):
        now = datetime.datetime.now()
        node_id = add_inline_node(
            self.view, 
            include_timestamp=False,
            locate_inside=False)
        # This should possibly be moved into Urtext as a utility method.
        position = self.view.sel()[0].a
        content = '\n\n[[ ID(' + node_id + ')\n\n ]]'
        
        for s in self.view.sel():
            if s.empty():
                self.view.insert(self.edit, s.a, content)
            else:
                view.replace(self.edit, s, content)

        self.view.sel().clear()
        new_cursor_position = sublime.Region(position + 12, position + 12) 
        self.view.sel().add(new_cursor_position) 
        
class TagFromOtherNodeCommand(UrtextTextCommand):

    @refresh_project_text_command()
    def run(self):
        # save the current file first
        full_line = self.view.substr(self.view.line(self.view.sel()[0]))
        links = re.findall(
            '(?:[^\|]*\s)?>(' + node_id_regex + ')(?:\s[^\|]*)?\|?', full_line)
        if len(links) == 0:
            return
        path = get_path(self.view)
        node_id = links[0]
        timestamp = self._UrtextProjectList.current_project.timestamp(datetime.datetime.now())

        # TODO move this into urtext, not Sublime
        tag = '/-- tags: done ' + timestamp + ' --/'
        _UrtextProjectList.current_project.tag_other_node(node_id, tag)

class GenerateTimelineCommand(UrtextTextCommand):

    @refresh_project_text_command()
    def run(self):
        new_view = self.view.window().new_file()
        timeline = self._UrtextProjectList.current_project.build_timeline()
        self.show_stuff(new_view, timeline)
        new_view.set_scratch(True)

    def show_stuff(self, view, timeline):
        if not view.is_loading():
            view.run_command("append", {"characters": timeline + '\n|'})
        else:
            sublime.set_timeout(lambda: self.show_stuff(view, timeline), 10)

class ShowLinkedRelationshipsCommand(sublime_plugin.TextCommand):
    """ Display a tree of all nodes connected to this one """

    # TODO: for files that link to the same place more than one time,
    # show how many times on one tree node, instead of showing multiple nodes
    # would this require building the tree after scanning all files?
    #
    # Also this command does not currently utilize the global array, it reads files manually.
    # Necessary to change it?

    @refresh_project_text_command()
    def run(self):
        render = self._UrtextProjectList.current_project.get_node_relationships(get_node_id(self.view))

        def draw_tree(view, render):
            if not view.is_loading():
                view.run_command("insert_snippet", {"contents": render})
                view.set_scratch(True)
            else:
                sublime.set_timeout(lambda: draw_tree(view, render), 10)

        window = self.view.window()
        window.focus_group(0)  # always show the tree on the leftmost focus'
        new_view = window.new_file()
        window.focus_view(new_view)
        draw_tree(new_view, render)

class ReIndexFilesCommand(UrtextTextCommand):
    
    @refresh_project_text_command()
    def run(self):
        renamed_files = self._UrtextProjectList.current_project.reindex_files()
        for view in self.view.window().views():
            if view.file_name() == None:
                continue
            if os.path.basename(view.file_name()) in renamed_files:
                view.retarget(
                    os.path.join(
                        self._UrtextProjectList.current_project.path,
                        renamed_files[os.path.basename(view.file_name())]))

class AddNodeIdCommand(UrtextTextCommand):

    @refresh_project_text_command()
    def run(self):
        new_id = self._UrtextProjectList.current_project.next_index()
        self.view.run_command("insert_snippet",
                              {"contents": "/-- ID: " + new_id + " --/"})

class ImportProjectCommand(UrtextTextCommand):

    @refresh_project_text_command(import_project=True)
    def run(self):
        pass


class OpenUrtextLogCommand(UrtextTextCommand):
    
    @refresh_project_text_command()
    def run(self):

        log_id = self._UrtextProjectList.current_project.get_log_node()
        if not log_id:
            return

        open_urtext_node(self.view, log_id)

        def go_to_end(view):
            if not view.is_loading():
                view.show_at_center(sublime.Region(view.size()))
                view.sel().add(sublime.Region(view.size()))
                view.show_at_center(sublime.Region(view.size()))
            else:
                sublime.set_timeout(lambda: go_to_end(view), 10)

        go_to_end(self.view)

class UrtextNodeListCommand(UrtextTextCommand):

    @refresh_project_text_command()
    def run(self):
        if 'zzz' in self._UrtextProjectList.current_project.nodes:
            self._UrtextProjectList.nav_new('zzz')
            open_urtext_node(self.view, 'zzz')
        else:
            print('No zzz node')

class UrtextReloadProjectCommand(UrtextTextCommand):

    @refresh_project_text_command()
    def run(self):
        if initialize_project_list(self.view, reload_projects=True) == None:
            print('No Urtext Project')
            return None

class ExportFromIdCommand(UrtextTextCommand):

    @refresh_project_text_command()
    def run(self):        
        exported = self._UrtextProjectList.current_project.export_from_root_node(get_node_id(self.view))
        new_view = self.view.window().new_file()
        new_view.run_command("insert_snippet", {
                "contents":
               exported
            })

class ExportFileAsHtmlCommand(UrtextTextCommand):

    @refresh_project_text_command()
    def run(self):        
        filename = self.view.file_name()
        self._UrtextProjectList.current_project.export(  filename, 
                                html_filename, 
                                kind='HTML',
                                single_file=True,
                                strip_urtext_syntax=False, 
                                style_titles=False)
        html_view = self.view.window().open_file(os.path.join(self._UrtextProjectList.current_project.path, html_filename))

class ExportProjectAsHtmlCommand(UrtextTextCommand):
    
    @refresh_project_text_command()
    def run(self):        
        self._UrtextProjectList.current_project.export_project(jekyll=True, style_titles=False)

class CompactNodeCommand(UrtextTextCommand):

    @refresh_project_text_command()
    def run(self):
        add_compact_node(self.edit, self.view)

class PopNodeCommand(UrtextTextCommand):

    @refresh_project_text_command()
    def run(self):
        filename = self.view.file_name()
        position = self.view.sel()[0].a
        future = self._UrtextProjectList.current_project.pop_node(filename=filename, position=position)

class SplitNodeCommand(UrtextTextCommand):

    @refresh_project_text_command()
    def run(self):
        node_id = self._UrtextProjectList.current_project.next_index()
        self.view.run_command("insert_snippet",
                          {"contents": '/-- id:'+node_id+' --/\n% '})

class RandomNodeCommand(UrtextTextCommand):

    @refresh_project_text_command()
    def run(self):
        node_id = self._UrtextProjectList.current_project.random_node()
        self._UrtextProjectList.nav_new(node_id)
        open_urtext_node(self.view, node_id)


class ToggleTraverse(UrtextTextCommand):

    @refresh_project_text_command()
    def run(self):

        # determine whether then view already has traverse settings attached
        # if already on, turn it off
        if self.view.settings().has('traverse'):
            if self.view.settings().get('traverse') == 'true':
                self.view.settings().set('traverse', 'false')
                self.view.set_status('traverse', 'Traverse: Off')
                groups = self.view.window().num_groups()
                groups -= 1
                if groups == 0:
                    groups = 1
                size_to_groups(groups, self.view)
                self.view.settings().set("word_wrap", True)
                return

        # otherwise, if 'traverse' is not in settings or it's 'false',
        # turn it on.
        self.view.settings().set('traverse', 'true')
        self.view.set_status('traverse', 'Traverse: On')

        #
        # Add another group to the left if needed
        #
        groups = self.view.window().num_groups() # 1-indexed
        active_group = self.view.window().active_group()  # 0-indexed
        if active_group + 1 == groups:
            groups += 1
        size_to_groups(groups, self.view)
        self.view.settings().set("word_wrap", False)

        #
        # move any other open tabs to rightmost pane.
        #

        views = self.view.window().views_in_group(active_group)
        index = 0
        for view in views:
            if view != self.view:
                self.view.window().set_view_index(
                    view,
                    groups - 1,  # 0-indexed from 1-indexed value
                    index)
                index += 1

        self.view.window().focus_group(active_group)

class ShowAccessHistory(UrtextTextCommand):
    @refresh_project_text_command()
    def run(self):
        self._UrtextProjectList.current_project._show_access_history()


class ExportToIcs(UrtextTextCommand):
    @refresh_project_text_command()
    def run(self):
        self._UrtextProjectList.current_project.export_to_ics()


class TraverseFileTree(EventListener):

    def on_selection_modified(self, view):
        
        if not _UrtextProjectList or not _UrtextProjectList.current_project:
            return

        # give this view a name since we have so many to keep track of
        called_from_view = view 
        if called_from_view.name() == 'urtext_history':
            return
        #
        # TODO:
        # Add a failsafe in case the user has closed the next group to the left
        # but traverse is still on.
        #
        if called_from_view.window() == None:
            return
        if called_from_view.settings().get('traverse') == 'false':
            return

        # 1-indexed number of current groups ("group" = window division)
        self.groups = called_from_view.window().num_groups()        

        # 0-indexed number of the group with the tree view
        # Tree group is always made to be the view this was called from.
        self.tree_group = called_from_view.window().active_group() 
        if called_from_view.window().active_group() + 1 == self.groups:
            # if the called_from_group is rightmost, return
            # OR what if checking to see if the filenames are the same?
            return

        # 0-indexed number of the group with the content 
        # (may not yet exist)
        self.content_group = self.tree_group + 1        
        
        # TAB of the content (right) view. ("sheet" = tab)        
        self.content_tab = called_from_view.window().active_sheet_in_group(self.tree_group)

        
        # the contents of the content tab. 
        contents = get_contents(self.content_tab.view())

        """ 
        Scroll to a given position of the content 
        and then return focus to the tree view.
        """
        def move_to_location(moved_view, 
            position, 
            tree_view):
            
            if not moved_view.is_loading():

                # focus on the window division with the content
                moved_view.window().focus_group(self.content_group)

                # show the content tab with the given position as center
                self.content_tab.view().show_at_center(position)

                # Make this the selected spot and set word wrap
                moved_view.sel().clear()
                moved_view.sel().add(position)
                moved_view.settings().set("word_wrap", "auto")

                # refocus the tree (left) view
                self.return_to_left(moved_view, tree_view)

            else:
                sublime.set_timeout(lambda: move_to_location(moved_view, position),
                                    10)

        """ Only if Traverse is on for this group (window division) """

        if called_from_view.settings().get('traverse') == 'true':

            # the tree view is always the view that was modified.
            # assign it a name, get its filename and window

            this_file = called_from_view.file_name()
            
            if not this_file:
                return

            tree_view = called_from_view
            window = called_from_view.window()

            # Get the current line and find links
            full_line = view.substr(view.line(view.sel()[0]))
            links = re.findall('>' + node_id_regex, full_line)

            # if there are no links on this line:
            if len(links) == 0:  
                return

            # get all the filenames corresponding to the links
            filenames = []
            for link in links:
                filename = _UrtextProjectList.current_project.get_file_name(link[1:])
                if filename:
                    filenames.append(filename)

            if len(filenames) > 0:
                filename = filenames[0]
                position = _UrtextProjectList.current_project.nodes[link[1:]].ranges[0][0]
                
                """ If the tree is linking to another part of its own file """
                if filename == os.path.basename(this_file):
                    
                    instances = self.find_filename_in_window(
                        os.path.join(_UrtextProjectList.current_project.path, filename), window)

                    # Only allow two total instances of this file; 
                    # one to navigate, one to edit
                    if len(instances) < 2:
                        window.run_command("clone_file")
                        duplicate_file_view = self.find_filename_in_window(
                            os.path.join(_UrtextProjectList.current_project.path, filename),
                            window)[1]

                    if len(instances) >= 2:
                        duplicate_file_view = instances[1]
                    
                    """ If the duplicate view is in the content group """
                    if duplicate_file_view in window.views_in_group(self.content_group):
                        window.focus_view(duplicate_file_view)
                        duplicate_file_view.show_at_center(position)
                        duplicate_file_view.sel().clear()
                        duplicate_file_view.sel().add(position)
                        
                        self.return_to_left(duplicate_file_view, tree_view)
                        duplicate_file_view.settings().set('traverse', 'false')
                        return

                    """ If the duplicate view is in the tree group """
                    if duplicate_file_view in window.views_in_group(self.tree_group):
                        window.focus_group(self.tree_group)
                        duplicate_file_view.settings().set('traverse', 'false')  # this is for the cloned view
                        window.set_view_index(duplicate_file_view, self.content_group, 0)
                        duplicate_file_view.show_at_center(position)
                        window.focus_view(tree_view)
                        window.focus_group(self.tree_group)
                        self.restore_traverse(view, tree_view)
                        return

                else:
                    """ The tree is linking to another file """
                    path = _UrtextProjectList.current_project.path
                    window.focus_group(self.content_group)
                    file_view = window.open_file(os.path.join(path, filename),
                                                 sublime.TRANSIENT)
                    file_view.show_at_center(position)
                    file_view.sel().clear()
                    file_view.sel().add(position)
                    window.focus_group(self.tree_group)
                    self.return_to_left(file_view, tree_view)

    def find_filename_in_window(self, filename, window):
        instances = []
        for view in window.views():
            if view.file_name() == filename:
                instances.append(view)
        return instances

    def restore_traverse(self, wait_view, traverse_view):
        if not wait_view.is_loading():
            traverse_view.settings().set('traverse', 'true')
        else:
            sublime.set_timeout(
                lambda: self.return_to_left(wait_view, traverse_view), 10)
            return

    """ 
    Return to the left (tree) view,
    after waiting for another view to finish loading.
    """

    def return_to_left(self, 
        wait_view, 
        return_view):
        
        if not wait_view.window():
            return

        if not wait_view.is_loading():
            wait_view.window().focus_view(return_view)
            wait_view.window().focus_group(self.tree_group)
        
        else:
            sublime.set_timeout(lambda: self.return_to_left(wait_view, return_view), 10)

"""
Utility functions
"""
def open_urtext_node(view, node_id, project=None, position=0):
    
    if project:
        _UrtextProjectList.set_current_project(project.title)

    filename, position = _UrtextProjectList.current_project.get_file_and_position(node_id)
    if filename == None:
        return
    file_view = view.window().find_open_file(filename)
    if not file_view:
        file_view = view.window().open_file(filename)
    view.window().focus_view(file_view)
    center_node(file_view, position)
    return file_view
    """
    Note we do not involve this function with navigation, since it is
    use for purposes including forward/backward navigation and shouldn't
    duplicate/override any of the operations of the methods that call it.
    """

def center_node(new_view, position): 
        if not new_view.is_loading():
            new_view.sel().clear()
            # this has to be called both before and after:
            new_view.show_at_center(position)
            new_view.sel().add(sublime.Region(position, position))
            # this has to be called both before and after:
            new_view.show_at_center(position)
        else:
            sublime.set_timeout(lambda: center_node(new_view, position), 10)

def add_compact_node(edit, view):
    
    region = view.sel()[0]
    selection = view.substr(region)
    line = view.line(region) # get full line
    next_line_down = line.b
    new_node_contents = _UrtextProjectList.current_project.add_compact_node(contents=selection)

    view.sel().clear()
    view.sel().add(next_line_down) 
    view.run_command("insert_snippet",
                          {"contents": '\n'+new_node_contents})

    new_cursor_position = sublime.Region(next_line_down + 3, next_line_down + 3) 
    view.sel().clear()
    view.sel().add(new_cursor_position) 
    view.erase(edit, region)

def get_path(view):  ## makes the path persist as much as possible ##

    if view.file_name():
        return os.path.dirname(view.file_name())
    if view.window():
        return get_path_from_window(view.window())
    return None

def get_path_from_window(window):

    folders = window.folders()
    if folders:
        return folders[0]
    if window.project_data():
        return window.project_data()['folders'][0]['path']
    return None

def refresh_open_file(future, view):
    changed_files = future.result()
    open_files = view.window().views()
    for filename in open_files:
        if os.path.basename(filename) in changed_files:
            view.run_command('revert') # undocumented

def open_external_file(filepath):
    print(filepath)
    if sublime.platform() == "osx":
        subprocess.Popen(('open', filepath))
    elif sublime.platform() == "windows":
        os.startfile(filepath)
    elif sublime.platform() == "linux":
        subprocess.Popen(('xdg-open', filepath))

def get_node_id(view):
    global _UrtextProjectList
    filename = os.path.basename(view.file_name())
    position = view.sel()[0].a
    return _UrtextProjectList.current_project.get_node_id_from_position(filename, position)



