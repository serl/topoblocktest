import os
import re
import subprocess
from tempfile import NamedTemporaryFile


class CommandBlock:
    __timeout_re = re.compile(r"\s+timeout\s+.*?(\d+)")

    @classmethod
    def root_check(cls):
        return cls() + 'if [ $EUID -ne 0 ]; then echo "root account required!"; exit 1; fi'

    @classmethod
    def get_bash(cls, label='Bash'):
        cmds = cls()
        cmds += 'echo ; echo "DROP THE BASH!!"'
        prompt = r'\u@\h:\w%'
        cmds += 'PS1="[{}] {} " bash --norc'.format(label, prompt)
        return cmds

    def __init__(self):
        self.__commands = []

    def format(*args, **kwargs):
        self = args[0]  # must do this ugly trick in order to let you define self as a key in kwargs
        res = CommandBlock()
        for c in self.__commands:
            res += c.format(*args, **kwargs)
        return res

    def execution_time(self):
        time = 0.0
        for command in self.__commands:
            if command.strip().startswith('sleep'):
                time += float(command.split()[1])
            timeout_match = self.__timeout_re.search(command)
            if timeout_match is not None:
                time += float(timeout_match.group(1))
        return time

    def run(self, add_bash=False):
        if add_bash:
            self += self.__class__.get_bash(str(add_bash) if type(add_bash) != type(True) else 'Debug')
        with NamedTemporaryFile(mode='wt', delete=False) as script_file:
            script_file.write(str(self))
        proc = subprocess.Popen(['/bin/bash', script_file.name], universal_newlines=True)
        proc.wait()
        os.unlink(script_file.name)
        return proc.returncode

    def __iter__(self):
        return self.__commands.__iter__()

    def __next__(self):
        return self.__commands.__next__()

    def __add__(self, arg):
        res = CommandBlock()
        res += self
        res += arg
        return res

    def __iadd__(self, arg):
        if arg is None:
            return self
        if isinstance(arg, str):
            self.__commands.extend(arg.split('\n'))
            return self
        try:
            self.__commands.extend(arg)  # CommandBlock IS iterable, so this will also merge two CommandBlocks
            return self
        except TypeError:
            pass
        return NotImplemented

    def __radd__(self, arg):
        res = CommandBlock()
        res += arg
        res += self
        return res

    def __str__(self):
        return "\n".join(self.__commands)

if __name__ == '__main__':
    c = CommandBlock()
    c += 'echo one'
    d = c + 'echo two'
    e = d + ['echo three', 'echo four']
    f = e + c
    g = 'echo zero' + f
    print(c)
    print()
    print(d)
    print()
    print(e)
    print()
    print(f)
    print()
    print(g)
    print()
    print('executing the last block')
    print('exit value: {}'.format(g.run()))
