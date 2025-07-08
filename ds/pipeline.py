from config import load_configs_from_yaml
from factory import IndicatorsFactory, TargetsFactory

config_path = "features_sets/config_v_1.yaml"
START_DATE = "2024-01-01"
END_DATE = "2024-01-02"
DATA_DIR = "data"

config = load_configs_from_yaml(config_path)

trading_pair = config.trading_pair
name = config.name

features_config = config.features_config
targets_config = config.targets_config

indicators_factory = IndicatorsFactory(
    name, trading_pair, features_config, START_DATE, END_DATE, DATA_DIR
)
indicators_factory.build_and_save_indicators()

targets_factory = TargetsFactory(
    name, trading_pair, targets_config, START_DATE, END_DATE, DATA_DIR
)
targets_factory.build_and_save_targets()
