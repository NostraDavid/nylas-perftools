from time import sleep


def b() -> None:
    sleep(0.1)


def c():
    d()
    d()


def d():
    sleep(0.25)


def a() -> None:
    b()
    b()
    b()
    c()
    b()
    c()
