import math
import numpy as np
from scipy.stats import t


def mean_confidence(data, confidence=.95):
    values = np.array(data)
    mean = values.mean()
    #confidence_interval = t.interval(confidence, values.size-1, loc=mean, scale=values.std()/math.sqrt(values.size))
    h = values.std() / math.sqrt(values.size) * t.ppf((1 + confidence) / 2., values.size - 1)
    return (mean, h)


def jain_fairness(data):
    if len(data) == 0:
        return 1
    return sum(data)**2 / (len(data) * sum([x**2 for x in data]))
