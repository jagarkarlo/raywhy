# Roadmap

Ship order is chosen so that each phase is independently useful. If development
stops after any phase, what exists still solves a real problem.

## v0.1 — The verdict engine (CLI, read-only)

The whole value proposition, in the smallest shippable form.

- [x] Pure verdict engine over a normalized, read-only snapshot
- [x] Fixture-driven classification for `UNSATISFIABLE` | `CONTENDED` | `AUTOSCALER_BLOCKED` | `NODES_UNAVAILABLE`
- [x] Human-readable output with evidence and a concrete suggested fix
- [x] `--json` for scripting
- [x] `raywhy job <submission-id> --address <ray-dashboard>` against a Ray dashboard address
- [x] Read pending jobs via the Ray Job Submission API
- [x] Read node resource totals/availability via the Ray cluster status API

**Current result:** all four cases are covered by deterministic JSON fixtures and
the standard-library test suite. The live API adapter remains deliberately
unimplemented until the normalized contract is stable.

## v0.2 — Placement groups and blame

Where the genuinely hard logic lives.

- [x] Read-only Ray dashboard client for jobs and cluster status
- [x] Queue command for all pending normalized jobs
- [x] Explicit resource hints when the Jobs API omits the request
- [ ] Full placement group parsing: bundles, `PACK` / `SPREAD` / `STRICT_PACK` / `STRICT_SPREAD`
- [ ] Bin-packing feasibility check against real node shapes, not just totals
- [ ] Head-of-line blocker attribution — name the specific job/actor holding what you need
- [ ] Distinguish "will never schedule" from "will schedule eventually"
- [ ] `raywhy queue` — the whole pending queue with verdicts, sorted by wait time

**Done when:** given a cluster where a STRICT_SPREAD job is unsatisfiable, it
names the exact constraint that fails.

## v0.3 — Kubernetes awareness

- [ ] KubeRay CRD reading: `RayCluster`, `RayJob`, worker group specs
- [ ] Autoscaler bounds — `minReplicas` / `maxReplicas` per worker group
- [ ] Node conditions: cordoned, `NotReady`, taints without matching tolerations
- [ ] Pending Ray pods blocked at the k8s layer (quota, image pull, PVC binding)
- [ ] Correctly attribute k8s-layer causes rather than blaming Ray

## v0.4 — Prometheus exporter

- [ ] `raywhy export` — long-running exporter on `/metrics`
- [ ] `raywhy_job_pending_seconds{job_id, verdict}`
- [ ] `raywhy_job_pending_verdict{job_id, verdict}` (gauge, 1 for active verdict)
- [ ] `raywhy_queue_depth{verdict}`
- [ ] `raywhy_blocked_by{job_id, blocker_job_id}`
- [ ] Stable metric contract documented and versioned

**Done when:** you can alert on `UNSATISFIABLE` jobs, which is the alert every
shared cluster wants and nobody has.

## v0.5 — Grafana dashboards

- [ ] Dashboard pack: queue depth by verdict, pending duration heatmap, blocker graph
- [ ] Published to the Grafana dashboard catalogue
- [ ] Generated as code, not hand-edited JSON

## v0.6 — Ergonomics

- [ ] `raywhy watch` — live TUI of the pending queue
- [ ] `raywhy explain <shape>` — "would a job requesting X schedule right now?" (pre-flight)
- [ ] Pending-history retention so you can answer "why was it pending yesterday?"

## Explicitly out of scope

These are deliberate refusals, not unbuilt features:

- Any mutation of cluster state
- Scheduling policy, priority, or preemption
- A hosted service or SaaS component
- Support for non-Ray schedulers (Slurm, Volcano, Kueue) before v1.0

## Compatibility

- Ray: target the current stable minor, test against the previous one
- Kubernetes: current minus two
- Python: 3.10+
