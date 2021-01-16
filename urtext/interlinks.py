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
import re
from .metadata import NodeMetadata
from anytree import Node
from anytree import RenderTree
node_link_regex =       r'>[0-9,a-z]{3}\b'

node_id_regex = '[0-9,a-z]{3}'

class Interlinks():

    def __init__(self, project, root_node_id, omit=[]):
        self.visited_nodes = []
        self.backward_visited_nodes = []
        self.project = project
        self.exclude = []
        self.exclude.extend(omit)

        root_node = project.nodes[root_node_id]
        root_meta = project.nodes[root_node_id].metadata
        self.build_node_tree(root_node.id)
        self.build_backward_node_tree(root_node.id)

    def build_node_tree(self, oldest_node, parent=None):
        self.tree = Node(oldest_node)
        self.add_children(self.tree)

    def get_links_in_node(self, node_id):
        contents = self.project.nodes[node_id].content_only()
        nodes = re.findall('>' + node_id_regex,
                           contents)  # link RegEx
        links = []
        for node in nodes:
            links.append(node[1:])
        return links

    def add_children(self, parent):
        """ recursively add children """
        links = self.get_links_in_node(parent.name)

        for link in links:
            if link in self.exclude:
                continue
            if link == None:
                child_nodename = Node('(Broken Link)', parent=parent)
                continue
            if link not in self.project.nodes:
                print('link not found ' + link)
                continue
            if link in self.visited_nodes:
                child_nodename = Node(link, parent=parent)
                continue
            else:
                child_nodename = Node(link, parent=parent)
                self.visited_nodes.append(link)
            self.add_children(child_nodename)  # bug fix here

    def build_backward_node_tree(self, oldest_node, parent=None):
        self.backward_tree = Node(oldest_node)
        self.add_backward_children(self.backward_tree)

    def get_links_to_node(self, node_id):
        links_to_node = []
        for node in self.project.nodes:
            if node in self.exclude:
                continue
            contents = self.project.nodes[node].content_only()
            links = re.findall('>' + node_id, contents)  # link RegEx
            if len(links) > 0:
                links_to_node.append(node)
        return links_to_node

    def add_backward_children(self, parent):
        links = self.get_links_to_node(parent.name)
        for link in links:
           
            if link in self.exclude:
                continue
            if link in self.backward_visited_nodes:
                child_nodename = Node(link, parent=parent)
            else:
                self.backward_visited_nodes.append(link)
                child_nodename = Node(link, parent=parent)
                self.add_backward_children(child_nodename)

    def render_tree(self):
        render = ''
        for pre, fill, node in RenderTree(self.backward_tree):          
            render += ("%s%s" % (pre, self.project.nodes[node.name].title +
                             ' >' + node.name)) + '\n'
        render = render.replace('└', '┌')
        render = render.split('\n')
        render = render[1:]  # avoids duplicating the root node
        render_upside_down = ''
        for index in range(len(render)):
            render_upside_down += render[len(render) - 1 - index] + '\n'

        render = ''
        for pre, fill, node in RenderTree(self.tree):
            render += ("%s%s" % (pre, self.project.nodes[node.name].title +
                                 ' >' + node.name)) + '\n'
        render = render_upside_down + render
        render = render.split('\n')
        return '\n'.join(render)
