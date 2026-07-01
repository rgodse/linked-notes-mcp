from optimize.salience import importance_weight, salience_score, rerank

def test_importance_weight_defaults():
    assert importance_weight({"importance": "high"}) == 1.0
    assert importance_weight({"importance": "low"}) == 0.3
    assert importance_weight({}) == 0.5

def test_rerank_prefers_important_on_tie():
    # equal relevance, higher importance wins
    cands = [("a", 0.5, {"importance": "low"}), ("b", 0.5, {"importance": "high"})]
    assert rerank(cands) == ["b", "a"]

def test_rerank_relevance_dominates_with_default_weights():
    cands = [("a", 0.9, {"importance": "low"}), ("b", 0.2, {"importance": "high"})]
    assert rerank(cands)[0] == "a"
