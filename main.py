import argparse
import csv
import logging
import sys

import config
from interface.interface import MainTokenCargoInterFace


def parse_arguments():
    """Функция задает возможные аргументы для запуска скрипта
       и парсит входящие агрументы, переданные из командной строки"""
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group()
    parser.add_argument(
        '--routes',
        help='Укажите путь до csv-файла со списком маршрутов для парсинга.'
    )
    parser.add_argument(
        '--params',
        help='Укажите путь до csv-файла с параметрами.'
    )
    group.add_argument(
        '--token-mode',
        help=('Режип подключения к сайту через токен.'
              'Укажите путь до файла с токеном')
    )

    arguments = parser.parse_args()
    return parser, arguments


def get_routes_from_file(filename):
    """Функция для получения списка маршрутов из csv-файла."""
    results = []
    file_path = config.INPUT_DATA_DIR / filename
    with open(file_path, 'r', newline='', encoding='utf-8') as csv_file:
        csv_reader = csv.DictReader(csv_file)
        for row in csv_reader:
            results.append((row['city_from'], row['city_to']))
    return results


def get_params_from_file(filename):
    """Функция для получения словаря с параметрами из csv-файла."""
    results = []
    file_path = config.INPUT_DATA_DIR / filename
    with open(file_path, 'r', newline='', encoding='utf-8') as csv_file:
        csv_reader = csv.DictReader(csv_file)
        for row in csv_reader:
            results.append(row)
        print(results)
        return results[0]


def start_token_mode(arguments, **kwargs):
    """Функция обрабатывает аргументы, переданные в командную строку,
    и запускает интерфейс парсинга, работающий через токен."""

    logging.info('Режим: "--token-mode"')
    token_file = config.INPUT_DATA_DIR / arguments.token_mode
    with open(token_file, 'r') as file:
        token = file.read().rstrip()
    routes_data = get_routes_from_file(arguments.routes)
    params = get_params_from_file(arguments.params)

    app = MainTokenCargoInterFace(
        routes_to_parse=routes_data,
        token=token,
        mode=params['mode'],
        cargo_type_descr=params['cargo_type_descr'],
        tariff_description=params['tariff_description'],
    )
    app.run_parsing()


def main():
    """Функция вызывается при запуске приложения из командной строки.
    В зависимости от переданных аргументов, инициирует запуск подходящего
    интерфейса. (Пока есть только один интерфейс парсера, он использует
    токен для доступа к данным сайта)."""
    logging.basicConfig(
        level=logging.ERROR,
        stream=sys.stdout,
        format='%(asctime)s - %(levelname)s - %(message)s',
    )
    logging.info('Запущен скрипт')

    parser, arguments = parse_arguments()
    kwargs = {
        'arguments': arguments,
    }
    regimes = {
        'token_mode': start_token_mode,
    }
    for action in regimes.keys():
        if getattr(arguments, action):
            regimes[action](**kwargs)
            break
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
