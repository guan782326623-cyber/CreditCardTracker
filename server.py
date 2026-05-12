import sys
import os
import re
import json
import sqlite3
from datetime import datetime
from flask import Flask, jsonify, request, send_file
from flask_cors import CORS


def resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), relative_path)


def get_db_path():
    data_dir = os.path.join(os.path.expanduser('~'), 'AppData', 'Local', 'AmexTracker')
    os.makedirs(data_dir, exist_ok=True)
    return os.path.join(data_dir, 'amex_tracker.db')


app = Flask(__name__)
CORS(app)
DB_PATH = get_db_path()


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_db()
    current_year = datetime.now().year

    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id   INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE
        )
    ''')

    cols = [r[1] for r in conn.execute("PRAGMA table_info(benefit_usage)").fetchall()]

    if 'user_id' not in cols:
        # Case 1: table missing or pre-user_id era — full rebuild
        old_rows = []
        if cols:
            old_rows = conn.execute("SELECT * FROM benefit_usage").fetchall()
            conn.execute("DROP TABLE benefit_usage")

        conn.execute('''
            CREATE TABLE benefit_usage (
                user_id         INTEGER NOT NULL,
                card_id         TEXT    NOT NULL,
                benefit_id      TEXT    NOT NULL,
                benefit_year    INTEGER NOT NULL,
                used_amount     REAL    DEFAULT 0,
                checked_months  TEXT    DEFAULT '[]',
                checked_periods TEXT    DEFAULT '[]',
                completed       INTEGER DEFAULT 0,
                PRIMARY KEY (user_id, card_id, benefit_id, benefit_year),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        ''')

        conn.execute("INSERT OR IGNORE INTO users (name) VALUES ('Bill')")
        if old_rows:
            uid = conn.execute("SELECT id FROM users WHERE name='Bill'").fetchone()['id']
            for r in old_rows:
                conn.execute('''
                    INSERT OR IGNORE INTO benefit_usage
                        (user_id, card_id, benefit_id, benefit_year, used_amount, checked_months, checked_periods, completed)
                    VALUES (?, 'amex_platinum', ?, ?, ?, ?, ?, ?)
                ''', (uid, r['id'], current_year, r['used_amount'], r['checked_months'], r['checked_periods'], r['completed']))

    elif 'benefit_year' not in cols:
        # Case 2: has user_id but no benefit_year — migrate via table recreation
        conn.execute('''
            CREATE TABLE benefit_usage_new (
                user_id         INTEGER NOT NULL,
                card_id         TEXT    NOT NULL,
                benefit_id      TEXT    NOT NULL,
                benefit_year    INTEGER NOT NULL,
                used_amount     REAL    DEFAULT 0,
                checked_months  TEXT    DEFAULT '[]',
                checked_periods TEXT    DEFAULT '[]',
                completed       INTEGER DEFAULT 0,
                PRIMARY KEY (user_id, card_id, benefit_id, benefit_year),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        ''')
        conn.execute(f'''
            INSERT INTO benefit_usage_new
                (user_id, card_id, benefit_id, benefit_year, used_amount, checked_months, checked_periods, completed)
            SELECT user_id, card_id, benefit_id, {current_year}, used_amount, checked_months, checked_periods, completed
            FROM benefit_usage
        ''')
        conn.execute("DROP TABLE benefit_usage")
        conn.execute("ALTER TABLE benefit_usage_new RENAME TO benefit_usage")

    conn.execute('''
        CREATE TABLE IF NOT EXISTS user_cards (
            user_id INTEGER NOT NULL,
            card_id TEXT    NOT NULL,
            PRIMARY KEY (user_id, card_id),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    ''')

    conn.execute('''
        CREATE TABLE IF NOT EXISTS custom_cards (
            id     TEXT PRIMARY KEY,
            config TEXT NOT NULL
        )
    ''')

    conn.execute('''
        CREATE TABLE IF NOT EXISTS account_cards (
            last4   TEXT PRIMARY KEY,
            card_id TEXT NOT NULL
        )
    ''')

    existing_users = conn.execute("SELECT id FROM users").fetchall()
    for row in existing_users:
        uid = row['id']
        has_cards = conn.execute(
            "SELECT 1 FROM user_cards WHERE user_id=?", (uid,)
        ).fetchone()
        if not has_cards:
            conn.execute(
                "INSERT OR IGNORE INTO user_cards (user_id, card_id) VALUES (?, 'amex_platinum')",
                (uid,)
            )

    conn.commit()
    conn.close()


# ── Statement scanning helpers ────────────────────────────────────────────────

# Keywords per card per benefit.
# Each entry: list of substrings to look for in uppercase text.
BENEFIT_KEYWORDS = {
    'amex_platinum': {
        'airline':   ['AIRLINE FEE CREDIT', 'AIRLINE CREDIT', 'AIRLINE FEE STMT', 'AIRLINE STATEMENT CREDIT'],
        'hotel':     ['FHR CREDIT', 'FINE HOTELS', 'HOTEL COLLECTION CREDIT', 'THC STMT', 'FHR STMT', 'THC CREDIT', 'FHR/THC CREDIT'],
        'resy':      ['RESY CREDIT', 'RESY STMT', 'RESY DINING CREDIT', 'RESY STATEMENT CREDIT'],
        'uber':      ['UBER CREDIT', 'UBER CASH CREDIT', 'UBER CASH', 'UBER EATS CREDIT'],
        'digital':   ['DIGITAL ENT CREDIT', 'DIGITAL ENTERTAINMENT', 'DIGITAL MEDIA CREDIT', 'ENTERTAINMENT CREDIT'],
        'lululemon': ['LULULEMON CREDIT', 'LULULEMON STMT', 'LULULEMON STATEMENT CREDIT'],
        'saks':      ['SAKS CREDIT', 'SAKS FIFTH', 'SAKS STMT', 'SAKS STATEMENT CREDIT'],
        'equinox':   ['EQUINOX CREDIT', 'EQUINOX STMT', 'EQUINOX STATEMENT CREDIT'],
        'walmart':   ['WALMART+ CREDIT', 'WALMART CREDIT', 'WALMART PLUS CREDIT'],
        'oura':      ['OURA CREDIT', 'OURA RING CREDIT', 'OURA STMT', 'OURA STATEMENT CREDIT'],
        'clear':     ['CLEAR CREDIT', 'CLEAR PLUS CREDIT', 'CLEAR® CREDIT', 'CLEAR STATEMENT'],
    },
    'chase_sapphire_reserve_business': {
        'travel':            ['TRAVEL CREDIT', 'TRAVEL STMT CREDIT', 'TRAVEL STATEMENT CREDIT'],
        'hotel':             ['THE EDIT CREDIT', 'EDIT HOTEL CREDIT', 'EDIT CREDIT'],
        'lyft':              ['LYFT CREDIT', 'LYFT STATEMENT CREDIT'],
        'doordash':          ['DOORDASH CREDIT', 'DOOR DASH CREDIT', 'DOORDASH STMT'],
        'global_entry':      ['GLOBAL ENTRY CREDIT', 'TSA PRECHECK CREDIT', 'GLOBAL ENTRY REIMBURSEMENT'],
        'ziprecruiter':      ['ZIPRECRUITER CREDIT', 'ZIP RECRUITER CREDIT', 'ZIPRECRUITER STMT'],
        'google_workspace':  ['GOOGLE WORKSPACE CREDIT', 'GOOGLE WORKSPACE STMT'],
        'giftcards':         ['GIFTCARDS CREDIT', 'GIFTCARDS.COM CREDIT', 'GIFT CARDS CREDIT'],
    },
    'chase_sapphire_preferred': {
        'hotel': ['HOTEL CREDIT', 'HOTEL STMT CREDIT', 'SAPPHIRE PREFERRED HOTEL CREDIT'],
    },
    'chase_marriott_premier_plus': {
        'free_night': ['FREE NIGHT CERTIFICATE', 'FREE NIGHT CERT', 'MARRIOTT FREE NIGHT', 'FREE NIGHT AWARD'],
    },
    'chase_sapphire_reserve': {
        'travel':        ['TRAVEL CREDIT', 'TRAVEL STMT CREDIT', 'TRAVEL STATEMENT CREDIT'],
        'hotel':         ['THE EDIT CREDIT', 'EDIT HOTEL CREDIT', 'EDIT CREDIT'],
        'dining':        ['SAPPHIRE RESERVE TABLES', 'RESERVE TABLES CREDIT', 'DINING STMT CREDIT', 'DINING STATEMENT CREDIT'],
        'doordash':      ['DOORDASH CREDIT', 'DOOR DASH CREDIT', 'DOORDASH STMT'],
        'doordash_plus': ['DOORDASH+ CREDIT', 'DASHPASS CREDIT', 'DOORDASH PLUS CREDIT'],
        'apple':         ['APPLE SERVICES CREDIT', 'APPLE TV CREDIT', 'APPLE MUSIC CREDIT', 'APPLE CREDIT'],
        'lyft':          ['LYFT CREDIT', 'LYFT STATEMENT CREDIT'],
        'peloton':       ['PELOTON CREDIT', 'PELOTON STMT', 'PELOTON STATEMENT CREDIT'],
        'stubhub':       ['STUBHUB CREDIT', 'STUB HUB CREDIT', 'STUBHUB STMT'],
        'global_entry':  ['GLOBAL ENTRY CREDIT', 'TSA PRECHECK CREDIT', 'GLOBAL ENTRY REIMBURSEMENT'],
    },
    'amex_gold': {
        'dining':  ['DINING CREDIT', 'GRUBHUB CREDIT', 'DINING STMT CREDIT', 'DINING STATEMENT CREDIT'],
        'uber':    ['UBER CASH', 'UBER CREDIT', 'UBER EATS CREDIT'],
        'dunkin':  ["DUNKIN' CREDIT", 'DUNKIN CREDIT', "DUNKIN'"],
        'resy':    ['RESY CREDIT', 'RESY STMT', 'RESY STATEMENT CREDIT'],
        'hotel':   ['HOTEL COLLECTION CREDIT', 'THC CREDIT'],
    },
    'chase_amazon_prime': {},
}

# Benefit type per benefit_id per card (mirrors CARDS config in frontend)
BENEFIT_TYPES = {
    'amex_platinum': {
        'airline': 'annual', 'hotel': 'semi-annual',
        'resy': 'quarterly', 'uber': 'monthly_uber',
        'digital': 'monthly', 'lululemon': 'quarterly',
        'saks': 'semi-annual', 'equinox': 'toggle',
        'walmart': 'monthly', 'oura': 'toggle', 'clear': 'toggle',
    },
    'chase_sapphire_reserve_business': {
        'travel': 'annual', 'hotel': 'annual',
        'lyft': 'monthly', 'doordash': 'monthly',
        'global_entry': 'toggle', 'ziprecruiter': 'semi-annual',
        'google_workspace': 'annual', 'giftcards': 'semi-annual',
    },
    'chase_sapphire_preferred': {
        'hotel': 'annual',
    },
    'chase_marriott_premier_plus': {
        'free_night': 'toggle',
    },
    'chase_sapphire_reserve': {
        'travel': 'annual', 'hotel': 'annual',
        'dining': 'semi-annual', 'doordash': 'monthly',
        'doordash_plus': 'toggle', 'apple': 'annual',
        'lyft': 'monthly', 'peloton': 'monthly',
        'stubhub': 'semi-annual', 'global_entry': 'toggle',
    },
    'amex_gold': {
        'dining': 'monthly', 'uber': 'monthly', 'dunkin': 'monthly',
        'resy': 'semi-annual', 'hotel': 'annual',
    },
    'chase_amazon_prime': {},
}

CARD_TYPE_KEYWORDS = {
    'amex_platinum':                    ['PLATINUM CARD', 'THE PLATINUM', 'PLATINUM DELTA', 'PLATINUM DELTA SKYMILES'],
    'amex_gold':                        ['GOLD CARD', 'AMERICAN EXPRESS GOLD', 'AMEX GOLD', 'PREFERRED REWARDS GOLD'],
    'chase_sapphire_reserve_business':  ['SAPPHIRE RESERVE BUSINESS', 'CSR BUSINESS', 'CHASE SAPPHIRE RESERVE BUSINESS'],
    # Note: Chase PDFs often render card name as image logo — match on extractable text instead
    'chase_sapphire_reserve':           ['SAPPHIRE RESERVE', 'CHASE SAPPHIRE RESERVE',
                                         'TRAVEL CREDIT $300',           # CSR $300 annual travel credit (transaction line)
                                         'STUBHUB CREDIT',               # CSR StubHub benefit (unique to CSR)
                                         '8X POINTS ON CHASE TRAVEL',    # points summary format A
                                         '8X ON CHASE TRAVEL',           # points summary format B
                                         '+ 8X POINTS', '+ 8X ON'],
    'chase_sapphire_preferred':         ['SAPPHIRE PREFERRED', 'CHASE SAPPHIRE PREFERRED',
                                         'TRAVEL CREDIT $50',            # CSP $50 hotel credit
                                         '5X POINTS ON CHASE TRAVEL', '5X ON CHASE TRAVEL'],
    'chase_marriott_premier_plus':      ['MARRIOTT BONVOY PREMIER PLUS', 'MARRIOTT PREMIER PLUS', 'BONVOY PREMIER PLUS',
                                         'MARRIOTT BONVOY BOUNDLESS', 'BONVOY BOUNDLESS'],
    'chase_amazon_prime':               ['PRIME VISA', 'AMAZON PRIME VISA', 'YOUR PRIME VISA POINTS',
                                         'CHASE.COM/AMAZON', 'AMAZON REWARDS VISA'],
}


def extract_pdf_text(file_stream):
    """Extract full text from a PDF file stream using pdfplumber."""
    try:
        import pdfplumber
        text_parts = []
        with pdfplumber.open(file_stream) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    text_parts.append(t)
        return normalize_pdf_text('\n'.join(text_parts))
    except ImportError:
        raise RuntimeError('pdfplumber not installed')
    except Exception as e:
        raise RuntimeError(f'PDF read error: {e}')


def normalize_pdf_text(text):
    """
    Fix doubled-character text that pdfplumber sometimes produces from Chase PDFs.
    In these PDFs each character appears twice per word (e.g. 'YYOOUURR' instead of 'YOUR').
    Works word-by-word so that spaces between words don't break detection.
    """
    def is_doubled_word(w):
        """A word is 'doubled' if it has even length >= 4 and every consecutive pair of chars matches."""
        if len(w) < 4 or len(w) % 2 != 0:
            return False
        return all(w[i] == w[i + 1] for i in range(0, len(w) - 1, 2))

    fixed = []
    for line in text.split('\n'):
        words = line.split()
        if len(words) >= 2:
            doubled_count = sum(1 for w in words if is_doubled_word(w))
            if doubled_count / len(words) >= 0.5:
                fixed.append(' '.join(w[::2] if is_doubled_word(w) else w for w in words))
                continue
        elif len(words) == 1 and is_doubled_word(words[0]):
            fixed.append(words[0][::2])
            continue
        fixed.append(line)
    return '\n'.join(fixed)


def detect_card_type(text):
    """Return the card_id whose keywords best match the statement text."""
    upper = text.upper()
    for card_id, keywords in CARD_TYPE_KEYWORDS.items():
        for kw in keywords:
            if kw in upper:
                return card_id
    return None


def find_user_in_text(text, users):
    """
    Search for any registered user's name directly in the statement text.
    Handles: exact match, reversed order (Last First), and middle name/initial variations.
    Returns the matched user dict {'id', 'name'} or None.
    """
    upper_text = text.upper()
    for u in users:
        name = u['name'].upper().strip()
        words = name.split()

        # 1. Exact full name match
        if name in upper_text:
            return {'id': u['id'], 'name': u['name']}

        if len(words) >= 2:
            # 2. Reversed word order (e.g. "GUAN YU" for "YU GUAN")
            reversed_name = ' '.join(reversed(words))
            if reversed_name in upper_text:
                return {'id': u['id'], 'name': u['name']}

            # 3. First + last with optional middle name/initial in between
            #    e.g. "WILLIAM WAAS" matches "WILLIAM R WAAS" or "WILLIAM ROBERT WAAS"
            first = re.escape(words[0])
            last = re.escape(words[-1])
            pattern = rf'\b{first}\s+(?:\w{{1,20}}\s+){{0,2}}{last}\b'
            if re.search(pattern, upper_text):
                return {'id': u['id'], 'name': u['name']}

            # 4. Last, First format (e.g. "WAAS/WILLIAM" or "WAAS, WILLIAM")
            last_first = rf'\b{last}[/,\s]+{first}\b'
            if re.search(last_first, upper_text):
                return {'id': u['id'], 'name': u['name']}

    return None


def extract_account_last4(text):
    """
    Extract the last 4 digits of the account number from statement text.
    Handles Chase format (XXXX XXXX XXXX 4679) and Amex format (Account Ending 0-41001).
    """
    # Chase: "XXXX XXXX XXXX 4679" or "Account Number: XXXX XXXX XXXX 4679"
    m = re.search(r'XXXX[\s\-]+XXXX[\s\-]+XXXX[\s\-]+(\d{4})\b', text, re.IGNORECASE)
    if m:
        return m.group(1)
    # Amex: "Account Ending 0-41001" → last 4 of the suffix
    m = re.search(r'Account\s+Ending\s+[\w\-]*?(\d{4})\b', text, re.IGNORECASE)
    if m:
        return m.group(1)
    # Generic fallback: "Account Number: ... XXXX" near end of number
    m = re.search(r'Account\s+(?:Number|#)\s*:?\s*[\dXx\s\-]+?(\d{4})\b', text, re.IGNORECASE)
    if m:
        return m.group(1)
    return None


def parse_amount(line):
    """Extract the last dollar amount from a line (handles commas, no $ required)."""
    amounts = re.findall(r'(?<!\d)(\d{1,6}(?:,\d{3})*\.\d{2})(?!\d)', line)
    if amounts:
        return float(amounts[-1].replace(',', ''))
    return 0.0


def parse_date(line):
    """
    Extract (0-based month, 4-digit year) from a transaction line.
    Looks for MM/DD or MM/DD/YY(YY) patterns.
    Returns (None, None) if not found.
    """
    m = re.search(r'\b(\d{1,2})/\d{1,2}(?:/(\d{2,4}))?\b', line)
    if m:
        month_num = int(m.group(1))
        year_str = m.group(2)
        if year_str:
            yr = int(year_str)
            year = yr + 2000 if yr < 100 else yr
        else:
            year = None
        if 1 <= month_num <= 12:
            return month_num - 1, year  # 0-based month, 4-digit year
    return None, None


def scan_benefits(text, card_id):
    """
    Scan statement text for benefit credits.
    Returns list of dicts:
        {benefit_id, type, amount, month (0-based or None), line}
    """
    if card_id not in BENEFIT_KEYWORDS:
        return []

    upper_lines = [(line, line.upper()) for line in text.split('\n')]
    found = []
    seen_benefit_ids = set()

    for benefit_id, keywords in BENEFIT_KEYWORDS[card_id].items():
        for line, upper_line in upper_lines:
            matched_kw = next((kw for kw in keywords if kw in upper_line), None)
            if not matched_kw:
                continue
            amount        = parse_amount(line)
            month, year   = parse_date(line)
            b_type        = BENEFIT_TYPES[card_id].get(benefit_id, 'toggle')
            found.append({
                'benefit_id':  benefit_id,
                'type':        b_type,
                'amount':      amount,
                'month':       month,
                'year':        year,
                'description': line.strip(),
            })
            seen_benefit_ids.add(benefit_id)
            break  # one detection per benefit_id per statement

    return found


def apply_detected_benefits(conn, user_id, card_id, detected, stmt_month=None, stmt_year=None):
    """
    Apply detected benefit credits to the database.
    Returns list of applied items with 'was_new' flag.
    """
    if stmt_year is None:
        stmt_year = datetime.now().year

    applied = []
    for item in detected:
        bid    = item['benefit_id']
        btype  = item['type']
        amount = item['amount']
        month  = item['month'] if item['month'] is not None else stmt_month
        year   = item.get('year') or stmt_year

        # Load existing row for this year
        row = conn.execute(
            "SELECT * FROM benefit_usage WHERE user_id=? AND card_id=? AND benefit_id=? AND benefit_year=?",
            (user_id, card_id, bid, year)
        ).fetchone()

        used_amount     = float(row['used_amount'])     if row else 0.0
        checked_months  = json.loads(row['checked_months'])  if row else []
        checked_periods = json.loads(row['checked_periods']) if row else []
        completed       = bool(row['completed'])         if row else False

        was_new = False

        if btype == 'annual':
            if amount > 0 and used_amount < amount:
                used_amount = min(used_amount + amount, amount)
                was_new = True
        elif btype in ('monthly', 'monthly_uber'):
            if month is not None and month not in checked_months:
                checked_months = sorted(set(checked_months) | {month})
                was_new = True
        elif btype == 'semi-annual':
            if month is not None:
                period = 1 if month < 6 else 2
            else:
                period = 1 if datetime.now().month <= 6 else 2
            if period not in checked_periods:
                checked_periods = sorted(set(checked_periods) | {period})
                was_new = True
        elif btype == 'quarterly':
            if month is not None:
                period = (month // 3) + 1  # 0-2→Q1, 3-5→Q2, 6-8→Q3, 9-11→Q4
            else:
                period = (datetime.now().month - 1) // 3 + 1
            if period not in checked_periods:
                checked_periods = sorted(set(checked_periods) | {period})
                was_new = True
        elif btype == 'toggle':
            if not completed:
                completed = True
                was_new = True

        conn.execute('''
            INSERT OR REPLACE INTO benefit_usage
                (user_id, card_id, benefit_id, benefit_year, used_amount, checked_months, checked_periods, completed)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            user_id, card_id, bid, year,
            used_amount,
            json.dumps(checked_months),
            json.dumps(checked_periods),
            1 if completed else 0,
        ))

        applied.append({
            'benefit_id':  bid,
            'type':        btype,
            'amount':      amount,
            'month':       month,
            'year':        year,
            'description': item['description'],
            'was_new':     was_new,
        })

    return applied


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    from flask import make_response
    resp = make_response(send_file(resource_path('index.html')))
    resp.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    resp.headers['Pragma'] = 'no-cache'
    return resp


# ── Users ──────────────────────────────────────────────────────────────────────

@app.route('/api/users', methods=['GET'])
def get_users():
    conn = get_db()
    rows = conn.execute("SELECT id, name FROM users ORDER BY id").fetchall()
    conn.close()
    return jsonify([{'id': r['id'], 'name': r['name']} for r in rows])


@app.route('/api/users', methods=['POST'])
def create_user():
    name = (request.get_json(force=True) or {}).get('name', '').strip()
    if not name:
        return jsonify({'error': 'Name required'}), 400
    conn = get_db()
    try:
        conn.execute("INSERT INTO users (name) VALUES (?)", (name,))
        conn.commit()
        uid = conn.execute("SELECT id FROM users WHERE name=?", (name,)).fetchone()['id']
        conn.execute("INSERT OR IGNORE INTO user_cards (user_id, card_id) VALUES (?, 'amex_platinum')", (uid,))
        conn.commit()
        conn.close()
        return jsonify({'id': uid, 'name': name})
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({'error': 'User already exists'}), 409


@app.route('/api/users/<int:user_id>', methods=['PUT'])
def rename_user(user_id):
    name = (request.get_json(force=True) or {}).get('name', '').strip()
    if not name:
        return jsonify({'error': 'Name required'}), 400
    conn = get_db()
    try:
        conn.execute("UPDATE users SET name=? WHERE id=?", (name, user_id))
        conn.commit()
        conn.close()
        return jsonify({'id': user_id, 'name': name})
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({'error': 'User already exists'}), 409


@app.route('/api/users/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    conn = get_db()
    conn.execute("DELETE FROM benefit_usage WHERE user_id=?", (user_id,))
    conn.execute("DELETE FROM user_cards WHERE user_id=?", (user_id,))
    conn.execute("DELETE FROM users WHERE id=?", (user_id,))
    conn.commit()
    conn.close()
    return jsonify({'status': 'ok'})


# ── User cards ─────────────────────────────────────────────────────────────────

@app.route('/api/users/<int:user_id>/cards', methods=['GET'])
def get_user_cards(user_id):
    conn = get_db()
    rows = conn.execute(
        "SELECT card_id FROM user_cards WHERE user_id=? ORDER BY card_id", (user_id,)
    ).fetchall()
    conn.close()
    return jsonify([r['card_id'] for r in rows])


@app.route('/api/users/<int:user_id>/cards', methods=['POST'])
def add_user_card(user_id):
    card_id = (request.get_json(force=True) or {}).get('card_id', '').strip()
    if not card_id:
        return jsonify({'error': 'card_id required'}), 400
    conn = get_db()
    conn.execute("INSERT OR IGNORE INTO user_cards (user_id, card_id) VALUES (?, ?)", (user_id, card_id))
    conn.commit()
    conn.close()
    return jsonify({'status': 'ok'})


@app.route('/api/users/<int:user_id>/cards/<card_id>', methods=['DELETE'])
def remove_user_card(user_id, card_id):
    conn = get_db()
    conn.execute("DELETE FROM user_cards WHERE user_id=? AND card_id=?", (user_id, card_id))
    conn.commit()
    conn.close()
    return jsonify({'status': 'ok'})


# ── Usage ──────────────────────────────────────────────────────────────────────

@app.route('/api/usage/<int:user_id>/<card_id>', methods=['GET'])
def get_usage(user_id, card_id):
    year = request.args.get('year', datetime.now().year, type=int)
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM benefit_usage WHERE user_id=? AND card_id=? AND benefit_year=?",
        (user_id, card_id, year)
    ).fetchall()
    conn.close()
    result = {}
    for r in rows:
        result[r['benefit_id']] = {
            'usedAmount':     r['used_amount'],
            'checkedMonths':  json.loads(r['checked_months']),
            'checkedPeriods': json.loads(r['checked_periods']),
            'completed':      bool(r['completed']),
        }
    return jsonify(result)


@app.route('/api/usage/<int:user_id>/<card_id>', methods=['PUT'])
def update_usage(user_id, card_id):
    year = request.args.get('year', datetime.now().year, type=int)
    data = request.get_json(force=True)
    conn = get_db()
    for benefit_id, v in data.items():
        conn.execute('''
            INSERT OR REPLACE INTO benefit_usage
                (user_id, card_id, benefit_id, benefit_year, used_amount, checked_months, checked_periods, completed)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            user_id, card_id, benefit_id, year,
            v.get('usedAmount', 0),
            json.dumps(v.get('checkedMonths', [])),
            json.dumps(v.get('checkedPeriods', [])),
            1 if v.get('completed') else 0,
        ))
    conn.commit()
    conn.close()
    return jsonify({'status': 'ok'})


@app.route('/api/reset/<int:user_id>/<card_id>', methods=['POST'])
def reset_usage(user_id, card_id):
    year = request.args.get('year', datetime.now().year, type=int)
    conn = get_db()
    conn.execute("DELETE FROM benefit_usage WHERE user_id=? AND card_id=? AND benefit_year=?",
                 (user_id, card_id, year))
    conn.commit()
    conn.close()
    return jsonify({'status': 'ok'})


# ── Statement scan ─────────────────────────────────────────────────────────────

@app.route('/api/scan-statement', methods=['POST'])
def scan_statement():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400

    f = request.files['file']
    try:
        text = extract_pdf_text(f.stream)
    except RuntimeError as e:
        return jsonify({'error': str(e)}), 400

    # Extract account last 4 digits for mapping lookup
    last4 = extract_account_last4(text)

    conn = get_db()

    # Step 1: Try keyword-based card detection
    card_id = detect_card_type(text)

    # Step 2: If keyword detection failed, check account_cards mapping
    if not card_id and last4:
        row = conn.execute("SELECT card_id FROM account_cards WHERE last4=?", (last4,)).fetchone()
        if row:
            card_id = row['card_id']

    # Step 3: If keyword detection succeeded, auto-save the mapping for future use
    if card_id and last4:
        conn.execute("INSERT OR REPLACE INTO account_cards (last4, card_id) VALUES (?, ?)",
                     (last4, card_id))
        conn.commit()

    # Find which registered user this statement belongs to by searching their name in the text
    all_users = conn.execute("SELECT id, name FROM users").fetchall()
    matched_user = find_user_in_text(text, all_users)

    # No name found → not this user's statement
    if not matched_user:
        conn.close()
        return jsonify({
            'card_id':    card_id,
            'cardholder': None,
            'user':       None,
            'last4':      last4,
            'detected':   [],
            'applied':    [],
            'error':      '账单中未找到已注册用户的姓名，请确认账单归属',
        })

    # Name found but card type still unknown → prompt user to bind this account number
    if not card_id:
        conn.close()
        return jsonify({
            'card_id':    None,
            'cardholder': matched_user['name'],
            'user':       matched_user,
            'last4':      last4,
            'detected':   [],
            'applied':    [],
            'error':      'unidentified_card',
        })

    # Detect month and year from statement closing date (fallback to now)
    stmt_date_match = re.search(
        r'(?:Statement|Closing)\s+Date[:\s]+(\d{1,2})/\d{1,2}/(\d{2,4})', text, re.IGNORECASE
    )
    if stmt_date_match:
        stmt_month = int(stmt_date_match.group(1)) - 1  # 0-based
        yr = int(stmt_date_match.group(2))
        stmt_year = yr + 2000 if yr < 100 else yr
    else:
        stmt_month = datetime.now().month - 1
        stmt_year  = datetime.now().year

    # Scan for benefits
    detected = scan_benefits(text, card_id)

    # Auto-apply if we matched a user
    applied = []
    if matched_user and detected:
        applied = apply_detected_benefits(
            conn, matched_user['id'], card_id, detected, stmt_month, stmt_year
        )
        conn.commit()

    conn.close()

    return jsonify({
        'card_id':    card_id,
        'cardholder': matched_user['name'],
        'user':       matched_user,
        'last4':      last4,
        'stmt_month': stmt_month,
        'stmt_year':  stmt_year,
        'detected':   detected,
        'applied':    applied,
    })


# ── Account → Card mapping ─────────────────────────────────────────────────────

@app.route('/api/account-cards', methods=['GET'])
def list_account_cards():
    conn = get_db()
    rows = conn.execute("SELECT last4, card_id FROM account_cards ORDER BY last4").fetchall()
    conn.close()
    return jsonify([{'last4': r['last4'], 'card_id': r['card_id']} for r in rows])


@app.route('/api/account-cards', methods=['POST'])
def save_account_card():
    data = request.get_json(force=True) or {}
    last4 = (data.get('last4') or '').strip()
    card_id = (data.get('card_id') or '').strip()
    if not last4 or not card_id:
        return jsonify({'error': 'last4 and card_id required'}), 400
    conn = get_db()
    conn.execute("INSERT OR REPLACE INTO account_cards (last4, card_id) VALUES (?, ?)",
                 (last4, card_id))
    conn.commit()
    conn.close()
    return jsonify({'ok': True})


@app.route('/api/account-cards/<last4>', methods=['DELETE'])
def delete_account_card(last4):
    conn = get_db()
    conn.execute("DELETE FROM account_cards WHERE last4=?", (last4,))
    conn.commit()
    conn.close()
    return jsonify({'ok': True})


# ── Custom card storage ────────────────────────────────────────────────────────

@app.route('/api/custom-cards', methods=['GET'])
def list_custom_cards():
    conn = get_db()
    rows = conn.execute("SELECT config FROM custom_cards").fetchall()
    conn.close()
    return jsonify([json.loads(r['config']) for r in rows])


@app.route('/api/custom-cards', methods=['POST'])
def save_custom_card():
    card = request.get_json(force=True) or {}
    if not card.get('id'):
        return jsonify({'error': 'Card id required'}), 400
    conn = get_db()
    conn.execute("INSERT OR REPLACE INTO custom_cards (id, config) VALUES (?, ?)",
                 (card['id'], json.dumps(card)))
    conn.commit()
    conn.close()
    return jsonify({'ok': True})


@app.route('/api/custom-cards/<card_id>', methods=['DELETE'])
def delete_custom_card(card_id):
    conn = get_db()
    conn.execute("DELETE FROM custom_cards WHERE id=?", (card_id,))
    conn.commit()
    conn.close()
    return jsonify({'ok': True})


# ── Card scraping + parsing ────────────────────────────────────────────────────

def _infer_benefit_type(context):
    c = context.lower()
    if re.search(r'\bper\s+month\b|\bmonthly\b|/month\b|\bper\s+mo\b', c):
        return 'monthly'
    if re.search(r'\bquarterly\b|\bper\s+quarter\b|\bevery\s+(3|three)\s+months?\b', c):
        return 'quarterly'
    if re.search(r'\bsemi.?annual\b|\btwice\s+a\s+year\b|\bevery\s+six\s+months?\b|\bper\s+half', c):
        return 'semi-annual'
    if re.search(r'\bper\s+year\b|\bannual\b|\bannually\b|\byearly\b', c):
        return 'annual'
    if re.search(r'\bmembership\b|\bglobal\s+entry\b|\btsa\s+pre.?check\b|\bclear\b|\bfee\s+credit\b|\btoggle\b', c):
        return 'toggle'
    if re.search(r'\bcredit\b|\breimbursement\b|\bstatement\b', c):
        return 'annual'
    return None


def _reset_period(btype, lang):
    zh = {'annual': '每年', 'monthly': '每月', 'monthly_uber': '每月',
          'semi-annual': '每半年（H1/H2）', 'quarterly': '每季度（Q1-Q4）', 'toggle': '每年（使用后标记）'}
    en = {'annual': 'Annual', 'monthly': 'Monthly', 'monthly_uber': 'Monthly',
          'semi-annual': 'Semi-annual (H1/H2)', 'quarterly': 'Quarterly (Q1–Q4)', 'toggle': 'Annual (mark when used)'}
    return zh.get(btype, '每年') if lang == 'zh' else en.get(btype, 'Annual')


def _parse_html_to_text(html):
    import html as html_lib
    # Remove script, style, nav, header, footer blocks
    html = re.sub(r'<(script|style|nav|header|footer|aside)[^>]*>.*?</\1>', ' ', html,
                  flags=re.DOTALL | re.IGNORECASE)
    # Convert block/list elements to newlines
    html = re.sub(r'<br\s*/?>', '\n', html, flags=re.IGNORECASE)
    html = re.sub(r'<li[^>]*>', '\n• ', html, flags=re.IGNORECASE)
    html = re.sub(r'<(?:p|div|h[1-6]|tr|td|th|section|article)[^>]*>', '\n', html, flags=re.IGNORECASE)
    # Strip remaining tags
    text = re.sub(r'<[^>]+>', ' ', html)
    text = html_lib.unescape(text)
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
    return text.strip()


def _extract_card_name(title):
    if not title:
        return ''
    name = re.sub(r'\s*[-–|]\s*.*$', '', title).strip()
    name = re.sub(r'\s+(?:Full\s+)?(?:Card\s+)?Review\s*$', '', name, flags=re.IGNORECASE).strip()
    return name


def _extract_benefits(text, annual_fee):
    import html as html_lib
    benefits = []
    seen_ids = set()
    lines = [l.strip() for l in text.split('\n') if l.strip()]

    for i, line in enumerate(lines):
        amounts = list(re.finditer(r'\$\s*(\d[\d,]*)', line))
        if not amounts:
            continue
        for amt_m in amounts:
            amount = int(amt_m.group(1).replace(',', ''))
            # Skip annual-fee-sized amounts and very small/large ones
            if amount < 10 or amount > 2500:
                continue
            if amount == annual_fee:
                continue

            # Context = this line + 2 surrounding lines
            ctx_lines = lines[max(0, i - 2):i + 3]
            context = ' '.join(ctx_lines)

            btype = _infer_benefit_type(context)
            if not btype:
                continue

            # Build benefit name: strip dollar amounts and filler from the line
            name_raw = re.sub(r'\$\s*\d[\d,]*', '', line)
            name_raw = re.sub(
                r'\b(up\s+to|statement\s+credit|credit|reimbursement|per\s+year|annually|per\s+month|'
                r'monthly|quarterly|per\s+quarter|semi.?annual|per|each|every|get|earn|receive|enjoy|'
                r'includes?|toward|with|and|for|in|at|of|the|a|an)\b',
                ' ', name_raw, flags=re.IGNORECASE)
            name_raw = re.sub(r'[•\-:,\(\)]+', ' ', name_raw)
            name_raw = re.sub(r'\s+', ' ', name_raw).strip()

            if len(name_raw) < 3 or len(name_raw) > 70:
                continue

            bid = re.sub(r'[^a-z0-9]+', '_', name_raw.lower()).strip('_')[:30]
            if not bid or bid in seen_ids:
                continue
            seen_ids.add(bid)

            if btype in ('monthly', 'monthly_uber'):
                monthly_val = amount
                total_val   = amount * 12
            elif btype == 'semi-annual':
                monthly_val = None
                total_val   = amount * 2
            elif btype == 'quarterly':
                monthly_val = None
                total_val   = amount * 4
            else:
                monthly_val = None
                total_val   = amount

            benefit = {
                'id':          bid,
                'name':        {'zh': name_raw, 'en': name_raw},
                'type':        btype,
                'totalValue':  total_val,
                'resetPeriod': {'zh': _reset_period(btype, 'zh'), 'en': _reset_period(btype, 'en')},
                'description': {'zh': '', 'en': ''},
            }
            if monthly_val is not None:
                benefit['monthlyValue'] = monthly_val
            benefits.append(benefit)

    return benefits


@app.route('/api/scrape-card', methods=['POST'])
def scrape_card():
    import urllib.request as urllib_req
    url = (request.get_json(force=True) or {}).get('url', '').strip()
    if not url:
        return jsonify({'error': 'URL required'}), 400
    try:
        req = urllib_req.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept':     'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        })
        with urllib_req.urlopen(req, timeout=20) as resp:
            html = resp.read().decode('utf-8', errors='replace')
    except Exception as e:
        return jsonify({'error': f'无法访问该网页：{e}'}), 400

    # Extract title
    title_m = re.search(r'<title[^>]*>(.*?)</title>', html, re.IGNORECASE | re.DOTALL)
    raw_title = re.sub(r'<[^>]+>', '', title_m.group(1)) if title_m else ''
    import html as html_lib
    raw_title = html_lib.unescape(raw_title).strip()

    card_name = _extract_card_name(raw_title)
    card_id   = 'custom_' + re.sub(r'[^a-z0-9]+', '_', card_name.lower()).strip('_')
    if not card_id or card_id == 'custom_':
        card_id = f'custom_{int(datetime.now().timestamp())}'

    text = _parse_html_to_text(html)

    # Annual fee
    annual_fee = 0
    fee_m = re.search(r'(?:annual\s+fee|年费)[:\s]*\$\s*(\d[\d,]*)', text, re.IGNORECASE)
    if not fee_m:
        fee_m = re.search(r'\$\s*(\d[\d,]*)\s*(?:annual\s+fee|per\s+year)', text, re.IGNORECASE)
    if fee_m:
        annual_fee = int(fee_m.group(1).replace(',', ''))

    benefits = _extract_benefits(text, annual_fee)

    return jsonify({
        'id':         card_id,
        'name':       {'zh': card_name, 'en': card_name},
        'annualFee':  annual_fee,
        'headerBg':   'bg-slate-700',
        'benefits':   benefits,
        '_sourceUrl': url,
    })


# ── Apply pre-scanned benefits ────────────────────────────────────────────────

@app.route('/api/apply-benefits', methods=['POST'])
def apply_benefits_endpoint():
    data       = request.get_json(force=True) or {}
    user_id    = data.get('user_id')
    card_id    = data.get('card_id')
    detected   = data.get('detected', [])
    stmt_month = data.get('stmt_month')
    stmt_year  = data.get('stmt_year', datetime.now().year)

    if not user_id or not card_id:
        return jsonify({'error': 'user_id and card_id required'}), 400

    conn    = get_db()
    applied = apply_detected_benefits(conn, user_id, card_id, detected, stmt_month, stmt_year)
    conn.commit()
    conn.close()
    return jsonify({'applied': applied})


# ── Dev entry ──────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    init_db()
    print("=" * 50)
    print("Dev server: http://localhost:5000")
    print("=" * 50)
    app.run(debug=False, port=5000)
