#!/usr/bin/env python3
"""
Daily Telegram French Learning Bot for Moroccan Learners.
Standard library only (urllib, json, re, unicodedata, datetime, html).
"""

import argparse
import datetime
import html
import json
import os
import re
import sys
import unicodedata
import urllib.error
import urllib.parse
import urllib.request

INTERVALS = [1, 3, 7, 14, 30]  # Spaced repetition intervals in days


def normalize_text(text):
    """Normalize text by lowercasing and removing diacritics / accents."""
    if not text:
        return ""
    text = text.strip().lower()
    # Decompose unicode characters into base letters + combining marks
    nfd = unicodedata.normalize("NFD", text)
    # Remove combining marks
    cleaned = "".join(c for c in nfd if unicodedata.category(c) != "Mn")
    return cleaned


def find_in_glossary(query_word, stories):
    """
    Search for a word in all story glossaries (case- and accent-insensitive).
    Returns (word_dict, matched) or (None, False).
    """
    norm_query = normalize_text(query_word)
    if not norm_query:
        return None, False

    for story in stories:
        for item in story.get("glossary", []):
            item_word = item.get("word", "")
            # Direct normalized equality
            if normalize_text(item_word) == norm_query:
                return item, True
            # Check with elision removed (e.g. "l'addition" -> "addition")
            clean_item_word = re.sub(r"^[ldl]['’]", "", item_word.strip(), flags=re.IGNORECASE)
            if normalize_text(clean_item_word) == norm_query:
                return item, True
            # Check if query had elision removed
            clean_query = re.sub(r"^[ldl]['’]", "", query_word.strip(), flags=re.IGNORECASE)
            if normalize_text(clean_query) == normalize_text(item_word):
                return item, True

    return None, False


def escape_html(text):
    """Safely escape HTML entities."""
    return html.escape(str(text), quote=False)


def highlight_glossary_words(text, glossary):
    """
    Bold occurrences of glossary words in the story text.
    Handles HTML escaping properly so existing text is escaped
    and glossary occurrences are wrapped in <b>...</b> without collisions.
    """
    if not glossary or not text:
        return escape_html(text)

    # Sort glossary words by length descending so longer phrases match first
    words_to_match = []
    for g in glossary:
        w = g.get("word", "").strip()
        if w:
            words_to_match.append(w)
            # Also add without leading l' or d' if present
            without_elision = re.sub(r"^[ldl]['’]", "", w, flags=re.IGNORECASE).strip()
            if without_elision and without_elision != w:
                words_to_match.append(without_elision)

    # Deduplicate and sort descending by length
    words_to_match = sorted(list(set(words_to_match)), key=len, reverse=True)

    if not words_to_match:
        return escape_html(text)

    # Build regex pattern with word boundaries where applicable
    escaped_patterns = []
    for w in words_to_match:
        pattern = re.escape(w)
        escaped_patterns.append(r"\b" + pattern + r"\b")

    combined_regex = re.compile("(" + "|".join(escaped_patterns) + ")", re.IGNORECASE)

    parts = []
    last_idx = 0
    for match in combined_regex.finditer(text):
        start, end = match.span()
        # Non-matched preceding text
        if start > last_idx:
            parts.append(escape_html(text[last_idx:start]))
        # Matched word
        parts.append(f"<b>{escape_html(match.group(0))}</b>")
        last_idx = end

    if last_idx < len(text):
        parts.append(escape_html(text[last_idx:]))

    return "".join(parts)


def parse_commands(updates, target_chat_id, stories, deck, today_str):
    """
    Parse updates from Telegram:
    - /add word1, word2, word3
    - /add mot = ma3na
    - /hard word
    - /list

    Filters messages strictly by target_chat_id.
    Returns:
      added_words: list of dicts {word, darija, example}
      not_found_words: list of words
      hard_words: list of words reset
      list_requested: bool
      highest_update_id: int or None
    """
    added_words = []
    not_found_words = []
    hard_words = []
    list_requested = False
    highest_update_id = None

    # Track normalized words currently in deck (active or mastered)
    deck_norm_words = {normalize_text(item["word"]): item for item in deck}

    for update in updates:
        up_id = update.get("update_id")
        if up_id is not None:
            if highest_update_id is None or up_id > highest_update_id:
                highest_update_id = up_id

        msg = update.get("message") or update.get("edited_message")
        if not msg:
            continue

        chat = msg.get("chat", {})
        sender_chat_id = str(chat.get("id", ""))
        if sender_chat_id != str(target_chat_id):
            # Ignore messages from other chats
            continue

        raw_text = msg.get("text", "").strip()
        if not raw_text.startswith("/"):
            continue

        lines = raw_text.splitlines()
        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Command: /list
            if line.startswith("/list"):
                list_requested = True
                continue

            # Command: /hard <word>
            if line.startswith("/hard"):
                param = line[len("/hard"):].strip()
                if param:
                    norm_p = normalize_text(param)
                    if norm_p in deck_norm_words:
                        entry = deck_norm_words[norm_p]
                        entry["stage"] = 0
                        entry["due"] = today_str  # Due immediately for review
                        entry["mastered"] = False
                        hard_words.append(entry["word"])
                continue

            # Command: /add
            if line.startswith("/add"):
                content = line[len("/add"):].strip()
                if not content:
                    continue

                # Case A: /add mot = ma3na
                if "=" in content:
                    parts = content.split("=", 1)
                    mot = parts[0].strip()
                    ma3na = parts[1].strip()
                    if mot and ma3na:
                        norm_m = normalize_text(mot)
                        if norm_m not in deck_norm_words:
                            new_entry = {
                                "word": mot,
                                "darija": ma3na,
                                "example": "",
                                "stage": 0,
                                "due": calculate_due_date(today_str, INTERVALS[0]),
                                "mastered": False,
                            }
                            deck.append(new_entry)
                            deck_norm_words[norm_m] = new_entry
                            added_words.append(new_entry)
                    continue

                # Case B: /add word1, word2, word3
                raw_words = [w.strip() for w in content.split(",") if w.strip()]
                for w in raw_words:
                    norm_w = normalize_text(w)
                    if not norm_w:
                        continue
                    if norm_w in deck_norm_words:
                        # Ignore duplicates
                        continue

                    # Lookup in glossaries
                    matched_item, found = find_in_glossary(w, stories)
                    if found:
                        new_entry = {
                            "word": matched_item.get("word", w),
                            "darija": matched_item.get("darija", ""),
                            "example": matched_item.get("example", ""),
                            "stage": 0,
                            "due": calculate_due_date(today_str, INTERVALS[0]),
                            "mastered": False,
                        }
                        deck.append(new_entry)
                        deck_norm_words[norm_w] = new_entry
                        added_words.append(new_entry)
                    else:
                        not_found_words.append(w)

    return added_words, not_found_words, hard_words, list_requested, highest_update_id


def calculate_due_date(from_date_str, days):
    """Return YYYY-MM-DD date after `days` from from_date_str."""
    dt = datetime.datetime.strptime(from_date_str, "%Y-%m-%d").date()
    new_dt = dt + datetime.timedelta(days=days)
    return new_dt.strftime("%Y-%m-%d")


def process_deck_review(deck, today_str):
    """
    Find words that are due today or overdue.
    Move them to next stage and set next due date.
    If stage was 4 (the 30-day stage), mark as mastered and remove from future reviews.
    Returns list of review entries shown today: [{word, darija, example, stage}].
    """
    due_today = []
    for entry in deck:
        if entry.get("mastered", False):
            continue

        due_date = entry.get("due", today_str)
        if due_date <= today_str:
            # Word is due for review today
            current_stage = entry.get("stage", 0)
            due_today.append({
                "word": entry.get("word"),
                "darija": entry.get("darija"),
                "example": entry.get("example", ""),
                "stage": current_stage,
            })

            # Advance stage
            if current_stage >= 4:
                # Mastered after completing 30-day stage
                entry["stage"] = 5
                entry["mastered"] = True
            else:
                next_stage = current_stage + 1
                entry["stage"] = next_stage
                entry["due"] = calculate_due_date(today_str, INTERVALS[next_stage])

    return due_today


def build_daily_message(
    current_day,
    total_stories,
    story,
    app_url,
    due_words,
    added_words,
    not_found_words,
    hard_words,
    list_requested,
    deck,
    looped_note=False,
):
    """
    Build the formatted Telegram daily message in HTML.
    Properly escapes all user-supplied text.
    """
    title = story.get("title", f"Histoire {current_day}")
    text = story.get("text", "")
    glossary = story.get("glossary", [])

    highlighted_story = highlight_glossary_words(text, glossary)

    sections = []

    # Looped celebration note if story 30 was completed
    if looped_note:
        sections.append("🎉 <b>Kmmlti 30 9issa! Zid 9isas jdad f stories.json</b>\n")

    # 1. Story of the day
    clean_app_url = app_url.rstrip("/")
    header = f"📖 <b>9issa dyal lyoum ({current_day}/{total_stories}): {escape_html(title)}</b>"
    story_section = f"{header}\n\n{highlighted_story}\n\n🔗 <b>Sma3ha w dir shadowing:</b> {clean_app_url}?day={current_day}"
    sections.append(story_section)

    # 2. Review of the day
    review_lines = ["🔁 <b>Révision dyal lyoum:</b>"]
    if due_words:
        for item in due_words:
            w_esc = escape_html(item['word'])
            d_esc = escape_html(item['darija'])
            line = f"• <b>{w_esc}</b> → <tg-spoiler>{d_esc}</tg-spoiler>"
            if item.get("example"):
                line += f"\n  <i>{escape_html(item['example'])}</i>"
            review_lines.append(line)
    else:
        review_lines.append("<i>Ma 3ndek 7ta kelma f r-révision lyoum!</i>")
    sections.append("\n".join(review_lines))

    # 3. Confirmations of additions, errors, and hard resets
    feedback_lines = []
    if added_words:
        feedback_lines.append("✅ <b>Kelmat tzadou l-deck:</b>")
        for item in added_words:
            feedback_lines.append(f"• <b>{escape_html(item['word'])}</b>: {escape_html(item['darija'])}")

    if hard_words:
        feedback_lines.append("🔄 <b>Kelmat t-resetaw l-stage 0:</b>")
        for hw in hard_words:
            feedback_lines.append(f"• <b>{escape_html(hw)}</b>")

    if not_found_words:
        feedback_lines.append("⚠️ <b>Ma l9itch l-ma3na dyal had l-kelmat f l-glossaire:</b>")
        for nfw in not_found_words:
            feedback_lines.append(f"• <code>{escape_html(nfw)}</code> → sift: <code>/add {escape_html(nfw)} = ma3na</code>")

    if feedback_lines:
        sections.append("\n".join(feedback_lines))

    # 4. Optional /list deck display
    if list_requested:
        list_lines = ["📋 <b>L-deck kamel dyalek:</b>"]
        if deck:
            for item in deck:
                w_esc = escape_html(item.get("word", ""))
                d_esc = escape_html(item.get("darija", ""))
                stage = item.get("stage", 0)
                if item.get("mastered"):
                    status = "✅ Mastered"
                else:
                    due = item.get("due", "")
                    status = f"Stage {stage} (Due: {due})"
                list_lines.append(f"• <b>{w_esc}</b> ({d_esc}) — {status}")
        else:
            list_lines.append("<i>L-deck khawi ma fih walou daba.</i>")
        sections.append("\n".join(list_lines))

    # 5. Footer reminder
    footer = "💬 <i>Sift /add + l-kelmat li bghiti t-raj3hom</i>"
    sections.append(footer)

    return "\n\n".join(sections)


def split_telegram_message(message_text, max_len=4000):
    """
    Split message into chunks strictly <= max_len.
    Preserves HTML paragraphs and lines without breaking tags where possible.
    """
    if len(message_text) <= max_len:
        return [message_text]

    chunks = []
    # Try splitting by double newline (paragraphs)
    paragraphs = message_text.split("\n\n")
    current_chunk = ""

    for p in paragraphs:
        candidate = f"{current_chunk}\n\n{p}" if current_chunk else p
        if len(candidate) <= max_len:
            current_chunk = candidate
        else:
            if current_chunk:
                chunks.append(current_chunk)
                current_chunk = ""

            # If a single paragraph exceeds max_len, split by line
            if len(p) > max_len:
                lines = p.split("\n")
                for line in lines:
                    cand_line = f"{current_chunk}\n{line}" if current_chunk else line
                    if len(cand_line) <= max_len:
                        current_chunk = cand_line
                    else:
                        if current_chunk:
                            chunks.append(current_chunk)
                            current_chunk = ""
                        # If a single line still exceeds max_len, hard-split
                        while len(line) > max_len:
                            chunks.append(line[:max_len])
                            line = line[max_len:]
                        current_chunk = line
            else:
                current_chunk = p

    if current_chunk:
        chunks.append(current_chunk)

    return chunks


def send_telegram_message(token, chat_id, text_chunk):
    """Send one message chunk via Telegram Bot API using urllib."""
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text_chunk,
        "parse_mode": "HTML",
        "disable_web_page_preview": False,
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))


def get_telegram_updates(token, offset):
    """Retrieve new updates from Telegram Bot API using urllib."""
    url = f"https://api.telegram.org/bot{token}/getUpdates?offset={offset}"
    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, timeout=15) as resp:
        res = json.loads(resp.read().decode("utf-8"))
        if res.get("ok"):
            return res.get("result", [])
    return []


def run(stories_file="data/stories.json", state_file="data/state.json", dry_run=False):
    """Main orchestrator for daily bot execution."""
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    app_url = os.environ.get("APP_URL", "https://example.com/frEdu").strip()

    if not dry_run and (not bot_token or not chat_id):
        print("ERROR: Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID in environment.", file=sys.stderr)
        sys.exit(1)

    # 1. Load stories
    with open(stories_file, "r", encoding="utf-8") as f:
        stories = json.load(f)

    if not stories:
        print("ERROR: No stories found in data/stories.json", file=sys.stderr)
        sys.exit(1)

    # 2. Load state
    state = {"current_day": 1, "last_update_id": 0, "deck": []}
    if os.path.exists(state_file):
        try:
            with open(state_file, "r", encoding="utf-8") as f:
                state = json.load(f)
        except Exception as e:
            print(f"Warning: could not read {state_file}, using defaults: {e}", file=sys.stderr)

    deck = state.get("deck", [])
    last_update_id = state.get("last_update_id", 0)
    current_day = state.get("current_day", 1)

    today_str = datetime.date.today().strftime("%Y-%m-%d")

    # 3. Fetch Telegram updates if token provided
    updates = []
    if bot_token and not dry_run:
        try:
            offset = last_update_id + 1 if last_update_id else 0
            updates = get_telegram_updates(bot_token, offset)
        except Exception as e:
            print(f"Warning: Failed to fetch updates from Telegram: {e}", file=sys.stderr)

    # 4. Parse incoming commands
    added_words, not_found_words, hard_words, list_requested, highest_id = parse_commands(
        updates=updates,
        target_chat_id=chat_id,
        stories=stories,
        deck=deck,
        today_str=today_str,
    )

    if highest_id is not None:
        state["last_update_id"] = max(last_update_id, highest_id)

    # 5. Process deck reviews for today
    due_words = process_deck_review(deck, today_str)

    # 6. Current story
    total_stories = len(stories)
    story_idx = (current_day - 1) % total_stories
    story = stories[story_idx]

    # Check loop back condition
    looped_note = False
    next_day = current_day + 1
    if current_day >= total_stories:
        looped_note = True
        next_day = 1

    # 7. Build daily message
    full_message = build_daily_message(
        current_day=current_day,
        total_stories=total_stories,
        story=story,
        app_url=app_url,
        due_words=due_words,
        added_words=added_words,
        not_found_words=not_found_words,
        hard_words=hard_words,
        list_requested=list_requested,
        deck=deck,
        looped_note=looped_note,
    )

    # Split message into Telegram chunks if > 4000 characters
    chunks = split_telegram_message(full_message, max_len=4000)

    # 8. Send or Dry-Run
    if dry_run:
        print("=== DRY RUN MODE: DAILY TELEGRAM MESSAGE ===")
        print(f"Number of chunks: {len(chunks)}")
        for idx, chunk in enumerate(chunks, 1):
            print(f"\n--- CHUNK {idx}/{len(chunks)} ({len(chunk)} chars) ---")
            print(chunk)
        print("\n=== DRY RUN COMPLETED ===")
    else:
        for chunk in chunks:
            try:
                send_telegram_message(bot_token, chat_id, chunk)
            except Exception as e:
                print(f"ERROR: Failed to send Telegram message: {e}", file=sys.stderr)
                sys.exit(1)
        print(f"Successfully sent {len(chunks)} message(s) to chat {chat_id}.")

    # 9. Advance state
    state["current_day"] = next_day
    state["deck"] = deck

    # Save state
    with open(state_file, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

    print(f"Updated state: next day = {next_day}, deck size = {len(deck)}, last_update_id = {state.get('last_update_id')}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Daily Telegram French Learning Bot")
    parser.add_argument("--dry-run", action="store_true", help="Print message instead of sending via Telegram")
    args = parser.parse_args()

    run(dry_run=args.dry_run)

