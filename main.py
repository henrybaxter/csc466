import sys
import argparse
import logging
import os
import pprint
from urllib.parse import urljoin

import PyChromeDevTools
import toml
import paramiko

logger = logging.getLogger(__name__)

logging.basicConfig(level=logging.INFO)

DIR = os.path.dirname(__file__)


def parse_args():
    logger.debug('Parsing command line arguments')
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', default='config.toml')
    parser.add_argument('--rate-limit', type=float)
    parser.add_argument('--latency', type=int)
    parser.add_argument('--packet-loss', type=float)
    parser.add_argument('--object-count', type=int)
    parser.add_argument('--object-size', type=int)
    parser.add_argument('--timeout', type=int)
    args = parser.parse_args()
    try:
        logger.debug('Attempting to load TOML values from %s', args.config)
        config = toml.load(open(args.config))
    except FileNotFoundError:
        print('Could not find {}'.format(args.config))
        sys.exit(1)
    except toml.TomlDecodeError as err:
        print('Could not read TOML file: {}'.format(err))
        sys.exit(1)
    if args.rate_limit is not None:
        config['rate-limit'] = args.rate_limit
        config['rate-limits'] = [args.rate_limit]
    if args.packet_loss is not None:
        config['packet-loss'] = args.packet_loss
        config['packet-losses'] = [args.packet_loss]
    if args.latency is not None:
        config['latency'] = args.latency
        config['latencies'] = [args.latency]
    if args.object_count is not None:
        config['object-count'] = args.object_count
        config['object-counts'] = [args.object_count]
    if args.object_size is not None:
        config['object-size'] = args.object_size
        config['object-sizes'] = [args.object_sizes]
    if args.timeout is not None:
        config['page-load-timeout'] = args.timeout
    missing = set(config['object-sizes']) - set(config['available-image-sizes'])
    if missing:
        print('Missing the following image sizes:', ', '.join(str(m) for m in missing))
        sys.exit(1)
    sys.exit()
    logger.debug('Command line arguments parsed')
    return config


def generate_treatments(config):
    logger.debug('Generating treatments')
    dimensions = [
        ('rate-limit', 'rate-limits'),
        ('latency', 'latencies'),
        ('packet-loss', 'packet-losses'),
        ('object-count', 'object-counts'),
        ('object-size', 'object-sizes'),
    ]
    treatments = []
    for protocol in ['quic', 'tcp']:
        # for each varying dimension
        for vdim in range(len(dimensions)):
            varying = dimensions[vdim][0]
            # for each value in the varying dimension
            for value in config[dimensions[vdim][1]]:
                treatment = {
                    'protocol': protocol,
                    varying: value
                }
                # collect all the constants
                for cdim in range(len(dimensions)):
                    if cdim == vdim:
                        continue
                    constant = dimensions[cdim][0]
                    treatment[constant] = config[constant]
                treatments.append(treatment)
    logger.info('Generated %d treatments', len(treatments))
    return treatments


def ssh_connection(host):
    client = paramiko.SSHClient()
    client._policy = paramiko.WarningPolicy()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    ssh_config = paramiko.SSHConfig()
    user_config_file = os.path.expanduser("~/.ssh/config")
    if not os.path.exists(user_config_file):
        print('Could not find ssh config {}'.format(user_config_file))
        sys.exit(1)
    logger.info('Found SSH config file')
    with open(user_config_file) as f:
        ssh_config.parse(f)

    ssh_cfg = ssh_config.lookup(host)
    key = paramiko.RSAKey.from_private_key_file(ssh_cfg['identityfile'][0])
    cfg = {
        'hostname': ssh_cfg['hostname'],
        'username': ssh_cfg['user'],
        'port': ssh_cfg.get('port', 22),
        'pkey': key
    }
    client.connect(**cfg)
    logger.info('Connected to %s', host)
    return client


def execute_request(chrome, url):
    logger.info('Executing request for {}'.format(url))
    funcs = [
        'chrome.benchmarking.clearCache()',
        'chrome.benchmarking.clearHostResolverCache()',
        'chrome.benchmarking.clearPredictorCache()',
        'chrome.benchmarking.closeConnections()'
    ]
    for func in funcs:
        chrome.Runtime.evaluate(expression=func)
    chrome.Page.navigate(url=url)
    evt, payload = chrome.wait_event('Page.loadEventFired')
    #pprint.pprint(evt)
    #pprint.pprint(payload)
    requestWillBeSent = payload[1]
    assert requestWillBeSent['method'] == 'Network.requestWillBeSent', requestWillBeSent['method']
    loadEventFired = payload[-1]
    loadEventFired['method'] == 'Page.loadEventFired', loadEventFired['method']
    end = float(loadEventFired['params']['timestamp'])
    start = float(requestWillBeSent['params']['timestamp'])
    elapsed = (end - start) * 1000
    return elapsed


def run_treatment(config, router, chrome, treatment):
    logger.info('Running treatment %s', pprint.pformat(treatment))
    command = 'sudo ./csc466/set_router {rate-limit} {latency} {packet-loss}'.format(**treatment)
    logger.info('Running on router: %s', command)
    stdin, stdout, stderr = router.exec_command(command)
    retcode = stdout.channel.recv_exit_status()
    if retcode:
        logger.error('Retcode was %d, output was\n%s', retcode, stderr.read().decode('utf-8'))
        sys.exit(1)
    # ok now that we have setup the router, what about the server?
    # what about the url? we assume a url structure on the other side
    # of object-counte--object-size--page.html
    url = urljoin(
        config['host'],
        'page-{object-count}-{object-size}k.html'.format(**treatment)
    )
    logger.info('Requesting page {}'.format(url))
    results = []
    for i in range(config['iterations']):
        results.append(execute_request(chrome, url))
    return results


def main():
    config = parse_args()
    treatments = generate_treatments(config)
    router = ssh_connection('csc466-router')
    chrome = PyChromeDevTools.ChromeInterface(timeout=config['page-load-timeout'])
    chrome.Network.enable()
    chrome.Page.enable()
    for treatment in treatments:
        treatment['results'] = run_treatment(config, router, chrome, treatment)
        pprint.pprint(treatment['results'])
    pprint.pprint(treatments)


if __name__ == '__main__':
    sys.exit(main())
