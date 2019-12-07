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
import pprint
import logging
import sys

from urtext.project import UrtextProject
from urtext.project import NoProject
from urtext.metadata import NodeMetadata
from urtext.project_list import ProjectList
from urtext.project import node_id_regex

from sublime_plugin import EventListener
import webbrowser

_UrtextProject = None
_UrtextProjectList = None


def filter(filename):
  for fragment in ['urtext_log', '.git','.icloud']:
    if fragment in filename:
      return None
  return filename

class UrtextSaveListener(EventListener):

    def on_query_completions(self, view, prefix, locations):

        if _UrtextProject == None:
            return

        completions = []
        for tag in _UrtextProject.tagnames['tags']:
            completions.append([tag, '/-- tags:'+tag+' --/'])

        return completions

    def on_post_save(self, view):
        if  _UrtextProject and os.path.dirname(view.file_name()) == _UrtextProject.path:
            _UrtextProject.on_modified(view.file_name())   

class KeepPosition(EventListener):

    def on_modified(self, view):
        position = view.sel()

        def restore_position(view, position):
            if not view.is_loading():
                view.show(position)
            else:
                sublime.set_timeout(lambda: restore_position(view, position), 10)

        restore_position(view, position)


def wait_until_loaded(project):
    if project.loaded:
        return project
    else:
        sublime.set_timeout(lambda: return_the_project(project), 10)

def refresh_project(view, init_project=False):

    global _UrtextProject
    
    current_path = get_path(view)

    if _UrtextProject != None:

        if current_path == _UrtextProject.path:
            return wait_until_loaded(_UrtextProject)
        else:
            return focus_urtext_project(current_path, view)

    # no Urtext project yet defined
    if current_path != None:
        _UrtextProject = focus_urtext_project(current_path,
                                              view,
                                              init_project=init_project)

    else:
      return focus_urtext_project(current_path, view)

    # no Urtext project yet defined
    if current_path != None: 
        _UrtextProject = focus_urtext_project(current_path, view, init_project=init_project)
  
    else:
        return None

    #if _UrtextProjectList == None:        
    #  global _UrtextProjectList
    #  _UrtextProjectList = ProjectList(_UrtextProject.path, _UrtextProject.other_projects)

    return _UrtextProject


def focus_urtext_project(path, view, init_project=False):
    global _UrtextProject
    try:
        _UrtextProject = UrtextProject(path, 
            init_project=init_project)
    except NoProject:
        print('No Urtext nodes in this folder')
        return None
    return wait_until_loaded(_UrtextProject)

def get_path(view):  ## makes the path persist as much as possible ##

    if view.file_name():
        return os.path.dirname(view.file_name())
    return get_path_from_window(view.window())


def get_path_from_window(window):

    folders = window.folders()
    if folders:
        return folders[0]

    if window.project_data():
        return window.project_data()['folders'][0]['path']

    return None


def size_to_groups(groups, view):
    panel_size = 1 / groups
    cols = [0]
    cells = [[0, 0, 1, 1]]
    for index in range(1, groups):
        cols.append(cols[index - 1] + panel_size)
        cells.append([index, 0, index + 1, 1])
    cols.append(1)
    view.window().set_layout({"cols": cols, "rows": [0, 1], "cells": cells})


class FindByMetaCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        if refresh_project(self.view) == None:
            return
        self.tagnames = [value for value in _UrtextProject.tagnames]
        self.view.window().show_quick_panel(self.tagnames, self.list_values)

    def list_values(self, index):
        self.selected_tag = self.tagnames[index]
        self.values = [
            value for value in _UrtextProject.tagnames[self.selected_tag]
        ]
        self.values.insert(0, '< all >')
        self.view.window().show_quick_panel(self.values, self.display_files)

    def display_files(self, index):

        self.selected_value = self.values[index]
        if self.selected_value == '< all >':
            pass  # fix this
        self.menu = NodeBrowserMenu(
            _UrtextProject.tagnames[self.selected_tag][self.selected_value])
        show_panel(self.view.window(), self.menu.display_menu,
                   self.open_the_file)

    def open_the_file(self,
                      selected_option):  # copied from below, refactor later.
        if selected_option == -1:
            return
        path = get_path(self.view)
        new_view = self.view.window().open_file(
            os.path.join(
                path,
                self.menu.get_values_from_index(selected_option).filename))
        if len(selected_option) > 3 and selected_option[3] != None:
            self.locate_node(selected_option[3], new_view)

    def list_files(self, index):
        self.selected_value = self.values[index]
        new_view = self.view.window().new_file()
        new_view.set_scratch(True)
        if self.selected_value == '< all >':
            new_view.run_command("insert_snippet", {
                "contents":
                '\nFiles found for tag: %s\n\n' % self.selected_value
            })
            for value in _UrtextProject.tagnames[self.selected_tag]:
                new_view.run_command("insert_snippet",
                                     {"contents": value + "\n"})
                for node in _UrtextProject.tagnames[self.selected_tag][value]:
                    new_view.run_command("insert_snippet",
                                         {"contents": " -> " + node + "\n"})
                new_view.run_command("insert_snippet", {"contents": "\n"})

        else:
            new_view.run_command(
                "insert_snippet", {
                    "contents":
                    '\nFiles found for tag: %s with value %s\n\n' %
                    (self.selected_tag, self.selected_value)
                })
            for node in _UrtextProject.tagnames[self.selected_tag][
                    self.selected_value]:
                new_view.run_command("insert_snippet",
                                     {"contents": " -> " + node + "\n"})


class ShowTagsCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        if refresh_project(self.view) == None:
            return
        self.tag_values = [value for value in _UrtextProject.tagnames['tags']]
        self.tag_values.insert(0, '< all >')
        self.view.window().show_quick_panel(self.tag_values,
                                            self.display_files)

    def display_files(self, index):

        self.selected_value = self.tag_values[index]
        if self.selected_value == '< all >':
            pass  # fix this
        self.menu = NodeBrowserMenu(
            _UrtextProject.tagnames['tags'][self.selected_value])
        show_panel(self.view.window(), self.menu.display_menu,
                   self.open_the_file)

    def open_the_file(self,
                      selected_option):  # copied from below, refactor later.
        if selected_option == -1:
            return
        path = get_path(self.view)
        new_view = self.view.window().open_file(
            os.path.join(
                path,
                self.menu.get_values_from_index(selected_option).filename))
        #if selected_option[3] and selected_option[3] != None:
        #self.locate_node(selected_option[3], new_view)

    def list_files(self, index):
        self.selected_value = self.values[index]
        new_view = self.view.window().new_file()
        new_view.set_scratch(True)
        if self.selected_value == '< all >':
            new_view.run_command("insert_snippet", {
                "contents":
                '\nFiles found for tag: %s\n\n' % self.selected_value
            })
            for value in _UrtextProject.tagnames[self.selected_tag]:
                new_view.run_command("insert_snippet",
                                     {"contents": value + "\n"})
                for node in _UrtextProject.tagnames[self.selected_tag][value]:
                    new_view.run_command("insert_snippet",
                                         {"contents": " -> " + node + "\n"})
                new_view.run_command("insert_snippet", {"contents": "\n"})

        else:
            new_view.run_command(
                "insert_snippet", {
                    "contents":
                    '\nFiles found for tag: %s with value %s\n\n' %
                    (self.selected_tag, self.selected_value)
                })
            for node in _UrtextProject.tagnames[self.selected_tag][
                    self.selected_value]:
                new_view.run_command("insert_snippet",
                                     {"contents": " -> " + node + "\n"})


class TagNodeCommand(sublime_plugin.TextCommand):  #under construction
    def run(self, edit):
        if refresh_project(self.view) == None:
            return
        self.tagnames = [value for value in _UrtextProject.tagnames]
        self.view.window().show_quick_panel(self.tagnames, self.list_values)

    def list_values(self, index):
        if index == -1:
            return
        self.selected_tag = self.tagnames[index]
        self.values = [
            value for value in _UrtextProject.tagnames[self.selected_tag]
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

        if selected_tag not in metadata.get_tag(self.selected_tag):
            print('ADD IT')  # DEBUGGING


class ShowTreeFromNode(sublime_plugin.TextCommand):
    def run(self, edit):

        if refresh_project(self.view) == None:
            return

        def render_tree(view, tree_render):
            if not view.is_loading():
                view.run_command("insert_snippet", {"contents": tree_render})
            else:
                sublime.set_timeout(lambda: render_tree(view, tree_render), 10)

        filename = self.view.file_name()
        position = self.view.sel()[0].a
        node_id = _UrtextProject.get_node_id_from_position(filename, position)
        tree_render = _UrtextProject.show_tree_from(node_id)
        tree_view = target_tree_view(self.view)
        tree_view.erase(edit, sublime.Region(0, tree_view.size()))
        render_tree(tree_view, tree_render)


class ShowTreeFromRootCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        if refresh_project(self.view) == None:
            return

        def render_tree(view, tree_render):
            if not view.is_loading():
                view.run_command("insert_snippet", {"contents": tree_render})
            else:
                sublime.set_timeout(lambda: render_tree(view, tree_render), 10)

        filename = os.path.basename(self.view.file_name())
        position = self.view.sel()[0].a
        node_id = _UrtextProject.get_node_id_from_position(filename, position)
        tree_render = _UrtextProject.show_tree_from(node_id, from_root_of=True)
        tree_view = target_tree_view(self.view)
        tree_view.erase(edit, sublime.Region(0, tree_view.size()))
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


class InsertNodeCommand(sublime_plugin.TextCommand):
    """ inline only, does not make a new file """
    def run(self, edit):
        add_inline_node(self.view, one_line=False)

class InsertNodeSingleLineCommand(sublime_plugin.TextCommand):
    """ inline only, does not make a new file """
    def run(self, edit):
        add_inline_node(self.view, one_line=True, include_timestamp=False)    

def add_inline_node(view, one_line=False, include_timestamp=True):
    if refresh_project(view) == None:
        return
    region = view.sel()[0]
    selection = view.substr(region)
    new_node_contents = _UrtextProject.add_inline_node(
        metadata={},
        contents=selection,
        one_line=one_line,
        include_timestamp=include_timestamp)
    view.run_command("insert_snippet",
                          {"contents": new_node_contents})  # (whitespace)
    view.sel().clear()
    new_cursor_position = sublime.Region(region.a + 3, region.a + 3 ) 
    view.sel().add(new_cursor_position) 


class RenameFileCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        refresh_project(self.view)
        old_filename = self.view.file_name()
        new_filenames = _UrtextProject.rename_file_nodes(old_filename)
        self.view.retarget(
            os.path.join(_UrtextProject.path,
                         new_filenames[os.path.basename(old_filename)]))

class NodeBrowserCommand(sublime_plugin.WindowCommand):
    def run(self):
        if refresh_project(self.window.active_view()) == None:
            return
        global _UrtextProject
        self.menu = NodeBrowserMenu(_UrtextProject.indexed_nodes())
        self.menu.add(_UrtextProject.unindexed_nodes())
        show_panel(self.window, self.menu.display_menu, self.open_the_file)

    def open_the_file(self, selected_option):
        path = get_path(self.window.active_view())
        title = self.menu.get_values_from_index(selected_option).title
        
        new_view = self.window.open_file(
            os.path.join(
                path,
                self.menu.get_values_from_index(selected_option).filename))

        _UrtextProject.nav_new(
            self.menu.get_values_from_index(selected_option).node_id)

        self.locate_node(
            self.menu.get_values_from_index(selected_option).position,
            new_view, title)

    def locate_node(self, position, view, title):
        position = int(position)
        if not view.is_loading():
            view.sel().clear()
            view.show_at_center(position)
            view.sel().add(sublime.Region(position))
        else:
            sublime.set_timeout(
                lambda: self.locate_node(position, view, title), 10)


class NodeBrowserMenu():
    """ custom class to store more information on menu items than is displayed """

    global _UrtextProject

    def __init__(self, node_ids):
        self.full_menu = make_node_menu(node_ids)
        self.display_menu = sort_menu(self.full_menu)

    def get_values_from_index(self, selected_option):
        index = self.display_menu.index(selected_option)
        return self.full_menu[index]

    def add(self, node_ids):
        self.full_menu.extend(make_node_menu(_UrtextProject.unindexed_nodes()))
        self.display_menu = sort_menu(self.full_menu)


class NodeInfo():
    def __init__(self, node_id):
        self.title = _UrtextProject.nodes[node_id].title
        if self.title.strip() == '':
            self.title = '(no title)'
        self.date = _UrtextProject.nodes[node_id].date
        self.filename = _UrtextProject.nodes[node_id].filename
        self.position = _UrtextProject.nodes[node_id].ranges[0][0]
        self.title = _UrtextProject.nodes[node_id].title
        self.node_id = _UrtextProject.nodes[node_id].id


def make_node_menu(node_ids):
    menu = []
    for node_id in node_ids:
        item = NodeInfo(node_id)
        menu.append(item)
    return menu


def sort_menu(menu):
    display_menu = []
    for item in menu:  # there is probably a better way to copy this list.
        item.position = str(item.position)
        new_item = [
            item.title,
            item.date.strftime('<%a., %b. %d, %Y, %I:%M %p>')
        ]
        display_menu.append(new_item)
    return display_menu


class LinkToNodeCommand(sublime_plugin.WindowCommand):
    def run(self):
        if refresh_project(self.window.active_view()) == None:
            return
        self.menu = NodeBrowserMenu(_UrtextProject.nodes)
        show_panel(self.window, self.menu.display_menu, self.link_to_the_file)

    def link_to_the_file(self, selected_option):
        view = self.window.active_view()
        node_id = self.menu.get_values_from_index(selected_option).node_id
        title = self.menu.get_values_from_index(selected_option).title
        view.run_command("insert", {"characters": title + ' >' + node_id})


class LinkNodeFromCommand(sublime_plugin.WindowCommand):
    def run(self):
        if refresh_project(self.window.active_view()) == None:
            return
        self.current_file = os.path.basename(
            self.window.active_view().file_name())
        self.position = self.window.active_view().sel()[0].a
        self.menu = NodeBrowserMenu(_UrtextProject.nodes)
        show_panel(self.window, self.menu.display_menu,
                   self.link_from_the_file)

    def link_from_the_file(self, selected_option):
        new_view = self.window.open_file(
            self.menu.get_values_from_index(selected_option).filename)
        self.show_tip(new_view)

    def show_tip(self, view):
        if not view.is_loading():
            node_id = _UrtextProject.get_node_id_from_position(
                self.current_file, self.position)

            title = _UrtextProject.nodes[node_id].title
            link = title + ' >' + node_id
            sublime.set_clipboard(link)
            view.show_popup('Link to ' + link + ' copied to the clipboard')
        else:
            sublime.set_timeout(lambda: self.show_tip(view), 10)


def show_panel(window, menu, main_callback):
    def private_callback(index):
        if index == -1:
            return
        main_callback(menu[index])

    window.show_quick_panel(menu, private_callback)


def get_contents(view):
    if view != None:
        contents = view.substr(sublime.Region(0, view.size()))
        return contents
    return None


class ToggleTraverse(sublime_plugin.TextCommand):
    def run(self, edit):
        if refresh_project(self.view) == None:
            return
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
        #
        # if 'traverse' is not in settings or it's 'false':
        #
        self.view.settings().set('traverse', 'true')
        self.view.set_status('traverse', 'Traverse: On')

        #
        # Add another group to the left if needed
        #
        groups = self.view.window().num_groups()
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


class TraverseFileTree(sublime_plugin.EventListener):
    
    def on_selection_modified(self, view):

        # give this view a name since we have so many to keep track of
        called_from_view = view 

        global _UrtextProject
        #
        # TODO:
        # Add a failsafe in case the user has closed the next group to the left
        # but traverse is still on.
        #
        if called_from_view.window() == None:
            return

        # how many current groups ("group" = window division)
        self.groups = called_from_view.window().num_groups()        

         # 0-indexed number of the group with the tree view
        self.tree_group = called_from_view.window().active_group() 

        # 0-indexed number of the group with the content 
        # (may not yet exist)
        self.content_group = self.tree_group + 1        
        
        # TAB of the content (right) view. ("sheet" = tab)        
        self.content_tab = called_from_view.window().active_sheet_in_group(
            self.tree_group)
        
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

            tree_view = called_from_view
            this_file = called_from_view.file_name()
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
                filename = _UrtextProject.get_file_name(link[1:])
                if filename:
                    filenames.append(filename)
            

            if len(filenames) > 0:
                filename = filenames[0]
                position = _UrtextProject.nodes[link[1:]].ranges[0][0]
                
                """ If the tree is linking to another part of its own file """
                if filename == os.path.basename(this_file):
                    instances = self.find_filename_in_window(
                        os.path.join(_UrtextProject.path, filename), window)

                    if len(instances) < 2:
                        window.run_command("clone_file")
                        duplicate_file_view = self.find_filename_in_window(
                            os.path.join(_UrtextProject.path, filename),
                            window)[1]

                    if len(instances) >= 2:
                        duplicate_file_view = instances[1]

                    if duplicate_file_view in window.views_in_group(
                            self.content_group):
                        window.focus_view(duplicate_file_view)
                        duplicate_file_view.show_at_center(position)
                        duplicate_file_view.sel().clear()
                        duplicate_file_view.sel().add(position)
                        self.return_to_left(duplicate_file_view, tree_view)
                        return

                    if duplicate_file_view in window.views_in_group(
                            self.tree_group):
                        window.focus_group(self.tree_group)
                        duplicate_file_view.settings().set(
                            'traverse', 'false')  # this is for the cloned view
                        window.set_view_index(duplicate_file_view,
                                              self.content_group, 0)
                        duplicate_file_view.show_at_center(position)
                        window.focus_view(tree_view)
                        window.focus_group(self.tree_group)
                        self.restore_traverse(view, tree_view)
                        return

                else:
                    """ The tree is linking to another file """
                    path = _UrtextProject.path
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
            sublime.set_timeout(lambda: self.return_to_left(wait_view, return_view),
                                10)


class ShowAllNodesCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        if refresh_project(self.view) == None:
            return
        new_view = self.view.window().new_file()
        output = _UrtextProject.list_nodes()
        new_view.run_command("insert", {"characters": output})


class NewNodeCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        global _UrtextProject
        if refresh_project(self.view) == None:
            return
        path = _UrtextProject.path
        new_node = _UrtextProject.new_file_node()
        _UrtextProject.nav_new(new_node['id'])        
        new_view = self.view.window().open_file(os.path.join(path, new_node['filename']))


class NewProjectCommand(sublime_plugin.WindowCommand):
    def run(self):
        global _UrtextProject
        new_view = self.window.new_file()
        new_view.set_scratch(True)
        _UrtextProject = refresh_project(new_view, init_project=True)

        new_view = self.window.open_file(
            os.path.join(_UrtextProject.path, '000.txt'))


class DeleteThisNodeCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        if refresh_project(self.view) == None:
            return
        file_name = os.path.basename(self.view.file_name())
        if self.view.is_dirty():
            self.view.set_scratch(True)
        self.view.window().run_command('close_file')
        os.remove(os.path.join(_UrtextProject.path, file_name))
        _UrtextProject.remove_file(file_name) 

class InsertTimestampCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        if refresh_project(self.view) == None:
            return

        datestamp = _UrtextProject.timestamp(datetime.datetime.now())
        for s in self.view.sel():
            if s.empty():
                self.view.insert(edit, s.a, datestamp)
            else:
                self.view.replace(edit, s, datestamp)


class ConsolidateMetadataCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        if refresh_project(self.view) == None:
            return
        self.view.run_command('save')  # TODO insert notification
        filename = os.path.basename(self.view.file_name())
        position = self.view.sel()[0].a
        node_id = _UrtextProject.get_node_id_from_position(filename, position)
        _UrtextProject.consolidate_metadata(node_id, one_line=True)


class InsertDynamicNodeDefinitionCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        if refresh_project(self.view) == None:
            return
        now = datetime.datetime.now()
        node_id = _UrtextProject.next_index()
        content = '[[ ID:' + node_id + '\n\n ]]'
        for s in self.view.sel():
            if s.empty():
                self.view.insert(edit, s.a, content)
            else:
                view.replace(edit, s, content)


class UrtextSearchProjectCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        if refresh_project(self.view) == None:
            return
        caption = 'Search String: '
        self.view.window().show_input_panel(caption, '', self.search_project,
                                            None, None)

    def search_project(self, string):
        results = _UrtextProject.search(string).split('\n')

        new_view = self.view.window().new_file()
        new_view.set_scratch(True)
        for line in results:
            new_view.run_command("insert_snippet", {"contents": line + '\n'})

class OpenUrtextLinkCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        if refresh_project(self.view) == None:
            return
        position = self.view.sel()[0].a
        column = self.view.rowcol(position)[1]
        full_line = self.view.substr(self.view.line(self.view.sel()[0]))
        link = _UrtextProject.get_link(full_line, position=column)
        if link == None:    
            return
        if link[0] == 'HTTP':
            if not webbrowser.get().open(link[1]):
                sublime.error_message(
                    'Could not open tab using your "web_browser_path" setting: {}'
                    .format(browser_path))
            return
        if link[0] == 'NODE':
            _UrtextProject.nav_new(link[1])
            open_urtext_node(self.view, link[1], link[2])

def open_urtext_node(view, node_id, position):
    def center_node(new_view, position):  # copied from old OpenNode. Refactor
        if not new_view.is_loading():
            new_view.sel().clear()
            # this has to be called both before and after:
            new_view.show_at_center(position)
            new_view.sel().add(sublime.Region(position))
            # this has to be called both before and after:
            new_view.show_at_center(position)
        else:
            sublime.set_timeout(lambda: center_node(new_view, position), 10)

    filename = _UrtextProject.get_file_name(node_id)
    if filename == None:
        return
    file_view = view.window().open_file(
        os.path.join(_UrtextProject.path, filename))

    center_node(file_view, position)


class TagFromOtherNodeCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        if refresh_project(self.view) == None:
            return
        # save the current file first
        full_line = self.view.substr(self.view.line(self.view.sel()[0]))
        links = re.findall(
            '(?:[^\|]*\s)?>(' + node_id_regex + ')(?:\s[^\|]*)?\|?', full_line)
        if len(links) == 0:
            return
        path = get_path(self.view)
        node_id = links[0]
        timestamp = _UrtextProject.timestamp(datetime.datetime.now())

        # TODO move this into urtext, not Sublime
        tag = '/-- tags: done ' + timestamp + ' --/'
        _UrtextProject.tag_other_node(node_id, tag)
        _UrtextProject.update()
     

class GenerateTimelineCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        if refresh_project(self.view) == None:
            return
        new_view = self.view.window().new_file()
        nodes = [
            _UrtextProject.nodes[node_id] for node_id in _UrtextProject.nodes
        ]
        timeline = _UrtextProject.build_timeline(nodes)
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

    def run(self, edit):
        if refresh_project(self.view) == None:
            return
        filename = os.path.basename(self.view.file_name())
        position = self.view.sel()[0].a
        node_id = _UrtextProject.get_node_id_from_position(filename, position)
        render = _UrtextProject.get_node_relationships(node_id)

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


class ReIndexFilesCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        if refresh_project(self.view) == None:
            return
        global _UrtextProject
        renamed_files = _UrtextProject.reindex_files()
        for view in self.view.window().views():
            if view.file_name() == None:
                continue
            if os.path.basename(view.file_name()) in renamed_files:
                view.retarget(
                    os.path.join(
                        _UrtextProject.path,
                        renamed_files[os.path.basename(view.file_name())]))


class AddNodeIdCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        if refresh_project(self.view) == None:
            return
        global _UrtextProject
        new_id = _UrtextProject.next_index()
        self.view.run_command("insert_snippet",
                              {"contents": "/-- ID: " + new_id + " --/"})


class DebugCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        if refresh_project(self.view) == None:
            return
        filename = self.view.file_name()
        position = self.view.sel()[0].a
        node_id = _UrtextProject.get_node_id_from_position(filename, position)


class ImportProjectCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        global _UrtextProject
        _UrtextProject = UrtextProject(get_path(self.view),
                                       import_project=True)


class ShowUrtextHelpCommand(sublime_plugin.WindowCommand):
    def run(self):
        global _UrtextProject
        active_window = sublime.active_window()
        this_file_path = os.path.dirname(__file__)
        open_windows = sublime.windows()
        
        #for window in open_windows:
        _UrtextProject = UrtextProject(
            os.path.join(os.path.dirname(__file__), "documentation"))
        """if help_view != None:
        window.focus_view(help_view)
        if window != active_window:
          sublime.message_dialog('Urtext help is open in another window. Use Super - ~ to switch between windows  ')
        return"""
        sublime.run_command("new_window")

        help_view = sublime.active_window().new_file()
        open_urtext_node(help_view, _UrtextProject.settings['home'], 0)


class OpenUrtextLogCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        if refresh_project(self.view) == None:
            return
        file_view = self.view.window().open_file(
            os.path.join(_UrtextProject.path,
                         _UrtextProject.settings['logfile']))

        def go_to_end(view):
            if not view.is_loading():
                view.show_at_center(sublime.Region(view.size()))
                view.sel().add(sublime.Region(view.size()))
                view.show_at_center(sublime.Region(view.size()))
            else:
                sublime.set_timeout(lambda: go_to_end(view), 10)

        go_to_end(file_view)


class UrtextHomeCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        if refresh_project(self.view) == None:
            return
        node_id = _UrtextProject.settings['home']
        _UrtextProject.nav_new(node_id)
        open_urtext_node(self.view, node_id, 0)


class UrtextNodeListCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        if refresh_project(self.view) == None:
            return
        _UrtextProject.nav_new('zzz')
        open_urtext_node(self.view, 'zzz', 0)


class UrtextMetadataListCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        if refresh_project(self.view) == None:
            return
        _UrtextProject.nav_new('zzy')
        open_urtext_node(self.view, 'zzy', 0)


class UrtextReloadProjectCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        if refresh_project(self.view) == None:
            return
        global _UrtextProject
        current_path = get_path(self.view)
        if current_path != None:
            _UrtextProject = focus_urtext_project(current_path, self.view)
        else:
            print('No Urtext Project')
            return None

        if _UrtextProjectList == None:
            _UrtextProjectList = ProjectList(_UrtextProject.path,
                                             _UrtextProject.other_projects)

        return _UrtextProject


class NavigateBackwardCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        if refresh_project(self.view) == None:
            return
        last_node = _UrtextProject.nav_reverse()
        if last_node:
            position = _UrtextProject.nodes[last_node].ranges[0][0]
            open_urtext_node(self.view, last_node, position)

class NavigateForwardCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        if refresh_project(self.view) == None:
            return
        # and open this node
        next_node = _UrtextProject.nav_advance()
        if next_node:
            position = _UrtextProject.nodes[next_node].ranges[0][0]
            open_urtext_node(self.view, next_node, position)

class ExportAsMarkdownCommand(sublime_plugin.TextCommand):
    def run(self, edit):        
        if refresh_project(self.view) == None:
            return
        filename = self.view.file_name()
        markdown_filename = filename.replace('.txt','.md') 
        _UrtextProject.export(filename, markdown_filename, kind = 'Markdown')
        markdown_view = self.view.window().open_file(os.path.join(_UrtextProject.path, markdown_filename))

class ExportFileAsHtmlCommand(sublime_plugin.TextCommand):
    def run(self, edit):        
        if refresh_project(self.view) == None:
            return
        filename = self.view.file_name()
        _UrtextProject.export(  filename, 
                                html_filename, 
                                kind='HTML',
                                single_file=True,
                                strip_urtext_syntax=False, 
                                style_titles=False)
        html_view = self.view.window().open_file(os.path.join(_UrtextProject.path, html_filename))

class ExportProjectAsHtmlCommand(sublime_plugin.TextCommand):
    def run(self, edit):        
        if refresh_project(self.view) == None:
            return

        _UrtextProject.export_project(jekyll=True, style_titles=False)


class SyncGoogleCalendarCommand(sublime_plugin.TextCommand):
    def run(self, edit):        
        if refresh_project(self.view) == None:
            return

        _UrtextProject.sync_to_google_calendar()

class CompactNodeCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        if refresh_project(self.view) == None:
            return
        add_compact_node(self.view)

class PopNodeCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        if refresh_project(self.view) == None:
            return
        filename = self.view.file_name()
        position = self.view.sel()[0].a
        new_position = _UrtextProject.pop_node(filename=filename, position=position)
        if new_position:
            self.view.sel().clear()
            new_cursor_position = sublime.Region(new_position, new_position) 
            self.view.sel().add(new_cursor_position) 


class DebugCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        if refresh_project(self.view) == None:
            return
        filename = self.view.file_name()
        position = self.view.sel()[0].a
        node_id = _UrtextProject.get_node_id_from_position(filename, position)
        _UrtextProject.nodes[node_id].metadata.log()
        print(_UrtextProject.nodes[node_id].ranges)
        print(_UrtextProject.nodes[node_id].root_node)
        print(_UrtextProject.nodes[node_id].split)
        print(_UrtextProject.nodes[node_id].compact)


class RebuildSearchIndexCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        if refresh_project(self.view) == None:
            return
        _UrtextProject.rebuild_search_index()


class SplitNodeCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        if refresh_project(self.view) == None:
            return
        node_id = _UrtextProject.next_index()
        self.view.run_command("insert_snippet",
                          {"contents": '/-- id:'+node_id+' --/\n% '})




def add_compact_node(view):
    if refresh_project(view) == None:
        return
    region = view.sel()[0]
    
    selection = view.substr(region)
    new_node_contents = _UrtextProject.add_compact_node(contents=selection)
    view.run_command("insert_snippet",
                          {"contents": new_node_contents})
    view.sel().clear()
    new_cursor_position = sublime.Region(region.a + 2, region.a + 2) 
    view.sel().add(new_cursor_position) 
