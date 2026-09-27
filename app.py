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

        # Loadout moves chosen before battle
        self.loadout = []

    def reset_status(self):
        self.shield_active = False
        # Special active status persists for the designated turn, then clears


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
}

ALL_MOVES = [
    "Attack",
    "Shield",
    "Heal",
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


# --- UI: SETUP SCREEN ---
if st.session_state.game_state == "setup":
    st.title("⚔️ 4-Player FFA Streamlit RPG")
    st.markdown(
        "Welcome! Choose your character, pick 3 battle moves, and battle eeny, meeny, and teeny in a simultaneous turn-based free-for-all."
    )

    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("Select Your Character")
        player_char_key = st.selectbox(
            "Character",
            ["A", "B", "C"],
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
            if st.checkbox(move, value=(move in ["Attack", "Shield", "Heal"])):
                selected_moves.append(move)

    if st.button("Start Battle", type="primary", use_container_width=True):
        if len(selected_moves) != 3:
            st.error("Please select exactly **3** moves to bring into battle!")
        else:
            # Setup Player
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

            # Setup AI Opponents: eeny, meeny, teeny
            ai_names = ["eeny", "meeny", "teeny"]
            ai_choices = ["A", "B", "C"]
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
            st.session_state.log = [
                "Battle started! May the best fighter win."
            ]
            st.rerun()

# --- HELPER FUNCTIONS FOR COMBAT ---
def calculate_damage(attacker, defender, base_multiplier=1.0):
    # Defense check for Character C special
    if defender.special_active and "Char C" in defender.name:
        def_mod = random.randint(5, 10) * defender.defense
    else:
        def_mod = random.randint(0, 5) * defender.defense

    raw_dmg = (random.randint(0, 10) * attacker.dmg) * base_multiplier

    # Special multiplier for Character A
    if attacker.special_active and "Char A" in attacker.name:
        raw_dmg *= 1.5

    # Crit check: rng(0-3) * SPE %
    crit_roll = random.randint(0, 3) * attacker.spe
    is_crit = (
        random.choice([True, False])
        if crit_roll > 20
        else (random.random() * 100 < crit_roll)
    )

    if is_crit:
        raw_dmg *= 2

    # Mitigation via defense & shield
    final_dmg = max(1.0, raw_dmg - def_mod)

    if defender.shield_active:
        final_dmg *= 0.5

    return round(final_dmg, 1), is_crit


def execute_action(attacker, action, targets, all_players):
    log_messages = []

    # Handle Special Activation / Priming mechanics
    attacker.special_active = False
    if attacker.special_primed:
        attacker.special_active = True
        attacker.special_primed = False
        if "Char B" in attacker.name:
            log_messages.append(
                f"✨ {attacker.name}'s Special is active: 50% dodge chance!"
            )
        elif "Char A" in attacker.name:
            log_messages.append(
                f"✨ {attacker.name}'s Special is active: 1.5x damage boost!"
            )
        elif "Char C" in attacker.name:
            log_messages.append(
                f"✨ {attacker.name}'s Special is active: Enhanced defense RNG!"
            )

    # Tick down cooldowns at turn start
    if attacker.potency_cooldown > 0:
        attacker.potency_cooldown -= 1

    # Check if special should prime for the next turn
    if attacker.potency_cooldown == 0 and not attacker.special_active:
        attacker.special_primed = True
        attacker.potency_cooldown = attacker.max_potency
        log_messages.append(
            f"⚡ {attacker.name} charges up their Special ability for next turn!"
        )

    # Execute Selected Move
    if action == "Attack":
        if targets:
            target = targets[0]
            if target.hp > 0:
                if (
                    target.special_active
                    and "Char B" in target.name
                    and random.random() < 0.5
                ):
                    log_messages.append(
                        f"💨 {target.name} avoided {attacker.name}'s attack completely using Special!"
                    )
                else:
                    dmg, crit = calculate_damage(attacker, target)
                    target.hp = max(0.0, target.hp - dmg)
                    crit_txt = " (CRITICAL HIT!)" if crit else ""
                    log_messages.append(
                        f"⚔️ {attacker.name} attacked {target.name} for **{dmg} damage**{crit_txt}."
                    )

    elif action == "Shield":
        attacker.shield_active = True
        log_messages.append(
            f"🛡️ {attacker.name} raised a Shield (incoming damage halved this turn)."
        )

    elif action == "Heal":
        heal_amt = round(attacker.max_hp * 0.2, 1)
        attacker.hp = min(attacker.max_hp, attacker.hp + heal_amt)
        log_messages.append(f"💚 {attacker.name} healed for **{heal_amt} HP**.")

    elif action == "Spread attack (3)":
        for p in all_players:
            if p != attacker and p.hp > 0:
                if (
                    p.special_active
                    and "Char B" in p.name
                    and random.random() < 0.5
                ):
                    log_messages.append(
                        f"💨 {p.name} avoided {attacker.name}'s spread attack!"
                    )
                    continue
                dmg, crit = calculate_damage(attacker, p, base_multiplier=1 / 3)
                p.hp = max(0.0, p.hp - dmg)
                log_messages.append(
                    f"💥 {attacker.name} hit {p.name} with Spread (3) for **{dmg} damage**."
                )

    elif action == "Spread attack (2)":
        for t in targets:
            if t.hp > 0:
                if (
                    t.special_active
                    and "Char B" in t.name
                    and random.random() < 0.5
                ):
                    log_messages.append(
                        f"💨 {t.name} avoided {attacker.name}'s spread attack!"
                    )
                    continue
                dmg, crit = calculate_damage(attacker, t, base_multiplier=1 / 2)
                t.hp = max(0.0, t.hp - dmg)
                log_messages.append(
                    f"💥 {attacker.name} hit {t.name} with Spread (2) for **{dmg} damage**."
                )

    return log_messages


# --- UI: BATTLE SCREEN ---
if st.session_state.game_state == "battle":
    st.title(f"⚔️ FFA Battle Arena — Round {st.session_state.round_num}")

    # Display Player Status Cards
    cols = st.columns(4)
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
            st.caption(
                f"SPE: {p.spe} | Potency CD: {p.potency_cooldown}\nStatus: {status_txt}"
            )

    st.divider()

    player_obj = st.session_state.players[0]

    # --- ANIMATION PHASE (Step-by-step resolution) ---
    if st.session_state.battle_phase == "animating":
        st.info(
            "🎬 Resolving round actions sequentially in priority/speed order..."
        )

        if st.session_state.anim_index < len(st.session_state.anim_actions):
            actor, action_desc, targets_to_use = st.session_state.anim_actions[
                st.session_state.anim_index
            ]

            if actor is None:
                # Round header log entry
                st.session_state.log.append(action_desc)
            else:
                if actor.hp > 0:
                    action_logs = execute_action(
                        actor,
                        action_desc,
                        targets_to_use,
                        st.session_state.players,
                    )
                    st.session_state.log.extend(action_logs)

            st.session_state.anim_index += 1
            time.sleep(1.0)
            st.rerun()
        else:
            # Animation finished for this round — Append end-of-round HP status summary
            hp_summary = "   📋 End of Round HP: " + ", ".join(
                [f"{p.name.split(' (')[0]}: {p.hp}/{p.max_hp}" for p in st.session_state.players]
            )
            st.session_state.log.append(hp_summary)

            alive_combatants = [
                p for p in st.session_state.players if p.hp > 0
            ]
            if len(alive_combatants) <= 1:
                st.session_state.game_state = "game_over"
            else:
                st.session_state.round_num += 1
                st.session_state.battle_phase = "input"
            st.rerun()

    # --- INPUT PHASE ---
    elif st.session_state.battle_phase == "input":
        alive_players = [p for p in st.session_state.players if p.hp > 0]
        if len(alive_players) <= 1:
            st.session_state.game_state = "game_over"
            st.rerun()

        if player_obj.hp > 0:
            st.subheader("Your Action This Turn")
            chosen_move = st.selectbox("Select Move", player_obj.loadout)

            target_options = [
                p
                for p in st.session_state.players
                if p != player_obj and p.hp > 0
            ]
            player_targets = []

            if chosen_move == "Attack":
                if target_options:
                    t = st.selectbox(
                        "Select Target",
                        target_options,
                        format_func=lambda x: x.name,
                    )
                    player_targets = [t]
            elif chosen_move == "Spread attack (2)":
                if len(target_options) >= 2:
                    selected_ts = st.multiselect(
                        "Select exactly 2 targets",
                        target_options,
                        format_func=lambda x: x.name,
                        max_selections=2,
                    )
                    player_targets = selected_ts
                elif len(target_options) == 1:
                    st.info(
                        "Only 1 opponent left! They will be targeted."
                    )
                    player_targets = target_options
                else:
                    player_targets = []

            button_label = "Submit Move & Execute Round"
        else:
            st.warning(
                "💀 You have been defeated! You are now spectating the remainder of the battle."
            )
            chosen_move = None
            player_targets = []
            button_label = "Simulate Next AI Round"

        if st.button(button_label, type="primary", use_container_width=True):
            if (
                player_obj.hp > 0
                and chosen_move == "Spread attack (2)"
                and len(player_targets) != min(2, len(target_options))
            ):
                st.error(
                    "Please select exactly **2 targets** for your Spread Attack (2)!"
                )
            else:
                living_combatants = [
                    p for p in st.session_state.players if p.hp > 0
                ]
                round_actions = []

                # Clear shields before round
                for p in st.session_state.players:
                    p.reset_status()

                # Determine actions for everyone first to check priority
                actor_action_pairs = []
                for actor in living_combatants:
                    if actor.is_player:
                        action_to_take = chosen_move
                        targets_to_use = player_targets
                    else:
                        action_to_take = random.choice(actor.loadout)
                        valid_ai_targets = [
                            p
                            for p in st.session_state.players
                            if p != actor and p.hp > 0
                        ]
                        if action_to_take == "Attack":
                            targets_to_use = (
                                [random.choice(valid_ai_targets)]
                                if valid_ai_targets
                                else []
                            )
                        elif action_to_take == "Spread attack (2)":
                            targets_to_use = random.sample(
                                valid_ai_targets,
                                min(2, len(valid_ai_targets)),
                            )
                        else:
                            targets_to_use = []

                    actor_action_pairs.append(
                        (actor, action_to_take, targets_to_use)
                    )

                # Sort: Shield moves ALWAYS go first (priority 1 vs 0), tie-broken by speed
                random.shuffle(actor_action_pairs)
                actor_action_pairs.sort(
                    key=lambda item: (
                        1 if item[1] == "Shield" else 0,
                        item[0].spe,
                    ),
                    reverse=True,
                )

                round_actions.append(
                    (
                        None,
                        f"--- Round {st.session_state.round_num} ---",
                        [],
                    )
                )

                for actor, action_to_take, targets_to_use in actor_action_pairs:
                    round_actions.append((actor, action_to_take, targets_to_use))

                st.session_state.anim_actions = round_actions
                st.session_state.anim_index = 0
                st.session_state.battle_phase = "animating"
                st.rerun()

    # Battle Log Sidebar / Expandable
    with st.expander("📜 Battle Log", expanded=True):
        for log_entry in reversed(st.session_state.log[-15:]):
            st.text(log_entry)

# --- UI: GAME OVER SCREEN ---
if st.session_state.game_state == "game_over":
    st.title("🏆 Battle Concluded!")

    player_obj = st.session_state.players[0]
    alive_combatants = [p for p in st.session_state.players if p.hp > 0]

    if player_obj.hp > 0:
        st.success(
            "Congratulations! You emerged victorious in the Free-For-All!"
        )
    elif alive_combatants:
        winner = alive_combatants[0]
        st.error(
            f"You were defeated! **{winner.name}** won the Free-For-All deathmatch."
        )
    else:
        st.warning("It's a draw! Everyone was defeated simultaneously.")

    if st.button("Play Again", type="primary"):
        st.session_state.game_state = "setup"
        st.session_state.battle_phase = "input"
        st.session_state.players = []
        st.session_state.log = []
        st.rerun()
