using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.UI;
using TMPro;
using BayatGames.SaveGameFree;
using Michsky.UI.ModernUIPack;

public class GameTimer : MonoBehaviour {

    public static GameTimer Instance { get; private set; }

    private void Awake()
    {
        Instance = this;
    }

    public float levelTime = 40;
    public bool triggeredLevelFinished = false;
    Slider timeSlider;
    SliderManager sliderManager;
    TextMeshProUGUI stepValueText;
    LevelController levelController;
    bool timerFinished = false;
    public float totalTime = 0f;
    float timePreviousFrame;
    public bool gamePaused = false;
    bool doubleTime = false;
    private void Start()
    {
        SetTime();
        timeSlider = GetComponent<Slider>();
        sliderManager = GetComponent<SliderManager>();
        if (sliderManager != null)
            stepValueText = sliderManager.valueText;
        levelController = LevelController.Instance;
        timePreviousFrame = Time.timeSinceLevelLoad;
    }

    public void SetTime()
    {
        doubleTime = SaveGame.Load<bool>("doubleTime");
        levelTime = 20;
        if (doubleTime == true)
        {
            levelTime = levelTime * 2f;
        }
    }

    public bool ReturnTimerFinished()
    {
        //timerFinished = (totalTime >= levelTime);
        return timerFinished;
    }

    // In step-limited (benchmark / human-recording) mode the wall-clock
    // countdown never runs, so `timerFinished` stays false forever.
    // AgentBridge calls this on the step-cap edge so LevelTimerFinished's
    // `gameFinished = gameTimer.ReturnTimerFinished()` resolves to true,
    // propagating the game-over state to the rest of the scene.
    public void ForceFinished()
    {
        timerFinished = true;
    }

    public void TopUpTime()
    {
        totalTime = 0f;
    }

    // Update is called once per frame
    void Update ()
    {
        if (triggeredLevelFinished) { return; }
        if(gamePaused) //|| levelController.ReturnGamePaused())
        {
            timePreviousFrame = Time.timeSinceLevelLoad;
            return;
        }

        // Step-limited (benchmark) mode: the UI shows current/max actions
        // instead of a wall-clock countdown. The game itself is turn-based
        // now, so a seconds display is confounded by inference latency and
        // isn't meaningful. When no benchmark is running (maxSteps == 0),
        // fall back to the legacy time-based display for human play.
        var bridge = AgentBridge.Instance;
        if (bridge != null && bridge.MaxSteps > 0)
        {
            int step = bridge.ActionCount;
            int max = bridge.MaxSteps;
            float remaining = Mathf.Clamp01(1f - (float)step / max);
            timeSlider.value = 100f * remaining;
            if (stepValueText != null)
                stepValueText.text = step + "/" + max;
            // The termination check is owned by AgentBridge (it also fires
            // the end_game message to Python); GameTimer just mirrors the
            // state here so the UI doesn't show 0/100 after the bridge has
            // already torn down.
        }
        else
        {
            timeSlider.value = 100f * (1f - totalTime / levelTime);
            totalTime += Time.timeSinceLevelLoad - timePreviousFrame;
            timePreviousFrame = Time.timeSinceLevelLoad;
            timerFinished = (totalTime >= levelTime);
            if (timerFinished)
            {
                levelController.LevelTimerFinished();
            }
        }
	}
}
