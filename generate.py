import sys
import shutil
import logging
import argparse
from os.path import join
import os
from urllib.parse import urljoin

import toml
from jinja2 import Template

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)


def root(protocol):
    return '{}-root'.format(protocol)


def remake_dir(d):
    try:
        shutil.rmtree(d)
    except FileNotFoundError:
        pass
    os.makedirs(d)


def get_config():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', default='config.toml')
    args = parser.parse_args()
    try:
        logger.debug('Attempting to load TOML values from %s', args.config)
        config = toml.load(open(args.config))
    except FileNotFoundError:
        logger.error('Could not find {}'.format(args.config))
        sys.exit(1)
    except toml.TomlDecodeError as err:
        logger.error('Could not read TOML file: {}'.format(err))
        sys.exit(1)
    return config


def make_page(host, protocol, page, header, cnt, size):
    name = '{} objects of size {}kb'.format(cnt, size)
    page_url = 'page-{}-{}k.html'.format(cnt, size)
    img_urls = []
    if size:
        img_in = join('images', '{}k.jpeg'.format(size))
        img_contents = open(img_in, 'rb').read()
        for i in range(cnt):
            img_out = join(root(protocol), 'images', '{}k-{}.jpeg'.format(size, i))
            img_rel = 'images/{}k-{}.jpeg'.format(size, i)
            img_urls.append(img_rel)
            with open(img_out, 'wb') as ofp:
                if protocol == 'quic':
                    ofp.write(header.render({'content_type': 'image/jpeg', 'url': urljoin(host, img_rel)}).encode('utf-8'))
                ofp.write(img_contents)
    context = {
        'images': [{
            'url': img
        } for img in img_urls],
        'title': 'Test {} images of size {}kb'.format(cnt, size),
        'protocol': protocol
    }
    page_path = join(root(protocol), page_url)
    page_url = urljoin(host, page_url)
    with open(page_path, 'w') as ofp:
        if protocol == 'quic':
            ofp.write(header.render({'content_type': 'text/html', 'url': page_url}))
        ofp.write(page.render(context))
    return (name, page_url)


def make_site(host, protocol, counts, sizes):
    urls = []
    remake_dir(root(protocol))
    remake_dir(join(root(protocol), 'images'))
    header = Template(open('templates/headers').read())
    page = Template(open('templates/page.html').read())
    index = Template(open('templates/index.html').read())
    for cnt in counts:
        if not cnt:
            urls.append(make_page(host, protocol, page, header, 0, 0))
            continue
        for size in sizes:
            urls.append(make_page(host, protocol, page, header, cnt, size))
    url = urljoin(host, 'index.html')
    with open(join(root(protocol), 'index.html'), 'w') as ofp:
        if protocol == 'quic':
            ofp.write(header.render({'content_type': 'text/html', 'url': url}))
        ofp.write(index.render({'urls': urls, 'protocol': protocol}))


def main():
    config = get_config()
    counts = set(config['variations']['object-count']) | set([config['treatment']['object-count']])
    sizes = set(config['variations']['object-size']) | set([config['treatment']['object-size']])
    for protocol in ['tcp', 'quic']:
        make_site(config['host'], protocol, counts, sizes)



if __name__ == '__main__':
    main()
