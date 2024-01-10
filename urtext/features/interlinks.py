import os
if os.path.exists(os.path.join(os.path.dirname(os.path.realpath(__file__)), '../sublime.txt')):
    from Urtext.anytree import Node
    from Urtext.anytree import RenderTree
else:
    from anytree import Node
    from anytree import RenderTree

class Interlinks:

    name = ["INTERLINKS"]
    phase = 350
    
    def dynamic_output(self, nodes):

        self.visited_nodes = []
        self.backward_visited_nodes = []
        self.exclude = []

        if 'from' in self.params_dict and self.params_dict['from'][0] in self.project.nodes:
            root_node_id = self.params_dict['from'][0]
            root_node = self.project.nodes[root_node_id]
            root_meta = self.project.nodes[root_node_id].metadata
            self.build_node_tree(root_node.id)
            self.build_backward_node_tree(root_node.id)
            return self.render_tree()

        return ''


    def build_node_tree(self, oldest_node, parent=None):
        self.tree = Node(oldest_node)
        self.add_children(self.tree)

    def add_children(self, parent):
        links = self.project.nodes[parent.name].links

        for link in links:
            # if link in selfexclude:
            #     continue
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

    def add_backward_children(self, parent):
        links = [i for i in self.project.get_links_to(parent.name)] #if i not in self.exclude]
        for link in links:           
            # if link in self.exclude:
            #     continue
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

urtext_directives=[Interlinks]