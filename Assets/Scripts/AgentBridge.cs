using System.Collections;
using System.Collections.Generic;
using System.Runtime.InteropServices;
using UnityEngine;
using UnityEngine.SceneManagement;

/// <summary>
/// Bridge between Python gym/VLM agents and the Unity game.
/// Receives commands via WebSocket (through AgentBridge.jslib),
/// executes game actions, and sends back serialized game state.
/// </summary>
public class AgentBridge : MonoBehaviour
{
    public static AgentBridge Instance { get; private set; }

#if UNITY_WEBGL && !UNITY_EDITOR
    [DllImport("__Internal")] private static extern void JS_AgentConnect(string url);
    [DllImport("__Internal")] private static extern void JS_AgentSendMessage(string json);
    [DllImport("__Internal")] private static extern void JS_AgentSendScreenshot(int seq);
    [DllImport("__Internal")] private static extern int JS_AgentIsConnected();
    [DllImport("__Internal")] private static extern void JS_AgentDisconnect();
#endif

    // Agent mode: when true, game waits for agent commands
    public static bool agentMode = false;
    public static string agentServerUrl = "";

    // Cached references (populated after game scene loads)
    ManaDisplay manaDisplay;
    GameTimer gameTimer;
    CardDrawer cardDrawer;
    LevelController levelController;
    BeatGenerator beatGenerator;
    StatsCollectorExpanded statsCollector;

    // Slot references
    SlotGeneric slotNew;
    SlotGeneric[] numberedSlots; // slots 1-5
    SlotGeneric slotSell;

    bool refsReady = false;
    int cardIdCounter = 0;

    // Step-based game limit (0 = no limit, use timer)
    int maxSteps = 0;
    int actionCount = 0;

    // Auto-create the AgentBridge at startup — no manual scene setup needed
    [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
    static void AutoCreate()
    {
        if (Instance != null) return;
        var go = new GameObject("AgentBridge");
        go.AddComponent<AgentBridge>();
        Debug.Log("[AgentBridge] Auto-created AgentBridge GameObject");
    }

    void Awake()
    {
        if (Instance != null && Instance != this)
        {
            Destroy(gameObject);
            return;
        }
        Instance = this;
        DontDestroyOnLoad(gameObject);
    }

    void Start()
    {
        SceneManager.sceneLoaded += OnSceneLoaded;
        TryCacheReferences();

        // Auto-connect if ?agent=true is in the URL
        if (!agentMode)
        {
            StartCoroutine(AutoConnectFromUrl());
        }
    }

    IEnumerator AutoConnectFromUrl()
    {
        // Wait for everything to initialize
        yield return new WaitForSeconds(1f);

#if UNITY_WEBGL && !UNITY_EDITOR
        // Check URL for ?agent=true via JavaScript
        string url = GetAgentUrlFromBrowser();
        if (!string.IsNullOrEmpty(url))
        {
            Debug.Log("[AgentBridge] Auto-connecting to: " + url);
            ConnectToServer(url);
        }
#endif
    }

#if UNITY_WEBGL && !UNITY_EDITOR
    [DllImport("__Internal")] private static extern string JS_AgentGetUrlParam();
#endif

    string GetAgentUrlFromBrowser()
    {
#if UNITY_WEBGL && !UNITY_EDITOR
        try
        {
            string result = JS_AgentGetUrlParam();
            return result;
        }
        catch (System.Exception e)
        {
            Debug.LogWarning("[AgentBridge] Could not read URL params: " + e.Message);
        }
#endif
        return null;
    }

    void OnSceneLoaded(Scene scene, LoadSceneMode mode)
    {
        refsReady = false;
        StartCoroutine(CacheReferencesDelayed());
    }

    IEnumerator CacheReferencesDelayed()
    {
        // Wait a frame for all singletons to initialize
        yield return null;
        yield return null;
        TryCacheReferences();

        // In step-based mode, disable the game timer so only step count ends the game
        if (maxSteps > 0 && gameTimer != null)
        {
            gameTimer.levelTime = 999999f; // Effectively infinite
            Debug.Log("[AgentBridge] Step-based mode: timer disabled, max_steps=" + maxSteps);
        }

        // If agent is connected, send a scene_loaded event
        if (agentMode)
        {
            SendEvent("scene_loaded", new Dictionary<string, object> {
                { "scene", SceneManager.GetActiveScene().name }
            });
        }
    }

    void TryCacheReferences()
    {
        manaDisplay = ManaDisplay.Instance;
        gameTimer = GameTimer.Instance;
        cardDrawer = CardDrawer.Instance;
        levelController = LevelController.Instance;
        beatGenerator = BeatGenerator.Instance;
        statsCollector = StatsCollectorExpanded.Instance;

        // Find slots
        SlotNew slotNewObj = FindAnyObjectByType<SlotNew>();
        if (slotNewObj != null)
            slotNew = slotNewObj.GetComponent<SlotGeneric>();

        SlotSell slotSellObj = FindAnyObjectByType<SlotSell>();
        if (slotSellObj != null)
            slotSell = slotSellObj.GetComponent<SlotGeneric>();

        // Find numbered slots (1-5)
        numberedSlots = new SlotGeneric[5];
        SlotGeneric[] allSlots = FindObjectsByType<SlotGeneric>(FindObjectsSortMode.None);
        foreach (SlotGeneric sg in allSlots)
        {
            if (sg.slotNumber >= 1 && sg.slotNumber <= 5)
                numberedSlots[sg.slotNumber - 1] = sg;
        }

        refsReady = (manaDisplay != null && gameTimer != null);
        if (refsReady)
            Debug.Log("[AgentBridge] References cached successfully");
    }

    // ------------------------------------------------------------------
    // WebSocket connection management
    // ------------------------------------------------------------------

    public void ConnectToServer(string url)
    {
        agentServerUrl = url;
        agentMode = true;
#if UNITY_WEBGL && !UNITY_EDITOR
        JS_AgentConnect(url);
#else
        Debug.Log("[AgentBridge] WebSocket not available outside WebGL. URL: " + url);
#endif
    }

    // Called from JS when WebSocket connects
    public void OnConnected(string unused)
    {
        Debug.Log("[AgentBridge] Connected to agent server");
        agentMode = true;
    }

    // ------------------------------------------------------------------
    // Command handler — called from AgentBridge.jslib via SendMessage
    // ------------------------------------------------------------------

    public void OnAgentCommand(string commandJson)
    {
        var cmd = JsonUtility.FromJson<AgentCommand>(commandJson);
        if (cmd == null)
        {
            SendError(0, "Failed to parse command: " + commandJson);
            return;
        }

        Debug.Log("[AgentBridge] Command: " + cmd.type + " seq=" + cmd.seq);

        switch (cmd.type)
        {
            case "get_state":
                SendState(cmd.seq);
                break;
            case "get_screenshot":
                TakeScreenshot(cmd.seq);
                break;
            case "draw_card":
                ExecuteDrawCard(cmd);
                break;
            case "move_card":
                ExecuteMoveCard(cmd);
                break;
            case "sell_card":
                ExecuteSellCard(cmd);
                break;
            case "configure":
                ExecuteConfigure(cmd);
                break;
            case "reset":
                ExecuteReset(cmd);
                break;
            case "set_time_scale":
                Time.timeScale = cmd.time_scale;
                SendAck(cmd.seq, true);
                break;
            case "step_time":
                StartCoroutine(StepTime(cmd.seq, cmd.delta));
                break;
            case "get_valid_actions":
                SendValidActions(cmd.seq);
                break;
            case "start_game":
                ExecuteStartGame(cmd);
                break;
            case "ping":
                SendAck(cmd.seq, true);
                break;
            default:
                SendError(cmd.seq, "Unknown command type: " + cmd.type);
                break;
        }
    }

    // ------------------------------------------------------------------
    // Action execution
    // ------------------------------------------------------------------

    bool IsStepLimitReached()
    {
        return maxSteps > 0 && actionCount >= maxSteps;
    }

    void IncrementAction()
    {
        actionCount++;
    }

    IEnumerator EndGameAfterFrames(int seq, int frames)
    {
        for (int i = 0; i < frames; i++)
            yield return null;
        TryCacheReferences();

        // Send final state with game_over = true
        SendState(seq);

        // Auto-return to Heptagon after a short delay
        yield return null;
        if (levelController != null)
            levelController.BackButtonPressed();
        else
            SceneManager.LoadScene("Scene Selection Screen");
    }

    void ExecuteDrawCard(AgentCommand cmd)
    {
        if (!refsReady)
        {
            SendError(cmd.seq, "Game not ready");
            return;
        }

        if (cardDrawer == null)
        {
            SendError(cmd.seq, "CardDrawer not found");
            return;
        }

        // Check if draw is possible
        if (slotNew != null && slotNew.GetFilledInfo())
        {
            SendError(cmd.seq, "SlotNew is occupied");
            return;
        }

        if (!manaDisplay.HaveEnoughMana(cardDrawer.GetCardCost()))
        {
            SendError(cmd.seq, "Not enough mana");
            return;
        }

        cardDrawer.DrawCard();
        cardIdCounter++;
        IncrementAction();

        // Card creation spans 3 frames: Card.Awake → Card.Start(creates CardFrame) → CardFrame.Update(ActivateComponents)
        // Wait 4 frames to ensure all initialization is complete before reading state
        if (IsStepLimitReached())
            StartCoroutine(EndGameAfterFrames(cmd.seq, 4));
        else
            StartCoroutine(SendStateAfterFrames(cmd.seq, 4));
    }

    void ExecuteMoveCard(AgentCommand cmd)
    {
        if (!refsReady)
        {
            SendError(cmd.seq, "Game not ready");
            return;
        }

        SlotGeneric sourceSlot = GetSlotByName(cmd.source);
        SlotGeneric targetSlot = GetSlotByName(cmd.target);

        if (sourceSlot == null)
        {
            SendError(cmd.seq, "Invalid source slot: " + cmd.source);
            return;
        }
        if (targetSlot == null)
        {
            SendError(cmd.seq, "Invalid target slot: " + cmd.target);
            return;
        }
        if (!sourceSlot.GetFilledInfo())
        {
            SendError(cmd.seq, "Source slot is empty: " + cmd.source);
            return;
        }

        Card card = sourceSlot.GetCardObject();
        if (card == null)
        {
            SendError(cmd.seq, "No card in source slot");
            return;
        }

        CardFrame frame = card.GetCardFrame();
        if (frame == null)
        {
            SendError(cmd.seq, "No CardFrame for card");
            return;
        }

        // Execute programmatic drop
        frame.ExecuteProgrammaticDrop(targetSlot, cmd.motor_time, cmd.motor_distance,
            cmd.motor_dist_to_slot, cmd.motor_half_distance, cmd.motor_min_distances);
        IncrementAction();

        if (IsStepLimitReached())
            StartCoroutine(EndGameAfterFrames(cmd.seq, 2));
        else
            StartCoroutine(SendStateAfterFrames(cmd.seq, 2));
    }

    void ExecuteSellCard(AgentCommand cmd)
    {
        if (!refsReady)
        {
            SendError(cmd.seq, "Game not ready");
            return;
        }

        SlotGeneric sourceSlot = GetSlotByName(cmd.source);
        if (sourceSlot == null || !sourceSlot.GetFilledInfo())
        {
            SendError(cmd.seq, "Invalid or empty source slot: " + cmd.source);
            return;
        }

        if (slotSell == null)
        {
            SendError(cmd.seq, "No sell slot found");
            return;
        }

        Card card = sourceSlot.GetCardObject();
        CardFrame frame = card.GetCardFrame();

        // Move to sell slot triggers sell logic
        frame.ExecuteProgrammaticDrop(slotSell, 0, 0, 0, 0, null);
        IncrementAction();

        if (IsStepLimitReached())
            StartCoroutine(EndGameAfterFrames(cmd.seq, 2));
        else
            StartCoroutine(SendStateAfterFrames(cmd.seq, 2));
    }

    void ExecuteConfigure(AgentCommand cmd)
    {
        // Store configuration for when the game scene loads
        if (cmd.seed > 0)
        {
            Random.InitState(cmd.seed);
        }

        // Set player name if provided
        if (!string.IsNullOrEmpty(cmd.player_name))
        {
            ScoreManager.playerName = cmd.player_name;
        }

        SendAck(cmd.seq, true);
    }

    void ExecuteReset(AgentCommand cmd)
    {
        // Reload the gameplay scene for a clean reset
        Debug.Log("[AgentBridge] Resetting — reloading gameplay scene");
        Time.timeScale = 1;
        SceneManager.LoadScene("Level 1 Space for Unity");
        SendAck(cmd.seq, true);
    }

    void ExecuteStartGame(AgentCommand cmd)
    {
        // Set game modes directly on HeptagonController static fields
        // This bypasses the Heptagon UI entirely
        HeptagonController.modeNumber = string.IsNullOrEmpty(cmd.mode_number) ? null : cmd.mode_number;
        HeptagonController.modeColor = string.IsNullOrEmpty(cmd.mode_color) ? null : cmd.mode_color;
        HeptagonController.modeShape = string.IsNullOrEmpty(cmd.mode_shape) ? null : cmd.mode_shape;
        HeptagonController.modeWord = string.IsNullOrEmpty(cmd.mode_word) ? null : cmd.mode_word;
        HeptagonController.modeBeat = string.IsNullOrEmpty(cmd.mode_beat) ? null : cmd.mode_beat;
        HeptagonController.modeMemory = string.IsNullOrEmpty(cmd.mode_memory) ? null : cmd.mode_memory;
        HeptagonController.modeMotor = string.IsNullOrEmpty(cmd.mode_motor) ? null : cmd.mode_motor;

        // Set selectedLevel = 9 so LevelController.SetLevelParameters() reads from mode fields
        LevelLoader.selectedLevel = 9;
        BayatGames.SaveGameFree.SaveGame.Save<int>("selectedLevel", 9);

        // Step-based game limit (0 = no limit, use timer)
        maxSteps = cmd.max_steps > 0 ? cmd.max_steps : 0;
        actionCount = 0;

        // Set seed if provided
        if (cmd.seed > 0)
            Random.InitState(cmd.seed);

        // Set player name if provided
        if (!string.IsNullOrEmpty(cmd.player_name))
            ScoreManager.playerName = cmd.player_name;

        Debug.Log("[AgentBridge] Starting game: number=" + HeptagonController.modeNumber
            + " color=" + HeptagonController.modeColor
            + " shape=" + HeptagonController.modeShape
            + " word=" + HeptagonController.modeWord
            + " beat=" + HeptagonController.modeBeat
            + " memory=" + HeptagonController.modeMemory
            + " motor=" + HeptagonController.modeMotor
            + " max_steps=" + maxSteps);

        // Load the gameplay scene
        Time.timeScale = 1;
        SceneManager.LoadScene("Level 1 Space for Unity");
        SendAck(cmd.seq, true);
    }

    IEnumerator StepTime(int seq, float delta)
    {
        // Temporarily resume time for delta seconds
        float prevScale = Time.timeScale;
        Time.timeScale = 1f;
        yield return new WaitForSeconds(delta);
        Time.timeScale = prevScale;
        SendState(seq);
    }

    // ------------------------------------------------------------------
    // State serialization
    // ------------------------------------------------------------------

    void SendState(int seq)
    {
        if (!refsReady)
        {
            SendError(seq, "Game not ready");
            return;
        }

        string json = SerializeGameState(seq);
        SendToServer(json);
    }

    string SerializeGameState(int seq)
    {
        var state = new GameStateMsg();
        state.seq = seq;
        state.type = "state";

        // Global game state
        state.mana = manaDisplay != null ? manaDisplay.manaValue : 0;
        state.mana_max = manaDisplay != null ? manaDisplay.manaValueMax : 0;

        if (gameTimer != null)
        {
            state.timer_remaining = Mathf.Max(0, gameTimer.levelTime - gameTimer.totalTime);
            state.timer_total = gameTimer.levelTime;
            bool timerOver = gameTimer.triggeredLevelFinished ||
                (levelController != null && levelController.gameFinished);
            bool stepsOver = maxSteps > 0 && actionCount >= maxSteps;
            state.game_over = timerOver || stepsOver;
        }

        state.action_count = actionCount;
        state.max_steps = maxSteps;

        state.game_time = Time.timeSinceLevelLoad;

        // Beat phase
        if (beatGenerator != null && beatGenerator.GetBeatActivated())
        {
            state.beat_active = true;
            state.beat_phase = beatGenerator.GetBeat1Time(1);
            state.beat_period = beatGenerator.beatPeriod;
        }

        // Config
        state.config_key = ScoreManager.currentConfigKey;

        // Active modes
        state.mode_number = HeptagonController.modeNumber;
        state.mode_color = HeptagonController.modeColor;
        state.mode_shape = HeptagonController.modeShape;
        state.mode_word = HeptagonController.modeWord;
        state.mode_beat = HeptagonController.modeBeat;
        state.mode_memory = HeptagonController.modeMemory;
        state.mode_motor = HeptagonController.modeMotor;

        // Can draw?
        state.can_draw = (slotNew != null && !slotNew.GetFilledInfo() &&
            cardDrawer != null && manaDisplay != null &&
            manaDisplay.HaveEnoughMana(cardDrawer.GetCardCost()));

        // Slots
        state.slots = new SlotMsg[7];
        // Slot 0 = SlotNew
        state.slots[0] = SerializeSlot(slotNew, "new");
        // Slots 1-5
        for (int i = 0; i < 5; i++)
        {
            state.slots[i + 1] = SerializeSlot(
                numberedSlots != null && i < numberedSlots.Length ? numberedSlots[i] : null,
                (i + 1).ToString());
        }
        // Slot 6 = sell
        state.slots[6] = SerializeSlot(slotSell, "sell");

        // Valid actions
        state.valid_actions = ComputeValidActions();

        return JsonUtility.ToJson(state);
    }

    SlotMsg SerializeSlot(SlotGeneric slot, string name)
    {
        var msg = new SlotMsg();
        msg.name = name;
        msg.occupied = false;

        if (slot == null) return msg;

        msg.occupied = slot.GetFilledInfo();
        if (!msg.occupied) return msg;

        Card card = slot.GetCardObject();
        if (card == null)
        {
            msg.occupied = false;
            return msg;
        }

        CardFrame frame = card.GetCardFrame();
        if (frame == null) return msg;

        msg.card_mana = card.GetCardMana();
        msg.merges_done = frame.numberOfMerges;
        msg.number_active = frame.numberActive;

        // Number dimension (-1000 is the sentinel for "not yet activated")
        if (frame.numberCard != null && frame.numberCard.numberSelected > -999f)
            msg.number_value = frame.numberCard.numberSelected;
        else
            msg.number_value = 0;

        // Color dimension
        if (frame.colorCard != null)
        {
            Color c = frame.colorCard.colorSelected;
            msg.color_r = c.r;
            msg.color_g = c.g;
            msg.color_b = c.b;
            msg.color_index_gray = frame.colorCard.colorIndexGray;
        }

        // Shape dimension
        if (frame.shapeCard != null)
            msg.shape_index = frame.shapeCard.spriteSelectedIndex;

        // Word dimension
        if (frame.wordCard != null && frame.wordCard.wordSelectedList != null)
            msg.word_value = string.Join(",", frame.wordCard.wordSelectedList);

        // Memory: check if card is hidden
        if (frame.memoryCard != null)
        {
            // Check if background sorting order indicates hidden state
            var bg = frame.GetComponentInChildren<CardFrameBackground>();
            if (bg != null)
            {
                var sr = bg.GetComponent<SpriteRenderer>();
                msg.memory_hidden = (sr != null && sr.sortingOrder >= 13);
            }
        }

        return msg;
    }

    // ------------------------------------------------------------------
    // Valid action computation
    // ------------------------------------------------------------------

    int[] ComputeValidActions()
    {
        var valid = new List<int>();

        // Action 0: DRAW_CARD
        if (slotNew != null && !slotNew.GetFilledInfo() &&
            cardDrawer != null && manaDisplay != null &&
            manaDisplay.HaveEnoughMana(cardDrawer.GetCardCost()) &&
            !cardDrawer.haltCardDraw)
        {
            valid.Add(0);
        }

        // Actions 1-30: MOVE(src, dst)
        // src_idx: 0=new, 1-5=slots
        // dst_idx: 1-5 (slot numbers)
        // action = 1 + src_idx * 5 + (dst_idx - 1)
        SlotGeneric[] sources = new SlotGeneric[6];
        sources[0] = slotNew;
        for (int i = 0; i < 5; i++)
            sources[i + 1] = numberedSlots != null && i < numberedSlots.Length ? numberedSlots[i] : null;

        for (int srcIdx = 0; srcIdx < 6; srcIdx++)
        {
            SlotGeneric src = sources[srcIdx];
            if (src == null || !src.GetFilledInfo()) continue;

            Card card = src.GetCardObject();
            if (card == null) continue;
            CardFrame frame = card.GetCardFrame();
            if (frame == null) continue;

            for (int dstIdx = 1; dstIdx <= 5; dstIdx++)
            {
                if (numberedSlots == null || dstIdx - 1 >= numberedSlots.Length) continue;
                SlotGeneric dst = numberedSlots[dstIdx - 1];
                if (dst == null || dst == src) continue;

                if (dst.GetFilledInfo())
                {
                    // Merge: only if card has merges remaining
                    if (frame.numberOfMerges < frame.maxNumberOfMerges)
                        valid.Add(1 + srcIdx * 5 + (dstIdx - 1));
                }
                else
                {
                    // Move to empty slot
                    valid.Add(1 + srcIdx * 5 + (dstIdx - 1));
                }
            }

            // Actions 31-36: SELL(src)
            if (slotSell != null)
                valid.Add(31 + srcIdx);
        }

        // Action 37: WAIT
        valid.Add(37);

        return valid.ToArray();
    }

    // ------------------------------------------------------------------
    // Screenshot
    // ------------------------------------------------------------------

    void TakeScreenshot(int seq)
    {
#if UNITY_WEBGL && !UNITY_EDITOR
        JS_AgentSendScreenshot(seq);
#else
        // In editor, send a placeholder
        SendToServer(JsonUtility.ToJson(new ScreenshotMsg {
            seq = seq, type = "screenshot", data = "", width = 960, height = 540
        }));
#endif
    }

    // ------------------------------------------------------------------
    // Valid actions response
    // ------------------------------------------------------------------

    void SendValidActions(int seq)
    {
        var msg = new ValidActionsMsg();
        msg.seq = seq;
        msg.type = "valid_actions";
        msg.actions = ComputeValidActions();
        SendToServer(JsonUtility.ToJson(msg));
    }

    // ------------------------------------------------------------------
    // Slot lookup
    // ------------------------------------------------------------------

    SlotGeneric GetSlotByName(string name)
    {
        if (name == "new" || name == "0") return slotNew;
        if (name == "sell") return slotSell;

        int num;
        if (int.TryParse(name, out num) && num >= 1 && num <= 5)
        {
            if (numberedSlots != null && num - 1 < numberedSlots.Length)
                return numberedSlots[num - 1];
        }
        return null;
    }

    // ------------------------------------------------------------------
    // Communication helpers
    // ------------------------------------------------------------------

    void SendToServer(string json)
    {
#if UNITY_WEBGL && !UNITY_EDITOR
        JS_AgentSendMessage(json);
#else
        Debug.Log("[AgentBridge] Would send: " + json.Substring(0, Mathf.Min(json.Length, 500)));
#endif
    }

    void SendAck(int seq, bool ok)
    {
        var msg = new AckMsg { seq = seq, type = "ack", ok = ok };
        SendToServer(JsonUtility.ToJson(msg));
    }

    void SendError(int seq, string message)
    {
        Debug.LogWarning("[AgentBridge] Error: " + message);
        var msg = new ErrorMsg { seq = seq, type = "error", message = message };
        SendToServer(JsonUtility.ToJson(msg));
    }

    public void SendEvent(string eventName, Dictionary<string, object> data = null)
    {
        var msg = "{\"type\":\"event\",\"name\":\"" + eventName + "\"";
        if (data != null)
        {
            foreach (var kv in data)
            {
                msg += ",\"" + kv.Key + "\":";
                if (kv.Value is string)
                    msg += "\"" + kv.Value + "\"";
                else
                    msg += kv.Value.ToString().ToLower();
            }
        }
        msg += "}";
        SendToServer(msg);
    }

    IEnumerator SendStateAfterFrames(int seq, int frames)
    {
        for (int i = 0; i < frames; i++)
            yield return null;
        TryCacheReferences(); // Refresh in case cards were created/destroyed
        SendState(seq);
    }

    // ------------------------------------------------------------------
    // Slot position data (for motor noise computation on Python side)
    // ------------------------------------------------------------------

    public Dictionary<string, float[]> GetSlotPositions()
    {
        var positions = new Dictionary<string, float[]>();
        if (slotNew != null)
            positions["new"] = new float[] { slotNew.transform.position.x, slotNew.transform.position.y };
        for (int i = 0; i < 5; i++)
        {
            if (numberedSlots != null && i < numberedSlots.Length && numberedSlots[i] != null)
                positions[(i + 1).ToString()] = new float[] {
                    numberedSlots[i].transform.position.x, numberedSlots[i].transform.position.y };
        }
        if (slotSell != null)
            positions["sell"] = new float[] { slotSell.transform.position.x, slotSell.transform.position.y };
        return positions;
    }

    // ------------------------------------------------------------------
    // Auto-connect on startup (reads URL from query string)
    // ------------------------------------------------------------------

    void Update()
    {
        // Auto-connect logic runs once
        if (!agentMode && !string.IsNullOrEmpty(agentServerUrl))
        {
            ConnectToServer(agentServerUrl);
        }
    }

    void OnDestroy()
    {
        SceneManager.sceneLoaded -= OnSceneLoaded;
    }

    // ------------------------------------------------------------------
    // Message DTOs (serialized via JsonUtility)
    // ------------------------------------------------------------------

    [System.Serializable]
    public class AgentCommand
    {
        public int seq;
        public string type;
        // draw_card
        public bool super_card;
        // move_card / sell_card
        public string source;
        public string target;
        // motor noise params
        public float motor_time;
        public float motor_distance;
        public float motor_dist_to_slot;
        public float motor_half_distance;
        public float[] motor_min_distances;
        // configure / start_game
        public int seed;
        public string player_name;
        // start_game modes
        public string mode_number;
        public string mode_color;
        public string mode_shape;
        public string mode_word;
        public string mode_beat;
        public string mode_memory;
        public string mode_motor;
        // step limit
        public int max_steps;
        // time control
        public float time_scale;
        public float delta;
    }

    [System.Serializable]
    public class GameStateMsg
    {
        public int seq;
        public string type;
        public float mana;
        public float mana_max;
        public float timer_remaining;
        public float timer_total;
        public float game_time;
        public bool game_over;
        public bool beat_active;
        public float beat_phase;
        public float beat_period;
        public string config_key;
        public string mode_number;
        public string mode_color;
        public string mode_shape;
        public string mode_word;
        public string mode_beat;
        public string mode_memory;
        public string mode_motor;
        public bool can_draw;
        public int action_count;
        public int max_steps;
        public SlotMsg[] slots;
        public int[] valid_actions;
    }

    [System.Serializable]
    public class SlotMsg
    {
        public string name;
        public bool occupied;
        public float card_mana;
        public float number_value;
        public float color_r;
        public float color_g;
        public float color_b;
        public int color_index_gray;
        public int shape_index;
        public string word_value;
        public bool memory_hidden;
        public int merges_done;
        public bool number_active;
    }

    [System.Serializable]
    public class AckMsg
    {
        public int seq;
        public string type;
        public bool ok;
    }

    [System.Serializable]
    public class ErrorMsg
    {
        public int seq;
        public string type;
        public string message;
    }

    [System.Serializable]
    public class ScreenshotMsg
    {
        public int seq;
        public string type;
        public string data;
        public int width;
        public int height;
    }

    [System.Serializable]
    public class ValidActionsMsg
    {
        public int seq;
        public string type;
        public int[] actions;
    }
}
