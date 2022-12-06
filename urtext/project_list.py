# -*- coding: utf-8 -*-
"""
This file is part of Urtext.

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
import concurrent.futures
import os
import re

if os.path.exists(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'sublime.txt')):
    from .project import UrtextProject, NoProject
else:
    from urtext.project import UrtextProject, NoProject

class ProjectList():

    def __init__(self, 
        base_path, 
        initial_project=None,
        first_project=False):
        self.projects = []
        self.base_path = base_path
        self.current_project = None
        self.navigation = []
        self.nav_index = -1
        
        if first_project:
            self.init_new_project(base_path)    
        self._add_folder(base_path)
        
        if self.projects:
            self.current_project = self.projects[0]
        if initial_project:
            self.set_current_project(initial_project)
        self._propagate_projects(None)
    
    def _add_folder(self, folder):
        """ recursively add folders """
        if folder not in [p.path for p in self.projects]:
            try:
                if os.path.basename(folder) not in ['history','img','files' ]:
                    project = UrtextProject(folder)
                    self.projects.append(project)
            except NoProject:
                print('No project found in '+folder)
            sub_dirs = next(os.walk(folder))[1]
            for subdir in sub_dirs:
                if subdir not in ['.git','.DS_Store','/','history','files']:
                    self._add_folder(os.path.join(folder, subdir))

    def get_link_and_set_project(self, 
            string, 
            filename, 
            col_pos=0,
            file_pos=0):

        """
        Given a line of text, looks for a link to a node or project
        with node, sets the current project to the containing project,
        and returns the link information. Does not update navigation,
        this should be done by the calling procedure.
        """
        node_id = None
        project_link_r = re.compile(r'(=>\"(.*?)\")?.*?(\|.+>([0-9,a-z,A-Z,\s]+)\b)?')
        link = project_link_r.search(string)
        project_name = link.group(2)
        node_id = link.group(4)
        """ If a project name has been specified, locate the project and node """
        if project_name:
            if not self.set_current_project(project_name):
                return None
            if node_id and node_id in self.current_project.nodes:
                    return {
                        'kind' : "OTHER_PROJECT", 
                        'link' : node_id, 
                        'dest_position' : 0,
                    }

            return {
                'kind': 'NODE', 
                'link': self.current_project.nav_current(), 
                'dest_position' : 0,
                }
        
        """ Otherwise, set the project, search the link for a link in the current project """
        
        self.set_current_project(os.path.basename(filename))
        link = self.current_project.get_link( 
            string, 
            filename, 
            col_pos=col_pos,
            file_pos=file_pos
            )
        return link

    def on_modified(self, filenames):
        modified_files = []
        if not isinstance(filenames, list):
            filenames = [filenames]
        for f in filenames:
            project = self._get_project_from_path(os.path.dirname(f))
            if project:
                modified_files.append(project.on_modified(os.path.basename(f)))
        return modified_files         
        
    def _propagate_projects(self, future):
        # wait on future to complete
        if future: # future can be None
            s = future.result()
        for project in self.projects:
            project.project_list = self

    def _get_project_from_path(self, path):
        for project in self.projects:
            if path == project.path:
                return project
        return None

    def _get_project_from_title(self, title):
        for project in self.projects:
            if title == project.title:
                return project
        return None

    def get_project(self, title_or_path):
        project = self._get_project_from_title(title_or_path) 
        if not project:
            project = self._get_project_from_path(title_or_path) 
        return project

    def set_current_project(self, title_or_path):
        project = self.get_project(title_or_path) 
        if not project:
            return None
        if  ( not self.current_project ) or ( project and project.title != self.current_project.title ) :
           self.current_project = project
           print('Switched to project: ' + self.current_project.title)
        return project

    def build_contextual_link(self, 
        node_id,
        project_title=None, 
        pointer=False, 
        include_project=False):
        if node_id:
            
            if project_title == None:
                project = self.current_project
            else:
                project = self.get_project(project_title)
            node_title = ''
            if node_id in project.nodes:
                node_title = project.nodes[node_id].get_title()
            link = '| ' + node_title + ' >'
            if pointer:
                link +='>'
            if include_project or project != self.current_project:
                link = '=>"' + project.title +'"'+link
            return link

    def nav_current(self):
        return self.current_project.nav_current()
        
    def project_titles(self):
        titles = []
        for project in self.projects:
            titles.append(project.title)
        return titles

    def get_current_project(self, path):
        for project in self.projects:
            if project.path == path:
                return project
        return None

    def init_new_project(self, path):
        if path in self.project_titles():
            print('Path already in use.')
            return None
        if not os.path.exists(path):
            os.makedirs(path)
        project = UrtextProject(path, new_project=True)
        if project:
            self.projects.append(project)
            self.set_current_project(path)
            
        print('Initialized New project at '+os.path.abspath(path))

    def visit_file(self, filename):
        if filename:
            path = os.path.dirname(filename)
            self.set_current_project(path)
            return self.current_project.visit_file(filename)

    def move_file(self, 
        filename, 
        destination_project_name_or_path,
        replace_links=True):

        """
        Move a file from one project to another, checking for
        node ID duplication in the new project location, and 
        optionally replacing links to every affected node.
        """

        destination_project = self.get_project(destination_project_name_or_path)
        if not destination_project:
            print('Destination project `'+ destination_project_name_or_path +'` was not found.')
            return None

        filename = os.path.basename(filename)
        if filename not in self.current_project.files:
            print('File '+ filename +' not included in the current project.')
            return None

        affected_nodes = self.current_project.files[filename].nodes.keys()
        
        self.current_project.remove_file(filename) # also updates the source project

        os.rename(
            os.path.join( self.current_project.path, filename),
            os.path.join( destination_project.path, filename)
            )

        """
        add_file() will raise an exception if the file makes
        duplicate nodes in the destination project
        """
        try:
            destination_project.add_file(filename)    
        except:
            return None
 
        if replace_links:
            for node_id in affected_nodes:
                self.replace_links(
                    self.current_project.title,
                    destination_project.title,                   
                    node_id)

        # also move the history file
        history_file = filename.replace('.txt','.pkl')
        if os.path.exists(os.path.join(self.current_project.path, 'history', history_file)):
            os.rename(os.path.join(self.current_project.path, 'history', history_file),
                  os.path.join(destination_project.path, 'history', history_file))

        return True

    def get_all_meta_pairs(self):
        meta_values = []
        for project in self.projects:
            meta_pairs = project.get_all_meta_pairs()
            for pair in meta_pairs:
                if pair not in meta_values:
                    meta_values.append(pair)
        return meta_values

    def replace_links(self, old_project_path_or_title, new_project_path_or_title, node_id):
        old_project = self.get_project(old_project_path_or_title)
        new_project = self.get_project(new_project_path_or_title)
        old_project.replace_links(node_id, new_project=new_project.title)
    
    def titles(self):
        title_list = {}
        for project in self.projects:
            for node_id in project.nodes:
                title_list[project.nodes[node_id].get_title()] = (project.title, node_id)
        return title_list

    def is_in_export(self, filename, position):
        if not self.current_project:
            return None
        return self.current_project.is_in_export(filename, position)

    """
    Project List Navigation
    """

    def nav_advance(self):

        if not self.navigation:
            return None
            
        if self.nav_index == len(self.navigation) - 1:
            print('index is already at the end')
            return

        self.nav_index += 1
        project, next_node = self.navigation[self.nav_index]
        self.set_current_project(project)
        next_node = self.current_project.nav_advance()
        return next_node

    def delete_file(self, file_name, project=None, open_files=[]):
        if not project:
            project = self.current_project
        removed_node_ids = project.delete_file(os.path.basename(file_name), open_files=open_files)
        if project.is_async:
            removed_node_ids = removed_node_ids.future()
        for node_id in removed_node_ids:
            navigation_entry = (project.title, node_id)
            while navigation_entry in self.navigation:
                index = self.navigation.index(navigation_entry)
                del self.navigation[index]
                if self.nav_index > index: # >= ?
                    self.nav_index -= 1

    def nav_new(self, node_id, project=None):
        if not project:
            project = self.current_project

        # don't re-remember consecutive duplicate links
        if -1 < self.nav_index < len(self.navigation) and node_id == self.navigation[self.nav_index]:
            return

        # add the newly opened file as the new "HEAD"
        self.nav_index += 1
        del self.navigation[self.nav_index:]
        self.navigation.append((project.title, node_id))
        self.current_project.nav_new(node_id)

    def nav_reverse(self):
        
        if not self.navigation:
            print('no nav history')
            return None
            
        if self.nav_index == 0:
            print('index is already at the beginning.')
            return None
        
        self.nav_index -= 1

        project, last_node = self.navigation[self.nav_index]
        self.set_current_project(project)
        self.current_project.nav_reverse()   
        return last_node

