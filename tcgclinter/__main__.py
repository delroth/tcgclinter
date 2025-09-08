"""
tcgclinter: checks JSON card files for tcgcollector.com for common errors.

SPDX-License-Identifier: EUPL-1.2
SPDX-FileCopyrightText: 2025 Pierre Bourdon <delroth@gmail.com>
"""

import argparse
import dataclasses
import datetime
import functools
import json
import os
import os.path
import pathlib
import sys


def single_card_check(func):
    single_card_check.all.append(func)
single_card_check.all = []

def set_consistency_check(func):
    set_consistency_check.all.append(func)
set_consistency_check.all = []


@functools.total_ordering
@dataclasses.dataclass(frozen=True)
class Card:
    path: pathlib.Path
    data: dict

    def __str__(self):
        if self.data is None:
            return str(self.path)
        name = self.data.get("name", "<!Unnamed Card!>")
        if "number" in self.data:
            name += f" {self.data['number']}"
        if "expansion" in self.data and isinstance(self.data["expansion"], dict):
            xp = self.data["expansion"]
            if "tcgRegion" in xp and "name" in xp:
                name += f" ({xp['tcgRegion']} / {xp['name']})"
        return name

    def __repr__(self):
        return f"<Card: {self.path}>"

    def __hash__(self):
        return hash(self.path)
    def __eq__(self, other):
        return self.path == other.path
    def __lt__(self, other):
        return self.path < other.path


@functools.total_ordering
@dataclasses.dataclass()
class CardSet:
    info: dict
    cards: set

    def __str__(self):
        components = (self.info.get("tcgRegion", "!NOREGION!"),
                      self.info.get("series", "!NOSERIES!"),
                      self.info.get("name", "!NONAME"))
        name = " > ".join(components)
        if "id" in self.info:
            name += f" ({self.info['id']})"
        return name

    @staticmethod
    def key_from_info(info):
        if "id" in info:
            return (info["id"],)
        else:
            key = (info.get("tcgRegion", ""),
                   info.get("series", ""),
                   info.get("name", ""))
            return key

    @property
    def key(self):
        return CardSet.key_from_info(self.info)

    def __hash__(self):
        return hash(self.key)
    def __eq__(self, other):
        return self.key == other.key
    def __lt__(self, other):
        return self.key < other.key


@dataclasses.dataclass(frozen=True)
class Finding:
    context: str
    message: str


class Linter:
    def __init__(self, *, verbose):
        self.verbose = verbose

        self.errors = []
        self.warnings = []

    def process(self, sources, *, recursive):
        sources = self._collect_sources(sources, recursive)
        self._log(f"Processing {len(sources)} source card files.")

        cards = self._load_sources(sources)
        sets = self._partition_sets(cards)

        for card_set in sorted(sets):
            self._log(f"Checking set {card_set}")
            for card in sorted(card_set.cards):
                self._log(f"| Checking card {card}")
                for check in single_card_check.all:
                    check(self, card)
            self._log(f"| Checking set consistency")
            for check in set_consistency_check.all:
                check(self, card_set)

    def summarize(self):
        self._log("\nSummary")
        for warning in self.warnings:
            self._print_warning(warning)
        for err in self.errors:
            self._print_error(err)

        if len(self.errors + self.warnings) > 0:
            print()

        print(f"Found {len(self.errors)} errors and {len(self.warnings)} warnings.")

    def _log(self, message):
        if self.verbose:
            print(message)

    def _warn(self, context, message):
        finding = Finding(context=str(context), message=message)
        if self.verbose:
            self._print_warning(finding)
        self.warnings.append(finding)

    def _err(self, context, message):
        finding = Finding(context=str(context), message=message)
        if self.verbose:
            self._print_error(finding)
        self.errors.append(finding)

    def _print_warning(self, finding):
        print(f"Warning: ({finding.context}) {finding.message}")

    def _print_error(self, finding):
        print(f"Error:   ({finding.context}) {finding.message}")

    def _collect_sources(self, sources, recursive):
        collected = set()
        for source in sources:
            if source.is_file() and source.suffix == ".json":
                collected.add(source)
            elif source.is_dir() and recursive:
                for sub in source.glob("**/*.json"):
                    if sub.is_file():
                        collected.add(sub)
            else:
                self._log(f"Skipping {source} ({recursive=})")
        return collected

    def _load_sources(self, sources):
        loaded = set()
        for path in sources:
            with path.open() as fp:
                try:
                    # To avoid issues with putting lists in sets. Could
                    # probably go away once JSON schema checks are implemented,
                    # in the meantime this prevents having to type check in
                    # tons of extra places.
                    def _list_children_to_tuple(obj):
                        for k in obj:
                            if isinstance(obj[k], list):
                                obj[k] = tuple(obj[k])
                        return obj

                    data = json.load(fp, object_hook=_list_children_to_tuple)
                except ValueError as e:
                    self._err(Card(path=path, data=None),
                              f"invalid JSON file: {e}")
                    continue
                loaded.add(Card(path=path, data=data))
        return loaded

    def _partition_sets(self, cards):
        sets = {}
        for card in cards:
            if "expansion" not in card.data:
                self._err(card, f"no expansion/set info provided")
                continue
            key = CardSet.key_from_info(card.data["expansion"])
            card_set = sets.setdefault(key,
                                       CardSet(info=card.data["expansion"],
                                               cards=set()))
            card_set.cards.add(card)
        return sets.values()

    @single_card_check
    def _check_card_standard_attributes(self, card):
        if card.data.get("name") is None:
            self._err(card, "card has no name")
        if card.data.get("numberSortingOrder") is None:
            self._err(card, "card has no numberSortingOrder")
        if not card.data.get("variants", []):
            self._err(card, "card has no variants")
        if card.data.get("supertype") is None:
            self._err(card, "card has no supertype")
        if not card.data.get("types", []):
            self._err(card, "card has no types")
        if card.data.get("format") is None:
            self._err(card, "card has no format")

    @single_card_check
    def _check_card_number_against_sort_order(self, card):
        number = card.data.get("number")
        if not number:
            return

        sorting_order = card.data.get("numberSortingOrder")
        if not sorting_order:
            return

        if int(number.split("/")[0]) != sorting_order:
            self._warn(card, f"number {number} does not match sorting order {sorting_order}")

    @single_card_check
    def _check_pokemon_name_vs_card_type(self, card):
        name = card.data.get("name", "")
        types = card.data.get("types", [])

        if name.endswith(" ex") and "Pokémon ex" not in types:
            self._warn(card, f"card should maybe have 'Pokémon ex' type (current: {types})")

    @single_card_check
    def _check_card_rule_vs_card_type(self, card):
        has_rule = len(card.data.get("rules", [])) > 0
        rule_types = ("Pokémon ex", "Supporter", "Stadium")
        for t in rule_types:
            if t in card.data.get("types", []) and not has_rule:
                self._warn(card, f"{t} typed card has no rule text defined")

    @single_card_check
    def _check_card_number_against_right_part(self, card):
        right_part = card.data.get("expansion", {}).get("cardNumberRightPart")
        if not right_part:
            return

        number = card.data.get("number")
        if not number:
            self._err(card, "card in numbered set has no number")
            return

        if not number.endswith(f"/{right_part}"):
            self._err(card, f"card number {number} does not end with /{right_part}")

    @single_card_check
    def _check_pokemon_card_standard_attributes(self, card):
        if card.data.get("supertype") != "Pokémon":
            return

        if card.data.get("pokemonStage") is None:
            self._err(card, "Pokémon card has no pokemonStage")
        if card.data.get("hitPoints") is None:
            self._err(card, "Pokémon card has no hitPoints")
        if not card.data.get("energyTypes"):
            self._err(card, "Pokémon card has no energyTypes")
        if not card.data.get("attacks"):
            self._err(card, "Pokémon card has no attacks")
        if card.data.get("retreatCost") is None:
            self._err(card, "Pokémon card has no retreatCost")
        if not card.data.get("pokedexNumbers"):
            self._err(card, "Pokémon card has no pokedexNumbers")
        if not card.data.get("illustrators"):
            self._err(card, "Pokémon card has no illustrators")

        if card.data.get("evolvesInto"):
            self._err(card, "Pokémon card must not have evolvesInto")
        if card.data.get("description"):
            self._err(card, "Pokémon card must not have description")

    @single_card_check
    def _check_nonbasic_has_evolvesfrom_and_vice_versa(self, card):
        # Presence of a pokemonStage is checked elsewhere.
        is_evolved = ((card.data.get("pokemonStage") or "Basic") != "Basic")
        has_evolves_from = (card.data.get("evolvesFrom") is not None)
        if is_evolved and not has_evolves_from:
            self._err(card, "Evolution Pokémon is missing evolvesFrom")
        elif not is_evolved and has_evolves_from:
            self._err(card, "Basic Pokémon has evolvesFrom")

    @single_card_check
    def _check_energy_types(self, card):
        _VALID = {'Colorless', 'Darkness', 'Fighting', 'Grass', 'Lightning', 'Metal',
                  'Dragon', 'Psychic', 'Fire', 'Water', 'Fairy'}
        def _check(context, et):
            if et not in _VALID:
                self._err(card, f"wrong energy type {et} in {context}")

        [_check("Pokémon energyTypes", et) for et in card.data.get("energyTypes", [])]
        [_check("Pokémon weakness", wk.get("type")) for wk in card.data.get("weaknesses", [])]
        [_check("Pokémon resistances", res.get("type")) for res in card.data.get("resistances", [])]

        for atk in card.data.get("attacks", []):
            [_check(f"attack {atk.get('name', '!UNKNOWN!')}", er.get("type"))
             for er in atk.get("energies", [])]

    @single_card_check
    def _check_sorting_orders(self, card):
        def _check(context, l):
            orders = [e.get("sortingOrder") for e in l]
            if all(e is None for e in orders):
                return
            normalized = list(range(1, len(orders) + 1))
            if orders != normalized:
                self._warn(card, f"wrong {context} sorting order: {orders}")

        attrs = ("variants", "rules", "effects", "attacks", "weaknesses", "resistances")
        for a in attrs:
            v = card.data.get(a)
            if not v or not isinstance(v, tuple):
                continue
            _check(a, v)

        for attack in card.data.get("attacks", []):
            v = card.data.get("energies")
            if not v or not isinstance(v, tuple):
                continue
            _check(f"attack {attack} energies", v)

    @single_card_check
    def _check_set_timestamp(self, card):
        ts = card.data.get("expansion", {}).get("releaseDate")
        if not ts:
            return
        try:
            datetime.datetime.fromisoformat(ts)
        except ValueError:
            self._err(card, f"invalid set release date: {ts}")

    @set_consistency_check
    def _check_set_attributes_identical(self, card_set):
        attrs = ("id", "name", "series", "tcgRegion", "code", "releaseDate", "cardNumberRightPart")
        values = {a: {} for a in attrs}
        for card in card_set.cards:
            xp = card.data.get("expansion", {})
            for a in attrs:
                values[a].setdefault(xp.get(a), set()).add(card)
        for a in attrs:
            if len(values[a]) > 1:
                self._warn(card_set, f"Same set cards found with different expansion {a}: {values[a]}")

    @set_consistency_check
    def _check_same_pokemon_different_attributes(self, card_set):
        per_name = {}
        for card in card_set.cards:
            if (card.data.get("supertype") != "Pokémon"
                    or not card.data.get("name")):
                continue
            per_name.setdefault(card.data.get("name"), set()).add(card)

        attrs = ("stages", "evolvesFrom", "pokedexNumbers")
        for name, cards in per_name.items():
            values = {a: {} for a in attrs}
            for card in cards:
                for a in attrs:
                    values[a].setdefault(card.data.get(a), set()).add(card)
            for a in attrs:
                if len(values[a]) > 1:
                    self._warn(card_set, f"Pokémon {name} found with different {a}: {values[a]}")

    @set_consistency_check
    def _check_number_sorting_order_uniqueness(self, card_set):
        per_sorting_order = {}
        for card in card_set.cards:
            n = card.data.get("numberSortingOrder")
            if n is None:
                continue
            per_sorting_order.setdefault(n, set()).add(card)
        for n, cards in sorted(per_sorting_order.items()):
            if len(cards) > 1:
                self._err(card_set, f"two cards share sorting order {n}: {cards}")


def main():
    parser = argparse.ArgumentParser(prog="tcgclinter")
    parser.add_argument("-r", "--recursive", action="store_true")
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("sources", nargs="*", type=pathlib.Path)
    args = parser.parse_args()

    linter = Linter(verbose=args.verbose)
    linter.process(args.sources, recursive=args.recursive)
    linter.summarize()

    if len(linter.errors) > 0:
        sys.exit(2)
    elif len(linter.warnings) > 0:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
