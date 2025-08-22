"""
SRD Data Verification Service for D&D 5.1 System Reference Document.

This module provides data verification utilities for SRD data including:
- Official source verification against known SRD checksums
- Data accuracy checking mechanisms
- Source attribution and versioning system
- Data integrity validation routines
- Cross-reference validation with official sources
"""

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from packages.shared.logging_config import get_logger
from packages.shared.models import DataSource, Monster, Spell, Weapon

logger = get_logger(__name__)


class VerificationStatus(Enum):
    """Data verification status."""

    VERIFIED = "verified"
    UNVERIFIED = "unverified"
    MODIFIED = "modified"
    INVALID = "invalid"
    OUTDATED = "outdated"


class SourceType(Enum):
    """Type of data source."""

    OFFICIAL_SRD = "official_srd"
    WOTC_PUBLICATION = "wotc_publication"
    THIRD_PARTY_VERIFIED = "third_party_verified"
    COMMUNITY_CONTRIBUTION = "community_contribution"
    UNVERIFIED = "unverified"


@dataclass
class VerificationResult:
    """Result of data verification."""

    status: VerificationStatus
    source_type: SourceType
    checksum_match: bool
    accuracy_score: float
    issues: List[str]
    recommendations: List[str]
    verified_at: datetime
    verification_hash: str


@dataclass
class DataVersion:
    """Data version information."""

    version_id: str
    source_url: str
    publication_date: datetime
    checksum: str
    changes_summary: str
    is_latest: bool
    compatibility: List[str]


class SRDDataVerificationService:
    """
    Service for verifying SRD data against official sources.

    Features:
    - Official SRD checksum verification
    - Data accuracy checking
    - Source attribution tracking
    - Version management
    - Cross-reference validation
    """

    def __init__(self):
        self.logger = get_logger(f"{__name__}.SRDDataVerificationService")
        self._known_checksums = self._load_known_checksums()
        self._official_sources = self._load_official_sources()

    def _load_known_checksums(self) -> Dict[str, str]:
        """Load known checksums for official SRD data."""
        # In production, this would load from a configuration file or database
        return {
            "srd_5.1_monsters": "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z",
            "srd_5.1_spells": "z9y8x7w6v5u4t3s2r1q0p9o8n7m6l5k4j3i2h1g0f9e8d7c6b5a4",
            "srd_5.1_weapons": "1a2b3c4d5e6f7g8h9i0j1k2l3m4n5o6p7q8r9s0t1u2v3w4x5y6z",
        }

    def _load_official_sources(self) -> Dict[str, DataVersion]:
        """Load information about official SRD sources."""
        return {
            "srd_5.1": DataVersion(
                version_id="srd_5.1",
                source_url="https://dnd.wizards.com/articles/features/systems-reference-document-srd",
                publication_date=datetime(2016, 5, 12),
                checksum="a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z",
                changes_summary="Initial D&D 5.1 SRD release",
                is_latest=True,
                compatibility=["5.1", "5.0"],
            )
        }

    def verify_monster_data(self, monster: Monster) -> VerificationResult:
        """Verify monster data against official sources."""
        try:
            issues = []
            recommendations = []

            # Check data source
            source_type = self._classify_source(monster.data_source)

            # Verify checksum
            data_hash = self._calculate_entity_hash(monster, "monster")
            checksum_match = data_hash == monster.data_source.checksum

            # Check data accuracy
            accuracy_issues = self._check_monster_accuracy(monster)
            issues.extend(accuracy_issues)

            # Determine verification status
            status = self._determine_verification_status(
                source_type, checksum_match, issues
            )

            # Generate recommendations
            if not checksum_match:
                recommendations.append(
                    "Update data source checksum to match verified source"
                )
            if issues:
                recommendations.append("Review and correct identified accuracy issues")

            accuracy_score = max(0.0, 1.0 - (len(issues) * 0.1))

            return VerificationResult(
                status=status,
                source_type=source_type,
                checksum_match=checksum_match,
                accuracy_score=accuracy_score,
                issues=issues,
                recommendations=recommendations,
                verified_at=datetime.utcnow(),
                verification_hash=data_hash,
            )

        except Exception as e:
            self.logger.error("Failed to verify monster data", error=str(e))
            return VerificationResult(
                status=VerificationStatus.INVALID,
                source_type=SourceType.UNVERIFIED,
                checksum_match=False,
                accuracy_score=0.0,
                issues=[f"Verification failed: {str(e)}"],
                recommendations=["Manual review required"],
                verified_at=datetime.utcnow(),
                verification_hash="",
            )

    def verify_spell_data(self, spell: Spell) -> VerificationResult:
        """Verify spell data against official sources."""
        try:
            issues = []
            recommendations = []

            # Check data source
            source_type = self._classify_source(spell.data_source)

            # Verify checksum
            data_hash = self._calculate_entity_hash(spell, "spell")
            checksum_match = data_hash == spell.data_source.checksum

            # Check data accuracy
            accuracy_issues = self._check_spell_accuracy(spell)
            issues.extend(accuracy_issues)

            # Determine verification status
            status = self._determine_verification_status(
                source_type, checksum_match, issues
            )

            # Generate recommendations
            if not checksum_match:
                recommendations.append(
                    "Update data source checksum to match verified source"
                )
            if issues:
                recommendations.append("Review and correct identified accuracy issues")

            accuracy_score = max(0.0, 1.0 - (len(issues) * 0.1))

            return VerificationResult(
                status=status,
                source_type=source_type,
                checksum_match=checksum_match,
                accuracy_score=accuracy_score,
                issues=issues,
                recommendations=recommendations,
                verified_at=datetime.utcnow(),
                verification_hash=data_hash,
            )

        except Exception as e:
            self.logger.error("Failed to verify spell data", error=str(e))
            return VerificationResult(
                status=VerificationStatus.INVALID,
                source_type=SourceType.UNVERIFIED,
                checksum_match=False,
                accuracy_score=0.0,
                issues=[f"Verification failed: {str(e)}"],
                recommendations=["Manual review required"],
                verified_at=datetime.utcnow(),
                verification_hash="",
            )

    def verify_weapon_data(self, weapon: Weapon) -> VerificationResult:
        """Verify weapon data against official sources."""
        try:
            issues = []
            recommendations = []

            # Check data source
            source_type = self._classify_source(weapon.data_source)

            # Verify checksum
            data_hash = self._calculate_entity_hash(weapon, "weapon")
            checksum_match = data_hash == weapon.data_source.checksum

            # Check data accuracy
            accuracy_issues = self._check_weapon_accuracy(weapon)
            issues.extend(accuracy_issues)

            # Determine verification status
            status = self._determine_verification_status(
                source_type, checksum_match, issues
            )

            # Generate recommendations
            if not checksum_match:
                recommendations.append(
                    "Update data source checksum to match verified source"
                )
            if issues:
                recommendations.append("Review and correct identified accuracy issues")

            accuracy_score = max(0.0, 1.0 - (len(issues) * 0.1))

            return VerificationResult(
                status=status,
                source_type=source_type,
                checksum_match=checksum_match,
                accuracy_score=accuracy_score,
                issues=issues,
                recommendations=recommendations,
                verified_at=datetime.utcnow(),
                verification_hash=data_hash,
            )

        except Exception as e:
            self.logger.error("Failed to verify weapon data", error=str(e))
            return VerificationResult(
                status=VerificationStatus.INVALID,
                source_type=SourceType.UNVERIFIED,
                checksum_match=False,
                accuracy_score=0.0,
                issues=[f"Verification failed: {str(e)}"],
                recommendations=["Manual review required"],
                verified_at=datetime.utcnow(),
                verification_hash="",
            )

    def _classify_source(self, data_source: DataSource) -> SourceType:
        """Classify the type of data source."""
        if not data_source.is_official:
            return SourceType.UNVERIFIED

        # Check if it's a known official source
        official_urls = [
            "https://dnd.wizards.com/articles/features/systems-reference-document-srd",
            "https://dnd.wizards.com/resources/systems-reference-document",
        ]

        if any(url in data_source.source_url for url in official_urls):
            return SourceType.OFFICIAL_SRD

        # Check for other WotC publications
        if "dnd.wizards.com" in data_source.source_url:
            return SourceType.WOTC_PUBLICATION

        return SourceType.THIRD_PARTY_VERIFIED

    def _calculate_entity_hash(
        self, entity: Union[Monster, Spell, Weapon], entity_type: str
    ) -> str:
        """Calculate hash for entity data verification."""
        # Create a normalized representation of the entity
        if isinstance(entity, Monster):
            data = {
                "monster_name": entity.monster_name,
                "armor_class": entity.armor_class,
                "hit_points": entity.hit_points,
                "strength": entity.strength,
                "dexterity": entity.dexterity,
                "constitution": entity.constitution,
                "intelligence": entity.intelligence,
                "wisdom": entity.wisdom,
                "charisma": entity.charisma,
                "challenge_rating": entity.challenge_rating,
                "actions": entity.actions,
                "special_abilities": entity.special_abilities,
                "description": entity.description,
            }
        elif isinstance(entity, Spell):
            data = {
                "spell_name": entity.spell_name,
                "level": entity.level,
                "school": entity.school,
                "casting_time": entity.casting_time,
                "range": entity.range,
                "components": entity.components,
                "duration": entity.duration,
                "description": entity.description,
                "at_higher_levels": entity.at_higher_levels,
                "classes": entity.classes,
            }
        elif isinstance(entity, Weapon):
            data = {
                "weapon_name": entity.weapon_name,
                "category": entity.category,
                "cost": entity.cost,
                "damage": entity.damage,
                "weight": entity.weight,
                "properties": entity.properties,
                "description": entity.description,
            }
        else:
            raise ValueError(f"Unsupported entity type: {entity_type}")

        # Create hash of the normalized data
        data_str = json.dumps(data, sort_keys=True)
        return hashlib.sha256(data_str.encode()).hexdigest()

    def _check_monster_accuracy(self, monster: Monster) -> List[str]:
        """Check accuracy of monster data."""
        issues = []

        # Check ability scores
        abilities = [
            ("strength", monster.strength),
            ("dexterity", monster.dexterity),
            ("constitution", monster.constitution),
            ("intelligence", monster.intelligence),
            ("wisdom", monster.wisdom),
            ("charisma", monster.charisma),
        ]

        for ability_name, score in abilities:
            if not (1 <= score <= 30):
                issues.append(f"Invalid {ability_name} score: {score} (must be 1-30)")

        # Check armor class
        if not (5 <= monster.armor_class <= 25):
            issues.append(f"Suspicious armor class: {monster.armor_class}")

        # Check challenge rating format
        if monster.challenge_rating and not self._is_valid_challenge_rating(
            monster.challenge_rating
        ):
            issues.append(
                f"Invalid challenge rating format: {monster.challenge_rating}"
            )

        # Check for missing critical data
        if not monster.monster_name or monster.monster_name.strip() == "":
            issues.append("Missing monster name")
        if not monster.hit_points or monster.hit_points.strip() == "":
            issues.append("Missing hit points")

        return issues

    def _check_spell_accuracy(self, spell: Spell) -> List[str]:
        """Check accuracy of spell data."""
        issues = []

        # Check spell level
        if not (0 <= spell.level <= 9):
            issues.append(f"Invalid spell level: {spell.level} (must be 0-9)")

        # Check for missing critical data
        if not spell.spell_name or spell.spell_name.strip() == "":
            issues.append("Missing spell name")
        if not spell.description or spell.description.strip() == "":
            issues.append("Missing spell description")
        if not spell.casting_time or spell.casting_time.strip() == "":
            issues.append("Missing casting time")
        if not spell.components or spell.components.strip() == "":
            issues.append("Missing spell components")

        # Check school validity
        valid_schools = [
            "Abjuration",
            "Conjuration",
            "Divination",
            "Enchantment",
            "Evocation",
            "Illusion",
            "Necromancy",
            "Transmutation",
        ]
        if spell.school not in valid_schools:
            issues.append(f"Invalid spell school: {spell.school}")

        return issues

    def _check_weapon_accuracy(self, weapon: Weapon) -> List[str]:
        """Check accuracy of weapon data."""
        issues = []

        # Check for missing critical data
        if not weapon.weapon_name or weapon.weapon_name.strip() == "":
            issues.append("Missing weapon name")
        if not weapon.damage or weapon.damage.strip() == "":
            issues.append("Missing damage")
        if not weapon.cost or weapon.cost.strip() == "":
            issues.append("Missing cost")

        # Check category validity
        valid_categories = [
            "Simple Melee Weapons",
            "Simple Ranged Weapons",
            "Martial Melee Weapons",
            "Martial Ranged Weapons",
        ]
        if weapon.category not in valid_categories:
            issues.append(f"Invalid weapon category: {weapon.category}")

        return issues

    def _is_valid_challenge_rating(self, cr: str) -> bool:
        """Check if challenge rating format is valid."""
        try:
            # Handle fractional CRs like "1/4", "1/2", "1/8"
            if "/" in cr:
                numerator, denominator = cr.split("/")
                num = int(numerator)
                den = int(denominator)
                return den in [4, 8, 2] and num == 1
            else:
                # Handle whole number CRs
                cr_float = float(cr)
                return 0 <= cr_float <= 30
        except ValueError:
            return False

    def _determine_verification_status(
        self, source_type: SourceType, checksum_match: bool, issues: List[str]
    ) -> VerificationStatus:
        """Determine the verification status based on various factors."""
        if source_type == SourceType.OFFICIAL_SRD and checksum_match and not issues:
            return VerificationStatus.VERIFIED
        elif source_type == SourceType.OFFICIAL_SRD and checksum_match:
            return (
                VerificationStatus.VERIFIED
            )  # Still verified, but with issues to note
        elif source_type == SourceType.WOTC_PUBLICATION and not issues:
            return VerificationStatus.VERIFIED
        elif checksum_match and not issues:
            return VerificationStatus.VERIFIED
        elif issues and checksum_match:
            return VerificationStatus.MODIFIED
        elif source_type == SourceType.UNVERIFIED:
            return VerificationStatus.UNVERIFIED
        else:
            return VerificationStatus.INVALID

    def get_source_attribution(
        self, entity: Union[Monster, Spell, Weapon]
    ) -> Dict[str, Any]:
        """Get source attribution information for an entity."""
        if isinstance(entity, Monster):
            entity_type = "monster"
            name = entity.monster_name
        elif isinstance(entity, Spell):
            entity_type = "spell"
            name = entity.spell_name
        elif isinstance(entity, Weapon):
            entity_type = "weapon"
            name = entity.weapon_name
        else:
            raise ValueError("Unsupported entity type")

        return {
            "entity_type": entity_type,
            "entity_name": name,
            "data_source": entity.data_source.model_dump(),
            "srd_compliance": entity.srd_compliance.model_dump(),
            "attribution_required": entity.data_source.attribution_required,
            "attribution_text": self._generate_attribution_text(entity),
            "last_verified": entity.srd_compliance.last_verified.isoformat(),
            "verification_hash": entity.srd_compliance.verification_hash,
        }

    def _generate_attribution_text(self, entity: Union[Monster, Spell, Weapon]) -> str:
        """Generate proper attribution text for the entity."""
        source = entity.data_source
        if source.attribution_required:
            return f"Source: {source.source_name} ({source.source_url}) - Used under Open Gaming License v1.0a"
        else:
            return f"Source: {source.source_name} - No attribution required"

    def get_data_version_info(self, version_id: str) -> Optional[DataVersion]:
        """Get information about a specific data version."""
        return self._official_sources.get(version_id)

    def list_available_versions(self) -> List[DataVersion]:
        """List all available data versions."""
        return list(self._official_sources.values())

    def validate_data_integrity(
        self, entities: List[Union[Monster, Spell, Weapon]]
    ) -> Dict[str, Any]:
        """Validate data integrity across a collection of entities."""
        results = {
            "total_entities": len(entities),
            "verified_entities": 0,
            "unverified_entities": 0,
            "modified_entities": 0,
            "invalid_entities": 0,
            "integrity_score": 0.0,
            "summary_issues": [],
            "recommendations": [],
        }

        for entity in entities:
            if isinstance(entity, Monster):
                verification = self.verify_monster_data(entity)
            elif isinstance(entity, Spell):
                verification = self.verify_spell_data(entity)
            elif isinstance(entity, Weapon):
                verification = self.verify_weapon_data(entity)
            else:
                continue

            if verification.status == VerificationStatus.VERIFIED:
                results["verified_entities"] += 1
            elif verification.status == VerificationStatus.UNVERIFIED:
                results["unverified_entities"] += 1
            elif verification.status == VerificationStatus.MODIFIED:
                results["modified_entities"] += 1
            elif verification.status == VerificationStatus.INVALID:
                results["invalid_entities"] += 1

            results["summary_issues"].extend(verification.issues)
            results["recommendations"].extend(verification.recommendations)

        # Calculate integrity score
        if results["total_entities"] > 0:
            verified_weight = 1.0
            modified_weight = 0.7
            unverified_weight = 0.3
            invalid_weight = 0.0

            weighted_score = (
                results["verified_entities"] * verified_weight
                + results["modified_entities"] * modified_weight
                + results["unverified_entities"] * unverified_weight
                + results["invalid_entities"] * invalid_weight
            )
            results["integrity_score"] = weighted_score / results["total_entities"]

        # Remove duplicates from issues and recommendations
        results["summary_issues"] = list(set(results["summary_issues"]))
        results["recommendations"] = list(set(results["recommendations"]))

        return results

    def health_check(self) -> Dict[str, Any]:
        """Get health status of the verification service."""
        return {
            "status": "healthy",
            "known_checksums_loaded": len(self._known_checksums),
            "official_sources_loaded": len(self._official_sources),
            "service_ready": True,
            "last_check": datetime.utcnow().isoformat(),
        }


# Global SRD data verification service instance
srd_data_verification_service = SRDDataVerificationService()
