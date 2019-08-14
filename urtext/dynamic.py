import re
import os

parent_dir = os.path.dirname(__file__)
node_id_regex = r'\b[0-9,a-z]{3}\b'


class UrtextDynamicDefinition:
    """ Urtext Dynamic Definition """
    def __init__(self, contents):

        self.spaces = 0
        self.target_id = None
        self.include = []
        self.exclude = []
        self.tree = None
        self.sort_tagname = None
        self.metadata = {}
        self.show = 'full_contents'

        entries = re.split(';|\n', contents)

        for entry in entries:
            atoms = [
                atom.strip() for atom in entry.split(':') if atom.strip() != ''
            ]
            """
      skip entries without values
      """
            if len(atoms) < 2:
                continue
            """
      add metadata to target node
      """
            if atoms[0] == 'metadata' and len(atoms) > 2:
                self.metadata[atoms[1]] = ':'.join(
                    atoms[2:]) + '\n'  # use the rest of the
                continue
            """
      use case-insensitive values for the rest
      """
            atoms = [atom.lower() for atom in atoms]
            """
      indentation
      """
            if atoms[0] == 'indent':
                self.spaces = int(atoms[1])
                continue

            if atoms[0] == 'tree':
                self.tree = atoms[1]
                continue

            if atoms[0] == 'sort':
                self.sort_tagname = atoms[1]
                continue
            """
      target node ID
      """
            if atoms[0] == 'id':
                self.target_id = re.search(node_id_regex, atoms[1]).group(0)
                continue
            """
      show contents, title
      """
            if atoms[0] == 'show':
                if atoms[1] == 'title':
                    self.show = 'title'
                if atoms[1] == 'timeline':
                    self.show = 'timeline'
                continue
            """
      exclude/include meta
      """
            if atoms[0] == 'include':
                if atoms[1] == 'all':
                    self.include = 'all'
                    continue

                if atoms[1] == 'metadata' and len(atoms) > 3:
                    self.include.append((atoms[2], atoms[3]))
                    continue

            if atoms[0] == 'exclude':
                if atoms[1] == 'metadata' and len(atoms) > 3:
                    self.exclude.append((atoms[2], atoms[3]))
                    continue
