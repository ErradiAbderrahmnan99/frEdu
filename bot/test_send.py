#!/usr/bin/env python3
"""
Unit tests for bot/send.py.
Covers:
- Command parsing (/add, /add mot = ma3na, /hard, /list)
- Accent-insensitive lookup
- 'word = meaning' parsing
- Due-date scheduling and stages
- HTML escaping
- Message splitting
- Ignoring messages from other chats
"""

import datetime
import html
import unittest

from bot.send import (
    INTERVALS,
    build_daily_message,
    calculate_due_date,
    escape_html,
    find_in_glossary,
    highlight_glossary_words,
    normalize_text,
    parse_commands,
    process_deck_review,
    split_telegram_message,
)


class TestTelegramBot(unittest.TestCase):

    def setUp(self):
        self.sample_stories = [
            {
                "id": 1,
                "title": "Le café du matin",
                "topic": "vie quotidienne",
                "text": "Youssef commande un café au lait bien chaud. Il demande l'addition au comptoir.",
                "glossary": [
                    {"word": "commande", "darija": "talabiya", "example": "Le serveur prend notre commande."},
                    {"word": "l'addition", "darija": "le-7ssab", "example": "Garçon, l'addition s'il vous plaît !"},
                    {"word": "détente", "darija": "ra7a", "example": "Un moment de détente."},
                ],
                "shadowing": ["Youssef commande un café au lait bien chaud."],
            },
            {
                "id": 2,
                "title": "Au bureau",
                "topic": "travail",
                "text": "Salma passe son entretien d'embauche avec une tenue sobre.",
                "glossary": [
                    {"word": "d'embauche", "darija": "dyal t-tawzif", "example": "Un entretien d'embauche."},
                    {"word": "sobre", "darija": "bassit", "example": "Une tenue sobre."},
                ],
                "shadowing": ["Salma passe son entretien d'embauche."],
            },
        ]
        self.today = "2026-11-19"
        self.target_chat = "12345678"

    def test_normalize_text(self):
        """Test accent-insensitive and casing normalization."""
        self.assertEqual(normalize_text("Déjà"), "deja")
        self.assertEqual(normalize_text("ÉLÉGANTE"), "elegante")
        self.assertEqual(normalize_text("côte d'ivoire"), "cote d'ivoire")
        self.assertEqual(normalize_text("   détente   "), "detente")
        self.assertEqual(normalize_text(""), "")
        self.assertEqual(normalize_text(None), "")

    def test_accent_insensitive_lookup(self):
        """Test looking up words with accents, uppercase, and elisions."""
        # Exact match
        item, found = find_in_glossary("commande", self.sample_stories)
        self.assertTrue(found)
        self.assertEqual(item["darija"], "talabiya")

        # Accent variation: "detente" for "détente"
        item, found = find_in_glossary("detente", self.sample_stories)
        self.assertTrue(found)
        self.assertEqual(item["darija"], "ra7a")

        # Case variation
        item, found = find_in_glossary("DÉTENTE", self.sample_stories)
        self.assertTrue(found)

        # Elision handling: "addition" vs "l'addition"
        item, found = find_in_glossary("addition", self.sample_stories)
        self.assertTrue(found)
        self.assertEqual(item["darija"], "le-7ssab")

        # Elision in query: "l'embauche" vs "d'embauche" / "embauche"
        item, found = find_in_glossary("embauche", self.sample_stories)
        self.assertTrue(found)
        self.assertEqual(item["darija"], "dyal t-tawzif")

        # Nonexistent word
        item, found = find_in_glossary("mot_inconnu", self.sample_stories)
        self.assertFalse(found)
        self.assertIsNone(item)

    def test_word_equals_meaning_parsing(self):
        """Test /add mot = ma3na parsing."""
        deck = []
        updates = [
            {
                "update_id": 101,
                "message": {
                    "chat": {"id": int(self.target_chat)},
                    "text": "/add cahier = defter",
                },
            },
            {
                "update_id": 102,
                "message": {
                    "chat": {"id": int(self.target_chat)},
                    "text": "/add stylo=stilo",
                },
            },
        ]
        added, not_found, hard, list_req, highest_id = parse_commands(
            updates, self.target_chat, self.sample_stories, deck, self.today
        )

        self.assertEqual(len(added), 2)
        self.assertEqual(added[0]["word"], "cahier")
        self.assertEqual(added[0]["darija"], "defter")
        self.assertEqual(added[0]["stage"], 0)
        self.assertEqual(added[0]["due"], "2026-11-20")  # +1 day

        self.assertEqual(added[1]["word"], "stylo")
        self.assertEqual(added[1]["darija"], "stilo")

        self.assertEqual(len(deck), 2)
        self.assertEqual(highest_id, 102)

    def test_comma_separated_add_parsing(self):
        """Test /add word1, word2, word3 parsing with glossary lookup and errors."""
        deck = []
        updates = [
            {
                "update_id": 201,
                "message": {
                    "chat": {"id": int(self.target_chat)},
                    "text": "/add commande, sobre, mot_imaginaire",
                },
            }
        ]
        added, not_found, hard, list_req, highest_id = parse_commands(
            updates, self.target_chat, self.sample_stories, deck, self.today
        )

        self.assertEqual(len(added), 2)
        words_added = [a["word"] for a in added]
        self.assertIn("commande", words_added)
        self.assertIn("sobre", words_added)

        self.assertEqual(len(not_found), 1)
        self.assertEqual(not_found[0], "mot_imaginaire")

        # Test duplicate ignore
        updates_dup = [
            {
                "update_id": 202,
                "message": {
                    "chat": {"id": int(self.target_chat)},
                    "text": "/add commande",
                },
            }
        ]
        added_dup, _, _, _, _ = parse_commands(
            updates_dup, self.target_chat, self.sample_stories, deck, self.today
        )
        self.assertEqual(len(added_dup), 0)
        self.assertEqual(len(deck), 2)

    def test_hard_and_list_commands(self):
        """Test /hard <word> and /list commands."""
        deck = [
            {"word": "terrasse", "darija": "terras", "stage": 3, "due": "2026-12-01", "mastered": False},
            {"word": "savoure", "darija": "kaytldded", "stage": 5, "due": "2026-10-01", "mastered": True},
        ]
        updates = [
            {
                "update_id": 301,
                "message": {
                    "chat": {"id": int(self.target_chat)},
                    "text": "/hard terrasse\n/list",
                },
            }
        ]
        added, not_found, hard, list_req, highest_id = parse_commands(
            updates, self.target_chat, self.sample_stories, deck, self.today
        )

        self.assertTrue(list_req)
        self.assertIn("terrasse", hard)
        self.assertEqual(deck[0]["stage"], 0)
        self.assertEqual(deck[0]["due"], self.today)
        self.assertFalse(deck[0]["mastered"])

    def test_ignoring_messages_from_other_chats(self):
        """Ensure updates from unauthorized chat IDs are strictly ignored."""
        deck = []
        updates = [
            {
                "update_id": 401,
                "message": {
                    "chat": {"id": 99999999},  # Intruder chat ID
                    "text": "/add commande = mot_pirate",
                },
            },
            {
                "update_id": 402,
                "message": {
                    "chat": {"id": int(self.target_chat)},
                    "text": "/add sobre",
                },
            },
        ]
        added, not_found, hard, list_req, highest_id = parse_commands(
            updates, self.target_chat, self.sample_stories, deck, self.today
        )

        # Only the authorized chat's command was processed
        self.assertEqual(len(added), 1)
        self.assertEqual(added[0]["word"], "sobre")
        self.assertEqual(len(deck), 1)
        self.assertEqual(highest_id, 402)

    def test_due_date_scheduling(self):
        """Test interval advancement: 1, 3, 7, 14, 30 days and mastered status."""
        today = "2026-11-19"
        deck = [
            {"word": "w0", "darija": "d0", "example": "ex0", "stage": 0, "due": "2026-11-19"},
            {"word": "w1", "darija": "d1", "example": "ex1", "stage": 1, "due": "2026-11-18"},  # overdue
            {"word": "w2", "darija": "d2", "example": "ex2", "stage": 4, "due": "2026-11-19"},  # final stage
            {"word": "w3", "darija": "d3", "example": "ex3", "stage": 2, "due": "2026-11-25"},  # future
        ]

        due_today = process_deck_review(deck, today)

        # 3 words should be due today (w0, w1, w2)
        due_words = [d["word"] for d in due_today]
        self.assertEqual(len(due_today), 3)
        self.assertIn("w0", due_words)
        self.assertIn("w1", due_words)
        self.assertIn("w2", due_words)
        self.assertNotIn("w3", due_words)

        # w0 was at stage 0 -> moves to stage 1, due in INTERVALS[1] = 3 days
        self.assertEqual(deck[0]["stage"], 1)
        self.assertEqual(deck[0]["due"], calculate_due_date(today, INTERVALS[1]))

        # w1 was at stage 1 -> moves to stage 2, due in INTERVALS[2] = 7 days
        self.assertEqual(deck[1]["stage"], 2)
        self.assertEqual(deck[1]["due"], calculate_due_date(today, INTERVALS[2]))

        # w2 was at stage 4 (30-day stage) -> mastered!
        self.assertEqual(deck[2]["stage"], 5)
        self.assertTrue(deck[2]["mastered"])

        # Second run today: mastered word should NOT be due
        due_second_round = process_deck_review(deck, today)
        self.assertEqual(len(due_second_round), 0)

    def test_html_escaping(self):
        """Test HTML escaping on user-provided strings and story text."""
        raw_user_input = "<script>alert('xss')</script> & \"injection\""
        escaped = escape_html(raw_user_input)
        self.assertNotIn("<script>", escaped)
        self.assertIn("&lt;script&gt;", escaped)
        self.assertIn("&amp;", escaped)

        # Story glossary bolding escaping
        glossary = [{"word": "café", "darija": "9ahwa", "example": "un café"}]
        text = "Youssef boit un café & regarde le soleil <chaud>."
        highlighted = highlight_glossary_words(text, glossary)
        self.assertIn("<b>café</b>", highlighted)
        self.assertIn("&amp;", highlighted)
        self.assertIn("&lt;chaud&gt;", highlighted)
        self.assertNotIn("<chaud>", highlighted)

    def test_message_splitting(self):
        """Test splitting large message into chunks <= max_len."""
        # Short message
        short_msg = "Hello World"
        chunks = split_telegram_message(short_msg, max_len=4000)
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0], short_msg)

        # Long message with paragraphs
        p1 = "A" * 2500
        p2 = "B" * 2500
        long_msg = f"{p1}\n\n{p2}"
        chunks = split_telegram_message(long_msg, max_len=4000)
        self.assertEqual(len(chunks), 2)
        self.assertEqual(chunks[0], p1)
        self.assertEqual(chunks[1], p2)
        for c in chunks:
            self.assertLessEqual(len(c), 4000)

        # Very long single line
        huge_line = "C" * 9000
        huge_chunks = split_telegram_message(huge_line, max_len=4000)
        self.assertEqual(len(huge_chunks), 3)
        for c in huge_chunks:
            self.assertLessEqual(len(c), 4000)


if __name__ == "__main__":
    unittest.main()
