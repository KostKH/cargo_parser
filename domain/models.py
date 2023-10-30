from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field
from pydantic.functional_serializers import PlainSerializer
from typing_extensions import Annotated

CustomUid = Annotated[
    UUID,
    PlainSerializer(lambda uid: str(uid), return_type=str),
]


class ServiceArgument(BaseModel):
    """Модель аргументов для дополнительного сервиса."""

    name: str
    value: int


class RequestForService(BaseModel):
    """Модель дополнительного сервиса для перевозки"""

    alias: str
    arguments: list[ServiceArgument]


class Package(BaseModel):
    """Модель габаритов посулки / груза."""

    model_config = ConfigDict(frozen=True)
    height: int | float
    length: int | float
    width: int | float
    weight: int | float


class RequestForCargo(BaseModel):
    """Модель запроса на перевозку. На основе этой модели создается
    тело post-запроса для отравки на api сайта."""
    without_add_services: int = Field(
        serialization_alias='withoutAdditionalServices',
        default=0)
    service_id: CustomUid | None = Field(
        serialization_alias='serviceId',
        default=None)
    mode: str = 'HOME-HOME'
    payer_type: str = Field(
        serialization_alias='payerType',
        default='sender')
    currency_mark: str = Field(
        serialization_alias='currencyMark',
        default='RUB')
    sender_city_id: CustomUid = Field(serialization_alias='senderCityId')
    sender_city_name: str = Field(exclude=True)
    receiver_city_id: CustomUid = Field(serialization_alias='receiverCityId')
    receiver_city_name: str = Field(exclude=True)
    packages: list[Package]
    additional_services: list[RequestForService | None] = Field(
        serialization_alias='additionalServices',
        default=[])
    duration_min: int | float | None = Field(exclude=True, default=None)
    duration_max: int | float | None = Field(exclude=True, default=None)
    cargo_type_descr: str = Field(exclude=True)
    tariff_description: str = Field(exclude=True, default='')


class RequestForServiceId(BaseModel):
    """Модель запроса вариантов перевозок по маршруту.
    На основе этой модели создается тело post-запроса
    для отравки на api сайта."""
    model_config = ConfigDict(frozen=True)
    payer_type: str = Field(
        serialization_alias='payerType',
        default='sender')
    currency_mark: str = Field(
        serialization_alias='currencyMark',
        default='RUB')
    sender_city_id: CustomUid = Field(serialization_alias='senderCityId')
    receiver_city_id: CustomUid = Field(serialization_alias='receiverCityId')
    packages: tuple[Package]


class CalculatedService(BaseModel):
    """Модель для хранения данных сервисов, включенных в стоимость перевозки.
    Модель используется для обработки ответа от сайта."""
    alias: str
    original_name: str
    total_cost: int | float = 0


class Route(BaseModel):
    """Модель для хранения данных о стоимости перевозки
    (и других данных о ней). Модель используется для обработки
    ответа от сайта и для сохранения результатов парсинга в
    репозиторий."""
    city_from: str
    city_to: str
    delivery_price: int | float
    total_cost: int | float
    request: RequestForCargo | None = None
    services: list[CalculatedService | None] = []
    duration_min: int | float
    duration_max: int | float
    weight: int | float


class City(BaseModel):
    """Модель города."""
    model_config = ConfigDict(frozen=True)
    city_uid: CustomUid
    name: str
    full_name: str


class CitiesReport(BaseModel):
    """Модель отчета о результатах парсинга городов."""
    cities_total: int = 0
    cities_success: int = 0
    cities_fail: int = 0
    routes_fail_list: list[str | None] = []


class RequestsReport(BaseModel):
    """Модель отчета о результатах парсинга перевозок."""
    routes_total: int = 0
    routes_success: int = 0
    routes_fail: int = 0
    routes_fail_list: list[RequestForCargo | None] = []
