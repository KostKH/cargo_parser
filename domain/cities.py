import abc
import asyncio
import logging

import aiohttp

import config
from domain import models


class AbstractCityParser(abc.ABC):
    """Абстрактный парсер списка городов."""

    def get_cities_info(
        self,
        cities: list[str]
    ) -> tuple[dict[str: dict], models.CitiesReport]:
        """Метод для парсинга данных о городах."""
        return self._get_cities_info(cities)

    @abc.abstractmethod
    def _get_cities_info(
        self,
        cities: list[str]
    ) -> dict[str: dict]:
        """Абстрактный метод для парсинга данных о городах."""
        raise NotImplementedError


class CityParser(AbstractCityParser):
    """Парсер списка городов."""

    def __init__(
        self,
        cached_cities: dict[str: dict],
        thread_limit: int = 10,
    ) -> None:
        self._cached_cities = cached_cities
        self._city_url = config.CARGO_CITY_URL
        self._results = {}
        self._cities_total = 0
        self._cities_success = 0
        self._cities_fail = 0
        self._cities_fail_list = []
        self._queue = None
        self._thread_limit = thread_limit

    def _get_cities_info(
        self,
        cities: list[str]
    ) -> dict[str: dict]:
        """Метод для парсинга данных о городах."""
        self._results = {}
        asyncio.run(self._run_city_parsing(cities))
        report = models.CitiesReport(
            routes_total=len(cities),
            routes_success=self._cities_success,
            routes_fail=self._cities_fail,
            routes_fail_list=self._cities_fail_list
        )
        return (self._results, report)

    async def _parse_city(self, city_name):
        """Метод соединяется с сайтом и получат данные о городах."""
        async with aiohttp.ClientSession() as session:
            async with session.get(self._city_url.format(city_name)) as resp:
                return await resp.json()

    async def _run_city_parsing(self, cities: list[str]):
        """Метод формирует очередь городов на парсинг и запускает
        асинхронный парсинг в нескольких потоках."""
        self._queue = asyncio.Queue()
        for city_name in cities:
            self._queue.put_nowait(city_name)
        tasks = []
        for idx in range(min(len(cities), self._thread_limit)):
            task = asyncio.create_task(self._worker(f'worker-{idx}'))
            tasks.append(task)
        await self._queue.join()
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)

    async def _worker(self, worker_name: str):
        """Воркер - принимает город из очереди, проверяет, нет ли
        города в базе. Если нет - инициирует соединение с сайтом."""
        while True:
            if self._queue.qsize() <= 0:
                await asyncio.sleep(0.1)
                continue
            city_name = await self._queue.get()
            if self._cached_cities.get(city_name):
                self._results[city_name] = self._cached_cities.get(city_name)
                self._cities_success += 1
                self._queue.task_done()
                continue
            try:
                city_data = await self._parse_city(city_name)
                city_dict = self._extract_city_dict(city_data, city_name)
                self._results[city_name] = city_dict
                self._cached_cities[city_name] = city_dict
                self._cities_success += 1

            except Exception as e:
                logging.exception('Не удалось спарсить город '
                                  f'({city_name}): {e}')
                self._cities_fail += 1
                self._cities_fail_list.append(city_name)
            self._queue.task_done()

    def _extract_city_dict(
        self,
        city_data: dict,
        city_name: str,
    ) -> dict:
        """Метод обрабатывет данные,полученные с сайта. Метод
        формирует словарь с нужными данными о городе и возвращает его."""
        raw_city_list = city_data.get('data')
        if not raw_city_list:
            raise Exception(f'Ошибка при парсинге: {city_data}')
        city_dict = {}
        for item in raw_city_list:
            if not item.get('name') == city_name:
                continue
            city_dict['name'] = city_name
            city_dict['city_uid'] = item.get('uuid')
            city_dict['full_name'] = item.get('fullName')
        return city_dict
