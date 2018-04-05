import json
import csv
import sys
import argparse
import logging
import os
import shutil
import subprocess
import pprint
from urllib.parse import urljoin, urlparse
import time

import PyChromeDevTools
import toml
import paramiko
import numpy as np

logger = logging.getLogger(__name__)

logging.basicConfig(level=logging.INFO)


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
    parser.add_argument('--start-chrome', action='store_true')
    parser.add_argument('--single', action='store_true')
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
    config['single'] = args.single
    config['start-chrome'] = args.start_chrome
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
        default = {
            'protocol': protocol,
            'varying': 'none'
        }
        for dim in range(len(dimensions)):
            name = dimensions[dim][0]
            default[name] = config[name]
        treatments.append(default)
        for vdim in range(len(dimensions)):
            varying = dimensions[vdim][0]
            values = config[dimensions[vdim][1]]
            try:
                values.remove(config[varying])
            except ValueError:
                pass
            # for each value in the varying dimension
            for value in values:
                treatment = {
                    'protocol': protocol,
                    varying: value,
                    'varying': varying
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


def start_chrome(config, protocol):
    try:
        shutil.rmtree(config['{}-user-data-dir'.format(protocol)])
    except FileNotFoundError:
        pass
    os.makedirs(config['{}-user-data-dir'.format(protocol)])
    command = [
        config['chrome'],
        '--remote-debugging-port=' + str(config['{}-debugging-port'.format(protocol)]),
        '--user-data-dir=' + config['{}-user-data-dir'.format(protocol)]
    ]
    if protocol == 'quic':
        command.extend([
            '--enable-quic',
            '--origin-to-force-quic-on=' + urlparse(config['host']).netloc + ':443'
        ])
    logger.info('Launching chrome for {}:\n%s'.format(protocol), pprint.pformat(command))
    command += config['chrome-options']
    return subprocess.Popen(command)


def start_chrome_processes(config):
    os.system('killall "Google Chrome"')
    chromes = {}
    for protocol in ['quic', 'tcp']:
        chromes[protocol] = {'process': start_chrome(config, protocol)}
    time.sleep(config['chrome-startup-delay'])


def connect_chrome_interfaces(config):
    chromes = {}
    for protocol in ['quic', 'tcp']:
        port = config['{}-debugging-port'.format(protocol)]
        chromes[protocol] = PyChromeDevTools.ChromeInterface(
            timeout=config['page-load-timeout'],
            port=port
        )
        chromes[protocol].Network.enable()
        chromes[protocol].Page.enable()
    return chromes


def ssh_connection(host):
    client = paramiko.SSHClient()
    client._policy = paramiko.WarningPolicy()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    ssh_config = paramiko.SSHConfig()
    user_config_file = os.path.expanduser("~/.ssh/config")
    if not os.path.exists(user_config_file):
        logger.error('Could not find ssh config {}'.format(user_config_file))
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
    # url += '?random={}'.format(random.random())
    funcs = [
        'chrome.benchmarking.clearCache()',
        'chrome.benchmarking.clearHostResolverCache()',
        'chrome.benchmarking.clearPredictorCache()',
        'chrome.benchmarking.closeConnections()'
    ]
    for func in funcs:
        resp = chrome.Runtime.evaluate(expression=func)
        if resp['result']['result']['type'] != 'undefined':
            logger.error('Unexpected response calling %s: %s', func, resp)
            sys.exit(1)
    chrome.Page.navigate(url=url)
    evt, payload = chrome.wait_event('Page.loadEventFired')
    responsesReceived = []
    for p in payload:
        if p['method'] == 'Network.responseReceived':
            responsesReceived.append(p['params']['response'])
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
    # of object-count--object-size--page.html
    url = urljoin(
        config['host'],
        'page-{object-count}-{object-size}k.html'.format(**treatment)
    )
    logger.info('Requesting page {}'.format(url))
    results = []
    for i in range(config['iterations']):
        results.append(execute_request(chrome, url))
    return results


def save_treatments(treatments):
    try:
        shutil.rmtree('data')
    except FileNotFoundError:
        pass
    os.makedirs('data')
    with open('data/data.json', 'w') as ofp:
        json.dump(treatments, ofp)
    with open('data/data.csv', 'w') as ofp:
        fieldnames = list(treatments[0].keys()) + ['page-load-time']
        fieldnames.remove('results')
        writer = csv.DictWriter(ofp, fieldnames=fieldnames)
        writer.writeheader()
        rows = []
        for treatment in treatments:
            for result in treatment['results']:
                row = treatment.copy()
                row.pop('results')
                row['page-load-time'] = result
                rows.append(row)
        writer.writerows(rows)
    with open('data/summary.csv', 'w') as ofp:
        fieldnames = list(treatments[0].keys()) + ['page-load-time-mean', 'page-load-time-stdev']
        fieldnames.remove('results')
        writer = csv.DictWriter(ofp, fieldnames=fieldnames)
        writer.writeheader()
        rows = []
        for treatment in treatments:
            row = treatment.copy()
            row.pop('results')
            row['page-load-time-mean'] = np.mean(treatment['results'])
            row['page-load-time-stdev'] = np.std(treatment['results'])
            rows.append(row)
        writer.writerows(rows)


def main():
    absolute_start = time.time()
    config = parse_args()
    treatments = generate_treatments(config)
    if config['start-chrome']:
        start_chrome_processes(config)
    chromes = connect_chrome_interfaces(config)
    router = ssh_connection('csc466-router')
    elapsed = time.time() - absolute_start
    logger.info('Took {:.1f} seconds to prepare for treatments'.format(elapsed))
    start = time.time()
    for i, treatment in enumerate(treatments):
        treatment['results'] = run_treatment(config, router, chromes[treatment['protocol']], treatment)
        if config['single']:
            logger.info('Single shot, exiting early')
            sys.exit(0)
        elapsed = time.time() - start
        done = i + 1
        predicted = (len(treatments) / done - 1) * elapsed
        logger.info('Completed {} of {} treatments in {:.1f} seconds, estimate {:.1f} minutes left'.format(done, len(treatments), elapsed, predicted / 60))
    save_treatments(treatments)


if __name__ == '__main__':
    sys.exit(main())
