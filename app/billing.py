"""Stripe-ready billing (S16 / TH-030).

Offline by default (returns a mock checkout and activates the plan locally). If
STRIPE_API_KEY is set and the `stripe` package is installed, a live integration
would create a real Checkout Session here. Webhook events activate/suspend plans."""
from __future__ import annotations
import os
from .plans import plan
from .credits import ledger


def is_live() -> bool:
    return bool(os.environ.get("STRIPE_API_KEY"))


def create_checkout(org: str, plan_name: str) -> dict:
    p = plan(plan_name)
    if is_live():  # pragma: no cover - requires real Stripe + network
        # import stripe; stripe.api_key = os.environ["STRIPE_API_KEY"]
        # session = stripe.checkout.Session.create(...); return {"checkout_url": session.url}
        return {"mode": "live", "note": "wire stripe.checkout.Session.create here"}
    # offline/sandbox: activate immediately and return a mock URL
    ledger.set_plan(org, plan_name)
    return {"mode": "sandbox", "plan": plan_name, "fee": p["fee"],
            "checkout_url": f"https://sandbox.checkout/local/{org}/{plan_name}",
            "activated": True}


def handle_event(event_type: str, org: str, plan_name: str = "free") -> dict:
    if event_type == "checkout.session.completed":
        ledger.set_plan(org, plan_name)
        return {"status": "plan_activated", "org": org, "plan": plan_name}
    if event_type == "invoice.payment_failed":
        ledger.set_plan(org, "free")
        return {"status": "suspended_to_free", "org": org}
    return {"status": "ignored", "event": event_type}
