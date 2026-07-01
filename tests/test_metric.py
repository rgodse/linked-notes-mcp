from optimize.metric import recall_at_k, mrr

def test_recall_at_k():
    assert recall_at_k(["a","b","c"], ["a","c"], 5) == 1.0
    assert recall_at_k(["a","x","y"], ["a","c"], 5) == 0.5
    assert recall_at_k(["x","y","z","a"], ["a"], 3) == 0.0   # a is outside top-3
    assert recall_at_k(["a"], [], 5) == 1.0                   # empty gold => trivially satisfied

def test_mrr():
    assert mrr(["a","b"], ["a"]) == 1.0
    assert mrr(["x","a"], ["a"]) == 0.5
    assert mrr(["x","y"], ["a"]) == 0.0
