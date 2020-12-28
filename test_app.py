#!/usr/bin/env python

import click

from limud.words import Word


@click.command()
@click.option("--text", default="", help="Word (as text)")
def main(text):
    if not text:
        text = b'\xd7\xa8\xd7\x9e\xd6\xb7\xd7\x90\xd6\xb8'.decode("utf-8")
    Word(text=text, description="").render()


if __name__ == '__main__':
    click.secho("Testing rendering of Hebrew text", fg="blue")
    main()