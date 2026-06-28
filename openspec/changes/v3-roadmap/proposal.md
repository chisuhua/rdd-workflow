## Why

After completing v2.0.0-beta (5 phases, all 8 ADRs from ADR-0002~0008 implemented), 4 ADRs remain adopted but unimplemented:

| ADR | Subject | Status |
|-----|---------|--------|
| ADR-0009 | Scheduled triggers & event-driven loops | Draft |
| ADR-0010 | Full multi-session management (v2.1 scope) | Phased adoption |
| ADR-0011 | Phase-step pipeline execution model | Adopted |
| ADR-0012 | Flow customization layer | Adopted |

Without explicit planning, these ADRs become "design shelfware" — adopted on paper but never prioritized. This change evaluates each ADR, decides its release target (v2.1 patch vs v3.0), creates placeholder changes for each, and updates `roadmap.md` to reflect the forward direction.

## What Changes

- **Evaluate** each of the 4 unimplemented ADRs for effort, value, and dependencies
- **Decide** release target for each: v2.1 (smaller, compatible) vs v3.0 (larger, potentially breaking)
- **Create** placeholder openspec changes for each approved ADR
- **Update** `roadmap.md` with concrete v3.0 phases and milestones
- **Document** decisions in the ADR status table in `docs/adr/README.md`

## Capabilities

### New Capabilities
- `v3-roadmap-plan`: Forward-looking roadmap from v2.0-beta to v3.0
- `future-adr-placeholders`: Openspec change shells for each approved ADR

### Modified Capabilities
- `roadmap-md` (roadmap.md): Updated from generic Phase-1 placeholder to concrete v3.0 planning