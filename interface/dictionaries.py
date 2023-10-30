
from domain.models import Package, RequestForService, ServiceArgument

packages = {
    0.5: Package(
        height=9,
        length=17,
        width=12,
        weight=0.5,
    ),
    2: Package(
        height=10,
        length=23,
        width=19,
        weight=2,
    ),
    3: Package(
        height=15,
        length=33,
        width=25,
        weight=3,
    ),
    4: Package(
        height=15,
        length=33,
        width=25,
        weight=4,
    ),
    5: Package(
        height=15,
        length=33,
        width=25,
        weight=5,
    ),
    20: Package(
        height=30,
        length=60,
        width=60,
        weight=20,
    ),
}

insurance_service = RequestForService(
    alias='insurance',
    arguments=[ServiceArgument(name='insurance_declaredCost', value=999)]
)

additional_services = {
    0.5: [
        insurance_service,
        RequestForService(
            alias='cartonBox2',
            arguments=[ServiceArgument(name='cartonBox2_count', value=1)]),
    ],
    2: [
        insurance_service,
        RequestForService(
            alias='cartonBox2',
            arguments=[ServiceArgument(name='cartonBox2_count', value=1)]),
    ],
    3: [
        insurance_service,
        RequestForService(
            alias='cartonBox5',
            arguments=[ServiceArgument(name='cartonBox5_count', value=1)]),
    ],
    4: [
        insurance_service,
        RequestForService(
            alias='cartonBox5',
            arguments=[ServiceArgument(name='cartonBox5_count', value=1)]),
    ],
    5: [
        insurance_service,
        RequestForService(
            alias='cartonBox5',
            arguments=[ServiceArgument(name='cartonBox5_count', value=1)]),
    ],
    20: [
        insurance_service,
        RequestForService(
            alias='cartonBox5',
            arguments=[ServiceArgument(name='cartonBox5_count', value=4)]),
    ],
}

additional_services_off = {
    0.5: [],
    2: [],
    3: [],
    4: [],
    5: [],
    20: [],
}
