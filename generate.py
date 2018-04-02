import toml
import random
from os.path import join
import os
import errno

from jinja2 import Template


def main():
    config = toml.load(open('config.toml'))
    try:
        os.makedirs(config['webroot'])
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise
    template = Template(open('template.html').read())
    for cnt in config['object-counts']:
        for size in config['object-sizes']:
            path = 'page-{}-{}kb.html'.format(size, cnt)
            context = {
                'images': [{
                    'url': 'images/{}kb.jpg?rnd={}'.format(size, random.random())
                } for i in range(cnt)],
                'title': 'Test {} images of size {}kb'.format(cnt, size)
            }
            open(join(config['webroot'], path), 'w').write(template.render(context))


if __name__ == '__main__':
    main()
