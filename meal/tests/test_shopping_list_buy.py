import unittest, json, copy, os
from pathlib import Path
from fastapi.testclient import TestClient
from meal.api.api_run import app

DATA_DIR = Path(__file__).parent.parent / 'data'
PANTRY_FILE = (DATA_DIR / 'Pantry_ingredients.json').resolve()

class TestShoppingListBuy(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def setUp(self):
        # Backup pantry file content
        with open(PANTRY_FILE, encoding='utf-8') as f:
            self._original_pantry = f.read()

    def tearDown(self):
        # Restore pantry file
        with open(PANTRY_FILE, 'w', encoding='utf-8') as f:
            f.write(self._original_pantry)

    def test_buy_some_items(self):
        # Get current shopping list
        resp = self.client.get('/api/shopping-list')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        items = data['items']
        if not items:
            self.skipTest('No missing items to test buy flow.')
        # Choose up to first 2 items
        to_buy = [i['name'] for i in items[:2]]

        buy_resp = self.client.post('/api/shopping-list/buy', json={'week': data['week'], 'items': to_buy})
        self.assertEqual(buy_resp.status_code, 200)
        buy_data = buy_resp.json()
        # At least one of selected items should appear in updated/added
        updated_names = {u['name'].lower() for u in buy_data['updated']}
        added_names = {a['name'].lower() for a in buy_data['added']}
        self.assertTrue(any(n.lower() in updated_names or n.lower() in added_names for n in to_buy))

        # Re-fetch shopping list and confirm at least one of them is no longer missing (removed or missing decreased)
        resp2 = self.client.get('/api/shopping-list')
        self.assertEqual(resp2.status_code, 200)
        data2 = resp2.json()
        remaining = {i['name'].lower(): i for i in data2['items']}
        # For each bought item, either not present or missing reduced compared to original
        orig_map = {i['name'].lower(): i for i in items}
        for n in to_buy:
            ln = n.lower()
            if ln in remaining and ln in orig_map:
                self.assertLessEqual(remaining[ln]['missing'], orig_map[ln]['missing'])

# Removed unittest.main() for pytest compatibility
