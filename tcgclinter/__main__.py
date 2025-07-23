"""
tcgclinter: checks JSON card files for tcgcollector.com for common errors.

SPDX-License-Identifier: EUPL-1.2
SPDX-FileCopyrightText: 2025 Pierre Bourdon <delroth@gmail.com>
"""

import argparse
import dataclasses
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
    card: Card
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

    def _warn(self, card, message):
        finding = Finding(card=card, message=message)
        if self.verbose:
            self._print_warning(finding)
        self.warnings.append(finding)

    def _err(self, card, message):
        finding = Finding(card=card, message=message)
        if self.verbose:
            self._print_error(finding)
        self.errors.append(finding)

    def _print_warning(self, finding):
        print(f"Warning: ({finding.card}) {finding.message}")

    def _print_error(self, finding):
        print(f"Error:   ({finding.card}) {finding.message}")

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
                    data = json.load(fp)
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
        if not card.data.get("variants", []):
            self._err(card, "card has no variants")
        if card.data.get("supertype") is None:
            self._err(card, "card has no supertype")
        if not card.data.get("types", []):
            self._err(card, "card has no types")
        if card.data.get("format") is None:
            self._err(card, "card has no format")

    @single_card_check
    def _check_pokemon_card_standard_attributes(self, card):
        if card.data.get("supertype") != "Pokémon":
            return

        if card.data.get("pokemonStage") is None:
            self._err(card, "Pokémon card has no pokemonStage")
        if card.data.get("evolvesInto"):
            self._err(card, "Pokémon card must not have evolvesInto")
        if card.data.get("hitPoints") is None:
            self._err(card, "Pokémon card has no hitPoints")
        if not card.data.get("energyTypes"):
            self._err(card, "Pokémon card has no energyTypes")
        if not card.data.get("attacks"):
            self._err(card, "Pokémon card has no attacks")
        if card.data.get("retreatCost") is None:
            self._err(card, "Pokémon card has no retreatCost")
        if not card.data.get("illustrators"):
            self._err(card, "Pokémon card has no illustrators")
        if card.data.get("description"):
            self._err(card, "Pokémon card must not have description")

    @single_card_check
    def _check_nonbasic_has_evolvesfrom_and_vice_versa(self, card):
        # Presence of a pokemonStage is checked elsewhere.
        is_evolved = (card.data.get("pokemonStage", "Basic") != "Basic")
        has_evolves_from = (card.data.get("evolvesFrom") is not None)
        if is_evolved and not has_evolves_from:
            self._err(card, "Evolution Pokémon is missing evolvesFrom")
        elif not is_evolved and has_evolves_from:
            self._err(card, "Basic Pokémon has evolvesFrom")

    @single_card_check
    def _check_pokemon_has_pokedex_number(self, card):
        if (card.data.get("supertype") == "Pokémon" and
            len(card.data.get("pokedexNumbers", [])) == 0):
            self._err(card, "Pokémon card is missing Pokédex Number")


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
