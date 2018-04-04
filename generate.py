import shutil
from os.path import join
import os
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
    for protocol in ['tcp', 'quic']:
        urls = []
        root = '{}-root'.format(protocol)
        for cnt in config['object-counts']:
            for size in config['object-sizes']:
                name = '{} objects of size {}kb'.format(cnt, size)
                page_url = 'page-{}-{}k.html'.format(cnt, size)
                urls.append((name, page_url))
                img_in = join('images', '{}k.jpeg'.format(size))
                img_contents = open(img_in, 'rb').read()
                img_urls = []
                for i in range(cnt):
                    img_out = join(root, 'images', '{}k-{}.jpeg'.format(size, i))
                    img_url = 'images/{}k-{}.jpeg'.format(size, i)
                    img_urls.append(img_url)
                    with open(img_out, 'wb') as ofp:
                        if protocol == 'quic':
                            ofp.write(header.render({'content_type': 'image/jpeg', 'url': img_url}).encode('utf-8'))
                        ofp.write(img_contents)
                context = {
                    'images': [{
                        'url': img
                    } for img in img_urls],
                    'title': 'Test {} images of size {}kb'.format(cnt, size),
                    'protocol': protocol
                }
                page_path = join(root, page_url)
                page_url = urljoin(config['host'], page_url)
                with open(page_path, 'w') as ofp:
                    if protocol == 'quic':
                        ofp.write(header.render({'content_type': 'text/html', 'url': page_url}))
                    ofp.write(page.render(context))
        url = urljoin(config['host'], 'index.html')
        with open(join(root, 'index.html'), 'w') as ofp:
            if protocol == 'quic':
                ofp.write(header.render({'content_type': 'text/html', 'url': url}))
            ofp.write(index.render({'urls': urls, 'protocol': protocol}))


if __name__ == '__main__':
    main()
