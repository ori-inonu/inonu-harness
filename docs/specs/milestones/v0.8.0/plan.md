# v0.8.0 implementation plan

Read [spec.md](spec.md) for the frozen input/output contract and [decisions.md](decisions.md) for its sources and decisions.

1. Deliver the local library audit with public behavior tests and five frozen synthetic cases. Validate paths/digests and fail incomplete or disconnected handoffs.
2. Expose the audit through the existing CLI, document its use and limitations, and exercise the unchanged baseline v1 seam using computed audit results.
3. Obtain separate read-only standards and specification reviews; repair confirmed findings.
4. Record real test evidence, create a hash-bound self-audit of this milestone's requirements/tasks/checks, run it, and complete the native graph only after deterministic convergence.

No schema migration or installation is needed. Existing dirty v0.6/v0.7 work remains owned by its prior increments.
