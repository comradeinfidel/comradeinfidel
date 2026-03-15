"""Stripe payment tools for the AI assistant."""

import os
import stripe
from typing import Optional

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")


def send_payment(
    amount_cents: int,
    currency: str,
    description: str,
    to_email: Optional[str] = None,
    payment_method_id: Optional[str] = None,
) -> dict:
    """Create a payment intent via Stripe."""
    try:
        intent = stripe.PaymentIntent.create(
            amount=amount_cents,
            currency=currency.lower(),
            description=description,
            payment_method=payment_method_id,
            confirm=bool(payment_method_id),
            automatic_payment_methods={"enabled": True} if not payment_method_id else None,
            metadata={"to_email": to_email or ""},
        )
        return {
            "success": True,
            "payment_intent_id": intent.id,
            "status": intent.status,
            "amount": intent.amount,
            "currency": intent.currency,
            "client_secret": intent.client_secret,
            "description": description,
        }
    except stripe.StripeError as e:
        return {"success": False, "error": str(e)}


def get_payment_status(payment_intent_id: str) -> dict:
    """Check the status of a payment intent."""
    try:
        intent = stripe.PaymentIntent.retrieve(payment_intent_id)
        return {
            "success": True,
            "payment_intent_id": intent.id,
            "status": intent.status,
            "amount": intent.amount,
            "currency": intent.currency,
        }
    except stripe.StripeError as e:
        return {"success": False, "error": str(e)}


def list_recent_payments(limit: int = 10) -> dict:
    """List recent payment intents."""
    try:
        intents = stripe.PaymentIntent.list(limit=limit)
        payments = [
            {
                "id": p.id,
                "amount": p.amount,
                "currency": p.currency,
                "status": p.status,
                "description": p.description,
                "created": p.created,
            }
            for p in intents.data
        ]
        return {"success": True, "payments": payments}
    except stripe.StripeError as e:
        return {"success": False, "error": str(e)}
