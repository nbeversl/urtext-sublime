import os
import json
import time
if os.path.exists(os.path.join(os.path.dirname(os.path.realpath(__file__)), '../sublime.txt')):
    from Urtext.urtext.action import UrtextAction
    import Urtext.diff_match_patch as dmp_module
else:
    from urtext.action import UrtextAction
    import diff_match_patch as dmp_module

class HistorySnapshot(UrtextAction): 

    name=['HISTORY_SNAPSHOT']

    def execute(self, 
        param_string, 
        filename=None,
        file_pos=0,
        col_pos=0, 
        node_id=None):
        contents=param_string
        
        dmp = dmp_module.diff_match_patch()
        filename = os.path.basename(filename)
        if filename not in self.project.files:
            return None

        if not os.path.exists(os.path.join(self.project.path, 'history')):
            os.mkdir(os.path.join(self.project.path, 'history'))
        
        history_file = os.path.join(
            self.project.path, 
            'history',
            filename.replace('.txt','.diff'))
        
        file_history = get_history(self.project, filename)
        if not file_history:
            file_history = { int(time.time()) : contents}
            with open( history_file, "w") as f:
            	f.write(json.dumps(file_history))
        else:
            latest_history = apply_patches(file_history)
            if contents != latest_history:
                file_history[int(time.time())] = dmp.patch_toText(dmp.patch_make(latest_history, contents))                
                os.remove(history_file) # might prevent duplicate files on cloud storage ?
                with open( history_file, "w") as f:
                    f.write(json.dumps(file_history))


class GetHistory(UrtextAction):

    name=['HISTORY_GET_HISTORY']

    def execute(self, 
        param_string, 
        filename=None,
        file_pos=0,
        col_pos=0, 
        node_id=None):
        return get_history(self.project, filename)
 
    def most_recent_history(self, history):
        times = sorted(history.keys())
        return times[-1]

class ApplyHistoryPatches(UrtextAction):

    name=['APPLY_HISTORY_PATCHES']

    def execute(self, 
        param_string, 
        filename=None,
        file_pos=0,
        col_pos=0, 
        node_id=None):

        file_history = get_history(self.project, filename)
        distance_back = int(param_string)
        return apply_patches(file_history, distance_back)
 
    def most_recent_history(self, history):
        times = sorted(history.keys())
        return times[-1]

def apply_patches(history, distance_back=0):
    dmp = dmp_module.diff_match_patch()
    timestamps = sorted(history.keys())
    original = history[timestamps[0]]
    for index in range(1,len(timestamps)-distance_back):
        next_patch = history[timestamps[index]]
        original = dmp.patch_apply(dmp.patch_fromText(next_patch), original)[0]
    return original

def get_history(project, filename):
    filename = os.path.basename(filename)
    history_file = os.path.join(project.path, 'history', filename.replace('.txt','.diff'))
    if os.path.exists(history_file):
        with open(history_file, "r") as f:
            file_history = f.read()
        return json.loads(file_history)
    print('NO HISTORY FILE FOUND')

