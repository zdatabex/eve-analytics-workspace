# System Overview

## Component boundaries

### Contracts
Defines shared interfaces between components:
- Data schemas
- Event definitions
- Naming conventions
- Entity definitions
- Data ownership metadata

### Data Generation
Creates or ingests source data for development and testing.

### Warehouse / dbt
Owns:
- Staging models
- Intermediate transformations
- Marts
- Data quality tests
- Documentation

### Analytics
Hex and Omni consume governed warehouse models and shared metadata.

### Agent Platform
Coordinates ticket execution, planning, implementation, testing,
reviews, and delivery.

### Infrastructure
Owns infrastructure provisioning, environments, permissions,
and deployment configuration.

## Dependency direction

Contracts are the shared interface.

Data generation produces source data.
dbt transforms source data into governed models.
Analytics applications consume governed models.

Agents coordinate work across these boundaries without
taking ownership away from the components.
