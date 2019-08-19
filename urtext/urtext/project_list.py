from .project import UrtextProject, node_id_regex
import re
import os


class ProjectList:
    def __init__(self, base_path, other_paths):
        self.projects = []
        for other_path in other_paths:
            self.projects.append(
                UrtextProject(os.path.join(base_path, other_path)))
        print(self.projects)

    def get_project(self, path):
        for project in self.projects:
            if project.path == path:
                return project
        return None

    def get_node_link(self, string):

        node_string = re.compile(node_id_regex + '(\:\d{0,20})?')
        if re.search(node_string, string):
            node_and_position = re.search(node_string, string).group(0)
            node_id = node_and_position.split(':')[0].strip()
            for project in self.projects:
                for node in project.nodes:
                    if node == node_id:
                        return {
                            'project_path': project.path,
                            'filename': project.nodes[node].filename
                        }
        return None
