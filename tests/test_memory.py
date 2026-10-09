from app.memory.store import MemoryStore


def test_memory_round_trip(tmp_path):
    store = MemoryStore(str(tmp_path / "memory.db"))
    store.save_insight("CL001", "HIGH", "Needs review", {"anomaly_count": 2})

    items = store.recent_insights("CL001")
    assert len(items) == 1
    assert items[0]["risk_level"] == "HIGH"
    assert items[0]["payload"]["anomaly_count"] == 2
