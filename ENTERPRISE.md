# Apex Enterprise Features

Reserved for a future Enterprise tier. These are intentionally out of scope for the free and Team plans.

## Multi-node & Distributed Training
- Multi-node cluster support (schedule jobs across multiple GPU machines)
- Gang scheduling for distributed training (all-or-nothing GPU allocation)
- Fractional GPU sharing (MIG / time-slicing for interactive + training on the same GPU)

## Advanced Scheduling
- Preemption (high-priority jobs can evict low-priority ones)
- Fair-share scheduling across users/teams
- Resource quotas per user or group

## Image Management
- Built-in image builder (Buildkit-based, no external registry needed)
- Private registry integration
- Image caching and layer deduplication

## Experiment Tracking & Artifacts
- Native experiment tracking (metrics, hyperparameters, model versioning)
- Artifact storage and lineage
- W&B / MLflow deep integration (auto-log from jobs)
- Historical GPU utilization graphs per user / per project

## Enterprise Auth & Compliance
- SSO (SAML / OIDC)
- RBAC with custom roles
- Audit logging
- Namespace isolation between teams
