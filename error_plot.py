from matplotlib import pyplot as plt
import csv

with open('execute.log') as fp:
    execute_rdr = csv.DictReader(fp, fieldnames='k,time,error,register,target'.split(','))

    for i, d in enumerate(execute_rdr):
        t = float(d['time'])
        if i == 0:
            t0 = t
        if d['error'].lower() == 'false':
            plt.axvline((t - t0) * 1e-9)

with open('key.log') as fp:
    key_rdr = csv.DictReader(fp, fieldnames='k,time,bit,error,register,target'.split(','))

    for i, d in enumerate(key_rdr):
        t = float(d['time'])

        if d['error'].lower() == 'false':
            plt.axvline(((t - t0) * 1e-9), color='orange')
plt.show()