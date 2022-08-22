from time import time


def b() -> None:
    r = 100_000
    for x in range(r):
        if x % (r / 10):
            print("yote!")


def c() -> None:
    d()


def d() -> None:
    r = 100_000
    for x in range(r):
        if x % (r / 10):
            print("yeet!")


def a() -> None:
    print(time())
    b()
    print(time())
    c()
