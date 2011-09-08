import sys
from datetime import datetime
import time
import threading
import math

__all__ = ('PercentageProgress', 'BarProgress', 'TimeProgress')

if sys.version_info >= (3,):
    unicode = str
    unichr = chr
else:
    unicode = unicode
    unichr = unichr

################################################################################
# Terminal introspection
################################################################################
CURSES_AVAILABLE = True
try:
    import curses
except ImportError:
    CURSES_AVAILABLE = False
    
def printer(text):
    def wrapped(times=1):
        written = str(text) * times
        sys.stdout.write(written)
        return written
    return wrapped

if CURSES_AVAILABLE:
    curses.setupterm(None, sys.__stdout__.fileno())
    code_printer = lambda *args: printer(''.join([unicode(curses.tigetstr(code)) for code in args]))
    get_columns = lambda: curses.tigetnum('cols') or 80
    get_lines = lambda: curses.tigetnum('lines') or 25
else:
    get_columns = lambda: 80
    get_lines = lambda: 25
    code_printer = lambda *args: printer('')

ON_WINDOWS = sys.platform == 'win32'
if ON_WINDOWS:
    # http://code.activestate.com/recipes/440694-determine-size-of-console-window-on-windows/
    from ctypes import windll, create_string_buffer
    
    # stdin handle is -10
    # stdout handle is -11
    # stderr handle is -12
    
    def _get_dimensions():
        h = windll.kernel32.GetStdHandle(-12)
        csbi = create_string_buffer(22)
        res = windll.kernel32.GetConsoleScreenBufferInfo(h, csbi)
        
        if res:
            import struct
            (bufx, bufy, curx, cury, wattr,
             left, top, right, bottom, maxx, maxy) = struct.unpack("hhhhHhhhhhh", csbi.raw)
            sizex = right - left + 1
            sizey = bottom - top + 1
            
            return sizex, sizey
        
    get_columns = lambda: _get_dimensions()[0] or 80
    get_lines = lambda: _get_dimensions()[1] or 25
        
# http://pubs.opengroup.org/onlinepubs/7908799/xcurses/terminfo.html
clear_line = code_printer('cr', 'el')
home = code_printer('cr')
new_line = printer('\n')
show_cursor = code_printer('cnorm')
hide_cursor = code_printer('civis')
go_right = code_printer('cuf1')
go_left = code_printer('cub1')
go_up = code_printer('cuu1')
go_down = code_printer('cud1')

################################################################################
# Classes
################################################################################
class ProgressBase(object):
    def __init__(self):
        self.__last_text = ''
    
    def write(self, text):
        text = unicode(text)
        if text == self.__last_text:
            return
        
        last_length = len(self.__last_text)
        current_length = len(text)
        if last_length > current_length:
            text += ' ' * (last_length - current_length)
        backup = chr(8) * last_length
        sys.stdout.write(unicode('{}{}').format(backup, text))
        sys.stdout.flush()
        
        self.__last_text = text
    
    def start(self):
        self.cursor = False
    
    def update(self, *args, **kwargs):
        pass
    
    def finish(self):
        self.cursor = True
        new_line()
    
    def __enter__(self):
        self.start()
        return self
        
    def __exit__(self, *args):
        self.finish()
    
    __cursor = True
    @property
    def cursor(self):
        return self.__cursor
    @cursor.setter
    def cursor(self, value):
        if value:
            show_cursor()
            self.__cursor = True
        else:
            hide_cursor()
            self.__cursor = False
    
class PercentageProgress(ProgressBase):
    template = '{:0.0%}'
    
    def __init__(self, total=1, template=None):
        super(PercentageProgress, self).__init__()
        self.total = max(total, 1)
        if template is not None:
            self.template = template
        self.current = 0
        self.last_message = ''
    
    def update(self, amount=1, context=''):
        self.current += amount
        if self.current > self.total:
            self.current = self.total
        if self.current < 0:
            self.current = 0
            
        progress = float(self.current) / float(self.total)
        args = [progress]
        kwargs = {'progress': progress, 'context': context}
        
        self.write(self.template.format(*args, **kwargs))
        
class BarProgress(ProgressBase):
    def __init__(self, total=1):
        super(BarProgress, self).__init__()
        
        self.parts = [unichr(code) for code in ((0x258c, 0x2588) if ON_WINDOWS else reversed(range(0x2588, 0x258f + 1)))]
        
        self.total = max(total, 1)
        self.current = 0
    
    def update(self, amount=1):
        self.current += amount
        if self.current > self.total:
            self.current = self.total
        if self.current < 0:
            self.current = 0
        
        percentage = float(self.current) / float(self.total)
        columns = get_columns()
        
        parts_length = len(self.parts)
        pieces = columns * parts_length
        current_pieces = int(math.floor(pieces * percentage))
        full_pieces = int(math.floor(current_pieces / parts_length))
        piece_parts = current_pieces % parts_length
        
        self.write(self.parts[-1] * full_pieces + (self.parts[piece_parts - 1] if piece_parts > 0 else ''))

class TimeProgress(ProgressBase):
    template = '{0:.{1}f}'
    
    def __init__(self, precision=0, period=None, template=None):
        super(TimeProgress, self).__init__()
        if template is not None:
            self.template = template
        self.precision = min(max(precision, 0), 6)
        if period is None:
            self.period = 1 / (10 ** precision)
        else:
            self.period = period
        self.running = False
            
    def start(self):
        self._start = datetime.now()
        self.running = True
        def go():
            try:
                while self.running:
                    time.sleep(self.period)
                    self.update()
            except:
                self.running = False
                raise
        thread = threading.Thread(target=go)
        thread.start()
        super(TimeProgress, self).start()
    
    def update(self):
        if self.running:
            seconds = (datetime.now() - self._start).total_seconds()
            self.write(self.template.format(seconds, self.precision))
        
    def finish(self):
        self.running = False
        super(TimeProgress, self).finish()
