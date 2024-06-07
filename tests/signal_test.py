from cognixlib.api.data import *
import numpy as np

def run():
    
    # LABELS TEST
    size = 5
    # x0 until x4
    labels = [f"x{i}" for i in range(size)]
    data = np.random.rand(3, size)
    a = LabeledSignal(labels, data, None)
    
    assert np.array_equal(
        a.ldm['x1':'x3'].data, 
        a[:, 1:4]
    ) # x3 is inclusive
    assert np.array_equal(
        a.ldm['x2'].data, 
        a[:, 2]
    )
    assert np.array_equal(
        a.ldm[['x1', 'x2', 'x4']].data, 
        a[:, [1, 2, 4]]
    )

    # TIMESTAMPS TEST
    timestamps = np.random.rand(size)
    data = np.random.rand(size, 6)
    a = TimeSignal(timestamps, data, None)
    
    assert np.array_equal(
        a.tdm[0:2].data, 
        a[0:2]
    )
    assert np.array_equal(
        a.tdm[4].data, 
        a[4]
    )
    
    # STREAM TEST - MUST BE USED IN LSL
    b = StreamSignal(timestamps, labels, data, None)
    
    # CLASS TEST - MUST BE USED FOR TRAINING
    # same labels as above, x0 until x4
    data = np.random.rand(25, size)
    classes = {
        "george": (0, 14), # EXCLUSIVE
        "john": (14, 25)
    }
    f1 = FeatureSignal(
        labels,
        classes,
        data,
        None
    )
    
    assert np.array_equal(
        f1.cdm["george"].data, 
        f1[0:14]
    )
    assert np.array_equal(
        f1.cdm["john"].data, 
        f1[14:25]
    )
    
    # CLASS MERGE TEST
    data = np.random.rand(30, size)
    classes = {
        "john": (10, 20),
        "george": (0, 10),
        "dam": (20, 30)
    }
    f2 = FeatureSignal(
        labels,
        classes,
        data,
        None,
    )
    
    f_signal = FeatureSignal.concat_classes(f1, f2)

    assert np.array_equal(
        f_signal.cdm['george'].data[0:14],
        f1.cdm['george'].data
    )
    assert np.array_equal(
        f_signal.cdm['john'].data[11:21],
        f2.cdm['john'].data
    )
    
    # REMOVE TESTs
    
    # Class remove
    new_sig = f2.withoutRows(slice(0, 15))
    assert np.array_equal(
        f2.cdm['john'].data[5:10],
        new_sig.cdm['john'].data
    )
    
    new_sig = f2.withoutRows(slice(15, 23))
    assert np.array_equal(
        f2.cdm['dam'].data[3:10],
        new_sig.cdm['dam'].data
    )
    
    # test for removing class
    new_data = np.random.rand(100000, 5)
    import time
    t0 = time.perf_counter()
    labels = ['A', 'B', 'C', 'D', 'E']
    classes = {
        "k0": (0,10000),
        "k1": (10000, 20000),
        "k2": (20000, 30000),
        "k3": (30000, 40000),
        "k4": (40000, 50000),
        "k5": (50000, 60000),
        "k6": (60000, 70000),
        "k7": (70000, 80000),
        "k8": (80000, 90000),
        "k8": (90000, 100000)
    }
    new_sig = FeatureSignal(
        labels,
        classes,
        new_data,
        None
    )
    t1 = time.perf_counter()
    new_sig = new_sig.withoutRows(slice(15000, 46750))
    t2 = time.perf_counter()
    print(f"CREATION: {t1-t0}")
    print(f"WITHOUT ROWS: {t2-t1}")
if __name__ == '__main__':
    run()