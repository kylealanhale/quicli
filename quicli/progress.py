import sys
from datetime import datetime
import time
import threading

class ProgressBase(object):
    def __init__(self):
        self.__last_text = ''
    
    def write(self, text):
        text = str(text)
        if text == self.__last_text:
            return
        
        last_length = len(self.__last_text)
        current_length = len(text)
        if last_length > current_length:
            text += ' ' * (last_length - current_length)
        backup = chr(8) * last_length
        sys.stdout.write('{}{}'.format(backup, text))
        
        self.__last_text = text        
        
class PercentageProgress(ProgressBase):
    template = '{:0.0%}'
    
    def __init__(self, total, template=None):
        super(PercentageProgress, self).__init__()
        self.total = total
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
        if self.total == 0:
            progress = 1
        else:
            progress = float(self.current) / float(self.total)
        args = [progress]
        kwargs = {'progress': progress, 'context': context}
        
        self.write(self.template.format(*args, **kwargs))

class TimeProgress(ProgressBase):
    template = '{days} {seconds}.{microseconds}'
    
    def __init__(self, template=None, resolution='seconds', period=1):
        super(TimeProgress, self).__init__()
        if template is not None:
            self.template = template
        self.resolution = resolution
        self.period = period
        self.running = False
            
    def start(self):
        self.start = datetime.now()
        self.running = True
        def go():
            try:
                while self.running:
                    self.update()
                    time.sleep(self.period)
            except:
                self.running = False
                raise
        thread = threading.Thread(target=go)
        thread.start()
    
    def update(self):
        delta = datetime.now() - self.start
        pieces = dict([(piece, getattr(delta, piece)) for piece in ('days', 'seconds', 'microseconds')])
        self.write(self.template.format(**pieces))
        
    def stop(self):
        self.running = False
