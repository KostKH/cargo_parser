import abc
import asyncio
import logging
from uuid import UUID

import aiohttp

import config
from domain import models


class AbstractCargoParser(abc.ABC):
    """Абстрактный парсер условий грузоперевозок. Задает фреймворк
    и основные методы для запуска парсинга. Конкретные реализации
    парсера должны наследоваться от этого класса."""

    def retrieve_data(
        self,
        cargo_requests: list[models.RequestForCargo]
    ) -> tuple[list[models.Route], models.RequestsReport]:
        """Метод для парсинга условий грузоперевозок."""
        return self._retrieve_data(cargo_requests)

    @abc.abstractmethod
    def _retrieve_data(
        self,
        cargo_requests: list[models.RequestForCargo]
    ) -> tuple[list[models.Route], models.RequestsReport]:
        """Метод для парсинга условий грузоперевозок."""
        raise NotImplementedError


class CargoParserWithToken(AbstractCargoParser):
    """Парсер маршрутов, получающий данные с сайта с помощью токена."""

    def __init__(
        self,
        token: str,
        thread_limit: int = 10,
        cargo_url: str = config.CARGO_PARSER_URL,
        service_id_url: str = config.SERVICE_ID_URL,
        default_headers: dict = config.DEFAULT_HEADERS,
    ) -> None:
        super().__init__()
        self._cargo_url = cargo_url
        self._service_id_url = service_id_url
        self._thread_limit = thread_limit
        self._token = token
        self._default_headers = default_headers
        self._auth_headers = default_headers.copy()
        self._auth_headers['Authorization'] = 'Bearer ' + token
        self._routes_total = 0
        self._routes_success = 0
        self._routes_fail = 0
        self._routes_fail_list = []
        self._result_list = []
        self._queue = None

    def _retrieve_data(
        self,
        cargo_requests: list[models.RequestForCargo]
    ) -> tuple[list[models.Route], models.RequestsReport]:
        """Метод для парсинга условий грузоперевозок."""
        asyncio.run(self._run_cargo_parsing(cargo_requests))
        report = models.RequestsReport(
            routes_total=len(cargo_requests),
            routes_success=self._routes_success,
            routes_fail=self._routes_fail,
            routes_fail_list=self._routes_fail_list
        )
        return (self._result_list, report)

    async def _parse_cargo(self, body):
        """Метод соединяется с сайтом и получает json со стоимостью
        перевозки."""
        async with aiohttp.ClientSession() as session:
            async with session.post(
                self._cargo_url,
                headers=self._auth_headers,
                json=body
            ) as resp:
                return await resp.json()

    async def _run_cargo_parsing(self, cargo_requests):
        """Метод создает очередь на парсинг, и потом запускает
        парсинг в асинхронном режиме в несколько потоков."""
        self._queue = asyncio.Queue()
        for cargo_request in cargo_requests:
            self._queue.put_nowait(cargo_request)
        tasks = []
        for idx in range(min(len(cargo_requests), self._thread_limit)):
            task = asyncio.create_task(self._worker(f'worker-{idx}'))
            tasks.append(task)
        await self._queue.join()
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)

    async def _worker(self, worker_name: str):
        """Метод для создания воркера, который получает задачи на
        парсинг из очереди и запрашивает нужные данные с сайта."""
        while True:
            if self._queue.qsize() <= 0:
                await asyncio.sleep(0.1)
                continue
            cargo_request = await self._queue.get()

            try:
                data_tuple = await self._parse_service_id(cargo_request)
                service_id, duration_min, duration_max = data_tuple
                cargo_request.service_id = service_id
                cargo_request.duration_min = duration_min
                cargo_request.duration_max = duration_max

                body = cargo_request.model_dump(by_alias=True)
                cargo_data = await self._parse_cargo(body)
                route = self._extract_data_from_resp_dict(
                    cargo_data,
                    cargo_request)
                self._result_list.append(route)
                self._routes_success += 1

            except Exception as e:
                logging.exception('Не удалось спарсить условия маршрута '
                                  f'({cargo_request}): {e}')
                self._routes_fail += 1
                self._routes_fail_list.append(cargo_request)
            self._queue.task_done()

    async def _parse_service_id(self, cargo_request):
        """Метод для парсинга возможных вариантов перевозки
        по маршруту, с тем чтобы по параметрам запроса на парсинг
        отобрать нужный вариант и взять в запрос service_id этого
        варианта. Также, здесь берутся данные о минимальном и
        максимальном сроке перевозки."""
        service_id_request = models.RequestForServiceId(
            payer_type=cargo_request.payer_type,
            currency_mark=cargo_request.currency_mark,
            sender_city_id=cargo_request.sender_city_id,
            receiver_city_id=cargo_request.receiver_city_id,
            packages=tuple(cargo_request.packages),
        )
        async with aiohttp.ClientSession() as session:
            async with session.post(
                self._service_id_url,
                json=service_id_request.model_dump(by_alias=True)
            ) as resp:
                data = await resp.json()
        list_of_services = data.get('data')
        if not list_of_services:
            raise Exception(f'Не удалось спарсить service_id: {data}')
        for outer_list in list_of_services:
            cargo_type_descr = cargo_request.cargo_type_descr
            if outer_list.get('description') != cargo_type_descr:
                continue
            inner_list = outer_list.get('tariffs')
            for item in inner_list:
                condition = bool(
                    item.get('mode') == cargo_request.mode
                    and item.get('shortDescription')
                    == cargo_request.tariff_description
                )
                if condition:
                    service_id = UUID(item.get('serviceId'))
                    duration_min = item.get('durationMin')
                    duration_max = item.get('durationMax')
                    return service_id, duration_min, duration_max
        raise Exception(f'Не найден нужный service_id в даннных: {data}')

    def _extract_data_from_resp_dict(
        self,
        cargo_data: dict,
        cargo_request: models.RequestForCargo
    ) -> models.Route:
        """Метод обрабатывает данные, полученные с сайта, из них
        создает экземпляр перевозки на основе модели."""
        cargo_dict = cargo_data.get('data')
        if not cargo_dict:
            raise Exception(f'Ошибка при парсинге: {cargo_data}')
        calcuated_services = []
        service_list = cargo_dict.get('calculatedAdditionalServices') or []
        for item in service_list:

            calcuated_services.append(
                models.CalculatedService(
                    alias=item.get('alias'),
                    original_name=item.get('original_name'),
                    total_cost=item.get('paymentDetail').get('totalCost'))
            )

        return models.Route(
            city_from=cargo_request.sender_city_name,
            city_to=cargo_request.receiver_city_name,
            delivery_price=cargo_dict.get('deliveryPrice'),
            total_cost=cargo_dict.get('totalCost'),
            request=cargo_request,
            services=calcuated_services,
            duration_min=cargo_request.duration_min,
            duration_max=cargo_request.duration_max,
            weight=cargo_request.packages[0].weight
        )
