
if __name__ != '__main__':
    exit()

import numpy as np
import time

# List TEST
t0 = time.perf_counter()
l = list()
for i in range(4000):
    l.append(i)
c = np.array(l, dtype='float64')
t1 = time.perf_counter()
print(t1 - t0)

t0 = time.perf_counter()
result = [
    i for i in l
    if i % 2 == 0
]
t1 = time.perf_counter()
print(t1-t0)

a = np.array(l, dtype='float64')
t0 = time.perf_counter()
filter = np.where(a % 2 == 0)
result = np.delete(a, filter)
t1 = time.perf_counter()
print(t1-t0)