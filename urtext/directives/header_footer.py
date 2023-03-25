import os
if os.path.exists(os.path.join(os.path.dirname(os.path.realpath(__file__)), '../sublime.txt')):
    from Urtext.urtext.directive import UrtextDirective
else:
    from urtext.directive import UrtextDirective

class UrtextHeader(UrtextDirective):

    name = ["HEADER"]
    phase = 410
    
    def dynamic_output(self, contents):
        if not self.argument_string:
            self.argument_string = ''
        header = bytes(self.argument_string, "utf-8").decode("unicode_escape")
        if header and header[-1] != '\n':
            header += '\n'
        return ''.join([header, contents])

class UrtextFooter(UrtextDirective):

    name = ["FOOTER"]
    phase = 420

    def dynamic_output(self, contents):
        footer = bytes(self.argument_string, "utf-8").decode("unicode_escape") + '\n'
        return ''.join([contents, footer])
