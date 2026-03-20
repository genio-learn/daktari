import os
from typing import List, Set, Type, Union

from daktari.check import Check
from daktari.collection_utils import flatten


class CyclicCheckException(Exception):
    def __init__(self, message):
        super().__init__(message)


def check_for_cycles(check: Union[Check, Type[Check]], prev_parents: Set[str]):
    if check.name in prev_parents:
        raise CyclicCheckException(f"Check [{check.name}] has cyclic dependencies")
    for sub_check in check.depends_on:
        check_for_cycles(sub_check, prev_parents.union({check.name}))


def get_all_dependent_check_names(check: Union[Check, Type[Check]]) -> Set[str]:
    check_for_cycles(check, set())
    return _get_all_dependent_check_names_recursive(check)


def _get_all_dependent_check_names_recursive(check: Union[Check, Type[Check]]) -> Set[str]:
    sub_dependents = [_get_all_dependent_check_names_recursive(dep) for dep in check.depends_on]
    flat_sub_dependents = flatten(sub_dependents)
    return flat_sub_dependents.union({dep.name for dep in check.depends_on})


def filter_checks_by_name(
    checks: List[Check],
    requested_check_names: Set[str],
    unknown_check_error_prefix: str = "Unknown Daktari check names",
) -> List[Check]:
    available_checks_by_name = {check.name: check for check in checks}

    unknown_check_names = sorted(requested_check_names - set(available_checks_by_name.keys()))
    if len(unknown_check_names) > 0:
        raise ValueError(f"{unknown_check_error_prefix}: {', '.join(unknown_check_names)}")

    required_check_names = set()
    for requested_check_name in requested_check_names:
        requested_check = available_checks_by_name[requested_check_name]
        required_check_names.add(requested_check_name)
        required_check_names.update(get_all_dependent_check_names(requested_check))

    return [check for check in checks if check.name in required_check_names]


def filter_out_checks_by_name(checks: List[Check], ignored_check_names: Set[str]) -> List[Check]:
    checks_to_ignore = [
        check
        for check in checks
        if check.name in ignored_check_names
        or len(get_all_dependent_check_names(check).intersection(ignored_check_names)) > 0
    ]
    return [check for check in checks if check not in checks_to_ignore]


def filter_checks_by_env_var(checks: List[Check], env_var_name: str = "DAKTARI_ONLY_CHECKS") -> List[Check]:
    only_checks_csv = os.getenv(env_var_name, "").strip()
    if only_checks_csv == "":
        return checks

    requested_check_names = {check_name.strip() for check_name in only_checks_csv.split(",") if check_name.strip()}
    return filter_checks_by_name(
        checks,
        requested_check_names,
        unknown_check_error_prefix=f"Unknown Daktari check names in {env_var_name}",
    )
