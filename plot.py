import os
import json
import shutil
import sqlite3

import matplotlib
matplotlib.use('TKAgg')
import matplotlib.pylab as plt

import numpy as np
import seaborn as sns


def stringify(treatment):
    return '{protocol}-{object-count}n-{object-size}k-{rate-limit}mbit-{packet-loss}%-{latency}ms'.format(**treatment)


def similar_along(t1, t2, dims=['object-count', 'object-size', 'rate-limit', 'packet-loss', 'latency']):
    for dim in dims:
        if t1[dim] != t2[dim]:
            return False
    return True


def main():
    try:
        shutil.rmtree('plots')
    except FileNotFoundError:
        pass
    os.makedirs('plots')
    treatments = json.load(open('data/treatments.json'))
    # if we group both protocols together, we can always compare them
    # can we find some that are equal in every other way?

    # choose a dimension to vary along
    for dim in ['latency', 'rate-limit', 'packet-loss', 'object-size', 'object-count']:
        for t in treatments:
            data = {}
            if t['varying'] == dim:
                data.setdefault(t['protocol'], []).append(t)
            # now got it varying along, ok, now


    for i, t1 in enumerate(treatments):
        for t2 in treatments[i+1:]:
            if similar_along(t1, t2):
                plt.figure()
                if t1['protocol'] == 'quic':
                    quic = np.array(t1['results'])
                    tcp = np.array(t2['results'])
                else:
                    quic = np.array(t2['results'])
                    tcp = np.array(t1['results'])
                sns.distplot(quic, label='QUIC')
                sns.distplot(tcp, label='TCP')
                plt.xlabel('PLT (ms)')
                plt.ylabel('Empirical Distribution')
                plt.legend()
                plt.savefig('plots/{object-count}n-{object-size}k-{rate-limit}mbit-{packet-loss}%-{latency}ms'.format(**t1) + '.png')
                plt.close()

    for treatment in treatments:
        plt.figure()
        a = np.array(treatment['results'])
        b = a[abs(a - np.mean(a)) < np.std(a)]
        sns.distplot(b)
        plt.savefig('plots/' + stringify(treatment) + '.png')
        plt.close()


if __name__ == '__main__':
    main()
