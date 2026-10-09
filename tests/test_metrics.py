import math
from tesis_enasem.metrics import classification_metrics


def test_metrics():
    m=classification_metrics([0,1,0,1],[.1,.9,.2,.8])
    assert m['n']==4 and m['roc_auc']==1.0


def test_single_class_roc_auc_not_defined():
    m=classification_metrics([0,0],[.1,.2])
    assert math.isnan(m['roc_auc'])
