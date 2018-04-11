import json
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

from convert_data import convert_data

logger = logging.getLogger(__name__)

logging.basicConfig(level=logging.INFO)


def parse_args():
    logger.debug('Parsing command line arguments')
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', default='config.toml')
    parser.add_argument('--timeout', type=int)
    parser.add_argument('--start-chrome', action='store_true')
    parser.add_argument('--single', action='store_true')
    parser.add_argument('--environment')
    parser.add_argument('--iterations', type=int)
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
    if args.iterations is not None:
        config['iterations'] = args.iterations
    if args.timeout is not None:
        config['page-load-timeout'] = args.timeout
    if args.environment is not None:
        env = args.environment
    else:
        env = os.environ.get('CSC466ENV')
    if not env:
        logger.error('No --environment or CSC466ENV defined')
        sys.exit(1)
    if env not in ['local', 'ec2']:
        logger.error('Unexpected environment %s', env)
    config['environment'] = env
    config['single'] = args.single
    config['start-chrome'] = args.start_chrome
    logger.debug('Command line arguments parsed')
    return config


def generate_treatments(config):
    logger.debug('Generating treatments')
    default = config['treatment'].copy()
    default.update({
        'environment': config['environment'],
        'varying': 'none'
    })
    treatments = []
    for protocol in ['quic', 'tcp']:
        treatment = default.copy()
        treatment.update({
            'protocol': protocol
        })
        treatments.append(treatment)
        for name, values in config['variations'].items():
            # for each value in the varying dimension
            for value in values:
                variation = treatment.copy()
                variation.update({
                    name: value,
                    'varying': name
                })
                treatments.append(variation)
        for description in config['dual-variations']:
            axis1 = description['axis1']
            axis2 = description['axis2']
            assert axis1 in default
            assert axis2 in default
            for value1, value2 in description['values']:
                variation = treatment.copy()
                variation.update({
                    axis1: value1,
                    axis2: value2,
                    'varying': '{}, {}'.format(axis1, axis2)
                })
                treatments.append(variation)
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
    logger.debug('Executing request for {}'.format(url))
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
    for i, p in enumerate(payload):
        # logger.info('p %s %s', i, p['method'])
        if p['method'] == 'Network.servedFromCache':
            logger.error('Something was served from cache, exiting')
            sys.exit(1)
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


def save_results(config, treatments):
    root = os.path.join('data', config['environment'])
    try:
        shutil.rmtree(root)
    except FileNotFoundError:
        pass
    os.makedirs(root)
    path = os.path.join(root, 'results.json')
    results = config.copy()
    results['treatments'] = treatments
    with open(path, 'w') as ofp:
        json.dump(results, ofp, sort_keys=True, indent=4)


def run_treatment(config, router, chrome, treatment):
    logger.info('Running treatment %s', pprint.pformat(treatment))
    command = "sudo ./csc466/set_router.sh"
    logger.info('Running on router: %s', command)
    logger.info('Passing JSON to stdin: %s', json.dumps(treatment, indent=4, sort_keys=True))
    stdin, stdout, stderr = router.exec_command(command)
    stdin.write(json.dumps(treatment, indent=4, sort_keys=True))
    stdin.flush()
    stdin.close()
    stdin.channel.shutdown_write()
    retcode = stdout.channel.recv_exit_status()
    if retcode:
        logger.error('Retcode was %d, output was\n%s', retcode, stderr.read().decode('utf-8'))
        sys.exit(1)
    logger.info('Output was\n%s', stdout.read().decode('utf-8'))
    url = urljoin(
        config['host'],
        'page-{object-count}-{object-size}k.html'.format(**treatment)
    )
    logger.info('Running {} treatments on page {}'.format(config['iterations'], url))
    results = []
    for i in range(config['iterations']):
        results.append(execute_request(chrome, url))
        if (i+1) % (config['iterations'] // 10) == 0:
            logger.info('Executed {} of {}'.format(i + 1, config['iterations']))
    return results


def run_treatments(config, router, chromes, treatments):
    start = time.time()
    results = []
    cache = {}
    for i, treatment in enumerate(treatments):
        result = treatment.copy()
        key = tuple(sorted((key, value) for key, value in treatment.items() if key != 'varying'))
        if key not in cache:
            cache[key] = run_treatment(config, router, chromes[treatment['protocol']], treatment)
        else:
            logger.info('Found treatment in cache!')
        result['page-load-times'] = cache[key]
        results.append(result)
        if config['single']:
            logger.info('Single shot, exiting early')
            sys.exit(0)
        elapsed = time.time() - start
        done = i + 1
        predicted = (len(treatments) / done - 1) * elapsed
        logger.info('Completed {} of {} treatments in {:.1f} seconds, estimate {:.1f} minutes left'.format(done, len(treatments), elapsed, predicted / 60))
    return results


def main():
    absolute_start = time.time()
    config = parse_args()
    treatments = generate_treatments(config)
    # pprint.pprint(treatments)
    if config['start-chrome']:
        start_chrome_processes(config)
    chromes = connect_chrome_interfaces(config)
    router = ssh_connection('csc466-router')
    elapsed = time.time() - absolute_start
    logger.info('Took {:.1f} seconds to prepare for treatments'.format(elapsed))
    results = run_treatments(config, router, chromes, treatments)
    save_results(config, results)
    convert_data()


if __name__ == '__main__':
    sys.exit(main())
