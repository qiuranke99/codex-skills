"""Maintainer checks for the source catalog, never a research acceptance gate."""
from pathlib import Path
from urllib.parse import urlsplit
import copy
import json
import unittest

ROOT = Path(__file__).resolve().parents[1]


def validate_catalog(catalog):
    families = catalog['families']
    sources = catalog['sources']
    if not families or not sources:
        raise ValueError('Empty source catalog')
    family_ids = [row['family_id'] for row in families]
    source_ids = [row['source_id'] for row in sources]
    if len(set(family_ids)) != len(family_ids) or len(set(source_ids)) != len(source_ids):
        raise ValueError('Duplicate catalog identity')
    for source in sources:
        if source['family_id'] not in family_ids:
            raise ValueError('Unknown source family')
        url = urlsplit(source['canonical_url'])
        if url.scheme not in ('http', 'https') or not url.hostname or url.username or url.password:
            raise ValueError('Invalid public source URL')
        if not source['display_name'].strip() or not source['modalities']:
            raise ValueError('Missing source name or modality')
        if set(source['modalities']) - {'image', 'video'}:
            raise ValueError('Unknown modality')
        for fallback in source.get('fallback_source_ids', []):
            if fallback not in source_ids:
                raise ValueError('Missing fallback source')


class CatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = json.loads((ROOT/'references/source_registry.json').read_text(encoding='utf-8'))

    def test_catalog_integrity(self):
        validate_catalog(self.catalog)

    def test_duplicate_source_rejected(self):
        data = copy.deepcopy(self.catalog)
        data['sources'].append(data['sources'][0])
        with self.assertRaises(ValueError):
            validate_catalog(data)

    def test_missing_family_rejected(self):
        data = copy.deepcopy(self.catalog)
        data['sources'][0]['family_id'] = 'missing'
        with self.assertRaises(ValueError):
            validate_catalog(data)

    def test_missing_fallback_rejected(self):
        data = copy.deepcopy(self.catalog)
        data['sources'][0]['fallback_source_ids'] = ['missing']
        with self.assertRaises(ValueError):
            validate_catalog(data)

    def test_credential_url_rejected(self):
        data = copy.deepcopy(self.catalog)
        data['sources'][0]['canonical_url'] = 'https://user:password@example.com/'
        with self.assertRaises(ValueError):
            validate_catalog(data)


if __name__ == '__main__':
    unittest.main()
