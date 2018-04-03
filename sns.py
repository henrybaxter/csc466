import matplotlib
matplotlib.use('TKAgg')
import matplotlib.pylab as plt
import seaborn as sns
import numpy as np

sns.set(color_codes=True)
x = np.random.normal(size=100)
print(x)
sns.distplot(x)
plt.show()
