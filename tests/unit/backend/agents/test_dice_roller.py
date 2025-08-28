"""
Unit tests for the dice rolling system.
"""

import pytest
from packages.backend.ai.tools.calculators.dice_roller import (
    DiceRoller,
    DiceType,
    AdvantageType,
    DiceRoll,
    RollResult,
    roll,
    roll_stats
)


class TestDiceRoller:
    """Test the main DiceRoller class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.roller = DiceRoller(seed=42)  # Fixed seed for reproducible tests
    
    def test_roll_single_die(self):
        """Test rolling a single die."""
        result = self.roller.roll_single_die(6)
        assert 1 <= result <= 6
        
        result = self.roller.roll_single_die(20)
        assert 1 <= result <= 20
    
    def test_roll_single_die_invalid(self):
        """Test rolling invalid dice."""
        with pytest.raises(ValueError):
            self.roller.roll_single_die(0)
        
        with pytest.raises(ValueError):
            self.roller.roll_single_die(-1)
    
    def test_roll_multiple_dice(self):
        """Test rolling multiple dice."""
        results = self.roller.roll_multiple_dice(3, 6)
        assert len(results) == 3
        assert all(1 <= roll <= 6 for roll in results)
    
    def test_roll_multiple_dice_invalid(self):
        """Test rolling invalid multiple dice."""
        with pytest.raises(ValueError):
            self.roller.roll_multiple_dice(0, 6)
        
        with pytest.raises(ValueError):
            self.roller.roll_multiple_dice(-1, 6)
    
    def test_roll_with_advantage_normal(self):
        """Test normal d20 roll."""
        rolls, result = self.roller.roll_with_advantage(20, AdvantageType.NORMAL)
        assert len(rolls) == 1
        assert 1 <= result <= 20
        assert result == rolls[0]
    
    def test_roll_with_advantage(self):
        """Test advantage roll."""
        rolls, result = self.roller.roll_with_advantage(20, AdvantageType.ADVANTAGE)
        assert len(rolls) == 2
        assert result == max(rolls)
        assert 1 <= result <= 20
    
    def test_roll_with_disadvantage(self):
        """Test disadvantage roll."""
        rolls, result = self.roller.roll_with_advantage(20, AdvantageType.DISADVANTAGE)
        assert len(rolls) == 2
        assert result == min(rolls)
        assert 1 <= result <= 20


class TestDiceNotation:
    """Test dice notation parsing and rolling."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.roller = DiceRoller(seed=42)
    
    def test_parse_dice_notation_basic(self):
        """Test basic dice notation parsing."""
        result = self.roller.parse_dice_notation("2d6")
        assert result == {'count': 2, 'sides': 6, 'modifier': 0}
        
        result = self.roller.parse_dice_notation("1d20")
        assert result == {'count': 1, 'sides': 20, 'modifier': 0}
        
        result = self.roller.parse_dice_notation("d4")
        assert result == {'count': 1, 'sides': 4, 'modifier': 0}
    
    def test_parse_dice_notation_with_modifiers(self):
        """Test dice notation with modifiers."""
        result = self.roller.parse_dice_notation("2d6+3")
        assert result == {'count': 2, 'sides': 6, 'modifier': 3}
        
        result = self.roller.parse_dice_notation("1d20-2")
        assert result == {'count': 1, 'sides': 20, 'modifier': -2}
        
        result = self.roller.parse_dice_notation("d8+1")
        assert result == {'count': 1, 'sides': 8, 'modifier': 1}
    
    def test_parse_dice_notation_invalid(self):
        """Test invalid dice notation."""
        with pytest.raises(ValueError):
            self.roller.parse_dice_notation("invalid")
        
        with pytest.raises(ValueError):
            self.roller.parse_dice_notation("2x6")
        
        with pytest.raises(ValueError):
            self.roller.parse_dice_notation("d")
    
    def test_roll_dice_notation(self):
        """Test rolling using dice notation."""
        result = self.roller.roll_dice_notation("2d6+3")
        assert isinstance(result, DiceRoll)
        assert result.dice_type == 6
        assert len(result.rolls) == 2
        assert result.modifier == 3
        assert result.total == sum(result.rolls) + 3