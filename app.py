import random
import time
import streamlit as st

# Page Config
st.set_page_config(
    page_title="2v2 Tag Team RPG", page_icon="⚔️", layout="wide"
)

# --- GAME DATA & CLASSES ---


class Character:

    def __init__(self, name, hp, dmg, defense, spe, potency, is_player=False):
        self.name = name
        self.max_hp = hp
        self.hp = hp
        self.dmg = dmg
        self.defense = defense
        self.spe = spe
        self.max_potency = potency
        # Start on full cooldown so special cannot be used on the very first turn
        self.potency_cooldown = potency
        self.is_player = is_player

        # Status modifiers
        self.shield_active = False
        self.special_active = False  # Active for the current turn
        self.special_primed = False  # Queued up to activate on the upcoming turn
        self.boost_active = False  # Increases crit chance by 15% for the next turn

        # Loadout moves chosen before battle
        self.loadout = []

    def reset_status(self):
        self.shield_active = False


CHAR_TEMPLATES = {
    "A": {
        "hp": 150,
        "dmg": 7.5,
        "def": 6.0,
        "spe": 10,
        "potency": 3,
        "desc": "Deals +20 flat damage next turn",
    },
    "B": {
        "hp": 95,
        "dmg": 8.0,
        "def": 5.0,
        "spe": 18,
        "potency": 3,
        "desc": "50% chance to avoid all attacks next turn",
    },
    "C": {
        "hp": 190,  # Balance Patch: Reduced from 195 to 190
        "dmg": 6.5,
        "def": 8.0,
        "spe": 4,
        "potency": 5,
        "desc": "Defense modifier RNG becomes (5-10) next turn",
    },
    "D": {
        "hp": 170,
        "dmg": 5.5,
        "def": 5.5,
        "spe": 12,
        "potency": 4,
        "desc": "Heals 25 HP next turn",  # Balance Patch description update
    },
}

ALL_MOVES = [
    "Attack",
    "Shield",
    "Heal",
    "Boost",
    "Spread attack (3)",
    "Spread attack (2)",
]


# --- INITIALIZE SESSION STATE ---
if "game_state" not in st.session_state:
    st.session_state.game_state = "setup"  # setup, battle, game_over
    st.session_state.battle_phase = "input"  # input, animating
    st.session_state.players = []
    st.session_state.round_num = 1
    st.session_state.log = []
    st.session_state.anim_actions = []
    st.session_state.anim_index = 0
    st.session_state.manual_input_index = 0
    st.session_state.temp_round_actions = {}


# --- UI: SETUP SCREEN ---
if st.session_state.game_state == "setup":
    st.title("⚔️ Season 2: 2v2 Tag Team Chaos")
    st.markdown(
        "Welcome to Tag Team mode! Configure your team's classes, allies, and loadouts."
    )

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Team 1")
        t1_p1_name = st.selectbox("Team 1, Player 1", ["Gemini", "ChatGPT", "Perplexity", "DeepSeek"], index=0, key="t1_p1_n")
        t1_p1_class = st.selectbox("T1P1 Class", ["A", "B", "C", "D"], index=1, key="t1_p1_c")
        t1_p1_loadout = st.multiselect("T1P1 Loadout", ALL_MOVES, default=["Attack", "Shield", "Heal"], key="t1_p1_l")
        
        st.divider()
        t1_p2_name = st.selectbox("Team 1, Player 2", ["ChatGPT", "Gemini", "Perplexity", "DeepSeek"], index=1, key="t1_p2_n")
        t1_p2_class = st.selectbox("T1P2 Class", ["A", "B", "C", "D"], index=1, key="t1_p2_c")
        t1_p2_loadout = st.multiselect("T1P2 Loadout", ALL_MOVES, default=["Attack", "Shield", "Heal"], key="t1_p2_l")

    with col2:
        st.subheader("Team 2")
        t2_p1_name = st.selectbox("Team 2, Player 1", ["Perplexity", "Gemini", "ChatGPT", "DeepSeek"], index=0, key="t2_p1_n")
        t2_p1_class = st.selectbox("T2P1 Class", ["A", "B", "C", "D"], index=0, key="t2_p1_c")
        t2_p1_loadout = st.multiselect("T2P1 Loadout", ALL_MOVES, default=["Attack", "Shield", "Heal"], key="t2_p1_l")
        
        st.divider()
        t2_p2_name = st.selectbox("Team 2, Player 2", ["DeepSeek", "Gemini", "ChatGPT", "Perplexity"], index=0, key="t2_p2_n")
        t2_p2_class = st.selectbox("T2P2 Class", ["A", "B", "C", "D"], index=0, key="t2_p2_c")
        t2_p2_loadout = st.multiselect("T2P2 Loadout", ALL_MOVES, default=["Attack", "Shield", "Heal"], key="t2_p2_l")

    st.divider()
    
    if st.button("Start 2v2 Tag Team Match", type="primary", use_container_width=True):
        configs = [
            (t1_p1_name, t1_p1_class, t1_p1_loadout, True),
            (t1_p2_name, t1_p2_class, t1_p2_loadout, True),
            (t2_p1_name, t2_p1_class, t2_p1_loadout, False),
            (t2_p2_name, t2_p2_class, t2_p2_loadout, False),
        ]
        
        players_list = []
        for name, char_key, loadout, is_t1 in configs:
            c_data = CHAR_TEMPLATES[char_key]
            c_obj = Character(
                name=f"{name} (Char {char_key})",
                hp=c_data["hp"],
                dmg=c_data["dmg"],
                defense=c_data["def"],
                spe=c_data["spe"],
                potency=c_data["potency"],
                is_player=is_t1,
            )
            c_obj.loadout = loadout if loadout else ["Attack"]
            players_list.append(c_obj)

        st.session_state.players = players_list
        st.session_state.game_state = "battle"
        st.session_state.battle_phase = "input"
        st.session_state.round_num = 1
        st.session_state.log = ["2v2 Tag Team match started! Team 1 vs Team 2."]
        st.session_state.manual_input_index = 0
        st.session_state.temp_round_actions = {}
        st.rerun()


# --- HELPER FUNCTIONS FOR COMBAT ---
def calculate_damage(attacker, defender, base_multiplier=1.0):
    if defender.special_active and "Char C" in defender.name:
        def_mod = random.randint(5, 10) * defender.defense
    else:
        def_mod = random.randint(0, 5) * defender.defense

    raw_dmg = (random.randint(0, 10) * attacker.dmg) * base_multiplier

    crit_roll = random.randint(0, 3) * attacker.spe
    is_crit = (
        random.choice([True, False])
        if crit_roll > 20
        else (random.random() * 100 < crit_roll)
    )
    
    if attacker.boost_active:
        if random.random() < 0.15:
            is_crit = True
        attacker.boost_active = False

    if is_crit:
        raw_dmg *= 2

    final_dmg = max(1.0, raw_dmg - def_mod)

    if attacker.special_active and "Char A" in attacker.name:
        final_dmg += 20.0

    if defender.shield_active:
        final_dmg *= 0.5

    return round(final_dmg, 1), is_crit


def execute_action(actor_idx, action, target_indices, all_players):
    log_messages = []
    attacker = all_players[actor_idx]

    if attacker.hp <= 0:
        return log_messages

    attacker.special_active = False
    if attacker.special_primed:
        attacker.special_active = True
        attacker.special_primed = False
        if "Char B" in attacker.name:
            log_messages.append(f"✨ {attacker.name}'s Special is active: 50% dodge chance!")
        elif "Char A" in attacker.name:
            log_messages.append(f"✨ {attacker.name}'s Special is active: +20 flat damage boost!")
        elif "Char C" in attacker.name:
            log_messages.append(f"✨ {attacker.name}'s Special is active: Enhanced defense RNG!")
        elif "Char D" in attacker.name:
            heal_amt = 25.0  # Balance Patch: Class D special heal increased to 25
            attacker.hp = min(attacker.max_hp, attacker.hp + heal_amt)
            log_messages.append(f"✨ {attacker.name}'s Special is active: Healed for **{heal_amt} HP**!")

    if attacker.potency_cooldown > 0:
        attacker.potency_cooldown -= 1

    if attacker.potency_cooldown == 0 and not attacker.special_active:
        attacker.special_primed = True
        attacker.potency_cooldown = attacker.max_potency
        log_messages.append(f"⚡ {attacker.name} charges up their Special ability for next turn!")

    if action == "Attack":
        if target_indices:
            target = all_players[target_indices[0]]
            if target.hp > 0:
                if target.special_active and "Char B" in target.name and random.random() < 0.5:
                    log_messages.append(f"💨 {target.name} avoided {attacker.name}'s attack completely using Special!")
                else:
                    dmg, crit = calculate_damage(attacker, target)
                    target.hp = max(0.0, target.hp - dmg)
                    crit_txt = " (CRITICAL HIT!)" if crit else ""
                    log_messages.append(f"⚔️ {attacker.name} attacked {target.name} for **{dmg} damage**{crit_txt}.")

    elif action == "Shield":
        attacker.shield_active = True
        log_messages.append(f"🛡️ {attacker.name} raised a Shield (incoming damage halved this turn).")

    elif action == "Heal":
        if target_indices:
            target = all_players[target_indices[0]]
        else:
            target = attacker
        
        # Balance Patch: Class D base heal increased to 25 (or keeps scaling with max HP, but here set to flat 25 per balance rule)
        heal_amt = 25.0 if "Char D" in target.name else round(target.max_hp * 0.2, 1)
        target.hp = min(target.max_hp, target.hp + heal_amt)
        if target == attacker:
            log_messages.append(f"💚 {attacker.name} healed themselves for **{heal_amt} HP**.")
        else:
            log_messages.append(f"💚 {attacker.name} healed their ally {target.name} for **{heal_amt} HP**.")

    elif action == "Boost":
        if target_indices:
            target = all_players[target_indices[0]]
        else:
            target = attacker
            
        target.boost_active = True
        if target == attacker:
            log_messages.append(f"🔮 {attacker.name} boosts themselves for next turn.")
        else:
            log_messages.append(f"🔮 {attacker.name} boosts their ally {target.name} for next turn.")

    return log_messages


# --- UI: BATTLE SCREEN ---
if st.session_state.game_state == "battle":
    st.title(f"⚔️ Tag Team Arena — Round {st.session_state.round_num}")

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Team 1")
        t1_cols = st.columns(2)
        for i in [0, 1]:
            p = st.session_state.players[i]
            with t1_cols[i]:
                st.markdown(f"**{p.name}**")
                st.markdown(f"HP: `{p.hp}/{p.max_hp}`")
                st.progress(float(max(0.0, p.hp) / p.max_hp))
                status_txt = "✨ SPECIAL" if p.special_active else ("⚡ PRIMING" if p.special_primed else "Ready")
                st.caption(f"SPE: {p.spe} | CD: {p.potency_cooldown} | {status_txt}")

    with col2:
        st.subheader("Team 2")
        t2_cols = st.columns(2)
        for idx, i in enumerate([2, 3]):
            p = st.session_state.players[i]
            with t2_cols[idx]:
                st.markdown(f"**{p.name}**")
                st.markdown(f"HP: `{p.hp}/{p.max_hp}`")
                st.progress(float(max(0.0, p.hp) / p.max_hp))
                status_txt = "✨ SPECIAL" if p.special_active else ("⚡ PRIMING" if p.special_primed else "Ready")
                st.caption(f"SPE: {p.spe} | CD: {p.potency_cooldown} | {status_txt}")

    st.divider()

    # --- ANIMATION PHASE ---
    if st.session_state.battle_phase == "animating":
        st.info("🎬 Resolving round actions sequentially...")

        if st.session_state.anim_index < len(st.session_state.anim_actions):
            actor_idx, action_desc, target_indices = st.session_state.anim_actions[
                st.session_state.anim_index
            ]

            if actor_idx is None:
                st.session_state.log.append(action_desc)
            else:
                action_logs = execute_action(
                    actor_idx,
                    action_desc,
                    target_indices,
                    st.session_state.players,
                )
                st.session_state.log.extend(action_logs)

            st.session_state.anim_index += 1
            time.sleep(1.0)
            st.rerun()
        else:
            hp_summary = "    📋 End of Round HP: " + ", ".join(
                [f"{p.name.split(' (')[0]}: {p.hp}/{p.max_hp}" for p in st.session_state.players]
            )
            st.session_state.log.append(hp_summary)

            t1_alive = any(p.hp > 0 for p in st.session_state.players[:2])
            t2_alive = any(p.hp > 0 for p in st.session_state.players[2:])

            if not t1_alive or not t2_alive:
                st.session_state.game_state = "game_over"
            else:
                st.session_state.round_num += 1
                st.session_state.battle_phase = "input"
                st.session_state.manual_input_index = 0
                st.session_state.temp_round_actions = {}
            st.rerun()

    # --- INPUT PHASE ---
    elif st.session_state.battle_phase == "input":
        t1_alive = any(p.hp > 0 for p in st.session_state.players[:2])
        t2_alive = any(p.hp > 0 for p in st.session_state.players[2:])
        if not t1_alive or not t2_alive:
            st.session_state.game_state = "game_over"
            st.rerun()

        while (
            st.session_state.manual_input_index < len(st.session_state.players)
            and (
                st.session_state.players[st.session_state.manual_input_index].hp <= 0
                or st.session_state.manual_input_index in st.session_state.temp_round_actions
            )
        ):
            st.session_state.manual_input_index += 1

        if st.session_state.manual_input_index >= len(st.session_state.players):
            round_actions = [(None, f"--- Round {st.session_state.round_num} ---", [])]
            
            actor_action_pairs = []
            for actor_idx, (act, tgts) in st.session_state.temp_round_actions.items():
                actor_action_pairs.append((actor_idx, act, tgts))

            random.shuffle(actor_action_pairs)
            actor_action_pairs.sort(
                key=lambda item: (
                    1 if item[1] == "Shield" else 0,
                    st.session_state.players[item[0]].spe,
                ),
                reverse=True,
            )

            for actor_idx, action_to_take, target_indices_to_use in actor_action_pairs:
                round_actions.append((actor_idx, action_to_take, target_indices_to_use))

            for p in st.session_state.players:
                p.reset_status()

            st.session_state.anim_actions = round_actions
            st.session_state.anim_index = 0
            st.session_state.battle_phase = "animating"
            st.rerun()

        current_actor_idx = st.session_state.manual_input_index
        current_actor = st.session_state.players[current_actor_idx]

        st.subheader(f"🎮 Turn Input: {current_actor.name}")
        
        chosen_move = st.selectbox("Select Move", current_actor.loadout, key=f"move_{current_actor_idx}")

        target_indices = []
        is_team_1 = current_actor_idx < 2
        ally_indices = [0, 1] if is_team_1 else [2, 3]
        enemy_indices = [2, 3] if is_team_1 else [0, 1]

        if chosen_move == "Attack":
            valid_enemies = [i for i in enemy_indices if st.session_state.players[i].hp > 0]
            if not valid_enemies:
                valid_enemies = [i for i in enemy_indices]
            t_idx = st.selectbox(
                "Select Target Enemy",
                valid_enemies,
                format_func=lambda i: st.session_state.players[i].name,
                key=f"target_atk_{current_actor_idx}"
            )
            target_indices = [t_idx]
        elif chosen_move in ["Heal", "Boost"]:
            valid_allies = [i for i in ally_indices if st.session_state.players[i].hp > 0]
            t_idx = st.selectbox(
                "Select Target Ally",
                valid_allies,
                format_func=lambda i: st.session_state.players[i].name,
                key=f"target_support_{current_actor_idx}"
            )
            target_indices = [t_idx]

        with st.form(key=f"input_form_{current_actor_idx}"):
            submitted = st.form_submit_button("Lock In Move", type="primary")
            if submitted:
                st.session_state.temp_round_actions[current_actor_idx] = (chosen_move, target_indices)
                st.rerun()

    with st.expander("📜 Battle Log", expanded=True):
        for log_entry in reversed(st.session_state.log[-15:]):
            st.text(log_entry)

# --- UI: GAME OVER SCREEN ---
if st.session_state.game_state == "game_over":
    st.title("🏆 Tag Team Battle Concluded!")

    t1_alive = any(p.hp > 0 for p in st.session_state.players[:2])
    t2_alive = any(p.hp > 0 for p in st.session_state.players[2:])

    if t1_alive and not t2_alive:
        st.success("🎉 **Team 1** emerges victorious!")
    elif t2_alive and not t1_alive:
        st.success("🎉 **Team 2** emerges victorious!")
    else:
        st.warning("It's a draw!")

    if st.button("Play Again", type="primary"):
        st.session_state.game_state = "setup"
        st.session_state.battle_phase = "input"
        st.session_state.players = []
        st.session_state.log = []
        st.rerun()
