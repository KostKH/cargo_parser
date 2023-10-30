import abc
import json

import config


class AbstractCityRepository(abc.ABC):
    """Абстрактный репозиторий городов."""

    def save(self, cities: dict[str:dict]) -> None:
        """Метод для добавления словаря с городами в репозиторий."""
        self._save(cities)

    @abc.abstractmethod
    def _save(self, cities: dict[str:dict]) -> None:
        """Абстрактный метод добавления словаря с городами в репозиторий."""
        raise NotImplementedError

    def get_all(self) -> dict[str:dict]:
        """Метод для получения словаря с городами из репозитория."""
        return self._get_all()

    @abc.abstractmethod
    def _get_all(self) -> dict[str:dict]:
        """Абстрактный метод для получения словаря
        с городами из репозитория."""
        raise NotImplementedError


class CityJsonRepository(AbstractCityRepository):
    """Класс реализует хранение словаря с городами
    в json-файле."""

    def __init__(self) -> None:
        super().__init__()
        self._db = config.CITY_DB_NAME
        self._db.touch()

    def _save(self, cities: dict) -> None:
        """Абстрактный метод добавления словаря с городами в репозиторий.
        Сохраняет словарь в json-файл."""
        self._db.write_text(json.dumps(cities))

    def _get_all(self) -> dict[str:dict]:
        """Метод для получения словаря с городами из json-файла."""
        data = self._db.read_text()
        if not data:
            return {}
        return json.loads(data)
