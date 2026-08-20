# raywhy

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

## What it looks like

```
$ raywhy job raysubmit_a1b2c3

PENDING for 41m

  Requests   1 placement group, STRICT_SPREAD
             4 bundles x {GPU: 1, CPU: 2}

  Verdict    UNSATISFIABLE
             No node type in this cluster can satisfy the placement group.
             STRICT_SPREAD requires 4 distinct nodes with >=1 GPU each.
             Cluster has 2 GPU-capable nodes (max 2 by autoscaler config).

  Fix        Relax to PACK/SPREAD, reduce to 2 bundles, or raise
             maxReplicas on the GPU worker group above 4.
```

```
$ raywhy job raysubmit_d4e5f6

PENDING for 6m

  Requests   {GPU: 2, CPU: 8}

  Verdict    CONTENDED
             Shape is satisfiable. Resources are held by other work.
             Head-of-line blocker: raysubmit_9z8y7x (RUNNING 3h12m, holds 2 GPU)

  Fix        Wait, or raise priority. Nothing is misconfigured.
```

## Non-goals

`raywhy` is **read-only and diagnostic**. It does not:

- schedule, preempt, evict, or cancel anything
- mutate cluster state in any way
- replace the Ray dashboard or the autoscaler
- require an agent, sidecar, or control plane

It reads the Ray Job Submission API, the Ray state API, and the Kubernetes API,
and it explains what it finds.

## Status

**Pre-alpha.** Nothing works yet. See [ROADMAP.md](ROADMAP.md).

## Contributing

Issues describing a pending job that `raywhy` explains badly are the most
valuable contribution right now. Include the resource request, the cluster's
node shapes, and what the real cause turned out to be.

## License

Apache-2.0
