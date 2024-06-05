
if __name__ != '__main__':
    exit()

import numpy as np
import time
a = ['george']*10000
b = ['george']*10000

print(len(a))
t1 = time.perf_counter()
total = 0
for i in range(3000): # xrange is slower according 
    for j in range(2):            #to my test but more memory-friendly.
        total += i
t2 = time.perf_counter()
print(total, t2-t1)