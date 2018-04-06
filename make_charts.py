import os
import json
import shutil

import matplotlib.pylab as plt

import numpy as np
import seaborn as sns


def stringify(treatment):
    return '{protocol}-{object-count}n-{object-size}k-{rate-limit}mbit-{packet-loss}loss-{latency}ms'.format(**treatment)


def similar_along(t1, t2, dims=['object-count', 'object-size', 'rate-limit', 'packet-loss', 'latency']):
    for dim in dims:
        if t1[dim] != t2[dim]:
            return False
    return True


def plot_each_tcp_vs_quic(results, out_dir):
    for i, t1 in enumerate(results['treatments']):
        if 'environment' not in t1:
            t1['environment'] = 'local'
        for t2 in results['treatments'][i+1:]:
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
                plt.savefig(os.path.join(out_dir, '{object-count}n-{object-size}k-{rate-limit}mbit-{packet-loss}loss-{latency}ms'.format(**t1) + '.eps'))
                plt.close()


def main():
    for environment in os.listdir('data'):
        print('Plotting', environment)
        in_path = os.path.join('data', environment, 'results.json')
        results = json.load(open(in_path))
        out_dir = os.path.join('plots', environment)
        try:
            shutil.rmtree(out_dir)
        except FileNotFoundError:
            pass
        os.makedirs(out_dir)
        plot_each_tcp_vs_quic(results, out_dir)


if __name__ == '__main__':
    main()
