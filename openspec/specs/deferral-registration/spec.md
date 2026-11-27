# deferral-registration Specification

## Purpose
TBD - created by archiving change add-deferral-registration-guard. Update Purpose after archive.

## Requirements

### Requirement: Deferral statements SHALL carry a registration target

Every deferral statement in improvement or review documents (`另案` / `另立` / `另行立项` / `后续另案`) SHALL immediately name a registration target: `另案（已登记：<improvement-slug>）` or `另案（backlog：<topic>）`. `rddf doctor` SHALL report one warning naming the file and the line when a deferral carries no target, and SHALL stay silent for registered deferrals and for the recorded exemption list.

#### Scenario: An unregistered deferral is reported

- **WHEN** an improvement document contains a deferral statement without a registration target
- **THEN** `rddf doctor` runs
