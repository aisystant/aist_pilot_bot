#!/usr/bin/env python3
"""
Основной скрипт проверки соответствия кода документации.

Поддерживает проверку:
- scenarios: соответствие сценариям
- processes: соответствие процессам
- data: соответствие данным
- states: соответствие State Machine

Использование:
    python -m tests.test_repo.scripts.checker --type scenarios
    python -m tests.test_repo.scripts.checker --type all

    # или напрямую
    python tests/test-repo/scripts/checker.py --type states

Опции:
    --type, -t      Тип проверки: scenarios, processes, data, states, all
    --output, -o    Путь для сохранения отчёта
    --verbose, -v   Подробный вывод
    --json          Вывод в JSON формате
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

import yaml

from .code_analyzer import CodeAnalyzer
from .report_generator import ReportGenerator, ClassResult, ScenarioResult


# Маппинг типов проверок на файлы требований
REQUIREMENTS_FILES = {
    'scenarios': 'requirements-scenarios.yaml',
    'processes': 'requirements-processes.yaml',
    'data': 'requirements-data.yaml',
    'states': 'requirements-states.yaml',
}

# Названия для отчётов
REPORT_NAMES = {
    'scenarios': 'тест-сценариев',
    'processes': 'тест-процессов',
    'data': 'тест-данных',
    'states': 'тест-стейтов',
}


def load_requirements(requirements_path: Path) -> dict:
    """Загружает ТЗ из YAML файла."""
    with open(requirements_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def run_checks(project_root: Path, requirements: dict, verbose: bool = False) -> list[ClassResult]:
    """Выполняет все проверки и возвращает результаты."""
    analyzer = CodeAnalyzer(project_root)
    results = []

    # Ключи для пропуска (метаданные)
    skip_keys = {'version', 'source', 'weights', 'thresholds'}

    # Проходим по всем секциям
    for key, value in requirements.items():
        if key in skip_keys:
            continue
        if not isinstance(value, dict):
            continue

        # Поддерживаем оба формата: class_* (сценарии) и другие (стейты, данные)
        class_id = key
        class_name = value.get('name', key)
        priority = value.get('priority', 'normal')

        # Получаем проверки: scenarios (старый формат) или checks (новый формат)
        scenarios_data = value.get('scenarios', [])
        checks_data = value.get('checks', [])

        if verbose:
            print(f"\n📋 Секция: {class_name}")

        scenario_results = []

        # Старый формат: scenarios с вложенными checks
        if scenarios_data:
            for scenario_data in scenarios_data:
                scenario_id = scenario_data.get('id', '?')
                scenario_name = scenario_data.get('name', 'Без названия')
                scenario_priority = scenario_data.get('priority', 'normal')
                scenario_checks = scenario_data.get('checks', [])

                if verbose:
                    print(f"  └─ {scenario_id} {scenario_name}", end='')

                check_results = []
                for check in scenario_checks:
                    result = analyzer.run_check(check)
                    check_results.append(result)

                scenario_result = ScenarioResult(
                    id=scenario_id,
                    name=scenario_name,
                    priority=scenario_priority,
                    checks=check_results
                )
                scenario_results.append(scenario_result)

                if verbose:
                    status = "✅" if scenario_result.passed else "❌"
                    print(f" {status} ({scenario_result.passed_count}/{scenario_result.total_count})")

        # Новый формат: checks напрямую в секции
        elif checks_data:
            check_results = []
            for check in checks_data:
                result = analyzer.run_check(check)
                check_results.append(result)

                if verbose:
                    status = "✅" if result.passed else "❌"
                    print(f"  └─ {result.description} {status}")

            # Создаём один "сценарий" из всех проверок секции
            scenario_result = ScenarioResult(
                id=class_id,
                name=class_name,
                priority=priority,
                checks=check_results
            )
            scenario_results.append(scenario_result)

        if scenario_results:
            class_result = ClassResult(
                id=class_id,
                name=class_name,
                scenarios=scenario_results
            )
            results.append(class_result)

    return results


def run_single_check(check_type: str, project_root: Path, test_repo_dir: Path,
                     reports_dir: Path, args) -> tuple[list[ClassResult], Path, dict]:
    """Выполняет одну проверку и возвращает результаты."""
    requirements_file = REQUIREMENTS_FILES[check_type]
    requirements_path = test_repo_dir / requirements_file

    if not requirements_path.exists():
        if args.verbose:
            print(f"⚠️ Файл {requirements_file} не найден, пропуск", file=sys.stderr)
        return [], None, {}

    if args.verbose:
        print(f"\n📄 Загрузка: {requirements_path}")

    requirements = load_requirements(requirements_path)
    results = run_checks(project_root, requirements, verbose=args.verbose)

    # Определяем путь для отчёта
    date_str = datetime.now().strftime('%Y-%m-%d')
    report_name = REPORT_NAMES.get(check_type, check_type)
    output_path = reports_dir / f'{date_str}-{report_name}.md'

    return results, output_path, requirements


def main():
    """Точка входа."""
    parser = argparse.ArgumentParser(
        description='Проверка соответствия кода документации'
    )
    parser.add_argument(
        '--type', '-t',
        type=str,
        default='scenarios',
        choices=['scenarios', 'processes', 'data', 'states', 'all'],
        help='Тип проверки (по умолчанию: scenarios)'
    )
    parser.add_argument(
        '--output', '-o',
        type=str,
        help='Путь для сохранения отчёта'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Подробный вывод'
    )
    parser.add_argument(
        '--json',
        action='store_true',
        help='Вывод в JSON формате'
    )
    parser.add_argument(
        '--project-root',
        type=str,
        help='Корень проекта (по умолчанию определяется автоматически)'
    )

    args = parser.parse_args()

    # Определяем пути
    script_dir = Path(__file__).parent
    test_repo_dir = script_dir.parent

    if args.project_root:
        project_root = Path(args.project_root)
    else:
        project_root = test_repo_dir.parent.parent  # tests/test-repo -> aist_track_bot

    reports_dir = test_repo_dir / 'reports'

    # Определяем типы проверок
    if args.type == 'all':
        check_types = list(REQUIREMENTS_FILES.keys())
    else:
        check_types = [args.type]

    # Выполняем проверки
    all_results = []
    all_json_results = []

    for check_type in check_types:
        results, output_path, requirements = run_single_check(
            check_type, project_root, test_repo_dir, reports_dir, args
        )

        if not results:
            continue

        all_results.extend(results)

        # Генерируем отчёт для каждого типа
        thresholds = requirements.get('thresholds', {'green': 90, 'yellow': 70})
        weights = requirements.get('weights', {'critical': 2, 'normal': 1})

        generator = ReportGenerator(thresholds=thresholds, weights=weights)

        if args.output and args.type != 'all':
            output_path = Path(args.output)

        report = generator.generate_report(
            results,
            output_path,
            project_name=f"AIST Track Bot ({check_type})"
        )

        if args.json:
            # Собираем JSON результаты
            total_scenarios = sum(c.total_scenarios for c in results)
            passed_scenarios = sum(c.passed_scenarios for c in results)
            coverage = (passed_scenarios / total_scenarios * 100) if total_scenarios else 0

            critical_total = sum(c.critical_total for c in results)
            critical_passed = sum(c.critical_passed for c in results)
            critical_coverage = (critical_passed / critical_total * 100) if critical_total else 100

            normal_total = sum(c.normal_total for c in results)
            normal_passed = sum(c.normal_passed for c in results)
            normal_coverage = (normal_passed / normal_total * 100) if normal_total else 100

            def get_status(cov: float, crit_cov: float, norm_cov: float) -> str:
                if crit_cov == 100 and norm_cov == 100:
                    return 'green'
                if crit_cov == 100 and cov >= 60:
                    return 'yellow'
                return 'red'

            status_code = get_status(coverage, critical_coverage, normal_coverage)

            all_json_results.append({
                'type': check_type,
                'date': datetime.now().isoformat(),
                'coverage': round(coverage, 1),
                'critical_coverage': round(critical_coverage, 1),
                'normal_coverage': round(normal_coverage, 1),
                'passed': passed_scenarios,
                'total': total_scenarios,
                'status': status_code,
                'report_path': str(output_path) if output_path else None
            })

    # Используем общие результаты для вывода
    results = all_results

    # Вычисляем итоговое покрытие по всем результатам
    total_scenarios = sum(c.total_scenarios for c in results)
    passed_scenarios = sum(c.passed_scenarios for c in results)
    coverage = (passed_scenarios / total_scenarios * 100) if total_scenarios else 0

    # Основные сценарии (critical)
    critical_total = sum(c.critical_total for c in results)
    critical_passed = sum(c.critical_passed for c in results)
    critical_coverage = (critical_passed / critical_total * 100) if critical_total else 100

    # Вспомогательные сценарии (normal)
    normal_total = sum(c.normal_total for c in results)
    normal_passed = sum(c.normal_passed for c in results)
    normal_coverage = (normal_passed / normal_total * 100) if normal_total else 100

    # Логика цветов:
    # 🟢 Зелёный: основные = 100% И вспомогательные = 100%
    # 🟡 Жёлтый: основные = 100% И общее ≥ 60%
    # 🔴 Красный: основные < 100% ИЛИ общее < 50%
    def get_status(cov: float, crit_cov: float, norm_cov: float) -> str:
        if crit_cov == 100 and norm_cov == 100:
            return 'green'
        if crit_cov == 100 and cov >= 60:
            return 'yellow'
        return 'red'

    status_code = get_status(coverage, critical_coverage, normal_coverage)

    if args.json:
        # JSON вывод
        if args.type == 'all':
            # Сводный результат по всем типам
            json_result = {
                'date': datetime.now().isoformat(),
                'type': 'all',
                'coverage': round(coverage, 1),
                'status': status_code,
                'checks': all_json_results
            }
        else:
            # Результат по одному типу
            json_result = all_json_results[0] if all_json_results else {
                'date': datetime.now().isoformat(),
                'type': args.type,
                'coverage': 0,
                'status': 'red',
                'error': 'No results'
            }
        print(json.dumps(json_result, ensure_ascii=False, indent=2))
    else:
        # Текстовый вывод
        emoji_map = {'green': '🟢', 'yellow': '🟡', 'red': '🔴'}
        status = emoji_map[status_code]

        if args.type == 'all':
            print(f"\n{'='*50}")
            print(f"📊 СВОДНЫЙ ОТЧЁТ ПО ВСЕМ ПРОВЕРКАМ")
            print(f"{'='*50}")
            for check_result in all_json_results:
                check_status = emoji_map[check_result['status']]
                print(f"{check_status} {check_result['type']}: {check_result['coverage']:.1f}%")
            print(f"{'='*50}")

        print(f"\n{status} Общее покрытие: {coverage:.1f}% ({passed_scenarios}/{total_scenarios})")
        print(f"   Критичные: {critical_coverage:.1f}% ({critical_passed}/{critical_total})")
        print(f"   Обычные: {normal_coverage:.1f}% ({normal_passed}/{normal_total})")

    # Возвращаем код выхода: 0 если зелёный или жёлтый
    if status_code in ('green', 'yellow'):
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == '__main__':
    main()
