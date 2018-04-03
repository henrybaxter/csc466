import shutil
import pprint
from os.path import join
import os
import sys
import re
from urllib.parse import urljoin

import toml
from jinja2 import Template

def remake_dir(d):
    try:
        shutil.rmtree(d)
    except FileNotFoundError:
        pass
    os.makedirs(d)

def main():
    config = toml.load(open('config.toml'))
    remake_dir('tcp-root/images')
    remake_dir('quic-root/images')
    page = Template(open('templates/page.html').read())
    header = Template(open('templates/headers').read())
    index = Template(open('templates/index.html').read())
    #available_sizes = [int(re.search('(\d+)k\.jpeg', img).group(1)) for img in os.listdir('images/')]
    #missing = set(config['object-sizes']) - set(available_sizes)
    #if missing:
    #    print('Missing the following image sizes:', ', '.join(str(m) for m in missing))
    #    sys.exit(1)
    for protocol in ['tcp', 'quic']:
        urls = []
        root = '{}-root'.format(protocol)
        for img in os.listdir('images/'):
            in_path = join('images', img)
            out_path = join(root, 'images', img)
            url = urljoin(config['host'], 'images/' + img)
            contents = open(in_path, 'rb').read()
            with open(out_path, 'wb') as ofp:
                if protocol == 'quic':
                    ofp.write(header.render({'content_type': 'image/jpeg', 'url': url}).encode('utf-8'))
                ofp.write(contents)
        for cnt in config['object-counts']:
            for size in config['object-sizes']:
                name = '{} objects of size {}kb'.format(cnt, size)
                path = 'page-{}-{}k.html'.format(cnt, size)
                urls.append((name, path))
                img_in = join(root, 'images', '{}k.jpeg'.format(size))
                images = []
                for i in range(cnt):
                    img_out = join(root, 'images', '{}k-{}.jpeg'.format(size, i))
                    images.append('images/{}k-{}.jpeg'.format(size, i))
                    shutil.copy(img_in, img_out)
                context = {
                    'images': [{
                        'url': img
                    } for img in images],
                    'title': 'Test {} images of size {}kb'.format(cnt, size),
                    'protocol': protocol
                }
                out_path = join(root, path)
                url = urljoin(config['host'], path)
                with open(out_path, 'w') as ofp:
                    if protocol == 'quic':
                        ofp.write(header.render({'content_type': 'text/html', 'url': url}))
                    ofp.write(page.render(context))
        url = urljoin(config['host'], 'index.html')
        with open(join(root, 'index.html'), 'w') as ofp:
            if protocol == 'quic':
                ofp.write(header.render({'content_type': 'text/html', 'url': url}))
            ofp.write(index.render({'urls': urls, 'protocol': protocol}))


if __name__ == '__main__':
    main()
