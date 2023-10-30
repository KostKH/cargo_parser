import abc
import logging
from itertools import chain
from typing import Literal
from uuid import UUID

from config import RESULTS_DB_NAME
from domain import models
from domain.cities import AbstractCityParser, CityParser
from domain.parsing import AbstractCargoParser, CargoParserWithToken
from repository.cities import AbstractCityRepository, CityJsonRepository
from repository.routes import AbstractRouteRepository, ExcelRouteRepository

from .dictionaries import additional_services, packages


class AbstractCargoInterFace(abc.ABC):
    """Абстрактный класс интерфейса для запуска парсинга."""

    def run_parsing(self):
        """Метод для запуска парсинга."""
        self._run_parsing()

    @abc.abstractclassmethod
    def _run_parsing(self):
        """Абстрактный метод для запуска парсинга."""
        raise NotImplementedError


class MainTokenCargoInterFace(AbstractCargoInterFace):
    """Интерфейс для запуска парсинга. Этот интерфейс для получения
    данных с сайта использует токен."""

    def __init__(
        self,
        routes_to_parse: list[tuple],
        token: str,
        payer: Literal['sender', 'reciever'] = 'sender',
        mode: str = 'HOME-HOME',
        currency_mark: str = 'RUB',
        packages: dict = packages,
        cargo_type_descr: str = 'Экспресс-доставка ко времени',
        tariff_description: str = '16:00',
        additional_services: dict = additional_services,
        route_rep_cls: AbstractRouteRepository = ExcelRouteRepository,
        city_rep_cls: AbstractCityRepository = CityJsonRepository,
        route_parser_cls: AbstractCargoParser = CargoParserWithToken,
        city_parser_cls: AbstractCityParser = CityParser,
    ) -> None:
        self.route_rep_cls = route_rep_cls
        self.city_rep_cls = city_rep_cls
        self.route_parser_cls = route_parser_cls
        self.city_parser_cls = city_parser_cls
        self.routes_to_parse = routes_to_parse
        self.token = token
        self.payer = payer
        self.mode = mode
        self.currency_mark = currency_mark
        self.packages = packages
        self.additional_services = additional_services
        self.cargo_type_descr = cargo_type_descr
        self.tariff_description = tariff_description

        self._cached_cities: dict = {}
        self._cargo_requests: list = []
        self._route_errors: list = []
        self._report: models.RequestsReport | None = None

    def _run_parsing(self):
        """Метод запускает парсинг. Вначле запрашивается с сайта
        список городов, чтобы получить id городов. Затем
        подгатавливаются модели запросов на сайт. После
        этого запускается парсинг, сохраняются результаты,
        выводится отчет о парсинге."""
        self._get_city_dicts()
        self._prepare_cargo_requests()

        cargo_parser = self.route_parser_cls(token=self.token)
        results, self._report = cargo_parser.retrieve_data(
            self._cargo_requests)

        results_repository = self.route_rep_cls(
            weight_list=list(self.packages.keys()),
            mode=(f'{self.cargo_type_descr}, {self.mode}, '
                  f'{self.tariff_description}'),
            routes_to_parse=self.routes_to_parse
        )
        results_repository.add_all(results)

        self._print_statistics()

    def _get_city_dicts(self):
        """Метод запрашивает с сайта список нужных городов, чтобы
        получить их id. Запрашиваются с сайта только те города,
        которые не были найдены в БД городов."""
        city_rep = self.city_rep_cls()
        self._cached_cities = city_rep.get_all()
        unique_cities = list(set(chain(*self.routes_to_parse)))
        city_parser = self.city_parser_cls(self._cached_cities)
        city_parser.get_cities_info(unique_cities)
        city_rep.save(self._cached_cities)

    def _prepare_cargo_requests(self):
        """Метод готовит список моделей запросов на парсинг."""
        for sender_city, receiver_city in self.routes_to_parse:
            try:
                sender_uuid = UUID(
                    self._cached_cities[sender_city]['city_uid'])
                receiver_uuid = UUID(
                    self._cached_cities[receiver_city]['city_uid'])
                for key, package in self.packages.items():
                    add_service = self.additional_services[key]
                    request = models.RequestForCargo(
                        sender_city_id=sender_uuid,
                        sender_city_name=sender_city,
                        receiver_city_id=receiver_uuid,
                        receiver_city_name=receiver_city,
                        mode=self.mode,
                        packages=[package],
                        additional_services=add_service,
                        currency_mark=self.currency_mark,
                        payer_type=self.payer,
                        cargo_type_descr=self.cargo_type_descr,
                        tariff_description=self.tariff_description
                    )
                    self._cargo_requests.append(request)
            except Exception as e:
                logging.exception(
                    'Маршрут не добавлен в очередь парсинга:'
                    f'({sender_city}, {receiver_city}): {e}'
                )
                self._route_errors.append((sender_city, receiver_city))

    def _print_statistics(self):
        """Метод выводит на экран сводный отчет по результатам парсинга."""
        separator = '\n' + '-' * 20 + '\n'
        input_routes_count = len(self.routes_to_parse)
        routes_sent_to_parse = (len(self.routes_to_parse)
                                - len(self._route_errors))

        msg_preparing = (
            'Подготовка данных к парсингу:\n'
            f'Получено направлений на парсинг, шт.: {input_routes_count}\n'
            f'Удалось отправить на парсинг, шт.: {routes_sent_to_parse}\n'
            f'Не обработанные направления, шт.: {len(self._route_errors)}'
        )
        msg_parsing = (
            'Парсинг:\n'
            f'Сформировано запросов всего, шт.: {self._report.routes_total}\n'
            f'Успешно спарсены, шт.: {self._report.routes_success}\n'
            f'Ошибка при выполнении запроса, шт.: {self._report.routes_fail}'
        )
        print('*' * 20)
        print('Итоги парсинга', msg_preparing, msg_parsing, sep=separator)
        print(separator)
        print(f'Результаты парсинга сохранены в файл:\n{RESULTS_DB_NAME}')
        print('*' * 20)
