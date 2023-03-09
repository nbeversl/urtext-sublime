class UrtextPointer:

    def __init__(self, 
        node_id,
        position):

        self.id = node_id
        self.position = position

    def start_position(self):
        return self.position