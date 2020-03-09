import argparse
import os

import pandas as pd
import stripe

stripe.api_key = os.environ["STRIPE_SECRET_KEY"]
stripe.api_version = "2020-03-02"


def get_subscriptions():
    parser = argparse.ArgumentParser(description="Get subscriptions")
    parser.add_argument("--out", help="If specified, write to this file")
    args = parser.parse_args()

    df = pd.DataFrame(
        columns=["name", "email", "status", "invoice status"], data=_subs_as_tuple()
    )

    if args.out:
        df.to_csv(args.out)
    else:
        with pd.option_context("display.max_rows", None, "display.max_columns", None):
            print(df)


def _subs_as_tuple():
    subs = stripe.Subscription.list(limit=100)
    for sub in subs.auto_paging_iter():
        cust = stripe.Customer.retrieve(sub.customer)
        invoice = stripe.Invoice.retrieve(sub.latest_invoice)
        yield cust.name, cust.email, sub.status, invoice.status


def add_subscription():
    parser = argparse.ArgumentParser(description="Add subscriptions")
    parser.add_argument("--email", required=True)
    parser.add_argument("--name", required=True)
    args = parser.parse_args()

    out = subscribe(args.email, args.name)
    print(out)


def subscribe(email: str, name: str = None) -> str:
    """
    Subscribe a new member or return their subscription
    """
    c_id = customer(email, name)

    subs = stripe.Subscription.list(customer=c_id)
    subs = [s for s in subs.data if s.status not in {"cancelled"}]

    if subs:
        print("Already subscribed")
        return subs[0].id

    print("Creating new subscription")
    s = stripe.Subscription.create(
        customer=c_id,
        items=[{"plan": plan()},],
        collection_method="send_invoice",
        days_until_due=30,
    )

    return s.id


def plan():
    """
    Fetch the annual membership plan
    """
    plans = stripe.Plan.list(limit=3)
    plans = [p for p in plans.data if p.nickname == "annual membership"]
    if len(plans) != 1:
        raise RuntimeError(f"Multiple plans matched 'annual membership'")
    elif not plans:
        raise RuntimeError(f"No plans matched 'annual membership'")

    return plans[0].id


def customer(email: str, name: str = None):
    """
    Fetch an existing customer by email address or create a new one
    """
    matches = stripe.Customer.list(email=email)
    if matches:
        print("Existing customer found")
        return matches.data[0].id

    print("Creating new customer")
    c = stripe.Customer.create(name=name, email=email,)
    return c.id
