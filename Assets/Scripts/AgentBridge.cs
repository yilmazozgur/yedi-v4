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

    // Step-based game limit (0 = no limit, use timer).
    // Exposed via public properties so GameTimer can drive the on-screen
    // step counter UI without having to receive its own RPC from Python.
    int maxSteps = 0;
    int actionCount = 0;
    public int MaxSteps => maxSteps;
    public int ActionCount => actionCount;

    // Mana deducted when an agent issues a slot-to-slot move that does NOT
    // produce a merge (oscillation pattern). The reward-shaping penalty in
    // YediEnv is only visible to RL reward logs and to LLM conversational
    // mode; we need an in-game mana hit so the model sees the cost through
    // the normal state dump and max_mana scoring in every mode.
    const float UNPRODUCTIVE_MOVE_MANA_PENALTY = 5f;

    // When false (default), the bridge respects MemoryCard.hidden — slot dim
    // values are nulled out and merge_previews entries that touch a hidden
    // card are dropped, so the agent must actually remember card identity.
    // Set true to opt into a "perfect memory" ablation where the bridge ships
    // every value regardless of the hidden flag. Configured per-run via
    // start_game.perfect_memory.
    bool perfectMemory = false;

    // When true, Time.timeScale is forced to 0 between agent actions so that
    // mana drain and the episode timer do NOT advance while the agent is
    // thinking. This is the fairness invariant for model comparisons: a slow
    // model should not lose mana just because its inference takes longer.
    //
    // DEFAULT OFF: the previous "on" default froze card/merge animations
    // mid-flight (they use scaled WaitForSeconds coroutines) and caused the
    // Chrome WebGL canvas to lose its GPU mailbox during long idle gaps.
    // Re-enable per run via `set_time_scale` with time_scale <= 0 once the
    // animation pipeline is converted to WaitForSecondsRealtime.
    bool pauseBetweenActions = false;

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

        // Disable the Development Console overlay — it renders on the canvas
        // and ruins vision-based benchmarks (screenshots include the overlay).
        Debug.developerConsoleEnabled = false;
        Debug.developerConsoleVisible = false;
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
            Debug.Log("[AgentBridge] WARN: Could not read URL params: " + e.Message);
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

        // In WebGL, scene loading is async and singletons may not be ready
        // after just 2 frames. Retry for up to ~2 seconds (60 frames) so we
        // don't leave refsReady permanently false — which causes every
        // subsequent get_state to return "Game not ready" and wastes entire
        // benchmark episodes on a 15s polling timeout.
        if (!refsReady)
        {
            Debug.Log("[AgentBridge] Singletons not ready after 2 frames, retrying...");
            for (int i = 0; i < 60 && !refsReady; i++)
            {
                yield return null;
                TryCacheReferences();
            }
            if (!refsReady)
                Debug.Log("[AgentBridge] WARNING: Singletons still not ready after 60 retries");
        }

        // In step-based mode, disable the game timer so only step count ends the game
        if (maxSteps > 0 && gameTimer != null)
        {
            gameTimer.levelTime = 999999f; // Effectively infinite
            Debug.Log("[AgentBridge] Step-based mode: timer disabled, max_steps=" + maxSteps);
        }

        // Freeze the scene so mana drain and the episode timer do not advance
        // before the agent's first action. Without this, the stretch between
        // scene load and the first command burns 1-3 mana plus a chunk of
        // timer, which shows up as spurious starting-state variance.
        if (agentMode)
            PauseTimeForAgent();

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
        // Top-level try/catch around the whole dispatch. Without this, an
        // unhandled exception in a sync handler (e.g. NullRef in
        // ExecuteDrawCard) would silently die inside Unity's SendMessage
        // pump and the agent would sit on a 30s wait_for timeout. By
        // funnelling exceptions to SendError, the env gets a real reason
        // and the runner's per-episode catch can recover within 1 frame.
        AgentCommand cmd = null;
        try
        {
            cmd = JsonUtility.FromJson<AgentCommand>(commandJson);
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
                    // time_scale=0 means "agent-pause mode" (default — the
                    // bridge freezes time between actions). Any positive
                    // value disables the pause and runs real-time at that
                    // scale for Music/Motor ablations.
                    if (cmd.time_scale <= 0f)
                    {
                        pauseBetweenActions = true;
                        Time.timeScale = 0f;
                    }
                    else
                    {
                        pauseBetweenActions = false;
                        Time.timeScale = cmd.time_scale;
                    }
                    SendAck(cmd.seq, true);
                    break;
                case "step_time":
                    StartCoroutine(StepTime(cmd.seq, cmd.delta));
                    break;
                case "get_valid_actions":
                    SendValidActions(cmd.seq);
                    break;
                case "preview_merge":
                    ExecutePreviewMerge(cmd);
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
        catch (System.Exception e)
        {
            int seq = (cmd != null) ? cmd.seq : 0;
            string cmdType = (cmd != null && !string.IsNullOrEmpty(cmd.type)) ? cmd.type : "unknown";
            Debug.Log("[AgentBridge] ERROR: " + cmdType + " threw: " + e);
            SendError(seq, cmdType + " failed: " + e.Message);
        }
    }

    // ------------------------------------------------------------------
    // Coroutine error handling helpers
    // ------------------------------------------------------------------

    /// <summary>
    /// Run TryCacheReferences + SendState inside a try/catch so a serializer
    /// crash inside a coroutine surfaces as a bridge error instead of dying
    /// silently and stalling the agent on a 30s wait_for.
    ///
    /// After the state is on the wire we freeze Time.timeScale so no drain or
    /// timer advance happens while the agent is deliberating (see
    /// pauseBetweenActions). Every action handler calls ResumeTimeForAction()
    /// before executing so game logic, animations, and coroutines still run
    /// during the action itself.
    /// </summary>
    void SafeSendState(int seq, string cmdLabel)
    {
        try
        {
            TryCacheReferences();
            SendState(seq);
        }
        catch (System.Exception e)
        {
            Debug.Log("[AgentBridge] ERROR: " + cmdLabel + " serialize failed: " + e);
            SendError(seq, cmdLabel + " serialize failed: " + e.Message);
        }
        PauseTimeForAgent();
    }

    /// <summary>
    /// Freeze Time.timeScale so mana drain and the episode timer stop while
    /// the agent is thinking. Called at the end of every post-action state
    /// send. No-op when pauseBetweenActions is false (real-time ablation).
    /// </summary>
    void PauseTimeForAgent()
    {
        if (pauseBetweenActions)
            Time.timeScale = 0f;
    }

    /// <summary>
    /// Restore Time.timeScale = 1 before executing an action so card
    /// animations, delayed initializations, and game-logic coroutines that
    /// rely on Time.deltaTime can run to completion.
    /// </summary>
    void ResumeTimeForAction()
    {
        Time.timeScale = 1f;
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

        // Send final state with game_over = true
        SafeSendState(seq, "end_game");

        // Auto-return to Heptagon after a short delay
        yield return null;
        try
        {
            if (levelController != null)
                levelController.BackButtonPressed();
            else
                SceneManager.LoadScene("Scene Selection Screen");
        }
        catch (System.Exception e)
        {
            Debug.Log("[AgentBridge] WARN: EndGameAfterFrames scene unload threw: " + e.Message);
        }
    }

    void ExecuteDrawCard(AgentCommand cmd)
    {
        if (!refsReady)
        {
            SendError(cmd.seq, "Game not ready");
            return;
        }

        ResumeTimeForAction();

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

        if (cardDrawer.GetCardType() <= 0f)
        {
            SendError(cmd.seq, "CardDrawer cardType not set (still " + cardDrawer.GetCardType() + ")");
            return;
        }

        cardDrawer.DrawCard();
        cardIdCounter++;
        IncrementAction();

        // Card creation spans multiple frames: Card.Awake → Card.Start (creates
        // CardFrame) → CardFrame.Awake → CardFrame.Start (resolves child cards) →
        // CardFrame.Update (calls ActivateComponents). A fixed-frame wait was
        // racy — sometimes the bridge serialized a card whose numberSelected was
        // still the -1000 sentinel and the agent saw a "blank" card. We now poll
        // the slot every frame and call EnsureActivated() so the state read is
        // never half-initialized.
        if (IsStepLimitReached())
            StartCoroutine(EndGameAfterDrawReady(cmd.seq));
        else
            StartCoroutine(SendStateAfterDrawReady(cmd.seq));
    }

    IEnumerator WaitForDrawReady(int maxFrames = 20)
    {
        // Wait until SlotNew has a card whose CardFrame has been initialized
        // (CardFrame.Start populated child cards and ActivateComponents has
        // run), bounded so a stuck draw doesn't hang the bridge forever.
        // We can't just poll numberCard.numberSelected because color/shape/word
        // -only modes legitimately leave the number sentinel as -1000.
        //
        // Each iteration's body is wrapped in try/catch so a transient null
        // ref while the card is half-initialized doesn't kill the coroutine
        // (which would strand the agent on a 30s wait_for). We just retry.
        for (int i = 0; i < maxFrames; i++)
        {
            yield return null;
            bool ready = false;
            try
            {
                if (slotNew == null || !slotNew.GetFilledInfo()) continue;
                Card card = slotNew.GetCardObject();
                if (card == null) continue;
                CardFrame frame = card.GetCardFrame();
                if (frame == null) continue;
                // Force activation if Start has resolved the dimension components.
                frame.EnsureActivated();
                ready = frame.IsInitialized;
            }
            catch (System.Exception e)
            {
                Debug.Log("[AgentBridge] WARN: WaitForDrawReady iter " + i +
                                 " threw, retrying: " + e.Message);
                continue;
            }
            if (ready) yield break;
        }
        Debug.Log("[AgentBridge] WARN: WaitForDrawReady gave up after " + maxFrames + " frames");
    }

    IEnumerator SendStateAfterDrawReady(int seq)
    {
        yield return WaitForDrawReady();
        SafeSendState(seq, "draw_card");
    }

    IEnumerator EndGameAfterDrawReady(int seq)
    {
        yield return WaitForDrawReady();
        SafeSendState(seq, "draw_card");
        yield return null;
        try
        {
            if (levelController != null)
                levelController.BackButtonPressed();
            else
                SceneManager.LoadScene("Scene Selection Screen");
        }
        catch (System.Exception e)
        {
            Debug.Log("[AgentBridge] WARN: EndGameAfterDrawReady scene unload threw: " + e.Message);
        }
    }

    void ExecuteMoveCard(AgentCommand cmd)
    {
        if (!refsReady)
        {
            SendError(cmd.seq, "Game not ready");
            return;
        }

        ResumeTimeForAction();

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

        // Snapshot occupied board count BEFORE the drop so we can detect an
        // unproductive slot-to-slot move (no merge). Only board-to-board
        // moves qualify — placing a freshly-drawn card from "new" into a
        // build slot is always legitimate and never penalised.
        bool sourceIsBuildSlot = (sourceSlot != slotNew);
        int occupiedBefore = CountOccupiedBoardSlots();

        // Capture the potential merge victim BEFORE the drop. If the target
        // slot is occupied, this card will be destroyed by the merge via a
        // delayed Destroy(obj, 0.1f) — which races our state serialization
        // and never fires at all when Time.timeScale == 0. We force a
        // synchronous destroy after the drop so its OnDestroy refund
        // (AddMana(cardMana)) is reflected in the next state snapshot.
        Card cardOther = targetSlot.GetCardObject();
        CardFrame cardFrameOther = cardOther != null ? cardOther.GetCardFrame() : null;

        // Execute programmatic drop
        frame.ExecuteProgrammaticDrop(targetSlot, cmd.motor_time, cmd.motor_distance,
            cmd.motor_dist_to_slot, cmd.motor_half_distance, cmd.motor_min_distances);

        // If a merge happened, the target slot now holds the moving card
        // instead of cardOther. Destroy the orphaned victim synchronously.
        if (cardOther != null && cardOther.gameObject != null &&
            targetSlot.GetCardObject() != cardOther)
        {
            DestroyImmediate(cardOther.gameObject);
            if (cardFrameOther != null && cardFrameOther.gameObject != null)
                DestroyImmediate(cardFrameOther.gameObject);
        }

        IncrementAction();

        if (IsStepLimitReached())
            StartCoroutine(EndGameAfterFrames(cmd.seq, 2));
        else
            StartCoroutine(SendStateAfterMoveCheck(cmd.seq, 2, sourceIsBuildSlot, occupiedBefore));
    }

    /// <summary>
    /// Count how many of the 5 build slots currently hold a card. Used to
    /// decide whether a slot-to-slot move produced a merge (count drops) or
    /// was an unproductive oscillation (count unchanged).
    /// </summary>
    int CountOccupiedBoardSlots()
    {
        int n = 0;
        if (numberedSlots != null)
        {
            for (int i = 0; i < numberedSlots.Length; i++)
            {
                if (numberedSlots[i] != null && numberedSlots[i].GetFilledInfo())
                    n++;
            }
        }
        return n;
    }

    /// <summary>
    /// After a move_card command settles, deduct a small mana penalty if the
    /// source was a build slot AND the occupied count didn't drop — i.e. the
    /// agent shuffled a card between slots without producing a merge. This is
    /// the "oscillation tax": every move already costs a step and ticks the
    /// drain timer, but the in-game mana hit also shows up in the state dump
    /// and the max_mana score, so every agent mode feels the penalty.
    /// </summary>
    IEnumerator SendStateAfterMoveCheck(int seq, int frames, bool sourceIsBuildSlot, int occupiedBefore)
    {
        for (int i = 0; i < frames; i++)
            yield return null;
        try
        {
            TryCacheReferences();

            if (sourceIsBuildSlot && manaDisplay != null)
            {
                int occupiedAfter = CountOccupiedBoardSlots();
                if (occupiedAfter >= occupiedBefore)
                {
                    manaDisplay.SpendMana(UNPRODUCTIVE_MOVE_MANA_PENALTY);
                    Debug.Log($"[AgentBridge] Unproductive slot-to-slot move — deducted " +
                              $"{UNPRODUCTIVE_MOVE_MANA_PENALTY} mana");
                }
            }
        }
        catch (System.Exception e)
        {
            Debug.Log("[AgentBridge] ERROR: move_card post-check threw: " + e);
            SendError(seq, "move_card post-check failed: " + e.Message);
            yield break;
        }

        SafeSendState(seq, "move_card");
    }

    void ExecuteSellCard(AgentCommand cmd)
    {
        if (!refsReady)
        {
            SendError(cmd.seq, "Game not ready");
            return;
        }

        ResumeTimeForAction();

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

        // Move to sell slot triggers sell logic (schedules Destroy(obj, 0.3f))
        frame.ExecuteProgrammaticDrop(slotSell, 0, 0, 0, 0, null);

        // Force synchronous destruction so Card.OnDestroy fires AddMana(cardMana)
        // refund BEFORE we serialize state. The scheduled delayed Destroy would
        // otherwise race our 2-frame state snapshot (and never fire at all when
        // Time.timeScale == 0 during agent-paused play).
        if (card != null && card.gameObject != null)
            DestroyImmediate(card.gameObject);
        if (frame != null && frame.gameObject != null)
            DestroyImmediate(frame.gameObject);

        IncrementAction();

        if (IsStepLimitReached())
            StartCoroutine(EndGameAfterFrames(cmd.seq, 2));
        else
            StartCoroutine(SendStateAfterFrames(cmd.seq, 2));
    }

    // Preview a merge WITHOUT committing it. Used by the greedy agent baseline
    // (and eventually by the merge_preview observation field) to score every
    // candidate merge before picking one. We delegate to the same
    // ComputeMerge*Gain functions the real merge code calls, so the preview is
    // guaranteed to match the actual scoring without any drift.
    //
    // Convention matches CardFrame.AnimateGain:
    //   - cmd.source is the moving card (the one being dragged)
    //   - cmd.target is the slot it would land on (must be occupied)
    //   - per-dim gain returned as the SAME tier values the gain functions
    //     return: -1 = bad, 0 = neutral / inactive, 1 = ok, 2 = great, 3 = perfect
    void ExecutePreviewMerge(AgentCommand cmd)
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
        if (sourceSlot == targetSlot)
        {
            SendError(cmd.seq, "Source and target are the same slot");
            return;
        }
        if (!sourceSlot.GetFilledInfo() || !targetSlot.GetFilledInfo())
        {
            SendError(cmd.seq, "Both source and target must be occupied for a merge preview");
            return;
        }

        CardFrame sourceFrame = GetCardFrame(sourceSlot);
        CardFrame targetFrame = GetCardFrame(targetSlot);
        if (sourceFrame == null || targetFrame == null)
        {
            SendError(cmd.seq, "Missing card object or CardFrame on source/target");
            return;
        }

        // Force activation so a freshly-drawn source card with sentinel values
        // doesn't return spurious 0-gains.
        sourceFrame.EnsureActivated();
        targetFrame.EnsureActivated();

        var msg = new MergePreviewMsg();
        msg.seq = cmd.seq;
        msg.type = "merge_preview";
        msg.source = cmd.source;
        msg.target = cmd.target;

        ComputeMergeGains(sourceFrame, targetFrame,
            out msg.number_gain, out msg.color_gain, out msg.shape_gain, out msg.word_gain);

        // Whether the target card has any merges left. The greedy agent uses
        // this to skip merges that would be rejected by the game.
        msg.target_merges_done = targetFrame.numberOfMerges;
        msg.target_merges_max = targetFrame.maxNumberOfMerges;
        msg.target_can_accept_merge =
            (targetFrame.numberOfMerges < targetFrame.maxNumberOfMerges);

        SendToServer(JsonUtility.ToJson(msg));
    }

    // Pure helper: pull the CardFrame off a SlotGeneric, or null if anything is
    // missing. Used by both ExecutePreviewMerge and the per-state merge preview
    // batch in SerializeGameState.
    CardFrame GetCardFrame(SlotGeneric slot)
    {
        if (slot == null) return null;
        Card card = slot.GetCardObject();
        if (card == null) return null;
        return card.GetCardFrame();
    }

    // Mirrors the hidden detection in SerializeSlot — when MemoryCard is on
    // and the background sprite has been raised above the dim layers, the
    // card face is hidden from the player and we treat it as opaque to the
    // agent too. Used by ComputeMergePreviews to drop entries that would
    // otherwise leak the underlying card identity through the gain math.
    bool IsCardHidden(CardFrame frame)
    {
        if (frame == null || frame.memoryCard == null) return false;
        var bg = frame.GetComponentInChildren<CardFrameBackground>();
        if (bg == null) return false;
        var sr = bg.GetComponent<SpriteRenderer>();
        return sr != null && sr.sortingOrder >= 13;
    }

    // Compute the per-dimension gain tier for a hypothetical merge, using the
    // SAME ComputeMerge*Gain functions the real merge code calls. Inactive
    // dimensions get 0 (the gain functions are no-ops in that case).
    void ComputeMergeGains(
        CardFrame sourceFrame, CardFrame targetFrame,
        out float numberGain, out float colorGain,
        out float shapeGain, out float wordGain)
    {
        numberGain = 0f;
        colorGain = 0f;
        shapeGain = 0f;
        wordGain = 0f;

        if (sourceFrame == null || targetFrame == null) return;

        if (sourceFrame.numberCard != null && targetFrame.numberCard != null)
            numberGain = sourceFrame.numberCard.ComputeMergeNumberGain(
                targetFrame.numberCard.numberSelected);

        if (sourceFrame.colorCard != null && targetFrame.colorCard != null)
            colorGain = sourceFrame.colorCard.ComputeMergeColorGain(
                targetFrame.colorCard.colorSelected, targetFrame.colorCard.colorIndexGray);

        if (sourceFrame.shapeCard != null && targetFrame.shapeCard != null)
            shapeGain = sourceFrame.shapeCard.ComputeMergeShapeGain(
                targetFrame.shapeCard.spriteSelectedIndex);

        if (sourceFrame.wordCard != null && targetFrame.wordCard != null
            && targetFrame.wordCard.wordSelectedList != null)
            wordGain = sourceFrame.wordCard.ComputeMergeWordGain(
                targetFrame.wordCard.wordSelectedList);
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
        // Cancel any in-flight coroutines (especially EndGameAfterFrames from
        // the previous episode — its auto-nav to Scene Selection Screen races
        // with this scene load and can override it, stranding the bridge on a
        // scene with no ManaDisplay/GameTimer → permanent "Game not ready").
        StopAllCoroutines();

        // Reload the gameplay scene for a clean reset
        Debug.Log("[AgentBridge] Resetting — reloading gameplay scene");
        Time.timeScale = 1;
        SceneManager.LoadScene("Level 1 Space for Unity");
        SendAck(cmd.seq, true);
    }

    void ExecuteStartGame(AgentCommand cmd)
    {
        // Cancel any in-flight coroutines from the previous episode.
        // EndGameAfterFrames/EndGameAfterDrawReady auto-navigate to
        // "Scene Selection Screen" after game over. If that coroutine
        // is still pending when start_game arrives, its LoadScene call
        // races with ours and can strand the bridge on a scene that has
        // no gameplay singletons — causing 100% of subsequent get_state
        // calls to return "Game not ready" for the entire reset timeout.
        StopAllCoroutines();

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

        // Perfect-memory ablation: when true, the bridge stops masking hidden
        // card values + stops dropping previews involving hidden cards. Off by
        // default so the Memory dimension stays meaningful.
        perfectMemory = cmd.perfect_memory;

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

        // Pre-computed merge previews — one entry per legal merge candidate
        // this turn. The LLM agents see this in the state description so they
        // can pick the best merge with ground-truth multipliers, no extra
        // round-trip needed.
        state.merge_previews = ComputeMergePreviews();

        return JsonUtility.ToJson(state);
    }

    MergePreviewEntry[] ComputeMergePreviews()
    {
        var entries = new List<MergePreviewEntry>();

        // Build the same source/target lookup that ComputeValidActions uses
        // so the entries align with the MOVE action IDs.
        SlotGeneric[] sources = new SlotGeneric[6];
        sources[0] = slotNew;
        for (int i = 0; i < 5; i++)
            sources[i + 1] = numberedSlots != null && i < numberedSlots.Length
                ? numberedSlots[i] : null;

        string[] sourceNames = new string[] { "new", "1", "2", "3", "4", "5" };

        for (int srcIdx = 0; srcIdx < 6; srcIdx++)
        {
            SlotGeneric src = sources[srcIdx];
            if (src == null || !src.GetFilledInfo()) continue;

            CardFrame srcFrame = GetCardFrame(src);
            if (srcFrame == null) continue;
            // Source must have merges remaining for a merge to be legal.
            if (srcFrame.numberOfMerges >= srcFrame.maxNumberOfMerges) continue;

            // Skip previews involving a hidden source unless perfect_memory is
            // on. The gain values come from the real card data, so emitting
            // them for a hidden card would leak everything memory mode tries
            // to hide (number value, colour, shape, word).
            if (!perfectMemory && IsCardHidden(srcFrame)) continue;

            for (int dstNum = 1; dstNum <= 5; dstNum++)
            {
                if (numberedSlots == null || dstNum - 1 >= numberedSlots.Length) continue;
                SlotGeneric dst = numberedSlots[dstNum - 1];
                if (dst == null || dst == src) continue;
                // Only emit entries for occupied targets — empty-target moves
                // are placement actions, not merges, and have no preview.
                if (!dst.GetFilledInfo()) continue;

                CardFrame dstFrame = GetCardFrame(dst);
                if (dstFrame == null) continue;
                // Target must also have merges left or the merge will be
                // rejected by the game.
                if (dstFrame.numberOfMerges >= dstFrame.maxNumberOfMerges) continue;

                // Same masking on the destination side.
                if (!perfectMemory && IsCardHidden(dstFrame)) continue;

                // Force activation so freshly-drawn cards don't return
                // sentinel-value gains.
                srcFrame.EnsureActivated();
                dstFrame.EnsureActivated();

                var entry = new MergePreviewEntry();
                entry.source = sourceNames[srcIdx];
                entry.target = dstNum.ToString();
                entry.action = 1 + srcIdx * 5 + (dstNum - 1);
                ComputeMergeGains(srcFrame, dstFrame,
                    out entry.number_gain, out entry.color_gain,
                    out entry.shape_gain, out entry.word_gain);
                entries.Add(entry);
            }
        }

        return entries.ToArray();
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

        // Force activation in case the bridge is reading state before
        // CardFrame.Update has had a chance to fire ActivateComponents().
        // Without this, freshly drawn cards intermittently serialize with
        // numberSelected == -1000f and the agent sees a "blank" card.
        frame.EnsureActivated();

        msg.card_mana = card.GetCardMana();
        msg.merges_done = frame.numberOfMerges;
        msg.number_active = frame.numberActive;

        // Memory: check if card is hidden FIRST so we can mask the dim values
        // before they get serialized. The "hidden" signal is the background
        // sprite renderer's sortingOrder being raised above the dim layers
        // (>= 13) — that's how MemoryCard hides the card visually.
        if (frame.memoryCard != null)
        {
            var bg = frame.GetComponentInChildren<CardFrameBackground>();
            if (bg != null)
            {
                var sr = bg.GetComponent<SpriteRenderer>();
                msg.memory_hidden = (sr != null && sr.sortingOrder >= 13);
            }
        }

        // If the card is currently hidden by Memory mode and the run did NOT
        // opt into perfect_memory, drop every dim value here. The agent must
        // remember which face this slot showed before it flipped — leaking
        // the live values defeats the whole dimension. Sentinel zeros are
        // safe because describe_state branches on memory_hidden first.
        bool maskHidden = msg.memory_hidden && !perfectMemory;

        if (!maskHidden)
        {
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
        }
        else
        {
            // Sentinels that match SlotMsg's default-init values, written
            // explicitly so a future refactor that pre-fills the struct
            // doesn't accidentally start leaking real values for hidden
            // cards. shape_index uses -1 which describe_state already treats
            // as "no shape".
            msg.number_value = 0;
            msg.color_r = 0;
            msg.color_g = 0;
            msg.color_b = 0;
            msg.color_index_gray = 0;
            msg.shape_index = -1;
            msg.word_value = "";
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
        Debug.Log("[AgentBridge] WARN: Error: " + message);
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
        // Refresh in case cards were created/destroyed; SafeSendState
        // catches serializer crashes so they can't strand the agent.
        SafeSendState(seq, "post_action");
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
        // memory ablation: when true, the bridge ships card values + previews
        // even for hidden cards. Default false (Memory dimension is real).
        public bool perfect_memory;
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
        // One entry per LEGAL merge candidate this turn (both src and dst
        // occupied, src has merges remaining, src != dst). Lets the LLM and
        // greedy agents see ground-truth gains without an extra round-trip.
        public MergePreviewEntry[] merge_previews;
    }

    [System.Serializable]
    public class MergePreviewEntry
    {
        public string source;        // "new" or "1".."5"
        public string target;        // "1".."5"
        public int action;           // matching MOVE action ID (1..30)
        // Per-dim gain tier (-1=bad, 0=neutral/inactive, 1=ok, 2=great, 3=perfect)
        public float number_gain;
        public float color_gain;
        public float shape_gain;
        public float word_gain;
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

    [System.Serializable]
    public class MergePreviewMsg
    {
        public int seq;
        public string type;          // "merge_preview"
        public string source;        // echoed source slot
        public string target;        // echoed target slot
        // Per-dimension gain tier (-1=bad, 0=neutral/inactive, 1=ok, 2=great, 3=perfect)
        public float number_gain;
        public float color_gain;
        public float shape_gain;
        public float word_gain;
        // Merge-budget info on the target so the agent can avoid invalid merges
        public int target_merges_done;
        public int target_merges_max;
        public bool target_can_accept_merge;
    }
}
