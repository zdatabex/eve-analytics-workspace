# Local Development

## Requirements

- Git
- Bash
- Python (for Python-based components)
- Docker (where required)
- Access to the development warehouse

## Environment

Use component-specific environment files.
Never commit credentials or secrets.

## Testing

Run component tests before integration tests.

Cross-component changes must include integration validation
against the relevant contracts.
