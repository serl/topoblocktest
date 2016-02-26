import subprocess

class CommandBlock:
    def __init__(self):
        self.__commands = []
    def format(self, *args, **kwargs):
        res = CommandBlock()
        for c in self.__commands:
            res += c.format(*args, **kwargs)
        return res
    def run(self):
        proc = subprocess.Popen('/bin/bash', stdin=subprocess.PIPE, universal_newlines=True)
        proc.communicate(str(self))
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
            self.__commands.append(arg)
            return self
        try:
            self.__commands.extend(arg) #CommandBlock IS iterable, so this will also merge two CommandBlocks
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
