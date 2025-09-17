import json
import os
import sys
import random
import hashlib
import re
from typing import Optional

USERS_FILE = "users.json"
ADMINS_FILE = "admins.json"
LEADERBOARD_FILE = "leaderboard.json"
QUESTION_FILE = "questions.json"
SAVE_DIR = "saves"

USERS = {}
ADMINS = {}
QUESTIONS = []
LEADERBOARD = []

DEV_MODE = {"god_mode": False, "show_answers": False, "instant_win": False}

ITEMS = {
    "potion": {"name": "Healing Potion", "desc": "Restores 30 HP", "price": 50},
    "shield": {"name": "Shield", "desc": "Blocks next hit", "price": 100},
}

DEFAULT_PLAYER = {
    "name": "Hero",
    "level": 1,
    "xp": 0,
    "hp": 80,
    "max_hp": 80,
    "damage": 8,
    "score": 0,
    "combo": 0,
    "gold": 0,
    "gold_bonus": 0,
    "inventory": {},
    "shield_active": False
}

def ensure_dirs():
    os.makedirs(SAVE_DIR, exist_ok=True)

def safe_json_load(path):
    try:
        if not os.path.exists(path):
            return None
        with open(path, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if not content:
                return None
            return json.loads(content)
    except Exception as e:
        print(f"⚠️ Error loading {path}: {e}")
        return None

def safe_json_write(path, data):
    try:
        ensure_dirs()
        d = os.path.dirname(path)
        if d:
            os.makedirs(d, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"⚠️ Error saving {path}: {e}")
        return False

def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")

def press_enter():
    try:
        input("\n⚡ Press Enter to continue...")
    except (EOFError, KeyboardInterrupt):
        pass

def safe_input(prompt=""):
    try:
        return input(prompt).strip()
    except (EOFError, KeyboardInterrupt):
        print("\n⚠️ Input interrupted")
        return ""

def get_valid_choice(prompt, valid_choices, error_msg="⚠️ Invalid choice."):
    while True:
        c = safe_input(prompt)
        if c in valid_choices:
            return c
        print(error_msg)
        press_enter()

def _find_record_case_insensitive(d: dict, key: str):
    if not isinstance(d, dict) or not key:
        return None, None
    key_low = key.lower()
    for k, v in d.items():
        if k.lower() == key_low:
            return k, v
    return None, None

def hash_password(password: str, salt: Optional[bytes] = None) -> dict:
    if salt is None:
        salt = os.urandom(16)
    h = hashlib.sha256(salt + password.encode()).hexdigest()
    return {"hash": h, "salt": salt.hex()}

def verify_password(password: str, stored: dict) -> bool:
    try:
        salt = bytes.fromhex(stored.get("salt", ""))
        return hashlib.sha256(salt + password.encode()).hexdigest() == stored.get("hash", "")
    except Exception:
        return False

def normalize_player(p: Optional[dict]) -> dict:
    """Return a safe copy of player dict using defaults and validation."""
    p = p or {}
    player = DEFAULT_PLAYER.copy()
    player.update({k: p.get(k, player[k]) for k in player.keys()})
    for n in ("level", "xp", "hp", "max_hp", "damage", "score", "combo", "gold", "gold_bonus"):
        try:
            player[n] = int(player.get(n, DEFAULT_PLAYER[n]))
        except Exception:
            player[n] = DEFAULT_PLAYER[n]
    player["level"] = max(1, player["level"])
    player["max_hp"] = max(1, player["max_hp"])
    player["hp"] = max(0, min(player["hp"], player["max_hp"]))
    player["damage"] = max(1, player["damage"])
    player["score"] = max(0, player["score"])
    player["combo"] = max(0, player["combo"])
    player["gold"] = max(0, player["gold"])
    player["gold_bonus"] = max(0, player["gold_bonus"])
    inv = player.get("inventory", {}) or {}
    if not isinstance(inv, dict):
        inv = {}
    new_inv = {}
    for k, v in inv.items():
        if isinstance(k, str):
            try:
                new_inv[k] = max(0, int(v))
            except Exception:
                new_inv[k] = 0
    player["inventory"] = new_inv
    player["shield_active"] = bool(player.get("shield_active", False))
    if not isinstance(player.get("name"), str) or not player["name"].strip():
        player["name"] = DEFAULT_PLAYER["name"]
    return player

def load_users():
    global USERS
    data = safe_json_load(USERS_FILE)
    USERS = data if isinstance(data, dict) else {}
    return USERS

def save_users():
    global USERS
    return safe_json_write(USERS_FILE, USERS)

def load_admins():
    global ADMINS
    data = safe_json_load(ADMINS_FILE)
    ADMINS = data if isinstance(data, dict) else {}
    if "admin" not in ADMINS or not isinstance(ADMINS["admin"], dict):
        ADMINS["admin"] = hash_password("admin123")
        save_admins()
    return ADMINS

def save_admins():
    global ADMINS
    return safe_json_write(ADMINS_FILE, ADMINS)

def load_leaderboard():
    global LEADERBOARD
    data = safe_json_load(LEADERBOARD_FILE)
    if not isinstance(data, list):
        LEADERBOARD = []
    else:
        out = []
        for e in data:
            if isinstance(e, dict) and e.get("name"):
                try:
                    out.append({
                        "name": str(e["name"]),
                        "score": max(0, int(e.get("score", 0))),
                        "level": max(1, int(e.get("level", 1))),
                        "xp": max(0, int(e.get("xp", 0)))
                    })
                except Exception:
                    continue
        LEADERBOARD = out[:10]
    return LEADERBOARD

def save_leaderboard():
    global LEADERBOARD
    return safe_json_write(LEADERBOARD_FILE, LEADERBOARD)

def update_leaderboard_with_player(player: dict):
    if not isinstance(player, dict) or "name" not in player:
        return False
    load_leaderboard()
    LEADERBOARD[:] = [e for e in LEADERBOARD if e.get("name") != player["name"]]
    LEADERBOARD.append({
        "name": player["name"],
        "score": int(player.get("score", 0)),
        "level": int(player.get("level", 1)),
        "xp": int(player.get("xp", 0))
    })
    LEADERBOARD.sort(key=lambda x: x.get("score", 0), reverse=True)
    del LEADERBOARD[10:]
    return save_leaderboard()

def load_questions():
    global QUESTIONS
    data = safe_json_load(QUESTION_FILE)
    if not isinstance(data, list):
        sample = [
            {"question":"What is 2 + 2?","options":["3","4","5","6"],"answer":"4","difficulty":"easy"},
            {"question":"What is the capital of France?","options":["London","Berlin","Paris","Madrid"],"answer":"Paris","difficulty":"medium"},
        ]
        safe_json_write(QUESTION_FILE, sample)
        QUESTIONS = sample
        return QUESTIONS
    valid = []
    for i, q in enumerate(data):
        if not isinstance(q, dict):
            continue
        question = q.get("question","").strip()
        options = q.get("options")
        answer = q.get("answer","").strip()
        if not question or not isinstance(options, list) or len(options) < 2 or not answer:
            continue
        if answer not in options:
            continue
        diff = q.get("difficulty","medium").lower()
        if diff not in ("easy","medium","hard","boss"):
            diff = "medium"
        valid.append({"question": question, "options": options, "answer": answer, "difficulty": diff})
    if not valid:
        print("⚠️ No valid questions found. Creating sample questions.")
        load_questions()
    else:
        QUESTIONS = valid
    return QUESTIONS

def player_save_path(username: str) -> str:
    safe_username = re.sub(r'[<>:"/\\|?*]', '_', username)
    return os.path.join(SAVE_DIR, f"{safe_username}.json")

def load_player(username: str) -> dict:
    ensure_dirs()
    data = safe_json_load(player_save_path(username))
    if not data:
        return normalize_player({"name": username})
    return normalize_player(data)

def save_player(username: str, player: dict) -> bool:
    if not isinstance(player, dict):
        print("⚠️ Invalid player data")
        return False
    return safe_json_write(player_save_path(username), normalize_player(player))

def health_bar(current, maximum, length=20):
    try:
        maximum = max(1, int(maximum))
        current = max(0, min(int(current), maximum))
    except Exception:
        maximum = 1
        current = 0
    filled = max(0, min(length, int(length * current / maximum)))
    return "🟩" * filled + "⬜" * (length - filled) + f" {current}/{maximum} HP"

def username_valid(username: str) -> bool:
    if not username or not (3 <= len(username) <= 20):
        return False
    return bool(re.match(r'^[A-Za-z0-9_-]+$', username))

def register_user():
    load_users()
    username = safe_input("Choose a username (3-20 chars, letters/numbers/_/- only): ").strip()
    if not username_valid(username):
        print("⚠️ Invalid username format.")
        press_enter(); return None
    if any(u.lower() == username.lower() for u in USERS.keys()):
        print("⚠️ Username already exists.")
        press_enter(); return None
    pw = safe_input("Choose a password (minimum 4 characters): ")
    if len(pw) < 4:
        print("⚠️ Password too short."); press_enter(); return None
    confirm = safe_input("Confirm password: ")
    if pw != confirm:
        print("⚠️ Passwords do not match."); press_enter(); return None
    if os.path.exists(player_save_path(username)):
        print("⚠️ Save file collision detected. Choose different username."); press_enter(); return None
    USERS[username] = hash_password(pw)
    if not save_users():
        print("⚠️ Failed to save user account."); press_enter(); return None
    player = normalize_player({"name": username})
    save_player(username, player)
    print(f"✅ Account created for {username}")
    press_enter()
    return username

def login_account(is_admin=False):
    if is_admin:
        load_admins()
        db = ADMINS
        role = "Admin"
    else:
        load_users()
        db = USERS
        role = "User"
    username = safe_input(f"{role} username: ").strip()
    pw = safe_input("Password: ").strip()
    if not username or not pw:
        print("⚠️ Username and password cannot be empty."); press_enter(); return None
    key, stored = _find_record_case_insensitive(db, username)
    if stored and isinstance(stored, dict) and verify_password(pw, stored):
        print(f"✅ {role} logged in as {key if key else username}")
        press_enter()
        return key if not is_admin else True
    print("⚠️ Invalid credentials.")
    press_enter()
    return None

def reset_password():
    load_users()
    username = safe_input("Enter your username: ").strip()
    if not username:
        print("⚠️ Username cannot be empty."); press_enter(); return None
    key, stored = _find_record_case_insensitive(USERS, username)
    if not key:
        print("⚠️ Username not found."); press_enter(); return None
    new_pw = safe_input("Enter a NEW password (minimum 4 characters): ").strip()
    if len(new_pw) < 4:
        print("⚠️ Password must be at least 4 characters long."); press_enter(); return None
    confirm = safe_input("Confirm NEW password: ").strip()
    if new_pw != confirm:
        print("⚠️ Passwords do not match."); press_enter(); return None
    USERS[key] = hash_password(new_pw)
    if save_users():
        print("✅ Password reset successful!"); press_enter(); return key
    print("⚠️ Failed to save password change."); press_enter(); return None

def ask_question(q: dict) -> bool:
    opts = q.get("options", [])
    ans = q.get("answer")
    question_text = q.get("question", "???")
    if not ans or not opts or ans not in opts:
        print("⚠️ Invalid question data."); return False
    print(f"\n❓ {question_text}")
    for i, o in enumerate(opts, 1):
        print(f"   {i}. {o}")
    if DEV_MODE["show_answers"]:
        print(f"💡 [Answer: {ans}]")
    opts_norm = [o.lower().strip() for o in opts]
    ans_norm = ans.lower().strip()
    for attempt in range(3):
        user_input = safe_input(f"👉 Your answer (attempt {attempt+1}/3): ")
        if not user_input:
            print("⚠️ Please enter an answer."); continue
        if user_input.isdigit():
            idx = int(user_input) - 1
            if 0 <= idx < len(opts):
                return opts[idx] == ans
            print(f"⚠️ Enter a number between 1 and {len(opts)}."); continue
        u = user_input.lower().strip()
        if u == ans_norm:
            return True
        for i, on in enumerate(opts_norm):
            if u == on:
                return opts[i] == ans
        print("⚠️ Invalid input. Use an option number or exact option text.")
    print(f"⚠️ Max attempts. The correct answer was: {ans}")
    return False

def get_xp_required(level: int) -> int:
    try:
        level = max(1, int(level))
        if level > 100:
            return int(50000 + (level - 100) * 1000)
        base_xp = 120
        level_multiplier = level ** 1.3
        bonus = level * 20
        result = base_xp * level_multiplier + bonus
        result = max(result, 50 + level * 10)
        return min(int(result), 1000000)
    except Exception:
        return 1000

def check_level_up(player: dict) -> bool:
    leveled = False
    while player["xp"] >= get_xp_required(player["level"]):
        req = get_xp_required(player["level"])
        player["xp"] -= req
        player["level"] += 1
        leveled = True
        clear_screen()
        print(f"\n🎉 {player['name']} leveled up! Now Level {player['level']}")
        print(f"📈 Next level requires: {get_xp_required(player['level'])} XP")
        while True:
            print("Choose your upgrade:")
            print("1) 🛡️ +15 Max HP")
            print("2) ⚔️ +3 Damage")
            print("3) 💰 +2 Gold per victory bonus")
            choice = safe_input("👉 Choose (1, 2, or 3): ")
            if choice == "1":
                player["max_hp"] += 15
                print("🛡️ Max HP increased by 15!"); break
            if choice == "2":
                player["damage"] += 3
                print("⚔️ Damage increased by 3!"); break
            if choice == "3":
                player["gold_bonus"] = player.get("gold_bonus", 0) + 2
                print("💰 Gold bonus increased by 2 per victory!"); break
            print("⚠️ Please enter 1, 2, or 3.")
        old_hp = player["hp"]
        player["hp"] = player["max_hp"]
        if player["hp"] > old_hp:
            print(f"❤️ Restored {player['hp'] - old_hp} HP! Now at full health.")
        press_enter()
    return leveled

def get_level_scaling_factor(player_level: int) -> float:
    if player_level <= 1:
        return 1.0
    if player_level <= 5:
        return 1.0 + (player_level - 1) * 0.3
    if player_level <= 10:
        return 2.2 + (player_level - 5) * 0.25
    return 3.45 + (player_level - 10) * 0.2

def get_enemy_name_variant(base_name: str, player_level: int) -> str:
    variants = {
        "Slime": ["Slime","Green Slime","Acid Slime","Giant Slime","Toxic Slime","Crystal Slime","Shadow Slime","Ancient Slime","Void Slime","Primordial Slime"],
        "Goblin": ["Goblin","Goblin Scout","Goblin Warrior","Goblin Berserker","Goblin Champion","Goblin Chieftain","Goblin Warlord","Goblin King","Demon Goblin","Goblin Overlord"],
        "Orc": ["Orc","Orc Brute","Orc Warrior","Orc Savage","Orc Destroyer","Orc Warchief","Orc Juggernaut","Orc Warlord","Demon Orc","Orc Titan"],
        "Dragon": ["Dragon","Young Dragon","Adult Dragon","Elder Dragon","Ancient Dragon","Wyrm Dragon","Shadow Dragon","Void Dragon","Primordial Dragon","Cosmic Dragon"],
    }
    lst = variants.get(base_name, [base_name])
    if player_level <= 1:
        return lst[0]
    idx = min(len(lst)-1, (player_level-1)//1 if player_level<=10 else 8 + (player_level-10)//3)
    return lst[idx]

def make_enemy(diff: str, player_level: int=1) -> dict:
    base = {
        "easy": {"name":"Slime","hp":35,"damage":6,"xp_reward":10,"gold_base":25},
        "medium": {"name":"Goblin","hp":60,"damage":10,"xp_reward":20,"gold_base":40},
        "hard": {"name":"Orc","hp":90,"damage":16,"xp_reward":35,"gold_base":65},
        "boss": {"name":"Dragon","hp":150,"damage":25,"xp_reward":75,"gold_base":120},
    }.get(diff, {"name":"Goblin","hp":60,"damage":10,"xp_reward":20,"gold_base":40})
    f = get_level_scaling_factor(player_level)
    v = random.uniform(0.9, 1.1)
    hp = max(int(base["hp"] * f * v), base["hp"])
    dmg = max(int(base["damage"] * f * v), base["damage"])
    return {
        "name": get_enemy_name_variant(base["name"], player_level),
        "hp": hp,
        "max_hp": hp,
        "damage": dmg,
        "xp_reward": int(base["xp_reward"] * (1 + (player_level - 1) * 0.1)),
        "gold_base": int(base["gold_base"] * (1 + (player_level - 1) * 0.15))
    }

def get_item_drop_chance(difficulty: str, player_level: int) -> float:
    base = {"easy":0.15,"medium":0.2,"hard":0.25,"boss":0.4}.get(difficulty,0.2)
    level_bonus = min(0.2, player_level * 0.02)
    return base + level_bonus

def apply_victory_rewards(player: dict, enemy: dict, diff: str):
    xp_reward = enemy.get("xp_reward", 10)
    player["xp"] += xp_reward
    base_gold = enemy.get("gold_base", random.randint(30,100))
    level_bonus = player["level"] * 3
    gb = player.get("gold_bonus", 0)
    total_gold = base_gold + level_bonus + gb
    player["gold"] = player.get("gold", 0) + total_gold
    print(f"⭐ XP +{xp_reward}")
    if gb:
        print(f"💰 Gold +{base_gold} + {level_bonus} (level) + {gb} (bonus) = {total_gold}")
    else:
        print(f"💰 Gold +{base_gold} + {level_bonus} (level bonus) = {total_gold}")
    if random.random() < get_item_drop_chance(diff, player["level"]):
        item_key = random.choice(list(ITEMS.keys()))
        add_item(player, item_key)
        print(f"🎁 You found a {ITEMS[item_key]['name']}!")

def add_item(player: dict, item_key: str, qty: int=1) -> bool:
    if item_key not in ITEMS: return False
    try:
        qty = max(1, int(qty))
        inv = player.setdefault("inventory", {})
        inv[item_key] = inv.get(item_key, 0) + qty
        return True
    except Exception:
        return False

def use_item(player: dict, item_key: str) -> bool:
    inv = player.setdefault("inventory", {})
    if inv.get(item_key,0) <= 0:
        print("⚠️ You don't have that item.") ; return False
    if item_key == "potion":
        heal = 30
        old = player["hp"]
        player["hp"] = min(player["max_hp"], player["hp"] + heal)
        actual = player["hp"] - old
        inv[item_key] -= 1
        print(f"🧪 You used a Healing Potion. Restored {actual} HP.")
        return True
    if item_key == "shield":
        inv[item_key] -= 1
        player["shield_active"] = True
        print("🛡️ Shield activated. It will block the next hit.")
        return True
    print("⚠️ Unknown item."); return False

def show_inventory(player: dict):
    clear_screen()
    print("🎒 Inventory\n" + "─"*30)
    inv = player.get("inventory", {})
    if not inv or not any(v>0 for v in inv.values()):
        print("Empty")
    else:
        for k, v in inv.items():
            if v > 0:
                it = ITEMS.get(k, {"name":k,"desc":"Unknown"})
                print(f"{it['name']}: {v} - {it.get('desc','')}")
    print(f"\nGold: {player.get('gold',0)}")
    print("─"*30)
    press_enter()

def shop_menu(player: dict):
    while True:
        clear_screen()
        print("🏪 Adventure Shop\n" + "─"*40)
        for i,(k,it) in enumerate(ITEMS.items(),1):
            print(f"{i}. {it['name']:<15} - {it['desc']}\n   Price: {it['price']} gold\n")
        print("0. Exit Shop\n" + "─"*40)
        print(f"💰 Your Gold: {player.get('gold',0)}\n")
        choice = safe_input("👉 Enter item number to buy (or 0 to exit): ")
        if choice == "0": break
        try:
            idx = int(choice)-1
            if 0 <= idx < len(ITEMS):
                key = list(ITEMS.keys())[idx]
                it = ITEMS[key]
                if player.get("gold",0) >= it["price"]:
                    confirm = safe_input(f"Buy {it['name']} for {it['price']} gold? (Y/n): ").lower()
                    if confirm in ('','y','yes'):
                        player["gold"] -= it["price"]
                        add_item(player, key)
                        print(f"✅ Purchased {it['name']}!")
                        press_enter()
                    else:
                        print("❌ Purchase cancelled."); press_enter()
                else:
                    print("⚠️ Not enough gold!"); press_enter()
            else:
                print("⚠️ Invalid item number."); press_enter()
        except Exception:
            print("⚠️ Please enter a valid number."); press_enter()

def battle(player: dict, enemy: dict, qs: list, diff: str="easy") -> bool:
    if not qs:
        print("⚠️ No questions available for this difficulty."); press_enter(); return False
    player.setdefault("shield_active", False)
    questions_copy = qs.copy()
    random.shuffle(questions_copy)
    qidx = 0
    while player["hp"] > 0 and enemy["hp"] > 0:
        clear_screen()
        print("╔" + "═"*40 + "╗")
        print(f"{('⚔️ Battle vs ' + enemy['name']):^40}")
        print("╚" + "═"*40 + "╝\n")
        print(f"🧑 {player['name']}\n   {health_bar(player['hp'], player['max_hp'])}")
        print(f"   ⚔️ Damage: {player['damage']} | 💥 Combo: {player['combo']} | ⭐ XP: {player['xp']}")
        print(f"\n👹 {enemy['name']}\n   {health_bar(enemy['hp'], enemy['max_hp'])}\n   ⚔️ Damage: {enemy['damage']}")
        if player.get("shield_active"): print("\n🛡️ Shield is active!")
        print("\n" + "─"*40)
        if DEV_MODE["instant_win"]:
            print("💻 Dev Mode: Instant Win!"); enemy["hp"] = 0; break
        print("\nOptions:\n[A] Answer question\n[I] Inventory\n[S] Use shop\n[Q] Quit battle (forfeit)")
        opt = safe_input("👉 Choose (or press Enter to answer): ").lower()
        if opt == "i":
            show_inventory(player); continue
        if opt == "s":
            shop_menu(player); continue
        if opt == "q":
            confirm = safe_input("Are you sure you want to forfeit? (y/N): ").lower()
            if confirm in ['y','yes']:
                print("You forfeited the battle."); press_enter(); return False
            continue
        if qidx >= len(questions_copy):
            random.shuffle(questions_copy); qidx = 0
        q = questions_copy[qidx]; qidx += 1
        if ask_question(q):
            combo_bonus = min(player.get("combo",0), 10)
            total_damage = player["damage"] + combo_bonus
            print(f"✅ Correct! You deal {total_damage} damage!")
            enemy["hp"] = max(0, enemy["hp"] - total_damage)
            player["combo"] = player.get("combo",0) + 1
            score_reward = 50 + combo_bonus * 5
            player["score"] = player.get("score",0) + score_reward
            print(f"💰 Score +{score_reward}")
            if check_level_up(player):
                pass
        else:
            print("❌ Wrong answer!")
            if DEV_MODE["god_mode"]:
                print("💻 Dev Mode: No damage taken!")
            else:
                if player.get("shield_active", False):
                    print("🛡️ Your shield blocked the attack!"); player["shield_active"] = False
                else:
                    dmg = enemy.get("damage", 0)
                    print(f"👹 {enemy['name']} hits you for {dmg} damage!")
                    player["hp"] = max(0, player["hp"] - dmg)
            player["combo"] = 0
        if enemy["hp"] <= 0:
            print(f"\n🎉 Victory! You defeated the {enemy['name']}!")
            apply_victory_rewards(player, enemy, diff)
            press_enter(); return True
        if player["hp"] <= 0:
            print(f"\n💀 Defeat! You were defeated by the {enemy['name']}...")
            gold_loss = min(player.get("gold",0)//4, 50)
            xp_loss = min(player.get("xp",0)//3, 30)
            player["gold"] = max(0, player.get("gold",0) - gold_loss)
            player["xp"] = max(0, player.get("xp",0) - xp_loss)
            if gold_loss: print(f"💸 Lost {gold_loss} gold")
            if xp_loss: print(f"📉 Lost {xp_loss} XP")
            player["hp"] = player["max_hp"] // 4
            print(f"❤️ Recovered to {player['hp']} HP")
            press_enter(); return False
        press_enter()
    return player["hp"] > 0

def show_leaderboard():
    load_leaderboard()
    clear_screen()
    print("🏆 Leaderboard\n" + "─"*50)
    if not LEADERBOARD:
        print("No scores yet.")
    else:
        for i, e in enumerate(LEADERBOARD,1):
            name = e.get("name","Unknown")[:10]
            print(f"{i:2}. {name:<10} | Score: {e.get('score',0):<6} | Lv: {e.get('level',1):<3} | XP: {e.get('xp',0)}")
    print("─"*50)

def dev_menu():
    while True:
        clear_screen()
        print("🔧 Dev/Admin Menu\n" + "─"*35)
        print(f"1. God Mode:     {'🟢 ON' if DEV_MODE['god_mode'] else '🔴 OFF'}")
        print(f"2. Show Answers: {'🟢 ON' if DEV_MODE['show_answers'] else '🔴 OFF'}")
        print(f"3. Instant Win:  {'🟢 ON' if DEV_MODE['instant_win'] else '🔴 OFF'}")
        print("4. View All Users\n5. Reset Leaderboard\n6. Create Sample Questions\n7. View Questions Statistics\n8. Back to Main Menu")
        choice = safe_input("👉 Choose: ")
        if choice == "1":
            DEV_MODE["god_mode"] = not DEV_MODE["god_mode"]; print("God Mode toggled."); press_enter()
        elif choice == "2":
            DEV_MODE["show_answers"] = not DEV_MODE["show_answers"]; print("Show Answers toggled."); press_enter()
        elif choice == "3":
            DEV_MODE["instant_win"] = not DEV_MODE["instant_win"]; print("Instant Win toggled."); press_enter()
        elif choice == "4":
            load_users(); clear_screen(); print("👥 Registered Users:\n" + "─"*30)
            if USERS:
                for i,u in enumerate(USERS.keys(),1):
                    pd = load_player(u)
                    print(f"{i:2}. {u:<15} | Lv: {pd.get('level',1):<2} | Score: {pd.get('score',0)}")
            else:
                print("No users registered.")
            press_enter()
        elif choice == "5":
            c = safe_input("Reset leaderboard? (y/N): ").lower()
            if c in ('y','yes'):
                save_leaderboard(); LEADERBOARD.clear(); safe_json_write(LEADERBOARD_FILE, LEADERBOARD); print("✅ Leaderboard reset.")
            else:
                print("❌ Reset cancelled.")
            press_enter()
        elif choice == "6":
            create_sample_questions(); press_enter()
        elif choice == "7":
            show_question_stats(); press_enter()
        elif choice == "8":
            break
        else:
            print("⚠️ Invalid choice."); press_enter()

def create_sample_questions():
    sample_questions = [
        {"question":"What is 2 + 2?","options":["3","4","5","6"],"answer":"4","difficulty":"easy"},
        {"question":"What is the capital of France?","options":["London","Berlin","Paris","Madrid"],"answer":"Paris","difficulty":"easy"},
        {"question":"What is 15 × 8?","options":["110","120","130","140"],"answer":"120","difficulty":"medium"},
        {"question":"Which planet is known as the Red Planet?","options":["Venus","Mars","Jupiter","Saturn"],"answer":"Mars","difficulty":"medium"},
        {"question":"What is the square root of 144?","options":["11","12","13","14"],"answer":"12","difficulty":"hard"},
        {"question":"Who wrote 'To Kill a Mockingbird'?","options":["Harper Lee","Mark Twain","Ernest Hemingway","F. Scott Fitzgerald"],"answer":"Harper Lee","difficulty":"hard"},
        {"question":"What is the chemical symbol for Gold?","options":["Go","Gd","Au","Ag"],"answer":"Au","difficulty":"boss"},
        {"question":"In which year did World War II end?","options":["1944","1945","1946","1947"],"answer":"1945","difficulty":"boss"}
    ]
    if safe_json_write(QUESTION_FILE, sample_questions):
        print(f"✅ Created {QUESTION_FILE} with {len(sample_questions)} sample questions.")
    else:
        print(f"⚠️ Failed to create {QUESTION_FILE}")

def show_question_stats():
    try:
        qs = load_questions()
        clear_screen()
        print("📊 Question Statistics\n" + "─"*30)
        total = len(qs)
        print(f"Total Questions: {total}\nBy Difficulty:")
        diffs = {}
        for q in qs:
            diffs[q.get("difficulty","unknown")] = diffs.get(q.get("difficulty","unknown"),0) + 1
        for d,c in sorted(diffs.items()):
            print(f"  {d.capitalize()}: {c}")
        print(f"\nFile: {QUESTION_FILE}")
    except Exception as e:
        print(f"⚠️ Error analyzing questions: {e}")

def use_item_menu(player: dict):
    while True:
        clear_screen()
        print("🧪 Use Item\n" + "─"*30)
        available = [(k,v,ITEMS[k]) for k,v in player.get("inventory", {}).items() if v>0 and k in ITEMS]
        if not available:
            print("🎒 No usable items in inventory."); press_enter(); return
        print("Available Items:")
        for i,(k,q,it) in enumerate([(a[0],a[1],a[2]) for a in available],1):
            pass
        for i, (key, qty, info) in enumerate(available,1):
            print(f"{i}. {info['name']} x{qty} - {info['desc']}")
        print("0. Back to main menu")
        print(f"\n📊 Current HP: {health_bar(player['hp'], player['max_hp'], 15)}")
        choice = safe_input("👉 Choose item to use: ")
        if choice == "0": break
        try:
            idx = int(choice)-1
            if 0 <= idx < len(available):
                item_key = available[idx][0]
                if use_item(player, item_key):
                    press_enter()
                    if not any(v>0 for v in player.get("inventory",{}).values()):
                        break
            else:
                print("⚠️ Invalid item number."); press_enter()
        except Exception:
            print("⚠️ Please enter a valid number."); press_enter()

def battle_menu(player: dict, username: str, questions: list):
    while True:
        clear_screen()
        print("⚔️ Choose Your Battle!\n" + "─"*30)
        print("1. 🟢 Easy Battle   (Slimes)\n2. 🟡 Medium Battle (Goblins)\n3. 🔴 Hard Battle   (Orcs)\n4. 💀 Boss Battle   (Dragons)\n5. 🏠 Return to Main Menu")
        print(f"\n📊 Your Stats: Lv.{player['level']} | {health_bar(player['hp'], player['max_hp'], 12)}")
        diff_choice = safe_input("👉 Choose your challenge: ")
        if diff_choice == "5": break
        mapping = {"1":"easy","2":"medium","3":"hard","4":"boss"}
        if diff_choice not in mapping:
            print("⚠️ Invalid choice."); press_enter(); continue
        diff = mapping[diff_choice]
        if player["hp"] <= 0:
            print("⚠️ You need to heal before battling!"); press_enter(); continue
        filtered = [q for q in questions if (diff == "medium" and q.get("difficulty") in ("easy","medium")) or
                    (diff == "hard" and q.get("difficulty") in ("medium","hard")) or
                    (diff == "easy" and q.get("difficulty") == "easy") or
                    (diff == "boss" and q.get("difficulty") == "boss") or
                    (diff not in ("easy","medium","hard","boss"))]
        if not filtered:
            filtered = questions
        enemy = make_enemy(diff, player["level"])
        print(f"\n🎯 Preparing {diff.capitalize()} battle against {enemy['name']}...")
        print(f"👹 Enemy: {health_bar(enemy['hp'], enemy['max_hp'], 12)} | ⚔️ {enemy['damage']}")
        confirm = safe_input("Ready to fight? (Y/n): ").lower()
        if confirm not in ('','y','yes'):
            print("❌ Battle cancelled."); press_enter(); continue
        result = battle(player, enemy, filtered, diff)
        save_player(username, player)
        update_leaderboard_with_player(player)
        if result:
            if diff == "boss":
                print("🎉 Congratulations! You've defeated a mighty boss!"); press_enter(); break
            else:
                while True:
                    print("\n🎉 Victory! What would you like to do next?")
                    print("1. Fight another enemy (same difficulty)\n2. Choose different difficulty\n3. Return to main menu")
                    next_action = safe_input("👉 Choose: ")
                    if next_action in ("1","2","3"): break
                    print("⚠️ Invalid choice.")
                if next_action == "1":
                    continue
                if next_action == "2":
                    continue
                return
        else:
            print("💀 Perhaps try an easier difficulty or heal up first..."); press_enter(); break

def player_game_loop(player: dict, username: str, questions: list):
    while True:
        clear_screen()
        req = get_xp_required(player['level'])
        xp_progress = f"{player['xp']}/{req}"
        print(f"╔{'═'*35}╗\n  Welcome back, {player['name'][:15]}!\n╚{'═'*35}╝\n")
        print(f"   Level: {player['level']} | XP: {xp_progress} ({(player['xp']/req)*100:.1f}%)")
        print(f"   {health_bar(player['hp'], player['max_hp'], 15)}")
        print(f"   💰 Gold: {player.get('gold', 0)} | 🏆 Score: {player['score']}\n")
        print("🎮 Game Menu:\n1. 🗡️  Battle Enemies\n2. 🏆 View Leaderboard\n3. 🎒 Check Inventory\n4. 🏪 Visit Shop\n5. 🧪 Use Item\n6. 💾 Save & Logout")
        choice = get_valid_choice("\n👉 Choose your action: ", ["1","2","3","4","5","6"])
        if choice == "1":
            battle_menu(player, username, questions)
        elif choice == "2":
            show_leaderboard(); press_enter()
        elif choice == "3":
            show_inventory(player)
        elif choice == "4":
            shop_menu(player); save_player(username, player)
        elif choice == "5":
            use_item_menu(player); save_player(username, player)
        elif choice == "6":
            print("💾 Saving your progress...")
            if save_player(username, player):
                update_leaderboard_with_player(player)
                print("✅ Game saved successfully!")
            else:
                print("⚠️ Error saving game!")
            print("👋 See you next time!"); press_enter(); break
        else:
            print("⚠️ Invalid choice."); press_enter()

def main():
    try:
        ensure_dirs()
        load_users(); load_admins(); load_questions(); load_leaderboard()
        print("🎮 Loading Quiz Battle Game...")
        print(f"✅ Game ready with {len(QUESTIONS)} questions!")
        while True:
            clear_screen()
            print("╔" + "═"*40 + "╗")
            print("       ⚔️ Quiz Battle Game (Public Test Build) 1.1 ⚔️")
            print("╚" + "═"*40 + "╝\n")
            print("🎯 Test your knowledge in epic battles!\n")
            print("1️⃣ Play Game (Login/Register)\n2️⃣ Admin Panel\n3️⃣ View Leaderboard\n4️⃣ Quit Game")
            choice = get_valid_choice("\n👉 Choose your adventure: ", ["1","2","3","4"])
            if choice == "1":
                clear_screen()
                print("🔐 Player Access\n" + "─"*30)
                print("1. Login to existing account\n2. Create new account\n3. Reset forgotten password\n4. Back to main menu")
                sub = get_valid_choice("👉 Choose: ", ["1","2","3","4"])
                username = None
                if sub == "1":
                    username = login_account(is_admin=False)
                elif sub == "2":
                    username = register_user()
                elif sub == "3":
                    username = reset_password()
                elif sub == "4":
                    continue
                if not username:
                    continue
                player = load_player(username)
                player_game_loop(player, username, QUESTIONS)
            elif choice == "2":
                clear_screen(); print("🔑 Admin Access Required")
                if login_account(is_admin=True):
                    dev_menu()
            elif choice == "3":
                show_leaderboard(); press_enter()
            elif choice == "4":
                print("👋 Thanks for playing Quiz Battle Game!\n💫 Your progress has been saved. See you next time!")
                break
    except KeyboardInterrupt:
        print("\n\n👋 Game interrupted. Your progress has been saved!")
    except Exception as e:
        print(f"\n⚠️ An unexpected error occurred: {e}\nPlease restart the game. Your progress should be saved.")

if __name__ == "__main__":
    main()
