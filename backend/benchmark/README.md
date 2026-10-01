# Integrity benchmark

`integrity_benchmark.js` provides a dependency-free Node.js reference implementation used by `backend/tests/integrity.test.js` to verify:

- deterministic canonical JSON ordering for the supported JSON values;
- SHA-256 hashing;
- linked hash-chain verification and tamper detection;
- a conservative CI performance guard of under 500 ms per phase for 1,000 events.

Run it from the repository root with:

```bash
node --test backend/tests/integrity.test.js
```

The performance threshold is a regression guard, not a production throughput claim. Actual throughput depends on hardware and workload.
