import pprint
import random
from os.path import join
import os
import errno

import toml
from jinja2 import Template


def main():
    config = toml.load(open('config.toml'))
    try:
        os.makedirs(config['webroot'])
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise
    template = Template(open('templates/page.html').read())
    urls = []
    pprint.pprint(config)
    missing = set(config['object-sizes']) - set(config['available-image-sizes'])
    if missing:
        print('Missing the following image sizes:', ', '.join(str(m) for m in missing))
        sys.exit(1)
    for cnt in config['object-counts']:
        for size in config['object-sizes']:
            name = '{} objects of size {}kb'.format(cnt, size)
            path = 'page-{}-{}k.html'.format(cnt, size)
            urls.append((name, path))
            context = {
                'images': [{
                    'url': 'images/{}k.jpg?rnd={}'.format(size, random.random())
                } for i in range(cnt)],
                'title': 'Test {} images of size {}kb'.format(cnt, size)
            }
            open(join(config['webroot'], path), 'w').write(template.render(context))
    open(join(config['webroot'], 'index.html'), 'w').write(Template(open('templates/index.html').read()).render({'urls': urls}))


if __name__ == '__main__':
    main()
