import sublime
from .sublime_urtext import UrtextTextCommand, refresh_project_text_command

folding_margins = {
    'dynamic-definition' : [2,2],
    'entity.name.struct.datestamp.urtext' : [1,1],
    'metadata_entry.urtext' : [0,0],
    'inline_node_5' : [1,1],
    'inline_node_4' : [1,1],
    'inline_node_3' : [1,1],
    'inline_node_2' : [1,1],
    'inline_node_1' : [1,1],
    'compact_node.urtext' : [1,0], }

scopes_to_fold = [
    'dynamic-definition',
    'entity.name.struct.datestamp.urtext',
    'metadata_entry.urtext',
    'compact_node.urtext',  
    'inline_node_5',
    'inline_node_4',
    'inline_node_3',
    'inline_node_2',
    'inline_node_1',]

class ToggleFoldSingleCommand(UrtextTextCommand):

    @refresh_project_text_command()
    def run(self):
        region = self.view.extract_scope(self.view.sel()[0].a)
        scope_name = self.view.scope_name(self.view.sel()[0].a)
        scope = get_scope_for_folding(scope_name)
        if scope and region:
            region = expand_scope_for_folding(scope_name, region, self.view)
            if region:
                if self.view.is_folded(region):
                    self.view.unfold(region)
                else:
                    self.view.fold(region)

class ToggleFoldAllCommand(UrtextTextCommand):

    @refresh_project_text_command()
    def run(self):
        region = self.view.extract_scope(self.view.sel()[0].a)
        scope_name = self.view.scope_name(self.view.sel()[0].a)    
        scope = get_scope_for_folding(scope_name)
        if scope:
            region = expand_scope_for_folding(scope_name, region, self.view)
            if region:
                all_regions = self.view.find_by_selector(scope)
                if self.view.is_folded(region):
                    action = self.view.unfold
                else:
                    action = self.view.fold
                for r in all_regions:
                    r = expand_scope_for_folding(scope, r, self.view)
                    action(r)

def get_scope_for_folding(scope_name):
    
    for s in scopes_to_fold:
        if s in scope_name:
            if s == 'compact_node.urtext':
                for t in scopes_to_fold:
                    if t in scope_name and t != 'compact_node.urtext':
                        return t
            return s

def expand_scope_for_folding(scope_name, region, view):
    for s in scopes_to_fold:  
        if s in scope_name:
            if s == 'compact_node.urtext':
                for t in scopes_to_fold:
                    if t != 'compact_node.urtext' and t in scope_name:
                        s = t
            region = view.expand_to_scope(region.a, s)
            if region:
                region = sublime.Region(
                    region.a + folding_margins[s][0],
                    region.b - folding_margins[s][1])
                return region
    return region