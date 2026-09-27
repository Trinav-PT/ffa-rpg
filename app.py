import random
import time
import streamlit as st

# Page Config
st.set_page_config(
    page_title="FFA Streamlit RPG", page_icon="⚔️", layout="wide"
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
        self.special_primed = (
            False  # Queued up to activate on the upcoming turn
        )
        self.boost_active = False  # Increases crit chance by 15% for the next turn

        # Loadout moves chosen before battle
        self.loadout = []

    def reset_status(self):
        self.shield_active = False


CHAR_TEMPLATES = {
    "A": {
        "hp": 145,
        "dmg": 7.0,
        "def": 6.0,
        "spe": 10,
        "potency": 4,
        "desc": "Deals 1.5x more damage next turn",
    },
    "B": {
        "hp": 95,
        "dmg": 8.0,
        "def": 5.0,
        "spe": 18,
        "potency": 2,
        "desc": "50% chance to avoid all attacks next turn",
    },
    "C": {
        "hp": 200,
        "dmg": 7.5,
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
        "desc": "Heals 30 HP next turn",
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
    st.session_state.manual_input_index = 0  # Tracks which manual player is picking a move
    st.session_state.temp_round_actions = {}  # Stores chosen moves per player index


# --- UI: SETUP SCREEN ---
if st.session_state.game_state == "setup":
    st.title("⚔️ 4-Player FFA Streamlit RPG")
    st.markdown(
        "Welcome! Choose your battle mode, character templates, and loadouts."
    )

    game_mode = st.radio(
        "Select Game Mode",
        [
            "Singleplayer vs AI (eeny, meeny, teeny)",
            "4-Player Manual (Gemini vs ChatGPT vs Perplexity vs DeepSeek)",
        ],
    )

    if "Singleplayer" in game_mode:
        col1, col2 = st.columns([1, 1])
        with col1:
            st.subheader("Select Your Character")
            player_char_key = st.selectbox(
                "Character",
                ["A", "B", "C", "D"],
                format_func=lambda x: f"Character {x} (HP: {CHAR_TEMPLATES[x]['hp']}, SPE: {CHAR_TEMPLATES[x]['spe']})",
            )
            p_template = CHAR_TEMPLATES[player_char_key]
            st.info(
                f"""
            * **HP:** {p_template['hp']}
            * **DMG:** {p_template['dmg']} | **DEF:** {p_template['def']} | **SPE:** {p_template['spe']}
            * **Special ({p_template['potency']} turns CD):** {p_template['desc']}
            """
            )

        with col2:
            st.subheader("Choose 3 Battle Moves")
            selected_moves = []
            for move in ALL_MOVES:
                if st.checkbox(move, value=(move in ["Attack", "Shield", "Heal"]), key=f"setup_{move}"):
                    selected_moves.append(move)

        if st.button("Start Battle", type="primary", use_container_width=True):
            if len(selected_moves) != 3:
                st.error("Please select exactly **3** moves to bring into battle!")
            else:
                p_data = CHAR_TEMPLATES[player_char_key]
                player = Character(
                    name=f"Player (Char {player_char_key})",
                    hp=p_data["hp"],
                    dmg=p_data["dmg"],
                    defense=p_data["def"],
                    spe=p_data["spe"],
                    potency=p_data["potency"],
                    is_player=True,
                )
                player.loadout = selected_moves

                ai_names = ["eeny", "meeny", "teeny"]
                ai_choices = ["A", "B", "C", "D"]
                ai_list = []
                for name in ai_names:
                    char_key = random.choice(ai_choices)
                    c_data = CHAR_TEMPLATES[char_key]
                    ai = Character(
                        name=f"{name.capitalize()} (Char {char_key})",
                        hp=c_data["hp"],
                        dmg=c_data["dmg"],
                        defense=c_data["def"],
                        spe=c_data["spe"],
                        potency=c_data["potency"],
                        is_player=False,
                    )
                    ai.loadout = random.sample(ALL_MOVES, 3)
                    ai_list.append(ai)

                st.session_state.players = [player] + ai_list
                st.session_state.game_state = "battle"
                st.session_state.battle_phase = "input"
                st.session_state.round_num = 1
                st.session_state.log = ["Battle started! May the best fighter win."]
                st.session_state.manual_input_index = 0
                st.session_state.temp_round_actions = {}
                st.rerun()
    else:
        st.subheader("Configure 4 Manual Combatants & Their Loadouts")
        combatant_names = ["Gemini", "ChatGPT", "Perplexity", "DeepSeek"]
        manual_configs = []

        cols_cfg = st.columns(4)
        for i, name in enumerate(combatant_names):
            with cols_cfg[i]:
                st.markdown(f"### {name}")
                char_choice = st.selectbox(
                    f"Class", ["A", "B", "C", "D"], key=f"manual_class_{i}"
                )
                st.caption(f"HP: {CHAR_TEMPLATES[char_choice]['hp']} | SPE: {CHAR_TEMPLATES[char_choice]['spe']}")
                
                st.markdown("**Choose 3 Moves:**")
                player_moves = []
                for move in ALL_MOVES:
                    default_checked = (move in ["Attack", "Shield", "Heal"]) if i != 1 else (move in ["Attack", "Shield", "Spread attack (3)"])
                    if st.checkbox(move, value=default_checked, key=f"manual_move_{i}_{move}"):
                        player_moves.append(move)
                
                manual_configs.append((name, char_choice, player_moves))

        if st.button("Start 4-Way Manual Battle", type="primary", use_container_width=True):
            invalid_loadout = False
            for name, char_key, p_moves in manual_configs:
                if len(p_moves) != 3:
                    st.error(f"{name} must have exactly **3** moves selected (currently has {len(p_moves)}).")
                    invalid_loadout = True

            if not invalid_loadout:
                players_list = []
                for name, char_key, p_moves in manual_configs:
                    c_data = CHAR_TEMPLATES[char_key]
                    c_obj = Character(
                        name=f"{name} (Char {char_key})",
                        hp=c_data["hp"],
                        dmg=c_data["dmg"],
                        defense=c_data["def"],
                        spe=c_data["spe"],
                        potency=c_data["potency"],
                        is_player=True,
                    )
                    c_obj.loadout = p_moves
                    players_list.append(c_obj)

                st.session_state.players = players_list
                st.session_state.game_state = "battle"
                st.session_state.battle_phase = "input"
                st.session_state.round_num = 1
                st.session_state.log = ["4-Way AI Deathmatch started! Choose your moves wisely."]
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

    if attacker.special_active and "Char A" in attacker.name:
        raw_dmg *= 1.5

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
            log_messages.append(f"✨ {attacker.name}'s Special is active: 1.5x damage boost!")
        elif "Char C" in attacker.name:
            log_messages.append(f"✨ {attacker.name}'s Special is active: Enhanced defense RNG!")
        elif "Char D" in attacker.name:
            heal_amt = 30.0
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
        heal_amt = round(attacker.max_hp * 0.2, 1)
        attacker.hp = min(attacker.max_hp, attacker.hp + heal_amt)
        log_messages.append(f"💚 {attacker.name} healed for **{heal_amt} HP**.")

    elif action == "Boost":
        attacker.boost_active = True
        log_messages.append(f"🔮 {attacker.name} uses Boost, increasing critical strike chance by 15% for next turn.")

    elif action == "Spread attack (3)":
        for p in all_players:
            if p != attacker and p.hp > 0:
                if p.special_active and "Char B" in p.name and random.random() < 0.5:
                    log_messages.append(f"💨 {p.name} avoided {attacker.name}'s spread attack!")
                    continue
                dmg, crit = calculate_damage(attacker, p, base_multiplier=1 / 3)
                p.hp = max(0.0, p.hp - dmg)
                log_messages.append(f"💥 {attacker.name} hit {p.name} with Spread (3) for **{dmg} damage**.")

    elif action == "Spread attack (2)":
        for t_idx in target_indices:
            t = all_players[t_idx]
            if t.hp > 0:
                if t.special_active and "Char B" in t.name and random.random() < 0.5:
                    log_messages.append(f"💨 {t.name} avoided {attacker.name}'s spread attack!")
                    continue
                dmg, crit = calculate_damage(attacker, t, base_multiplier=1 / 2)
                t.hp = max(0.0, t.hp - dmg)
                log_messages.append(f"💥 {attacker.name} hit {t.name} with Spread (2) for **{dmg} damage**.")

    return log_messages


# --- UI: BATTLE SCREEN ---
if st.session_state.game_state == "battle":
    st.title(f"⚔️ FFA Battle Arena — Round {st.session_state.round_num}")

    cols = st.columns(len(st.session_state.players))
    for idx, p in enumerate(st.session_state.players):
        with cols[idx]:
            st.markdown(f"### {p.name}")
            st.markdown(f"**HP:** `{p.hp}/{p.max_hp}`")
            st.progress(float(max(0.0, p.hp) / p.max_hp))
            status_txt = (
                "✨ SPECIAL ACTIVE"
                if p.special_active
                else ("⚡ PRIMING SPECIAL" if p.special_primed else "Ready")
            )
            st.caption(f"SPE: {p.spe} | CD: {p.potency_cooldown}\n{status_txt}")

    st.divider()

    # --- ANIMATION PHASE ---
    if st.session_state.battle_phase == "animating":
        st.info("🎬 Resolving round actions sequentially in priority/speed order...")

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
            hp_summary = "   📋 End of Round HP: " + ", ".join(
                [f"{p.name.split(' (')[0]}: {p.hp}/{p.max_hp}" for p in st.session_state.players]
            )
            st.session_state.log.append(hp_summary)

            alive_combatants = [p for p in st.session_state.players if p.hp > 0]
            if len(alive_combatants) <= 1:
                st.session_state.game_state = "game_over"
            else:
                st.session_state.round_num += 1
                st.session_state.battle_phase = "input"
                st.session_state.manual_input_index = 0
                st.session_state.temp_round_actions = {}
            st.rerun()

    # --- INPUT PHASE ---
    elif st.session_state.battle_phase == "input":
        alive_players = [p for p in st.session_state.players if p.hp > 0]
        if len(alive_players) <= 1:
            st.session_state.game_state = "game_over"
            st.rerun()

        # Advance manual input index until it points to a living player who hasn't submitted yet
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
        
        # Move choice outside form so target pickers update live
        chosen_move = st.selectbox("Select Move", current_actor.loadout, key=f"move_{current_actor_idx}")

        target_options_indices = [
            i for i, p in enumerate(st.session_state.players) if i != current_actor_idx and p.hp > 0
        ]
        target_indices = []

        if chosen_move == "Attack":
            if target_options_indices:
                t_idx = st.selectbox(
                    "Select Target",
                    target_options_indices,
                    format_func=lambda i: st.session_state.players[i].name,
                    key=f"target_atk_{current_actor_idx}"
                )
                target_indices = [t_idx]
        elif chosen_move == "Spread attack (2)":
            if len(target_options_indices) >= 2:
                selected_ts = st.multiselect(
                    "Select exactly 2 targets",
                    target_options_indices,
                    format_func=lambda i: st.session_state.players[i].name,
                    max_selections=2,
                    key=f"target_sp2_{current_actor_idx}"
                )
                target_indices = selected_ts
            elif len(target_options_indices) == 1:
                st.info("Only 1 opponent left! They will be targeted automatically.")
                target_indices = target_options_indices

        with st.form(key=f"input_form_{current_actor_idx}"):
            submitted = st.form_submit_button("Lock In Move", type="primary")
            if submitted:
                if chosen_move == "Spread attack (2)" and len(target_indices) != min(2, len(target_options_indices)):
                    st.error("Please select exactly **2 targets** for your Spread Attack (2)!")
                else:
                    st.session_state.temp_round_actions[current_actor_idx] = (chosen_move, target_indices)
                    st.rerun()

    with st.expander("📜 Battle Log", expanded=True):
        for log_entry in reversed(st.session_state.log[-15:]):
            st.text(log_entry)

# --- UI: GAME OVER SCREEN ---
if st.session_state.game_state == "game_over":
    st.title("🏆 Battle Concluded!")

    alive_combatants = [p for p in st.session_state.players if p.hp > 0]

    if len(alive_combatants) == 1:
        st.success(f"🎉 **{alive_combatants[0].name}** emerged victorious in the Free-For-All!")
    elif alive_combatants:
        st.info("Multiple fighters survived!")
    else:
        st.warning("It's a draw! Everyone was defeated simultaneously.")

    if st.button("Play Again", type="primary"):
        st.session_state.game_state = "setup"
        st.session_state.battle_phase = "input"
        st.session_state.players = []
        st.session_state.log = []
        st.rerun()
