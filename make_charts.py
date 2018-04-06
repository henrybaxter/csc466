import os
import json
import shutil
import pprint

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
    dimensions = [
        ('latency', 'Latency (ms)'),
        ('rate-limit', 'Rate Limit (mbit)'),
        ('packet-loss', 'Packet Loss (%)'),
        ('object-size', 'Object Size (kb)'),
        ('object-count', 'Object Count')
    ]
    for varying, label in dimensions:
        plt.figure()
        plt.title('QUIC vs TCP: Varying {} ({})'.format(label, environment))
        sns.barplot(x=varying, y='page-load-time', hue='protocol', data=df[(df.varying == varying) | (df.varying == 'none')])
        plt.xlabel(label)
        plt.ylabel('Page Load Time (ms)')
        slug = '{}'.format(varying)
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
        plot_each_tcp_vs_quic(results['treatments'], out_dir)
        bar_plots(df, environment, out_dir)


if __name__ == '__main__':
    main()
