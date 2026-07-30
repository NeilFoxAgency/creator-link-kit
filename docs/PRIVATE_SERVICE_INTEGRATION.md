# Private attribution service integration

`creator-link-kit` is the deterministic link-policy layer. It should remain
safe to publish, install in CI, and run without network access.

A separate private service should own managed-link provider credentials,
commerce integrations, click and conversion events, and client reporting.

## Boundary

The public package is responsible for:

- validating the UTM convention
- building the original governed destination URL
- enforcing placement identity and batch uniqueness
- rejecting unapproved production destinations
- producing a portable link specification
- optionally generating placement-specific discount-code and QR artifacts
- defining provider-neutral request and response models

The private service is responsible for:

- authenticating to a link provider
- selecting a custom tracking domain and slug
- creating or retrieving the managed tracking link idempotently
- storing provider link IDs and tracking URLs
- receiving and verifying provider webhooks
- integrating with merchant order and refund systems
- calculating attribution and ROAS
- protecting client and customer data

No provider adapter or credential loader should be added to this repository.

## Suggested flow

1. Create stable brand, campaign, creator, and placement IDs in the private
   campaign database.
2. Call `build_link_specification` with those IDs and the approved destination.
3. Refuse provisioning unless `specification.audit.valid` is true.
4. Convert the specification to `LinkProvisionRequest`.
5. Pass the request to a private `LinkProvider` implementation.
6. Store the returned `ProvisionedLink` beside the immutable specification.
7. Create or verify the placement-specific discount code in the merchant system.
8. Give the creator only the managed tracking URL and approved discount code.

## Idempotency

The private adapter should treat `placement_id` as the business idempotency key.
A retry for the same placement should return the existing managed link unless an
explicit, audited replacement operation was approved.

Do not infer identity from a slug or creator handle. Both can change or collide.

## Example adapter skeleton

This example is intentionally non-networked and contains no provider-specific
fields:

```python
from creator_link_kit import LinkProvider, LinkProvisionRequest, ProvisionedLink


class PrivateManagedLinkAdapter(LinkProvider):
    def provision(self, request: LinkProvisionRequest) -> ProvisionedLink:
        placement_id = request.identifiers.placement_id
        if placement_id is None:
            raise ValueError("placement_id is required for managed links")

        existing = self.lookup_by_placement_id(placement_id)
        if existing is not None:
            return existing

        # Translate the request inside the private service, call the selected
        # provider, and persist the provider response atomically.
        raise NotImplementedError
```

## Recommended persistence

Store the complete link specification as immutable JSON together with:

- internal placement record ID
- provider name
- provider link ID
- managed tracking URL
- configuration fingerprint from the immutable link specification
- provisioning idempotency key
- creation timestamp
- last verification timestamp
- active or replaced status

Do not mutate an old specification after a published link changes. Create a new
revision and retain the prior record for auditability.

## Data minimization

The public models intentionally omit:

- credentials and tokens
- customer identifiers
- order and invoice identifiers
- sale amounts and currencies
- discount codes
- conversion or refund events
- arbitrary metadata dictionaries

Those data types belong in purpose-built private models with access controls,
retention rules, and audit logs.

## Agent exposure

Expose a narrow private tool such as `provision_placement_tracking` rather than
giving an agent raw provider credentials. The tool should:

- accept a placement ID or validated link specification
- enforce the approved brand and destination policy
- use an idempotency key
- return only the managed URL and non-secret provider record identifiers
- log every mutation

Destination changes after publication, domain changes, credential changes, and
conversion reassignment should remain separately controlled operations.
