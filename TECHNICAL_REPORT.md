# Yedi - Technical Game Report
### Mindfree Games | Unity 6 (6000.4.1f1) | Android

---

## 1. GAME OVERVIEW

**Yedi** (Turkish for "seven") is a **brain training card game** built around 7 cognitive dimensions. The player draws cards, places them in slots, and merges them to generate mana. Each card can carry one or more cognitive dimensions (number, color, shape, word, beat, memory, motor), and the merge outcome depends on the specific rules of each dimension. The goal is to maintain your mana above zero as long as possible while the timer and mana decay work against you.

The name "yedi" reflects the core structure: 7 cognitive categories, visualized as a heptagon in the main menu.

**Platform:** Android (with iOS scaffolding)
**Monetization:** AdMob interstitial + rewarded ads, plus a one-time in-app purchase to unlock all content
**Persistence:** BayatGames SaveGameFree for all game state, PlayerPrefs for user settings

---

## 2. PROJECT STRUCTURE

### 2.1 Scenes (8 game scenes)

| Scene | Purpose |
|-------|---------|
| `Splash Screen` | Initial loading / branding |
| `Mindfree Games Screen` | Company splash screen |
| `_Start Screen` | Main menu / entry point |
| `Scene Selection Screen` | Heptagon-based game mode picker |
| `Level 1 Space for Unity` | Primary gameplay scene (space theme) |
| `_Level 1 Dark Star` | Alternate gameplay scene (dark theme) |
| `Stats Screen Expanded` | Performance stats + charts |
| `Options Screen` | Player settings (name, volume, difficulty) |

### 2.2 Asset Folders

| Folder | Content |
|--------|---------|
| `Prefabs/Cards/` | Card, CardFrame, CardDrawer, BeatGenerator, MemoryGenerator, MotorGenerator, draw/super buttons |
| `Prefabs/Core Game/` | Level Controller, Level Loader, Music Player, Tutorial, Stats, Options, Buttons, Cameras, Canvases, Unlock/Purchase dialogs |
| `Sprites/Cards/` | Card frames, slot sprites (empty/filled), shape sprites (vectors, intervals, hanoi, sphere), musical note |
| `Sprites/Dimensions/` | Heptagon artwork, category icons (math, visual, spatial, verbal, music, memory, physical), mode icons |
| `Sprites/Gain/` | Merge feedback sprites: thumbs_up_1/2/3 (gain levels), thumbs_down, flat, loss |
| `Sounds/` | 17 audio files: background music, card draw SFX, merge SFX, level complete jingles, beat sounds |
| `Resources/` | `wordlist.txt` (3,000 common English words for scrabble mode validation) |
| `Fonts/` | Custom typefaces |

### 2.3 Third-Party Dependencies

| Package | Purpose |
|---------|---------|
| **EasyMobile** | Advertising (AdMob), In-App Purchasing, Native UI |
| **BayatGames SaveGameFree** | Persistent data storage (JSON-based) |
| **LightShaft YouTube Player** | In-app tutorial video playback |
| **EzChart** | Statistical charts (line, pie, bar) |
| **Lean Touch** | Touch/gesture input handling |
| **Lean Localization** | Multi-language support (scaffolded) |
| **AllIn1SpriteShader** | Visual effects on card sprites |
| **Modern UI Pack** | Polished UI components (sliders, buttons) |
| **TextMesh Pro** | Advanced text rendering |
| **Febucci Text Animator** | Animated text effects |
| **Firebase** | Analytics (SDK 8.7.0) |
| **Google Mobile Ads** | AdMob integration layer |
| **ExternalDependencyManager (EDM4U)** | Android/iOS native dependency resolution |
| **Unity Purchasing** | IAP framework (4.14.2) |

---

## 3. ARCHITECTURE

### 3.1 Singleton Managers (15 classes)

These classes use the pattern `public static ClassName Instance { get; private set; }` + `Awake()`:

| Singleton | Role |
|-----------|------|
| `LevelController` | Game flow, level configuration, pause/resume, mode activation |
| `CardDrawer` | Card instantiation, cost management, super card mode |
| `ManaDisplay` | Mana resource tracking, time-based decay, difficulty multipliers |
| `GameTimer` | Countdown timer (10s or 20s), pause support |
| `BeatGenerator` | Audio beat system for music games |
| `HeptagonController` | 7-sided UI for game mode selection |
| `SevenMinuteController` | 5-game "Seven Minute Workout" sequencer |
| `TutorialController` | 14-step tutorial progression |
| `LevelLoader` | Scene transitions, purchase gating, tutorial enforcement |
| `StatsCollectorExpanded` | Per-game stats collection, logistic ranking |
| `StatsControllerExpanded` | Historical stats aggregation, chart rendering |
| `AdsControllerYedi` | AdMob interstitial + rewarded ad lifecycle |
| `SuperDisplay` | Super card resource counter (starts at 3) |
| `ContinueButton` | Continue game button (placeholder) |
| `MusicPlayer` | Background music (DontDestroyOnLoad, persists across scenes) |

### 3.2 Card System Hierarchy

```
Card (MonoBehaviour)
  |-- instantiates --> CardFrame (MonoBehaviour)
                         |-- contains --> NumberCard : CardTypeBase
                         |-- contains --> ColorCard  : CardTypeBase
                         |-- contains --> ShapeCard  : CardTypeBase
                         |-- contains --> WordCard   : CardTypeBase
                         |-- contains --> BeatCard   : CardTypeBase
                         |-- contains --> MemoryCard : CardTypeBase
                         |-- contains --> MotorCard  : CardTypeBase
                         |-- contains --> FindClosestSlot
```

- **Card** is the top-level container. It holds `cardMana` (mana cost/value), `cardType`, and a reference to `CardFrame`.
- **CardFrame** is the visual/logic controller. It handles drag-drop, merge operations, gain animations, and activates/deactivates the 7 dimension components.
- **CardTypeBase** is the abstract base class providing shared initialization (mana multipliers, CardFrame reference, activation state).
- Each dimension component (NumberCard, ColorCard, etc.) implements its own merge logic.

### 3.3 Slot System

```
SlotGeneric (MonoBehaviour)
  |-- has component --> Slot1..Slot7 (marker classes for identification)
  |-- OR has component --> SlotNew (extends SlotEffect) - card draw origin
  |-- OR has component --> SlotSell (extends SlotEffect) - card sell target
```

- **5 gameplay slots** (Slot1-Slot5): Cards are placed and merged here
- **SlotNew**: Where new cards spawn when drawn (Space key)
- **SlotSell**: Drag target to sell/destroy a card for mana refund
- **Slot6, Slot7**: Exist as markers but not used in current gameplay
- **SlotEffect**: Base class providing particle VFX + audio on draw/sell

### 3.4 Card Type Encoding System

Cards use a float `cardType` to encode which dimensions are active and which mode each uses. There are two encoding schemes:

**Simple types (1-22):**
| Type | Dimensions |
|------|------------|
| 1 | 1 random dimension |
| 2 | 2 random dimensions |
| 3 | 3 random dimensions |
| 4 | 4 random dimensions (Number + Color + Shape + Word) |
| 5 | Number only (add mode) |
| 6 | Color only (add mode) |
| 7 | Shape only (triangle mode) |
| 8 | Word only (verbs mode) |
| 9-12 | Single dimensions with alternate modes |
| 13-16 | Combined alternate modes |
| 17-22 | Special: beat-only, motor-only, memory combos |

**Encoded types (>1000) - 7-digit format: `NCSW BMM`**

Each digit represents a dimension (Number, Color, Shape, Word, Beat, Memory, Motor):
- `1` = dimension inactive
- `2` = mode 1 (default)
- `3` = mode 2
- `4` = mode 3
- `5`+ = mode 4+

Example: `2222000` = Number(add) + Color(add) + Shape(triangle) + Word(verbs) + no beat/memory/motor

The digit-to-mode mapping per dimension:

| Digit | Number | Color | Shape | Word | Beat | Memory | Motor |
|-------|--------|-------|-------|------|------|--------|-------|
| 1 | off | off | off | off | off | off | off |
| 2 | add | add | triangle | verbs | double | show all | speed accuracy |
| 3 | multiply | subtract | rectangle | adjectives | single | show one | speed accuracy halfway |
| 4 | gcd | gray | triple | nouns | double fast | every action | visit all slots |
| 5 | vector | text | kanizsa | synVerbs | single fast | | |
| 6 | interval | | sphere | synAdjectives | tiktok | | |
| 7 | trigon | | hanoi | grammar | five | | |
| 8 | sort | | | questions | | | |
| 9 | | | | scrabble | | | |

---

## 4. GAME FLOW

### 4.1 Startup Sequence

```
Splash Screen --> Mindfree Games Screen --> _Start Screen --> Scene Selection Screen
```

### 4.2 Scene Selection (Heptagon)

The `Scene Selection Screen` displays a heptagon (7-sided polygon) where each face represents one cognitive category:

1. **Math** (Number dimension)
2. **Visual** (Color dimension)
3. **Spatial** (Shape dimension)
4. **Verbal** (Word dimension)
5. **Music** (Beat dimension)
6. **Memory** (Memory dimension)
7. **Physical** (Motor dimension)

The player clicks a category face to cycle through available modes for that dimension. The selection is highlighted with colored masks. Constraints:
- Music and Physical are **mutually exclusive**
- Memory **requires** at least one other dimension to be active
- At least one dimension must be selected

### 4.3 Predefined Levels

| Level | Name | Dimensions | Modes |
|-------|------|------------|-------|
| 0 | Tutorial | N+C+S+W | add, add, triangle, verbs |
| 1 | Number Only | N | add |
| 2 | Color Only | C | add |
| 3 | Shape Only | S | triangle |
| 4 | Word Only | W | verbs |
| 5 | All Basic | N+C+S+W | add, add, triangle, verbs |
| 6 | Beat Only | B | double |
| 7 | Number + Memory | N+M | add, show all |
| 8 | Motor Only | P | speed accuracy |
| 9/100 | Custom / Workout | Player-selected | User-configured |

### 4.4 In-Game Loop

1. **Draw Phase**: Player presses Space (or taps draw button) to create a new card at SlotNew
   - Costs mana (configurable per card type, base = 10)
   - CardDrawer instantiates Card -> Card instantiates CardFrame
   - CardFrame activates dimension components based on cardType
   - Each active dimension generates a random initial value

2. **Place Phase**: Player drags card from SlotNew to an empty slot (Slot1-5)
   - FindClosestSlot tracks the nearest slot in real-time during drag
   - If motor dimension is active: drag speed/accuracy is evaluated
   - If beat dimension is active: timing of drop relative to beat is evaluated

3. **Merge Phase**: Player drags a card onto another card's occupied slot
   - Each active dimension calls `ComputeMergeXXXGain()` on the target card
   - Gain is displayed as thumbs up/down sprites (gain levels 1-3, flat, or loss)
   - Target card's mana is multiplied by the appropriate multiplier
   - Merging card is destroyed
   - Maximum merges per card: 3-5 (based on difficulty)

4. **Sell Phase**: Player drags card to SlotSell
   - Card is destroyed
   - Mana is refunded (card's current mana value added back)

5. **Mana Decay**: Every frame, mana decays at a rate of `elapsedTime / timeManaDiv` (timeManaDiv = 5)
   - Game ends when mana reaches 0

6. **Timer**: Countdown from 10s (or 20s for hanoi/scrabble modes)
   - When timer expires: pause game, offer rewarded ad for +10s
   - Up to 2 rewarded ads per game

### 4.5 Post-Game

- Stats are collected by `StatsCollectorExpanded` and persisted by `StatsControllerExpanded`
- Logistic function converts raw performance to percentile rankings
- Three chart types available: Line (trend), Distribution (pie), Ranking (bar)
- 45 tracked metrics across all game modes

---

## 5. THE 7 COGNITIVE DIMENSIONS (Detailed)

### 5.1 NUMBER (Math)

**7 modes**, each with distinct merge rules:

#### Add Mode
- Card shows: random integer from -3 to +3 (excluding 0)
- Super card: shows 0
- **Merge goal**: Get the sum to equal 0
- Gain table:
  - Both 0: gain 3 (best)
  - 0 + non-zero: gain -1 (penalty)
  - Sum = 0: gain 2
  - Sum close to 0: gain 1
  - Sum far from 0: gain -1

#### Multiply Mode
- Card shows: fraction (x1 to x4 or /1 to /4)
- Super card: shows x1
- **Merge goal**: Get the product to equal 1
- Same gain structure as add but targeting product = 1

#### GCD Mode
- Card shows: number from {2, 3, 4, 5, 7, 8, 9, 10, 14, 15, 18, 21}
- **Merge goal**: Find numbers that share a common divisor
- Both 1: gain 3; GCD=1: gain 2; GCD>1: gain -1

#### Vector Mode
- Card shows: 2D vector from 9 options: (0,0), (0,1), (1,0), (1,1), (0,-1), (-1,0), (-1,-1), (1,-1), (-1,1)
- Displayed as vector sprite images (sp_p_p.png = positive/positive, etc.)
- **Merge goal**: Complex lookup table for vector pair combinations
- Merge updates the target vector based on a predefined combination table

#### Interval Mode
- Card shows: mathematical interval from 10 options including "nihil", (-inf,-1), (-inf,1), etc.
- **Merge goal**: Complex gain matrix for interval pair combinations
- Merge updates the target interval

#### Trigon Mode
- Card shows: trigonometric function from 11 options: 0, sin(x), cos(x), sin(-x), cos(-x), sin(pi-x), cos(pi-x), sin+cos, sin-cos, cos-sin, -sin-cos
- **Merge goal**: Complex trig function combination table

#### Sort Mode
- Card shows: single digits (1-5) or two-digit pairs (11, 12, ..., 55)
- **Merge goal**: Compare and sort digit values
- Gains based on correct sorting order logic

### 5.2 COLOR (Visual)

**4 modes:**

#### Add Mode (RGB)
- Essential colors: Red, Green, Blue
- Mix colors: Yellow, Cyan, Magenta
- Null color: White
- **Merge goal**: Match complementary or same-type colors
- Gain table based on color pair interaction (12 possible outcomes)

#### Subtract Mode (CMY)
- Essential colors: Cyan, Magenta, Yellow
- Mix colors: Blue, Red, Green
- Null color: Black
- Same merge structure as Add but with subtractive color model

#### Text Mode
- Same as Add mode but displays the color NAME instead of the color itself
- Tests color-word association (Stroop-like effect)

#### Gray Mode
- 9 grayscale levels (brightness 0.1 to 0.9)
- **Merge goal**: Combine gray levels so sum exceeds 9 (turns white)
- Gain: sum > 9 = gain 2; normal increment = gain 1; decrement = gain -1

### 5.3 SHAPE (Spatial)

**6 modes**, each using a different sprite set:

#### Triangle Mode
- 9 shapes (indices 0-8): various triangle orientations
- Index 7 = special ("nihil" equivalent)
- Index 8 = empty
- **Merge**: Lookup table maps every pair to a new shape and gain

#### Rectangle Mode
- 9 shapes: various rectangle/line patterns
- Same structure as Triangle with different lookup table

#### Triple Mode
- 9 shapes: combinations of three geometric primitives
- Same structure with different lookup table

#### Kanizsa Mode
- 9 shapes: Kanizsa illusion patterns (subjective contours)
- Same structure with different lookup table

#### Sphere Mode
- 11 shapes (indices 0-10): 3D sphere/cube projections
- Index 0 = special, Index 10 = empty
- Larger lookup table for more complex spatial relationships

#### Hanoi Mode
- 17 shapes (indices 0-16): Tower of Hanoi states
- Index 9 = special, Index 16 = empty
- **Double time enabled** (20s instead of 10s)
- Largest lookup table - follows Tower of Hanoi puzzle rules

### 5.4 WORD (Verbal)

**9 modes:**

#### Antonym Modes (verbs, adjectives, prepositions, nouns)
- 14 words per list, organized in pairs of antonyms:
  - Verbs: appear/vanish, contract/expand, fail/succeed, help/hinder, separate/join, build/destroy, conceal/reveal
  - Adjectives: empty/full, messy/neat, boring/fun, young/old, private/public, quiet/loud, sweet/sour
  - Prepositions: before/after, away from/towards, in/out, against/for, below/above, backward/forward, here/there
  - Nouns: despair/hope, past/present, poverty/wealth, success/failure, virtue/vice, war/peace, bless/curse
- **Merge goal**: Match antonym pairs
- Card can hold up to 2 words. Special "nihil" word acts as a wildcard.
- Matching pair: gain 2; Same word: gain -1; Nihil+Nihil: gain 3

#### Synonym Modes (synVerbs, synAdjectives)
- 14 words organized in synonym pairs:
  - synVerbs: choose/select, close/shut, refuse/reject, collect/gather, defend/protect, forbid/ban, begin/start
  - synAdjectives: happy/amused, little/tiny, good/terrific, bad/awful, pretty/handsome, angry/annoyed, mad/crazy
- Same merge logic as antonym modes

#### Grammar Mode
- 14 items in paired grammar structures:
  - I/am, you/are, she/is, to/be, either/or, neither/nor, not only/but also
- Same merge logic

#### Questions Mode
- 14 items in question/answer pairs:
  - what/this, where/here, when/now, why/because, who/she, whom/her, how often/rarely

#### Scrabble Mode
- 19 single characters: e, t, a, o, u, i, n, s, r, h, l, d, c, d, p, m, g, f, b
- **Merge**: Concatenates letters and validates against 3,000-word dictionary
- **Double time enabled** (20s)
- Gain based on word length: 2 chars = gain 1; 3 chars = gain 2; 4+ chars = gain 3

### 5.5 BEAT (Music)

**6 modes**, all based on rhythmic timing:

The BeatGenerator plays repeating audio beats. When the player drops a card, the timing relative to the beat cycle determines the gain.

| Mode | Description | Beat Period |
|------|-------------|-------------|
| double | Main beat + 4 sub-beats | 1.8s |
| single | Main beat only | 1.8s |
| double fast | Double at 1.3x speed | ~1.38s |
| single fast | Single at 1.6x speed | ~1.13s |
| tiktok | Main + one sub-beat | 1.8s |
| five | Main + 5 sub-beats, 2.4x slower | ~4.32s |

**Gain calculation:**
The beat timing is normalized to 0-1 (position within beat cycle). Mode-specific adjustments shift the timing window. Then:
- < 0.03 or > 0.97: gain 3 (perfect rhythm)
- < 0.12 or > 0.88: gain 2
- < 0.17 or > 0.83: gain 1
- < 0.25 or > 0.75: gain 0
- Otherwise: gain -1

### 5.6 MEMORY

**3 modes:**

| Mode | Description |
|------|-------------|
| show all | After merge, briefly reveals all cards on board |
| show one | After merge, briefly reveals the merged card only |
| every action | Reveals cards after every action (most information) |

Memory gain is computed as an average of all other active dimension gains:
- Avg < 0.7: gain -1
- 0.7-1.6: gain 1
- 1.6-2.7: gain 2
- >= 2.7: gain 3

The MemoryGenerator handles the visual hide/reveal of card contents using sprite swaps between `emptySprite` (card face hidden) and `fullSprite` (card face revealed).

### 5.7 MOTOR (Physical)

**3 modes**, all based on drag performance:

All modes use the formula: `successDrop = speedNorm / (1 + accuracyNorm)`

| Mode | Speed Factor | Accuracy Factor | Scale |
|------|-------------|-----------------|-------|
| speed accuracy | distance^0.7 / time | accuracy^1.75 | 1x |
| speed accuracy halfway | (20+dist)^0.7 / time^0.7 | ((half+dist)/2)^2.1 | 1.5x |
| visit all slots | fixed distance | avg distance to all 5 slots | 3.5x |

**Gain thresholds:**
- < 15: gain -1
- 15-21: gain 0
- 21-30: gain 1
- 30-55: gain 2
- >= 55: gain 3

Motor action is evaluated when a card is first placed (not during merges), measuring how fast and accurately the player dragged the card to its slot.

---

## 6. MANA SYSTEM

### 6.1 Mana Economy

| Parameter | Difficulty 0 | Difficulty 1 | Difficulty 2 |
|-----------|-------------|-------------|-------------|
| Starting Mana | 200 | 150 | 100 |
| Reduction Multiplier | 0.9 | 0.8 | 0.7 |
| Increase Multiplier 1 | 1.5 | 1.2 | 1.1 |
| Increase Multiplier 2 | 2.0 | 1.5 | 1.3 |
| Increase Multiplier 3 | 2.5 | 2.0 | 1.7 |
| Card Draw Threshold | 100 | 200 | 400 |
| Max Merges per Card | 3 | 4 | 5 |

### 6.2 Mana Sources and Sinks

**Sources (increase mana):**
- Selling a card (refunds current card mana value)
- Good merges multiply card mana value upward

**Sinks (decrease mana):**
- Drawing a card (costs `cardCost`, base 10)
- Time-based decay (continuous, `elapsed_time / 5` per frame)
- Bad merges multiply card mana value downward (below 1.0)

### 6.3 Merge Gain to Mana Multiplier Mapping

| Gain Level | Sprite | Mana Multiplier Applied |
|------------|--------|------------------------|
| 3 (best) | thumbs_up_3 | manaIncreaseMultiplier3 |
| 2 (good) | thumbs_up_2 | manaIncreaseMultiplier2 |
| 1 (ok) | thumbs_up_1 | manaIncreaseMultiplier1 |
| 0 (neutral) | flat | No change |
| -1 (bad) | thumbs_down / loss | manaReductionMultiplier |

### 6.4 Super Cards

- Player starts with 3 super cards (tracked by `SuperDisplay`)
- Super card = 4x normal cost
- Super cards generate the "ideal" starting value for each dimension:
  - Number add: 0 (the merge target)
  - Number multiply: x1
  - Color: null color (white/black)
  - Shape: special index (nihil equivalent)
  - Word: "nihil" word
- Toggled by double-clicking a BuyCardButton

---

## 7. TUTORIAL SYSTEM

14-step linear tutorial controlled by `TutorialController`:

| Step | Trigger | Teaches |
|------|---------|---------|
| 1 | Game start | Buy first card (press Space) |
| 2 | Card drawn | Move card to a slot |
| 3 | Card placed | Buy another card |
| 4 | Second card drawn | Merge two cards |
| 5 | Merge complete | Understanding merge gains |
| 6 | After gains | The goal (maintain mana) |
| 7 | After goal | Selecting different games |
| 8 | After games | Selling a card |
| 9 | After sell | Understanding card value |
| 10 | After value | The timer |
| 11 | After timer | Card dimensions |
| 12 | After dimensions | Other dimensions |
| 13 | After other dims | Pause/help system |
| 14 | After pause | Stats screen |

Tutorial state is persisted (`tutorialPlayed` flag) so it only runs once.

---

## 8. SEVEN MINUTE WORKOUT

The `SevenMinuteController` generates a curated 5-game sequence:

| Game # | Structure |
|--------|-----------|
| 1 | 2 modes from {Math, Visual, Spatial, Verbal} |
| 2 | 2 different modes from {Math, Visual, Spatial, Verbal} |
| 3 | Music + 1 mode from first 4 categories |
| 4 | Memory + 1 mode from first 4 categories |
| 5 | Physical + 1 mode from first 4 categories |

Each category randomly selects from its available mode variations. Progress is shown via `WorkoutProgressBar`. The workout state is persisted and regenerated after all 5 games complete.

---

## 9. STATISTICS AND RANKING

### 9.1 Per-Game Collection (StatsCollectorExpanded)

After each game, the following are tracked per active mode:
- Number of merges
- Mana gained/lost per merge
- Peak mana reached
- Peak mana-per-second rate

### 9.2 Historical Aggregation (StatsControllerExpanded)

- All game stats persisted to SaveGame dictionary
- 45 tracked metrics organized by category
- Three visualization modes:
  - **Line Chart**: Single metric trend over time
  - **Distribution Chart**: Pie chart of current session breakdown
  - **Ranking Chart**: Bar chart comparing performance across all categories

### 9.3 Logistic Ranking

Raw performance is converted to a percentile (6-100%) using:

```
percentile = 100 / (1 + exp(-std * (value - mean)))
```

Where `mean` and `std` are category-specific benchmark values:
- Generic: mean=1.3, std=1.6
- Math: mean=1.3, std=1.4
- Visual: mean=1.3, std=1.3
- Spatial: mean=1.2, std=1.3
- Verbal: mean=1.3, std=1.3
- Music: mean=1.3, std=1.3
- Memory: mean=1.3, std=1.3
- Physical: mean=1.3, std=1.3

---

## 10. MONETIZATION

### 10.1 Advertising (AdsControllerYedi)

- **Interstitial ads**: Shown between games (loaded at level start)
- **Rewarded ads**: Offered when timer expires, grants +10 seconds (max 2 per game)
- GDPR consent granted automatically at startup

### 10.2 In-App Purchase (UnlockController)

- Single product: `EM_IAPConstants.Product_unlock`
- **Free tier**: Levels 0-8 + stats screen (limited to 20 games)
- **Premium tier**: All levels + unlimited stats + custom combinations (Level 9)

### 10.3 Paywall Points

- Level 9 (custom combination): Requires purchase
- Stats screen: Free for first 20 games, then requires purchase

---

## 11. SETTINGS (OptionsController + PlayerPrefsController)

| Setting | Key | Range | Default |
|---------|-----|-------|---------|
| Volume | MASTER_VOLUME_KEY | 0.0-1.0 | 0.6 (60%) |
| Difficulty | DIFFICULTY_KEY | 0-2 | 0 |
| Player Name | PLAYER_NAME_KEY | 3+ chars | "yedi_player" |

Difficulty affects:
- Starting mana (200/150/100)
- Merge multipliers (reward/penalty ratios)
- Card draw cost threshold
- Max merges per card (3/4/5)
- Starting lives (3/2/1 in LivesDisplay)

---

## 12. MARKER / STUB CLASSES

The following ~35 classes are empty `MonoBehaviour` stubs used as component markers for `FindAnyObjectByType<T>()` lookups or as prefab attachment points:

**Slot markers**: Slot1, Slot2, Slot3, Slot4, Slot5, Slot6, Slot7, Slots
**Gain markers**: NumberGain, ColorGain, ShapeGain, WordGain, BeatGain, MemoryGain, MotorGain
**Result markers**: GameResultMana, GameResultManaSpeed, GameResultMath, GameResultColor, GameResultSpatial, GameResultVerbal, GameResultMusic, GameResultMemory, GameResultMotor, GameResultTitle
**UI markers**: AudioSourceEffects, BeatSource, CardFrameBackground, ColorText, CurrentPlotShownText, DrawCardCollider, GameDescription, GameDescriptionCanvas, GameInfo, HeptagonCanvas, HeptagonItem, LevelCompleteCanvas, MainCanvas, MotorGenerator, OptionsDifficultySlider, OptionsPlayerName, OptionsPlayerNameSaved, OptionsUnlock, OptionsVolumeSlider, PurchasedDialogCanvas, RankingValueStats, ResetDialogCanvas, Tutorial, TutorialPopup, UnlockButton, UnlockDialogCanvas, VideoButtonsOptions, VideoCanvas, VideoObject, WorkoutNextGameName

These markers allow the code to locate specific GameObjects in the scene hierarchy without hardcoding names or paths.

---

## 13. KEY DATA FLOWS

### 13.1 Card Creation Flow

```
Player presses Space
  -> CardDrawer.DrawCard()
    -> Checks ManaDisplay.HaveEnoughMana()
    -> Instantiates Card prefab at SlotNew position
    -> ManaDisplay.SpendMana(cardCost)
    -> SlotGeneric.SetFilledInfo(true)
    -> Card.Start()
      -> Gets cardType from CardDrawer
      -> Calculates cardMana = cost * manaReductionMultiplier
      -> Instantiates CardFrame prefab
      -> CardFrame.Start()
        -> Gets all 7 dimension components
        -> Calls ActivateComponents(cardType)
          -> Decodes cardType to determine which dimensions are active
          -> Activates matching dimension components
          -> Each component generates random initial value
```

### 13.2 Merge Flow

```
Player drags card onto occupied slot
  -> CardFrame.Update() detects drop on filled slot
    -> For each active dimension:
      -> Calls ComputeMergeXXXGain() for preview
      -> Displays gain sprite (thumbs up/down)
    -> For each active dimension:
      -> Calls MergeXXXCard() on TARGET card
        -> Applies dimension-specific merge logic
        -> Calls cardAttached.ChangeCardMana(multiplier)
          -> Card.cardMana *= multiplier
          -> SlotGeneric.UpdateManaValue()
    -> Destroys dragged card
    -> Updates StatsCollectorExpanded
```

### 13.3 Mana Decay Flow

```
Every frame:
  -> ManaDisplay.Update()
    -> timeManaCost = Time.deltaTime / timeManaDiv (5)
    -> timeManaCostCumulative += timeManaCost
    -> When cumulative >= 1:
      -> SpendMana(1)
      -> If mana <= 0:
        -> LevelController.StopCardDealing()
        -> Game Over
```

---

## 14. COMPLETE MODE CATALOG

### 14.1 All 40+ Game Variations

| Category | Mode | Description | Complexity |
|----------|------|-------------|------------|
| **Math** | add | Integer addition targeting 0 | Easy |
| | multiply | Fraction multiplication targeting 1 | Medium |
| | gcd | Greatest common divisor matching | Medium |
| | vector | 2D vector combination | Hard |
| | interval | Mathematical interval algebra | Hard |
| | trigon | Trigonometric function matching | Hard |
| | sort | Digit sorting | Medium |
| **Visual** | add | RGB additive color mixing | Easy |
| | subtract | CMY subtractive color mixing | Medium |
| | gray | Grayscale level combination | Easy |
| | text | Color name matching (Stroop) | Medium |
| **Spatial** | triangle | Triangle orientation matching | Easy |
| | rectangle | Rectangle pattern matching | Easy |
| | triple | Triple shape combination | Medium |
| | kanizsa | Kanizsa illusion matching | Medium |
| | sphere | 3D projection matching | Hard |
| | hanoi | Tower of Hanoi | Hard (double time) |
| **Verbal** | verbs | Antonym verb pairs | Easy |
| | adjectives | Antonym adjective pairs | Easy |
| | nouns | Antonym noun pairs | Easy |
| | synVerbs | Synonym verb pairs | Medium |
| | synAdjectives | Synonym adjective pairs | Medium |
| | grammar | Grammar structure pairs | Medium |
| | questions | Question-answer pairs | Medium |
| | scrabble | Letter combination + dictionary | Hard (double time) |
| **Music** | double | Main + 4 sub-beats | Easy |
| | single | Main beat only | Easy |
| | double fast | Fast double beat | Medium |
| | single fast | Fast single beat | Medium |
| | tiktok | Two-beat pattern | Medium |
| | five | 5 sub-beats, slow | Hard |
| **Memory** | show all | Reveal all cards after merge | Easy |
| | show one | Reveal one card after merge | Medium |
| | every action | Reveal after every action | Easy |
| **Physical** | speed accuracy | Speed + drop precision | Easy |
| | speed accuracy halfway | Speed + midpoint accuracy | Medium |
| | visit all slots | Visit all 5 slots | Hard |

---

## 15. PERSISTENCE MAP (SaveGame Keys)

| Key | Type | Purpose |
|-----|------|---------|
| `selectedLevel` | int | Current level selection |
| `modeNumber/Color/Shape/Word/Beat/Memory/Motor` | string | Active modes per dimension |
| `gamePaused` | bool | Pause state |
| `levelTimerFinished` | bool | Timer status |
| `numberOfRewardedAdsWatched` | int | Rewarded ad counter |
| `tutorialPlayed` | bool | Tutorial completion flag |
| `doubleTime` | bool | Extended timer for hard modes |
| `currentScene` | int | Scene index for resume |
| `purchaseGame` | bool | Purchase status |
| `numberOfGamesPlayed` | int | Total games for paywall |
| `workoutInitialized` | bool | Workout state |
| `gamesPlayed` | bool[] | 5-game workout progress |
| `game1Modes..game5Modes` | string[] | Workout game configurations |

---

## 16. AUDIO SYSTEM

| Sound | Usage |
|-------|-------|
| `moon_music_1344997839.mp3` | Background music (main) |
| `Surface Exploration LOOP.mp3` | Alternative background loop |
| `Spooky_Groddle_1291879214.mp3` | Alternative background |
| `MAGIC_SPELL_Flame_01/03_mono.wav` | Card draw SFX |
| `COINS_Rattle_01_mono.wav` | Card sell SFX |
| `IMPACT_Wood_Plank_On_Wood_Pile_01_mono.wav` | Card place SFX |
| `IMPACT_Energy_Solid_08_mono.wav` | Merge SFX |
| `IMPACT_Incoming_Buzz_Metal_03_mono.wav` | Beat 1 |
| `PEN_Marker_Scribble_mono.wav` | Beat 2 |
| `PUZZLE_Success_Harp_Three_Note_Bright_End_Wet_stereo.wav` | Level complete |
| `quest_complete.mp3` | Achievement |
| `game_loaded_2.mp3` | Game loaded |
| `level_up_kazoo.mp3` | Level up |
| `BREAK_Bone_or_Neck_mono.wav` | Damage/failure |
| `THUD_Bright_03_mono.wav` | UI interaction |
| `MAGIC_SPELL_Morphing_Synth_Harp_Scales_Deep_stereo.wav` | Special effect |
| `MAGIC_SPELL_Stutter_Echo_stereo.wav` | Special effect |

---

*Report generated 2026-04-05*
