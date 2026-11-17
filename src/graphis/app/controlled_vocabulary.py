# Copyright (C) 2026 Martin Wieser, Geert Verhoeven
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

TARGET_REGION_ROLE = "rRole"
TARGET_REGION_TYPE = "rCtype"
TARGET_CONTRIBUTOR_ROLE = "XMP-iptcExt:Contributor/role"
SUPPORTED_TARGETS = (TARGET_REGION_ROLE, TARGET_REGION_TYPE, TARGET_CONTRIBUTOR_ROLE)
TARGET_LABELS = {
    TARGET_REGION_ROLE: "Region Role (rRole)",
    TARGET_REGION_TYPE: "Region Content Type (rCtype)",
    TARGET_CONTRIBUTOR_ROLE: "Contributor Role",
}
VOCABULARY_SCHEMA = "graphis-controlled-vocabulary"
VOCABULARY_VERSION = 1

SOURCE_GRAPHIS = "GRAPHIS configured"
SOURCE_IMAGE_METADATA = "From image metadata"
SOURCE_CUSTOM = "Custom terms"
SOURCE_EXPORT = "GRAPHIS controlled vocabularies"
SOURCE_IPTC_ROLE = "IPTC Image Region Role"
SOURCE_IPTC_TYPE = "IPTC Image Region Type"


@dataclass(frozen=True)
class VocabularyTerm:
    target: str
    source: str
    name: str
    identifier: str
    qcode: str = ""
    definition: str = ""

    @property
    def display_name(self) -> str:
        if self.source == SOURCE_GRAPHIS:
            return self.name
        return f"{self.name} ({self.source})"

    def matches(self, text: str) -> bool:
        query = text.casefold().strip()
        if not query:
            return True
        haystack = " ".join((self.source, self.name, self.identifier, self.qcode, self.definition)).casefold()
        return query in haystack


@dataclass(frozen=True)
class VocabularyRefreshResult:
    terms: list[VocabularyTerm]
    refreshed: bool
    message: str = ""


IPTC_SCHEMES = {
    TARGET_REGION_ROLE: {
        "source": SOURCE_IPTC_ROLE,
        "url": "https://cv.iptc.org/newscodes/imageregionrole/?format=json&lang=en-GB",
        "scheme_uri": "http://cv.iptc.org/newscodes/imageregionrole/",
        "prefix": "imgregrole",
    },
    TARGET_REGION_TYPE: {
        "source": SOURCE_IPTC_TYPE,
        "url": "https://cv.iptc.org/newscodes/imageregiontype/?format=json&lang=en-GB",
        "scheme_uri": "http://cv.iptc.org/newscodes/imageregiontype/",
        "prefix": "imgregtype",
    },
}


IPTC_FALLBACK_TERMS = {
    TARGET_REGION_ROLE: (
        VocabularyTerm(
            TARGET_REGION_ROLE,
            SOURCE_IPTC_ROLE,
            "cropping",
            "http://cv.iptc.org/newscodes/imageregionrole/cropping",
            "imgregrole:cropping",
            "Image region can be used for any cropping",
        ),
        VocabularyTerm(
            TARGET_REGION_ROLE,
            SOURCE_IPTC_ROLE,
            "recommended cropping",
            "http://cv.iptc.org/newscodes/imageregionrole/recomCropping",
            "imgregrole:recomCropping",
            "Image region is recommended for cropping",
        ),
        VocabularyTerm(
            TARGET_REGION_ROLE,
            SOURCE_IPTC_ROLE,
            "landscape format cropping",
            "http://cv.iptc.org/newscodes/imageregionrole/landscapeCropping",
            "imgregrole:landscapeCropping",
            "Image region suggested for cropping in landscape format",
        ),
        VocabularyTerm(
            TARGET_REGION_ROLE,
            SOURCE_IPTC_ROLE,
            "portrait format cropping",
            "http://cv.iptc.org/newscodes/imageregionrole/portraitCropping",
            "imgregrole:portraitCropping",
            "Image region suggested for cropping in portrait format",
        ),
        VocabularyTerm(
            TARGET_REGION_ROLE,
            SOURCE_IPTC_ROLE,
            "square format cropping",
            "http://cv.iptc.org/newscodes/imageregionrole/squareCropping",
            "imgregrole:squareCropping",
            "Image region suggested for cropping in square format",
        ),
        VocabularyTerm(
            TARGET_REGION_ROLE,
            SOURCE_IPTC_ROLE,
            "composite image item",
            "http://cv.iptc.org/newscodes/imageregionrole/compositeImageItem",
            "imgregrole:compositeImageItem",
            "Image region of an item in a composite image",
        ),
        VocabularyTerm(
            TARGET_REGION_ROLE,
            SOURCE_IPTC_ROLE,
            "copyright region",
            "http://cv.iptc.org/newscodes/imageregionrole/copyrightRegion",
            "imgregrole:copyrightRegion",
            "Image region with a copyright different from the copyright of the whole picture",
        ),
        VocabularyTerm(
            TARGET_REGION_ROLE,
            SOURCE_IPTC_ROLE,
            "subject area",
            "http://cv.iptc.org/newscodes/imageregionrole/subjectArea",
            "imgregrole:subjectArea",
            "Image region contains a subject in the overall scene.",
        ),
        VocabularyTerm(
            TARGET_REGION_ROLE,
            SOURCE_IPTC_ROLE,
            "main subject area",
            "http://cv.iptc.org/newscodes/imageregionrole/mainSubjectArea",
            "imgregrole:mainSubjectArea",
            "Image region contains the main subject in the overall scene.",
        ),
        VocabularyTerm(
            TARGET_REGION_ROLE,
            SOURCE_IPTC_ROLE,
            "area of interest",
            "http://cv.iptc.org/newscodes/imageregionrole/areaOfInterest",
            "imgregrole:areaOfInterest",
            "Image region contains a thing of special interest to the viewer",
        ),
        VocabularyTerm(
            TARGET_REGION_ROLE,
            SOURCE_IPTC_ROLE,
            "anonymised",
            "http://cv.iptc.org/newscodes/imageregionrole/anonymised",
            "imgregrole:anonymised",
            "Image region obfuscates a person or object which should not be identifiable by this image",
        ),
        VocabularyTerm(
            TARGET_REGION_ROLE,
            SOURCE_IPTC_ROLE,
            "recommended anonymisation",
            "http://cv.iptc.org/newscodes/imageregionrole/recommendedAnonymisation",
            "imgregrole:recommendedAnonymisation",
            "Image Region should obfuscate a person or object in an upcoming workflow step",
        ),
        VocabularyTerm(
            TARGET_REGION_ROLE,
            SOURCE_IPTC_ROLE,
            "business use",
            "http://cv.iptc.org/newscodes/imageregionrole/businessUse",
            "imgregrole:businessUse",
            "Image region is dedicated to a specific business use",
        ),
    ),
    TARGET_REGION_TYPE: (
        VocabularyTerm(
            TARGET_REGION_TYPE,
            SOURCE_IPTC_TYPE,
            "animal",
            "http://cv.iptc.org/newscodes/imageregiontype/animal",
            "imgregtype:animal",
            "A living organism different from humans or flora",
        ),
        VocabularyTerm(
            TARGET_REGION_TYPE,
            SOURCE_IPTC_TYPE,
            "artwork",
            "http://cv.iptc.org/newscodes/imageregiontype/artwork",
            "imgregtype:artwork",
            "Artistic work",
        ),
        VocabularyTerm(
            TARGET_REGION_TYPE,
            SOURCE_IPTC_TYPE,
            "dividing line",
            "http://cv.iptc.org/newscodes/imageregiontype/dividingLine",
            "imgregtype:dividingLine",
            "A line expressing a visual division of the image, such as a horizon",
        ),
        VocabularyTerm(
            TARGET_REGION_TYPE,
            SOURCE_IPTC_TYPE,
            "plant",
            "http://cv.iptc.org/newscodes/imageregiontype/plant",
            "imgregtype:plant",
            "A living organism different from humans and animals",
        ),
        VocabularyTerm(
            TARGET_REGION_TYPE,
            SOURCE_IPTC_TYPE,
            "geographic area",
            "http://cv.iptc.org/newscodes/imageregiontype/geoArea",
            "imgregtype:geoArea",
            "A named area on the surface of the planet earth",
        ),
        VocabularyTerm(
            TARGET_REGION_TYPE,
            SOURCE_IPTC_TYPE,
            "graphic",
            "http://cv.iptc.org/newscodes/imageregiontype/graphic",
            "imgregtype:graphic",
            "A graphic representation of information",
        ),
        VocabularyTerm(
            TARGET_REGION_TYPE,
            SOURCE_IPTC_TYPE,
            "machine-readable code",
            "http://cv.iptc.org/newscodes/imageregiontype/machineCode",
            "imgregtype:machineCode",
            "Optical label such as barcode or QR code",
        ),
        VocabularyTerm(
            TARGET_REGION_TYPE,
            SOURCE_IPTC_TYPE,
            "human",
            "http://cv.iptc.org/newscodes/imageregiontype/human",
            "imgregtype:human",
            "A human being",
        ),
        VocabularyTerm(
            TARGET_REGION_TYPE,
            SOURCE_IPTC_TYPE,
            "product",
            "http://cv.iptc.org/newscodes/imageregiontype/product",
            "imgregtype:product",
            "A thing that was produced and can be handed over",
        ),
        VocabularyTerm(
            TARGET_REGION_TYPE,
            SOURCE_IPTC_TYPE,
            "text",
            "http://cv.iptc.org/newscodes/imageregiontype/text",
            "imgregtype:text",
            "Human readable script of any language",
        ),
        VocabularyTerm(
            TARGET_REGION_TYPE,
            SOURCE_IPTC_TYPE,
            "building",
            "http://cv.iptc.org/newscodes/imageregiontype/building",
            "imgregtype:building",
            "A structure with walls and roof in most cases",
        ),
        VocabularyTerm(
            TARGET_REGION_TYPE,
            SOURCE_IPTC_TYPE,
            "vehicle",
            "http://cv.iptc.org/newscodes/imageregiontype/vehicle",
            "imgregtype:vehicle",
            "An object used for transporting something, like car, train, ship, plane or bike",
        ),
        VocabularyTerm(
            TARGET_REGION_TYPE,
            SOURCE_IPTC_TYPE,
            "food",
            "http://cv.iptc.org/newscodes/imageregiontype/food",
            "imgregtype:food",
            "Substances providing nutrition for a living body",
        ),
        VocabularyTerm(
            TARGET_REGION_TYPE,
            SOURCE_IPTC_TYPE,
            "clothing",
            "http://cv.iptc.org/newscodes/imageregiontype/clothing",
            "imgregtype:clothing",
            "Something worn to cover the body",
        ),
        VocabularyTerm(
            TARGET_REGION_TYPE,
            SOURCE_IPTC_TYPE,
            "rock formation",
            "http://cv.iptc.org/newscodes/imageregiontype/rockFormation",
            "imgregtype:rockFormation",
            "A special formation of stone mass",
        ),
        VocabularyTerm(
            TARGET_REGION_TYPE,
            SOURCE_IPTC_TYPE,
            "body of water",
            "http://cv.iptc.org/newscodes/imageregiontype/bodyOfWater",
            "imgregtype:bodyOfWater",
            "A significant accumulation of water",
        ),
    ),
}


class ControlledVocabularyStore:
    def __init__(self, cache_dir: Path):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._graphis_terms: dict[str, list[VocabularyTerm]] = {
            TARGET_REGION_ROLE: [],
            TARGET_REGION_TYPE: [],
            TARGET_CONTRIBUTOR_ROLE: [],
        }
        self._metadata_terms: dict[str, list[VocabularyTerm]] = {
            TARGET_REGION_ROLE: [],
            TARGET_REGION_TYPE: [],
            TARGET_CONTRIBUTOR_ROLE: [],
        }
        self._custom_terms = self._load_custom_terms()
        self._removed_term_keys = self._load_removed_term_keys()

    def set_graphis_terms(self, terms: list[VocabularyTerm]):
        grouped = {target: [] for target in SUPPORTED_TARGETS}
        for term in terms:
            if term.target in grouped:
                grouped[term.target].append(term)
        self._graphis_terms = {target: _unique_terms(items) for target, items in grouped.items()}

    def ensure_metadata_term(self, target: str, name: str, identifier: str) -> VocabularyTerm:
        term = self.find(target, name=name, identifier=identifier)
        if term is not None:
            return term
        term = VocabularyTerm(target, SOURCE_IMAGE_METADATA, name or identifier, identifier, "", "")
        self._metadata_terms[target] = _unique_terms([*self._metadata_terms.get(target, []), term])
        return term

    def terms(self, target: str, include_iptc: bool = True) -> list[VocabularyTerm]:
        terms = [
            *self._graphis_terms.get(target, []),
            *self._custom_terms.get(target, []),
            *self._metadata_terms.get(target, []),
        ]
        if include_iptc and target in IPTC_SCHEMES:
            terms.extend(load_iptc_terms(target, self.cache_dir, refresh=False))
        return [term for term in _unique_terms(terms) if not self._is_removed(term)]

    def refresh_iptc_terms(self, target: str) -> VocabularyRefreshResult:
        if target not in IPTC_SCHEMES:
            return VocabularyRefreshResult([], False, "No IPTC vocabulary is configured for this target.")
        return refresh_iptc_terms(target, self.cache_dir)

    def custom_terms(self, target: str) -> list[VocabularyTerm]:
        return list(self._custom_terms.get(target, []))

    def set_custom_terms(self, target: str, terms: list[VocabularyTerm]):
        self._custom_terms[target] = _unique_terms(
            [self._custom_term(term) for term in terms if term.name and term.identifier]
        )
        self._write_custom_terms()

    def add_custom_term(self, term: VocabularyTerm) -> VocabularyTerm:
        custom_term = self._custom_term(term)
        existing_terms = [
            item
            for item in self._custom_terms.get(custom_term.target, [])
            if _normalize_identifier(item.identifier) != _normalize_identifier(custom_term.identifier)
        ]
        self._custom_terms[custom_term.target] = _unique_terms([*existing_terms, custom_term])
        self._removed_term_keys.discard(_term_key(custom_term))
        self._write_custom_terms()
        self._write_removed_term_keys()
        return custom_term

    def remove_term(self, term: VocabularyTerm):
        self._removed_term_keys.add(_term_key(term))
        if term.source == SOURCE_CUSTOM:
            self._custom_terms[term.target] = [
                item
                for item in self._custom_terms.get(term.target, [])
                if _normalize_identifier(item.identifier) != _normalize_identifier(term.identifier)
            ]
            self._write_custom_terms()
        if term.source == SOURCE_IMAGE_METADATA:
            self._metadata_terms[term.target] = [
                item
                for item in self._metadata_terms.get(term.target, [])
                if _normalize_identifier(item.identifier) != _normalize_identifier(term.identifier)
            ]
        self._write_removed_term_keys()

    def clear_user_terms(self):
        self._custom_terms = {target: [] for target in SUPPORTED_TARGETS}
        self._metadata_terms = {target: [] for target in SUPPORTED_TARGETS}
        self._removed_term_keys = set()
        self._write_custom_terms()
        self._write_removed_term_keys()

    def export_user_terms(self, path: Path) -> int:
        terms = []
        for target in SUPPORTED_TARGETS:
            terms.extend(self.terms(target))
        terms = _unique_terms(terms)
        _write_terms(Path(path), terms, SOURCE_EXPORT)
        return len(terms)

    def import_custom_terms(self, path: Path) -> int:
        imported_terms = []
        for term in _read_terms(Path(path)):
            if term.target not in SUPPORTED_TARGETS:
                continue
            existing = self.find(term.target, name=term.name, identifier=term.identifier)
            if existing is not None and existing.source != SOURCE_CUSTOM:
                continue
            imported_terms.append(self._custom_term(term))
        for term in imported_terms:
            self.add_custom_term(term)
        return len(imported_terms)

    def find(self, target: str, name: str = "", identifier: str = "") -> VocabularyTerm | None:
        name_key = name.casefold().strip()
        identifier_key = _normalize_identifier(identifier)
        for term in self.terms(target):
            if identifier_key and _normalize_identifier(term.identifier) == identifier_key:
                return term
            if name_key and term.name.casefold().strip() == name_key:
                return term
        return None

    def _custom_term(self, term: VocabularyTerm) -> VocabularyTerm:
        return VocabularyTerm(
            term.target,
            SOURCE_CUSTOM,
            term.name.strip(),
            term.identifier.strip(),
            term.qcode.strip(),
            term.definition.strip(),
        )

    def _load_custom_terms(self) -> dict[str, list[VocabularyTerm]]:
        grouped = {target: [] for target in SUPPORTED_TARGETS}
        for term in _read_terms(self.cache_dir / "custom_terms.json", SOURCE_CUSTOM):
            if term.target in grouped:
                grouped[term.target].append(self._custom_term(term))
        return {target: _unique_terms(terms) for target, terms in grouped.items()}

    def _write_custom_terms(self):
        terms = []
        for target in SUPPORTED_TARGETS:
            terms.extend(self._custom_terms.get(target, []))
        _write_terms(self.cache_dir / "custom_terms.json", _unique_terms(terms), SOURCE_CUSTOM)

    def _is_removed(self, term: VocabularyTerm) -> bool:
        return _term_key(term) in self._removed_term_keys

    def _load_removed_term_keys(self) -> set[str]:
        cache_file = self.cache_dir / "removed_terms.json"
        if not cache_file.exists():
            return set()
        try:
            values = json.loads(cache_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return set()
        return {str(value) for value in values if value}

    def _write_removed_term_keys(self):
        cache_file = self.cache_dir / "removed_terms.json"
        cache_file.write_text(
            json.dumps(sorted(self._removed_term_keys), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )


def graphis_role_term(name: str, identifier: str) -> VocabularyTerm:
    return VocabularyTerm(TARGET_REGION_ROLE, SOURCE_GRAPHIS, name, identifier)


def graphis_type_term(name: str, identifier: str) -> VocabularyTerm:
    return VocabularyTerm(TARGET_REGION_TYPE, SOURCE_GRAPHIS, name, identifier)


def graphis_contributor_role_term(name: str, identifier: str) -> VocabularyTerm:
    return VocabularyTerm(TARGET_CONTRIBUTOR_ROLE, SOURCE_GRAPHIS, name, identifier)


def load_iptc_terms(target: str, cache_dir: Path, refresh: bool = False) -> list[VocabularyTerm]:
    cache_file = Path(cache_dir) / f"iptc_{target}.json"
    if not refresh:
        cached = _read_terms(cache_file, IPTC_SCHEMES[target]["source"])
        if cached:
            return cached

    if refresh:
        return refresh_iptc_terms(target, cache_dir).terms

    return list(IPTC_FALLBACK_TERMS.get(target, ()))


def refresh_iptc_terms(target: str, cache_dir: Path) -> VocabularyRefreshResult:
    cache_file = Path(cache_dir) / f"iptc_{target}.json"
    try:
        terms = _download_iptc_terms(target)
    except (HTTPError, URLError, TimeoutError, OSError, json.JSONDecodeError, ValueError) as exc:
        cached = _read_terms(cache_file, IPTC_SCHEMES[target]["source"])
        if cached:
            return VocabularyRefreshResult(cached, False, f"IPTC refresh failed; using cached terms. {exc}")
        fallback = list(IPTC_FALLBACK_TERMS.get(target, ()))
        return VocabularyRefreshResult(fallback, False, f"IPTC refresh failed; using bundled fallback terms. {exc}")
    _write_terms(cache_file, terms, IPTC_SCHEMES[target]["source"])
    return VocabularyRefreshResult(terms, True, "IPTC terms refreshed.")


def _download_iptc_terms(target: str) -> list[VocabularyTerm]:
    scheme = IPTC_SCHEMES[target]
    request = Request(
        scheme["url"],
        headers={
            "Accept": "application/json",
            "User-Agent": "GRAPHIS controlled vocabulary updater",
        },
    )
    with urlopen(request, timeout=15) as response:
        raw_data = response.read().decode("utf-8")
    payload = json.loads(raw_data)
    terms = _parse_iptc_json(target, payload)
    if not terms:
        raise ValueError("No IPTC terms found")
    return terms


def _parse_iptc_json(target: str, payload) -> list[VocabularyTerm]:
    scheme = IPTC_SCHEMES[target]
    if isinstance(payload, dict):
        records = payload.get("conceptSet") or payload.get("@graph") or payload.get("hasTopConcept") or []
    else:
        records = payload
    if not isinstance(records, list):
        return []

    terms = []
    for record in records:
        if not isinstance(record, dict):
            continue
        identifier = _text(record.get("uri") or record.get("@id") or record.get("id"))
        if not identifier.startswith(scheme["scheme_uri"]):
            continue
        if identifier.rstrip("/") == scheme["scheme_uri"].rstrip("/"):
            continue
        name = _literal_text(
            record.get("prefLabel") or record.get("skos:prefLabel") or record.get("name") or record.get("label")
        )
        if not name:
            continue
        definition = _literal_text(record.get("definition") or record.get("skos:definition"))
        qcode = _text(record.get("qcode") or record.get("QCode"))
        if not qcode:
            qcode = f"{scheme['prefix']}:{identifier.rsplit('/', 1)[-1]}"
        terms.append(VocabularyTerm(target, scheme["source"], name, identifier, qcode, definition))
    return _unique_terms(terms)


def _literal_text(value) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, list):
        for item in value:
            text = _literal_text(item)
            if text:
                return text
    if isinstance(value, dict):
        for key in ("@value", "value", "en-GB", "en", "label", "name"):
            text = _literal_text(value.get(key))
            if text:
                return text
    return ""


def _text(value) -> str:
    return str(value).strip() if value is not None else ""


def _read_terms(cache_file: Path, source: str = SOURCE_CUSTOM) -> list[VocabularyTerm]:
    if not cache_file.exists():
        return []
    try:
        payload = json.loads(cache_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    if not isinstance(payload, dict):
        return []
    raw_terms = payload.get("terms", [])
    if not isinstance(raw_terms, list):
        return []
    term_source = _text(payload.get("source")) or source
    terms = []
    for item in raw_terms:
        if not isinstance(item, dict):
            continue
        target = _text(item.get("target"))
        name = _text(item.get("name"))
        identifier = _text(item.get("identifier"))
        if target not in SUPPORTED_TARGETS or not name or not identifier:
            continue
        terms.append(
            VocabularyTerm(
                target,
                _text(item.get("source")) or term_source,
                name,
                identifier,
                _text(item.get("qcode")),
                _text(item.get("definition")),
            )
        )
    return _unique_terms(terms)


def _write_terms(cache_file: Path, terms: list[VocabularyTerm], source: str = SOURCE_CUSTOM):
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema": VOCABULARY_SCHEMA,
        "version": VOCABULARY_VERSION,
        "source": source,
        "terms": [
            _term_json(term, source)
            for term in terms
            if term.target in SUPPORTED_TARGETS and term.name and term.identifier
        ],
    }
    cache_file.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def _term_json(term: VocabularyTerm, source: str) -> dict[str, str]:
    data = {
        "target": term.target,
        "name": term.name,
        "identifier": term.identifier,
        "qcode": term.qcode,
        "definition": term.definition,
    }
    if term.source and term.source != source:
        data["source"] = term.source
    return data


def _unique_terms(terms: list[VocabularyTerm]) -> list[VocabularyTerm]:
    seen = set()
    unique = []
    for term in terms:
        key = (term.target, _normalize_identifier(term.identifier), term.name.casefold().strip(), term.source)
        if key in seen:
            continue
        seen.add(key)
        unique.append(term)
    return unique


def _term_key(term: VocabularyTerm) -> str:
    identifier = _normalize_identifier(term.identifier)
    if identifier:
        return f"{term.target}|{identifier}"
    return f"{term.target}|name:{term.name.casefold().strip()}"


def _normalize_identifier(identifier: str) -> str:
    return (identifier or "").strip().replace("https://cv.iptc.org/", "http://cv.iptc.org/").rstrip("/")
