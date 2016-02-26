class CommandBlock:
    def __init__(self):
        self.__commands = []
    def format(self, *args, **kwargs):
        res = CommandBlock()
        for c in self.__commands:
            res += c.format(*args, **kwargs)
        return res
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
    c += 'uno'
    d = c + 'quattro'
    e = d + ['bau', 'miao']
    f = e + c
    g = 'newone' + f
    print(c)
    print()
    print(d)
    print()
    print(e)
    print()
    print(f)
    print()
    print(g)
