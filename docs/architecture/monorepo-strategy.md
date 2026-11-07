# Monorepo Strategy

The monorepo is the development and integration boundary,
not necessarily the permanent deployment boundary.

Components have explicit paths and ownership in workspace.yaml.

Initially, Hex and dbt live in the same Git repository.
They retain separate directories, configuration, tests,
and deployment lifecycles.

If a component needs to become an independent repository:

1. Extract its directory into a new repository.
2. Assign the repository URL in workspace.yaml.
3. Preserve its component contract and integration interface.
4. Update the orchestration layer to coordinate its repository.
5. Continue running cross-component integration tests.

The ticket workflow should not assume all components will
always live in the same Git repository.
