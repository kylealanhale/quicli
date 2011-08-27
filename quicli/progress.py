import sys

class PercentageProgress(object):
    template = '{0:0.0%}'
    
    def __init__(self, total):
        self.total = total
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
        message = self.template.format(*args, **kwargs)
        if message == self.last_message:
            return
        
        last_length = len(self.last_message)
        current_length = len(message)
        if last_length > current_length:
            message += ' ' * (last_length - current_length)
        backup = chr(8) * last_length
        sys.stdout.write('{0}{1}'.format(backup, message))
        
        self.last_message = message
