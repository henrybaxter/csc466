import os
import json
import shutil
import pprint
import sys

import matplotlib.pylab as plt

import numpy as np
import seaborn as sns
from pandas import DataFrame


def similar_along(t1, t2, dims=['object-count', 'object-size', 'rate-limit', 'packet-loss', 'latency']):
    for dim in dims:
        if t1[dim] != t2[dim]:
            return False
    return True


def plot_each_tcp_vs_quic(treatments, out_dir):
    for i, t1 in enumerate(treatments):
        if 'environment' not in t1:
            t1['environment'] = 'local'
        for t2 in treatments[i+1:]:
            if similar_along(t1, t2):
                plt.figure()
                if t1['protocol'] == 'quic':
                    quic = np.array(t1['page-load-times'])
                    tcp = np.array(t2['page-load-times'])
                else:
                    quic = np.array(t2['page-load-times'])
                    tcp = np.array(t1['page-load-times'])
                sns.distplot(quic, label='QUIC')
                sns.distplot(tcp, label='TCP')
                plt.title('QUIC vs TCP: {object-count}x{object-size}kb, {rate-limit}mbit, {packet-loss}% loss, {latency}ms latency ({environment})'.format(**t1))
                plt.xlabel('Page Load Time (ms)')
                plt.ylabel('Empirical Distribution')
                plt.legend()
                slug = '{object-count}n-{object-size}k-{rate-limit}mbit-{packet-loss}loss-{latency}ms'.format(**t1)
                plt.savefig(os.path.join(out_dir, slug + '.eps'))
                plt.savefig(os.path.join(out_dir, slug + '.png'))
                plt.close()


def to_panda_dataframe(results):
    keys = list(results['treatments'][0].keys())
    keys.remove('page-load-times')
    keys.append('page-load-time')
    dict_in = {key: [] for key in keys}
    for t in results['treatments']:
        for page_load_time in t['page-load-times']:
            for key in keys:
                if key == 'page-load-time':
                    dict_in[key].append(page_load_time)
                else:
                    dict_in[key].append(t[key])
    return DataFrame(dict_in)


def bar_plots(df, environment, out_dir):
    # choose something 'varying', so regroup by 'varying', pairs...
    labels = {
        'delay-time': 'Delay Time (ms)',
        'delay-jitter': 'Delay Jitter (ms)',
        'delay-correlation': 'Delay Correlation (%)',
        'delay-distribution': 'Delay Distribution',
        'loss-p': 'Probability of Bad State',
        'loss-r': 'Probability of Recovered State',
        'loss-h': 'Inverse Loss Probability in Recovered State',
        'loss-k': 'Inverse Loss Probability in Bad State',
        'corrupt-percent': 'Corrupt Packets (%)',
        'corrupt-correlation': 'Corruption Correlation (%)',
        'duplicate-percent': 'Duplicate Packets (%)',
        'duplicate-correlation': 'Duplication Correlation (%)',
        'rate-limit': 'Rate Limit (mbit)',
        'object-count': 'Object Count',
        'object-size': 'Object Size (kb)'

    }
    df.varying.unique()
    for dimension in df.varying.unique():
        if ',' in dimension or dimension == 'none':
            continue
        plt.figure()
        plt.title('QUIC vs TCP: Varying {} ({})'.format(labels[dimension], environment))
        sns.barplot(x=dimension, y='page-load-time', hue='protocol', data=df[df.varying == dimension])
        plt.xlabel(labels[dimension])
        plt.ylabel('Page Load Time (ms)')
        slug = '{}'.format(dimension)
        plt.savefig(os.path.join(out_dir, slug + '.eps'))
        plt.savefig(os.path.join(out_dir, slug + '.png'))
        plt.close()


def main():
    for environment in os.listdir('data'):
        if environment == '.DS_Store':
            continue
        print('Plotting', environment)
        in_path = os.path.join('data', environment, 'results.json')
        results = json.load(open(in_path))
        out_dir = os.path.join('plots', environment)
        try:
            shutil.rmtree(out_dir)
        except FileNotFoundError:
            pass
        os.makedirs(out_dir)
        df = to_panda_dataframe(results)
        # plot_each_tcp_vs_quic(results['treatments'], out_dir)
        bar_plots(df, environment, out_dir)


if __name__ == '__main__':
    main()
