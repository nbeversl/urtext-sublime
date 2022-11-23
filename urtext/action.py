class UrtextAction:

    name=["URTEXT_ACTION_BASE"]

    def __init__(self, project):
    	self.project = project

    def execute(self, 
        param_string, 
        filename=None,
        action_span=None,
        file_pos=0,
        col_pos=0, 
        node_id=None):
    
        return None