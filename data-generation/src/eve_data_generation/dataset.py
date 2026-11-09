"""Build a dataset from configuration and an optional population."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from eve_data_generation.config import Config, ensure_window
from eve_data_generation.contracts import Contract, load_contracts
from eve_data_generation.errors import ConfigError
from eve_data_generation.population import baseline_population
from eve_data_generation.scenarios import scenario_population
from eve_data_generation.validate import validate_dataset
from eve_data_generation.world import World

Population = object


@dataclass
class Dataset:
    seed: int
    config_file: str
    start_date: date
    end_date: date
    delivery_id: str
    rows: dict[str, list[dict]]


def _check_vocabulary(config: Config, contracts: dict[str, Contract]) -> None:
    stages = set(contracts["hubspot.deal"].allowed("stage"))
    if not set(config.stage_mix) <= stages:
        raise ConfigError("stage_mix contains a stage outside the deal contract")
    if set(config.lead_status_mix) != set(contracts["hubspot.lead"].allowed("status")):
        raise ConfigError("lead_status_mix must cover the lead status vocabulary")
    if set(config.channel_mix) != set(contracts["marketing.campaign"].allowed("channel")):
        raise ConfigError("channel_mix must cover the campaign channel vocabulary")
    if set(config.forecast_by_stage) != stages:
        raise ConfigError("forecast_by_stage must cover every deal stage")
    allowed_forecast = set(contracts["hubspot.deal"].allowed("forecast_category"))
    if not set(config.forecast_by_stage.values()) <= allowed_forecast:
        raise ConfigError("forecast_by_stage contains a value outside the deal contract")
    activity_types = set(contracts["hubspot.activity"].allowed("activity_type"))
    if set(config.activity_subjects) != activity_types:
        raise ConfigError("activity_subjects must cover call, email, and meeting")


def build_dataset(config: Config, population=None) -> Dataset:
    """Generate one dataset.

    ``population`` replaces the sampler. When it is omitted, a configuration
    that contains ``journeys`` uses the scenario population. Every other
    configuration uses ``baseline_population``.
    """

    contracts = load_contracts()
    _check_vocabulary(config, contracts)
    ensure_window(config)
    world = World(config, contracts)
    if population is not None:
        population(world)
    elif config.journeys is not None:
        scenario_population(world)
    else:
        baseline_population(world)
    dataset = Dataset(
        seed=config.seed,
        config_file=config.config_file,
        start_date=config.start_date,
        end_date=config.end_date,
        delivery_id=config.delivery_id,
        rows={contract_id: list(world.rows.get(contract_id, [])) for contract_id in contracts},
    )
    validate_dataset(dataset, contracts)
    return dataset
