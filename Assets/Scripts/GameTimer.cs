using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.UI;
using BayatGames.SaveGameFree;

public class GameTimer : MonoBehaviour {

    public float levelTime = 40;
    public bool triggeredLevelFinished = false;
    Slider timeSlider;
    LevelController levelController;
    bool timerFinished = false;
    float totalTime = 0f;
    float timePreviousFrame;
    public bool gamePaused = false;
    bool doubleTime = false;
    private void Start()
    {
        SetTime();
        timeSlider = GetComponent<Slider>();
        levelController = FindObjectOfType<LevelController>();
        timePreviousFrame = Time.timeSinceLevelLoad;
    }

    public void SetTime()
    {
        doubleTime = SaveGame.Load<bool>("doubleTime");
        levelTime = 10; //84, 105
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
        timeSlider.value = 100f * (1f - totalTime / levelTime);
        totalTime += Time.timeSinceLevelLoad - timePreviousFrame;
        timePreviousFrame = Time.timeSinceLevelLoad;
        timerFinished = (totalTime >= levelTime);
        if (timerFinished)
        {
            levelController.LevelTimerFinished();
            //triggeredLevelFinished = true;
        }
	}
}
