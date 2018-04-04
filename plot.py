
import matplotlib
matplotlib.use('TKAgg')
import matplotlib.pylab as plt

import numpy as np
import seaborn as sns
def stringify(treatment):
    return '{protocol}-{object-count}n-{object-size}k-{rate-limit}mbit-{packet-loss}%-{latency}ms'.format(**treatment)
