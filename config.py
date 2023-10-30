from pathlib import Path

CARGO_PARSER_URL = 'https://www.cdek.ru/api-lkfl/getTariffInfo'
CARGO_CITY_URL = ('https://www.cdek.ru/api-lkfl/cities/autocomplete?'
                  'str={}&page=1&perPage=10')
SERVICE_ID_URL = 'https://www.cdek.ru/api-lkfl/estimateV2'
DEFAULT_HEADERS = {}

CITY_BASE_DIR = Path(__file__).parent / 'data_input'
CITY_BASE_DIR.mkdir(exist_ok=True)
CITY_DB_NAME = CITY_BASE_DIR / 'cities.json'

INPUT_DATA_DIR = Path(__file__).parent / 'data_input'
INPUT_DATA_DIR.mkdir(exist_ok=True)

RESULTS_DIR = Path(__file__).parent / 'data_output'
RESULTS_DIR.mkdir(exist_ok=True)
RESULTS_DB_NAME = RESULTS_DIR / 'prices_cdek.xlsx'
