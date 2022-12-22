
class NoPathProvided(Exception):
    def __init__(self):
        print('At least one valid project path is required')

class NoValidSettings(Exception):
    def __init__(self):
        print('No valid Urtext settings found')