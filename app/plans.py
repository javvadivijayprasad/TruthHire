"""Subscription plans (S16). Base credits + per-check rate + contribution multiplier."""
from __future__ import annotations

PLANS = {
    "free":       {"fee": 0,   "base_credits": 0,    "check_rate": 0.75, "multiplier": 1.0},
    "starter":    {"fee": 99,  "base_credits": 150,  "check_rate": 0.70, "multiplier": 1.1},
    "growth":     {"fee": 299, "base_credits": 500,  "check_rate": 0.65, "multiplier": 1.25},
    "scale":      {"fee": 799, "base_credits": 1500, "check_rate": 0.55, "multiplier": 1.5},
    "enterprise": {"fee": None,"base_credits": None, "check_rate": 0.50, "multiplier": 2.0},
}


def plan(name: str) -> dict:
    return PLANS.get(name, PLANS["free"])
