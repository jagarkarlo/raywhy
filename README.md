# raywhy

<p align="center">
  <img src="https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/Ray-028CF0?style=for-the-badge" alt="Ray">
  <img src="https://img.shields.io/badge/Kubernetes-326CE5?style=for-the-badge&logo=kubernetes&logoColor=white" alt="Kubernetes">
  <img src="https://img.shields.io/badge/Prometheus-E6522C?style=for-the-badge&logo=prometheus&logoColor=white" alt="Prometheus">
  <img src="https://img.shields.io/badge/License-Apache_2.0-3FB950?style=for-the-badge" alt="License">
</p>

**Explain why your Ray job is pending.**

`raywhy` answers one question that Ray's dashboard cannot: *why is this job still
PENDING, and what do I do about it?*

On a single-user Ray cluster you rarely need to ask. On a shared, multi-tenant
KubeRay cluster it is the most common support question there is — and the
existing answer is "go read the autoscaler logs."

## The problem

Ray's dashboard shows you **state**. It does not show you **causality**.

A job sits in PENDING. The dashboard tells you it is pending. It does not tell
you whether:

- the resource shape is **unsatisfiable** — no node type in the cluster can ever
  host this placement group, so the job will wait forever
- the cluster is **contended** — the shape is fine, but another workload holds
  the resources, and you are Nth in line behind it
- the autoscaler is **throttled or capped** — a node could be added, but
  `maxReplicas`, a quota, or a cooldown is blocking it
- the nodes are **unavailable** — cordoned, NotReady, or failing to pull an image

These four cases have completely different remedies. Today you distinguish them
by hand, by reading Ray logs and `kubectl describe` output side by side.

`raywhy` distinguishes them for you.

## What the v0.1 CLI looks like

```
$ raywhy job job-1 --snapshot tests/fixtures/unsatisfiable.json

UNSATISFIABLE
Job       job-1
Verdict   No schedulable node shape can satisfy this job's resource request.
Evidence  Requested resources: {'GPU': 4.0, 'CPU': 8.0}
Fix       Change the resource request or add a node type that can host it.
```

Live Ray API access, placement-group detail, pending duration, and blocker
attribution are v0.2 work. The examples from those future capabilities belong in
the roadmap, not in the current CLI contract.

## Non-goals

`raywhy` is **read-only and diagnostic**. It does not:

- schedule, preempt, evict, or cancel anything
- mutate cluster state in any way
- replace the Ray dashboard or the autoscaler
- require an agent, sidecar, or control plane

It reads the Ray Job Submission API, the Ray state API, and the Kubernetes API,
and it explains what it finds.

## v0.1 today

The first release proves the verdict engine against a small normalized snapshot
format. The CLI is deliberately read-only and adapter-independent while the Ray
API mapping is developed:

```bash
python -m pip install -e .
raywhy job job-1 --snapshot snapshot.json
raywhy job job-1 --snapshot snapshot.json --json
```

The snapshot contract contains `jobs`, `nodes`, and optional `autoscaler` data:

```json
{
  "jobs": {
    "job-1": {
      "state": "PENDING",
      "request": {"resources": {"GPU": 2, "CPU": 8}}
    }
  },
  "nodes": [
    {
      "id": "gpu-a",
      "schedulable": true,
      "condition": "Ready",
      "total": {"GPU": 4, "CPU": 32},
      "available": {"GPU": 0, "CPU": 4}
    }
  ],
  "autoscaler": {"blocked": true, "reason": "worker group reached maxReplicas"}
}
```

The engine returns `UNSATISFIABLE`, `CONTENDED`, `AUTOSCALER_BLOCKED`,
`NODES_UNAVAILABLE`, or `UNKNOWN`, with evidence and a suggested next action.
The four known-cause fixtures under `tests/fixtures/` are the executable
contract for v0.1.

## Status

**Pre-alpha.** The fixture-driven verdict engine and CLI are working; live Ray
and Kubernetes adapters are next. See [ROADMAP.md](ROADMAP.md).

## Contributing

Issues describing a pending job that `raywhy` explains badly are the most
valuable contribution right now. Include the resource request, the cluster's
node shapes, and what the real cause turned out to be.

## License

Apache-2.0
