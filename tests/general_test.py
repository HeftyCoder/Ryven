
if __name__ != '__main__':
    exit()

import numpy as np
import time

a = np.random.rand(10, 10)
a = np.delete(a, [0, 3, 5], axis=0)
print(a.shape)
print(a)