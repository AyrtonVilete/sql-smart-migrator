import pytest
from src.agent import Agent


def test_greet():
    a = Agent("Tester")
    assert "Tester" in a.greet()


def test_run_task():
    a = Agent()
    res = a.run_task("build")
    assert res["task"] == "build"
    assert res["status"] == "completed"
