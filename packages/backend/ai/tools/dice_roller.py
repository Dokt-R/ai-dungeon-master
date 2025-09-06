"""
Comprehensive dice rolling system for D&D 5.1 campaigns.
Handles all standard dice types, modifiers, advantage/disadvantage, and complex rolls.
"""

import random
import re
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

# TODO: Enhance to return critical success and refactor nodes accordingly


class DiceType(Enum):
    """Standard D&D dice types."""

    D4 = 4
    D6 = 6
    D8 = 8
    D10 = 10
    D12 = 12
    D20 = 20
    D100 = 100


class AdvantageType(Enum):
    """Advantage/disadvantage types for d20 rolls."""

    NORMAL = "normal"
    ADVANTAGE = "advantage"
    DISADVANTAGE = "disadvantage"


@dataclass
class DiceRoll:
    """Represents a single dice roll result."""

    dice_type: int
    rolls: List[int]
    modifier: int = 0
    advantage_type: AdvantageType = AdvantageType.NORMAL
    total: int = 0
    description: str = ""


@dataclass
class RollResult:
    """Complete result of a dice rolling operation."""

    individual_rolls: List[DiceRoll]
    total: int
    description: str
    raw_input: str


class DiceRoller:
    """Main dice rolling engine for D&D operations."""

    def __init__(self, seed: Optional[int] = None):
        """Initialize the dice roller with optional seed for testing."""
        if seed is not None:
            random.seed(seed)

    def roll_single_die(self, sides: int) -> int:
        """Roll a single die with specified number of sides."""
        if sides <= 0:
            raise ValueError(f"Invalid dice sides: {sides}")
        return random.randint(1, sides)

    def roll_multiple_dice(self, count: int, sides: int) -> List[int]:
        """Roll multiple dice of the same type."""
        if count <= 0:
            raise ValueError(f"Invalid dice count: {count}")
        return [self.roll_single_die(sides) for _ in range(count)]

    def roll_with_advantage(
        self, sides: int = 20, advantage_type: AdvantageType = AdvantageType.NORMAL
    ) -> Tuple[List[int], int]:
        """Roll with advantage, disadvantage, or normal."""
        if advantage_type == AdvantageType.NORMAL:
            roll = self.roll_single_die(sides)
            return [roll], roll

        # Roll twice for advantage/disadvantage
        rolls = [self.roll_single_die(sides), self.roll_single_die(sides)]

        if advantage_type == AdvantageType.ADVANTAGE:
            result = max(rolls)
        else:  # DISADVANTAGE
            result = min(rolls)

        return rolls, result

    def _parse_dice_notation(self, notation: str) -> Dict[str, Any]:
        """
        Parse standard dice notation like '2d6+3', '1d20', 'd4-1', etc.

        Supported formats:
        - XdY: X dice of Y sides
        - XdY+Z: X dice of Y sides plus Z modifier
        - XdY-Z: X dice of Y sides minus Z modifier
        - dY: Single die of Y sides (X defaults to 1)
        """
        notation = notation.lower().strip().replace(" ", "")

        # Pattern for dice notation: optional count, 'd', sides, optional modifier
        pattern = r"^(\d*)d(\d+)([+-]\d+)?$"
        match = re.match(pattern, notation)

        if not match:
            raise ValueError(f"Invalid dice notation: {notation}")

        count_str, sides_str, modifier_str = match.groups()

        count = int(count_str) if count_str else 1
        sides = int(sides_str)
        modifier = int(modifier_str) if modifier_str else 0

        return {"count": count, "sides": sides, "modifier": modifier}

    def roll_dice_notation(
        self, notation: str, advantage_type: AdvantageType = AdvantageType.NORMAL
    ) -> DiceRoll:
        """Roll dice using standard notation with optional advantage/disadvantage."""
        parsed = self._parse_dice_notation(notation)
        count = parsed["count"]
        sides = parsed["sides"]
        modifier = parsed["modifier"]

        # Handle advantage/disadvantage for d20 rolls
        if sides == 20 and count == 1 and advantage_type != AdvantageType.NORMAL:
            rolls, result = self.roll_with_advantage(sides, advantage_type)
            total = result + modifier
        else:
            rolls = self.roll_multiple_dice(count, sides)
            total = sum(rolls) + modifier

        return DiceRoll(
            dice_type=sides,
            rolls=rolls,
            modifier=modifier,
            advantage_type=advantage_type,
            total=total,
            description=f"{count}d{sides}{'+' + str(modifier) if modifier > 0 else str(modifier) if modifier < 0 else ''}",
        )

    def roll_complex_expression(self, expression: str) -> RollResult:
        """
        Roll complex dice expressions like '2d6+1d4+3' or '1d20+5'.

        Supports:
        - Multiple dice types in one expression
        - Addition and subtraction
        - Modifiers
        """
        expression = expression.lower().strip().replace(" ", "")

        # Split by + and - while keeping the operators
        parts = re.split(r"([+-])", expression)

        individual_rolls = []
        total = 0
        current_sign = 1

        for part in parts:
            if part == "+":
                current_sign = 1
                continue
            elif part == "-":
                current_sign = -1
                continue
            elif not part:
                continue

            # Check if it's a dice notation or just a number
            if "d" in part:
                roll = self.roll_dice_notation(part)
                roll.total *= current_sign
                individual_rolls.append(roll)
                total += roll.total
            else:
                # It's just a modifier
                modifier_value = int(part) * current_sign
                total += modifier_value

        return RollResult(
            individual_rolls=individual_rolls,
            total=total,
            description=expression,
            raw_input=expression,
        )

    def roll_ability_scores(self, method: str = "4d6_drop_lowest") -> Dict[str, int]:
        """
        Roll ability scores using various methods.

        Methods:
        - '4d6_drop_lowest': Roll 4d6, drop lowest (standard)
        - '3d6': Straight 3d6 rolls
        - 'point_buy': Return standard point buy array
        - 'standard_array': Return standard array [15,14,13,12,10,8]
        """
        abilities = [
            "strength",
            "dexterity",
            "constitution",
            "intelligence",
            "wisdom",
            "charisma",
        ]

        if method == "standard_array":
            values = [15, 14, 13, 12, 10, 8]
            return dict(zip(abilities, values))

        elif method == "point_buy":
            # Standard point buy starting values
            values = [13, 13, 13, 13, 13, 13]
            return dict(zip(abilities, values))

        elif method == "3d6":
            return {
                ability: sum(self.roll_multiple_dice(3, 6)) for ability in abilities
            }

        elif method == "4d6_drop_lowest":
            scores = {}
            for ability in abilities:
                rolls = self.roll_multiple_dice(4, 6)
                rolls.sort(reverse=True)
                scores[ability] = sum(rolls[:3])  # Take top 3
            return scores

        else:
            raise ValueError(f"Unknown ability score method: {method}")

    def roll_hit_points(
        self, hit_die: int, level: int, constitution_modifier: int = 0
    ) -> int:
        """Roll hit points for a character at given level."""
        if level <= 0:
            raise ValueError(f"Invalid level: {level}")

        # First level gets max hit die + con mod
        total_hp = hit_die + constitution_modifier

        # Roll for remaining levels
        for _ in range(level - 1):
            roll = self.roll_single_die(hit_die)
            total_hp += roll + constitution_modifier

        return max(1, total_hp)  # Minimum 1 HP

    def roll_attack(
        self, attack_bonus: int, advantage_type: AdvantageType = AdvantageType.NORMAL
    ) -> DiceRoll:
        """Roll an attack roll with bonus and optional advantage/disadvantage."""
        roll = self.roll_dice_notation("1d20", advantage_type)
        roll.modifier = attack_bonus
        roll.actual = (
            roll.rolls[0]
            if advantage_type == AdvantageType.NORMAL
            else max(roll.rolls)
            if advantage_type == AdvantageType.ADVANTAGE
            else min(roll.rolls)
        )
        roll.total = roll.actual + attack_bonus
        roll.description = f"Attack: 1d20{'+' + str(attack_bonus) if attack_bonus >= 0 else str(attack_bonus)}"

        if advantage_type != AdvantageType.NORMAL:
            roll.description += f" ({advantage_type.value})"

        return roll

    def roll_damage(self, damage_dice: str, damage_type: str = "") -> DiceRoll:
        """Roll damage dice with optional damage type."""
        roll = self.roll_dice_notation(damage_dice)
        roll.description = f"Damage: {damage_dice}"
        if damage_type:
            roll.description += f" ({damage_type})"
        return roll

    def roll_saving_throw(
        self, save_bonus: int, advantage_type: AdvantageType = AdvantageType.NORMAL
    ) -> DiceRoll:
        """Roll a saving throw with bonus and optional advantage/disadvantage."""
        roll = self.roll_dice_notation("1d20", advantage_type)
        roll.modifier = save_bonus
        roll.total = (
            roll.rolls[0]
            if advantage_type == AdvantageType.NORMAL
            else max(roll.rolls)
            if advantage_type == AdvantageType.ADVANTAGE
            else min(roll.rolls)
        )
        roll.total += save_bonus
        roll.description = (
            f"Save: 1d20{'+' + str(save_bonus) if save_bonus >= 0 else str(save_bonus)}"
        )

        if advantage_type != AdvantageType.NORMAL:
            roll.description += f" ({advantage_type.value})"

        return roll

    def roll_skill_check(
        self, skill_bonus: int, advantage_type: AdvantageType = AdvantageType.NORMAL
    ) -> DiceRoll:
        """Roll a skill check with bonus and optional advantage/disadvantage."""
        roll = self.roll_dice_notation("1d20", advantage_type)
        roll.modifier = skill_bonus
        roll.total = (
            roll.rolls[0]
            if advantage_type == AdvantageType.NORMAL
            else max(roll.rolls)
            if advantage_type == AdvantageType.ADVANTAGE
            else min(roll.rolls)
        )
        roll.total += skill_bonus
        roll.description = f"Skill: 1d20{'+' + str(skill_bonus) if skill_bonus >= 0 else str(skill_bonus)}"

        if advantage_type != AdvantageType.NORMAL:
            roll.description += f" ({advantage_type.value})"

        return roll

    def roll_initiative(self, dexterity_modifier: int = 0) -> DiceRoll:
        """Roll initiative with dexterity modifier."""
        return self.roll_skill_check(dexterity_modifier)

    def format_roll_result(self, result: RollResult) -> str:
        """Format a roll result for display."""
        lines = [f"**{result.description}**"]

        for roll in result.individual_rolls:
            roll_details = f"Rolled {len(roll.rolls)}d{roll.dice_type}: {roll.rolls}"
            if roll.modifier != 0:
                roll_details += f" {'+' if roll.modifier > 0 else ''}{roll.modifier}"
            if roll.advantage_type != AdvantageType.NORMAL:
                roll_details += f" ({roll.advantage_type.value})"
            roll_details += f" = **{roll.total}**"
            lines.append(roll_details)

        if len(result.individual_rolls) > 1:
            lines.append(f"**Total: {result.total}**")

        return "\n".join(lines)


# Convenience functions for common operations
def roll(notation: str, advantage: str = "normal") -> RollResult:
    """Quick roll function using dice notation."""
    roller = DiceRoller()
    advantage_type = AdvantageType(advantage.lower())

    if "d" in notation:
        roll_result = roller.roll_dice_notation(notation, advantage_type)
        return RollResult(
            individual_rolls=[roll_result],
            total=roll_result.total,
            description=notation,
            raw_input=notation,
        )
    else:
        return roller.roll_complex_expression(notation)


def roll_stats() -> Dict[str, int]:
    """Quick ability score generation using 4d6 drop lowest."""
    roller = DiceRoller()
    return roller.roll_ability_scores("4d6_drop_lowest")
